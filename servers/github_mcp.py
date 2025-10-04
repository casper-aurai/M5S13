#!/usr/bin/env python3
"""GitHub MCP server implementation."""

import argparse
import asyncio
import json
import logging
import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from .base_mcp_server import MCPServer, MCPError, Tool
except ImportError:
    from base_mcp_server import MCPServer, MCPError, Tool  # type: ignore


CONFIG_PATH = Path(".windsurf/github-repo.json")
DEFAULT_LABEL_COLOR = "6f42c1"  # purple-ish
DEFAULT_LABEL_DESC = "Auto-managed by MCP"


def _run(cmd: str, check: bool = True) -> subprocess.CompletedProcess:
    proc = subprocess.run(shlex.split(cmd), capture_output=True, text=True)
    if check and proc.returncode != 0:
        raise MCPError("GITHUB_CLI_ERROR", f"{cmd}\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}")
    return proc


def _load_config() -> Dict[str, Any]:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    # permissive defaults if file missing
    return {
        "default_repo": os.getenv("MCP_GITHUB_DEFAULT_REPO", ""),
        "default_labels": ["documentation"],
        "enforce_remote_issues": True,
        "fallback_to_local_markdown": False,
    }


def _require_repo(repo: Optional[str]) -> str:
    cfg = _load_config()
    target = repo or cfg.get("default_repo") or ""
    if not target:
        raise MCPError("INVALID_CONFIG", "No repository configured. Set default_repo in .windsurf/github-repo.json")
    return target


def _assert_gh_auth():
    proc = _run("gh auth status", check=False)
    if proc.returncode != 0 or "Logged in" not in proc.stdout:
        raise MCPError("GITHUB_AUTH", "gh CLI not authenticated. Run: gh auth login (token needs repo scope).")


def _label_exists(repo: str, name: str) -> bool:
    proc = _run(f'gh label view "{name}" --repo "{repo}"', check=False)
    return proc.returncode == 0


def _ensure_label(
    repo: str,
    name: str,
    color: str = DEFAULT_LABEL_COLOR,
    desc: str = DEFAULT_LABEL_DESC,
):
    if _label_exists(repo, name):
        return

    result = _run(
        f'gh label create "{name}" --color "{color}" --description "{desc}" --repo "{repo}"',
        check=False,
    )
    if result.returncode != 0:
        raise MCPError(
            "GITHUB_LABEL_CREATE_FAILED",
            f"Failed to create label '{name}' in {repo}",
            {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
            },
        )


def _search_issue_by_title(repo: str, title: str) -> Optional[int]:
    proc = _run(f'gh issue list --repo "{repo}" --search {shlex.quote(title)} --json number,title,state', check=False)
    if proc.returncode != 0 or not proc.stdout.strip():
        return None
    try:
        items = json.loads(proc.stdout)
        for it in items:
            if it.get("title") == title and str(it.get("state", "")).upper() == "OPEN":
                return int(it["number"])
    except Exception:
        return None
    return None


