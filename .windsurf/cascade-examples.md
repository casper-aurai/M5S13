# Example: Cascade Rule Outcomes for "service writer scaffold"
# This demonstrates what happens when someone creates a task with:
# component: "service"
# description: "scaffold service-writer"

## Original Task Created
```
Task ID: task_001
Title: "scaffold service-writer"
Component: "service"
Description: "scaffold service-writer"
Priority: "high"
Status: "open"
Assignee: "developer"
Labels: ["service", "scaffold"]
```

## Cascade Rules Triggered

### 1. Service Scaffold Cascade
**Trigger Condition Met:**
- `whenTool: "task-master.task_create"`
- `condition.component: "service"` ✓

**Actions Generated:**
1. **Scaffold writer service**
   - Component: "writer"
   - Description: "Scaffold writer service (http skeleton, Dockerfile, health, metrics)"
   - Priority: "high"
   - Labels: ["scaffold", "service", "backend"]

2. **Add observability config**
   - Component: "observability"
   - Description: "Add /health & /metrics + Prometheus scrape config for writer"
   - Priority: "high"
   - Labels: ["observability", "monitoring", "prometheus"]

3. **Generate documentation**
   - Component: "documentation"
   - Description: "Generate ADR stub and update README for writer"
   - Priority: "medium"
   - Labels: ["documentation", "adr"]

4. **Git workflow**
   - Component: "git"
   - Description: "Create branch and commit scaffold setup for writer"
   - Priority: "medium"
   - Labels: ["git", "branch", "commit"]

## Generated Task Tree

```
📋 task_001 (Original)
└── 🎯 scaffold service-writer
    ├── 🔧 task_002: Scaffold writer service
    │   ├── Component: "writer"
    │   ├── Priority: "high"
    │   └── Labels: ["scaffold", "service", "backend"]
    ├── 📊 task_003: Add observability config
    │   ├── Component: "observability"
    │   ├── Priority: "high"
    │   └── Labels: ["observability", "monitoring", "prometheus"]
    ├── 📚 task_004: Generate documentation
    │   ├── Component: "documentation"
    │   ├── Priority: "medium"
    │   └── Labels: ["documentation", "adr"]
    └── 🔀 task_005: Create branch and commit
        ├── Component: "git"
        ├── Priority: "medium"
        └── Labels: ["git", "branch", "commit"]
```

## Dependencies and Execution Order

The cascade rules establish these dependencies:

1. **task_002** (service scaffold) → **task_003** (observability)
2. **task_003** (observability) → **task_004** (documentation)
3. **task_004** (documentation) → **task_005** (git)

**Execution Flow:**
```
task_001 (trigger) → task_002 → task_003 → task_004 → task_005
```

## Task Details

### Task 002: Scaffold writer service
```json
{
  "id": "task_002",
  "title": "Scaffold writer service (http skeleton, Dockerfile, health, metrics)",
  "component": "writer",
  "type": "service",
  "priority": "high",
  "status": "open",
  "assignee": "developer",
  "labels": ["scaffold", "service", "backend"],
  "depends_on": ["task_001"],
  "metadata": {
    "cascade_generated": true,
    "cascade_rule": "Service Scaffold Cascade",
    "parent_task": "task_001"
  }
}
```

### Task 003: Add observability config
```json
{
  "id": "task_003",
  "title": "Add /health & /metrics + Prometheus scrape config for writer",
  "component": "observability",
  "type": "observability",
  "priority": "high",
  "status": "open",
  "assignee": "developer",
  "labels": ["observability", "monitoring", "prometheus"],
  "depends_on": ["task_002"],
  "metadata": {
    "cascade_generated": true,
    "cascade_rule": "Service Scaffold Cascade",
    "parent_task": "task_001"
  }
}
```

### Task 004: Generate documentation
```json
{
  "id": "task_004",
  "title": "Generate ADR stub and update README for writer",
  "component": "documentation",
  "type": "documentation",
  "priority": "medium",
  "status": "open",
  "assignee": "developer",
  "labels": ["documentation", "adr"],
  "depends_on": ["task_003"],
  "metadata": {
    "cascade_generated": true,
    "cascade_rule": "Service Scaffold Cascade",
    "parent_task": "task_001"
  }
}
```

### Task 005: Git workflow
```json
{
  "id": "task_005",
  "title": "Create branch and commit scaffold setup for writer",
  "component": "git",
  "type": "git",
  "priority": "medium",
  "status": "open",
  "assignee": "developer",
  "labels": ["git", "branch", "commit"],
  "depends_on": ["task_004"],
  "metadata": {
    "cascade_generated": true,
    "cascade_rule": "Service Scaffold Cascade",
    "parent_task": "task_001"
  }
}
```

## Additional Cascade Rules That Could Trigger

### If API endpoints are mentioned:
**API Endpoint Cascade** could trigger:
- Unit tests for API endpoints
- API documentation generation

### If observability is explicitly mentioned:
**Observability Cascade** could trigger:
- Prometheus scrape configuration
- Grafana dashboard panels

### If database changes are mentioned:
**Database Migration Cascade** could trigger:
- Schema design tasks
- Migration script creation
- Seed data setup

## Security Enforcement

All generated tasks are subject to security constraints:

- **Filesystem operations**: Sandboxed to workspace, size limits enforced
- **Git operations**: Repository boundary validation, no force pushes
- **HTTP requests**: Whitelist-only access, timeout limits
- **Container operations**: User socket only, no privileged containers
- **Redis operations**: Session-scoped only, size limits enforced

## Benefits of Cascade Rules

1. **Consistency**: Every service follows the same scaffolding pattern
2. **Completeness**: No steps are forgotten (observability, docs, git)
3. **Automation**: Reduces manual task creation overhead
4. **Quality**: Enforces best practices across all components
5. **Visibility**: Clear dependency chains and execution order
6. **Security**: All operations are security-constrained

## Configuration

The cascade rules are defined in `.windsurf/cascade-rules.yaml` and can be customized for different project needs. The MCP Task Master server automatically processes these rules when tasks are created.
