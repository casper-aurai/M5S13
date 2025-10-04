#!/usr/bin/env python3
"""
Git MCP Server

Provides Git repository operations with proper isolation.
Implements stdio and WebSocket transport layers.
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

try:
    from .base_mcp_server import MCPServer, MCPError, Tool
except ImportError:
    # For standalone execution
    from base_mcp_server import MCPServer, MCPError, Tool


class GitMCPServer(MCPServer):
    """Git MCP Server implementation."""

    def __init__(self, repo_root: Optional[str] = None):
        super().__init__("git", "1.0.0")

        # Resolve repository root
        if repo_root:
            self.repo_root = Path(repo_root).resolve()
        else:
            self.repo_root = Path.cwd().resolve()

        # Ensure it's a git repository
        if not (self.repo_root / ".git").exists():
            raise MCPError("INVALID_CONFIG", f"Not a git repository: {self.repo_root}")

        logging.info(f"Git server initialized with repository root: {self.repo_root}")

    def validate_repo_path(self, path: str) -> Path:
        """Validate path is within repository."""
        if not path:
            return self.repo_root

        resolved_path = Path(path).resolve()

        # Check if path is within repository
        try:
            resolved_path.relative_to(self.repo_root)
        except ValueError:
            raise MCPError(
                "PATH_OUTSIDE_REPO",
                f"Path is outside repository: {path}",
                {"requested_path": path, "repo_root": str(self.repo_root)}
            )

        return resolved_path

    def run_git_command(self, args: List[str], cwd: Path = None, check: bool = True) -> Tuple[str, str, int]:
        """Run a git command and return stdout, stderr, return code."""
        if cwd is None:
            cwd = self.repo_root

        try:
            result = subprocess.run(
                ["git"] + args,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=30  # 30 second timeout
            )

            if check and result.returncode != 0:
                raise MCPError(
                    "GIT_COMMAND_FAILED",
                    f"Git command failed: {' '.join(args)}",
                    {
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                        "returncode": result.returncode
                    }
                )

            return result.stdout.strip(), result.stderr.strip(), result.returncode

        except subprocess.TimeoutExpired:
            raise MCPError("GIT_TIMEOUT", f"Git command timed out: {' '.join(args)}")
        except FileNotFoundError:
            raise MCPError("GIT_NOT_FOUND", "Git executable not found")
        except Exception as e:
            raise MCPError("GIT_ERROR", f"Git command error: {str(e)}")

    def parse_git_status(self, status_output: str) -> List[Dict[str, Any]]:
        """Parse git status output into structured format."""
        files = []
        for line in status_output.split('\n'):
            if not line.strip():
                continue

            # Parse status line (e.g., "M  file.txt", "?? new.txt", "A  staged.txt")
            status = line[:2]
            filename = line[3:]

            status_map = {
                'M ': 'modified',
                'A ': 'added',
                'D ': 'deleted',
                'R ': 'renamed',
                'C ': 'copied',
                '??': 'untracked',
                '!!': 'ignored',
                'U ': 'unmerged'
            }

            status_code = status_map.get(status, 'unknown')

            files.append({
                "path": filename,
                "status": status_code,
                "raw_status": status
            })

        return files

    def parse_git_log(self, log_output: str) -> List[Dict[str, Any]]:
        """Parse git log output into structured format."""
        commits = []

        # Split by commit separator (empty line between commits)
        commit_blocks = [block.strip() for block in log_output.split('\n\n') if block.strip()]

        for block in commit_blocks:
            lines = block.split('\n')
            if not lines:
                continue

            # Parse first line: commit_hash author_date
            first_line = lines[0]
            parts = first_line.split()
            if len(parts) < 2:
                continue

            commit_hash = parts[0]
            author_date = ' '.join(parts[1:])

            # Find subject and body
            subject = ""
            body = ""
            in_body = False

            for line in lines[1:]:
                if line.startswith('    '):  # Body continuation
                    if in_body:
                        body += line[4:] + '\n'
                    else:
                        body += line[4:] + '\n'
                        in_body = True
                elif line.strip() and not in_body:
                    subject = line.strip()
                    in_body = True

            commits.append({
                "hash": commit_hash,
                "subject": subject,
                "body": body.strip(),
                "author_date": author_date
            })

        return commits

    async def setup_tools(self):
        """Setup git tools."""
        # Repository status tools
        self.register_tool(Tool(
            "git_status",
            "Get the status of the repository",
            {
                "type": "object",
                "properties": {
                    "porcelain": {
                        "type": "boolean",
                        "description": "Use porcelain format (default: false)",
                        "default": False
                    },
                    "path": {
                        "type": "string",
                        "description": "Path to check status for (default: entire repo)"
                    }
                }
            },
            self.git_status
        ))

        # Branch management tools
        self.register_tool(Tool(
            "git_branch",
            "List branches or create/switch branches",
            {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "Action to perform: 'list', 'create', 'switch', 'delete'",
                        "enum": ["list", "create", "switch", "delete"],
                        "default": "list"
                    },
                    "name": {
                        "type": "string",
                        "description": "Branch name (required for create/switch/delete)"
                    },
                    "base": {
                        "type": "string",
                        "description": "Base branch for new branch (default: current)"
                    }
                },
                "required": ["action"]
            },
            self.git_branch
        ))

        # Commit tools
        self.register_tool(Tool(
            "git_commit",
            "Create a commit",
            {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "Commit message"
                    },
                    "files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific files to commit (default: all staged)"
                    },
                    "amend": {
                        "type": "boolean",
                        "description": "Amend previous commit (default: false)",
                        "default": False
                    },
                    "allow_empty": {
                        "type": "boolean",
                        "description": "Allow empty commit (default: false)",
                        "default": False
                    }
                },
                "required": ["message"]
            },
            self.git_commit
        ))

        # Staging tools
        self.register_tool(Tool(
            "git_add",
            "Stage files for commit",
            {
                "type": "object",
                "properties": {
                    "files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Files to stage (use ['.'] for all)"
                    },
                    "force": {
                        "type": "boolean",
                        "description": "Force add ignored files (default: false)",
                        "default": False
                    }
                },
                "required": ["files"]
            },
            self.git_add
        ))

        # Diff tools
        self.register_tool(Tool(
            "git_diff",
            "Show differences",
            {
                "type": "object",
                "properties": {
                    "commit1": {
                        "type": "string",
                        "description": "First commit (default: HEAD)"
                    },
                    "commit2": {
                        "type": "string",
                        "description": "Second commit (default: working directory)"
                    },
                    "staged": {
                        "type": "boolean",
                        "description": "Show staged changes (default: false)",
                        "default": False
                    },
                    "path": {
                        "type": "string",
                        "description": "Path to show diff for"
                    }
                }
            },
            self.git_diff
        ))

        # Log tools
        self.register_tool(Tool(
            "git_log",
            "Show commit history",
            {
                "type": "object",
                "properties": {
                    "max_count": {
                        "type": "integer",
                        "description": "Maximum number of commits (default: 10)",
                        "minimum": 1,
                        "maximum": 100,
                        "default": 10
                    },
                    "path": {
                        "type": "string",
                        "description": "Path to show history for"
                    },
                    "author": {
                        "type": "string",
                        "description": "Filter by author"
                    },
                    "since": {
                        "type": "string",
                        "description": "Show commits since date (YYYY-MM-DD)"
                    }
                }
            },
            self.git_log
        ))

        # Remote tools
        self.register_tool(Tool(
            "git_remote",
            "Manage remote repositories",
            {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "Action: 'list', 'add', 'remove'",
                        "enum": ["list", "add", "remove"],
                        "default": "list"
                    },
                    "name": {
                        "type": "string",
                        "description": "Remote name (required for add/remove)"
                    },
                    "url": {
                        "type": "string",
                        "description": "Remote URL (required for add)"
                    }
                },
                "required": ["action"]
            },
            self.git_remote
        ))

        # Checkout tools
        self.register_tool(Tool(
            "git_checkout",
            "Checkout branch or files",
            {
                "type": "object",
                "properties": {
                    "branch": {
                        "type": "string",
                        "description": "Branch to checkout"
                    },
                    "files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Files to checkout from index"
                    },
                    "create": {
                        "type": "boolean",
                        "description": "Create branch if it doesn't exist (default: false)",
                        "default": False
                    }
                }
            },
            self.git_checkout
        ))

    async def git_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get repository status."""
        porcelain = params.get("porcelain", False)
        path = params.get("path")

        if path:
            # Validate path is within repo
            self.validate_repo_path(path)

        if porcelain:
            stdout, _, _ = self.run_git_command(["status", "--porcelain"])
            files = self.parse_git_status(stdout)
            return {
                "porcelain": True,
                "files": files,
                "count": len(files)
            }
        else:
            stdout, _, _ = self.run_git_command(["status"])
            return {
                "porcelain": False,
                "output": stdout
            }

    async def git_branch(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Manage branches."""
        action = params.get("action", "list")
        name = params.get("name")
        base = params.get("base")

        if action == "list":
            stdout, _, _ = self.run_git_command(["branch", "-v"])
            branches = []
            for line in stdout.split('\n'):
                if line.strip():
                    parts = line.strip().split()
                    current = line.startswith('*')
                    branch_name = parts[0][1:] if current else parts[0]
                    commit_hash = parts[1] if len(parts) > 1 else ""
                    message = ' '.join(parts[2:]) if len(parts) > 2 else ""

                    branches.append({
                        "name": branch_name,
                        "current": current,
                        "commit": commit_hash,
                        "message": message
                    })

            return {
                "branches": branches,
                "count": len(branches),
                "current": next((b["name"] for b in branches if b["current"]), None)
            }

        elif action == "create":
            if not name:
                raise MCPError("INVALID_PARAMS", "Branch name is required for create action")

            base_ref = base or "HEAD"
            stdout, _, _ = self.run_git_command(["checkout", "-b", name, base_ref])

            return {
                "created": True,
                "branch": name,
                "base": base_ref,
                "output": stdout
            }

        elif action == "switch":
            if not name:
                raise MCPError("INVALID_PARAMS", "Branch name is required for switch action")

            stdout, _, _ = self.run_git_command(["checkout", name])

            return {
                "switched": True,
                "branch": name,
                "output": stdout
            }

        elif action == "delete":
            if not name:
                raise MCPError("INVALID_PARAMS", "Branch name is required for delete action")

            # Use -D for force delete
            stdout, _, _ = self.run_git_command(["branch", "-D", name])

            return {
                "deleted": True,
                "branch": name,
                "output": stdout
            }

        else:
            raise MCPError("INVALID_ACTION", f"Unknown branch action: {action}")

    async def git_commit(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create a commit."""
        message = params.get("message")
        files = params.get("files")
        amend = params.get("amend", False)
        allow_empty = params.get("allow_empty", False)

        if not message:
            raise MCPError("INVALID_PARAMS", "Commit message is required")

        cmd = ["commit"]

        if amend:
            cmd.append("--amend")

        if allow_empty:
            cmd.append("--allow-empty")

        cmd.extend(["-m", message])

        if files:
            # Commit specific files
            cmd.extend(files)
        elif not amend:
            # Check if there are staged changes
            stdout, _, _ = self.run_git_command(["diff", "--cached", "--name-only"])
            if not stdout.strip():
                raise MCPError("NO_CHANGES", "No staged changes to commit")

        stdout, _, _ = self.run_git_command(cmd)

        return {
            "committed": True,
            "message": message,
            "files": files,
            "amend": amend,
            "output": stdout
        }

    async def git_add(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Stage files."""
        files = params.get("files", [])
        force = params.get("force", False)

        if not files:
            raise MCPError("INVALID_PARAMS", "Files list is required")

        cmd = ["add"]

        if force:
            cmd.append("-f")

        # Validate all paths are within repo
        for file_path in files:
            self.validate_repo_path(file_path)

        cmd.extend(files)

        stdout, _, _ = self.run_git_command(cmd)

        return {
            "staged": True,
            "files": files,
            "force": force,
            "output": stdout
        }

    async def git_diff(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Show differences."""
        commit1 = params.get("commit1", "HEAD")
        commit2 = params.get("commit2")
        staged = params.get("staged", False)
        path = params.get("path")

        cmd = ["diff"]

        if staged:
            cmd.append("--cached")
            if commit1 != "HEAD":
                cmd.extend([commit1])
        else:
            if commit1 and commit2:
                cmd.extend([commit1, commit2])
            elif commit1 and commit1 != "HEAD":
                cmd.append(commit1)

        if path:
            self.validate_repo_path(path)
            cmd.append(path)

        stdout, _, _ = self.run_git_command(cmd)

        return {
            "diff": stdout,
            "commit1": commit1,
            "commit2": commit2,
            "staged": staged,
            "path": path
        }

    async def git_log(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Show commit history."""
        max_count = params.get("max_count", 10)
        path = params.get("path")
        author = params.get("author")
        since = params.get("since")

        cmd = ["log", f"--max-count={max_count}", "--oneline"]

        if path:
            self.validate_repo_path(path)
            cmd.extend(["--", path])

        if author:
            cmd.extend(["--author", author])

        if since:
            cmd.extend(["--since", since])

        stdout, _, _ = self.run_git_command(cmd)

        commits = self.parse_git_log(stdout)

        return {
            "commits": commits,
            "count": len(commits),
            "max_count": max_count,
            "path": path,
            "author": author,
            "since": since
        }

    async def git_remote(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Manage remotes."""
        action = params.get("action", "list")
        name = params.get("name")
        url = params.get("url")

        if action == "list":
            stdout, _, _ = self.run_git_command(["remote", "-v"])
            remotes = {}

            for line in stdout.split('\n'):
                if not line.strip():
                    continue

                parts = line.split()
                if len(parts) >= 2:
                    remote_name = parts[0]
                    remote_url = parts[1]
                    direction = parts[2] if len(parts) > 2 else "fetch"

                    if remote_name not in remotes:
                        remotes[remote_name] = {"fetch": None, "push": None}

                    remotes[remote_name][direction] = remote_url

            return {
                "remotes": remotes,
                "count": len(remotes)
            }

        elif action == "add":
            if not name or not url:
                raise MCPError("INVALID_PARAMS", "Name and URL are required for add action")

            stdout, _, _ = self.run_git_command(["remote", "add", name, url])

            return {
                "added": True,
                "name": name,
                "url": url,
                "output": stdout
            }

        elif action == "remove":
            if not name:
                raise MCPError("INVALID_PARAMS", "Name is required for remove action")

            stdout, _, _ = self.run_git_command(["remote", "remove", name])

            return {
                "removed": True,
                "name": name,
                "output": stdout
            }

        else:
            raise MCPError("INVALID_ACTION", f"Unknown remote action: {action}")

    async def git_checkout(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Checkout branch or files."""
        branch = params.get("branch")
        files = params.get("files")
        create = params.get("create", False)

        if branch:
            cmd = ["checkout"]

            if create:
                cmd.append("-b")

            cmd.append(branch)

            stdout, _, _ = self.run_git_command(cmd)

            return {
                "checked_out": True,
                "branch": branch,
                "created": create,
                "output": stdout
            }

        elif files:
            # Validate all file paths
            for file_path in files:
                self.validate_repo_path(file_path)

            cmd = ["checkout", "--"] + files
            stdout, _, _ = self.run_git_command(cmd)

            return {
                "checked_out": True,
                "files": files,
                "output": stdout
            }

        else:
            raise MCPError("INVALID_PARAMS", "Either branch or files must be specified")


async def main():
    """Main server entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Git MCP Server")
    parser.add_argument(
        "--repo-root",
        help="Repository root directory (default: current directory)"
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
        server = GitMCPServer(repo_root=args.repo_root)

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
