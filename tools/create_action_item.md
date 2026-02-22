# create_action_item tool

**Tool ID:** `create_action_item`  

**Purpose / Description:**  
Creates a formal action item with a full tracking schema.

---

**Type:** MCP

The MCP server runs locally via tools.py and is exposed publicly using ngrok. To connect:

Run the MCP server: python src/tools.py
In a separate terminal, expose it: ngrok http 8000
Create a new connector in Kibana pointing to your ngrok URL
Copy the ngrok URL and add it as the MCP Server URL.

In the tool settings, select the newly created connector as the MCP server. The tools will be automatically detected
Select create_action_item to create the tool

---

## Agents:
Used in Action Item Extraction agent.
