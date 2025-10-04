# Sequential Thinking MCP Server Documentation

## Overview

The Sequential Thinking MCP Server provides advanced chain-of-thought reasoning capabilities through the Model Context Protocol (MCP). It enables AI agents to engage in structured, step-by-step thinking processes with session management, branching logic, confidence tracking, and comprehensive audit trails for complex problem-solving and decision-making.

## Features

- **Session-Based Thinking**: Persistent thinking sessions with state management
- **Thought Branching**: Support for exploring multiple reasoning paths
- **Confidence Tracking**: Quantitative confidence levels for each thought
- **Thought Types**: Structured categorization (reasoning, analysis, conclusion, question, hypothesis)
- **Session Analytics**: Statistics on thinking patterns and confidence distribution
- **Automatic Guidance**: AI-powered suggestions for next thinking steps
- **Memory Management**: Configurable session limits and automatic cleanup
- **Export Capabilities**: Session data export for analysis and review

## Thinking Framework

### Thought Types
- **Reasoning**: Logical deduction and inference steps
- **Analysis**: Breaking down complex information
- **Conclusion**: Final determinations and outcomes
- **Question**: Points requiring clarification or investigation
- **Hypothesis**: Proposed explanations or solutions

### Session Structure
- **Root Thoughts**: Initial thinking points
- **Branches**: Alternative reasoning paths
- **Current Path**: Active thinking trajectory
- **Metadata**: Confidence levels and contextual information

## Quick Start

### Basic Usage

```python
from servers.sequential_thinking_server import SequentialThinkingMCPServer

# Initialize server with session limits
server = SequentialThinkingMCPServer(
    max_sessions=50,
    max_thoughts_per_session=100,
    session_timeout=3600  # 1 hour
)

# Setup thinking tools
await server.setup_tools()

# Start server with stdio transport
server.transport_type = "stdio"
await server.start()
```

### Command Line Usage

```bash
# Start with default session limits
python servers/sequential_thinking_server.py --transport stdio

# Configure for intensive thinking sessions
python servers/sequential_thinking_server.py --max-sessions 20 --max-thoughts-per-session 200

# Use WebSocket for real-time thinking sessions
python servers/sequential_thinking_server.py --transport websocket --port 8906

# Enable auto-save for session persistence
python servers/sequential_thinking_server.py --no-auto-save  # Disable for testing
```

## Available Tools

### 1. sequential_thinking
Start or continue a sequential thinking session.

**Parameters:**
- `prompt` (string): Initial prompt or next thinking step (required)
- `session_id` (string): Existing session ID (creates new if not provided)
- `thought_type` (string): Type of thought (reasoning, analysis, conclusion, question, hypothesis)
- `confidence` (number): Confidence level (0-1, default: 0.5)
- `parent_thought_id` (string): Parent thought ID for branching
- `metadata` (object): Additional thought metadata

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "sequential_thinking",
    "arguments": {
      "prompt": "How should I approach debugging this complex algorithm?",
      "thought_type": "question",
      "confidence": 0.6,
      "metadata": {"context": "algorithm_debugging", "complexity": "high"}
    }
  }
}
```

Continue existing session:
```json
{
  "method": "tools/call",
  "params": {
    "name": "sequential_thinking",
    "arguments": {
      "prompt": "The algorithm fails when input size exceeds 1000 elements",
      "session_id": "550e8400-e29b-41d4-a716-446655440000",
      "thought_type": "analysis",
      "parent_thought_id": "previous_thought_id"
    }
  }
}
```

### 2. thought_create
Create a new thought in an existing session.

**Parameters:**
- `session_id` (string): Session ID (required)
- `content` (string): Thought content (required)
- `thought_type` (string): Type of thought (default: reasoning)
- `confidence` (number): Confidence level (0-1, default: 0.5)
- `parent_id` (string): Parent thought ID for branching
- `metadata` (object): Additional thought metadata

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "thought_create",
    "arguments": {
      "session_id": "550e8400-e29b-41d4-a716-446655440000",
      "content": "First, I need to understand the algorithm's time complexity",
      "thought_type": "analysis",
      "confidence": 0.8,
      "metadata": {"step": 1, "focus": "complexity_analysis"}
    }
  }
}
```

### 3. thought_complete
Mark a thinking session as completed.

