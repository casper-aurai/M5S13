#!/usr/bin/env python3
"""
Podman MCP Server

Provides container orchestration via Podman API.
Implements WebSocket transport for real-time updates.
"""

import asyncio
import json
import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse

try:
    import podman
    from podman.domain.containers import Container
    from podman.domain.images import Image
except ImportError:
    podman = None

try:
    from .base_mcp_server import MCPServer, MCPError, Tool
except ImportError:
    # For standalone execution
    from base_mcp_server import MCPServer, MCPError, Tool


class PodmanMCPServer(MCPServer):
    """Podman MCP Server implementation."""

    def __init__(
        self,
        socket_path: Optional[str] = None,
        base_url: str = "unix:///run/user/$(id -u)/podman/podman.sock",
        timeout: int = 30,
        max_containers: int = 100
    ):
        super().__init__("podman", "1.0.0")

        if podman is None:
            raise MCPError("PODMAN_DEPENDENCY", "podman-py package is required for Podman server")

        # Determine socket path
        if socket_path:
            self.socket_path = socket_path
        else:
            # Default to user-specific socket
            user_id = os.getuid()
            self.socket_path = f"/run/user/{user_id}/podman/podman.sock"

        self.base_url = base_url
        self.timeout = timeout
        self.max_containers = max_containers

        self.client = None

        logging.info(f"Podman server configured for socket: {self.socket_path}")

    async def connect(self):
        """Establish Podman connection."""
        try:
            # Create Podman client
            self.client = podman.PodmanClient(base_url=self.base_url)

            # Test connection by getting system info
            system_info = self.client.system.info
            logging.info(f"Podman connection established: {system_info['OSType']} {system_info['ServerVersion']}")

        except Exception as e:
            raise MCPError("PODMAN_CONNECTION_FAILED", f"Failed to connect to Podman: {str(e)}")

    async def disconnect(self):
        """Close Podman connection."""
        if self.client:
            self.client.close()
            logging.info("Podman connection closed")

    def validate_container_name(self, name: str) -> bool:
        """Validate container name format."""
        if not name or not isinstance(name, str):
            return False

        # Container names must match [a-zA-Z0-9][a-zA-Z0-9_.-]*
        pattern = r'^[a-zA-Z0-9][a-zA-Z0-9_.-]*$'
        return bool(re.match(pattern, name)) and len(name) <= 255

    def format_container_info(self, container: Container) -> Dict[str, Any]:
        """Format container information for response."""
        try:
            # Get container stats
            stats = container.stats(stream=False) if container.status == 'running' else None

            return {
                "id": container.id[:12],  # Short ID
                "name": container.name,
                "image": container.image.tags[0] if container.image.tags else container.image.id[:12],
                "status": container.status,
                "state": {
                    "running": container.status == "running",
                    "paused": container.status == "paused",
                    "exited": container.status == "exited",
                    "created": container.status == "created"
                },
                "ports": [
                    {
                        "ip": port.get("IP", ""),
                        "private_port": port.get("PrivatePort", 0),
                        "public_port": port.get("PublicPort", 0),
                        "type": port.get("Type", "tcp")
                    }
                    for port in container.ports or []
                ],
                "created": container.attrs.get("Created", ""),
                "command": container.attrs.get("Config", {}).get("Cmd", []),
                "labels": container.labels or {},
                "networks": list(container.attrs.get("NetworkSettings", {}).get("Networks", {}).keys()),
                "mounts": [
                    {
                        "type": mount.get("Type", ""),
                        "source": mount.get("Source", ""),
                        "destination": mount.get("Destination", ""),
                        "mode": mount.get("Mode", "")
                    }
                    for mount in container.attrs.get("Mounts", [])
                ],
                "resources": {
                    "cpu_shares": stats.get("cpu_stats", {}).get("cpu_usage", {}).get("total_usage", 0) if stats else 0,
                    "memory_usage": stats.get("memory_stats", {}).get("usage", 0) if stats else 0,
                    "memory_limit": stats.get("memory_stats", {}).get("limit", 0) if stats else 0
                } if stats else {}
            }
        except Exception as e:
            logging.error(f"Error formatting container info: {e}")
            return {
                "id": container.id[:12],
                "name": container.name,
                "status": container.status,
                "error": str(e)
            }

    def format_image_info(self, image: Image) -> Dict[str, Any]:
        """Format image information for response."""
        return {
            "id": image.id[:12],
            "tags": image.tags or [],
            "created": image.attrs.get("Created", ""),
            "size": image.attrs.get("Size", 0),
            "labels": image.labels or {},
            "architecture": image.attrs.get("Architecture", ""),
            "os": image.attrs.get("Os", "")
        }

    async def setup_tools(self):
        """Setup Podman tools."""
        # Container management
        self.register_tool(Tool(
            "podman_ps",
            "List containers",
            {
                "type": "object",
                "properties": {
                    "all": {
                        "type": "boolean",
                        "description": "Show all containers (default: false)",
                        "default": False
                    },
                    "filters": {
                        "type": "object",
                        "description": "Filter containers",
                        "properties": {
                            "status": {
                                "type": "string",
                                "description": "Filter by status (running, exited, etc.)"
                            },
                            "name": {
                                "type": "string",
                                "description": "Filter by name"
                            },
                            "label": {
                                "type": "string",
                                "description": "Filter by label"
                            }
                        }
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of containers to return",
                        "minimum": 1,
                        "maximum": self.max_containers,
                        "default": 50
                    }
                }
            },
            self.podman_ps
        ))

        self.register_tool(Tool(
            "podman_run",
            "Create and run a new container",
            {
                "type": "object",
                "properties": {
                    "image": {
                        "type": "string",
                        "description": "Image to run"
                    },
                    "name": {
                        "type": "string",
                        "description": "Container name"
                    },
                    "command": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Command to run"
                    },
                    "env": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Environment variables (KEY=VALUE format)"
                    },
                    "ports": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Port mappings (HOST:CONTAINER format)"
                    },
                    "volumes": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Volume mounts (HOST:CONTAINER format)"
                    },
                    "detach": {
                        "type": "boolean",
                        "description": "Run in background (default: true)",
                        "default": True
                    },
                    "restart": {
                        "type": "string",
                        "description": "Restart policy",
                        "enum": ["no", "always", "on-failure", "unless-stopped"]
                    }
                },
                "required": ["image"]
            },
            self.podman_run
        ))

        self.register_tool(Tool(
            "podman_stop",
            "Stop one or more containers",
            {
                "type": "object",
                "properties": {
                    "containers": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Container names or IDs to stop"
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds (default: 10)",
                        "minimum": 1,
                        "default": 10
                    }
                },
                "required": ["containers"]
            },
            self.podman_stop
        ))

        self.register_tool(Tool(
            "podman_start",
            "Start one or more containers",
            {
                "type": "object",
                "properties": {
                    "containers": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Container names or IDs to start"
                    }
                },
                "required": ["containers"]
            },
            self.podman_start
        ))

        self.register_tool(Tool(
            "podman_logs",
            "Get logs from a container",
            {
                "type": "object",
                "properties": {
                    "container": {
                        "type": "string",
                        "description": "Container name or ID"
                    },
                    "tail": {
                        "type": "integer",
                        "description": "Number of lines to show (default: all)",
                        "minimum": 1,
                        "default": 100
                    },
                    "since": {
                        "type": "string",
                        "description": "Show logs since timestamp"
                    },
                    "follow": {
                        "type": "boolean",
                        "description": "Follow log output (default: false)",
                        "default": False
                    },
                    "timestamps": {
                        "type": "boolean",
                        "description": "Show timestamps (default: false)",
                        "default": False
                    }
                },
                "required": ["container"]
            },
            self.podman_logs
        ))

        self.register_tool(Tool(
            "podman_inspect",
            "Get detailed information about a container",
            {
                "type": "object",
                "properties": {
                    "container": {
                        "type": "string",
                        "description": "Container name or ID"
                    }
                },
                "required": ["container"]
            },
            self.podman_inspect
        ))

        # Image management
        self.register_tool(Tool(
            "podman_images",
            "List images",
            {
                "type": "object",
                "properties": {
                    "all": {
                        "type": "boolean",
                        "description": "Show all images (default: false)",
                        "default": False
                    },
                    "filters": {
                        "type": "object",
                        "description": "Filter images",
                        "properties": {
                            "reference": {
                                "type": "string",
                                "description": "Filter by image reference"
                            },
                            "label": {
                                "type": "string",
                                "description": "Filter by label"
                            }
                        }
                    }
                }
            },
            self.podman_images
        ))

        self.register_tool(Tool(
            "podman_pull",
            "Pull an image from a registry",
            {
                "type": "object",
                "properties": {
                    "image": {
                        "type": "string",
                        "description": "Image to pull (name:tag format)"
                    }
                },
                "required": ["image"]
            },
            self.podman_pull
        ))

        # Compose operations
        self.register_tool(Tool(
            "podman_compose_up",
            "Start services from compose file",
            {
                "type": "object",
                "properties": {
                    "file": {
                        "type": "string",
                        "description": "Compose file path (default: docker-compose.yml)"
                    },
                    "project_name": {
                        "type": "string",
                        "description": "Project name"
                    },
                    "detach": {
                        "type": "boolean",
                        "description": "Run in background (default: true)",
                        "default": True
                    }
                }
            },
            self.podman_compose_up
        ))

        self.register_tool(Tool(
            "podman_compose_down",
            "Stop services from compose file",
            {
                "type": "object",
                "properties": {
                    "file": {
                        "type": "string",
                        "description": "Compose file path (default: docker-compose.yml)"
                    },
                    "project_name": {
                        "type": "string",
                        "description": "Project name"
                    },
                    "volumes": {
                        "type": "boolean",
                        "description": "Remove volumes (default: false)",
                        "default": False
                    }
                }
            },
            self.podman_compose_down
        ))

    async def start(self):
        """Start the Podman MCP server."""
        # Establish Podman connection first
        await self.connect()

        try:
            # Call parent start method
            await super().start()
        except Exception:
            # Ensure Podman connection is closed on error
            await self.disconnect()
            raise

    def stop(self):
        """Stop the Podman MCP server."""
        # Close Podman connection
        if self.client:
            asyncio.create_task(self.disconnect())

        # Call parent stop method
        super().stop()

    async def podman_ps(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List containers."""
        all_containers = params.get("all", False)
        filters = params.get("filters", {})
        limit = params.get("limit", 50)

        if not self.client:
            raise MCPError("PODMAN_NOT_CONNECTED", "Podman client not connected")

        try:
            containers = self.client.containers.list(all=all_containers, limit=limit)

            # Apply filters if provided
            if filters:
                filtered_containers = []
                for container in containers:
                    match = True

                    if "status" in filters and container.status != filters["status"]:
                        match = False
                    if "name" in filters and not filters["name"] in container.name:
                        match = False
                    if "label" in filters:
                        # Simple label filter - check if label exists
                        container_labels = container.labels or {}
                        if not any(filters["label"] in label for label in container_labels.keys()):
                            match = False

                    if match:
                        filtered_containers.append(container)

                containers = filtered_containers[:limit]  # Apply limit after filtering

            # Format container information
            container_list = [self.format_container_info(c) for c in containers]

            return {
                "containers": container_list,
                "count": len(container_list),
                "all": all_containers,
                "filters": filters
            }

        except Exception as e:
            raise MCPError("PODMAN_ERROR", f"Failed to list containers: {str(e)}")

    async def podman_run(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create and run a new container."""
        image = params["image"]
        name = params.get("name")
        command = params.get("command", [])
        env = params.get("env", [])
        ports = params.get("ports", [])
        volumes = params.get("volumes", [])
        detach = params.get("detach", True)
        restart = params.get("restart")

        if not self.client:
            raise MCPError("PODMAN_NOT_CONNECTED", "Podman client not connected")

        try:
            # Validate container name if provided
            if name and not self.validate_container_name(name):
                raise MCPError("INVALID_CONTAINER_NAME", f"Invalid container name: {name}")

            # Prepare container configuration
            container_config = {
                "image": image,
                "command": command,
                "environment": {env_var.split('=', 1)[0]: env_var.split('=', 1)[1] for env_var in env if '=' in env_var},
                "ports": ports,
                "volumes": volumes,
                "detach": detach,
                "name": name
            }

            if restart:
                container_config["restart_policy"] = {"Name": restart}

            # Create and start container
            container = self.client.containers.create(**container_config)
            container.start()

            return {
                "created": True,
                "container": self.format_container_info(container),
                "name": name or container.name,
                "id": container.id[:12]
            }

        except Exception as e:
            raise MCPError("PODMAN_ERROR", f"Failed to run container: {str(e)}")

    async def podman_stop(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Stop containers."""
        containers = params["containers"]
        timeout = params.get("timeout", 10)

        if not self.client:
            raise MCPError("PODMAN_NOT_CONNECTED", "Podman client not connected")

        try:
            stopped_containers = []

            for container_name in containers:
                try:
                    container = self.client.containers.get(container_name)
                    container.stop(timeout=timeout)
                    stopped_containers.append({
                        "name": container_name,
                        "stopped": True,
                        "status": container.status
                    })
                except Exception as e:
                    stopped_containers.append({
                        "name": container_name,
                        "stopped": False,
                        "error": str(e)
                    })

            return {
                "containers": stopped_containers,
                "stopped_count": sum(1 for c in stopped_containers if c["stopped"])
            }

        except Exception as e:
            raise MCPError("PODMAN_ERROR", f"Failed to stop containers: {str(e)}")

    async def podman_start(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Start containers."""
        containers = params["containers"]

        if not self.client:
            raise MCPError("PODMAN_NOT_CONNECTED", "Podman client not connected")

        try:
            started_containers = []

            for container_name in containers:
                try:
                    container = self.client.containers.get(container_name)
                    container.start()
                    started_containers.append({
                        "name": container_name,
                        "started": True,
                        "status": container.status
                    })
                except Exception as e:
                    started_containers.append({
                        "name": container_name,
                        "started": False,
                        "error": str(e)
                    })

            return {
                "containers": started_containers,
                "started_count": sum(1 for c in started_containers if c["started"])
            }

        except Exception as e:
            raise MCPError("PODMAN_ERROR", f"Failed to start containers: {str(e)}")

    async def podman_logs(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get container logs."""
        container_name = params["container"]
        tail = params.get("tail", 100)
        since = params.get("since")
        follow = params.get("follow", False)
        timestamps = params.get("timestamps", False)

        if not self.client:
            raise MCPError("PODMAN_NOT_CONNECTED", "Podman client not connected")

        try:
            container = self.client.containers.get(container_name)

            # Get logs
            logs = container.logs(
                tail=tail,
                since=since,
                timestamps=timestamps,
                stream=follow
            )

            # Handle streaming vs non-streaming
            if follow:
                # For streaming, we'd need WebSocket support
                # For now, just get recent logs and note streaming not supported
                logs_text = str(logs) if hasattr(logs, '__str__') else "Streaming not supported in this implementation"
            else:
                logs_text = logs.decode('utf-8', errors='replace') if isinstance(logs, bytes) else str(logs)

            return {
                "container": container_name,
                "logs": logs_text,
                "tail": tail,
                "timestamps": timestamps,
                "follow": follow,
                "since": since
            }

        except Exception as e:
            raise MCPError("PODMAN_ERROR", f"Failed to get logs for container '{container_name}': {str(e)}")

    async def podman_inspect(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed container information."""
        container_name = params["container"]

        if not self.client:
            raise MCPError("PODMAN_NOT_CONNECTED", "Podman client not connected")

        try:
            container = self.client.containers.get(container_name)

            # Get full container configuration
            inspection = container.inspect()

            return {
                "container": container_name,
                "inspection": inspection,
                "formatted": self.format_container_info(container)
            }

        except Exception as e:
            raise MCPError("PODMAN_ERROR", f"Failed to inspect container '{container_name}': {str(e)}")

    async def podman_images(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List images."""
        all_images = params.get("all", False)
        filters = params.get("filters", {})

        if not self.client:
            raise MCPError("PODMAN_NOT_CONNECTED", "Podman client not connected")

        try:
            images = self.client.images.list(all=all_images)

            # Apply filters if provided
            if filters:
                filtered_images = []
                for image in images:
                    match = True

                    if "reference" in filters:
                        image_refs = image.tags or [image.id[:12]]
                        if not any(filters["reference"] in ref for ref in image_refs):
                            match = False

                    if "label" in filters:
                        image_labels = image.labels or {}
                        if not any(filters["label"] in label for label in image_labels.keys()):
                            match = False

                    if match:
                        filtered_images.append(image)

                images = filtered_images

            # Format image information
            image_list = [self.format_image_info(img) for img in images]

            return {
                "images": image_list,
                "count": len(image_list),
                "all": all_images,
                "filters": filters
            }

        except Exception as e:
            raise MCPError("PODMAN_ERROR", f"Failed to list images: {str(e)}")

    async def podman_pull(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Pull an image."""
        image = params["image"]

        if not self.client:
            raise MCPError("PODMAN_NOT_CONNECTED", "Podman client not connected")

        try:
            # Pull the image
            pulled_image = self.client.images.pull(image)

            return {
                "pulled": True,
                "image": image,
                "image_info": self.format_image_info(pulled_image)
            }

        except Exception as e:
            raise MCPError("PODMAN_ERROR", f"Failed to pull image '{image}': {str(e)}")

    async def podman_compose_up(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Start services from compose file."""
        file_path = params.get("file", "docker-compose.yml")
        project_name = params.get("project_name")
        detach = params.get("detach", True)

        if not self.client:
            raise MCPError("PODMAN_NOT_CONNECTED", "Podman client not connected")

        try:
            # Check if compose file exists
            compose_file = Path(file_path)
            if not compose_file.exists():
                raise MCPError("COMPOSE_FILE_NOT_FOUND", f"Compose file not found: {file_path}")

            # For now, we'll use a simple approach
            # In a full implementation, you'd parse the compose file and create containers accordingly
            # This is a placeholder that would need docker-compose integration

            return {
                "started": True,
                "file": file_path,
                "project_name": project_name,
                "detach": detach,
                "note": "Compose file parsing not fully implemented - use individual container operations"
            }

        except MCPError:
            raise
        except Exception as e:
            raise MCPError("PODMAN_ERROR", f"Failed to start compose services: {str(e)}")

    async def podman_compose_down(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Stop services from compose file."""
        file_path = params.get("file", "docker-compose.yml")
        project_name = params.get("project_name")
        volumes = params.get("volumes", False)

        if not self.client:
            raise MCPError("PODMAN_NOT_CONNECTED", "Podman client not connected")

        try:
            # Placeholder implementation
            # In a full implementation, you'd identify containers by compose project and stop them

            return {
                "stopped": True,
                "file": file_path,
                "project_name": project_name,
                "volumes": volumes,
                "note": "Compose file parsing not fully implemented - use individual container operations"
            }

        except Exception as e:
            raise MCPError("PODMAN_ERROR", f"Failed to stop compose services: {str(e)}")


async def main():
    """Main server entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Podman MCP Server")
    parser.add_argument(
        "--socket-path",
        help="Path to Podman socket (default: user-specific socket)"
    )
    parser.add_argument(
        "--base-url",
        default="unix:///run/user/$(id -u)/podman/podman.sock",
        help="Podman API base URL"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Operation timeout in seconds (default: 30)"
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "websocket"],
        default="websocket",
        help="Transport mechanism (default: websocket for container operations)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8913,
        help="Port for WebSocket transport (default: 8913)"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Log level"
    )

    args = parser.parse_args()

    # Configure logging
    logging.getLogger().setLevel(getattr(logging, args.log_level))

    try:
        # Create server instance
        server = PodmanMCPServer(
            socket_path=args.socket_path,
            base_url=args.base_url,
            timeout=args.timeout
        )

        # Configure transport
        if args.transport == "websocket":
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
