#!/usr/bin/env python3
"""Tests for TaskMasterMCPServer remote issue flag handling."""

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from typing import List

import pytest

from servers import task_master_server as task_master_module
from servers.task_master_server import TaskMasterMCPServer


@pytest.fixture
def configure_repo_config(tmp_path: Path, monkeypatch):
    """Configure the repo policy file for a test."""

    def _configure(enforce: bool) -> Path:
        config_path = tmp_path / "github-repo.json"
        config_path.write_text(
            json.dumps(
                {
                    "default_repo": "example/repo",
                    "default_labels": [],
                    "enforce_remote_issues": enforce,
                    "fallback_to_local_markdown": False,
                }
            )
        )
        monkeypatch.setattr(task_master_module, "REPO_CONFIG_PATH", config_path)
        return config_path

    return _configure


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    """Return a temporary database path."""

    return tmp_path / "tasks.db"


@pytest.fixture
def mock_github_cli(monkeypatch):
    """Mock GitHub CLI interactions for deterministic tests."""

    if getattr(task_master_module, "github_mcp", None) is None:
        pytest.skip("GitHub MCP helpers unavailable")

    commands: List[str] = []

    monkeypatch.setattr(task_master_module.github_mcp, "_assert_gh_auth", lambda: None)
    monkeypatch.setattr(task_master_module.github_mcp, "_require_repo", lambda repo=None: "example/repo")
    monkeypatch.setattr(task_master_module.github_mcp, "_search_issue_by_title", lambda repo, title: None)

    def fake_run(cmd: str, check: bool = True):
        commands.append(cmd)
        stdout = ""
        if "issue create" in cmd:
            stdout = "https://github.com/example/repo/issues/123\n"
        return SimpleNamespace(returncode=0, stdout=stdout, stderr="")

    monkeypatch.setattr(task_master_module.github_mcp, "_run", fake_run)
    monkeypatch.setattr(
        task_master_module.github_mcp.GithubMCP,
        "_ensure_label_state",
        lambda self, repo, labels: (labels, []),
    )

    return commands


def test_create_remote_issue_persists_flag(configure_repo_config, db_path: Path):
    """Ensure the flag defaults to True and persists to storage."""

    configure_repo_config(enforce=False)
    server = TaskMasterMCPServer(db_path=str(db_path))

    result = asyncio.run(server.task_create({"title": "Example", "description": "Test"}))

    assert result["task"]["create_remote_issue"] is True

    stored = server.database.get_task(result["task"]["id"])
    assert stored is not None
    assert stored.create_remote_issue is True
    assert stored.to_dict()["create_remote_issue"] is True


def test_trigger_labels_override_request(configure_repo_config, db_path: Path):
    """Trigger labels should force remote issue creation even when disabled by caller."""

    configure_repo_config(enforce=False)
    server = TaskMasterMCPServer(db_path=str(db_path))

    trigger_label = next(iter(task_master_module.REMOTE_ISSUE_TRIGGER_LABELS))
    params = {
        "title": "Wave 2 task",
        "description": "Needs remote issue",
        "labels": [trigger_label, "extra"],
        "create_remote_issue": False,
    }

    result = asyncio.run(server.task_create(params))

    assert result["task"]["create_remote_issue"] is True

    stored = server.database.get_task(result["task"]["id"])
    assert stored is not None
    assert stored.create_remote_issue is True


def test_enforce_remote_issues_overrides_request(configure_repo_config, db_path: Path):
    """Repository enforcement should override user preference."""

    configure_repo_config(enforce=True)
    server = TaskMasterMCPServer(db_path=str(db_path))

    result = asyncio.run(
        server.task_create(
            {
                "title": "Policy enforced",
                "description": "Remote issues mandated",
                "create_remote_issue": False,
            }
        )
    )

    assert result["task"]["create_remote_issue"] is True


