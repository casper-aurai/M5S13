# Git MCP Server Documentation

## Overview

The Git MCP Server provides comprehensive Git repository management capabilities through the Model Context Protocol (MCP). It enables AI agents to perform git operations safely while maintaining repository integrity and security boundaries.

## Features

- **Complete Git Operations**: Status, diff, commit, add, branch, log, checkout, remote management
- **Security Boundaries**: All operations are validated to stay within the repository
- **Safe Command Execution**: Prevents injection attacks and validates all inputs
- **Multiple Transport Modes**: stdio, WebSocket, and HTTP (for health/metrics)
- **Health & Metrics**: Built-in health checks and operational metrics
- **Error Handling**: Comprehensive error reporting with proper JSON-RPC formatting

## Quick Start

### Basic Usage

```python
from servers.git_server import GitMCPServer

# Initialize server with repository path
server = GitMCPServer("/path/to/your/repo")

# Setup tools (git operations)
await server.setup_tools()

# Start server with stdio transport
server.transport_type = "stdio"
await server.start()
```

### Command Line Usage

```bash
# Start with stdio transport (default)
python servers/git_server.py

# Start with WebSocket transport on port 8080
python servers/git_server.py --transport websocket --port 8080

# Specify custom repository path
python servers/git_server.py --repo-root /path/to/custom/repo
```

## Available Tools

### 1. git_status
Get repository status information.

**Parameters:**
- `porcelain` (boolean): Use porcelain format (default: false)
- `path` (string): Specific path to check (optional)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "git_status",
    "arguments": {
      "porcelain": true,
      "path": "src/"
    }
  }
}
```

### 2. git_add
Stage files for commit.

**Parameters:**
- `files` (array): List of files to stage
- `force` (boolean): Force add ignored files (default: false)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "git_add",
    "arguments": {
      "files": ["file1.txt", "file2.txt"],
      "force": false
    }
  }
}
```

### 3. git_commit
Create a commit.

**Parameters:**
- `message` (string): Commit message (required)
- `files` (array): Specific files to commit (optional)
- `amend` (boolean): Amend previous commit (default: false)
- `allow_empty` (boolean): Allow empty commit (default: false)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "git_commit",
    "arguments": {
      "message": "Add new feature implementation",
      "files": ["feature.py"],
      "amend": false
    }
  }
}
```

### 4. git_branch
Manage branches.

**Parameters:**
- `action` (string): "list", "create", "switch", "delete" (required)
- `name` (string): Branch name (required for create/switch/delete)
- `base` (string): Base branch for new branch (default: current)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "git_branch",
    "arguments": {
      "action": "create",
      "name": "feature-branch",
      "base": "main"
    }
  }
}
```

### 5. git_diff
Show differences.

**Parameters:**
- `commit1` (string): First commit (default: HEAD)
- `commit2` (string): Second commit (optional)
- `staged` (boolean): Show staged changes (default: false)
- `path` (string): Path to show diff for (optional)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "git_diff",
    "arguments": {
      "staged": true
    }
  }
}
```

### 6. git_log
Show commit history.

**Parameters:**
- `max_count` (integer): Maximum commits to show (default: 10)
- `path` (string): Path to filter history (optional)
- `author` (string): Filter by author (optional)
- `since` (string): Show commits since date (optional)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "git_log",
    "arguments": {
      "max_count": 5,
      "author": "john.doe@example.com"
    }
  }
}
```

### 7. git_checkout
Checkout branches or files.

**Parameters:**
- `branch` (string): Branch to checkout (optional)
- `files` (array): Files to checkout from index (optional)
- `create` (boolean): Create branch if it doesn't exist (default: false)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "git_checkout",
    "arguments": {
      "branch": "develop",
      "create": false
    }
  }
}
```

### 8. git_remote
Manage remote repositories.

**Parameters:**
- `action` (string): "list", "add", "remove" (required)
- `name` (string): Remote name (required for add/remove)
- `url` (string): Remote URL (required for add)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "git_remote",
    "arguments": {
      "action": "add",
      "name": "upstream",
      "url": "https://github.com/original/repo.git"
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
  "server_name": "git"
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
  "registered_tools": 8,
  "server_name": "git",
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
    "code": "INVALID_PARAMS",
    "message": "Parameter validation failed",
    "data": {
      "details": "Missing required parameter: message"
    }
  }
}
```

### Common Error Codes

- `INVALID_REQUEST`: Malformed request
- `INVALID_PARAMS`: Invalid or missing parameters
- `TOOL_NOT_FOUND`: Requested tool doesn't exist
- `TOOL_EXECUTION_ERROR`: Error during tool execution
- `INVALID_PATH`: Path outside repository boundaries
- `NO_CHANGES`: No staged changes to commit

## Security Considerations

### Repository Boundaries
All file operations are validated to ensure they stay within the repository root directory. This prevents:

- Access to files outside the repository
- Directory traversal attacks
- Unauthorized file system access

### Safe Command Execution
- All git commands use parameterized subprocess calls
- No shell interpretation of user input
- Command timeouts prevent hanging operations
- Input validation on all parameters

### Best Practices

1. **Repository Setup**: Ensure git is properly initialized before starting the server
2. **Path Validation**: Always validate paths before operations
3. **Error Handling**: Implement proper error handling for all operations
4. **Resource Limits**: Be aware of subprocess timeouts and resource usage

## Development

### Running Tests

```bash
# Run all tests
python test_git_server.py

# Run with verbose output
python test_git_server.py -v

# Run specific test class
python test_git_server.py::TestGitMCPServer -v
```

### Code Structure

```
servers/
├── git_server.py          # Main server implementation
├── base_mcp_server.py     # Base MCP framework
└── test_git_server.py     # Comprehensive test suite

docs/adr/
└── ADR-0004-git-mcp-server.md  # Architecture decision record
```

## Troubleshooting

### Common Issues

1. **"Not a git repository"**
   - Ensure the specified path contains a `.git` directory
   - Initialize the repository: `git init`

2. **"Path outside repository"**
   - Verify all file paths are within the repository root
   - Use relative paths when possible

3. **"No staged changes to commit"**
   - Stage files first using `git_add`
   - Check repository status with `git_status`

4. **Permission denied**
   - Ensure proper file permissions
   - Verify git user configuration

### Debug Mode

Enable debug logging for troubleshooting:

```python
import logging
logging.getLogger().setLevel(logging.DEBUG)
```

## Contributing

When extending the Git MCP Server:

1. Follow the existing tool registration pattern
2. Implement proper parameter validation
3. Add comprehensive error handling
4. Include tests for new functionality
5. Update this documentation

## License

This Git MCP Server is part of the larger MCP ecosystem and follows the same licensing terms.
