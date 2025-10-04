# Fetch MCP Server Documentation

## Overview

The Fetch MCP Server provides secure HTTP client capabilities through the Model Context Protocol (MCP). It enables AI agents to perform HTTP requests to internal services for health checks, smoke testing, and service integration while maintaining strict security boundaries through URL whitelisting and comprehensive safety controls.

## Features

- **Secure HTTP Operations**: GET and POST requests with strict URL validation
- **URL Whitelisting**: Configurable regex patterns for allowed endpoints
- **Health Checking**: Dedicated health check functionality with expected status codes
- **Response Validation**: Size limits and timeout controls to prevent resource exhaustion
- **SSL/TLS Security**: Configurable SSL verification and certificate validation
- **Error Recovery**: Comprehensive error handling with detailed reporting
- **Production Ready**: Robust timeout handling and connection management

## Security Features

### URL Whitelisting
- **Strict Validation**: Only whitelisted URLs are allowed
- **Regex Patterns**: Flexible pattern matching for endpoint authorization
- **Default Security**: Pre-configured for localhost/127.0.0.1 only
- **Pattern Compilation**: Runtime validation of whitelist patterns

### Request Safety
- **Size Limits**: Maximum response size prevents memory exhaustion
- **Timeout Controls**: Configurable request timeouts prevent hanging
- **Connection Limits**: HTTP client connection pooling and limits
- **SSL Verification**: Optional SSL certificate validation

## Quick Start

### Basic Usage

```python
from servers.fetch_server import FetchMCPServer

# Initialize server with custom whitelist
server = FetchMCPServer(
    whitelist_patterns=[
        r"^https?://127\.0\.0\.1:\d+/?$",
        r"^https?://localhost:\d+/?$",
        r"^https?://api\.internal:\d+/.*$"
    ],
    timeout=30,
    max_response_size=1024*1024  # 1MB
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
python servers/fetch_server.py --transport stdio

# Add custom whitelist patterns
python servers/fetch_server.py --whitelist "api.internal" "service.local" --timeout 60

# Use WebSocket transport for real-time operations
python servers/fetch_server.py --transport websocket --port 8910

# Allow insecure SSL connections (not recommended for production)
python servers/fetch_server.py --allow-insecure
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
      "url": "http://localhost:8080/api/health",
      "headers": {"Authorization": "Bearer token123"},
      "params": {"format": "json"},
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

### 3. http_health
Check if a service endpoint is healthy.

**Parameters:**
- `url` (string): URL to health check (must be whitelisted) (required)
- `expected_status` (integer): Expected HTTP status code (default: 200)
- `timeout` (integer): Request timeout in seconds (default: 10, max: 60)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "http_health",
    "arguments": {
      "url": "http://localhost:8080/health",
      "expected_status": 200,
      "timeout": 5
    }
  }
}
```

### 4. http_validate_url
Check if a URL is allowed by whitelist.

**Parameters:**
- `url` (string): URL to validate (required)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "http_validate_url",
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
    r"^https?://localhost:\d+/.*$"
]
```

### Custom Patterns
Configure custom patterns for your environment:

```python
# Internal API servers
patterns = [
    r"^https?://api\.internal:\d+/.*$",
    r"^https?://service\.local:\d+/.*$",
    r"^https?://10\.0\.1\.\d+:\d+/.*$"  # Internal network
]

server = FetchMCPServer(whitelist_patterns=patterns)
```

### Pattern Examples

```python
# Single endpoint
r"^https://api\.example\.com:443/health$"

# All endpoints on a service
r"^https://user-service:\d+/.*$"

