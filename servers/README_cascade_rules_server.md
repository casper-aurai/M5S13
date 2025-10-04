# Cascade Rules Management Server Documentation

## Overview

The Cascade Rules Management Server provides centralized governance for AI agent behavior rules through the Model Context Protocol (MCP). It enables organizations to manage, version, and distribute rules that govern AI agent decision-making processes, task execution patterns, and operational boundaries across different domains and use cases.

## Features

- **Complete Rule Lifecycle**: Create, read, update, delete, activate, and deprecate rules
- **Advanced Rule Management**: Categorization, tagging, versioning, and conflict detection
- **Rule Validation**: JSON schema validation with comprehensive error reporting
- **Audit & Compliance**: Complete audit trails for rule changes and access tracking
- **Web Interface**: Built-in web UI for rule management and visualization
- **REST API**: Programmatic access for automation and integration
- **Conflict Resolution**: Automatic detection of overlapping or conflicting rules
- **Search & Discovery**: Full-text search across rule content and metadata

## Quick Start

### Basic Usage

```python
from servers.cascade_rules_server import CascadeRulesMCPServer

# Initialize server with storage path
server = CascadeRulesMCPServer(
    storage_path="./rules_storage",
    enable_web_ui=True
)

# Setup rule management tools
await server.setup_tools()

# Start server with WebSocket transport
server.transport_type = "websocket"
server.websocket_port = 8082
await server.start()
```

### Command Line Usage

```bash
# Start with default configuration
python servers/cascade_rules_server.py --transport websocket --port 8082

# Specify custom storage path
python servers/cascade_rules_server.py --storage-path /custom/rules/path

# Disable web UI for headless operation
python servers/cascade_rules_server.py --no-web-ui
```

## Available Tools

### 1. cascade_rule_create
Create a new cascade rule.

**Parameters:**
- `name` (string): Rule name (required)
- `description` (string): Rule description (required)
- `category` (string): Rule category (required)
- `tags` (array): Rule tags (optional)
- `priority` (string): Rule priority (low, medium, high, critical) (default: medium)
- `content` (object): Rule content and logic (required)
- `created_by` (string): Rule creator (required)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "cascade_rule_create",
    "arguments": {
      "name": "Code Quality Standards",
      "description": "Enforce consistent code formatting and quality checks",
      "category": "development",
      "tags": ["formatting", "quality", "standards"],
      "priority": "high",
      "content": {
        "conditions": {"file_type": "python"},
        "actions": {"format_code": true, "run_lints": true}
      },
      "created_by": "dev-team-lead"
    }
  }
}
```

### 2. cascade_rule_get
Get a specific rule by ID.

**Parameters:**
- `rule_id` (string): Rule ID (required)
- `version` (string): Specific version (optional)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "cascade_rule_get",
    "arguments": {
      "rule_id": "550e8400-e29b-41d4-a716-446655440000"
    }
  }
}
```

### 3. cascade_rule_update
Update an existing rule.

**Parameters:**
- `rule_id` (string): Rule ID (required)
- `name` (string): Updated rule name (optional)
- `description` (string): Updated description (optional)
- `category` (string): Updated category (optional)
- `tags` (array): Updated tags (optional)
- `priority` (string): Updated priority (optional)
- `content` (object): Updated content (optional)
- `updated_by` (string): User making update (required)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "cascade_rule_update",
    "arguments": {
      "rule_id": "550e8400-e29b-41d4-a716-446655440000",
      "description": "Updated rule description with new requirements",
      "priority": "critical",
      "updated_by": "system-admin"
    }
  }
}
```

### 4. cascade_rule_delete
Delete a rule.

**Parameters:**
- `rule_id` (string): Rule ID (required)
- `deleted_by` (string): User deleting rule (required)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "cascade_rule_delete",
    "arguments": {
      "rule_id": "550e8400-e29b-41d4-a716-446655440000",
      "deleted_by": "system-admin"
    }
  }
}
```

### 5. cascade_rule_list
List rules with filtering and pagination.

**Parameters:**
- `category` (string): Filter by category (optional)
- `tags` (array): Filter by tags (optional)
- `status` (string): Filter by status (draft, active, deprecated, archived) (optional)
- `priority` (string): Filter by priority (optional)
- `limit` (integer): Maximum results (default: 100, max: 1000)
- `offset` (integer): Pagination offset (default: 0)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "cascade_rule_list",
    "arguments": {
      "category": "development",
      "status": "active",
      "priority": "high",
      "limit": 50,
      "offset": 0
    }
  }
}
```

### 6. cascade_rule_search
Search rules by content and metadata.

**Parameters:**
- `query` (string): Search query (required)
- `fields` (array): Fields to search (name, description, content) (optional)
- `limit` (integer): Maximum results (default: 20, max: 100)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "cascade_rule_search",
    "arguments": {
      "query": "security vulnerability",
      "fields": ["name", "description", "content"],
      "limit": 20
    }
  }
}
```

