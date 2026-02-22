from fastmcp import FastMCP
from elasticsearch import Elasticsearch
import os
import uuid
from datetime import datetime
from dotenv import load_dotenv


load_dotenv()
mcp = FastMCP("Meeting Intelligence Agent")
es = Elasticsearch(os.getenv("ELASTICSEARCH_URL"), api_key=os.getenv("ELASTICSEARCH_API"))


# creates and stores a new action item in the action_items index
@mcp.tool()
def create_action_item(task: str, owner: str, meeting_id: str, team: str = None, due_date: str = None, risk_level: str = "Medium"):

    doc = {
        "action_id": str(uuid.uuid4())[:8],
        "meeting_id": meeting_id,
        "task": task,
        "owner": owner,
        "team": team,
        "due_date": due_date,
        "status": "Open",
        "created_at": datetime.now().isoformat(),
        "risk_level": risk_level
    }
    try:
        es.index(index="action_items", document=doc)
        return f"Created action item: {task} (ID: {doc['action_id']}) assigned to {owner}."
    except Exception as e:
        return f"Error creating action item: {str(e)}"
    


# updates the status of an existing action item to Open, Completed, or Overdue
@mcp.tool()
def update_action_item(action_id: str = None, status: str = None):
    from datetime import date
    today = date.today().isoformat()

    try:
        if action_id and status:
            result = es.update_by_query(
                index="action_items",
                body={
                    "script": {
                        "source": "ctx._source.status = params.status",
                        "params": {"status": status}
                    },
                    "query": {"term": {"action_id": action_id}}
                }
            )

            updated = result.get("updated", 0)
            return f"Updated {updated} item(s) with action_id {action_id} to {status}."

        overdue = es.update_by_query(
            index="action_items",
            body={
                "script": {
                    "source": "ctx._source.status = 'Overdue'",
                },
                "query": {
                    "bool": {
                        "must": {"term": {"status": "Open"}},
                        "filter": {"range": {"due_date": {"lt": today}}}
                    }
                }
            }
        )

        swept = overdue.get("updated", 0)
        return f"Swept {swept} overdue items."

    except Exception as e:
        return f"Error: {str(e)}"


if __name__ == "__main__":
    mcp.run(transport="http", port=8000)