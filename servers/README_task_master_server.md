# Task Master MCP Server Documentation

## Overview

The Task Master MCP Server provides comprehensive task and project management capabilities through the Model Context Protocol (MCP). It enables AI agents to create, track, and manage tasks with advanced features like dependency relationships, cascade rule automation, and SQLite-based persistence for reliable task coordination and project management.

## Features

- **Complete Task Lifecycle**: Create, read, update, delete tasks with full metadata
- **Project Management**: Organize tasks into projects with status tracking
- **Dependency Management**: Task relationships and blocking dependencies
- **Cascade Rules Integration**: Automatic subtask generation based on configurable rules
- **Database Persistence**: SQLite-based storage for reliability and performance
- **Advanced Filtering**: Multi-criteria task filtering and search
- **Label Management**: Flexible labeling system for task categorization
- **Status Tracking**: Comprehensive status management (open, in_progress, completed, cancelled)

## Architecture

### Database Schema
- **Tasks Table**: Stores all task information with relationships
- **Projects Table**: Project metadata and organization
- **Cascade Rules**: YAML-based automation rules for task generation
- **Relationships**: Parent-child and dependency relationships

### Cascade Rules Integration
- **Rule-Based Automation**: Automatically generates subtasks based on task properties
- **Component Matching**: Triggers based on task type, component, or content
- **Template Interpolation**: Dynamic task creation from rule templates
- **Dependency Linking**: Automatic relationship creation between tasks

## Quick Start

### Basic Usage

```python
from servers.task_master_server import TaskMasterMCPServer

# Initialize server with database
server = TaskMasterMCPServer(db_path="./data/tasks.db")

# Setup task management tools
await server.setup_tools()

# Start server with stdio transport
server.transport_type = "stdio"
await server.start()
```

### Command Line Usage

```bash
# Start with default database location
python servers/task_master_server.py --transport stdio

# Specify custom database path
python servers/task_master_server.py --db-path /path/to/tasks.db

# Use WebSocket transport for real-time operations
python servers/task_master_server.py --transport websocket --port 8907
```

## Available Tools

### 1. task_create
Create a new task with optional cascade rule processing.

**Parameters:**
- `title` (string): Task title (required)
- `description` (string): Task description (optional)
- `type` (string): Task type (task, issue, bug, feature, epic) (default: task)
- `priority` (string): Task priority (low, medium, high, critical) (default: medium)
- `assignee` (string): Task assignee (optional)
- `labels` (array): Task labels (optional)
- `project_id` (string): Project ID (optional)
- `parent_id` (string): Parent task ID for subtasks (optional)
- `depends_on` (array): Task IDs this task depends on (optional)
- `metadata` (object): Additional task metadata (optional)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "task_create",
    "arguments": {
      "title": "Implement user authentication system",
      "description": "Build OAuth2 authentication with JWT tokens and user management",
      "type": "feature",
      "priority": "high",
      "labels": ["backend", "security", "authentication"],
      "assignee": "dev-team-alpha",
      "metadata": {
        "estimated_hours": 40,
        "complexity": "high",
        "business_value": "critical"
      }
    }
  }
}
```

### 2. task_get
Get detailed task information.

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
Update task information and status.

**Parameters:**
- `task_id` (string): Task ID (required)
- `title` (string): Updated title (optional)
- `description` (string): Updated description (optional)
- `status` (string): Updated status (open, in_progress, completed, cancelled) (optional)
- `priority` (string): Updated priority (optional)
- `assignee` (string): Updated assignee (optional)
- `labels` (array): Updated labels (optional)
- `depends_on` (array): Updated dependencies (optional)
- `metadata` (object): Updated metadata (optional)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "task_update",
    "arguments": {
      "task_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "in_progress",
      "assignee": "developer-jane",
      "metadata": {
        "progress": 0.3,
        "last_worked": "2024-01-15T10:00:00Z"
      }
    }
  }
}
```

### 4. task_list
List tasks with advanced filtering.

**Parameters:**
- `status` (string): Filter by status (optional)
- `priority` (string): Filter by priority (optional)
- `assignee` (string): Filter by assignee (optional)
- `project_id` (string): Filter by project (optional)
- `parent_id` (string): Filter by parent task (optional)
- `labels` (array): Filter by labels (must have all specified) (optional)
- `limit` (integer): Maximum tasks to return (default: 50, max: 1000)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "task_list",
    "arguments": {
      "status": "in_progress",
      "priority": "high",
      "assignee": "dev-team-alpha",
      "limit": 20
    }
  }
}
```

### 5. task_delete
Delete a task and clean up relationships.

**Parameters:**
- `task_id` (string): Task ID to delete (required)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "task_delete",
    "arguments": {
      "task_id": "550e8400-e29b-41d4-a716-446655440000"
    }
  }
}
```

