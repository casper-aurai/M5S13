#!/usr/bin/env python3
"""
Sequential Thinking MCP Server

Provides chain-of-thought session management and guidance.
Implements stdio and WebSocket transport layers.
"""

import asyncio
import json
import logging
import os
import sys
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

try:
    from .base_mcp_server import MCPServer, MCPError, Tool
except ImportError:
    # For standalone execution
    from base_mcp_server import MCPServer, MCPError, Tool


class Thought:
    """Represents a single thought in a thinking session."""

    def __init__(
        self,
        content: str,
        thought_type: str = "reasoning",
        confidence: float = 0.5,
        metadata: Dict[str, Any] = None
    ):
        self.id = str(uuid.uuid4())
        self.content = content
        self.thought_type = thought_type  # "reasoning", "analysis", "conclusion", "question", "hypothesis"
        self.confidence = max(0.0, min(1.0, confidence))  # Clamp to 0-1
        self.metadata = metadata or {}
        self.created_at = datetime.utcnow()
        self.children: List[str] = []  # IDs of child thoughts
        self.parent: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert thought to dictionary representation."""
        return {
            "id": self.id,
            "content": self.content,
            "type": self.thought_type,
            "confidence": self.confidence,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "children": self.children,
            "parent": self.parent
        }


class ThinkingSession:
    """Represents a sequential thinking session."""

    def __init__(
        self,
        session_id: str,
        initial_prompt: str,
        max_thoughts: int = 100,
        auto_branch: bool = False
    ):
        self.id = session_id
        self.initial_prompt = initial_prompt
        self.max_thoughts = max_thoughts
        self.auto_branch = auto_branch

        self.thoughts: Dict[str, Thought] = {}
        self.root_thoughts: List[str] = []
        self.current_branch: List[str] = []  # Current path of thought IDs

        self.created_at = datetime.utcnow()
        self.updated_at = self.created_at
        self.status = "active"  # "active", "completed", "abandoned"

        # Session metadata
        self.metadata = {
            "total_thoughts": 0,
            "branches_explored": 0,
            "average_confidence": 0.0
        }

    def add_thought(
        self,
        content: str,
        thought_type: str = "reasoning",
        confidence: float = 0.5,
        metadata: Dict[str, Any] = None,
        parent_id: Optional[str] = None
    ) -> str:
        """Add a new thought to the session."""
        if len(self.thoughts) >= self.max_thoughts:
            raise MCPError("SESSION_FULL", f"Maximum thoughts ({self.max_thoughts}) reached")

        if parent_id and parent_id not in self.thoughts:
            raise MCPError("INVALID_PARENT", f"Parent thought '{parent_id}' not found")

        # Create new thought
        thought = Thought(content, thought_type, confidence, metadata)

        # Set up parent-child relationship
        if parent_id:
            parent_thought = self.thoughts[parent_id]
            parent_thought.children.append(thought.id)
            thought.parent = parent_id

            # Update current branch
            if parent_id in self.current_branch:
                branch_index = self.current_branch.index(parent_id)
                self.current_branch = self.current_branch[:branch_index + 1]
                self.current_branch.append(thought.id)
        else:
            # Root thought
            self.root_thoughts.append(thought.id)
            if not self.current_branch:
                self.current_branch = [thought.id]

        # Add to session
        self.thoughts[thought.id] = thought
        self.metadata["total_thoughts"] = len(self.thoughts)

        # Update average confidence
        confidences = [t.confidence for t in self.thoughts.values()]
        self.metadata["average_confidence"] = sum(confidences) / len(confidences)

        self.updated_at = datetime.utcnow()

        return thought.id

    def get_thought_path(self, thought_id: str) -> List[str]:
        """Get the path from root to the specified thought."""
        if thought_id not in self.thoughts:
            return []

        path = []
        current_id = thought_id

        while current_id:
            path.insert(0, current_id)
            thought = self.thoughts[current_id]
            current_id = thought.parent

        return path

    def get_subtree(self, root_id: str) -> Dict[str, Any]:
        """Get all thoughts in the subtree rooted at the given thought."""
        if root_id not in self.thoughts:
            return {}

        subtree = {}
        to_process = [root_id]

        while to_process:
            current_id = to_process.pop()
            if current_id in subtree:
                continue

            thought = self.thoughts[current_id]
            subtree[current_id] = thought.to_dict()

            # Add children to process
            to_process.extend(thought.children)

        return subtree

    def complete_session(self, conclusion: str = None) -> Dict[str, Any]:
        """Mark session as completed."""
        self.status = "completed"
        self.updated_at = datetime.utcnow()

        summary = {
            "session_id": self.id,
            "status": self.status,
            "total_thoughts": len(self.thoughts),
            "root_thoughts": len(self.root_thoughts),
            "branches_explored": self.metadata["branches_explored"],
            "average_confidence": self.metadata["average_confidence"],
            "duration_seconds": (self.updated_at - self.created_at).total_seconds()
        }

        if conclusion:
            summary["conclusion"] = conclusion

        return summary

    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary representation."""
        return {
            "id": self.id,
            "initial_prompt": self.initial_prompt,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "thought_count": len(self.thoughts),
            "root_thoughts": self.root_thoughts,
            "current_branch": self.current_branch,
            "metadata": self.metadata
        }


