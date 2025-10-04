#!/usr/bin/env python3
"""
Github MCP Server
- Tools:
    github.ensure_labels(labels)
    github.create_issue(title, body, labels, repo?)
    github.comment_issue(number, body, repo?)
    github.close_issue(number, reason="completed", repo?)
- Reads defaults from .windsurf/github-repo.json
- Requires: GitHub CLI (gh), authenticated with repo scope
"""

import json
import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

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


def _ensure_label(repo: str, name: str, color: str = DEFAULT_LABEL_COLOR, desc: str = DEFAULT_LABEL_DESC):
    if _label_exists(repo, name):
        return
    _run(f'gh label create "{name}" --color "{color}" --description "{desc}" --repo "{repo}"', check=False)


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
    def __init__(self):
        super().__init__("github", "1.0.0")
        self.register_tool(Tool("github.ensure_labels", self.ensure_labels))
        self.register_tool(Tool("github.create_issue", self.create_issue))
        self.register_tool(Tool("github.comment_issue", self.comment_issue))
        self.register_tool(Tool("github.close_issue", self.close_issue))

    def ensure_labels(self, labels: List[str], repo: Optional[str] = None) -> Dict[str, Any]:
        _assert_gh_auth()
        target = _require_repo(repo)
        created, existing = [], []
        for name in labels:
            if _label_exists(target, name):
                existing.append(name)
            else:
                _ensure_label(target, name)
                created.append(name)
        return {"repo": target, "created": created, "existing": existing}

    def create_issue(self, title: str, body: str, labels: List[str], repo: Optional[str] = None) -> Dict[str, Any]:
        _assert_gh_auth()
        target = _require_repo(repo)

        # idempotent: ensure labels first
        self.ensure_labels(labels=labels, repo=target)

        # idempotent: reuse open issue with same title
        existing = _search_issue_by_title(target, title)
        if existing:
            return {"repo": target, "number": existing, "url": f"https://github.com/{target}/issues/{existing}", "reused": True}

        # create
        label_flags = " ".join([f'--label "{l}"' for l in labels])
        proc = _run(f'gh issue create --repo "{target}" --title {shlex.quote(title)} --body {shlex.quote(body)} {label_flags}')
        url = proc.stdout.strip().splitlines()[-1]
        number = int(url.rstrip("/").split("/")[-1])
        return {"repo": target, "number": number, "url": url, "reused": False}

    def comment_issue(self, number: int, body: str, repo: Optional[str] = None) -> Dict[str, Any]:
        _assert_gh_auth()
        target = _require_repo(repo)
        _run(f'gh issue comment {number} --repo "{target}" --body {shlex.quote(body)}')
        return {"repo": target, "number": number, "commented": True}

    def close_issue(self, number: int, reason: str = "completed", repo: Optional[str] = None) -> Dict[str, Any]:
        _assert_gh_auth()
        target = _require_repo(repo)
        _run(f'gh issue close {number} --repo "{target}" --reason {shlex.quote(reason)}')
        return {"repo": target, "number": number, "closed": True, "reason": reason}


def main():
    server = GithubMCP()
    server.run_stdio()


if __name__ == "__main__":
    main()
