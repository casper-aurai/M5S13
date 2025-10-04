# Filesystem MCP Server Documentation

## Overview

The Filesystem MCP Server provides secure file system operations through the Model Context Protocol (MCP). It enables AI agents to read, write, and manage files within designated workspace boundaries while enforcing strict sandboxing to prevent access outside the workspace root and maintain security.

## Features

- **Secure File Operations**: Read, write, and delete files with workspace sandboxing
- **Directory Management**: List contents with recursive traversal options
- **Advanced Search**: Glob pattern matching for file discovery
- **File Information**: Detailed metadata and MIME type detection
- **Safety Controls**: Size limits, encoding validation, and permission checks
- **Batch Operations**: Efficient handling of multiple file operations
- **Cross-Platform**: Works on Windows, macOS, and Linux

## Security Features

### Workspace Sandboxing
- **Root Boundary**: All operations confined to workspace root directory
- **Path Validation**: Prevents directory traversal attacks (`../`)
- **Absolute Path Checking**: Validates all paths are within workspace
- **Permission Enforcement**: Read/write permission validation

### File Safety
- **Size Limits**: Maximum file size prevents memory exhaustion
- **Encoding Validation**: Proper encoding handling with error detection
- **Content Validation**: Input sanitization and validation
- **Atomic Operations**: Safe file operations with rollback on errors

## Quick Start

### Basic Usage

```python
from servers.filesystem_server import FilesystemMCPServer

# Initialize server with workspace root
server = FilesystemMCPServer(
    workspace_root="/path/to/your/workspace",
    readonly=False
)

# Setup filesystem tools
await server.setup_tools()

# Start server with stdio transport
server.transport_type = "stdio"
await server.start()
```

### Command Line Usage

```bash
# Start with current directory as workspace
python servers/filesystem_server.py --transport stdio

# Specify custom workspace root
python servers/filesystem_server.py --workspace-root /path/to/project

# Run in read-only mode for safety
python servers/filesystem_server.py --workspace-root /path/to/project --readonly

# Use WebSocket transport for advanced operations
python servers/filesystem_server.py --workspace-root /path/to/project --transport websocket --port 8905
```

## Available Tools

### 1. fs_read
Read file contents with optional line range specification.

**Parameters:**
- `path` (string): File path relative to workspace root (required)
- `encoding` (string): File encoding (default: utf-8)
- `start_line` (integer): Starting line number (1-indexed, optional)
- `end_line` (integer): Ending line number (inclusive, optional)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "fs_read",
    "arguments": {
      "path": "src/main.py",
      "encoding": "utf-8"
    }
  }
}
```

Read specific lines:
```json
{
  "method": "tools/call",
  "params": {
    "name": "fs_read",
    "arguments": {
      "path": "config/app.yaml",
      "start_line": 10,
      "end_line": 20
    }
  }
}
```

### 2. fs_write
Write content to a file.

**Parameters:**
- `path` (string): File path relative to workspace root (required)
- `content` (string): Content to write (required)
- `encoding` (string): File encoding (default: utf-8)
- `mode` (string): Write mode (overwrite or append) (default: overwrite)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "fs_write",
    "arguments": {
      "path": "docs/README.md",
      "content": "# Project Documentation\n\nThis is the main documentation file.",
      "mode": "overwrite"
    }
  }
}
```

Append to existing file:
```json
{
  "method": "tools/call",
  "params": {
    "name": "fs_write",
    "arguments": {
      "path": "logs/app.log",
      "content": "INFO: Application started successfully\n",
      "mode": "append"
    }
  }
}
```

### 3. fs_list
List directory contents with optional recursion.

**Parameters:**
- `path` (string): Directory path (default: root)
- `recursive` (boolean): List recursively (default: false)
- `show_hidden` (boolean): Include hidden files (default: false)
- `max_depth` (integer): Maximum recursion depth (optional)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "fs_list",
    "arguments": {
      "path": "src",
      "recursive": true,
      "show_hidden": false
    }
  }
}
```

### 4. fs_stat
Get detailed information about a file or directory.

**Parameters:**
- `path` (string): Path to check (required)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "fs_stat",
    "arguments": {
      "path": "package.json"
    }
  }
}
```

### 5. fs_search
Search for files and directories using glob patterns.

**Parameters:**
- `pattern` (string): Glob pattern (e.g., `*.py`, `**/*.md`) (required)
- `path` (string): Directory to search (default: root)
- `max_results` (integer): Maximum results (default: 100, max: 1000)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "fs_search",
    "arguments": {
      "pattern": "*.py",
      "path": "src",
      "max_results": 50
    }
  }
}
```

### 6. fs_delete
Delete a file or directory.

**Parameters:**
- `path` (string): Path to delete (required)
- `recursive` (boolean): Delete directory recursively (default: false)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "fs_delete",
    "arguments": {
      "path": "temp/cache.dat"
    }
  }
}
```

Delete directory with contents:
```json
{
  "method": "tools/call",
  "params": {
    "name": "fs_delete",
    "arguments": {
      "path": "old_build",
      "recursive": true
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
  "server_name": "filesystem"
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
  "server_name": "filesystem",
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
    "code": "PATH_OUTSIDE_WORKSPACE",
    "message": "Path outside workspace boundaries",
    "data": {
      "path": "/etc/passwd",
      "workspace_root": "/path/to/workspace"
    }
  }
}
```

