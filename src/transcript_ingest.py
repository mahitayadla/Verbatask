from datetime import datetime, timezone
from elasticsearch import Elasticsearch
import os
from dotenv import load_dotenv

load_dotenv()

es = Elasticsearch(os.getenv("ELASTICSEARCH_URL"), api_key=os.getenv("ELASTICSEARCH_API"))

# indexes parsed transcript messages into the meeting_messages index
def index_meeting_messages(meeting_id, parsed_transcript):
    for message in parsed_transcript:

        if "speaker" not in message or "text" not in message:
            continue
        
        doc = {
            "meeting_id": meeting_id,
            "speaker": message["speaker"],
            "text": message["text"],
            "ingested_at": datetime.now(timezone.utc).isoformat()
        }
        
        es.index(index="meeting_messages", document=doc)
    return True