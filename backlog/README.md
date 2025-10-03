# Architecture & MCP Task Backlog

This directory contains a backlog of architecture and MCP-level tasks that can be imported into GitHub Issues.

## Structure

- `.github/ISSUE_TEMPLATES/architecture-mcp-task.md` - GitHub issue template for architecture/MCP tasks
- `backlog/` - Directory containing individual task files that can be imported as GitHub issues

## How to Use

### 1. Template Setup
The GitHub issue template has been created and will be available when creating new issues in the repository.

### 2. Importing Backlog Items

To import these backlog items into GitHub Issues:

1. **Manual Import**: Copy the content from each `.md` file in the `backlog/` directory
2. **Create GitHub Issue**: Go to GitHub → Issues → New Issue
3. **Use Template**: Select the "🛠️ Architecture & MCP Task" template
4. **Paste Content**: Copy the relevant content from the backlog files
5. **Customize**: Adjust assignees, labels, and other details as needed

### 3. Alternative: GitHub CLI Import

You can also use GitHub CLI to import these issues programmatically:

```bash
# For each backlog file
gh issue create --title "MCP Podman Server" --body-file mcp-podman-server.md --label architecture,mcp,task
```

## Current Backlog Items

1. **MCP Podman Server** - Container management capabilities
2. **Cascade Rule Server** - Centralized rule management system
3. **Task Master Integration** - Multi-platform task management integration

## Adding New Items

1. Create a new `.md` file in the `backlog/` directory
2. Follow the same structure as existing files
3. Include all required sections from the template

## Maintenance

- Keep backlog items up to date with current priorities
- Archive completed items by moving them to an `archive/` subdirectory
- Update the template as needed to reflect evolving requirements