### 7. cascade_rule_activate
Activate a draft rule.

**Parameters:**
- `rule_id` (string): Rule ID (required)
- `activated_by` (string): User activating rule (required)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "cascade_rule_activate",
    "arguments": {
      "rule_id": "550e8400-e29b-41d4-a716-446655440000",
      "activated_by": "operations-team"
    }
  }
}
```

### 8. cascade_rule_deprecate
Deprecate an active rule.

**Parameters:**
- `rule_id` (string): Rule ID (required)
- `deprecated_by` (string): User deprecating rule (required)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "cascade_rule_deprecate",
    "arguments": {
      "rule_id": "550e8400-e29b-41d4-a716-446655440000",
      "deprecated_by": "operations-team"
    }
  }
}
```

### 9. cascade_rule_validate
Validate rule content against schema.

**Parameters:**
- `content` (object): Rule content to validate (required)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "cascade_rule_validate",
    "arguments": {
      "content": {
        "conditions": {"environment": "production"},
        "actions": {"enable_feature": false}
      }
    }
  }
}
```

### 10. cascade_rule_check_conflicts
Check for conflicts with existing rules.

**Parameters:**
- `rule_id` (string): Rule ID to check (required)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "cascade_rule_check_conflicts",
    "arguments": {
      "rule_id": "550e8400-e29b-41d4-a716-446655440000"
    }
  }
}
```

### 11. cascade_rule_categories
List all rule categories.

**Parameters:** None

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "cascade_rule_categories",
    "arguments": {}
  }
}
```

### 12. cascade_rule_tags
List all rule tags.

**Parameters:** None

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "cascade_rule_tags",
    "arguments": {}
  }
}
```

### 13. cascade_rule_history
Get version history for a rule.

**Parameters:**
- `rule_id` (string): Rule ID (required)
- `limit` (integer): Maximum versions to return (default: 10, max: 100)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "cascade_rule_history",
    "arguments": {
      "rule_id": "550e8400-e29b-41d4-a716-446655440000",
      "limit": 5
    }
  }
}
```

### 14. cascade_rule_audit
Get audit log entries.

**Parameters:**
- `rule_id` (string): Filter by rule ID (optional)
- `action` (string): Filter by action (create, update, delete, activate, deprecate) (optional)
- `user` (string): Filter by user (optional)
- `limit` (integer): Maximum entries (default: 100, max: 1000)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "cascade_rule_audit",
    "arguments": {
      "rule_id": "550e8400-e29b-41d4-a716-446655440000",
      "action": "update",
      "limit": 10
    }
  }
}
```

## Web Interface

The server includes a built-in web UI for rule management:

### Dashboard
- **URL**: `http://localhost:8081/`
- **Features**: Overview of rules, categories, and system status

### Rules Browser
- **URL**: `http://localhost:8081/rules`
- **Features**: Browse and search rules with filtering

### Rule Details
- **URL**: `http://localhost:8081/rules/{rule_id}`
- **Features**: View complete rule information and history

### API Endpoints
- **GET** `/api/rules` - List rules
- **GET** `/api/rules/{rule_id}` - Get specific rule
- **POST** `/api/rules` - Create rule
- **PUT** `/api/rules/{rule_id}` - Update rule
- **DELETE** `/api/rules/{rule_id}` - Delete rule
- **GET** `/api/categories` - List categories
- **GET** `/api/tags` - List tags
- **GET** `/api/audit` - Get audit log

## Rule Schema

Rules must follow this JSON schema:

```json
{
  "type": "object",
  "properties": {
    "name": {"type": "string", "minLength": 1},
    "description": {"type": "string", "minLength": 1},
    "category": {"type": "string", "minLength": 1},
    "tags": {"type": "array", "items": {"type": "string"}},
    "priority": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
    "content": {"type": "object"}
  },
  "required": ["name", "description", "category", "content"]
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
  "server_name": "cascade_rules"
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
  "registered_tools": 14,
  "server_name": "cascade_rules",
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
    "code": "RULE_CONFLICT",
    "message": "Rule conflicts detected",
    "data": {
      "conflicts": ["Tag conflict with rule 'Existing Rule'"]
    }
  }
}
```

### Common Error Codes

- `INVALID_RULE`: Rule validation failed
- `RULE_NOT_FOUND`: Specified rule doesn't exist
- `RULE_CONFLICT`: Conflicts with existing rules
- `INVALID_PARAMS`: Missing or invalid parameters

## Security Considerations

### Access Control
- **Authentication**: Currently relies on transport-level security (WebSocket/HTTP)
- **Audit Logging**: All rule changes are logged with user attribution
- **Validation**: Strict input validation prevents malicious rule content

