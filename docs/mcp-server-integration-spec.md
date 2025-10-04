# MCP Server Integration Specification

## Overview

This document defines the architecture and implementation requirements for integrating Model Context Protocol (MCP) servers into the AI agent ecosystem. The specification ensures unified tool access, secure sandboxing, and consistent operational patterns across all MCP servers.

## Goals

1. **Unified Tool Interface**: All MCP servers provide specific tool methods that agents can call via standardized configuration
2. **Flexible Transport**: Support multiple transport mechanisms (stdio, WebSocket, HTTP/SSE)
3. **Security First**: Implement sandboxing, minimal permissions, and safe operational boundaries
4. **Operational Resilience**: Handle server startup ordering and retry logic gracefully

## MCP Server Registry

### Core Servers

| Server | Purpose | Key Tools | Transport | Sandbox Constraints |
|--------|---------|-----------|-----------|-------------------|
| **filesystem** | Read/write repository files | `fs_read`, `fs_write`, `fs_list`, `fs_search` | stdio/WebSocket | Rooted at workspace, no path escapes |
| **git** | Repository operations | `git_status`, `git_diff`, `git_commit`, `git_add`, `git_branch`, `git_log`, `git_checkout` | stdio/WebSocket | Limited to local repository only |
| **fetch** | HTTP health/smoke checks | `http_get`, `http_post`, `http_health` | stdio/WebSocket | Whitelist internal services (127.0.0.1) |
| **redis** | Key-value store/coordination | `redis_get`, `redis_set`, `redis_del`, `redis_keys` | stdio/WebSocket | Ephemeral agent state only |

### Infrastructure Servers

| Server | Purpose | Key Tools | Transport | Sandbox Constraints |
|--------|---------|-----------|-----------|-------------------|
| **podman** | Container orchestration | `podman_ps`, `podman_logs`, `podman_compose_up`, `podman_compose_down` | WebSocket/HTTP | Podman socket access, project containers only |
| **sequential-thinking** | Chain-of-thought guidance | `sequential_thinking`, `thought_create`, `thought_complete` | stdio/WebSocket | Stateful sessions by ID |
| **task-master** | Issue/task orchestration | `task_create`, `task_list`, `task_update`, `task_link` | stdio/WebSocket | Internal task database |
| **http-mcp** | Local HTTP endpoint wrapper | `http_get`, `endpoint_call` | WebSocket/stdio | Whitelist pattern matching |

## Server Implementation Requirements

### Transport Specifications

#### Stdio Transport
- **Process-based**: Server runs as child process
- **Communication**: JSON-RPC over stdin/stdout
- **Startup**: Command + arguments execution
- **Example**:
  ```json
  {
    "command": "./venv/bin/python",
    "args": ["servers/fs_server.py"],
    "env": { "MCP_FS_ROOT": "${workspaceFolder}" }
  }
  ```

#### WebSocket Transport
- **Network-based**: Server runs as WebSocket server
- **Communication**: JSON-RPC over WebSocket
- **Ports**: Configurable per server (e.g., 8911-8913)
- **Example**:
  ```json
  {
    "transport": "websocket",
    "url": "ws://127.0.0.1:8913"
  }
  ```

#### HTTP/SSE Transport (Future)
- **REST-based**: HTTP endpoints with Server-Sent Events
- **Communication**: REST + SSE for real-time updates
- **Authentication**: Bearer tokens or API keys

### Security Constraints

#### Filesystem Server
```bash
# Allowed operations only within workspace root
MCP_FS_ROOT="${workspaceFolder}"
# No parent directory traversal (../)
# No absolute paths outside root
# Read-only by default, write requires explicit permission
```

#### Git Server
```bash
# Repository root constraint
MCP_GIT_ROOT="${workspaceFolder}"
# Operations limited to git repository boundaries
# No access to other repositories
```

#### Podman Server
```bash
# Socket connection only
PODMAN_SOCKET="/run/user/$(id -u)/podman/podman.sock"
# Container/project isolation
# No access to host processes
```