class GithubMCP(MCPServer):
    """MCP server exposing GitHub issue management workflows."""

    def __init__(self):
        super().__init__("github", "1.0.0")
        self.logger = logging.getLogger(__name__)

    async def setup_tools(self):
        """Register GitHub tools with schemas."""

        self.register_tool(
            Tool(
                "github.ensure_labels",
                "Ensure that the provided labels exist in the configured GitHub repository, creating any that are missing.",
                {
                    "type": "object",
                    "properties": {
                        "labels": {
                            "type": "array",
                            "items": {"type": "string"},
                            "minItems": 1,
                            "description": "List of label names to ensure exist on the repository.",
                        },
                        "repo": {
                            "type": "string",
                            "description": "Optional owner/repo override. Defaults to the configured repository.",
                        },
                    },
                    "required": ["labels"],
                    "additionalProperties": False,
                },
                self.ensure_labels,
            )
        )
        self.register_tool(
            Tool(
                "github.create_issue",
                "Create a GitHub issue (idempotent by title) with the provided body and labels.",
                {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "minLength": 1,
                            "description": "Title for the issue.",
                        },
                        "body": {
                            "type": "string",
                            "minLength": 1,
                            "description": "Markdown body content for the issue.",
                        },
                        "labels": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Labels to apply to the issue.",
                        },
                        "repo": {
                            "type": "string",
                            "description": "Optional owner/repo override. Defaults to the configured repository.",
                        },
                    },
                    "required": ["title", "body", "labels"],
                    "additionalProperties": False,
                },
                self.create_issue,
            )
        )
        self.register_tool(
            Tool(
                "github.comment_issue",
                "Add a comment to an existing GitHub issue.",
                {
                    "type": "object",
                    "properties": {
                        "number": {
                            "type": "integer",
                            "minimum": 1,
                            "description": "Issue number to comment on.",
                        },
                        "body": {
                            "type": "string",
                            "minLength": 1,
                            "description": "Markdown body content for the comment.",
                        },
                        "repo": {
                            "type": "string",
                            "description": "Optional owner/repo override. Defaults to the configured repository.",
                        },
                    },
                    "required": ["number", "body"],
                    "additionalProperties": False,
                },
                self.comment_issue,
            )
        )
        self.register_tool(
            Tool(
                "github.close_issue",
                "Close an existing GitHub issue with the provided reason.",
                {
                    "type": "object",
                    "properties": {
                        "number": {
                            "type": "integer",
                            "minimum": 1,
                            "description": "Issue number to close.",
                        },
                        "reason": {
                            "type": "string",
                            "description": "Closure reason (completed, not_planned, duplicate). Defaults to completed.",
                            "default": "completed",
                        },
                        "repo": {
                            "type": "string",
                            "description": "Optional owner/repo override. Defaults to the configured repository.",
                        },
                    },
                    "required": ["number"],
                    "additionalProperties": False,
                },
                self.close_issue,
            )
        )

    def _ensure_label_state(self, repo: str, labels: List[str]) -> Tuple[List[str], List[str]]:
        """Ensure labels exist and return created/existing lists."""

        created: List[str] = []
        existing: List[str] = []

        for name in labels:
            if _label_exists(repo, name):
                existing.append(name)
            else:
                _ensure_label(repo, name)
                created.append(name)

        return created, existing

    async def ensure_labels(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure labels exist on the repository."""

        _assert_gh_auth()
        labels = params["labels"]
        repo = _require_repo(params.get("repo"))

        created, existing = self._ensure_label_state(repo, labels)
        return {"repo": repo, "created": created, "existing": existing}

    async def create_issue(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new GitHub issue or reuse an existing open one with the same title."""

        _assert_gh_auth()

        title = params["title"]
        body = params["body"]
        labels = params.get("labels", [])
        repo = _require_repo(params.get("repo"))

        if labels:
            self._ensure_label_state(repo, labels)

        existing_number = _search_issue_by_title(repo, title)
        if existing_number:
            return {
                "repo": repo,
                "number": existing_number,
                "url": f"https://github.com/{repo}/issues/{existing_number}",
                "reused": True,
            }

        command = f'gh issue create --repo "{repo}" --title {shlex.quote(title)} --body {shlex.quote(body)}'
        if labels:
            label_flags = " ".join([f'--label "{label}"' for label in labels])
            command = f"{command} {label_flags}"

        proc = _run(command)
        url = proc.stdout.strip().splitlines()[-1]
        number = int(url.rstrip("/").split("/")[-1])
        return {"repo": repo, "number": number, "url": url, "reused": False}

    async def comment_issue(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Add a comment to an existing issue."""

        _assert_gh_auth()
        number = params["number"]
        body = params["body"]
        repo = _require_repo(params.get("repo"))

        _run(f'gh issue comment {number} --repo "{repo}" --body {shlex.quote(body)}')
        return {"repo": repo, "number": number, "commented": True}

    async def close_issue(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Close an issue with the provided reason."""

        _assert_gh_auth()
        number = params["number"]
        reason = params.get("reason", "completed")
        repo = _require_repo(params.get("repo"))

        _run(f'gh issue close {number} --repo "{repo}" --reason {shlex.quote(reason)}')
        return {"repo": repo, "number": number, "closed": True, "reason": reason}


async def main():
    """Entrypoint for running the GitHub MCP server."""

    parser = argparse.ArgumentParser(description="GitHub MCP server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "websocket"],
        default="stdio",
        help="Transport to use (default: stdio)",
    )
    parser.add_argument(
        "--port",
        type=int,
        help="Port for WebSocket transport",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Log level",
    )

    args = parser.parse_args()

    logging.getLogger().setLevel(getattr(logging, args.log_level))

    try:
        server = GithubMCP()

        if args.transport == "websocket":
            if not args.port:
                parser.error("--port is required for WebSocket transport")
            server.transport_type = "websocket"
            server.websocket_port = args.port
        else:
            server.transport_type = "stdio"

        await server.start()

    except KeyboardInterrupt:
        logging.info("Server interrupted by user")
    except Exception as exc:
        logging.error("Server error: %s", exc, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