def test_cascade_tasks_inherit_remote_issue_flag(configure_repo_config, db_path: Path):
    """Cascade-generated tasks should inherit the remote issue decision."""

    configure_repo_config(enforce=False)
    server = TaskMasterMCPServer(db_path=str(db_path))

    server.cascade_rules = [
        {
            "name": "Propagation",
            "trigger": {
                "whenTool": "task-master.task_create",
                "condition": {"component": "service"},
            },
            "actions": [
                {
                    "createTask": {
                        "component": "documentation",
                        "description": "Document ${component}",
                        "priority": "low",
                        "labels": [],
                    }
                }
            ],
        }
    ]

    trigger_label = next(iter(task_master_module.REMOTE_ISSUE_TRIGGER_LABELS))
    result = asyncio.run(
        server.task_create(
            {
                "title": "Service kickoff",
                "description": "Cascade propagation",
                "component": "service",
                "labels": [trigger_label],
                "create_remote_issue": False,
            }
        )
    )

    assert result["task"]["create_remote_issue"] is True
    assert result["cascade_generated"] == len(result["cascade_tasks"])
    assert result["cascade_generated"] > 0
    for cascade_task in result["cascade_tasks"]:
        assert cascade_task["create_remote_issue"] is True
        stored = server.database.get_task(cascade_task["id"])
        assert stored is not None
        assert stored.create_remote_issue is True


def test_cascade_metadata_guidance(configure_repo_config, db_path: Path):
    """Cascade subtasks should merge metadata and interpolate templates."""

    configure_repo_config(enforce=False)
    server = TaskMasterMCPServer(db_path=str(db_path))
    server.cascade_rules = [
        {
            "name": "Metadata Guidance",
            "trigger": {
                "whenTool": "task-master.task_create",
                "condition": {"component": "service"},
            },
            "actions": [
                {
                    "createTask": {
                        "component": "commit",
                        "description": "Commit ${component} changes",
                        "priority": "medium",
                        "labels": ["git", "commit"],
                        "metadata": {
                            "git": {
                                "commitMessageGuidance": {
                                    "requiresDescriptiveSummary": True,
                                    "summaryTemplate": "Summaries for ${component}",
                                }
                            },
                            "notes": ["${component} readiness", {"detail": "${component} runbook"}],
                        },
                    }
                }
            ],
        }
    ]

    result = asyncio.run(
        server.task_create(
            {
                "title": "Service kickoff",
                "description": "Cascade metadata",
                "component": "writer",
                "type": "service",
            }
        )
    )

    assert result["cascade_generated"] == 1
    cascade_task = result["cascade_tasks"][0]
    assert cascade_task["component"] == "commit"
    guidance = cascade_task["metadata"]["git"]["commitMessageGuidance"]
    assert guidance["requiresDescriptiveSummary"] is True
    assert guidance["summaryTemplate"] == "Summaries for writer"
    assert cascade_task["metadata"]["notes"][0] == "writer readiness"
    assert cascade_task["metadata"]["notes"][1]["detail"] == "writer runbook"


def test_remote_issue_created_on_task_creation(configure_repo_config, db_path: Path, mock_github_cli):
    """Task creation should automatically create and store GitHub issue metadata."""

    configure_repo_config(enforce=False)
    server = TaskMasterMCPServer(db_path=str(db_path))

    result = asyncio.run(
        server.task_create(
            {
                "title": "Automate GitHub issue",
                "description": "Ensure issue is created",
                "labels": ["automation"],
            }
        )
    )

    metadata = result["task"]["metadata"].get("github")
    assert metadata is not None
    assert metadata["issue_number"] == 123
    assert any("gh issue create" in cmd for cmd in mock_github_cli)

    stored = server.database.get_task(result["task"]["id"])
    assert stored is not None
    assert stored.metadata.get("github", {}).get("issue_number") == 123


def test_task_update_closes_remote_issue(configure_repo_config, db_path: Path, mock_github_cli):
    """Updating a task to completed should close the linked GitHub issue."""

    configure_repo_config(enforce=False)
    server = TaskMasterMCPServer(db_path=str(db_path))

    create_result = asyncio.run(
        server.task_create(
            {
                "title": "Complete workflow",
                "description": "Initial task",
                "labels": ["sync"],
            }
        )
    )

    mock_github_cli.clear()

    asyncio.run(
        server.task_update(
            {
                "task_id": create_result["task"]["id"],
                "status": "completed",
            }
        )
    )

    assert any("gh issue comment" in cmd for cmd in mock_github_cli)
    assert any("gh issue close" in cmd for cmd in mock_github_cli)

    stored = server.database.get_task(create_result["task"]["id"])
    assert stored is not None
    assert stored.metadata.get("github", {}).get("closed_at") is not None
