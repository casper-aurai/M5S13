# Task Master Integration Server Documentation

## Overview

The Task Master Integration Server connects the MCP ecosystem with GitHub Issues for seamless task management and tracking. It provides bidirectional synchronization between internal task management and GitHub Issues, enabling AI agents to create, track, and manage tasks while maintaining consistency across systems.

## Features

- **Complete Task Lifecycle**: Create, read, update, delete tasks with full metadata
- **GitHub Integration**: Bidirectional sync with GitHub Issues using GitHub CLI
- **Webhook Support**: Real-time GitHub event processing for automatic updates
- **Bulk Operations**: Mass task creation and updates for efficiency
- **Migration Tools**: Import existing GitHub issues as tasks
- **Status Mapping**: Automatic conversion between task and issue states
- **Priority Management**: Intelligent priority mapping from labels
- **Audit Trail**: Complete tracking of task changes and GitHub sync

## Quick Start

### Basic Usage

```python
from servers.task_master_integration_server import TaskMasterIntegrationMCPServer

# Initialize server with GitHub integration
server = TaskMasterIntegrationMCPServer(
    github_token=os.getenv("GITHUB_TOKEN"),
    github_repo="myorg/myproject",
    enable_webhooks=True
)

# Setup task management tools
await server.setup_tools()

# Start server with WebSocket transport
server.transport_type = "websocket"
server.websocket_port = 8084
await server.start()
```

### Command Line Usage

```bash
# Start with GitHub integration
python servers/task_master_integration_server.py --github-repo myorg/myproject

# Specify custom GitHub token
python servers/task_master_integration_server.py --github-token $GITHUB_TOKEN --github-repo myorg/myproject

# Enable webhooks for real-time updates
python servers/task_master_integration_server.py --github-repo myorg/myproject --webhook-port 8083
```

## Available Tools

### 1. task_create
Create a new task.

**Parameters:**
- `title` (string): Task title (required)
- `description` (string): Task description (required)
- `priority` (string): Task priority (low, medium, high, urgent) (default: medium)
- `labels` (array): Task labels (optional)
- `assignee` (string): GitHub username to assign (optional)
- `github_issue` (boolean): Create GitHub issue (default: true)
- `created_by` (string): Task creator (required)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "task_create",
    "arguments": {
      "title": "Implement user authentication",
      "description": "Add OAuth2 authentication with JWT tokens",
      "priority": "high",
      "labels": ["feature", "authentication", "security"],
      "assignee": "dev-team",
      "created_by": "product-manager"
    }
  }
}
```

### 2. task_get
Get a specific task.

**Parameters:**
- `task_id` (string): Task ID (required)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "task_get",
    "arguments": {
      "task_id": "550e8400-e29b-41d4-a716-446655440000"
    }
  }
}
```

### 3. task_update
Update an existing task.

**Parameters:**
- `task_id` (string): Task ID (required)
- `title` (string): Updated title (optional)
- `description` (string): Updated description (optional)
- `status` (string): Updated status (todo, in_progress, in_review, completed, cancelled) (optional)
- `priority` (string): Updated priority (optional)
- `labels` (array): Updated labels (optional)
- `assignee` (string): Updated assignee (optional)
- `updated_by` (string): User making update (required)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "task_update",
    "arguments": {
      "task_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "in_progress",
      "assignee": "developer-john",
      "updated_by": "scrum-master"
    }
  }
}
```

### 4. task_delete
Delete a task.

**Parameters:**
- `task_id` (string): Task ID (required)
- `deleted_by` (string): User deleting task (required)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "task_delete",
    "arguments": {
      "task_id": "550e8400-e29b-41d4-a716-446655440000",
      "deleted_by": "product-manager"
    }
  }
}
```

### 5. task_list
List tasks with filtering and pagination.

**Parameters:**
- `status` (string): Filter by status (optional)
- `priority` (string): Filter by priority (optional)
- `labels` (array): Filter by labels (optional)
- `assignee` (string): Filter by assignee (optional)
- `github_issue` (boolean): Filter by GitHub issue presence (optional)
- `limit` (integer): Maximum results (default: 100, max: 1000)
- `offset` (integer): Pagination offset (default: 0)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "task_list",
    "arguments": {
      "status": "in_progress",
      "priority": "high",
      "assignee": "dev-team",
      "limit": 20,
      "offset": 0
    }
  }
}
```

### 6. task_sync_github
Sync tasks with GitHub issues.

**Parameters:**
- `direction` (string): Sync direction (to_github, from_github, bidirectional) (default: bidirectional)
- `force` (boolean): Force sync even if no changes (default: false)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "task_sync_github",
    "arguments": {
      "direction": "bidirectional",
      "force": false
    }
  }
}
```

### 7. task_github_create
Create GitHub issue from task.

