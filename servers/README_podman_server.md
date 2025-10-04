# Podman MCP Server Documentation

## Overview

The Podman MCP Server provides comprehensive container orchestration capabilities through the Model Context Protocol (MCP). It enables AI agents to manage Podman containers and pods for dynamic deployment of development environments, testing containers, and service containers while maintaining security and operational control.

## Features

- **Complete Container Lifecycle**: Create, start, stop, and manage containers with full configuration options
- **Image Management**: Pull, list, and inspect container images from registries
- **Advanced Filtering**: Sophisticated container and image filtering by status, labels, names
- **Real-time Operations**: WebSocket transport for live container monitoring and log streaming
- **Compose Support**: Framework for Docker Compose integration
- **Health & Metrics**: Built-in health checks and operational monitoring
- **Error Recovery**: Robust error handling with detailed reporting

## Quick Start

### Basic Usage

```python
from servers.podman_server import PodmanMCPServer

# Initialize server with Podman socket path
server = PodmanMCPServer(socket_path="/run/user/1000/podman/podman.sock")

# Setup container management tools
await server.setup_tools()

# Start server with WebSocket transport (recommended for containers)
server.transport_type = "websocket"
server.websocket_port = 8913
await server.start()
```

### Command Line Usage

```bash
# Start with WebSocket transport (recommended for real-time container ops)
python servers/podman_server.py --transport websocket --port 8913

# Specify custom socket path
python servers/podman_server.py --socket-path /custom/path/podman.sock

# Use stdio transport for simple operations
python servers/podman_server.py --transport stdio
```

## Available Tools

### 1. podman_ps
List and filter containers.

**Parameters:**
- `all` (boolean): Show all containers including stopped (default: false)
- `filters` (object): Filter containers by criteria
  - `status` (string): Filter by status (running, exited, etc.)
  - `name` (string): Filter by container name
  - `label` (string): Filter by label
- `limit` (integer): Maximum number of containers (default: 50, max: 100)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "podman_ps",
    "arguments": {
      "all": true,
      "filters": {
        "status": "running",
        "name": "web"
      },
      "limit": 20
    }
  }
}
```

### 2. podman_run
Create and run a new container.

**Parameters:**
- `image` (string): Container image to run (required)
- `name` (string): Container name (optional)
- `command` (array): Command to execute (optional)
- `env` (array): Environment variables (KEY=VALUE format)
- `ports` (array): Port mappings (HOST:CONTAINER format)
- `volumes` (array): Volume mounts (HOST:CONTAINER format)
- `detach` (boolean): Run in background (default: true)
- `restart` (string): Restart policy (no, always, on-failure, unless-stopped)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "podman_run",
    "arguments": {
      "image": "nginx:latest",
      "name": "web-server",
      "ports": ["8080:80"],
      "volumes": ["/host/data:/container/data"],
      "env": ["NGINX_PORT=80"],
      "detach": true,
      "restart": "always"
    }
  }
}
```

### 3. podman_stop
Stop one or more containers.

**Parameters:**
- `containers` (array): Container names or IDs to stop (required)
- `timeout` (integer): Timeout in seconds (default: 10)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "podman_stop",
    "arguments": {
      "containers": ["web-server", "db-container"],
      "timeout": 30
    }
  }
}
```

### 4. podman_start
Start one or more containers.

**Parameters:**
- `containers` (array): Container names or IDs to start (required)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "podman_start",
    "arguments": {
      "containers": ["web-server", "cache-service"]
    }
  }
}
```

### 5. podman_logs
Get logs from containers.

**Parameters:**
- `container` (string): Container name or ID (required)
- `tail` (integer): Number of lines to show (default: 100)
- `since` (string): Show logs since timestamp (optional)
- `follow` (boolean): Follow log output (default: false)
- `timestamps` (boolean): Show timestamps (default: false)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "podman_logs",
    "arguments": {
      "container": "web-server",
      "tail": 50,
      "timestamps": true
    }
  }
}
```

### 6. podman_inspect
Get detailed container information.

**Parameters:**
- `container` (string): Container name or ID (required)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "podman_inspect",
    "arguments": {
      "container": "web-server"
    }
  }
}
```

### 7. podman_images
List and filter container images.

**Parameters:**
- `all` (boolean): Show all images including intermediate (default: false)
- `filters` (object): Filter images by criteria
  - `reference` (string): Filter by image reference
  - `label` (string): Filter by label

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "podman_images",
    "arguments": {
      "all": true,
      "filters": {
        "reference": "nginx"
      }
    }
  }
}
```

### 8. podman_pull
Pull an image from a registry.

**Parameters:**
- `image` (string): Image to pull (name:tag format) (required)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "podman_pull",
    "arguments": {
      "image": "docker.io/library/redis:7-alpine"
    }
  }
}
```

### 9. podman_compose_up
Start services from a compose file.

**Parameters:**
- `file` (string): Compose file path (default: docker-compose.yml)
- `project_name` (string): Project name (optional)
- `detach` (boolean): Run in background (default: true)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "podman_compose_up",
    "arguments": {
      "file": "docker-compose.prod.yml",
      "project_name": "myapp-production",
      "detach": true
    }
  }
}
```

### 10. podman_compose_down
Stop services from a compose file.

**Parameters:**
- `file` (string): Compose file path (default: docker-compose.yml)
- `project_name` (string): Project name (optional)
- `volumes` (boolean): Remove volumes (default: false)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "podman_compose_down",
    "arguments": {
      "project_name": "myapp-production",
      "volumes": true
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
  "server_name": "podman"
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
  "registered_tools": 10,
  "server_name": "podman",
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
    "code": "PODMAN_ERROR",
    "message": "Failed to start container",
    "data": {
      "details": "Container already exists"
    }
  }
}
```

