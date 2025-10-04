#!/usr/bin/env python3
"""
Base MCP Server Framework

Provides common functionality for all MCP server implementations including:
- JSON-RPC message handling
- Transport layer abstraction (stdio/WebSocket)
- Tool registration and execution
- Error handling and logging
- Health check endpoints
"""

import asyncio
import json
import logging
import os
import sys
import traceback
import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger(__name__)


class MCPError(Exception):
    """Base exception for MCP-related errors."""

    def __init__(self, code: str, message: str, data: Any = None):
        self.code = code
        self.message = message
        self.data = data
        super().__init__(message)


class Tool:
    """Represents an MCP tool with metadata and handler."""

    def __init__(
        self,
        name: str,
        description: str,
        input_schema: Dict[str, Any],
        handler: Callable
    ):
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.handler = handler


class MCPServer(ABC):
    """Base class for MCP server implementations."""

    def __init__(self, server_name: str, server_version: str = "1.0.0"):
        self.server_name = server_name
        self.server_version = server_version
        self.tools: Dict[str, Tool] = {}
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.running = False

        # Transport configuration
        self.transport_type = None  # "stdio" or "websocket"
        self.websocket_port = None

        logger.info(f"Initializing MCP server: {server_name} v{server_version}")

    def register_tool(self, tool: Tool):
        """Register a tool with the server."""
        self.tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")

    def get_tool(self, name: str) -> Optional[Tool]:
        """Get a registered tool by name."""
        return self.tools.get(name)

    def list_tools(self) -> List[Dict[str, Any]]:
        """List all registered tools."""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.input_schema
            }
            for tool in self.tools.values()
        ]

    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle an incoming JSON-RPC request."""
        try:
            # Validate request structure
            if not isinstance(request, dict):
                raise MCPError("INVALID_REQUEST", "Request must be a JSON object")

            method = request.get("method")
            if not method:
                raise MCPError("INVALID_REQUEST", "Request missing 'method' field")

            params = request.get("params", {})
            request_id = request.get("id")

            logger.info(f"Handling request: {method}")

            # Handle system methods
            if method == "initialize":
                return await self._handle_initialize(params, request_id)
            elif method == "tools/list":
                return await self._handle_tools_list(request_id)
            elif method == "tools/call":
                return await self._handle_tools_call(params, request_id)
            elif method == "ping":
                return await self._handle_ping(request_id)
            else:
                # Handle tool execution
                return await self._execute_tool(method, params, request_id)

        except MCPError as e:
            logger.error(f"MCP error in {request.get('method', 'unknown')}: {e.message}")
            return self._create_error_response(e.code, e.message, e.data, request.get("id"))
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            return self._create_error_response(
                "INTERNAL_ERROR",
                f"Internal server error: {str(e)}",
                None,
                request.get("id")
            )

    async def _handle_initialize(self, params: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """Handle server initialization."""
        client_name = params.get("clientName", "Unknown")
        client_version = params.get("clientVersion", "1.0.0")

        logger.info(f"Initializing connection from {client_name} v{client_version}")

        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "serverName": self.server_name,
                "serverVersion": self.server_version,
                "capabilities": {
                    "tools": True,
                    "sessions": True
                }
            }
        }

    async def _handle_tools_list(self, request_id: str) -> Dict[str, Any]:
        """Handle tools list request."""
        tools = self.list_tools()
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "tools": tools
            }
        }

    async def _handle_tools_call(self, params: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """Handle tool call request."""
        tool_name = params.get("name")
        if not tool_name:
            raise MCPError("INVALID_PARAMS", "Tool name is required")

        tool_params = params.get("arguments", {})

        return await self._execute_tool(tool_name, tool_params, request_id)

    async def _handle_ping(self, request_id: str) -> Dict[str, Any]:
        """Handle ping request."""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": "pong"
        }

    async def _execute_tool(self, tool_name: str, params: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """Execute a tool with the given parameters."""
        tool = self.get_tool(tool_name)
        if not tool:
            raise MCPError("TOOL_NOT_FOUND", f"Tool '{tool_name}' not found")

        try:
            logger.info(f"Executing tool: {tool_name}")
            result = await tool.handler(params)

            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result
            }

        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {str(e)}", exc_info=True)
            raise MCPError("TOOL_EXECUTION_ERROR", f"Error executing tool '{tool_name}': {str(e)}")

    def _create_error_response(self, code: str, message: str, data: Any, request_id: str) -> Dict[str, Any]:
        """Create a JSON-RPC error response."""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": code,
                "message": message,
                "data": data
            }
        }

    def create_session(self, session_id: str = None) -> str:
        """Create a new session."""
        if session_id is None:
            session_id = str(uuid.uuid4())

        self.sessions[session_id] = {
            "id": session_id,
            "created_at": datetime.utcnow().isoformat(),
            "data": {}
        }

        logger.info(f"Created session: {session_id}")
        return session_id

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data."""
        return self.sessions.get(session_id)

    def update_session(self, session_id: str, data: Dict[str, Any]):
        """Update session data."""
        if session_id in self.sessions:
            self.sessions[session_id]["data"].update(data)
            self.sessions[session_id]["updated_at"] = datetime.utcnow().isoformat()

    def destroy_session(self, session_id: str):
        """Destroy a session."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"Destroyed session: {session_id}")

    @abstractmethod
    async def setup_tools(self):
        """Setup server-specific tools. Must be implemented by subclasses."""
        pass

    async def start(self):
        """Start the MCP server."""
        logger.info(f"Starting MCP server: {self.server_name}")

        # Setup tools
        await self.setup_tools()

        # Start transport
        if self.transport_type == "stdio":
            await self._start_stdio_transport()
        elif self.transport_type == "websocket":
            await self._start_websocket_transport()
        else:
            raise MCPError("INVALID_CONFIG", "Transport type must be 'stdio' or 'websocket'")

    async def _start_stdio_transport(self):
        """Start stdio transport."""
        logger.info("Starting stdio transport")

        async def read_stdin():
            """Read messages from stdin."""
            try:
                while self.running:
                    line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
                    if not line:
                        break

                    try:
                        request = json.loads(line.strip())
                        response = await self.handle_request(request)

                        # Write response to stdout
                        response_json = json.dumps(response, ensure_ascii=False)
                        await asyncio.get_event_loop().run_in_executor(
                            None,
                            lambda: print(response_json, flush=True)
                        )

                    except json.JSONDecodeError:
                        logger.error("Invalid JSON received from stdin")
                    except Exception as e:
                        logger.error(f"Error processing stdin message: {e}")

            except Exception as e:
                logger.error(f"Error in stdin reader: {e}")

        self.running = True
        await read_stdin()

    async def _start_websocket_transport(self):
        """Start WebSocket transport."""
        try:
            import websockets
        except ImportError:
            raise MCPError("WEBSOCKET_DEPENDENCY", "websockets package is required for WebSocket transport")

        logger.info(f"Starting WebSocket transport on port {self.websocket_port}")

        async def handle_websocket(websocket, path):
            """Handle WebSocket connection."""
            logger.info("WebSocket client connected")

            try:
                async for message in websocket:
                    try:
                        request = json.loads(message)
                        response = await self.handle_request(request)

                        await websocket.send(json.dumps(response, ensure_ascii=False))

                    except json.JSONDecodeError:
                        logger.error("Invalid JSON received from WebSocket")
                    except Exception as e:
                        logger.error(f"Error processing WebSocket message: {e}")

            except websockets.exceptions.ConnectionClosed:
                logger.info("WebSocket connection closed")
            except Exception as e:
                logger.error(f"WebSocket error: {e}")

        self.running = True
        server = await websockets.serve(
            handle_websocket,
            "localhost",
            self.websocket_port
        )

        logger.info(f"WebSocket server started on ws://localhost:{self.websocket_port}")

        # Keep server running
        await server.wait_closed()

    def stop(self):
        """Stop the MCP server."""
        logger.info(f"Stopping MCP server: {self.server_name}")
        self.running = False
