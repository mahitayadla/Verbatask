# search_meeting_messages tool

This tool needs to be created in the Elasticsearch Agent Builder platform.

**Tool ID:** `search_meeting_messages`  
**Display Name:** Overdue Item Validator Agent  

**Purpose / Description:**  
Searches the meeting_messages index for a given meeting_id. Returns all messages from that meeting so the Action Item Extraction Agent can extract actionable tasks. Only fetches messages; does not modify or index anything.

---

**Type:** Index Search

**Target Pattern:** `meeting_messages`

---

## Custom Instructions

Always filter by meeting_id. Return all rows for the matching meeting.

---

## Agents:
Used in Action Item Extraction Agent and Meeting Summary Agent.






