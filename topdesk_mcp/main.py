from fastmcp import FastMCP
from topdesk_mcp import _topdesk_sdk as topdesk_sdk
import os
import logging

# Set up logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    filename=os.getenv("LOG_FILE", None)
)

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
def topdesk_get_fiql_query_howto() -> str:
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
def topdesk_get_object_schemas() -> str:
    """Get the full object schemas for TOPdesk incidents and all their subfields."""
    try:
        with open(os.path.join(os.path.dirname(__file__), "resources", "object_schemas.yaml"), "r", encoding="utf-8") as file:
            return file.read()
    except Exception as e:
        return f"Error reading object schemas: {str(e)}"

#################
# INCIDENTS
#################
@mcp.tool()
def topdesk_get_incident(incident_id: str) -> dict:
    """Get a TOPdesk incident by UUID or by Incident Number (I-xxxxxx-xxx). Both formats are accepted.

    Parameters:
        incident_id: The UUID or incident number of the TOPdesk incident to retrieve.
    """
    return topdesk_client.incident.get(incident=incident_id)

@mcp.tool()
def topdesk_get_incidents_by_fiql_query(query: str) -> list:
    """Get TOPdesk incidents by FIQL query.

    Parameters:
        query: The FIQL query string to filter incidents.
    """
    return topdesk_client.incident.get_list(query=query)

@mcp.tool()
def topdesk_get_incident_user_requests(incident_id: str) -> list:
    """Get all user requests on a TOPdesk incident.

    Parameters:
        incident_id: The UUID or incident number of the TOPdesk incident whose requests to retrieve.
    """
    return topdesk_client.incident.request.get_list(incident=incident_id)

@mcp.tool()
def topdesk_create_incident(caller_id: str, incident_fields: dict) -> dict:
    """Create a new TOPdesk incident.

    Parameters:
        caller_id: The ID of the caller creating the incident.
        incident_fields: A dictionary of fields for the new incident.
    """
    return topdesk_client.incident.create(caller=caller_id, **incident_fields)

@mcp.tool()
def topdesk_archive_incident(incident_id: str) -> dict:
    """Archive a TOPdesk incident.

    Parameters:
        incident_id: The UUID or incident number of the TOPdesk incident to archive.
    """
    return topdesk_client.incident.archive(incident=incident_id)

@mcp.tool()
def topdesk_unarchive_incident(incident_id: str) -> dict:
    """Unarchive a TOPdesk incident.

    Parameters:
        incident_id: The UUID or incident number of the TOPdesk incident to unarchive.
    """
    return topdesk_client.incident.unarchive(incident=incident_id)

@mcp.tool()
def topdesk_get_timespent_on_incident(incident_id: str) -> list:
    """Get all time spent entries for a TOPdesk incident.

    Parameters:
        incident_id: The UUID or incident number of the TOPdesk incident.
    """
    return topdesk_client.incident.timespent.get(incident=incident_id)

@mcp.tool()
def topdesk_register_timespent_on_incident(incident_id: str, time_spent: int) -> dict:
    """Register time spent on a TOPdesk incident.

    Parameters:
        incident_id: The UUID or incident number of the TOPdesk incident.
        time_spent: Time spent in minutes.
    """
    return topdesk_client.incident.timespent.register(incident=incident_id, timespent=time_spent)

@mcp.tool()
def topdesk_escalate_incident(incident_id: str, reason_id: str) -> dict:
    """Escalate a TOPdesk incident.

    Parameters:
        incident_id: The UUID or incident number of the TOPdesk incident to escalate.
        reason_id: The ID of the escalation reason.
    """
    return topdesk_client.incident.escalate(incident=incident_id, reason=reason_id)

@mcp.tool()
def topdesk_get_available_escalation_reasons() -> list:
    """Get all available escalation reasons for a TOPdesk incident.

    (No parameters)
    """
    return topdesk_client.incident.escalation_reasons()

@mcp.tool()
def topdesk_get_available_deescalation_reasons() -> list:
    """Get all available de-escalation reasons for a TOPdesk incident.

    (No parameters)
    """
    return topdesk_client.incident.deescalation_reasons()

@mcp.tool()
def topdesk_deescalate_incident(incident_id: str, reason_id: str) -> dict:
    """De-escalate a TOPdesk incident.

    Parameters:
        incident_id: The UUID or incident number of the TOPdesk incident to de-escalate.
        reason_id: The ID of the de-escalation reason.
    """
    return topdesk_client.incident.deescalate(incident=incident_id, reason_id=reason_id)

@mcp.tool()
def topdesk_get_progress_trail(incident_id: str, include_all_attachments: bool = False) -> list:
    """Get the progress trail for a TOPdesk incident.

    Parameters:
        incident_id: The UUID or incident number of the TOPdesk incident.
        include_all_attachments: Whether to include base64-encoded attachments in the response.
    """
    return topdesk_client.incident.get_progress_trail(
        incident=incident_id, 
        non_api_attachments_url=include_all_attachments
    )

