# ADR-0004: Git MCP Server Architecture and Implementation

## Status
Accepted

## Context
The project requires comprehensive Git repository management capabilities for AI agents to perform version control operations safely and efficiently. The initial analysis showed a need for git operations that maintain repository integrity while providing secure boundaries for AI agent interactions.

## Decision
Implement a dedicated Git MCP Server that provides comprehensive git operations through the Model Context Protocol (MCP) framework. This server will:

1. Provide a complete set of git operations (status, diff, commit, branch, log, etc.)
2. Implement strict repository boundary validation to prevent operations outside the designated repository
3. Use safe command execution patterns to prevent injection attacks
4. Support both stdio and WebSocket transport mechanisms for maximum compatibility
5. Maintain backward compatibility with existing git workflows

## Consequences

### Positive
- **Security**: Repository boundary validation prevents unauthorized file access
- **Reliability**: Safe command execution prevents git repository corruption
- **Flexibility**: Multiple transport options support various deployment scenarios
- **Maintainability**: Clean separation between git operations and transport layer
- **Extensibility**: Modular design allows easy addition of new git operations

### Negative
- **Dependency**: Requires git to be installed and accessible on the system
- **Performance**: Subprocess calls add slight overhead compared to direct git operations
- **Complexity**: Additional abstraction layer between AI agents and git commands

## Implementation Approach

### Core Architecture
```
┌─────────────────┐    ┌──────────────────┐    ┌────────────────┐
│   MCP Client    │◄──►│  Git MCP Server  │◄──►│   Git Repo     │
│   (AI Agent)    │    │                  │    │                │
└─────────────────┘    │ • Tool Registry  │    │ • Boundary     │
                       │ • Request Handler│    │   Validation   │
┌─────────────────┐    │ • Safe Execution │    │ • Command      │
│   Transport     │◄──►│ • Error Handling │    │   Execution    │
│   (stdio/ws)    │    │ • Repository     │    │ • Status       │
└─────────────────┘    │   Management     │    │   Parsing      │
                       └──────────────────┘    └────────────────┘
```

### Key Components

#### 1. Repository Boundary Validation
```python
def validate_repo_path(self, path: str) -> Path:
    """Ensure all operations stay within repository boundaries."""
    resolved_path = Path(path).resolve()
    if not resolved_path.is_relative_to(self.repo_root):
        raise MCPError("INVALID_PATH", "Path outside repository")
    return resolved_path
```

#### 2. Safe Git Command Execution
```python
def run_git_command(self, cmd: List[str]) -> Tuple[str, str, int]:
    """Execute git commands safely with proper error handling."""
    try:
        result = subprocess.run(
            ['git'] + cmd,
            cwd=self.repo_root,
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except subprocess.TimeoutExpired:
        raise MCPError("COMMAND_TIMEOUT", "Git command timed out")
```

#### 3. Comprehensive Tool Set
- **git_status**: Repository status with porcelain and human-readable formats
- **git_diff**: Show differences between commits, branches, or staged changes
- **git_commit**: Create commits with validation and support for amending
- **git_add**: Stage files with force option for ignored files
- **git_branch**: Complete branch lifecycle management (create, switch, delete, list)
- **git_log**: Commit history with filtering and formatting options
- **git_checkout**: Branch and file checkout operations
- **git_remote**: Remote repository management

#### 4. Transport Layer Support
- **stdio**: Direct process communication for local usage
- **WebSocket**: Network-based communication for distributed deployments

### Security Considerations

#### Repository Isolation
- All file paths are validated against the repository root
- Absolute path resolution prevents directory traversal attacks
- Git commands are executed within the repository directory only

#### Command Injection Prevention
- All git commands use parameterized subprocess calls
- User input is validated and sanitized before execution
- No shell interpretation of git commands

#### Error Information Limiting
- Error messages are sanitized to prevent information disclosure
- Repository structure details are not exposed in error responses

## Implementation Status
✅ **Core Implementation Complete** - All git tools implemented with comprehensive error handling
✅ **Security Features** - Repository boundary validation and safe command execution
✅ **Transport Support** - Both stdio and WebSocket transports functional
✅ **Dependencies** - GitPython and subprocess management properly integrated

## Future Enhancements
- [ ] Integration with Git LFS for large file support
- [ ] Git hooks integration for automated workflows
- [ ] Advanced merge conflict resolution tools
- [ ] GitHub/GitLab integration for remote operations
- [ ] Performance optimizations for large repositories

## Migration Strategy
This is a new service implementation, so no existing system migration is required. The Git MCP Server can be deployed alongside existing git workflows without disruption.

## Rollback Plan
If issues arise with the MCP-based approach, the architecture supports:
1. Direct git command execution as a fallback option
2. Gradual rollout starting with read-only operations
3. Easy removal of MCP layer if needed

## Notes
- The Git MCP Server assumes git is installed and properly configured
- Repository must be initialized before server startup
- All git operations are logged for audit purposes
- Server supports both interactive and automated usage patterns
