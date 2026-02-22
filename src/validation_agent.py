import requests
import os
from dotenv import load_dotenv
from datetime import date
from elasticsearch import Elasticsearch

load_dotenv()

KIBANA_URL = os.getenv("KIBANA_URL")
KIBANA_API_KEY = os.getenv("KIBANA_API_KEY")
VALIDATION_AGENT_ID = os.getenv("VALIDATION_AGENT_ID")

es = Elasticsearch(os.getenv("ELASTICSEARCH_URL"), api_key=os.getenv("ELASTICSEARCH_API"))

def validate_action_items(meeting_id: str) -> dict:
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"ApiKey {KIBANA_API_KEY}",
        "kbn-xsrf": "true"
    }
    payload = {
        "agent_id": VALIDATION_AGENT_ID,
        "input": f"Today's date is {date.today().isoformat()}. Validate action items for meeting_id: {meeting_id}. Only mark items as Overdue if their due date is strictly before today, not equal to today."
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
        validation_reply = data.get("response", {}).get("message", str(data))

        es.index(index="meeting_validations", id=meeting_id,
                 body={"meeting_id": meeting_id, "validation_reply": validation_reply})
        return {"meeting_id": meeting_id, "success": True, "validation_reply": validation_reply}

    except Exception as e:
        return {"meeting_id": meeting_id, "success": False, "error": str(e)}