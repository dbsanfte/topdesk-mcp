# topdesk-mcp

This project is a Model Context Protocol (MCP) server implemented in Python. It exposes the Topdesk API via the TOPdeskPy SDK.

## Project Purpose
- Acts as an MCP server to bridge MCP clients with the Topdesk API.
- Uses the [TOPdeskPy SDK](https://github.com/TwinkelToe/TOPdeskPy) (with some modifications) for all Topdesk API interactions.

## MCP Config JSON
```
{
  "servers": {
    "topdesk-mcp": {
      "type": "stdio",
      "command": "uvx",
      "args": [
        "--from", 
        "git+https://github.com/dbsanfte/topdesk-mcp@master",
        "topdesk_mcp"
      ],
      "env": {
         "TOPDESK_URL": "<your topdesk URL>",
         "TOPDESK_USERNAME": "<your topdesk username>",
         "TOPDESK_PASSWORD": "<your topdesk api key>"
      }
    }
  }
}
```

## Setup for Local Development
1. Ensure Python 3.11+ is installed.
2. Create and activate a virtual environment:

   **PowerShell:**
   ```powershell
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   ```

   **Bash:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Install dependencies:
   ```
   pip install uv
   uv pip install -r requirements.txt
   ```
   
4. Run:
   ```
   python -m topdesk_mcp.main
   ```
   
### Notes:
* The server skeleton was generated using the official MCP server template.
* Contributions are welcome.

## Package Structure
```
topdesk_mcp/  # Directory for the MCP server package
    __init__.py     # Marks as a Python package
    main.py         # Entry point for the MCP server
    
    _topdesk_sdk.py # TOPdeskPy SDK
    _incident.py    # Incidents API
    _operator.py    # Operator API
    _person.py      # Person API
    _utils.py       # Helper methods for Requests
```

## References
- [MCP Protocol Documentation](https://modelcontextprotocol.io/llms-full.txt)
- [TOPdeskPy SDK](https://github.com/TwinkelToe/TOPdeskPy)
- [FastMCP](https://github.com/jlowin/fastmcp)

## License
MIT license.