**Parameters:**
- `task_id` (string): Task ID (required)
- `repo` (string): GitHub repository (owner/repo) (optional, uses default if not specified)
- `created_by` (string): User creating issue (required)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "task_github_create",
    "arguments": {
      "task_id": "550e8400-e29b-41d4-a716-446655440000",
      "repo": "myorg/myproject",
      "created_by": "developer"
    }
  }
}
```

### 8. task_github_update
Update GitHub issue from task.

**Parameters:**
- `task_id` (string): Task ID (required)
- `updated_by` (string): User updating issue (required)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "task_github_update",
    "arguments": {
      "task_id": "550e8400-e29b-41d4-a716-446655440000",
      "updated_by": "developer"
    }
  }
}
```

### 9. task_bulk_create
Create multiple tasks.

**Parameters:**
- `tasks` (array): List of task objects (required)
- `created_by` (string): User creating tasks (required)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "task_bulk_create",
    "arguments": {
      "tasks": [
        {
          "title": "Setup CI/CD pipeline",
          "description": "Configure automated testing and deployment",
          "priority": "high",
          "labels": ["infrastructure", "automation"]
        },
        {
          "title": "Update documentation",
          "description": "Refresh API documentation",
          "priority": "medium",
          "labels": ["documentation"]
        }
      ],
      "created_by": "project-manager"
    }
  }
}
```

### 10. task_bulk_update
Update multiple tasks.

**Parameters:**
- `updates` (array): List of task updates (required)
- `updated_by` (string): User making updates (required)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "task_bulk_update",
    "arguments": {
      "updates": [
        {
          "task_id": "550e8400-e29b-41d4-a716-446655440000",
          "status": "completed"
        },
        {
          "task_id": "550e8400-e29b-41d4-a716-446655440001",
          "priority": "urgent"
        }
      ],
      "updated_by": "scrum-master"
    }
  }
}
```

### 11. task_migrate_from_issues
Migrate existing GitHub issues to tasks.

**Parameters:**
- `repo` (string): GitHub repository (owner/repo) (optional)
- `labels` (array): Filter by labels (optional)
- `state` (string): Filter by state (open, closed, all) (default: open)
- `limit` (integer): Maximum issues to migrate (default: 100, max: 1000)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "task_migrate_from_issues",
    "arguments": {
      "repo": "myorg/myproject",
      "labels": ["bug", "enhancement"],
      "state": "open",
      "limit": 50
    }
  }
}
```

## GitHub Integration

### Setup Requirements

1. **GitHub CLI**: Install and authenticate with `gh auth login`
2. **Repository Access**: Ensure GitHub token has repo and issues permissions
3. **Webhook Configuration**: Configure GitHub webhooks for real-time updates

### GitHub CLI Authentication

```bash
# Login to GitHub
gh auth login

# Set default repository context
gh repo set-default myorg/myproject

# Test authentication
gh issue list --limit 1
```

### Webhook Configuration

Configure GitHub webhook in your repository:

- **Payload URL**: `http://your-server:8083/webhooks/github`
- **Content type**: `application/json`
- **Events**: Issues, Issue comments
- **Secret**: Optional for signature verification

## Task States and Mapping

### Status Mapping

| Task Status | GitHub State | Description |
|-------------|--------------|-------------|
| `todo` | open | Task created but not started |
| `in_progress` | open | Active development |
| `in_review` | open | Ready for review |
| `completed` | closed | Work finished |
| `cancelled` | closed | Task cancelled |

### Priority Mapping

| Task Priority | GitHub Labels | Description |
|---------------|---------------|-------------|
| `low` | low | Nice to have |
| `medium` | (none) | Standard priority |
| `high` | high | Important |
| `urgent` | urgent | Critical |

## Webhook Events

The server processes these GitHub webhook events:

### Issues Events
- `opened`: New issue created
- `edited`: Issue content updated
- `closed`: Issue closed (marks task as completed)
- `reopened`: Issue reopened (marks task as todo)

