import requests
import os
from dotenv import load_dotenv
load_dotenv()

KIBANA_URL = os.getenv("KIBANA_URL")
KIBANA_API_KEY = os.getenv("KIBANA_API_KEY")
INSIGHTS_AGENT_ID = os.getenv("INSIGHTS_AGENT_ID")


# calls the Kibana insights agent to answer natural language questions across all meetings
def get_insights(question: str) -> dict:
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"ApiKey {KIBANA_API_KEY}",
        "kbn-xsrf": "true"
    }
    payload = {
        "agent_id": INSIGHTS_AGENT_ID,
        "input": question
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
        reply = data.get("response", {}).get("message", str(data))
        return {"success": True, "reply": reply}

    except Exception as e:
        return {"success": False, "error": str(e)}