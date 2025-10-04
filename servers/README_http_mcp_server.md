# HTTP-MCP Wrapper Server Documentation

## Overview

The HTTP-MCP Wrapper Server provides secure HTTP client capabilities with full REST API support through the Model Context Protocol (MCP). It enables AI agents to perform comprehensive HTTP operations (GET, POST, PUT, DELETE) to internal services while maintaining strict security boundaries through URL whitelisting and advanced safety controls.

## Features

- **Full REST Operations**: GET, POST, PUT, DELETE with comprehensive parameter support
- **URL Whitelisting**: Configurable regex patterns for allowed endpoints
- **Concurrency Control**: Configurable concurrent request limits to prevent resource exhaustion
- **Health Checking**: Dedicated health check functionality with expected status codes
- **Response Validation**: Size limits and timeout controls for operational safety
- **SSL/TLS Security**: Configurable SSL verification and certificate validation
- **Connection Management**: Efficient HTTP client pooling and connection reuse

## Security Features

### URL Whitelisting
- **Strict Validation**: Only whitelisted URLs are allowed for requests
- **Regex Patterns**: Flexible pattern matching for endpoint authorization
- **Default Security**: Pre-configured for localhost/127.0.0.1/0.0.0.0 only
- **Pattern Compilation**: Runtime validation of whitelist patterns

### Request Safety
- **Concurrency Limits**: Maximum concurrent requests prevent system overload
- **Size Limits**: Maximum response size prevents memory exhaustion
- **Timeout Controls**: Configurable request timeouts prevent hanging
- **Connection Pooling**: Efficient HTTP client connection management

## Quick Start

### Basic Usage

```python
from servers.http_mcp_server import HTTPMCPWrapperServer

# Initialize server with custom whitelist
server = HTTPMCPWrapperServer(
    whitelist_patterns=[
        r"^https?://127\.0\.0\.1:\d+/.*$",
        r"^https?://localhost:\d+/.*$",
        r"^https?://api\.internal:\d+/.*$"
    ],
    timeout=30,
    max_response_size=1024*1024,  # 1MB
    max_concurrent_requests=10
)

# Setup HTTP tools
await server.setup_tools()

# Start server with stdio transport
server.transport_type = "stdio"
await server.start()
```

### Command Line Usage

```bash
# Start with default localhost-only whitelist
python servers/http_mcp_server.py --transport stdio

# Add custom whitelist patterns with concurrency control
python servers/http_mcp_server.py --whitelist "api.internal" "service.local" --max-concurrent-requests 5

# Use WebSocket transport for real-time operations
python servers/http_mcp_server.py --transport websocket --port 8911

# Configure for production with strict security
python servers/http_mcp_server.py --whitelist "api.production.internal" --timeout 15 --max-response-size 512000
```

## Available Tools

### 1. http_get
Perform HTTP GET request to whitelisted endpoint.

**Parameters:**
- `url` (string): URL to fetch (must be whitelisted) (required)
- `headers` (object): Additional HTTP headers (optional)
- `params` (object): Query parameters (optional)
- `timeout` (integer): Request timeout in seconds (default: 30, max: 300)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "http_get",
    "arguments": {
      "url": "http://localhost:8080/api/users",
      "headers": {"Authorization": "Bearer token123"},
      "params": {"limit": "100", "format": "json"},
      "timeout": 10
    }
  }
}
```

### 2. http_post
Perform HTTP POST request to whitelisted endpoint.

**Parameters:**
- `url` (string): URL to post to (must be whitelisted) (required)
- `data` (string): Raw data to send in request body (optional)
- `json` (object): JSON data to send (alternative to data) (optional)
- `headers` (object): Additional HTTP headers (optional)
- `timeout` (integer): Request timeout in seconds (default: 30, max: 300)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "http_post",
    "arguments": {
      "url": "http://localhost:8080/api/webhook",
      "json": {
        "event": "deployment_completed",
        "service": "user-api",
        "status": "success"
      },
      "headers": {"X-Source": "mcp-agent"},
      "timeout": 15
    }
  }
}
```

### 3. http_put
Perform HTTP PUT request to whitelisted endpoint.

