# [ARCH/MCP] Task Master Integration Layer - GitHub Issues Only

## Component name
task-master-integration

## Description
Build an integration layer that connects the MCP ecosystem with GitHub Issues using the GitHub CLI for issue management and tracking. This provides seamless task creation, tracking, and synchronization while maintaining consistency in task metadata and status.

## Sub-tasks
- [x] Design unified task schema for GitHub Issues integration
- [ ] Implement GitHub Issues integration using GitHub CLI
- [x] Remove GitHub Projects, Jira, and Linear integration requirements
- [ ] Build webhook handlers for real-time updates
- [ ] Implement task status mapping and conversion
- [ ] Add bulk operations support
- [ ] Create migration tools for existing tasks

## Priority
High

## Ready checklist
- [x] exists ADR for this (ADR-0003)
- [ ] dependencies (GitHub CLI) are in place
- [ ] health & metrics endpoints defined
- [ ] TODO: Add this to cascade rules store
        
