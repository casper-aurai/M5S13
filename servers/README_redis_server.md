# Redis MCP Server Documentation

## Overview

The Redis MCP Server provides comprehensive key-value store operations through the Model Context Protocol (MCP). It enables AI agents to manage ephemeral state, coordinate between agents, and maintain session data using Redis as a backend. This server is specifically designed for agent state management and inter-agent communication without accessing business-critical data.

## Features

- **Complete Redis Operations**: Full key-value, list, and hash operations with serialization
- **Session Management**: Built-in session handling for AI agent state persistence
- **TTL Support**: Automatic expiration for ephemeral data with configurable TTL
- **Connection Pooling**: Efficient Redis connection management with health monitoring
- **Data Serialization**: Automatic JSON serialization/deserialization for complex data types
- **Error Recovery**: Robust error handling with automatic reconnection
- **Health & Metrics**: Built-in health checks and operational monitoring

## Quick Start

### Basic Usage

```python
from servers.redis_server import RedisMCPServer

# Initialize server with Redis connection
server = RedisMCPServer(
    redis_url="redis://localhost:6379",
    db=1,  # Use database 1 for agent data
    max_connections=10
)

# Setup Redis tools
await server.setup_tools()

# Start server with stdio transport
server.transport_type = "stdio"
await server.start()
```

### Command Line Usage

```bash
# Start with default Redis connection
python servers/redis_server.py --transport stdio

# Connect to custom Redis instance
python servers/redis_server.py --redis-url redis://redis.example.com:6379 --db 2

# Use WebSocket transport for real-time operations
python servers/redis_server.py --transport websocket --port 8920
```

## Available Tools

### 1. redis_get
Get value by key.

**Parameters:**
- `key` (string): Key to retrieve (required)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "redis_get",
    "arguments": {
      "key": "user:preferences"
    }
  }
}
```

### 2. redis_set
Set key-value pair with optional TTL.

**Parameters:**
- `key` (string): Key to set (required)
- `value` (any): Value to store (required)
- `ttl` (integer): Time-to-live in seconds (optional)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "redis_set",
    "arguments": {
      "key": "session:abc123",
      "value": {"user_id": "user456", "preferences": {"theme": "dark"}},
      "ttl": 3600
    }
  }
}
```

### 3. redis_del
Delete one or more keys.

**Parameters:**
- `keys` (array): Keys to delete (required)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "redis_del",
    "arguments": {
      "keys": ["temp:data", "cache:old", "session:expired"]
    }
  }
}
```

### 4. redis_exists
Check if keys exist.

**Parameters:**
- `keys` (array): Keys to check (required)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "redis_exists",
    "arguments": {
      "keys": ["user:123", "config:app", "cache:recent"]
    }
  }
}
```

### 5. redis_keys
Get all keys matching pattern.

**Parameters:**
- `pattern` (string): Pattern to match (default: "*")
- `count` (integer): Maximum keys to return (default: 100, max: 1000)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "redis_keys",
    "arguments": {
      "pattern": "session:*",
      "count": 50
    }
  }
}
```

### 6. redis_ttl
Get TTL for key.

**Parameters:**
- `key` (string): Key to check (required)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "redis_ttl",
    "arguments": {
      "key": "session:abc123"
    }
  }
}
```

### 7. redis_lpush
Push values to front of list.

**Parameters:**
- `key` (string): List key (required)
- `values` (array): Values to push (required)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "redis_lpush",
    "arguments": {
      "key": "task:queue",
      "values": ["task1", "task2", "task3"]
    }
  }
}
```

### 8. redis_rpush
Push values to end of list.

**Parameters:**
- `key` (string): List key (required)
- `values` (array): Values to push (required)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "redis_rpush",
    "arguments": {
      "key": "notifications",
      "values": ["Welcome!", "New feature available"]
    }
  }
}
```

### 9. redis_lpop
Pop values from front of list.

