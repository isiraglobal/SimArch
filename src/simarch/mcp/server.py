"""SimArch Model Context Protocol (MCP) Stdio Server.

Exposes SimArch autonomous organizations, persistent task execution,
decision intelligence, world simulation, and localhost control as an
extension to any MCP-compatible AI tool (Claude Code, Cursor, Antigravity, etc.).
"""

import asyncio
import json
import sys
from typing import Any, Dict, List, Optional
from simarch import __version__
from simarch.extension.toolkit import SimArchAIExtension


class MCPServer:
    """Stdio JSON-RPC 2.0 server implementing Model Context Protocol."""

    def __init__(self) -> None:
        self.extension = SimArchAIExtension()

    async def handle_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Dispatch JSON-RPC request to appropriate MCP handler."""
        req_id = request.get("id")
        method = request.get("method")
        params = request.get("params", {})

        if not method:
            return None

        # 1. Initialize
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {
                        "name": "simarch-ai-extension",
                        "version": __version__
                    },
                    "capabilities": {
                        "tools": {"listChanged": False},
                        "resources": {"subscribe": False, "listChanged": False}
                    }
                }
            }

        # 2. Initialized Notification
        elif method in ["notifications/initialized", "initialized"]:
            return None  # No response needed for notifications

        # 3. Ping
        elif method == "ping":
            return {"jsonrpc": "2.0", "id": req_id, "result": {}}

        # 4. Tools List
        elif method == "tools/list":
            tools = []
            for t in self.extension.get_tool_definitions():
                tools.append({
                    "name": t["name"],
                    "description": t["description"],
                    "inputSchema": t["parameters"]
                })
            return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": tools}}

        # 5. Tools Call
        elif method == "tools/call":
            tool_name = params.get("name", "")
            arguments = params.get("arguments", {})
            result = self.extension.execute_tool(tool_name, arguments)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, indent=2)
                        }
                    ],
                    "isError": "error" in result
                }
            }

        # 6. Resources List
        elif method == "resources/list":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "resources": [
                        {
                            "uri": "simarch://organizations",
                            "name": "SimArch Organizations",
                            "description": "Active organizations and corporate hierarchies",
                            "mimeType": "application/json"
                        },
                        {
                            "uri": "simarch://projects",
                            "name": "SimArch Projects",
                            "description": "Strategic projects, tasks, and deliverables",
                            "mimeType": "application/json"
                        },
                        {
                            "uri": "simarch://decisions",
                            "name": "SimArch Decision Intelligence",
                            "description": "Evaluated decisions and trade-offs",
                            "mimeType": "application/json"
                        },
                        {
                            "uri": "simarch://localhost-status",
                            "name": "SimArch Localhost Status",
                            "description": "Lock status of the localhost web dashboard",
                            "mimeType": "application/json"
                        }
                    ]
                }
            }

        # 7. Resources Read
        elif method == "resources/read":
            uri = params.get("uri", "")
            content_text = ""
            if uri == "simarch://organizations":
                orgs = self.extension.db.fetch_all("SELECT * FROM organizations")
                content_text = json.dumps(orgs, indent=2)
            elif uri == "simarch://projects":
                projs = self.extension.db.fetch_all("SELECT * FROM projects")
                content_text = json.dumps(projs, indent=2)
            elif uri == "simarch://decisions":
                decs = self.extension.db.fetch_all("SELECT * FROM decisions")
                content_text = json.dumps(decs, indent=2)
            elif uri == "simarch://localhost-status":
                status = self.extension.get_localhost_status()
                content_text = json.dumps(status, indent=2)
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32602, "message": f"Resource not found: {uri}"}
                }

            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "contents": [
                        {
                            "uri": uri,
                            "mimeType": "application/json",
                            "text": content_text
                        }
                    ]
                }
            }

        # Unknown method
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Method '{method}' not implemented"}
        }

    async def run_stdio(self) -> None:
        """Run standard I/O communication loop."""
        loop = asyncio.get_event_loop()
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await loop.connect_read_pipe(lambda: protocol, sys.stdin)

        while True:
            line = await reader.readline()
            if not line:
                break

            line_str = line.decode("utf-8").strip()
            if not line_str:
                continue

            try:
                request = json.loads(line_str)
                response = await self.handle_request(request)
                if response:
                    sys.stdout.write(json.dumps(response) + "\n")
                    sys.stdout.flush()
            except Exception as e:
                err_resp = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": f"Parse error: {str(e)}"}
                }
                sys.stdout.write(json.dumps(err_resp) + "\n")
                sys.stdout.flush()


def main() -> None:
    """MCP server CLI entrypoint."""
    server = MCPServer()
    asyncio.run(server.run_stdio())


if __name__ == "__main__":
    main()
