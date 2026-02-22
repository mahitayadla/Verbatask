import requests
import os
from dotenv import load_dotenv
from elasticsearch import Elasticsearch

load_dotenv()

KIBANA_URL = os.getenv("KIBANA_URL")
KIBANA_API_KEY = os.getenv("KIBANA_API_KEY")
SUMMARY_AGENT_ID = os.getenv("MEETING_SUMMARY_AGENT_ID")

es = Elasticsearch(os.getenv("ELASTICSEARCH_URL"), api_key=os.getenv("ELASTICSEARCH_API"))

def summarize_meeting(meeting_id: str) -> dict:
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"ApiKey {KIBANA_API_KEY}",
        "kbn-xsrf": "true"
    }
    payload = {
        "agent_id": SUMMARY_AGENT_ID,
        "input": f"Summarize meeting_id: {meeting_id}"
    }

    try:
        res = requests.post(
            f"{KIBANA_URL}/api/agent_builder/converse",
            json=payload,
            headers=headers,
            timeout=120
        )
        res.raise_for_status()
        data = res.json()
        summary = data.get("response", {}).get("message", str(data))

        es.index(index="meeting_summaries", id=meeting_id, body={"meeting_id": meeting_id, "summary": summary})
        return {"meeting_id": meeting_id, "success": True, "summary": summary}

    except Exception as e:
        return {"meeting_id": meeting_id, "success": False, "error": str(e)}