### 6. task_link
Create dependency relationships between tasks.

**Parameters:**
- `task_id` (string): Task ID (required)
- `depends_on` (array): Task IDs this task depends on (optional)
- `blocks` (array): Task IDs this task blocks (optional)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "task_link",
    "arguments": {
      "task_id": "550e8400-e29b-41d4-a716-446655440000",
      "depends_on": ["550e8400-e29b-41d4-a716-446655440001"],
      "blocks": ["550e8400-e29b-41d4-a716-446655440002"]
    }
  }
}
```

### 7. project_create
Create a new project for task organization.

**Parameters:**
- `name` (string): Project name (required)
- `description` (string): Project description (optional)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "project_create",
    "arguments": {
      "name": "E-commerce Platform",
      "description": "Complete e-commerce solution with user management, payments, and inventory"
    }
  }
}
```

### 8. project_list
List all projects with optional status filtering.

**Parameters:**
- `status` (string): Filter by status (active, completed, archived) (optional)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "project_list",
    "arguments": {
      "status": "active"
    }
  }
}
```

## Cascade Rules Integration

### Rule Configuration
Cascade rules are defined in `.windsurf/cascade-rules.yaml`:

```yaml
cascadeRules:
  - name: "Service Component Breakdown"
    trigger:
      whenTool: "task-master.task_create"
      condition:
        component: "service"
    actions:
      - createTask:
          description: "Set up service repository and structure"
          component: "repository"
          priority: "high"
          labels: ["infrastructure"]
      - createTask:
          description: "Implement service core functionality"
          component: "development"
          priority: "high"
          labels: ["backend", "core"]
```

### Automatic Task Generation
When a task matches cascade rule conditions, subtasks are automatically created:

```json
{
  "created": true,
  "task": {
    "id": "main-task-id",
    "title": "Deploy User Service",
    "type": "service"
  },
  "cascade_generated": 2,
  "cascade_tasks": [
    {
      "title": "Set up service repository and structure",
      "type": "repository",
      "parent_id": "main-task-id"
    },
    {
      "title": "Implement service core functionality",
      "type": "development",
      "parent_id": "main-task-id"
    }
  ]
}
```

## Task Relationships

### Dependency Types
- **depends_on**: Tasks that must be completed before this task
- **blocked_by**: Tasks that block this task from starting
- **subtasks**: Child tasks that belong to this task
- **parent_id**: Parent task for hierarchical organization

### Relationship Management
```json
{
  "method": "tools/call",
  "params": {
    "name": "task_link",
    "arguments": {
      "task_id": "database-setup",
      "depends_on": ["environment-setup"],
      "blocks": ["api-implementation", "testing-phase"]
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
  "server_name": "task-master"
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
  "server_name": "task-master",
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
    "code": "TASK_NOT_FOUND",
    "message": "Task not found",
    "data": {
      "task_id": "550e8400-e29b-41d4-a716-446655440000"
    }
  }
}
```

### Common Error Codes

- `TASK_NOT_FOUND`: Specified task doesn't exist
- `INVALID_PARENT`: Parent task not found for subtask creation
- `INVALID_PROJECT`: Project not found for task assignment
- `INVALID_DEPENDENCY`: Dependency task not found
- `DATABASE_ERROR`: Database operation failed

## Database Schema

### Tasks Table
```sql
CREATE TABLE tasks (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    type TEXT,
    component TEXT,
    priority TEXT,
    status TEXT,
    assignee TEXT,
    labels TEXT,           -- JSON array
    parent_id TEXT,
    project_id TEXT,
    created_at TEXT,
    updated_at TEXT,
    completed_at TEXT,
    metadata TEXT,         -- JSON object
    depends_on TEXT,       -- JSON array
    blocked_by TEXT,       -- JSON array
    subtasks TEXT          -- JSON array
);
```

### Projects Table
```sql
CREATE TABLE projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    status TEXT,
    created_at TEXT,
    updated_at TEXT
);
```

## Advanced Features

### Task Analytics
The server provides insights into task patterns:

```json
{
  "analytics": {
    "total_tasks": 150,
    "completed_tasks": 45,
    "in_progress_tasks": 25,
    "blocked_tasks": 5,
    "average_completion_time": "3.2 days",
    "priority_distribution": {
      "low": 20,
      "medium": 80,
      "high": 40,
      "critical": 10
    }
  }
}
```

### Dependency Graph
Tasks maintain dependency relationships for workflow management:

```json
{
  "task": {
    "id": "api-implementation",
    "depends_on": ["database-schema", "authentication-service"],
    "subtasks": ["endpoint-design", "validation-logic", "error-handling"]
  }
}
```

## Integration Examples

### Project Planning Workflow

```json
{
  "method": "tools/call",
  "params": {
    "name": "project_create",
    "arguments": {
      "name": "Mobile App Development",
      "description": "Cross-platform mobile application with user authentication and data sync"
    }
  }
}
```

### Sprint Management

```json
{
  "method": "tools/call",
  "params": {
    "name": "task_bulk_create",
    "arguments": {
      "tasks": [
        {
          "title": "User registration flow",
          "type": "feature",
          "priority": "high",
          "labels": ["frontend", "authentication"]
        },
        {
          "title": "Database schema design",
          "type": "task",
          "priority": "high",
          "labels": ["backend", "database"]
        }
      ]
    }
  }
}
```

### Dependency Management

```json
{
  "method": "tools/call",
  "params": {
    "name": "task_link",
    "arguments": {
      "task_id": "frontend-implementation",
      "depends_on": ["api-design", "database-schema"],
      "blocks": ["integration-testing", "deployment"]
    }
  }
}
```

## Cascade Rules Examples

### Service Component Rule
```yaml
- name: "Service Component Breakdown"
  trigger:
    whenTool: "task-master.task_create"
    condition:
      component: "service"
  actions:
    - createTask:
        description: "Set up service infrastructure"
        component: "infrastructure"
        priority: "high"
    - createTask:
        description: "Implement service logic"
        component: "development"
        priority: "high"
