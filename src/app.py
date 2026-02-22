import streamlit as st
from elasticsearch import Elasticsearch
from dotenv import load_dotenv
import os
from transcript_parser import parse_transcript
from transcript_ingest import index_meeting_messages
from extract_action_items import extract_and_store_action_items
from meeting_summary_agent import summarize_meeting
from validation_agent import validate_action_items
import json
from datetime import datetime, date
from insights_agent import get_insights


load_dotenv()

st.set_page_config(page_title="VerbaTask", layout="wide", initial_sidebar_state="expanded")

es = Elasticsearch(os.getenv("ELASTICSEARCH_URL"), api_key=os.getenv("ELASTICSEARCH_API"))


risk_colors = {"High": "red", "Medium": "orange", "Low": "green"}
status_colors = {"Open":"#2563eb", "Overdue": "#dc2626", "Completed": "#16a34a"}


def get_all_action_items():

    try:
        res = es.search(index="action_items", body={"query": {"match_all": {}}, "size": 1000})
        items = []
        for h in res["hits"]["hits"]:
            item = h["_source"]
            item["_id"] = h["_id"]
            items.append(item)
        return items
    except:
        return []

def update_status(doc_id, new_status):
    try:
        es.update(index="action_items", id=doc_id, body={"doc": {"status": new_status}})
        return True
    except:
        return False

def extract_text(value):

    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        if "response" in value and isinstance(value["response"], dict):
            return value["response"].get("message", str(value))
        return value.get("message") or value.get("output") or value.get("response") or str(value)
    return str(value)



#Sidebar

with st.sidebar:
    st.title("VerbaTask")
    st.caption("Your meeting, tracked.")
    st.divider()
    page = st.radio(
        "Navigate",
        ["Dashboard", "Process Transcripts", "Ask Insights", "About & Architecture"],
        label_visibility="collapsed"
    )




#Dashboard Page