**Parameters:**
- `session_id` (string): Session ID to complete (required)
- `conclusion` (string): Final conclusion or summary (optional)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "thought_complete",
    "arguments": {
      "session_id": "550e8400-e29b-41d4-a716-446655440000",
      "conclusion": "The algorithm issue stems from O(n²) complexity with large inputs. Solution: implement early termination for sorted subarrays."
    }
  }
}
```

### 4. thought_list
List thoughts in a session with optional subtree expansion.

**Parameters:**
- `session_id` (string): Session ID (required)
- `thought_id` (string): Specific thought ID (shows subtree if provided)
- `max_depth` (integer): Maximum depth to traverse (default: 10)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "thought_list",
    "arguments": {
      "session_id": "550e8400-e29b-41d4-a716-446655440000",
      "max_depth": 5
    }
  }
}
```

### 5. thought_get
Get detailed information about a specific thought.

**Parameters:**
- `session_id` (string): Session ID (required)
- `thought_id` (string): Thought ID (required)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "thought_get",
    "arguments": {
      "session_id": "550e8400-e29b-41d4-a716-446655440000",
      "thought_id": "550e8400-e29b-41d4-a716-446655440001"
    }
  }
}
```

### 6. session_list
List all active thinking sessions.

**Parameters:**
- `status` (string): Filter by status (active, completed, abandoned)
- `limit` (integer): Maximum sessions to return (default: 20)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "session_list",
    "arguments": {
      "status": "active",
      "limit": 10
    }
  }
}
```

### 7. session_get
Get detailed session information with analytics.

**Parameters:**
- `session_id` (string): Session ID (required)

