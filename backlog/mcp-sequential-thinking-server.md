# [ARCH/MCP] Sequential Thinking MCP Server Implementation

## Component name
mcp-sequential-thinking-server

## Description
Build a chain-of-thought guidance MCP server that helps AI agents structure their reasoning and decision-making processes. This server provides tools for creating, managing, and completing sequential thinking sessions with proper state management and session isolation.

## Sub-tasks
- [ ] Design sequential thinking interface (`sequential_thinking`, `thought_create`, `thought_complete`, `thought_list`)
- [ ] Implement session state management and isolation
- [ ] Create thought validation and structure guidance
- [ ] Add thought branching and revision capabilities
- [ ] Implement progress tracking and completion detection
- [ ] Add export functionality for thought processes
- [ ] Create stdio and WebSocket transport layers
- [ ] Write comprehensive tests and usage examples

## Priority
Medium

## Ready checklist
- [ ] exists ADR for this
- [ ] dependencies (session management, state persistence) are in place
- [ ] health & metrics endpoints defined
- [ ] TODO: Add this to cascade rules store
