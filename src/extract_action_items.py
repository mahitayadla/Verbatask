import requests
import os
from datetime import date
from dotenv import load_dotenv

load_dotenv()

KIBANA_URL = os.getenv("KIBANA_URL")
KIBANA_API_KEY = os.getenv("KIBANA_API_KEY")
AGENT_ID = os.getenv("ACTION_ITEM_EXTRACTION_AGENT_ID")


def extract_and_store_action_items(meeting_id: str) -> dict:
    
    today = date.today().isoformat()

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"ApiKey {KIBANA_API_KEY}",
        "kbn-xsrf": "true"
    }

    payload = {
        "agent_id": AGENT_ID,
        "input": f"Today is {date.today().strftime('%A, %Y-%m-%d')}. Extract all action items from meeting_id: {meeting_id}. Resolve any relative dates like 'tomorrow' or 'next Monday' into absolute YYYY-MM-DD dates based on today."
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
        agent_reply = data.get("response", {}).get("message", str(data))
        return {"meeting_id": meeting_id, "success": True, "agent_reply": agent_reply}

    except Exception as e:
        return {"meeting_id": meeting_id, "success": False, "error": str(e)}