**Examples:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "session_get",
    "arguments": {
      "session_id": "550e8400-e29b-41d4-a716-446655440000"
    }
  }
}
```

## Session Management

### Session Lifecycle

1. **Creation**: Sessions start with an initial prompt
2. **Development**: Thoughts are added sequentially or as branches
3. **Branching**: Alternative reasoning paths can be explored
4. **Completion**: Sessions end with conclusions and summaries
5. **Cleanup**: Expired sessions are automatically removed

### Session Limits

```python
# Configure session constraints
server = SequentialThinkingMCPServer(
    max_sessions=50,                    # Maximum concurrent sessions
    max_thoughts_per_session=100,       # Maximum thoughts per session
    session_timeout=3600,               # Session expiration (1 hour)
    auto_save=True                      # Automatic session persistence
)
```

## Thinking Patterns

### Linear Thinking
```json
{
  "method": "tools/call",
  "params": {
    "name": "sequential_thinking",
    "arguments": {
      "prompt": "Step 1: Analyze the problem requirements",
      "thought_type": "analysis"
    }
  }
}
```

### Branching Exploration
```json
{
  "method": "tools/call",
  "params": {
    "name": "thought_create",
    "arguments": {
      "session_id": "existing_session",
      "content": "Alternative approach: Use a different algorithm",
      "parent_id": "root_thought_id",
      "thought_type": "hypothesis"
    }
  }
}
```

### Confidence-Guided Thinking
```json
{
  "method": "tools/call",
  "params": {
    "name": "sequential_thinking",
    "arguments": {
      "prompt": "This hypothesis seems uncertain - let me verify the assumptions",
      "thought_type": "analysis",
      "confidence": 0.3,
      "metadata": {"uncertainty": "high", "requires_verification": true}
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
  "server_name": "sequential-thinking"
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
  "registered_tools": 7,
  "server_name": "sequential-thinking",
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
    "code": "SESSION_FULL",
    "message": "Maximum thoughts reached",
    "data": {
      "max_thoughts": 100,
      "current_thoughts": 100
    }
  }
}
```

### Common Error Codes

- `SESSION_NOT_FOUND`: Specified session doesn't exist
- `THOUGHT_NOT_FOUND`: Specified thought doesn't exist
- `SESSION_FULL`: Maximum thoughts per session reached
- `SESSION_LIMIT_REACHED`: Maximum concurrent sessions reached
- `INVALID_PARENT`: Parent thought not found for branching

## Advanced Features

### Confidence Analytics

The server provides session-level analytics:

```json
{
  "statistics": {
    "depth": 5,
    "branching_factor": 2.3,
    "confidence_distribution": {
      "high": 3,
      "medium": 4,
      "low": 1
    }
  }
}
```

### Thought Path Analysis

```json
{
  "path": [
    {"id": "thought_1", "type": "question", "confidence": 0.6},
    {"id": "thought_2", "type": "analysis", "confidence": 0.8},
    {"id": "thought_3", "type": "hypothesis", "confidence": 0.4}
  ]
}
```

### Guidance Generation

The server provides AI-powered thinking guidance:

```json
{
  "guidance": {
    "current_focus": "Focus on hypothesis",
    "confidence_level": "low",
    "next_steps": [
      "Test this hypothesis with evidence",
      "Consider alternative hypotheses",
      "Identify assumptions in this hypothesis"
    ],
    "branching_suggestions": [
      "Consider alternative approaches - confidence is low"
    ]
  }
}
```

## Integration Examples

### Complex Problem Solving

```json
{
  "method": "tools/call",
  "params": {
    "name": "sequential_thinking",
    "arguments": {
      "prompt": "Design a scalable authentication system for a microservices architecture",
      "thought_type": "question",
      "metadata": {"domain": "security", "scale": "enterprise"}
    }
  }
}
```

### Code Review Thinking

```json
{
  "method": "tools/call",
  "params": {
    "name": "thought_create",
    "arguments": {
      "session_id": "code_review_session",
      "content": "The authentication logic looks sound, but I need to verify the token refresh mechanism",
      "thought_type": "analysis",
      "confidence": 0.7,
      "metadata": {"focus": "token_refresh", "security_critical": true}
    }
  }
}
```

### Decision Making Process

```json
{
  "method": "tools/call",
  "params": {
    "name": "thought_complete",
    "arguments": {
      "session_id": "decision_session",
      "conclusion": "Recommendation: Implement OAuth2 with JWT tokens. This provides the best balance of security, scalability, and developer experience for our use case."
    }
  }
}
```

## Session Data Structure

### Session Object
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "initial_prompt": "How to implement secure authentication?",
  "status": "active",
  "created_at": "2024-01-15T10:00:00Z",
  "updated_at": "2024-01-15T10:15:00Z",
  "thought_count": 12,
  "root_thoughts": ["thought_1", "thought_2"],
  "current_branch": ["thought_1", "thought_3", "thought_5"],
  "metadata": {
    "total_thoughts": 12,
    "branches_explored": 2,
    "average_confidence": 0.65
  }
}
```

### Thought Object
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440001",
  "content": "First, I need to understand the security requirements",
  "type": "analysis",
  "confidence": 0.8,
  "metadata": {"focus": "requirements_analysis"},
  "created_at": "2024-01-15T10:01:00Z",
  "children": ["thought_2", "thought_3"],
  "parent": null
}
```

## Performance Considerations

### Resource Usage
- **Memory**: Scales with number of active sessions and thoughts
- **Storage**: Session data can be persisted for analysis
- **CPU**: Minimal for most thinking operations

### Optimization Tips
1. **Session Limits**: Configure appropriate session and thought limits
2. **Cleanup**: Automatic cleanup of expired sessions
3. **Branching Control**: Limit deep branching for performance
4. **Metadata Management**: Keep metadata lightweight

## Troubleshooting

### Common Issues

1. **"Session not found"**
   - Verify session ID format (UUID)
   - Check if session expired or was deleted
   - Use `session_list` to see active sessions

2. **"Maximum thoughts reached"**
   - Complete current session and start new one
   - Consider if current approach needs restructuring
   - Archive old sessions to free up capacity

3. **"Invalid parent thought"**
   - Verify parent thought exists in session
   - Check thought ID format
   - Ensure parent is in the same session

4. **Memory usage high**
   - Reduce `max_sessions` or `max_thoughts_per_session`
   - Enable automatic cleanup of old sessions
   - Monitor session sizes and archive completed ones

### Debug Mode

Enable debug logging:

```python
import logging
logging.getLogger("sequential_thinking").setLevel(logging.DEBUG)
```

## Production Deployment

### Systemd Service

```ini
[Unit]
Description=Sequential Thinking MCP Server
After=network.target

[Service]
Type=simple
User=thinking-user
ExecStart=/usr/bin/python /path/to/servers/sequential_thinking_server.py --transport websocket --port 8906
Restart=always
Environment=MAX_SESSIONS=20

[Install]
WantedBy=multi-user.target
```

### Docker Container

```dockerfile
FROM python:3.11-slim

COPY servers/ /app/servers/

WORKDIR /app
EXPOSE 8906

CMD ["python", "servers/sequential_thinking_server.py", "--transport", "websocket", "--port", "8906"]
```

## Contributing

When extending the Sequential Thinking Server:

1. Follow the existing tool registration pattern in `setup_tools()`
2. Implement proper parameter validation for all inputs
3. Add comprehensive error handling with meaningful messages
4. Include integration tests for new functionality
5. Update this documentation with new features

## License

This Sequential Thinking MCP Server is part of the larger MCP ecosystem and follows the same licensing terms.