**Parameters:**
- `key` (string): List key (required)
- `count` (integer): Number of items to pop (default: 1)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "redis_lpop",
    "arguments": {
      "key": "task:queue",
      "count": 5
    }
  }
}
```

### 10. redis_hset
Set field in hash.

**Parameters:**
- `key` (string): Hash key (required)
- `field` (string): Field name (required)
- `value` (any): Field value (required)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "redis_hset",
    "arguments": {
      "key": "user:profile",
      "field": "preferences",
      "value": {"theme": "dark", "language": "en"}
    }
  }
}
```

### 11. redis_hget
Get field from hash.

**Parameters:**
- `key` (string): Hash key (required)
- `field` (string): Field name (required)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "redis_hget",
    "arguments": {
      "key": "user:profile",
      "field": "preferences"
    }
  }
}
```

### 12. redis_hgetall
Get all fields from hash.

**Parameters:**
- `key` (string): Hash key (required)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "redis_hgetall",
    "arguments": {
      "key": "user:profile"
    }
  }
}
```

## Session Management Tools

### 13. redis_session_create
Create a new session for AI agent state.

**Parameters:**
- `session_id` (string): Session ID (auto-generated if not provided)
- `data` (object): Initial session data (optional)
- `ttl` (integer): Session TTL in seconds (default: 3600)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "redis_session_create",
    "arguments": {
      "data": {
        "user_id": "agent123",
        "conversation_id": "conv456",
        "context": {"current_task": "analyze_code"}
      },
      "ttl": 7200
    }
  }
}
```

### 14. redis_session_get
Get session data.

**Parameters:**
- `session_id` (string): Session ID (required)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "redis_session_get",
    "arguments": {
      "session_id": "sess_abc123"
    }
  }
}
```

### 15. redis_session_update
Update session data.

**Parameters:**
- `session_id` (string): Session ID (required)
- `data` (object): Data to update (required)
- `extend_ttl` (boolean): Extend session TTL (default: true)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "redis_session_update",
    "arguments": {
      "session_id": "sess_abc123",
      "data": {
        "current_task": "generate_tests",
        "progress": 0.5
      }
    }
  }
}
```

### 16. redis_session_delete
Delete session.

**Parameters:**
- `session_id` (string): Session ID (required)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "redis_session_delete",
    "arguments": {
      "session_id": "sess_abc123"
    }
  }
}
```

## Health & Metrics

### Health Check
```bash
curl http://localhost:8080/health
```