if page == "Dashboard":
    st.title("Action Item Tracker")
    st.caption("Track and manage action items across all your meetings")
    st.divider()

    all_items = get_all_action_items()

    if not all_items:
        st.info("No action items found yet. Head over to **Process Transcripts** to get started!")

    else:
        total_meetings = 0
        total_open = 0
        total_overdue = 0
        total_completed = 0
        meeting_ids = []

        for item in all_items:
            mid = item.get("meeting_id")
            if mid and mid not in meeting_ids:
                meeting_ids.append(mid)
                total_meetings += 1
            status = item.get("status")
            if status == "Open":
                total_open += 1
            elif status == "Overdue":
                total_overdue += 1
            elif status == "Completed":
                total_completed += 1

        completion_rate = round(total_completed / len(all_items) * 100) if all_items else 0

        col1, col2, col3, col4, col5 = st.columns(5)

        col1.markdown(f"**Meetings**\n\n<div style='font-size:2rem;font-weight:700;padding-left:0.5rem'>{total_meetings}</div>", unsafe_allow_html=True)
        col2.markdown(f"**Open**\n\n<div style='font-size:2rem;font-weight:700;padding-left:0.5rem;color:{status_colors['Open']}'>{total_open}</div>", unsafe_allow_html=True)
        col3.markdown(f"**Overdue**\n\n<div style='font-size:2rem;font-weight:700;padding-left:0.5rem;color:{status_colors['Overdue']}'>{total_overdue}</div>", unsafe_allow_html=True)
        col4.markdown(f"**Completed**\n\n<div style='font-size:2rem;font-weight:700;padding-left:0.5rem;color:{status_colors['Completed']}'>{total_completed}</div>", unsafe_allow_html=True)
        col5.markdown(f"**Completion Rate**\n\n<div style='font-size:2rem;font-weight:700;padding-left:0.5rem;color:{status_colors['Completed']}'>{completion_rate}%</div>", unsafe_allow_html=True)

        st.divider()

        sel_col, prog_col = st.columns([2, 3])
        meetings = sorted(meeting_ids)
        with sel_col:
            selected = st.selectbox("Select a Meeting", meetings)

        meeting_items = [item for item in all_items if item.get("meeting_id") == selected]
        done_count = sum(1 for item in meeting_items if item.get("status") == "Completed")
        progress = done_count / len(meeting_items) if meeting_items else 0

        with prog_col:
            st.write("")
            st.progress(progress, text=f"{done_count} of {len(meeting_items)} tasks completed ({round(progress * 100)}%)")

        st.divider()

        with st.expander("Filters", expanded=False):
            fcol1, fcol2 = st.columns(2)
            filter_status = fcol1.multiselect("Status", ["Open", "Overdue", "Completed"], default=["Open", "Overdue", "Completed"])
            filter_risk = fcol2.multiselect("Risk Level", ["High", "Medium", "Low"], default=["High", "Medium", "Low"])

        filtered = [
            i for i in meeting_items
            if i.get("status") in filter_status and i.get("risk_level", "Medium") in filter_risk
        ]

        hcol1, hcol2, hcol3, hcol4, hcol5, hcol6 = st.columns([0.5, 2.5, 1.5, 1.5, 1, 1])
        hcol1.caption("Done")
        hcol2.caption("Task")
        hcol3.caption("Owner")
        hcol4.caption("Due Date")
        hcol5.caption("Risk")
        hcol6.caption("Status")
        

        if not filtered:
            st.warning("No items match your filters.")
        else:
            for item in filtered:
                is_done = item.get("status") == "Completed"
                risk = item.get("risk_level", "Medium")
                status = item.get("status", "Open")

                c1, c2, c3, c4, c5, c6 = st.columns([0.5, 2.5, 1.5, 1.5, 1, 1])

                checked = c1.checkbox("", value=is_done, key=f"chk_{item['_id']}", label_visibility="collapsed")
                if checked != is_done:
                    update_status(item["_id"], "Completed" if checked else "Open")
                    st.rerun()

                task_text = f"~~{item.get('task', '')}~~" if is_done else item.get("task", "")
                c2.markdown(task_text)
                c3.write(item.get("owner", "—"))

                current_due = item.get("due_date")
                try:
                    default_date = datetime.strptime(current_due, "%Y-%m-%d").date() if current_due and current_due != "null" else None
                except:
                    default_date = None
                new_date = c4.date_input("", value=default_date, key=f"date_{item['_id']}", label_visibility="collapsed")
                if new_date and new_date.isoformat() != (current_due or ""):
                    es.update(index="action_items", id=item["_id"], body={"doc": {"due_date": new_date.isoformat()}})
                    st.rerun()

                risk_options = ["High", "Medium", "Low"]
                current_risk_index = risk_options.index(risk) if risk in risk_options else 1
                new_risk = c5.selectbox("", risk_options, index=current_risk_index, key=f"risk_{item['_id']}", label_visibility="collapsed")
                if new_risk != risk:
                    es.update(index="action_items", id=item["_id"], body={"doc": {"risk_level": new_risk}})
                    st.rerun()

                c6.markdown(f"<span style='color:{status_colors.get(status, 'gray')}'>{status}</span>", unsafe_allow_html=True)
                


        st.divider()
        if st.button("Re-validate Meeting", key="revalidate_btn"):
            today = date.today().isoformat()
            result = es.update_by_query(
                index="action_items",
                body={
                    "script": {"source": "ctx._source.status = 'Overdue'"},
                    "query": {
                        "bool": {
                            "must": {"term": {"status": "Open"}},
                            "filter": {"range": {"due_date": {"lt": today}}}
                        }
                    }
                }
            )
            updated = result.get("updated", 0)
            with st.spinner("Re-running validation..."):
                validation = validate_action_items(selected)
            if validation["success"]:
                st.success(f"Done. {updated} items marked Overdue, validation report updated.")
                st.rerun()
            else:
                st.error(f"Validation failed: {validation['error']}")

        st.divider()

        intel_col1, intel_col2 = st.columns(2)

        with intel_col1:
            try:
                summary_doc = es.get(index="meeting_summaries", id=selected)
                summary_text = extract_text(summary_doc["_source"]["summary"])
                with st.expander("Meeting Summary", expanded=False):
                    st.markdown(summary_text)
            except:
                with st.expander("Meeting Summary", expanded=False):
                    st.caption("No summary available for this meeting yet.")

        with intel_col2:
            try:
                validation_doc = es.get(index="meeting_validations", id=selected)
                validation_text = extract_text(validation_doc["_source"]["validation_reply"])
                with st.expander("Validation Report", expanded=False):
                    st.markdown(validation_text)
            except:
                with st.expander("Validation Report", expanded=False):
                    st.caption("No validation report available for this meeting yet.")




#Process Meeting Page

