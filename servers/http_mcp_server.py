#!/usr/bin/env python3
"""
HTTP-MCP Wrapper Server

Provides secure wrapper for calling local HTTP endpoints.
Implements WebSocket transport for real-time updates.
"""

import asyncio
import json
import logging
import os
import re
import sys
import time
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse

try:
    import httpx
except ImportError:
    httpx = None

try:
    from .base_mcp_server import MCPServer, MCPError, Tool
except ImportError:
    # For standalone execution
    from base_mcp_server import MCPServer, MCPError, Tool


class HTTPMCPWrapperServer(MCPServer):
    """HTTP-MCP Wrapper Server implementation."""

    def __init__(
        self,
        whitelist_patterns: List[str] = None,
        timeout: int = 30,
        max_response_size: int = 1024 * 1024,  # 1MB
        allow_insecure: bool = False,
        user_agent: str = "MCP-HTTP-Wrapper/1.0",
        max_concurrent_requests: int = 10
    ):
        super().__init__("http-mcp", "1.0.0")

        if httpx is None:
            raise MCPError("HTTPX_DEPENDENCY", "httpx package is required for HTTP wrapper server")

        # Default whitelist for local services only
        self.whitelist_patterns = whitelist_patterns or [
            r"^https?://127\.0\.0\.1:\d+/?$",
            r"^https?://localhost:\d+/?$",
            r"^https?://127\.0\.0\.1:\d+/.*$",
            r"^https?://localhost:\d+/.*$",
            r"^https?://0\.0\.0\.0:\d+/?$",
            r"^https?://0\.0\.0\.0:\d+/.*$"
        ]

        self.timeout = timeout
        self.max_response_size = max_response_size
        self.allow_insecure = allow_insecure
        self.user_agent = user_agent
        self.max_concurrent_requests = max_concurrent_requests

        # Compile regex patterns
        self.compiled_patterns = []
        for pattern in self.whitelist_patterns:
            try:
                self.compiled_patterns.append(re.compile(pattern))
            except re.error as e:
                raise MCPError("INVALID_WHITELIST_PATTERN", f"Invalid regex pattern '{pattern}': {str(e)}")

        # Request semaphore for concurrency control
        self.request_semaphore = asyncio.Semaphore(max_concurrent_requests)

        logging.info(f"HTTP wrapper server configured with {len(self.whitelist_patterns)} whitelist patterns")

    def validate_endpoint(self, url: str) -> bool:
        """Validate endpoint against whitelist patterns."""
        if not url:
            return False

        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return False

            # Only allow http and https
            if parsed.scheme not in ['http', 'https']:
                return False

            # Check against whitelist patterns
            for pattern in self.compiled_patterns:
                if pattern.match(url):
                    return True

            return False

        except Exception as e:
            logging.error(f"Error validating endpoint '{url}': {str(e)}")
            return False

    def create_http_client(self) -> httpx.AsyncClient:
        """Create HTTP client with appropriate configuration."""
        # Configure SSL context
        import ssl

        ssl_context = None
        if not self.allow_insecure:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = True
            ssl_context.verify_mode = ssl.CERT_REQUIRED

        # Configure limits
        limits = httpx.Limits(
            max_keepalive_connections=20,
            max_connections=100,
            keepalive_expiry=30.0
        )

        # Create client with timeout
        return httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            limits=limits,
            headers={"User-Agent": self.user_agent},
            follow_redirects=True,
            verify=ssl_context
        )

    async def setup_tools(self):
        """Setup HTTP wrapper tools."""
        # Basic HTTP GET
        self.register_tool(Tool(
            "http_get",
            "Perform HTTP GET request to whitelisted endpoint",
            {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL to fetch (must be whitelisted)"
                    },
                    "headers": {
                        "type": "object",
                        "description": "Additional HTTP headers",
                        "additionalProperties": {"type": "string"}
                    },
                    "params": {
                        "type": "object",
                        "description": "Query parameters",
                        "additionalProperties": {"type": "string"}
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Request timeout in seconds",
                        "minimum": 1,
                        "maximum": 300,
                        "default": 30
                    }
                },
                "required": ["url"]
            },
            self.http_get
        ))

        # HTTP POST
        self.register_tool(Tool(
            "http_post",
            "Perform HTTP POST request to whitelisted endpoint",
            {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL to post to (must be whitelisted)"
                    },
                    "data": {
                        "type": "string",
                        "description": "Data to send in request body"
                    },
                    "json": {
                        "type": "object",
                        "description": "JSON data to send (alternative to data)"
                    },
                    "headers": {
                        "type": "object",
                        "description": "Additional HTTP headers",
                        "additionalProperties": {"type": "string"}
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Request timeout in seconds",
                        "minimum": 1,
                        "maximum": 300,
                        "default": 30
                    }
                },
                "required": ["url"]
            },
            self.http_post
        ))

        # HTTP PUT
        self.register_tool(Tool(
            "http_put",
            "Perform HTTP PUT request to whitelisted endpoint",
            {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL to put to (must be whitelisted)"
                    },
                    "data": {
                        "type": "string",
                        "description": "Data to send in request body"
                    },
                    "json": {
                        "type": "object",
                        "description": "JSON data to send (alternative to data)"
                    },
                    "headers": {
                        "type": "object",
                        "description": "Additional HTTP headers",
                        "additionalProperties": {"type": "string"}
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Request timeout in seconds",
                        "minimum": 1,
                        "maximum": 300,
                        "default": 30
                    }
                },
                "required": ["url"]
            },
            self.http_put
        ))

        # HTTP DELETE
        self.register_tool(Tool(
            "http_delete",
            "Perform HTTP DELETE request to whitelisted endpoint",
            {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL to delete from (must be whitelisted)"
                    },
                    "headers": {
                        "type": "object",
                        "description": "Additional HTTP headers",
                        "additionalProperties": {"type": "string"}
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Request timeout in seconds",
                        "minimum": 1,
                        "maximum": 300,
                        "default": 30
                    }
                },
                "required": ["url"]
            },
            self.http_delete
        ))

        # Endpoint health check
        self.register_tool(Tool(
            "endpoint_health",
            "Check if an endpoint is healthy",
            {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL to health check (must be whitelisted)"
                    },
                    "expected_status": {
                        "type": "integer",
                        "description": "Expected HTTP status code (default: 200)",
                        "minimum": 100,
                        "maximum": 599,
                        "default": 200
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Request timeout in seconds",
                        "minimum": 1,
                        "maximum": 60,
                        "default": 10
                    }
                },
                "required": ["url"]
            },
            self.endpoint_health
        ))

        # URL validation tool
        self.register_tool(Tool(
            "validate_endpoint",
            "Check if an endpoint is allowed by whitelist",
            {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL to validate"
                    }
                },
                "required": ["url"]
            },
            self.validate_endpoint
        ))

    async def http_get(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Perform HTTP GET request."""
        async with self.request_semaphore:
            return await self._make_request("GET", params)

    async def http_post(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Perform HTTP POST request."""
        async with self.request_semaphore:
            return await self._make_request("POST", params)

    async def http_put(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Perform HTTP PUT request."""
        async with self.request_semaphore:
            return await self._make_request("PUT", params)

    async def http_delete(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Perform HTTP DELETE request."""
        async with self.request_semaphore:
            return await self._make_request("DELETE", params)

    async def _make_request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make HTTP request with common logic."""
        url = params["url"]
        headers = params.get("headers", {})
        timeout = params.get("timeout", self.timeout)

        # Extract data based on method
        data = None
        if method in ["POST", "PUT"]:
            data = params.get("data")
            json_data = params.get("json")

            if data is None and json_data is None:
                raise MCPError("INVALID_PARAMS", f"Method {method} requires 'data' or 'json' parameter")

            # Set content type if not provided
            if json_data and "Content-Type" not in headers:
                headers["Content-Type"] = "application/json"

        # Validate endpoint
        if not self.validate_endpoint(url):
            raise MCPError(
                "ENDPOINT_NOT_ALLOWED",
                f"Endpoint not allowed by whitelist: {url}",
                {"url": url, "whitelist_patterns": self.whitelist_patterns}
            )

        try:
            async with self.create_http_client() as client:
                # Override timeout if specified
                client.timeout = httpx.Timeout(timeout)

                # Make request based on method
                if method == "GET":
                    response = await client.get(url, headers=headers, params=params.get("params", {}))
                elif method == "POST":
                    response = await client.post(url, content=data, json=params.get("json"), headers=headers)
                elif method == "PUT":
                    response = await client.put(url, content=data, json=params.get("json"), headers=headers)
                elif method == "DELETE":
                    response = await client.delete(url, headers=headers)
                else:
                    raise MCPError("INVALID_METHOD", f"Unsupported HTTP method: {method}")

                # Check response size
                content_length = len(response.content)
                if content_length > self.max_response_size:
                    raise MCPError(
                        "RESPONSE_TOO_LARGE",
                        f"Response too large ({content_length} bytes > {self.max_response_size} bytes)",
                        {"content_length": content_length, "max_size": self.max_response_size}
                    )

                return {
                    "method": method,
                    "url": url,
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "content": response.text,
                    "content_length": content_length,
                    "request_time": time.time()
                }

        except httpx.TimeoutException:
            raise MCPError("REQUEST_TIMEOUT", f"Request timed out after {timeout} seconds")
        except httpx.ConnectError as e:
            raise MCPError("CONNECTION_ERROR", f"Failed to connect to {url}: {str(e)}")
        except httpx.HTTPStatusError as e:
            raise MCPError(
                "HTTP_ERROR",
                f"HTTP error {e.response.status_code} for {url}",
                {"status_code": e.response.status_code, "response": e.response.text[:500]}
            )
        except Exception as e:
            raise MCPError("REQUEST_ERROR", f"Request failed: {str(e)}")

    async def endpoint_health(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Check if an endpoint is healthy."""
        url = params["url"]
        expected_status = params.get("expected_status", 200)
        timeout = params.get("timeout", 10)

        # Validate endpoint
        if not self.validate_endpoint(url):
            raise MCPError(
                "ENDPOINT_NOT_ALLOWED",
                f"Endpoint not allowed by whitelist: {url}",
                {"url": url, "whitelist_patterns": self.whitelist_patterns}
            )

        try:
            async with self.create_http_client() as client:
                # Override timeout for health checks
                client.timeout = httpx.Timeout(timeout)

                start_time = time.time()
                response = await client.get(url)
                response_time = time.time() - start_time

                is_healthy = response.status_code == expected_status

                # Check response size for health checks
                content_length = len(response.content)
                if content_length > self.max_response_size:
                    raise MCPError(
                        "RESPONSE_TOO_LARGE",
                        f"Health check response too large ({content_length} bytes > {self.max_response_size} bytes)",
                        {"content_length": content_length, "max_size": self.max_response_size}
                    )

                return {
                    "url": url,
                    "healthy": is_healthy,
                    "status_code": response.status_code,
                    "expected_status": expected_status,
                    "response_time": response_time,
                    "content": response.text if is_healthy else None,
                    "check_time": time.time()
                }

        except httpx.TimeoutException:
            return {
                "url": url,
                "healthy": False,
                "status_code": None,
                "expected_status": expected_status,
                "response_time": None,
                "error": "timeout",
                "check_time": time.time()
            }
        except httpx.ConnectError as e:
            return {
                "url": url,
                "healthy": False,
                "status_code": None,
                "expected_status": expected_status,
                "response_time": None,
                "error": f"connection_error: {str(e)}",
                "check_time": time.time()
            }
        except MCPError:
            raise
        except Exception as e:
            return {
                "url": url,
                "healthy": False,
                "status_code": None,
                "expected_status": expected_status,
                "response_time": None,
                "error": str(e),
                "check_time": time.time()
            }


async def main():
    """Main server entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="HTTP-MCP Wrapper Server")
    parser.add_argument(
        "--whitelist",
        nargs="*",
        default=["127.0.0.1", "localhost", "0.0.0.0"],
        help="URL patterns to allow (default: localhost, 127.0.0.1, 0.0.0.0)"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Request timeout in seconds (default: 30)"
    )
    parser.add_argument(
        "--max-response-size",
        type=int,
        default=1024*1024,
        help="Maximum response size in bytes (default: 1MB)"
    )
    parser.add_argument(
        "--max-concurrent-requests",
        type=int,
        default=10,
        help="Maximum concurrent requests (default: 10)"
    )
    parser.add_argument(
        "--allow-insecure",
        action="store_true",
        help="Allow insecure SSL connections"
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "websocket"],
        default="stdio",
        help="Transport mechanism (default: stdio)"
    )
    parser.add_argument(
        "--port",
        type=int,
        help="Port for WebSocket transport"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Log level"
    )

    args = parser.parse_args()

    # Convert whitelist patterns to regex patterns
    whitelist_patterns = []
    for pattern in args.whitelist:
        if pattern.startswith("http"):
            # Full URL pattern
            whitelist_patterns.append(pattern)
        else:
            # Host pattern - convert to URL patterns
            whitelist_patterns.append(f"https?://{re.escape(pattern)}:\\d+/?")
            whitelist_patterns.append(f"https?://{re.escape(pattern)}:\\d+/.*")

    # Configure logging
    logging.getLogger().setLevel(getattr(logging, args.log_level))

    try:
        # Create server instance
        server = HTTPMCPWrapperServer(
            whitelist_patterns=whitelist_patterns,
            timeout=args.timeout,
            max_response_size=args.max_response_size,
            allow_insecure=args.allow_insecure,
            max_concurrent_requests=args.max_concurrent_requests
        )

        # Configure transport
        if args.transport == "websocket":
            if not args.port:
                parser.error("--port is required for WebSocket transport")
            server.transport_type = "websocket"
            server.websocket_port = args.port
        else:
            server.transport_type = "stdio"

        # Start server
        await server.start()

    except KeyboardInterrupt:
        logging.info("Server interrupted by user")
    except Exception as e:
        logging.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