**Parameters:**
- `url` (string): URL to put to (must be whitelisted) (required)
- `data` (string): Raw data to send in request body (optional)
- `json` (object): JSON data to send (alternative to data) (optional)
- `headers` (object): Additional HTTP headers (optional)
- `timeout` (integer): Request timeout in seconds (default: 30, max: 300)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "http_put",
    "arguments": {
      "url": "http://localhost:8080/api/users/123",
      "json": {
        "name": "Updated Name",
        "email": "updated@example.com"
      },
      "headers": {"Authorization": "Bearer token123"},
      "timeout": 10
    }
  }
}
```

### 4. http_delete
Perform HTTP DELETE request to whitelisted endpoint.

**Parameters:**
- `url` (string): URL to delete from (must be whitelisted) (required)
- `headers` (object): Additional HTTP headers (optional)
- `timeout` (integer): Request timeout in seconds (default: 30, max: 300)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "http_delete",
    "arguments": {
      "url": "http://localhost:8080/api/users/123",
      "headers": {"Authorization": "Bearer token123"},
      "timeout": 10
    }
  }
}
```

### 5. endpoint_health
Check if an endpoint is healthy and responding correctly.

**Parameters:**
- `url` (string): URL to health check (must be whitelisted) (required)
- `expected_status` (integer): Expected HTTP status code (default: 200)
- `timeout` (integer): Request timeout in seconds (default: 10, max: 60)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "endpoint_health",
    "arguments": {
      "url": "http://api.internal:8080/health",
      "expected_status": 200,
      "timeout": 5
    }
  }
}
```

### 6. validate_endpoint
Check if an endpoint is allowed by whitelist.

**Parameters:**
- `url` (string): URL to validate (required)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "validate_endpoint",
    "arguments": {
      "url": "http://localhost:8080/api/data"
    }
  }
}
```

## URL Whitelist Configuration

### Default Patterns
The server includes secure defaults for local development:
```python
default_patterns = [
    r"^https?://127\.0\.0\.1:\d+/?$",
    r"^https?://localhost:\d+/?$",
    r"^https?://127\.0\.0\.1:\d+/.*$",
    r"^https?://localhost:\d+/.*$",
    r"^https?://0\.0\.0\.0:\d+/?$",
    r"^https?://0\.0\.0\.0:\d+/.*$"
]
```

### Custom Patterns
Configure custom patterns for your environment:

```python
# Internal API servers
patterns = [
    r"^https://api\.internal:443/.*$",
    r"^https://service1\.internal:443/.*$",
    r"^http://localhost:(8080|8081|8082)/.*$"
]

server = HTTPMCPWrapperServer(whitelist_patterns=patterns)
```

### Pattern Examples

```python
# Single endpoint
r"^https://api\.example\.com:443/health$"

# All endpoints on a service
r"^https://user-service:\d+/.*$"

# Multiple ports on localhost
r"^http://localhost:(8080|8081|8082)/.*$"

# IP range (use with caution)
r"^https?://192\.168\.1\.\d+:\d+/.*$"
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
  "server_name": "http-mcp"
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
  "registered_tools": 6,
  "server_name": "http-mcp",
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
    "code": "ENDPOINT_NOT_ALLOWED",
    "message": "Endpoint not allowed by whitelist",
    "data": {
      "url": "http://external-api.com/data",
      "whitelist_patterns": ["127.0.0.1", "localhost"]
    }
  }
}
```

### Common Error Codes

- `ENDPOINT_NOT_ALLOWED`: URL not in whitelist
- `REQUEST_TIMEOUT`: Request exceeded timeout limit
- `CONNECTION_ERROR`: Failed to connect to endpoint
- `HTTP_ERROR`: HTTP error response (4xx, 5xx)
- `RESPONSE_TOO_LARGE`: Response exceeded size limit

## Security Considerations

### Whitelist Security
- **Principle of Least Privilege**: Only allow necessary endpoints
- **Pattern Validation**: All regex patterns are validated at startup
- **No External Access**: Default configuration blocks external APIs
- **IP Restrictions**: Use specific IP patterns for production

### Request Safety
- **Concurrency Control**: Maximum concurrent requests prevent system overload
- **Size Limits**: Prevents memory exhaustion from large responses
- **Timeout Enforcement**: Prevents hanging requests
- **Connection Pooling**: Efficient HTTP client connection management

### Best Practices

1. **Minimal Whitelist**: Only include necessary service endpoints
2. **Specific Patterns**: Use specific ports and paths when possible
3. **Concurrency Limits**: Set appropriate concurrent request limits
4. **Regular Review**: Periodically audit allowed endpoints

## Development

### Prerequisites

- **HTTPX Library**: Install httpx for HTTP client functionality
- **SSL Support**: OpenSSL for secure connections
- **Network Access**: Connectivity to target services

### Configuration Examples