### Common Error Codes

- `PATH_OUTSIDE_WORKSPACE`: Path not within workspace root
- `NOT_A_FILE`: Path exists but is not a file
- `NOT_A_DIRECTORY`: Path exists but is not a directory
- `FILE_TOO_LARGE`: File exceeds size limit
- `READ_PERMISSION_DENIED`: No read permission for path
- `WRITE_PERMISSION_DENIED`: No write permission for path

## Security Considerations

### Workspace Boundaries
- **Strict Sandboxing**: All operations confined to workspace root
- **Path Traversal Protection**: Prevents `../` directory traversal attacks
- **Absolute Path Validation**: Ensures all paths are within workspace
- **Symlink Restrictions**: Handles symlinks within workspace safely

### File Safety
- **Size Limits**: Prevents memory exhaustion from large files
- **Encoding Validation**: Proper character encoding with error detection
- **Content Sanitization**: Input validation and sanitization
- **Permission Checks**: OS-level permission validation

### Best Practices

1. **Workspace Selection**: Choose appropriate workspace root for operations
2. **Path Validation**: Always validate paths before operations
3. **Size Awareness**: Check file sizes for large operations
4. **Backup Strategy**: Implement backups for critical files

## Development

### Prerequisites

- **File System Access**: Read/write permissions in workspace
- **Python Pathlib**: For cross-platform path handling
- **MIME Type Detection**: For file type identification

### Configuration Examples

```python
# Development workspace
dev_server = FilesystemMCPServer(
    workspace_root="./",
    readonly=False  # Allow write operations
)

# Production workspace (read-only)
prod_server = FilesystemMCPServer(
    workspace_root="/app",
    readonly=True  # Prevent modifications
)
```

### Path Resolution

All paths are resolved relative to the workspace root:
```python
# Workspace root: /home/user/project
# Request path: "src/main.py"
# Resolved path: /home/user/project/src/main.py

# Request path: "../outside.txt"  # ❌ BLOCKED
# Request path: "/etc/passwd"     # ❌ BLOCKED
```

## Troubleshooting

### Common Issues

1. **"Path outside workspace boundaries"**
   - Ensure path is relative to workspace root
   - Avoid absolute paths or paths with `../`
   - Use `fs_stat` to verify path exists and permissions

2. **"File too large"**
   - Check file size before reading large files
   - Use line range parameters for large files
   - Increase `max_file_size` if necessary

3. **"Permission denied"**
   - Verify OS permissions for workspace files
   - Check if running as appropriate user
   - Use read-only mode if write access not needed

4. **"Directory not empty"**
   - Use `recursive=true` for non-empty directories
   - Move or backup important files first
   - Verify directory contents before deletion

### Debug Mode

Enable debug logging:

```python
import logging
logging.getLogger("filesystem").setLevel(logging.DEBUG)
```

## Production Deployment

### Systemd Service

```ini
[Unit]
Description=Filesystem MCP Server
After=local-fs.target

[Service]
Type=simple
User=app-user
ExecStart=/usr/bin/python /path/to/servers/filesystem_server.py --workspace-root /app/workspace
Restart=always
ReadWritePaths=/app/workspace

[Install]
WantedBy=multi-user.target
```

### Docker Container

```dockerfile
FROM python:3.11-slim

COPY servers/ /app/servers/
WORKDIR /app

# Create workspace directory
RUN mkdir -p /workspace
VOLUME /workspace

EXPOSE 8905

CMD ["python", "servers/filesystem_server.py", "--workspace-root", "/workspace"]
```

## Integration Examples

### Code Analysis Workflow

```json
{
  "method": "tools/call",
  "params": {
    "name": "fs_search",
    "arguments": {
      "pattern": "**/*.py",
      "path": "src",
      "max_results": 100
    }
  }
}
```

### Documentation Generation

```json
{
  "method": "tools/call",
  "params": {
    "name": "fs_read",
    "arguments": {
      "path": "README.md"
    }
  }
}
```

### Configuration Management

```json
{
  "method": "tools/call",
  "params": {
    "name": "fs_write",
    "arguments": {
      "path": "config/production.json",
      "content": "{\n  \"database_url\": \"postgresql://...\",\n  \"api_key\": \"...\"\n}",
      "mode": "overwrite"
    }
  }
}
```

### File Backup Operations

```json
{
  "method": "tools/call",
  "params": {
    "name": "fs_list",
    "arguments": {
      "path": "data",
      "recursive": true
    }
  }
}
```

## Performance Considerations

### Resource Usage
- **Memory**: Scales with file size and operation complexity
- **I/O**: File system operations may be I/O bound
- **CPU**: Minimal for most operations

### Optimization Tips
1. **Batch Operations**: Group related file operations
2. **Size Validation**: Check file sizes before large reads
3. **Line Ranges**: Use line ranges for large file access
4. **Search Optimization**: Use specific patterns to limit search scope

## Contributing

When extending the Filesystem MCP Server:

1. Follow the existing tool registration pattern in `setup_tools()`
2. Implement proper parameter validation for all inputs
3. Add comprehensive error handling with meaningful messages
4. Include integration tests for new functionality
5. Update this documentation with new features

## License

This Filesystem MCP Server is part of the larger MCP ecosystem and follows the same licensing terms.