```

### Feature Development Rule
```yaml
- name: "Feature Development Workflow"
  trigger:
    whenTool: "task-master.task_create"
    condition:
      type: "feature"
  actions:
    - createTask:
        description: "Design feature specifications"
        component: "design"
        priority: "medium"
    - createTask:
        description: "Implement feature functionality"
        component: "development"
        priority: "high"
    - createTask:
        description: "Write comprehensive tests"
        component: "testing"
        priority: "medium"
```

## Performance Considerations

### Database Optimization
- **SQLite Indexing**: Optimized queries with proper indexing
- **Connection Pooling**: Efficient database connection management
- **Batch Operations**: Support for bulk task operations
- **Lazy Loading**: Metadata loaded on-demand

### Memory Management
- **Task Caching**: Frequently accessed tasks cached in memory
- **Session Limits**: Configurable maximum concurrent operations
- **Cleanup Routines**: Automatic cleanup of old task data

### Scalability Features
- **Pagination**: Large result sets handled with pagination
- **Filtering**: Efficient database queries with multiple filters
- **Bulk Operations**: Batch processing for multiple tasks

## Troubleshooting

### Common Issues

1. **"Task not found"**
   - Verify task ID format (UUID)
   - Check if task was deleted or never created
   - Use `task_list` to see available tasks

2. **"Database error"**
   - Check database file permissions
   - Verify disk space availability
   - Ensure database file is not corrupted

3. **"Invalid parent task"**
   - Verify parent task exists and is accessible
   - Check parent-child relationship permissions
   - Ensure parent task is in the same project if required

4. **"Cascade rule not triggered"**
   - Verify rule conditions match task properties
   - Check cascade rules configuration file
   - Ensure rule syntax is correct in YAML

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
Description=Task Master MCP Server
After=network.target

[Service]
Type=simple
User=task-user
ExecStart=/usr/bin/python /path/to/servers/task_master_server.py --db-path /data/tasks.db
Restart=always
ReadWritePaths=/data

[Install]
WantedBy=multi-user.target
```

### Docker Container

```dockerfile
FROM python:3.11-slim

COPY servers/ /app/servers/

WORKDIR /app
VOLUME /data

CMD ["python", "servers/task_master_server.py", "--db-path", "/data/tasks.db"]
```

## Contributing

When extending the Task Master Server:

1. Follow the existing tool registration pattern in `setup_tools()`
2. Implement proper parameter validation for all inputs
3. Add comprehensive error handling with meaningful messages
4. Include integration tests for new functionality
5. Update this documentation with new features

## License

This Task Master MCP Server is part of the larger MCP ecosystem and follows the same licensing terms.
