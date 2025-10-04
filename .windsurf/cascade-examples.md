# Cascade Rule Usage Examples

## Real-World Example: Writer Service Scaffolding

### Scenario
When a developer creates a task to scaffold a new service component:

```json
{
  "title": "scaffold service-writer",
  "description": "scaffold service-writer HTTP + Dockerfile + health/metrics",
  "type": "service",
  "component": "service",
  "labels": ["scaffold", "service"]
}
```

### Cascade Rules Triggered

#### 1. Service Scaffold Cascade
**Trigger Condition Met:**
- `whenTool: "task-master.task_create"` ✓
- `condition.component: "service"` ✓

**Generated Tasks:**

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
   - Metadata:
     - `git.commitMessageGuidance.summaryTemplate`: "Provide a descriptive summary of writer changes"
     - `git.commitMessageGuidance.summaryField`: `descriptive_summary`
     - `git.commitMessageGuidance.styleGuide`: "Use present tense, highlight primary impact, limit to 72 characters"

5. **Commit summary validation**
   - Component: "commit-validation"
   - Description: "Validate descriptive summary commit for writer"
   - Priority: "medium"
   - Labels: ["git", "commit", "validation"]
   - Metadata checklist ensures a summary-backed commit exists and is captured for release notes

### Generated Task Tree

```
📋 Original Task: scaffold service-writer
└── 🎯 Service Scaffold Cascade (5 subtasks)
    ├── 🔧 Writer Service Scaffolding
    │   ├── HTTP skeleton with /health & /metrics endpoints
    │   ├── Dockerfile with healthcheck
    │   ├── requirements.txt with aiohttp & prometheus-client
    │   └── services/writer/ directory structure
    ├── 📊 Observability Configuration
    │   ├── Prometheus scrape config for writer:8080/metrics
    │   ├── Grafana dashboard panel for writer metrics
    │   └── docker-compose.yml service definition
    ├── 📚 Documentation Generation
    │   ├── ADR document for writer service architecture
    │   └── README.md updates with writer service info
    └── 🔀 Git Workflow Setup
        ├── feature/writer-scaffold branch creation
        ├── Initial commit of service scaffolding with descriptive summary guidance
        ├── Validation checklist to confirm the summary-backed commit exists
        └── PR template with proper labels and ADR references
```

### Files Created/Modified

#### Service Scaffolding (`services/writer/`)
```
services/writer/
├── app.py           # HTTP service with /health & /metrics
├── Dockerfile       # Multi-stage build with healthcheck
└── requirements.txt # aiohttp, prometheus-client dependencies
```

#### Observability Configuration
```
monitoring/prometheus.yml    # Added writer:8080/metrics scrape target
docker/docker-compose.yml    # Added writer service with Dgraph/Weaviate/MinIO deps
```

#### Documentation
```
docs/adr/adr-002-writer-service.md    # Architecture decision record
README.md                             # Updated with writer service info
```

#### Git Workflow
```
.git/
└── refs/heads/feature/writer-scaffold  # New feature branch
```

### Security Enforcement Applied

All generated tasks are subject to security constraints:

- **Filesystem operations**: Sandboxed to workspace, size limits enforced
- **Git operations**: Repository boundary validation, no force pushes
- **HTTP requests**: Whitelist-only access, timeout limits
- **Container operations**: User socket only, no privileged containers
- **Redis operations**: Session-scoped only, size limits enforced

### Benefits Demonstrated

1. **Consistency**: Every service follows the same scaffolding pattern
2. **Completeness**: No steps are forgotten (observability, docs, git)
3. **Automation**: Reduces manual task creation overhead
4. **Quality**: Enforces best practices across all components
5. **Visibility**: Clear dependency chains and execution order
6. **Security**: All operations are security-constrained

### Configuration Reference

The cascade rules are defined in `.windsurf/cascade-rules.yaml` and can be customized for different project needs. The MCP Task Master server automatically processes these rules when tasks are created.

**Service Scaffold Cascade Rule:**
```yaml
- name: "Service Scaffold Cascade"
  trigger:
    whenTool: "task-master.task_create"
    condition:
      component: "service"
  actions:
    - createTask:
        description: "Scaffold ${component} service (http skeleton, Dockerfile, health, metrics)"
        priority: "high"
        labels: ["scaffold", "service", "backend"]
    # ... additional tasks for observability, docs, git
```

This example demonstrates how a single task creation can automatically generate a complete development workflow with proper dependencies, security constraints, and machine-importable configuration formats.