# Multiple ports
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
  "server_name": "fetch"
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
  "registered_tools": 4,
  "server_name": "fetch",
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
    "code": "URL_NOT_ALLOWED",
    "message": "URL not allowed by whitelist",
    "data": {
      "url": "http://external-api.com/data",
      "whitelist_patterns": ["127.0.0.1", "localhost"]
    }
  }
}
```

### Common Error Codes

- `URL_NOT_ALLOWED`: URL not in whitelist
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
- **Size Limits**: Prevent memory exhaustion from large responses
- **Timeout Enforcement**: Prevent hanging requests
- **Connection Pooling**: Efficient HTTP client reuse
- **SSL Verification**: Optional certificate validation

### Best Practices

1. **Minimal Whitelist**: Only include necessary service endpoints
2. **Specific Patterns**: Use specific ports and paths when possible
3. **Regular Review**: Periodically audit allowed endpoints
4. **Network Segmentation**: Use internal networks for service communication

## Development

### Prerequisites

- **HTTPX Library**: Install httpx for HTTP client functionality
- **SSL Support**: OpenSSL for secure connections
- **Network Access**: Connectivity to target services

### Configuration Examples

```python
# Development environment
dev_server = FetchMCPServer(
    whitelist_patterns=[
        r"^https?://localhost:\d+/.*$",
        r"^https?://127\.0\.0\.1:\d+/.*$",
        r"^https?://.*\.local:\d+/.*$"
    ],
    timeout=60,
    allow_insecure=True  # For self-signed certificates
)

# Production environment
prod_server = FetchMCPServer(
    whitelist_patterns=[
        r"^https://api\.internal:443/.*$",
        r"^https://service1\.internal:443/.*$",
        r"^https://service2\.internal:443/.*$"
    ],
    timeout=30,
    max_response_size=512*1024,  # 512KB
    allow_insecure=False
)
```

## Troubleshooting

### Common Issues

1. **"URL not allowed by whitelist"**
   - Check URL against configured whitelist patterns
   - Verify URL format (http/https, port number)
   - Use `http_validate_url` to test URL before making requests

2. **"Request timeout"**
   - Increase timeout for slow services
   - Check network connectivity to target service
   - Verify service is running and accessible

3. **"Connection error"**
   - Verify service is running on specified port
   - Check firewall and network configuration
   - Ensure DNS resolution for hostnames

4. **"Response too large"**
   - Increase `max_response_size` if expecting large responses
   - Use pagination for large data sets
   - Implement streaming for very large responses

### Debug Mode

Enable debug logging:

```python
import logging
logging.getLogger("httpx").setLevel(logging.DEBUG)
logging.getLogger("fetch").setLevel(logging.DEBUG)
```

## Production Deployment

### Systemd Service

```ini
[Unit]
Description=Fetch MCP Server
After=network.target

[Service]
Type=simple
User=fetch-user
ExecStart=/usr/bin/python /path/to/servers/fetch_server.py --transport websocket --port 8910
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
EXPOSE 8910

CMD ["python", "servers/fetch_server.py", "--transport", "websocket", "--port", "8910"]
```

## Integration Examples

### Service Health Monitoring

```json
{
  "method": "tools/call",
  "params": {
    "name": "http_health",
    "arguments": {
      "url": "http://api.internal:8080/health",
      "expected_status": 200,
      "timeout": 5
    }
  }
}
```

### API Data Retrieval

```json
{
  "method": "tools/call",
  "params": {
    "name": "http_get",
    "arguments": {
      "url": "http://data-service:8080/api/users",
      "headers": {"Authorization": "Bearer ${API_TOKEN}"},
      "params": {"limit": "100", "format": "json"},
      "timeout": 15
    }
  }
}
```

### Webhook Testing

```json
{
  "method": "tools/call",
  "params": {
    "name": "http_post",
    "arguments": {
      "url": "http://webhook-service:8080/events",
      "json": {
        "event_type": "test_completed",
        "source": "mcp-agent",
        "data": {"test_id": "integration-test-001"}
      },
      "headers": {"X-Source": "mcp-fetch"},
      "timeout": 10
    }
  }
}
```

## Performance Considerations

### Resource Usage
- **Memory**: ~10-20MB per server instance
- **Network**: Efficient HTTP/2 support with connection reuse
- **CPU**: Minimal overhead for request processing

### Optimization Tips
1. **Connection Reuse**: HTTP client automatically reuses connections
2. **Timeout Tuning**: Set appropriate timeouts for service response times
3. **Batch Requests**: Use connection pooling for multiple requests
4. **Response Caching**: Cache health check results when appropriate

## Contributing

When extending the Fetch MCP Server:

1. Follow the existing tool registration pattern in `setup_tools()`
2. Implement proper parameter validation for all inputs
3. Add comprehensive error handling with meaningful messages
4. Include integration tests for new functionality
5. Update this documentation with new features

## License

This Fetch MCP Server is part of the larger MCP ecosystem and follows the same licensing terms.
