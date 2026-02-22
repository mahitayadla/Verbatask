#creates all the indexes in ES. Can skip if indexes already exist.
from elasticsearch import Elasticsearch
import os
from dotenv import load_dotenv

load_dotenv()

es = Elasticsearch(os.getenv("ELASTICSEARCH_URL"), api_key=os.getenv("ELASTICSEARCH_API"))

INDICES = {

    "meeting_messages": {
        "mappings": {
            "properties": {
                "meeting_id": {"type": "keyword"},
                "speaker": {"type": "keyword"},
                "text": {"type": "text"},
                "ingested_at": {"type": "date"}
            }
        }
    },

    "action_items": {
        "mappings": {
            "properties": {
                "action_id": {"type": "keyword"},
                "meeting_id": {"type": "keyword"},
                "task": {"type": "text"},
                "owner": {"type": "keyword"},
                "team": {"type": "keyword"},
                "due_date": {"type": "keyword"},
                "status": {"type": "keyword"},
                "risk_level": {"type": "keyword"},
                "created_at": {"type": "date"}
            }
        }
    },

    "meeting_summaries": {
        "mappings": {
            "properties": {
                "meeting_id": {"type": "keyword"},
                "summary": {"type": "text"}
            }
        }
    },

    "meeting_validations": {
        "mappings": {
            "properties": {
                "meeting_id": {"type": "keyword"},
                "validation_reply": {"type": "text"}
            }
        }
    }
}

def setup_indices():

    for name, body in INDICES.items():
        if not es.indices.exists(index=name):
            es.indices.create(index=name, body=body)
            print(f"Created index: {name}")
        else:
            print(f"Index already exists: {name}")

if __name__ == "__main__":
    setup_indices()