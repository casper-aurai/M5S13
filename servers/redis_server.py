#!/usr/bin/env python3
"""
Redis MCP Server

Provides key-value store operations for agent state management.
Implements stdio and WebSocket transport layers.
"""

import asyncio
import json
import logging
import os
import sys
import time
from typing import Any, Dict, List, Optional, Union

try:
    import redis.asyncio as redis
except ImportError:
    redis = None

try:
    from .base_mcp_server import MCPServer, MCPError, Tool
except ImportError:
    # For standalone execution
    from base_mcp_server import MCPServer, MCPError, Tool


class RedisMCPServer(MCPServer):
    """Redis MCP Server implementation."""

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        db: int = 1,
        max_connections: int = 10,
        session_ttl: int = 3600  # 1 hour default TTL for sessions
    ):
        super().__init__("redis", "1.0.0")

        if redis is None:
            raise MCPError("REDIS_DEPENDENCY", "redis package is required for Redis server")

        self.redis_url = redis_url
        self.db = db
        self.max_connections = max_connections
        self.session_ttl = session_ttl

        self.redis_client = None
        self.connection_pool = None

        logging.info(f"Redis server configured for {redis_url}, db={db}")

    async def connect(self):
        """Establish Redis connection."""
        try:
            # Create connection pool
            self.connection_pool = redis.ConnectionPool.from_url(
                self.redis_url,
                db=self.db,
                max_connections=self.max_connections,
                decode_responses=True  # Return strings instead of bytes
            )

            # Create Redis client
            self.redis_client = redis.Redis.from_url(
                self.redis_url,
                db=self.db,
                decode_responses=True
            )

            # Test connection
            await self.redis_client.ping()
            logging.info("Redis connection established successfully")

        except Exception as e:
            raise MCPError("REDIS_CONNECTION_FAILED", f"Failed to connect to Redis: {str(e)}")

    async def disconnect(self):
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()
            logging.info("Redis connection closed")

        if self.connection_pool:
            await self.connection_pool.disconnect()
            logging.info("Redis connection pool closed")

    def serialize_value(self, value: Any) -> str:
        """Serialize value for Redis storage."""
        if isinstance(value, (str, int, float, bool)):
            return str(value)
        else:
            # JSON serialize complex types
            return json.dumps(value, ensure_ascii=False)

    def deserialize_value(self, value: str) -> Any:
        """Deserialize value from Redis."""
        if value is None:
            return None

        # Try to parse as JSON first
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            # Return as string if not valid JSON
            return value

    async def setup_tools(self):
        """Setup Redis tools."""
        # Basic key-value operations
        self.register_tool(Tool(
            "redis_get",
            "Get value by key",
            {
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "Key to retrieve"
                    }
                },
                "required": ["key"]
            },
            self.redis_get
        ))

        self.register_tool(Tool(
            "redis_set",
            "Set key-value pair",
            {
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "Key to set"
                    },
                    "value": {
                        "type": "string",
                        "description": "Value to store (will be JSON serialized if object)"
                    },
                    "ttl": {
                        "type": "integer",
                        "description": "Time-to-live in seconds (optional)",
                        "minimum": 1
                    }
                },
                "required": ["key", "value"]
            },
            self.redis_set
        ))

        self.register_tool(Tool(
            "redis_del",
            "Delete key(s)",
            {
                "type": "object",
                "properties": {
                    "keys": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Keys to delete"
                    }
                },
                "required": ["keys"]
            },
            self.redis_del
        ))

        # Key management
        self.register_tool(Tool(
            "redis_exists",
            "Check if key(s) exist",
            {
                "type": "object",
                "properties": {
                    "keys": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Keys to check"
                    }
                },
                "required": ["keys"]
            },
            self.redis_exists
        ))

        self.register_tool(Tool(
            "redis_keys",
            "Get all keys matching pattern",
            {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Pattern to match (default: *)",
                        "default": "*"
                    },
                    "count": {
                        "type": "integer",
                        "description": "Maximum number of keys to return (default: 100)",
                        "minimum": 1,
                        "maximum": 1000,
                        "default": 100
                    }
                }
            },
            self.redis_keys
        ))

        self.register_tool(Tool(
            "redis_ttl",
            "Get TTL for key",
            {
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "Key to check"
                    }
                },
                "required": ["key"]
            },
            self.redis_ttl
        ))

        # List operations
        self.register_tool(Tool(
            "redis_lpush",
            "Push value to front of list",
            {
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "List key"
                    },
                    "values": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Values to push"
                    }
                },
                "required": ["key", "values"]
            },
            self.redis_lpush
        ))

        self.register_tool(Tool(
            "redis_rpush",
            "Push value to end of list",
            {
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "List key"
                    },
                    "values": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Values to push"
                    }
                },
                "required": ["key", "values"]
            },
            self.redis_rpush
        ))

        self.register_tool(Tool(
            "redis_lpop",
            "Pop value from front of list",
            {
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "List key"
                    },
                    "count": {
                        "type": "integer",
                        "description": "Number of items to pop (default: 1)",
                        "minimum": 1,
                        "default": 1
                    }
                },
                "required": ["key"]
            },
            self.redis_lpop
        ))

        # Hash operations
        self.register_tool(Tool(
            "redis_hset",
            "Set field in hash",
            {
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "Hash key"
                    },
                    "field": {
                        "type": "string",
                        "description": "Field name"
                    },
                    "value": {
                        "type": "string",
                        "description": "Field value"
                    }
                },
                "required": ["key", "field", "value"]
            },
            self.redis_hset
        ))

        self.register_tool(Tool(
            "redis_hget",
            "Get field from hash",
            {
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "Hash key"
                    },
                    "field": {
                        "type": "string",
                        "description": "Field name"
                    }
                },
                "required": ["key", "field"]
            },
            self.redis_hget
        ))

        self.register_tool(Tool(
            "redis_hgetall",
            "Get all fields from hash",
            {
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "Hash key"
                    }
                },
                "required": ["key"]
            },
            self.redis_hgetall
        ))

        # Session management (specific to MCP agent sessions)
        self.register_tool(Tool(
            "redis_session_create",
            "Create a new session",
            {
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Session ID (auto-generated if not provided)"
                    },
                    "data": {
                        "type": "object",
                        "description": "Initial session data"
                    },
                    "ttl": {
                        "type": "integer",
                        "description": "Session TTL in seconds (default: 3600)",
                        "minimum": 1,
                        "default": 3600
                    }
                }
            },
            self.redis_session_create
        ))

        self.register_tool(Tool(
            "redis_session_get",
            "Get session data",
            {
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Session ID"
                    }
                },
                "required": ["session_id"]
            },
            self.redis_session_get
        ))

        self.register_tool(Tool(
            "redis_session_update",
            "Update session data",
            {
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Session ID"
                    },
                    "data": {
                        "type": "object",
                        "description": "Data to update"
                    },
                    "extend_ttl": {
                        "type": "boolean",
                        "description": "Extend session TTL (default: true)",
                        "default": True
                    }
                },
                "required": ["session_id", "data"]
            },
            self.redis_session_update
        ))

        self.register_tool(Tool(
            "redis_session_delete",
            "Delete session",
            {
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Session ID"
                    }
                },
                "required": ["session_id"]
            },
            self.redis_session_delete
        ))

    async def start(self):
        """Start the Redis MCP server."""
        # Establish Redis connection first
        await self.connect()

        try:
            # Call parent start method
            await super().start()
        except Exception:
            # Ensure Redis connection is closed on error
            await self.disconnect()
            raise

    def stop(self):
        """Stop the Redis MCP server."""
        # Close Redis connection
        if self.redis_client:
            asyncio.create_task(self.disconnect())

        # Call parent stop method
        super().stop()

    async def redis_get(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get value by key."""
        key = params["key"]

        if not self.redis_client:
            raise MCPError("REDIS_NOT_CONNECTED", "Redis client not connected")

        try:
            value = await self.redis_client.get(key)
            return {
                "key": key,
                "value": self.deserialize_value(value),
                "exists": value is not None
            }
        except Exception as e:
            raise MCPError("REDIS_ERROR", f"Failed to get key '{key}': {str(e)}")

    async def redis_set(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Set key-value pair."""
        key = params["key"]
        value = params["value"]
        ttl = params.get("ttl")

        if not self.redis_client:
            raise MCPError("REDIS_NOT_CONNECTED", "Redis client not connected")

        try:
            serialized_value = self.serialize_value(value)

            if ttl:
                await self.redis_client.setex(key, ttl, serialized_value)
            else:
                await self.redis_client.set(key, serialized_value)

            return {
                "key": key,
                "value": value,
                "ttl": ttl,
                "set": True
            }
        except Exception as e:
            raise MCPError("REDIS_ERROR", f"Failed to set key '{key}': {str(e)}")

    async def redis_del(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Delete key(s)."""
        keys = params["keys"]

        if not self.redis_client:
            raise MCPError("REDIS_NOT_CONNECTED", "Redis client not connected")

        try:
            deleted_count = await self.redis_client.delete(*keys)

            return {
                "keys": keys,
                "deleted_count": deleted_count
            }
        except Exception as e:
            raise MCPError("REDIS_ERROR", f"Failed to delete keys: {str(e)}")

    async def redis_exists(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Check if key(s) exist."""
        keys = params["keys"]

        if not self.redis_client:
            raise MCPError("REDIS_NOT_CONNECTED", "Redis client not connected")

        try:
            exists_results = await self.redis_client.exists(*keys)

            return {
                "keys": keys,
                "exists": [bool(exists) for exists in exists_results]
            }
        except Exception as e:
            raise MCPError("REDIS_ERROR", f"Failed to check key existence: {str(e)}")

    async def redis_keys(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get all keys matching pattern."""
        pattern = params.get("pattern", "*")
        count = params.get("count", 100)

        if not self.redis_client:
            raise MCPError("REDIS_NOT_CONNECTED", "Redis client not connected")

        try:
            keys = await self.redis_client.keys(pattern)
            # Limit results
            limited_keys = keys[:count]

            return {
                "keys": limited_keys,
                "pattern": pattern,
                "count": len(limited_keys),
                "total_matched": len(keys)
            }
        except Exception as e:
            raise MCPError("REDIS_ERROR", f"Failed to get keys: {str(e)}")

    async def redis_ttl(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get TTL for key."""
        key = params["key"]

        if not self.redis_client:
            raise MCPError("REDIS_NOT_CONNECTED", "Redis client not connected")

        try:
            ttl = await self.redis_client.ttl(key)

            return {
                "key": key,
                "ttl": ttl,
                "persistent": ttl == -1,
                "not_found": ttl == -2
            }
        except Exception as e:
            raise MCPError("REDIS_ERROR", f"Failed to get TTL for '{key}': {str(e)}")

    async def redis_lpush(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Push value to front of list."""
        key = params["key"]
        values = params["values"]

        if not self.redis_client:
            raise MCPError("REDIS_NOT_CONNECTED", "Redis client not connected")

        try:
            pushed_count = await self.redis_client.lpush(key, *values)

            return {
                "key": key,
                "values": values,
                "pushed_count": pushed_count
            }
        except Exception as e:
            raise MCPError("REDIS_ERROR", f"Failed to push to list '{key}': {str(e)}")

    async def redis_rpush(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Push value to end of list."""
        key = params["key"]
        values = params["values"]

        if not self.redis_client:
            raise MCPError("REDIS_NOT_CONNECTED", "Redis client not connected")

        try:
            pushed_count = await self.redis_client.rpush(key, *values)

            return {
                "key": key,
                "values": values,
                "pushed_count": pushed_count
            }
        except Exception as e:
            raise MCPError("REDIS_ERROR", f"Failed to push to list '{key}': {str(e)}")

    async def redis_lpop(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Pop value from front of list."""
        key = params["key"]
        count = params.get("count", 1)

        if not self.redis_client:
            raise MCPError("REDIS_NOT_CONNECTED", "Redis client not connected")

        try:
            if count == 1:
                value = await self.redis_client.lpop(key)
                return {
                    "key": key,
                    "value": self.deserialize_value(value),
                    "values": [self.deserialize_value(value)] if value else []
                }
            else:
                values = await self.redis_client.lpop(key, count)
                return {
                    "key": key,
                    "values": [self.deserialize_value(v) for v in values],
                    "count": len(values)
                }
        except Exception as e:
            raise MCPError("REDIS_ERROR", f"Failed to pop from list '{key}': {str(e)}")

    async def redis_hset(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Set field in hash."""
        key = params["key"]
        field = params["field"]
        value = params["value"]

        if not self.redis_client:
            raise MCPError("REDIS_NOT_CONNECTED", "Redis client not connected")

        try:
            set_count = await self.redis_client.hset(key, field, self.serialize_value(value))

            return {
                "key": key,
                "field": field,
                "value": value,
                "set_count": set_count
            }
        except Exception as e:
            raise MCPError("REDIS_ERROR", f"Failed to set hash field '{key}:{field}': {str(e)}")

    async def redis_hget(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get field from hash."""
        key = params["key"]
        field = params["field"]

        if not self.redis_client:
            raise MCPError("REDIS_NOT_CONNECTED", "Redis client not connected")

        try:
            value = await self.redis_client.hget(key, field)

            return {
                "key": key,
                "field": field,
                "value": self.deserialize_value(value),
                "exists": value is not None
            }
        except Exception as e:
            raise MCPError("REDIS_ERROR", f"Failed to get hash field '{key}:{field}': {str(e)}")

    async def redis_hgetall(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get all fields from hash."""
        key = params["key"]

        if not self.redis_client:
            raise MCPError("REDIS_NOT_CONNECTED", "Redis client not connected")

        try:
            hash_data = await self.redis_client.hgetall(key)

            # Deserialize all values
            deserialized_data = {
                field: self.deserialize_value(value)
                for field, value in hash_data.items()
            }

            return {
                "key": key,
                "fields": deserialized_data,
                "count": len(deserialized_data)
            }
        except Exception as e:
            raise MCPError("REDIS_ERROR", f"Failed to get hash '{key}': {str(e)}")

    async def redis_session_create(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new session."""
        session_id = params.get("session_id") or f"session:{int(time.time())}:{id(self)}"
        data = params.get("data", {})
        ttl = params.get("ttl", self.session_ttl)

        if not self.redis_client:
            raise MCPError("REDIS_NOT_CONNECTED", "Redis client not connected")

        try:
            # Store session data as hash
            session_key = f"mcp_session:{session_id}"

            # Set initial data
            if data:
                await self.redis_client.hmset(session_key, {
                    field: self.serialize_value(value)
                    for field, value in data.items()
                })

            # Set TTL
            await self.redis_client.expire(session_key, ttl)

            # Store session metadata
            metadata_key = f"mcp_session_meta:{session_id}"
            await self.redis_client.hmset(metadata_key, {
                "created_at": str(int(time.time())),
                "ttl": str(ttl),
                "data_key": session_key
            })
            await self.redis_client.expire(metadata_key, ttl)

            return {
                "session_id": session_id,
                "created": True,
                "ttl": ttl,
                "data": data
            }
        except Exception as e:
            raise MCPError("REDIS_ERROR", f"Failed to create session: {str(e)}")

    async def redis_session_get(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get session data."""
        session_id = params["session_id"]

        if not self.redis_client:
            raise MCPError("REDIS_NOT_CONNECTED", "Redis client not connected")

        try:
            session_key = f"mcp_session:{session_id}"
            metadata_key = f"mcp_session_meta:{session_id}"

            # Check if session exists
            if not await self.redis_client.exists(session_key):
                raise MCPError("SESSION_NOT_FOUND", f"Session not found: {session_id}")

            # Get session data
            session_data = await self.redis_client.hgetall(session_key)

            # Deserialize data
            deserialized_data = {
                field: self.deserialize_value(value)
                for field, value in session_data.items()
            }

            # Get metadata
            metadata = await self.redis_client.hgetall(metadata_key)

            return {
                "session_id": session_id,
                "data": deserialized_data,
                "metadata": metadata,
                "exists": True
            }
        except MCPError:
            raise
        except Exception as e:
            raise MCPError("REDIS_ERROR", f"Failed to get session '{session_id}': {str(e)}")

    async def redis_session_update(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Update session data."""
        session_id = params["session_id"]
        data = params["data"]
        extend_ttl = params.get("extend_ttl", True)

        if not self.redis_client:
            raise MCPError("REDIS_NOT_CONNECTED", "Redis client not connected")

        try:
            session_key = f"mcp_session:{session_id}"

            # Check if session exists
            if not await self.redis_client.exists(session_key):
                raise MCPError("SESSION_NOT_FOUND", f"Session not found: {session_id}")

            # Update session data
            if data:
                await self.redis_client.hmset(session_key, {
                    field: self.serialize_value(value)
                    for field, value in data.items()
                })

            # Extend TTL if requested
            if extend_ttl:
                await self.redis_client.expire(session_key, self.session_ttl)

                # Also extend metadata TTL
                metadata_key = f"mcp_session_meta:{session_id}"
                await self.redis_client.expire(metadata_key, self.session_ttl)

            return {
                "session_id": session_id,
                "updated": True,
                "data": data,
                "extended_ttl": extend_ttl
            }
        except MCPError:
            raise
        except Exception as e:
            raise MCPError("REDIS_ERROR", f"Failed to update session '{session_id}': {str(e)}")

    async def redis_session_delete(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Delete session."""
        session_id = params["session_id"]

        if not self.redis_client:
            raise MCPError("REDIS_NOT_CONNECTED", "Redis client not connected")

        try:
            session_key = f"mcp_session:{session_id}"
            metadata_key = f"mcp_session_meta:{session_id}"

            # Delete both keys
            deleted_count = await self.redis_client.delete(session_key, metadata_key)

            return {
                "session_id": session_id,
                "deleted": deleted_count > 0
            }
        except Exception as e:
            raise MCPError("REDIS_ERROR", f"Failed to delete session '{session_id}': {str(e)}")


async def main():
    """Main server entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Redis MCP Server")
    parser.add_argument(
        "--redis-url",
        default="redis://localhost:6379",
        help="Redis URL (default: redis://localhost:6379)"
    )
    parser.add_argument(
        "--db",
        type=int,
        default=1,
        help="Redis database number (default: 1)"
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

    # Configure logging
    logging.getLogger().setLevel(getattr(logging, args.log_level))

    try:
        # Create server instance
        server = RedisMCPServer(
            redis_url=args.redis_url,
            db=args.db
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
