# ADR-0003: Task Master Integration Layer - GitHub Issues Only

## Status
Accepted

## Context
The project requires a unified task management system that integrates with external issue tracking platforms. Initially, the plan included support for multiple platforms (GitHub Projects, Jira, Linear), but analysis showed this creates unnecessary complexity and maintenance overhead.

## Decision
Implement a simplified Task Master Integration Layer that focuses exclusively on GitHub Issues using the GitHub CLI for issue management and tracking. This approach:

1. Reduces complexity by supporting only one external platform
2. Leverages the GitHub CLI which provides robust programmatic access to GitHub Issues
3. Maintains consistency with the project's existing GitHub-based workflow
4. Eliminates the need for complex multi-platform synchronization logic

## Consequences

### Positive
- **Simplicity**: Single integration point reduces maintenance burden
- **Consistency**: All tasks flow through GitHub Issues, maintaining one source of truth
- **Reliability**: GitHub CLI is mature and well-maintained
- **Developer Experience**: Familiar GitHub workflow for all team members

### Negative
- **Platform Limitation**: Cannot directly integrate with Jira or Linear instances
- **Workflow Constraint**: All project tasks must go through GitHub Issues

## Implementation Approach

### Core Components
1. **GitHub CLI Integration**: Use `gh` CLI for all GitHub Issues operations
2. **Task Synchronization**: Bidirectional sync between local task database and GitHub Issues
3. **Webhook Support**: GitHub webhooks for real-time updates
4. **Issue Templates**: Standardized issue formats for different task types

### Task Lifecycle
```
Local Task Creation → GitHub Issue Creation → Status Updates ↔ GitHub Issue Updates → Task Completion
```

### Supported Operations
- Create GitHub issues from local tasks
- Update issue status and metadata
- Link related issues (dependencies, blocks)
- Add/remove labels and assignees
- Comment synchronization

## Migration Strategy
Since this is a new integration, no existing data migration is required. The local task database will serve as the primary store, with GitHub Issues as the external tracking system.

## Rollback Plan
If GitHub Issues integration proves insufficient, the architecture supports adding additional platform integrations by extending the existing framework with platform-specific adapters.

## Notes
- GitHub CLI (`gh`) must be installed and authenticated on all systems using the Task Master
- The local SQLite database remains the single source of truth for task relationships and metadata
- GitHub Issues serve as the external visibility and collaboration layer