class SequentialThinkingMCPServer(MCPServer):
    """Sequential Thinking MCP Server implementation."""

    def __init__(
        self,
        max_sessions: int = 100,
        max_thoughts_per_session: int = 100,
        session_timeout: int = 3600,  # 1 hour
        auto_save: bool = True
    ):
        super().__init__("sequential-thinking", "1.0.0")

        self.max_sessions = max_sessions
        self.max_thoughts_per_session = max_thoughts_per_session
        self.session_timeout = session_timeout
        self.auto_save = auto_save

        self.sessions: Dict[str, ThinkingSession] = {}
        self.session_access_times: Dict[str, float] = {}

        logging.info(f"Sequential thinking server configured for max {max_sessions} sessions")

    def cleanup_expired_sessions(self):
        """Remove expired sessions."""
        current_time = time.time()
        expired_sessions = []

        for session_id, last_access in self.session_access_times.items():
            if current_time - last_access > self.session_timeout:
                expired_sessions.append(session_id)

        for session_id in expired_sessions:
            if session_id in self.sessions:
                del self.sessions[session_id]
            if session_id in self.session_access_times:
                del self.session_access_times[session_id]

        if expired_sessions:
            logging.info(f"Cleaned up {len(expired_sessions)} expired sessions")

    async def setup_tools(self):
        """Setup sequential thinking tools."""
        # Session management
        self.register_tool(Tool(
            "sequential_thinking",
            "Start or continue a sequential thinking session",
            {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Initial prompt or next thinking step"
                    },
                    "session_id": {
                        "type": "string",
                        "description": "Existing session ID (creates new if not provided)"
                    },
                    "thought_type": {
                        "type": "string",
                        "description": "Type of thought",
                        "enum": ["reasoning", "analysis", "conclusion", "question", "hypothesis"],
                        "default": "reasoning"
                    },
                    "confidence": {
                        "type": "number",
                        "description": "Confidence level (0-1)",
                        "minimum": 0,
                        "maximum": 1,
                        "default": 0.5
                    },
                    "parent_thought_id": {
                        "type": "string",
                        "description": "Parent thought ID for branching"
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Additional thought metadata"
                    }
                },
                "required": ["prompt"]
            },
            self.sequential_thinking
        ))

        self.register_tool(Tool(
            "thought_create",
            "Create a new thought in a session",
            {
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Session ID"
                    },
                    "content": {
                        "type": "string",
                        "description": "Thought content"
                    },
                    "thought_type": {
                        "type": "string",
                        "description": "Type of thought",
                        "enum": ["reasoning", "analysis", "conclusion", "question", "hypothesis"],
                        "default": "reasoning"
                    },
                    "confidence": {
                        "type": "number",
                        "description": "Confidence level (0-1)",
                        "minimum": 0,
                        "maximum": 1,
                        "default": 0.5
                    },
                    "parent_id": {
                        "type": "string",
                        "description": "Parent thought ID for branching"
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Additional thought metadata"
                    }
                },
                "required": ["session_id", "content"]
            },
            self.thought_create
        ))

        self.register_tool(Tool(
            "thought_complete",
            "Mark a thinking session as completed",
            {
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Session ID to complete"
                    },
                    "conclusion": {
                        "type": "string",
                        "description": "Final conclusion or summary"
                    }
                },
                "required": ["session_id"]
            },
            self.thought_complete
        ))

        self.register_tool(Tool(
            "thought_list",
            "List thoughts in a session",
            {
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Session ID"
                    },
                    "thought_id": {
                        "type": "string",
                        "description": "Specific thought ID (shows subtree if provided)"
                    },
                    "max_depth": {
                        "type": "integer",
                        "description": "Maximum depth to traverse",
                        "minimum": 1,
                        "default": 10
                    }
                },
                "required": ["session_id"]
            },
            self.thought_list
        ))

        self.register_tool(Tool(
            "thought_get",
            "Get detailed information about a specific thought",
            {
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Session ID"
                    },
                    "thought_id": {
                        "type": "string",
                        "description": "Thought ID"
                    }
                },
                "required": ["session_id", "thought_id"]
            },
            self.thought_get
        ))

        # Session management
        self.register_tool(Tool(
            "session_list",
            "List all active thinking sessions",
            {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "description": "Filter by status",
                        "enum": ["active", "completed", "abandoned"]
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum sessions to return",
                        "minimum": 1,
                        "maximum": self.max_sessions,
                        "default": 20
                    }
                }
            },
            self.session_list
        ))

        self.register_tool(Tool(
            "session_get",
            "Get detailed session information",
            {
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Session ID"
                    }
                },
                "required": ["session_id"]
            },
            self.session_get
        ))

    def get_or_create_session(self, session_id: str, initial_prompt: str) -> ThinkingSession:
        """Get existing session or create new one."""
        # Cleanup expired sessions first
        self.cleanup_expired_sessions()

        if session_id and session_id in self.sessions:
            session = self.sessions[session_id]
            self.session_access_times[session_id] = time.time()
            return session

        # Check session limit
        if len(self.sessions) >= self.max_sessions:
            raise MCPError("SESSION_LIMIT_REACHED", f"Maximum sessions ({self.max_sessions}) reached")

        # Create new session
        if not session_id:
            session_id = str(uuid.uuid4())

        session = ThinkingSession(
            session_id=session_id,
            initial_prompt=initial_prompt,
            max_thoughts=self.max_thoughts_per_session
        )

        self.sessions[session_id] = session
        self.session_access_times[session_id] = time.time()

        logging.info(f"Created new thinking session: {session_id}")

        return session

    async def sequential_thinking(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Start or continue sequential thinking session."""
        prompt = params["prompt"]
        session_id = params.get("session_id")
        thought_type = params.get("thought_type", "reasoning")
        confidence = params.get("confidence", 0.5)
        parent_thought_id = params.get("parent_thought_id")
        metadata = params.get("metadata", {})

        # Get or create session
        session = self.get_or_create_session(session_id, prompt)

        # Add thought to session
        thought_id = session.add_thought(
            content=prompt,
            thought_type=thought_type,
            confidence=confidence,
            metadata=metadata,
            parent_id=parent_thought_id
        )

        # Generate guidance for next steps
        next_steps = self.generate_next_steps(session, thought_id)

        return {
            "session_id": session.id,
            "thought_id": thought_id,
            "session_info": session.to_dict(),
            "next_steps": next_steps,
            "guidance": self.generate_guidance(session, thought_id)
        }

    async def thought_create(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new thought in an existing session."""
        session_id = params["session_id"]
        content = params["content"]
        thought_type = params.get("thought_type", "reasoning")
        confidence = params.get("confidence", 0.5)
        parent_id = params.get("parent_id")
        metadata = params.get("metadata", {})

        if session_id not in self.sessions:
            raise MCPError("SESSION_NOT_FOUND", f"Session not found: {session_id}")

        session = self.sessions[session_id]
        self.session_access_times[session_id] = time.time()

        # Add thought to session
        thought_id = session.add_thought(
            content=content,
            thought_type=thought_type,
            confidence=confidence,
            metadata=metadata,
            parent_id=parent_id
        )

        return {
            "session_id": session_id,
            "thought_id": thought_id,
            "thought": session.thoughts[thought_id].to_dict(),
            "guidance": self.generate_guidance(session, thought_id)
        }

    async def thought_complete(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Mark a thinking session as completed."""
        session_id = params["session_id"]
        conclusion = params.get("conclusion")

        if session_id not in self.sessions:
            raise MCPError("SESSION_NOT_FOUND", f"Session not found: {session_id}")

        session = self.sessions[session_id]

        # Complete the session
        summary = session.complete_session(conclusion)

        # Optionally save session data
        if self.auto_save:
            self.save_session(session)

        return {
            "completed": True,
            "session_summary": summary,
            "final_conclusion": conclusion
        }

    async def thought_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List thoughts in a session."""
        session_id = params["session_id"]
        thought_id = params.get("thought_id")
        max_depth = params.get("max_depth", 10)

        if session_id not in self.sessions:
            raise MCPError("SESSION_NOT_FOUND", f"Session not found: {session_id}")

        session = self.sessions[session_id]
        self.session_access_times[session_id] = time.time()

        if thought_id:
            # Return subtree for specific thought
            subtree = session.get_subtree(thought_id)

            # Limit depth
            def limit_depth(thoughts_dict, depth=0):
                if depth >= max_depth:
                    return {tid: {**t, "truncated": True} for tid, t in thoughts_dict.items()}

                result = {}
                for tid, thought in thoughts_dict.items():
                    children = {}
                    if thought.get("children"):
                        # Get child thoughts
                        child_subtree = session.get_subtree(tid)
                        children = limit_depth(child_subtree, depth + 1)

                    result[tid] = {
                        **thought,
                        "children_info": children
                    }

                return result

            thoughts = limit_depth(subtree)
        else:
            # Return all thoughts organized by structure
            thoughts = {
                "root_thoughts": [session.thoughts[tid].to_dict() for tid in session.root_thoughts],
                "all_thoughts": {tid: t.to_dict() for tid, t in session.thoughts.items()},
                "current_branch": [session.thoughts[tid].to_dict() for tid in session.current_branch]
            }

        return {
            "session_id": session_id,
            "thoughts": thoughts,
            "count": len(session.thoughts),
            "max_depth": max_depth
        }

    async def thought_get(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed information about a specific thought."""
        session_id = params["session_id"]
        thought_id = params["thought_id"]

        if session_id not in self.sessions:
            raise MCPError("SESSION_NOT_FOUND", f"Session not found: {session_id}")

        session = self.sessions[session_id]

        if thought_id not in session.thoughts:
            raise MCPError("THOUGHT_NOT_FOUND", f"Thought not found: {thought_id}")

        thought = session.thoughts[thought_id]

        # Get path and context
        path = session.get_thought_path(thought_id)
        path_thoughts = [session.thoughts[tid].to_dict() for tid in path]

        return {
            "session_id": session_id,
            "thought": thought.to_dict(),
            "path": path_thoughts,
            "children": [session.thoughts[child_id].to_dict() for child_id in thought.children]
        }

    async def session_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List all active thinking sessions."""
        status_filter = params.get("status")
        limit = params.get("limit", 20)

        # Cleanup expired sessions
        self.cleanup_expired_sessions()

        sessions = []
        for session_id, session in self.sessions.items():
            if status_filter and session.status != status_filter:
                continue

            sessions.append(session.to_dict())

            if len(sessions) >= limit:
                break

        return {
            "sessions": sessions,
            "count": len(sessions),
            "total_sessions": len(self.sessions),
            "status_filter": status_filter
        }

    async def session_get(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed session information."""
        session_id = params["session_id"]

        if session_id not in self.sessions:
            raise MCPError("SESSION_NOT_FOUND", f"Session not found: {session_id}")

        session = self.sessions[session_id]
        self.session_access_times[session_id] = time.time()

        return {
            "session": session.to_dict(),
            "thoughts": {tid: t.to_dict() for tid, t in session.thoughts.items()},
            "statistics": {
                "depth": max((len(session.get_thought_path(tid)) for tid in session.thoughts.keys()), default=0),
                "branching_factor": sum(len(t.children) for t in session.thoughts.values()) / max(len(session.thoughts), 1),
                "confidence_distribution": self.get_confidence_distribution(session)
            }
        }

    def generate_next_steps(self, session: ThinkingSession, thought_id: str) -> List[str]:
        """Generate suggested next steps for thinking."""
        thought = session.thoughts[thought_id]

        suggestions = []

        # Basic suggestions based on thought type
        if thought.thought_type == "question":
            suggestions.extend([
                "Analyze the question from different perspectives",
                "Break down the question into smaller components",
                "Consider what information is needed to answer this",
                "Explore potential hypotheses"
            ])
        elif thought.thought_type == "hypothesis":
            suggestions.extend([
                "Test this hypothesis with evidence",
                "Consider alternative hypotheses",
                "Identify assumptions in this hypothesis",
                "Plan experiments to validate this"
            ])
        elif thought.thought_type == "analysis":
            suggestions.extend([
                "Synthesize findings into conclusions",
                "Identify patterns or themes",
                "Consider implications of this analysis",
                "Look for gaps in the analysis"
            ])
        else:
            suggestions.extend([
                "Explore related concepts or ideas",
                "Consider alternative viewpoints",
                "Break down complex ideas into simpler parts",
                "Look for evidence or examples"
            ])

        return suggestions[:5]  # Limit to 5 suggestions

    def generate_guidance(self, session: ThinkingSession, thought_id: str) -> Dict[str, Any]:
        """Generate thinking guidance."""
        thought = session.thoughts[thought_id]

        guidance = {
            "current_focus": f"Focus on {thought.thought_type}",
            "confidence_level": "high" if thought.confidence > 0.7 else "medium" if thought.confidence > 0.4 else "low",
            "next_steps": self.generate_next_steps(session, thought_id),
            "branching_suggestions": []
        }

        # Branching suggestions based on confidence and context
        if thought.confidence < 0.3:
            guidance["branching_suggestions"].append("Consider alternative approaches - confidence is low")
        elif len(thought.children) == 0 and session.metadata["total_thoughts"] > 3:
            guidance["branching_suggestions"].append("Consider exploring alternative paths from this point")

        # Session-level guidance
        if len(session.thoughts) > 20:
            guidance["session_guidance"] = "Session has many thoughts - consider synthesis and conclusion"

        return guidance

    def get_confidence_distribution(self, session: ThinkingSession) -> Dict[str, int]:
        """Get confidence level distribution for session."""
        distribution = {"high": 0, "medium": 0, "low": 0}

        for thought in session.thoughts.values():
            if thought.confidence > 0.7:
                distribution["high"] += 1
            elif thought.confidence > 0.4:
                distribution["medium"] += 1
            else:
                distribution["low"] += 1

        return distribution

    def save_session(self, session: ThinkingSession):
        """Save session data (placeholder for persistent storage)."""
        # In a full implementation, this would save to a database or file
        logging.info(f"Session {session.id} saved (auto-save enabled)")


async def main():
    """Main server entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Sequential Thinking MCP Server")
    parser.add_argument(
        "--max-sessions",
        type=int,
        default=100,
        help="Maximum number of concurrent sessions (default: 100)"
    )
    parser.add_argument(
        "--max-thoughts-per-session",
        type=int,
        default=100,
        help="Maximum thoughts per session (default: 100)"
    )
    parser.add_argument(
        "--session-timeout",
        type=int,
        default=3600,
        help="Session timeout in seconds (default: 3600)"
    )
    parser.add_argument(
        "--no-auto-save",
        action="store_true",
        help="Disable automatic session saving"
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "websocket"],
        default="stdio",
        help="Transport mechanism (default: stdio)"
    )
    parser.add_argument(
        "--port",
        type=int,
        help="Port for WebSocket transport"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Log level"
    )

    args = parser.parse_args()

    # Configure logging
    logging.getLogger().setLevel(getattr(logging, args.log_level))

    try:
        # Create server instance
        server = SequentialThinkingMCPServer(
            max_sessions=args.max_sessions,
            max_thoughts_per_session=args.max_thoughts_per_session,
            session_timeout=args.session_timeout,
            auto_save=not args.no_auto_save
        )

        # Configure transport
        if args.transport == "websocket":
            if not args.port:
                parser.error("--port is required for WebSocket transport")
            server.transport_type = "websocket"
            server.websocket_port = args.port
        else:
            server.transport_type = "stdio"

        # Start server
        await server.start()

    except KeyboardInterrupt:
        logging.info("Server interrupted by user")
    except Exception as e:
        logging.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