### Common Error Codes

- `PODMAN_NOT_CONNECTED`: Podman daemon not accessible
- `INVALID_CONTAINER_NAME`: Invalid container name format
- `CONTAINER_NOT_FOUND`: Specified container doesn't exist
- `PODMAN_ERROR`: General Podman operation failure
- `INVALID_PARAMS`: Missing or invalid parameters

## Security Considerations

### Socket Access
- Requires access to Podman socket (typically `/run/user/*/podman/podman.sock`)
- Socket permissions should be restricted to authorized users only
- Consider using user-specific sockets for multi-user environments

### Container Validation
- All container names and IDs are validated before operations
- Image references are validated to prevent malicious pulls
- Resource limits should be enforced at the Podman daemon level

### Best Practices

1. **Socket Security**: Use user-specific Podman sockets when possible
2. **Resource Limits**: Configure container resource limits in Podman daemon
3. **Image Verification**: Validate image sources before pulling
4. **Network Policies**: Use Podman networks for container isolation

## Development

### Prerequisites

- **Podman**: Container engine must be installed and running
- **Socket Access**: User must have access to Podman socket
- **Python Dependencies**: Install from `servers/requirements.txt`

### Socket Configuration

```bash
# Check socket path
podman info | grep -A 5 "remoteSocket"

# Common socket locations:
# - /run/user/$(id -u)/podman/podman.sock (user-specific)
# - /run/podman/podman.sock (system-wide, requires root)
```

### Testing

```python
# Test Podman connectivity
import podman

client = podman.PodmanClient(base_url="unix:///run/user/1000/podman/podman.sock")
containers = client.containers.list()
print(f"Found {len(containers)} containers")
```

## Troubleshooting

### Common Issues

1. **"Podman client not connected"**
   - Verify Podman daemon is running: `systemctl status podman`
   - Check socket path exists: `ls -la /run/user/$(id -u)/podman/`
   - Ensure socket permissions: `ls -la /run/user/$(id -u)/podman/podman.sock`

2. **"Container already exists"**
   - Use different container name or remove existing container first
   - Check with `podman_ps` to see existing containers

3. **Permission denied**
   - Ensure user has access to Podman socket
   - Try: `podman system connection add dev unix:///run/user/$(id -u)/podman/podman.sock`

4. **Image pull failures**
   - Check registry access: `podman pull hello-world`
   - Verify image name format: `registry.com/image:tag`

### Debug Mode

Enable debug logging:

```python
import logging
logging.getLogger("podman").setLevel(logging.DEBUG)
```

## Production Deployment

### Systemd Service

```ini
[Unit]
Description=Podman MCP Server
After=podman.service

[Service]
Type=simple
User=podman-user
ExecStart=/usr/bin/python /path/to/servers/podman_server.py --transport websocket --port 8913
Restart=always

[Install]
WantedBy=multi-user.target
```

### Docker Container

```dockerfile
FROM python:3.11-slim

RUN apt-get update && apt-get install -y podman && rm -rf /var/lib/apt/lists/*

COPY servers/ /app/servers/
COPY servers/requirements.txt /app/

WORKDIR /app
RUN pip install -r requirements.txt

# Expose WebSocket port
EXPOSE 8913

CMD ["python", "servers/podman_server.py", "--transport", "websocket", "--port", "8913"]
```

## Integration Examples

### Development Environment Setup

```json
{
  "method": "tools/call",
  "params": {
    "name": "podman_run",
    "arguments": {
      "image": "python:3.11",
      "name": "dev-env",
      "volumes": ["/host/project:/workspace"],
      "ports": ["8080:8080"],
      "command": ["tail", "-f", "/dev/null"],
      "env": ["PYTHONPATH=/workspace"]
    }
  }
}
```

### Service Deployment

```json
{
  "method": "tools/call",
  "params": {
    "name": "podman_run",
    "arguments": {
      "image": "nginx:alpine",
      "name": "web-service",
      "ports": ["80:80"],
      "restart": "always",
      "detach": true
    }
  }
}
```

## Performance Considerations

### Resource Usage
- **Memory**: ~50-100MB per server instance
- **CPU**: Minimal overhead for JSON-RPC processing
- **Network**: WebSocket for real-time operations, HTTP for health/metrics

### Optimization Tips
1. **Connection Pooling**: Reuse Podman client connections
2. **Container Limits**: Set appropriate resource limits for containers
3. **Image Caching**: Use local registries for frequently used images
4. **Batch Operations**: Group multiple container operations when possible

## Contributing

When extending the Podman MCP Server:

1. Follow the existing tool registration pattern in `setup_tools()`
2. Implement proper parameter validation for all inputs
3. Add comprehensive error handling with meaningful messages
4. Include integration tests for new functionality
5. Update this documentation with new features

## License

This Podman MCP Server is part of the larger MCP ecosystem and follows the same licensing terms.
