#!/usr/bin/env python3
"""
Comprehensive tests for Redis MCP Server

Tests all Redis operations including key-value operations, lists, hashes, and session management.
"""
import asyncio
import json
import pytest
import time
from unittest.mock import patch, MagicMock, AsyncMock

# Import the Redis MCP Server
import sys
sys.path.append(str(Path(__file__).parent.parent))

from servers.redis_server import RedisMCPServer, MCPError


class TestRedisMCPServer:
    """Test suite for Redis MCP Server functionality."""

    @pytest.fixture
    def mock_redis_client(self):
        """Create a mock Redis client for testing."""
        mock_client = AsyncMock()

        # Mock basic operations
        mock_client.get.return_value = '{"key": "value"}'
        mock_client.set.return_value = True
        mock_client.delete.return_value = 1
        mock_client.exists.return_value = [1, 0, 1]  # First and third exist
        mock_client.keys.return_value = ["user:123", "session:abc", "cache:temp"]
        mock_client.ttl.return_value = 3600
        mock_client.lpush.return_value = 3
        mock_client.rpush.return_value = 2
        mock_client.lpop.return_value = "item1"
        mock_client.hset.return_value = 1
        mock_client.hget.return_value = '{"field": "data"}'
        mock_client.hgetall.return_value = {"name": "test", "value": "123"}

        # Mock session operations
        mock_client.hmset = AsyncMock(return_value=True)
        mock_client.hgetall = AsyncMock(return_value={"data": '{"user_id": "123"}'})
        mock_client.expire = AsyncMock(return_value=True)

        return mock_client

    @pytest.fixture
    def redis_server(self, mock_redis_client):
        """Create Redis MCP Server instance with mocked client."""
        with patch('redis.asyncio.Redis') as mock_redis_class:
            mock_redis_class.from_url.return_value = mock_redis_client

            server = RedisMCPServer()
            server.redis_client = mock_redis_client  # Inject mock client
            return server

    def test_server_initialization(self):
        """Test server initialization."""
        with patch('redis.asyncio.Redis') as mock_redis:
            mock_redis.from_url.return_value = MagicMock()

            server = RedisMCPServer()
            assert server.server_name == "redis"
            assert server.server_version == "1.0.0"
            assert server.session_ttl == 3600

    def test_invalid_redis_dependency(self):
        """Test server initialization without redis-py."""
        with patch.dict('sys.modules', {'redis.asyncio': None}):
            with pytest.raises(MCPError, match="redis package is required"):
                RedisMCPServer()

    @pytest.mark.asyncio
    async def test_redis_get_existing_key(self, redis_server, mock_redis_client):
        """Test getting an existing key."""
        result = await redis_server.redis_get({"key": "test:key"})

        assert result["key"] == "test:key"
        assert "value" in result
        assert result["exists"] is True
        mock_redis_client.get.assert_called_once_with("test:key")

    @pytest.mark.asyncio
    async def test_redis_get_nonexistent_key(self, redis_server, mock_redis_client):
        """Test getting a nonexistent key."""
        mock_redis_client.get.return_value = None

        result = await redis_server.redis_get({"key": "nonexistent"})

        assert result["key"] == "nonexistent"
        assert result["value"] is None
        assert result["exists"] is False

    @pytest.mark.asyncio
    async def test_redis_set_with_ttl(self, redis_server, mock_redis_client):
        """Test setting a key with TTL."""
        test_data = {"user_id": "123", "preferences": {"theme": "dark"}}

        result = await redis_server.redis_set({
            "key": "user:preferences",
            "value": test_data,
            "ttl": 7200
        })

        assert result["key"] == "user:preferences"
        assert result["value"] == test_data
        assert result["ttl"] == 7200
        assert result["set"] is True

    @pytest.mark.asyncio
    async def test_redis_set_without_ttl(self, redis_server, mock_redis_client):
        """Test setting a key without TTL."""
        result = await redis_server.redis_set({
            "key": "persistent:key",
            "value": "persistent_value"
        })

        assert result["key"] == "persistent:key"
        assert result["ttl"] is None

    @pytest.mark.asyncio
    async def test_redis_del_single_key(self, redis_server, mock_redis_client):
        """Test deleting a single key."""
        result = await redis_server.redis_del({"keys": ["temp:key"]})

        assert result["keys"] == ["temp:key"]
        assert result["deleted_count"] == 1
        mock_redis_client.delete.assert_called_once_with("temp:key")

    @pytest.mark.asyncio
    async def test_redis_del_multiple_keys(self, redis_server, mock_redis_client):
        """Test deleting multiple keys."""
        result = await redis_server.redis_del({
            "keys": ["key1", "key2", "key3"]
        })

        assert result["keys"] == ["key1", "key2", "key3"]
        assert result["deleted_count"] == 1  # Mock returns 1
        mock_redis_client.delete.assert_called_once_with("key1", "key2", "key3")

    @pytest.mark.asyncio
    async def test_redis_exists(self, redis_server, mock_redis_client):
        """Test checking key existence."""
        result = await redis_server.redis_exists({
            "keys": ["existing1", "nonexistent", "existing2"]
        })

        assert result["keys"] == ["existing1", "nonexistent", "existing2"]
        assert result["exists"] == [True, False, True]

    @pytest.mark.asyncio
    async def test_redis_keys_with_pattern(self, redis_server, mock_redis_client):
        """Test getting keys with pattern."""
        result = await redis_server.redis_keys({
            "pattern": "user:*",
            "count": 50
        })

        assert result["pattern"] == "user:*"
        assert result["count"] == 3  # Mock returns 3 keys
        assert "total_matched" in result
        mock_redis_client.keys.assert_called_once_with("user:*")

    @pytest.mark.asyncio
    async def test_redis_keys_default_pattern(self, redis_server, mock_redis_client):
        """Test getting keys with default pattern."""
        result = await redis_server.redis_keys({})

        assert result["pattern"] == "*"  # Default pattern
        assert result["count"] == 3

    @pytest.mark.asyncio
    async def test_redis_ttl_persistent_key(self, redis_server, mock_redis_client):
        """Test getting TTL for persistent key."""
        mock_redis_client.ttl.return_value = -1  # Persistent

        result = await redis_server.redis_ttl({"key": "persistent:key"})

        assert result["key"] == "persistent:key"
        assert result["ttl"] == -1
        assert result["persistent"] is True
        assert result["not_found"] is False

    @pytest.mark.asyncio
    async def test_redis_ttl_nonexistent_key(self, redis_server, mock_redis_client):
        """Test getting TTL for nonexistent key."""
        mock_redis_client.ttl.return_value = -2  # Not found

        result = await redis_server.redis_ttl({"key": "nonexistent"})

        assert result["key"] == "nonexistent"
        assert result["ttl"] == -2
        assert result["not_found"] is True

    @pytest.mark.asyncio
    async def test_redis_lpush(self, redis_server, mock_redis_client):
        """Test pushing to front of list."""
        result = await redis_server.redis_lpush({
            "key": "my:list",
            "values": ["item1", "item2", "item3"]
        })

        assert result["key"] == "my:list"
        assert result["values"] == ["item1", "item2", "item3"]
        assert result["pushed_count"] == 3

    @pytest.mark.asyncio
    async def test_redis_rpush(self, redis_server, mock_redis_client):
        """Test pushing to end of list."""
        result = await redis_server.redis_rpush({
            "key": "my:list",
            "values": ["item1", "item2"]
        })

        assert result["key"] == "my:list"
        assert result["values"] == ["item1", "item2"]
        assert result["pushed_count"] == 2

    @pytest.mark.asyncio
    async def test_redis_lpop_single(self, redis_server, mock_redis_client):
        """Test popping single item from list."""
        result = await redis_server.redis_lpop({"key": "my:list"})

        assert result["key"] == "my:list"
        assert "value" in result
        assert "values" in result
        assert len(result["values"]) == 1

    @pytest.mark.asyncio
    async def test_redis_lpop_multiple(self, redis_server, mock_redis_client):
        """Test popping multiple items from list."""
        mock_redis_client.lpop.return_value = ["item1", "item2"]

        result = await redis_server.redis_lpop({
            "key": "my:list",
            "count": 2
        })

        assert result["key"] == "my:list"
        assert result["count"] == 2
        assert len(result["values"]) == 2

    @pytest.mark.asyncio
    async def test_redis_hset(self, redis_server, mock_redis_client):
        """Test setting hash field."""
        test_value = {"nested": "data", "number": 42}

        result = await redis_server.redis_hset({
            "key": "user:profile",
            "field": "preferences",
            "value": test_value
        })

        assert result["key"] == "user:profile"
        assert result["field"] == "preferences"
        assert result["value"] == test_value
        assert result["set_count"] == 1

    @pytest.mark.asyncio
    async def test_redis_hget_existing_field(self, redis_server, mock_redis_client):
        """Test getting existing hash field."""
        result = await redis_server.redis_hget({
            "key": "user:profile",
            "field": "preferences"
        })

        assert result["key"] == "user:profile"
        assert result["field"] == "preferences"
        assert "value" in result
        assert result["exists"] is True

    @pytest.mark.asyncio
    async def test_redis_hget_nonexistent_field(self, redis_server, mock_redis_client):
        """Test getting nonexistent hash field."""
        mock_redis_client.hget.return_value = None

        result = await redis_server.redis_hget({
            "key": "user:profile",
            "field": "nonexistent"
        })

        assert result["key"] == "user:profile"
        assert result["field"] == "nonexistent"
        assert result["value"] is None
        assert result["exists"] is False

    @pytest.mark.asyncio
    async def test_redis_hgetall(self, redis_server, mock_redis_client):
        """Test getting all hash fields."""
        result = await redis_server.redis_hgetall({"key": "user:profile"})

        assert result["key"] == "user:profile"
        assert "fields" in result
        assert "count" in result
        assert result["count"] == 2  # Mock returns 2 fields

    @pytest.mark.asyncio
    async def test_redis_session_create(self, redis_server, mock_redis_client):
        """Test creating a session."""
        session_data = {
            "user_id": "user123",
            "context": {"task": "analyze_code", "progress": 0.1}
        }

        result = await redis_server.redis_session_create({
            "session_id": "test_session_123",
            "data": session_data,
            "ttl": 7200
        })

        assert result["session_id"] == "test_session_123"
        assert result["created"] is True
        assert result["ttl"] == 7200
        assert result["data"] == session_data

    @pytest.mark.asyncio
    async def test_redis_session_create_auto_id(self, redis_server, mock_redis_client):
        """Test creating session with auto-generated ID."""
        result = await redis_server.redis_session_create({})

        assert result["created"] is True
        assert "session_id" in result
        assert result["ttl"] == 3600  # Default TTL

    @pytest.mark.asyncio
    async def test_redis_session_get_existing(self, redis_server, mock_redis_client):
        """Test getting existing session."""
        result = await redis_server.redis_session_get({"session_id": "existing_session"})

        assert result["session_id"] == "existing_session"
        assert result["exists"] is True
        assert "data" in result
        assert "metadata" in result

    @pytest.mark.asyncio
    async def test_redis_session_get_nonexistent(self, redis_server, mock_redis_client):
        """Test getting nonexistent session."""
        mock_redis_client.exists.return_value = False

        with pytest.raises(MCPError, match="Session not found"):
            await redis_server.redis_session_get({"session_id": "nonexistent"})

    @pytest.mark.asyncio
    async def test_redis_session_update(self, redis_server, mock_redis_client):
        """Test updating session data."""
        update_data = {"progress": 0.8, "status": "in_progress"}

        result = await redis_server.redis_session_update({
            "session_id": "test_session",
            "data": update_data,
            "extend_ttl": True
        })

        assert result["session_id"] == "test_session"
        assert result["updated"] is True
        assert result["data"] == update_data
        assert result["extended_ttl"] is True

    @pytest.mark.asyncio
    async def test_redis_session_delete(self, redis_server, mock_redis_client):
        """Test deleting session."""
        result = await redis_server.redis_session_delete({"session_id": "test_session"})

        assert result["session_id"] == "test_session"
        assert result["deleted"] is True

    def test_serialize_value(self, redis_server):
        """Test value serialization."""
        # Test JSON serializable data
        data = {"key": "value", "number": 42}
        serialized = redis_server.serialize_value(data)
        assert isinstance(serialized, str)

        # Test string
        serialized = redis_server.serialize_value("simple string")
        assert serialized == "simple string"

    def test_deserialize_value(self, redis_server):
        """Test value deserialization."""
        # Test JSON string
        json_str = '{"key": "value", "number": 42}'
        deserialized = redis_server.deserialize_value(json_str)
        assert deserialized == {"key": "value", "number": 42}

        # Test None
        assert redis_server.deserialize_value(None) is None

    @pytest.mark.asyncio
    async def test_error_handling_invalid_params(self, redis_server):
        """Test error handling for invalid parameters."""
        with pytest.raises(MCPError):
            await redis_server.redis_get({})  # Missing required key

    @pytest.mark.asyncio
    async def test_health_check_endpoint(self, redis_server):
        """Test health check functionality."""
        request = {"method": "health", "id": "test"}
        response = await redis_server.handle_request(request)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == "test"
        assert "result" in response
        assert response["result"]["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_metrics_endpoint(self, redis_server):
        """Test metrics functionality."""
        request = {"method": "metrics", "id": "test"}
        response = await redis_server.handle_request(request)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == "test"
        assert "result" in response
        assert "uptime_seconds" in response["result"]
        assert "total_requests" in response["result"]


class TestRedisServerIntegration:
    """Integration tests for the complete Redis MCP Server."""

    @pytest.mark.asyncio
    async def test_complete_session_workflow(self, mock_redis_client):
        """Test complete session lifecycle: create -> get -> update -> delete."""
        with patch('redis.asyncio.Redis') as mock_redis_class:
            mock_redis_class.from_url.return_value = mock_redis_client

            server = RedisMCPServer()
            server.redis_client = mock_redis_client

            # 1. Create session
            session_data = {"user_id": "user123", "task": "analyze"}
            create_result = await server.redis_session_create({
                "data": session_data,
                "ttl": 3600
            })
            session_id = create_result["session_id"]
            assert create_result["created"] is True

            # 2. Get session
            get_result = await server.redis_session_get({"session_id": session_id})
            assert get_result["exists"] is True
            assert get_result["data"]["user_id"] == "user123"

            # 3. Update session
            update_data = {"progress": 0.5, "status": "in_progress"}
            update_result = await server.redis_session_update({
                "session_id": session_id,
                "data": update_data
            })
            assert update_result["updated"] is True

            # 4. Verify updated data
            get_updated = await server.redis_session_get({"session_id": session_id})
            assert get_updated["data"]["progress"] == 0.5

            # 5. Delete session
            delete_result = await server.redis_session_delete({"session_id": session_id})
            assert delete_result["deleted"] is True

    @pytest.mark.asyncio
    async def test_key_value_operations(self, mock_redis_client):
        """Test key-value operations workflow."""
        with patch('redis.asyncio.Redis') as mock_redis_class:
            mock_redis_class.from_url.return_value = mock_redis_client

            server = RedisMCPServer()
            server.redis_client = mock_redis_client

            # 1. Set key-value pair
            set_result = await server.redis_set({
                "key": "test:data",
                "value": {"type": "test", "value": "example"},
                "ttl": 1800
            })
            assert set_result["set"] is True

            # 2. Get the value back
            get_result = await server.redis_get({"key": "test:data"})
            assert get_result["exists"] is True
            assert get_result["value"]["type"] == "test"

            # 3. Check TTL
            ttl_result = await server.redis_ttl({"key": "test:data"})
            assert ttl_result["ttl"] > 0

            # 4. Delete the key
            del_result = await server.redis_del({"keys": ["test:data"]})
            assert del_result["deleted_count"] >= 1

    @pytest.mark.asyncio
    async def test_list_operations(self, mock_redis_client):
        """Test list operations workflow."""
        with patch('redis.asyncio.Redis') as mock_redis_class:
            mock_redis_class.from_url.return_value = mock_redis_client

            server = RedisMCPServer()
            server.redis_client = mock_redis_client

            list_key = "task:queue"

            # 1. Push items to list
            push_result = await server.redis_rpush({
                "key": list_key,
                "values": ["task1", "task2", "task3"]
            })
            assert push_result["pushed_count"] == 2  # Mock returns 2

            # 2. Pop items from list
            pop_result = await server.redis_lpop({
                "key": list_key,
                "count": 2
            })
            assert pop_result["count"] == 2

    @pytest.mark.asyncio
    async def test_hash_operations(self, mock_redis_client):
        """Test hash operations workflow."""
        with patch('redis.asyncio.Redis') as mock_redis_class:
            mock_redis_class.from_url.return_value = mock_redis_client

            server = RedisMCPServer()
            server.redis_client = mock_redis_client

            hash_key = "user:profile"

            # 1. Set hash fields
            hset_result = await server.redis_hset({
                "key": hash_key,
                "field": "name",
                "value": "John Doe"
            })
            assert hset_result["set_count"] == 1

            # 2. Set another field
            await server.redis_hset({
                "key": hash_key,
                "field": "email",
                "value": "john@example.com"
            })

            # 3. Get single field
            hget_result = await server.redis_hget({
                "key": hash_key,
                "field": "name"
            })
            assert hget_result["value"] == "John Doe"

            # 4. Get all fields
            hgetall_result = await server.redis_hgetall({"key": hash_key})
            assert hgetall_result["count"] == 2
            assert "name" in hgetall_result["fields"]
            assert "email" in hgetall_result["fields"]

    @pytest.mark.asyncio
    async def test_error_recovery(self, mock_redis_client):
        """Test error handling and recovery."""
        mock_redis_client.get.side_effect = Exception("Connection failed")

        with patch('redis.asyncio.Redis') as mock_redis_class:
            mock_redis_class.from_url.return_value = mock_redis_client

            server = RedisMCPServer()
            server.redis_client = mock_redis_client

            with pytest.raises(MCPError, match="Failed to get key"):
                await server.redis_get({"key": "test"})

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, mock_redis_client):
        """Test concurrent Redis operations."""
        with patch('redis.asyncio.Redis') as mock_redis_class:
            mock_redis_class.from_url.return_value = mock_redis_client

            server = RedisMCPServer()
            server.redis_client = mock_redis_client

            async def set_key_value(key, value):
                return await server.redis_set({
                    "key": key,
                    "value": value,
                    "ttl": 3600
                })

            async def run_concurrent():
                tasks = [
                    set_key_value("key1", "value1"),
                    set_key_value("key2", "value2"),
                    set_key_value("key3", "value3")
                ]
                results = await asyncio.gather(*tasks)

                for result in results:
                    assert result["set"] is True

            await run_concurrent()


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "--tb=short"])