##################
# OPERATORS
##################
@mcp.tool()
def topdesk_get_operatorgroups_of_operator(operator_id: str) -> list:
    """Get a list of TOPdesk operator groups that an op is a member of, optionally by FIQL query or leave blank to return all groups.

    Parameters:
        operator_id: The ID of the TOPdesk operator whose groups to retrieve.
    """
    return topdesk_client.operator.get_operatorgroups(operator_id=operator_id)

@mcp.tool()
def topdesk_get_operator(operator_id: str) -> dict:
    """Get a TOPdesk operator by ID.

    Parameters:
        operator_id: The ID of the TOPdesk operator to retrieve.
    """
    return topdesk_client.operator.get(id=operator_id)

@mcp.tool()
def topdesk_get_operators_by_fiql_query(query: str) -> list:
    """Get TOPdesk operators by FIQL query.

    Parameters:
        query: The FIQL query string to filter operators.
    """
    return topdesk_client.operator.get_list(query=query)

##################
# ACTIONS
##################
@mcp.tool()
def topdesk_add_action_to_incident(incident_id: str, text: str) -> dict:
    """Add an action (ie, reply/comment) to a TOPdesk incident.

    Parameters:
        incident_id: The UUID or incident number of the TOPdesk incident.
        text: The content of the action to add.
    """
    return topdesk_client.incident.patch(incident=incident_id, action=text)

@mcp.tool()
def topdesk_get_incident_actions(incident_id: str, include_all_attachments: bool = False) -> list:
    """Get all actions (ie, replies/comments) for a TOPdesk incident.

    Parameters:
        incident_id: The UUID or incident number of the TOPdesk incident.
        include_all_attachments: Whether to include base64-encoded attachments in the response.
    """
    return topdesk_client.incident.action.get_list(
        incident=incident_id, 
        non_api_attachments_url=include_all_attachments
    )

@mcp.tool()
def topdesk_delete_incident_action(incident_id: str, action_id: str) -> dict:
    """Delete a specific action (ie, reply/comment) for a TOPdesk incident.

    Parameters:
        incident_id: The UUID or incident number of the TOPdesk incident.
        action_id: The ID of the action to delete.
    """
    return topdesk_client.incident.action.delete(incident=incident_id, actions_id=action_id)

################
# PERSONS
################
@mcp.tool()
def topdesk_get_person_by_query(query: str) -> list:
    """Get TOPdesk persons by FIQL query.

    Parameters:
        query: The FIQL query string to filter persons.
    """
    return topdesk_client.person.get_list(query=query)

@mcp.tool()
def topdesk_get_person(person_id: str) -> dict:
    """Get a TOPdesk person by ID.

    Parameters:
        person_id: The ID of the TOPdesk person to retrieve.
    """
    return topdesk_client.person.get(id=person_id)

@mcp.tool()
def topdesk_create_person(person: dict) -> dict:
    """Create a new TOPdesk person.

    Parameters:
        person: A dictionary of person fields to create.
    """
    return topdesk_client.person.create(**person)

@mcp.tool()
def topdesk_update_person(person_id: str, updated_fields: dict) -> dict:
    """Update an existing TOPdesk person.

    Parameters:
        person_id: The ID of the TOPdesk person to update.
        updated_fields: A dictionary of fields to update.
    """
    return topdesk_client.person.update(person=person_id, **updated_fields)

@mcp.tool()
def topdesk_archive_person(person_id: str, reason_id: str = None) -> dict:
    """Archive a TOPdesk person.

    Parameters:
        person_id: The ID of the TOPdesk person to archive.
        reason_id: Optional ID of the archive reason.
    """
    return topdesk_client.person.archive(person_id=person_id, reason_id=reason_id)

@mcp.tool()
def topdesk_unarchive_person(person_id: str) -> dict:
    """Unarchive a TOPdesk person.

    Parameters:
        person_id: The ID of the TOPdesk person to unarchive.
    """
    return topdesk_client.person.unarchive(person_id=person_id)

def main():
    """Main function to run the MCP server."""
    transport = os.environ.get("TOPDESK_MCP_TRANSPORT", "stdio")
    host = os.environ.get("TOPDESK_MCP_HOST", "0.0.0.0")
    port = int(os.environ.get("TOPDESK_MCP_PORT", 3030))
    
    if transport not in ["stdio", "streamable-http", "sse"]:
        raise ValueError("Invalid transport type. Choose 'stdio', 'streamable-http', or 'sse'.")
    
    if transport == "stdio":
        mcp.run()    
    else:
        mcp.run(transport=transport, host=host, port=port)

if __name__ == "__main__":
    main()