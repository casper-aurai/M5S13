# MCP Servers Directory

This directory contains implementations of Model Context Protocol (MCP) servers that provide specific tool capabilities to AI agents.

## Server Implementations

Each server implements the MCP specification and provides a specific set of tools:

### Core Servers
- **filesystem_server.py** - File operations with workspace sandboxing
- **git_server.py** - Git repository operations
- **redis_server.py** - Key-value store for agent state
- **fetch_server.py** - HTTP client for internal service testing

### Infrastructure Servers
- **podman_server.py** - Container orchestration via Podman API
- **sequential_thinking_server.py** - Chain-of-thought session management
- **task_master_server.py** - Task and issue management
- **http_mcp_server.py** - HTTP endpoint wrapper with whitelisting

## Development Guidelines

### Transport Support
- **stdio**: For simple request/response tools
- **WebSocket**: For stateful or streaming operations
- **HTTP/SSE**: For web-based integrations (future)

### Security Requirements
- All servers must implement proper sandboxing
- Input validation and sanitization required
- No access to sensitive system resources
- Comprehensive error handling and logging

### Testing Requirements
- Unit tests for all tool methods
- Integration tests with MCP clients
- Security boundary testing
- Performance and load testing

## Getting Started

1. Install dependencies:
   ```bash
   pip install -r requirements-mcp.txt
   ```

2. Run a server:
   ```bash
   # Filesystem server (stdio)
   python servers/filesystem_server.py

   # Git server (WebSocket)
   python servers/git_server.py --port 8912
   ```

3. Configure in your MCP client:
   ```json
   {
     "mcpServers": {
       "filesystem": {
         "transport": "stdio",
         "command": "python",
         "args": ["servers/filesystem_server.py"]
       }
     }
   }
   ```

## Configuration

Each server supports configuration via:
- Environment variables (prefixed with server name)
- Command-line arguments
- Configuration files (YAML/JSON)

See individual server documentation for detailed configuration options.

## Monitoring

All servers provide:
- Health check endpoints (`/health`)
- Metrics collection (Prometheus compatible)
- Structured logging (JSON format)
- Graceful shutdown handling
