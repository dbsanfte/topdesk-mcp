from fastmcp import FastMCP
from topdesk_mcp import _topdesk_sdk as topdesk_sdk
import os

# Load config from environment variables
TOPDESK_URL = os.environ.get("TOPDESK_URL")
TOPDESK_USERNAME = os.environ.get("TOPDESK_USERNAME")
TOPDESK_PASSWORD = os.environ.get("TOPDESK_PASSWORD")

if not (TOPDESK_URL and TOPDESK_USERNAME and TOPDESK_PASSWORD):
    raise RuntimeError("Missing TOPdesk credentials. Set TOPDESK_URL, TOPDESK_USERNAME, and TOPDESK_PASSWORD as environment variables.")

# Initialise TOPdesk SDK
topdesk_client = topdesk_sdk.connect(TOPDESK_URL, TOPDESK_USERNAME, TOPDESK_PASSWORD)

# Initialise the MCP server
mcp = FastMCP("TOPdesk MCP Server")

###################
# HINTS
###################
@mcp.tool()
def get_fiql_query_howto() -> str:
    """Get a hint on how to construct FIQL queries, with examples."""
    try:
        with open(os.path.join(os.path.dirname(__file__), "resources", "fiql_query_howto.md"), "r", encoding="utf-8") as file:
            return file.read()
    except Exception as e:
        return f"Error reading FIQL query guide: {str(e)}"

##################
# SCHEMAS
##################
@mcp.tool()
def get_object_schemas() -> str:
    """Get the full object schemas for TOPdesk incidents and all their subfields."""
    try:
        with open(os.path.join(os.path.dirname(__file__), "resources", "object_shemas.yaml"), "r", encoding="utf-8") as file:
            return file.read()
    except Exception as e:
        return f"Error reading object schemas: {str(e)}"

#################
# INCIDENTS
#################
@mcp.tool()
def get_incident(incident_id: str) -> dict:
    """Get a TOPdesk incident by UUID or by Incident Number (I-xxxxxx-xxx). Both formats are accepted."""
    return topdesk_client.incident.get(incident_id)

@mcp.tool()
def get_incidents_by_fiql_query(query: str) -> list:
    """Get TOPdesk incidents by FIQL query."""
    return topdesk_client.incident.get_list(query=query)

@mcp.tool()
def get_incident_user_requests(incident_id: str) -> list:
    """Get all user requests on a TOPdesk incident."""
    return topdesk_client.incident.request.get_list(incident_id=incident_id)

@mcp.tool()
def create_incident(caller_id: str, incident_fields: dict) -> dict:
    """Create a new TOPdesk incident."""
    return topdesk_client.incident.create(caller=caller_id, **incident_fields)

@mcp.tool()
def archive_incident(incident_id: str) -> dict:
    """Archive a TOPdesk incident."""
    return topdesk_client.incident.archive(incident_id)

@mcp.tool()
def unarchive_incident(incident_id: str) -> dict:
    """Unarchive a TOPdesk incident."""
    return topdesk_client.incident.unarchive(incident_id)

@mcp.tool()
def get_timespent_on_incident(incident_id: str) -> list:
    """Get all time spent entries for a TOPdesk incident."""
    return topdesk_client.incident.timespent.get(incident_id=incident_id)

@mcp.tool()
def register_timespent_on_incident(incident_id: str, time_spent: int) -> dict:
    """Register time spent on a TOPdesk incident."""
    return topdesk_client.incident.timespent.register(incident_id=incident_id, time_spent=time_spent)

@mcp.tool()
def escalate_incident(incident_id: str, reason_id: str) -> dict:
    """Escalate a TOPdesk incident."""
    return topdesk_client.incident.escalate(incident=incident_id, reason=reason_id)

@mcp.tool()
def get_available_escalation_reasons() -> list:
    """Get all available escalation reasons for a TOPdesk incident."""
    return topdesk_client.incident.escalation_reasons()

@mcp.tool()
def get_available_deescalation_reasons() -> list:
    """Get all available de-escalation reasons for a TOPdesk incident."""
    return topdesk_client.incident.deescalation_reasons()

@mcp.tool()
def deescalate_incident(incident_id: str, reason_id: str) -> dict:
    """De-escalate a TOPdesk incident."""
    return topdesk_client.incident.deescalate(incident=incident_id, reason_id=reason_id)

@mcp.tool()
def get_progress_trail(incident_id: str) -> list:
    """Get the progress trail for a TOPdesk incident."""
    return topdesk_client.incident.get_progress_trail(incident_id=incident_id)

##################
# OPERATORS
##################
@mcp.tool()
def get_operatorgroups(archived: bool = False, page_size: int = 100, query: str = None) -> list:
    """Get a list of TOPdesk operator groups, optionally by FIQL query or leave blank to return all groups."""
    return topdesk_client.operator.get_operatorgroups(archived=archived, page_size=page_size, query=query)

@mcp.tool()
def get_operator(operator_id: str) -> dict:
    """Get a TOPdesk operator by ID."""
    return topdesk_client.operator.get(operator_id)

@mcp.tool()
def get_operators_by_fiql_query(query: str) -> list:
    """Get TOPdesk operators by FIQL query."""
    return topdesk_client.operator.get_list(query=query)

##################
# ACTIONS
##################
@mcp.tool()
def add_action_to_incident(incident_id: str, text: str) -> dict:
    """Add an action (ie, reply/comment) to a TOPdesk incident."""
    return topdesk_client.incident.patch(incident_id, action=text)

@mcp.tool()
def get_incident_actions(incident_id: str) -> list:
    """Get all actions (ie, replies/comments) for a TOPdesk incident."""
    return topdesk_client.incident.action.get_list(incident_id=incident_id)

@mcp.tool()
def delete_incident_action(incident_id: str, action_id: str) -> dict:
    """Delete a specific action (ie, reply/comment) for a TOPdesk incident."""
    return topdesk_client.incident.action.delete(incident_id=incident_id, action_id=action_id)

################
# PERSONS
################
@mcp.tool()
def get_person_by_query(query: str) -> list:
    """Get TOPdesk persons by FIQL query."""
    return topdesk_client.person.get_list(query=query)

@mcp.tool()
def get_person(person_id: str) -> dict:
    """Get a TOPdesk person by ID."""
    return topdesk_client.person.get(person_id)

@mcp.tool()
def create_person(person: dict) -> dict:
    """Create a new TOPdesk person."""
    return topdesk_client.person.create(**person)

@mcp.tool()
def update_person(person_id: str, updated_fields: dict) -> dict:
    """Update an existing TOPdesk person."""
    return topdesk_client.person.update(person_id, **updated_fields)

@mcp.tool()
def archive_person(person_id: str, reason_id: str = None) -> dict:
    """Archive a TOPdesk person."""
    return topdesk_client.person.archive(person_id, reason_id=reason_id)

@mcp.tool()
def unarchive_person(person_id: str) -> dict:
    """Unarchive a TOPdesk person."""
    return topdesk_client.person.unarchive(person_id)

def main():
    """Main function to run the MCP server."""
    mcp.run()

if __name__ == "__main__":
    main()