#### Fetch Server
```bash
# Internal services only
FETCH_WHITELIST="127.0.0.1:8080,127.0.0.1:3000,localhost:891*"
# No external HTTP calls
# Timeout constraints (5-30s)
```

## Configuration Schema

### Windsurf/Claude Configuration

```json
{
  "mcpServers": {
    "filesystem": {
      "transport": "stdio",
      "command": "./venv/bin/python",
      "args": ["servers/filesystem_server.py"],
      "env": {
        "MCP_FS_ROOT": "${workspaceFolder}",
        "MCP_FS_READONLY": "false"
      }
    },
    "git": {
      "transport": "stdio",
      "command": "./venv/bin/python",
      "args": ["servers/git_server.py"],
      "env": {
        "MCP_GIT_ROOT": "${workspaceFolder}"
      }
    },
    "redis": {
      "transport": "stdio",
      "command": "./venv/bin/python",
      "args": ["servers/redis_server.py"],
      "env": {
        "REDIS_URL": "redis://localhost:6379",
        "REDIS_DB": "1"
      }
    },
    "fetch": {
      "transport": "stdio",
      "command": "./venv/bin/python",
      "args": ["servers/fetch_server.py"],
      "env": {
        "FETCH_WHITELIST": "127.0.0.1:8080,127.0.0.1:3000"
      }
    },
    "podman": {
      "transport": "websocket",
      "url": "ws://127.0.0.1:8913",
      "env": {
        "PODMAN_SOCKET": "/run/user/$(id -u)/podman/podman.sock"
      }
    },
    "sequential-thinking": {
      "transport": "websocket",
      "url": "ws://127.0.0.1:8911"
    },
    "task-master": {
      "transport": "stdio",
      "command": "npx",
      "args": ["task-master-ai"],
      "env": {
        "TASK_DB_PATH": "./data/tasks.db"
      }
    }
  }
}
```

## Server Development Guidelines

### Tool Interface Standard

Each tool must implement:
```typescript
interface MCPTool {
  name: string;
  description: string;
  inputSchema: JSONSchema;
  handler: (params: any) => Promise<any>;
}
```

### Error Handling

```typescript
// Standard error responses
{
  "error": {
    "code": "PERMISSION_DENIED",
    "message": "Access denied to path outside workspace",
    "data": { "requested_path": "/etc/passwd" }
  }
}
```

### Health Checks

All servers must implement:
- **Health endpoint**: `GET /health` or `{"method": "health"}`
- **Readiness probe**: Verify dependencies are available
- **Liveness probe**: Verify server is responsive

## Implementation Roadmap

### Phase 1: Core Infrastructure
1. **Filesystem Server** - Basic file operations with sandboxing
2. **Git Server** - Repository operations
3. **Configuration System** - Unified MCP client setup

### Phase 2: Coordination Services
4. **Redis Server** - State management and coordination
5. **Fetch Server** - Internal HTTP service testing
6. **Sequential Thinking Server** - Chain-of-thought guidance

### Phase 3: Advanced Integration
7. **Podman Server** - Container orchestration
8. **Task Master Server** - Issue/task management
9. **HTTP-MCP Server** - Local endpoint integration

## Testing Strategy

### Unit Tests
- Tool method validation
- Error condition handling
- Sandbox boundary testing

### Integration Tests
- Full MCP client/server communication
- Multi-server scenarios
- Startup/shutdown sequences

### Security Tests
- Sandbox escape attempts
- Permission boundary validation
- Resource limit enforcement

## Monitoring and Observability

### Metrics
- Request/response times
- Error rates by tool
- Connection counts
- Resource utilization

### Logging
- Structured JSON logs
- Request tracing IDs
- Security event logging
- Performance monitoring

## Deployment Considerations

### Development Environment
- All servers run locally
- Stdio for simple servers
- WebSocket for stateful servers
- Hot-reload capability

### Production Environment
- Containerized deployment
- Service discovery
- Health check integration
- Graceful shutdown handling

---

*This specification serves as the foundation for implementing a robust, secure, and scalable MCP server ecosystem.*