```python
# Development environment
dev_server = HTTPMCPWrapperServer(
    whitelist_patterns=[
        r"^https?://localhost:\d+/.*$",
        r"^https?://127\.0\.0\.1:\d+/.*$"
    ],
    timeout=60,
    max_concurrent_requests=5,
    allow_insecure=True  # For self-signed certificates
)

# Production environment
prod_server = HTTPMCPWrapperServer(
    whitelist_patterns=[
        r"^https://api\.production\.internal:443/.*$",
        r"^https://service1\.internal:443/.*$"
    ],
    timeout=30,
    max_response_size=512*1024,  # 512KB
    max_concurrent_requests=20,
    allow_insecure=False
)
```

## Troubleshooting

### Common Issues

1. **"Endpoint not allowed by whitelist"**
   - Check URL against configured whitelist patterns
   - Verify URL format (http/https, port number)
   - Use `validate_endpoint` to test URL before making requests

2. **"Request timeout"**
   - Increase timeout for slow services
   - Check network connectivity to target service
   - Verify service is running and accessible

3. **"Connection error"**
   - Verify service is running on specified port
   - Check firewall and network configuration
   - Ensure DNS resolution for hostnames

4. **"Too many concurrent requests"**
   - Increase `max_concurrent_requests` if needed
   - Check if requests are hanging and not releasing semaphore
   - Implement proper error handling to ensure semaphore release

### Debug Mode

Enable debug logging:

```python
import logging
logging.getLogger("httpx").setLevel(logging.DEBUG)
logging.getLogger("http-mcp").setLevel(logging.DEBUG)
```

## Production Deployment

### Systemd Service

```ini
[Unit]
Description=HTTP-MCP Wrapper Server
After=network.target

[Service]
Type=simple
User=http-user
ExecStart=/usr/bin/python /path/to/servers/http_mcp_server.py --transport websocket --port 8911
Restart=always
Environment=WHITELIST="api.internal service.local"

[Install]
WantedBy=multi-user.target
```

### Docker Container

```dockerfile
FROM python:3.11-slim

RUN pip install httpx

COPY servers/ /app/servers/

WORKDIR /app
EXPOSE 8911

CMD ["python", "servers/http_mcp_server.py", "--transport", "websocket", "--port", "8911"]
```

## Integration Examples

### REST API Integration

```json
{
  "method": "tools/call",
  "params": {
    "name": "http_get",
    "arguments": {
      "url": "http://api.internal:8080/api/users",
      "headers": {"Authorization": "Bearer ${API_TOKEN}"},
      "params": {"limit": "100"},
      "timeout": 15
    }
  }
}
```

### Service Health Monitoring

```json
{
  "method": "tools/call",
  "params": {
    "name": "endpoint_health",
    "arguments": {
      "url": "http://api.internal:8080/health",
      "expected_status": 200,
      "timeout": 5
    }
  }
}
```

### CRUD Operations

```json
{
  "method": "tools/call",
  "params": {
    "name": "http_post",
    "arguments": {
      "url": "http://api.internal:8080/api/users",
      "json": {
        "name": "John Doe",
        "email": "john@example.com"
      },
      "timeout": 10
    }
  }
}
```

### Webhook Delivery

```json
{
  "method": "tools/call",
  "params": {
    "name": "http_post",
    "arguments": {
      "url": "http://webhook-service:8080/events",
      "json": {
        "event_type": "deployment_completed",
        "source": "mcp-agent",
        "data": {"deployment_id": "dep-001"}
      },
      "headers": {"X-Source": "mcp-http"},
      "timeout": 10
    }
  }
}
```

## Performance Considerations

### Resource Usage
- **Memory**: ~15-25MB per server instance
- **Network**: Efficient HTTP/2 support with connection reuse
- **CPU**: Minimal overhead for request processing
- **Concurrency**: Configurable concurrent request handling

### Optimization Tips
1. **Connection Reuse**: HTTP client automatically reuses connections
2. **Timeout Tuning**: Set appropriate timeouts for service response times
3. **Concurrency Limits**: Configure based on system capacity
4. **Response Caching**: Cache health check results when appropriate

## Contributing

When extending the HTTP-MCP Wrapper Server:

1. Follow the existing tool registration pattern in `setup_tools()`
2. Implement proper parameter validation for all inputs
3. Add comprehensive error handling with meaningful messages
4. Include integration tests for new functionality
5. Update this documentation with new features

## License

This HTTP-MCP Wrapper Server is part of the larger MCP ecosystem and follows the same licensing terms.