### Rule Conflicts
- **Automatic Detection**: Prevents activation of conflicting rules
- **Category Isolation**: Rules in different categories don't conflict
- **Priority Handling**: Higher priority rules override lower priority ones

### Best Practices

1. **Rule Naming**: Use clear, descriptive names for rules
2. **Category Organization**: Group related rules in categories
3. **Tag Management**: Use consistent tagging for searchability
4. **Version Control**: Update rules rather than delete them for audit trails

## Development

### Prerequisites

- **Python Dependencies**: aiofiles, aiohttp, jsonschema
- **Storage**: File system access for rule persistence
- **Network**: HTTP/WebSocket support for web interface

### Configuration

```python
# Custom configuration
server = CascadeRulesMCPServer(
    storage_path="/secure/rules/storage",
    cache_ttl=600,  # 10 minutes
    max_rules=50000,
    enable_web_ui=True
)
```

### Rule Storage

Rules are stored in JSON format:
```json
{
  "rules": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Example Rule",
      "description": "Example rule description",
      "category": "examples",
      "tags": ["example", "demo"],
      "priority": "medium",
      "status": "active",
      "content": {"condition": "example", "action": "demo"},
      "version": "1.0.0",
      "created_at": "2024-01-15T10:00:00Z",
      "updated_at": "2024-01-15T10:00:00Z",
      "created_by": "admin"
    }
  ],
  "categories": ["examples"],
  "tags": ["example", "demo"]
}
```

## Troubleshooting

### Common Issues

1. **"Rule conflicts detected"**
   - Check for overlapping tags or categories with existing rules
   - Use `cascade_rule_check_conflicts` to identify specific conflicts
   - Consider using different categories for conflicting rules

2. **"Rule not found"**
   - Verify rule ID format (UUID)
   - Check if rule was deleted or never created
   - Use `cascade_rule_list` to see available rules

3. **"Validation failed"**
   - Ensure rule content matches the required schema
   - Check for missing required fields
   - Use `cascade_rule_validate` to test content before creating

4. **Web UI not accessible**
   - Verify web UI is enabled (`enable_web_ui=True`)
   - Check if port 8081 is available
   - Ensure aiohttp dependencies are installed

### Debug Mode

Enable debug logging:

```python
import logging
logging.getLogger("cascade_rules").setLevel(logging.DEBUG)
```

## Production Deployment

### Systemd Service

```ini
[Unit]
Description=Cascade Rules Management Server
After=network.target

[Service]
Type=simple
User=cascade-user
ExecStart=/usr/bin/python /path/to/servers/cascade_rules_server.py --transport websocket --port 8082
Restart=always
Environment=STORAGE_PATH=/secure/cascade/rules

[Install]
WantedBy=multi-user.target
```

### Docker Container

```dockerfile
FROM python:3.11-slim

RUN pip install aiofiles aiohttp jsonschema

COPY servers/ /app/servers/

WORKDIR /app
EXPOSE 8081 8082

CMD ["python", "servers/cascade_rules_server.py", "--transport", "websocket", "--port", "8082"]
```

## Integration Examples

### Automated Rule Deployment

```json
{
  "method": "tools/call",
  "params": {
    "name": "cascade_rule_create",
    "arguments": {
      "name": "Security Policy Update",
      "description": "New security requirements for production deployments",
      "category": "security",
      "tags": ["security", "production", "deployment"],
      "priority": "critical",
      "content": {
        "conditions": {"environment": "production"},
        "actions": {"require_mfa": true, "scan_vulnerabilities": true}
      },
      "created_by": "security-team"
    }
  }
}
```

### Rule Compliance Checking

```json
{
  "method": "tools/call",
  "params": {
    "name": "cascade_rule_list",
    "arguments": {
      "category": "compliance",
      "status": "active"
    }
  }
}
```

### Audit Trail Analysis

```json
{
  "method": "tools/call",
  "params": {
    "name": "cascade_rule_audit",
    "arguments": {
      "action": "update",
      "limit": 50
    }
  }
}
```

## Performance Considerations

### Resource Usage
- **Memory**: ~50-100MB per server instance
- **Storage**: Scales with number of rules and versions
- **Network**: HTTP/WebSocket for web interface

### Optimization Tips
1. **Rule Caching**: Server caches frequently accessed rules
2. **Pagination**: Use pagination for large rule lists
3. **Bulk Operations**: Use bulk tools for multiple operations
4. **Cleanup**: Regularly archive old rule versions

## Contributing

When extending the Cascade Rules Server:

1. Follow the existing tool registration pattern in `setup_tools()`
2. Implement proper parameter validation for all inputs
3. Add comprehensive error handling with meaningful messages
4. Include integration tests for new functionality
5. Update this documentation with new features

## License

This Cascade Rules Management Server is part of the larger MCP ecosystem and follows the same licensing terms.