elif page == "Process Transcripts":
    st.title("Process Meeting Transcript")
    st.caption("Upload or paste a transcript to run the full agent pipeline")
    st.divider()

    tab_paste, tab_upload = st.tabs(["Paste Transcript", "Upload File"])

    with tab_paste:
        text_input = st.text_area(
            "Paste your meeting transcript here",
            height=250,
            placeholder="Paste/Type here"
        )

    with tab_upload:
        file = st.file_uploader("Upload a .txt transcript file", type=["txt"])
        if file:
            st.success(f"File loaded: **{file.name}**")

    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.makedirs(os.path.join(BASE_DIR, "raw_data"), exist_ok=True)
    os.makedirs(os.path.join(BASE_DIR, "parsed_data"), exist_ok=True)

    st.divider()

    if st.button("Process Transcript", type="primary", use_container_width=True):

        if file:
            raw_text = file.read().decode("utf-8")
        elif text_input.strip():
            raw_text = text_input
        else:
            st.warning("Please paste or upload a transcript first.")
            st.stop()

        messages = parse_transcript(raw_text)
        if not messages:
            st.error("No messages detected. Check your transcript format.")
            st.stop()

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        parsed_name = f"M_{ts}.json"
        meeting_id = os.path.splitext(parsed_name)[0]

        with open(os.path.join(BASE_DIR, "raw_data", f"M_{ts}.txt"), "w") as f:
            f.write(raw_text)
        with open(os.path.join(BASE_DIR, "parsed_data", parsed_name), "w") as f:
            json.dump(messages, f, indent=2)

        st.info(f"Meeting ID: `{meeting_id}` | Parsed **{len(messages)} messages**")
        st.divider()

        with st.status("Processing...", expanded=True) as pipeline_status:
            st.write("Step 1: Indexing transcript into Elasticsearch...")
            index_meeting_messages(meeting_id, messages)
            st.write("Transcript indexed")

            st.write("Step 2: Item Action Extraction Agent: finding action items...")
            result = extract_and_store_action_items(meeting_id)
            if result["success"]:
                st.write("Action items extracted and stored")
            else:
                st.write(f"Extraction failed: {result['error']}")

            st.write("Step 3: Meeting Summary Agent: generating meeting summary...")
            summary = summarize_meeting(meeting_id)
            if summary["success"]:
                st.write("Summary generated and saved")
            else:
                st.write(f"Summary failed: {summary['error']}")

            st.write("Step 4: Overdue Item Validator Agent: checking for overdue items...")
            validation = validate_action_items(meeting_id)
            if validation["success"]:
                st.write("Validation complete")
            else:
                st.write(f"Validation failed: {validation['error']}")

            pipeline_status.update(label="Done!", state="complete")

        st.divider()
        st.subheader("Results")

        res_col1, res_col2 = st.columns(2)
        with res_col1:
            if result.get("success"):
                with st.expander("Extracted Action Items", expanded=True):
                    st.markdown(extract_text(result["agent_reply"]))
        with res_col2:
            if summary.get("success"):
                with st.expander("Meeting Summary", expanded=True):
                    st.markdown(extract_text(summary["summary"]))

        if validation.get("success"):
            with st.expander("Validation Report"):
                st.markdown(extract_text(validation["validation_reply"]))

        st.success(f"Done! Head to **Dashboard** to manage tasks from `{meeting_id}`.")




#Ask Insights Page

elif page == "Ask Insights":
    st.title("Ask Insights")
    st.caption("Ask natural language questions across all your meetings and action items")
    st.divider()

    st.subheader("Suggested Questions")
    suggestions = [
        "Who has the most overdue tasks?",
        "Which meeting had the most action items?",
        "Which high-risk tasks are still open?",
    ]

    cols = st.columns(3)
    for i, q in enumerate(suggestions):
        if cols[i].button(q, use_container_width=True):
            st.session_state["insights_question"] = q
            st.rerun()

    st.divider()

    question = st.text_input(
        "Ask anything",
        value=st.session_state.get("insights_question", ""),
        placeholder="Type here"
    )

    ask_col, clear_col = st.columns([5, 1])
    ask_clicked = ask_col.button("Ask", type="primary", use_container_width=True)
    if clear_col.button("Clear", use_container_width=True):
        st.session_state.pop("insights_question", None)
        st.session_state.pop("insights_reply", None)
        st.rerun()

    if ask_clicked:
        if question.strip():
            with st.spinner("Analyzing your meetings..."):
                result = get_insights(question)
            if result["success"]:
                st.session_state["insights_reply"] = extract_text(result["reply"])
                st.session_state["insights_question"] = question
            else:
                st.error(f"Error: {result['error']}")
        else:
            st.warning("Please enter a question.")

    if "insights_reply" in st.session_state:
        st.divider()
        st.subheader("Answer")
        with st.container(border=True):
            st.markdown(st.session_state["insights_reply"])




#About & Architecture Page 