### Issue Comment Events
- `created`: New comment added
- `edited`: Comment content updated

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
  "server_name": "task_master_integration"
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
  "registered_tools": 11,
  "server_name": "task_master_integration",
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
    "code": "GITHUB_ERROR",
    "message": "Failed to create GitHub issue",
    "data": {
      "details": "Repository not found"
    }
  }
}
```

### Common Error Codes

- `TASK_NOT_FOUND`: Specified task doesn't exist
- `GITHUB_ERROR`: GitHub API or CLI error
- `GITHUB_REQUIRED`: GitHub repository or token required
- `INVALID_PARAMS`: Missing or invalid parameters

## Security Considerations

### GitHub Authentication
- **Token Security**: Use fine-grained personal access tokens
- **Repository Access**: Limit token scope to required repositories
- **Webhook Verification**: Implement webhook signature verification for production

### Data Protection
- **Task Privacy**: Tasks may contain sensitive project information
- **Access Control**: Implement proper authentication for task access
- **Audit Logging**: All task operations are logged for compliance

### Best Practices

1. **Token Management**: Use environment variables for GitHub tokens
2. **Repository Scope**: Limit token access to specific repositories
3. **Webhook Security**: Verify webhook signatures in production
4. **Error Handling**: Implement proper error handling for GitHub API failures

## Development

### Prerequisites

- **GitHub CLI**: Install and authenticate with `gh auth login`
- **Repository Access**: GitHub token with issues and repo permissions
- **Python Dependencies**: aiofiles, aiohttp for webhooks

### GitHub Token Setup

```bash
# Create fine-grained token
gh auth refresh -h github.com -s repo,issues

# Test token permissions
gh issue list --limit 1
```

### Webhook Setup

```bash
# Test webhook endpoint
curl -X POST http://localhost:8083/webhooks/github \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: issues" \
  -d '{"action": "opened", "issue": {"number": 123}}'
```

## Troubleshooting

### Common Issues

1. **"GitHub CLI not authenticated"**
   - Run `gh auth login` to authenticate
   - Verify token has required permissions
   - Check `gh auth status` for current authentication state

2. **"Repository not found"**
   - Verify repository exists and is accessible
   - Check repository name format (owner/repo)
   - Ensure token has access to the repository

3. **"Webhook delivery failed"**
   - Verify webhook URL is accessible from GitHub
   - Check firewall and network configuration
   - Ensure webhook port is not blocked

4. **"Task not found"**
   - Verify task ID format (UUID)
   - Check if task was deleted or never created
   - Use `task_list` to see available tasks

### Debug Mode

Enable debug logging:

```python
import logging
logging.getLogger("task_master").setLevel(logging.DEBUG)
```

## Production Deployment

### Systemd Service

```ini
[Unit]
Description=Task Master Integration Server
After=network.target

[Service]
Type=simple
User=task-user
ExecStart=/usr/bin/python /path/to/servers/task_master_integration_server.py --github-repo myorg/myproject
Restart=always
Environment=GITHUB_TOKEN=${GITHUB_TOKEN}

[Install]
WantedBy=multi-user.target
```

### Docker Container

```dockerfile
FROM python:3.11-slim

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

COPY servers/ /app/servers/

WORKDIR /app
EXPOSE 8083 8084

CMD ["python", "servers/task_master_integration_server.py", "--github-repo", "myorg/myproject"]
```

## Integration Examples

### Sprint Planning

```json
{
  "method": "tools/call",
  "params": {
    "name": "task_bulk_create",
    "arguments": {
      "tasks": [
        {
          "title": "Implement user dashboard",
          "description": "Create responsive user dashboard with charts",
          "priority": "high",
          "labels": ["frontend", "ui/ux"]
        },
        {
          "title": "Add payment processing",
          "description": "Integrate Stripe payment gateway",
          "priority": "medium",
          "labels": ["backend", "payments"]
        }
      ],
      "created_by": "product-owner"
    }
  }
}
```

### Issue Migration

```json
{
  "method": "tools/call",
  "params": {
    "name": "task_migrate_from_issues",
    "arguments": {
      "repo": "myorg/legacy-project",
      "labels": ["bug", "enhancement"],
      "state": "open",
      "limit": 100
    }
  }
}
```

### Status Updates

```json
{
  "method": "tools/call",
  "params": {
    "name": "task_bulk_update",
    "arguments": {
      "updates": [
        {
          "task_id": "550e8400-e29b-41d4-a716-446655440000",
          "status": "in_review"
        },
        {
          "task_id": "550e8400-e29b-41d4-a716-446655440001",
          "status": "completed"
        }
      ],
      "updated_by": "scrum-master"
    }
  }
}
```

## Performance Considerations

### Resource Usage
- **Memory**: ~30-60MB per server instance
- **Network**: GitHub API rate limits (5000 requests/hour for authenticated users)
- **Storage**: Scales with number of tasks

### Optimization Tips
1. **Batch Operations**: Use bulk tools for multiple operations
2. **Webhook Filtering**: Process only relevant webhook events
3. **Error Handling**: Implement retry logic for transient failures
4. **Caching**: Cache GitHub API responses when possible

## Contributing

When extending the Task Master Integration Server:

1. Follow the existing tool registration pattern in `setup_tools()`
2. Implement proper parameter validation for all inputs
3. Add comprehensive error handling with meaningful messages
4. Include integration tests for new functionality
5. Update this documentation with new features

## License

This Task Master Integration Server is part of the larger MCP ecosystem and follows the same licensing terms.