Response:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "uptime_seconds": 3600,
  "version": "1.0.0",
  "server_name": "redis"
}
```

### Metrics
```bash
curl http://localhost:8080/metrics
```

Response:
```json
{
  "uptime_seconds": 3600,
  "total_requests": 150,
  "total_errors": 2,
  "active_sessions": 3,
  "registered_tools": 16,
  "server_name": "redis",
  "version": "1.0.0",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## Error Handling

The server provides structured error responses:

```json
{
  "jsonrpc": "2.0",
  "id": "request-id",
  "error": {
    "code": "REDIS_ERROR",
    "message": "Failed to get key",
    "data": {
      "details": "Connection timeout"
    }
  }
}
```

### Common Error Codes

- `REDIS_NOT_CONNECTED`: Redis server not accessible
- `SESSION_NOT_FOUND`: Specified session doesn't exist
- `REDIS_ERROR`: General Redis operation failure
- `INVALID_PARAMS`: Missing or invalid parameters

## Security Considerations

### Data Isolation
- **Database Separation**: Uses separate Redis database (default: db 1) for agent data
- **Key Namespacing**: All keys use consistent naming patterns (e.g., `mcp_session:*`)
- **TTL Enforcement**: Automatic expiration prevents data accumulation

### Connection Security
- **Connection Pooling**: Efficient connection reuse with configurable limits
- **Authentication**: Supports Redis AUTH and TLS encryption
- **Network Security**: Configurable Redis URL for secure connections

### Best Practices

1. **Session TTL**: Always set appropriate TTL for session data
2. **Key Naming**: Use consistent naming conventions for keys
3. **Connection Limits**: Configure appropriate connection pool sizes
4. **Error Handling**: Implement proper error handling for Redis operations

## Development

### Prerequisites

- **Redis Server**: Redis must be installed and running
- **Python Dependencies**: Install from `servers/requirements.txt`
- **Network Access**: Ensure network connectivity to Redis instance

### Redis Configuration

```bash
# Check Redis status
redis-cli ping

# Check Redis configuration
redis-cli info server

# Test connection
redis-cli -h localhost -p 6379 ping
```

### Connection Examples

```python
# Local Redis
server = RedisMCPServer(redis_url="redis://localhost:6379", db=1)

# Remote Redis with authentication
server = RedisMCPServer(
    redis_url="redis://:password@redis.example.com:6379",
    db=2
)

# Redis with TLS
server = RedisMCPServer(
    redis_url="rediss://:password@redis.example.com:6380",
    db=1
)
```

## Troubleshooting

### Common Issues

1. **"Redis client not connected"**
   - Verify Redis is running: `redis-cli ping`
   - Check network connectivity: `redis-cli -h <host> -p <port> ping`
   - Ensure Redis accepts connections on specified port

2. **"Session not found"**
   - Check if session exists: Use `redis_session_get` first
   - Verify session ID format and TTL hasn't expired
   - Check Redis logs for key expiration events

3. **Connection timeout**
   - Increase connection timeout in Redis configuration
   - Check network latency and Redis server load
   - Verify firewall rules allow Redis connections

4. **Memory issues**
   - Monitor Redis memory usage: `redis-cli info memory`
   - Configure appropriate `maxmemory` and eviction policy
   - Use appropriate TTL values for ephemeral data

### Debug Mode

Enable debug logging:

```python
import logging
logging.getLogger("redis").setLevel(logging.DEBUG)
```

## Production Deployment

### Systemd Service

```ini
[Unit]
Description=Redis MCP Server
After=redis.service

[Service]
Type=simple
User=redis-user
ExecStart=/usr/bin/python /path/to/servers/redis_server.py --transport websocket --port 8920
Restart=always
Environment=REDIS_URL=redis://localhost:6379

[Install]
WantedBy=multi-user.target
```

### Docker Container

```dockerfile
FROM python:3.11-slim

RUN apt-get update && apt-get install -y redis-tools && rm -rf /var/lib/apt/lists/*

COPY servers/ /app/servers/
COPY servers/requirements.txt /app/

WORKDIR /app
RUN pip install -r requirements.txt

# Expose WebSocket port
EXPOSE 8920

CMD ["python", "servers/redis_server.py", "--transport", "websocket", "--port", "8920"]
```

## Integration Examples

### Agent State Management

```json
{
  "method": "tools/call",
  "params": {
    "name": "redis_session_create",
    "arguments": {
      "data": {
        "agent_id": "code-analyzer-001",
        "current_task": "analyze_repository",
        "context": {
          "repository": "/path/to/repo",
          "branch": "main",
          "files_analyzed": 0
        }
      },
      "ttl": 7200
    }
  }
}
```

### Task Queue Management

```json
{
  "method": "tools/call",
  "params": {
    "name": "redis_rpush",
    "arguments": {
      "key": "task:queue",
      "values": ["analyze_code", "generate_tests", "deploy_service"]
    }
  }
}
```

### Configuration Storage

```json
{
  "method": "tools/call",
  "params": {
    "name": "redis_hset",
    "arguments": {
      "key": "app:config",
      "field": "database",
      "value": {
        "host": "localhost",
        "port": 5432,
        "name": "production"
      }
    }
  }
}
```

## Performance Considerations

### Resource Usage
- **Memory**: ~20-50MB per server instance
- **CPU**: Minimal overhead for JSON-RPC processing
- **Network**: Efficient Redis protocol with connection pooling

### Optimization Tips
1. **Connection Pooling**: Reuse Redis connections for better performance
2. **Batch Operations**: Use Redis pipelines for multiple operations
3. **TTL Management**: Set appropriate expiration times for data
4. **Key Patterns**: Use efficient key patterns for Redis operations

## Contributing

When extending the Redis MCP Server:

1. Follow the existing tool registration pattern in `setup_tools()`
2. Implement proper parameter validation for all inputs
3. Add comprehensive error handling with meaningful messages
4. Include integration tests for new functionality
5. Update this documentation with new features

## License

This Redis MCP Server is part of the larger MCP ecosystem and follows the same licensing terms.