elif page == "About & Architecture":
    st.title("About VerbaTask")
    st.caption("A multi-agent system for meeting transcript analysis")
    st.divider()

    left, right = st.columns([3, 2])

    with left:
        st.subheader("What is VerbaTask?")
        st.write(
            "VerbaTask is a multi-agent AI system that turns raw meeting transcripts into structured, "
            "tracked action items automatically. Most meetings end with notes that need to be manually tracked or entered into project management platforms. "
            "VerbaTask fixes that by running a pipeline of four specialized AI agents the moment a transcript is uploaded."
        )

        st.subheader("The Problem")
        st.write(
            "Teams lose hours every week manually pulling action items from meeting notes, "
            "assigning owners, and chasing follow-ups. Accountability is weak because the process is manual and inconsistent."
        )

        st.subheader("The Solution")
        st.write(
            "Paste or upload any meeting transcript. VerbaTask automatically extracts every action item, "
            "assigns owners, assesses risk, summarizes the meeting, validates completeness, and stores everything in "
            "Elasticsearch, ready to query, track, and act on."
        )

    with right:
        st.subheader("Tech Stack")
        with st.container(border=True):
            st.markdown("**Elasticsearch Agent Builder**")
            st.caption("Hosts all four agents, manages tool orchestration, and stores/retrieves data")
            st.divider()
            st.markdown("**Python**")
            st.caption("Agent logic, transcript parsing, and pipeline orchestration")
            st.divider()
            st.markdown("**Streamlit**")
            st.caption("Full interactive UI dashboard and pipeline runner")

    st.divider()

    st.subheader("The Four Agents")
    st.caption("Run sequentially every time a transcript is processed")

    a1, a2, a3, a4 = st.columns(4)

    with a1:
        with st.container(border=True):
            st.markdown("**1. Action Item Extraction Agent**")
            st.caption("Reads the full transcript and extracts every action item with owner, due date, risk level and status. Writes results to the action_items index.")

    with a2:
        with st.container(border=True):
            st.markdown("**2. Meeting Summary Agent**")
            st.caption("Generates a concise meeting summary covering key decisions, blockers, and outcomes. Saved to meeting_summaries index.")

    with a3:
        with st.container(border=True):
            st.markdown("**3. Overdue Item Validator Agent**")
            st.caption("Checks all open action items and flags any where the due date has passed as Overdue. Saved to meeting_validations index.")

    with a4:
        with st.container(border=True):
            st.markdown("**4. Insights Agent**")
            st.caption("Answers natural language questions across all meetings using semantic search on the action_items index.")

    st.divider()

    st.subheader("Tools Used by Agents")

    t1, t2, t3, t4 = st.columns(4)

    with t1:
        with st.container(border=True):
            st.markdown("**search_meeting_messages**")
            st.caption("Used by Action Item Extraction Agent and Meeting Summary agents. Fetches all messages for a given meeting_id from the meeting_messages index.")

    with t2:
        with st.container(border=True):
            st.markdown("**create_action_item**")
            st.caption("Used by the Action Item Extraction Agent. Creates a new action item in the action_items index.")

    with t3:
        with st.container(border=True):
            st.markdown("**update_action_item**")
            st.caption("Used by Overdue Item Validator Agent. Updates the status of an action item to Overdue when due date has passed.")

    with t4:
        with st.container(border=True):
            st.markdown("**platform.core.search**")
            st.caption("Used by insights agent and Overdue Item Validator Agent. Native Elasticsearch tool for semantic search and ES|QL queries across all indices.")

    st.divider()
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    st.subheader("Architecture Diagram")
    st.image(os.path.join(BASE_DIR, "docs", "verbatask_architecture.png"), use_container_width=True)
  
    st.divider()

    st.subheader("Elasticsearch Indices")

    ic1, ic2 = st.columns(2)
    with ic1:
        with st.container(border=True):
            st.markdown("**`meeting_messages`**")
            st.caption("Raw transcript messages per meeting.")
            st.code('{ "meeting_id", "speaker", "text", "ingested_at" }', language="json")

        with st.container(border=True):
            st.markdown("**`meeting_summaries`**")
            st.caption("Meeting summaries generated by the Summary Agent.")
            st.code('{ "meeting_id", "summary" }', language="json")

    with ic2:
        with st.container(border=True):
            st.markdown("**`action_items`**")
            st.caption("Structured action items. Updated in real time as users mark tasks complete.")
            st.code('{ ""action_id", meeting_id", "task", "owner", "due_date", "team", "risk_level", "status", "created_at" }', language="json")
    
        with st.container(border=True):
            st.markdown("**`meeting_validations`**")
            st.caption("Validation reports from the Validation Agent.")

            st.code('{ "meeting_id", "validation_reply" }', language="json")
