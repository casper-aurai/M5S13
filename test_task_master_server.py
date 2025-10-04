#!/usr/bin/env python3
"""Tests for TaskMasterMCPServer remote issue flag handling."""

import asyncio
import json
from pathlib import Path

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
