#!/usr/bin/env python3
"""Task Master MCP Server implementation."""

from __future__ import annotations

import asyncio
import importlib
import json
import logging
import os
import sqlite3
import subprocess
import sys
import threading
import time
import uuid
import shlex
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

yaml_spec = importlib.util.find_spec("yaml")
yaml = importlib.import_module("yaml") if yaml_spec is not None else None


REPO_CONFIG_PATH = Path(".windsurf/github-repo.json")
REMOTE_ISSUE_TRIGGER_LABELS = frozenset(
    {
        "kafka",
        "weaviate",
        "reporting",
        "airflow",
        "observability",
        "dx",
        "dgraph",
        "storage",
        "deployment",
        "data-flow",
        "architecture",
    }
)

try:
    from .base_mcp_server import MCPError, MCPServer, Tool
except ImportError:
    # For standalone execution
    from base_mcp_server import MCPError, MCPServer, Tool

try:  # Optional GitHub tooling helper
    from . import github_mcp  # type: ignore
except ImportError:  # pragma: no cover - optional dependency for offline tests
    github_mcp = None  # type: ignore


class Task:
    """Represents a task or issue."""
    def __init__(
        self,
        title: str,
        description: str,
        task_type: str = "task",
        component: str = None,
        priority: str = "medium",
        status: str = "open",
        assignee: str = None,
        labels: Optional[List[str]] = None,
        parent_id: str = None,
        project_id: str = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None,
        depends_on: Optional[List[str]] = None,
        blocked_by: Optional[List[str]] = None,
        subtasks: Optional[List[str]] = None,
        create_remote_issue: bool = True,
    ):
        """Initialize task."""
        self.id = str(uuid.uuid4())
        self.title = title
        self.description = description
        self.type = task_type  # Use 'type' as the attribute name for consistency
        self.component = component
        self.priority = priority
        self.status = status
        self.assignee = assignee
        self.labels = labels or []
        self.parent_id = parent_id
        self.project_id = project_id

        self.created_at = created_at or datetime.utcnow()
        self.updated_at = self.created_at
        self.completed_at = completed_at

        self.metadata = metadata or {}
        self.github_issue_number: Optional[int] = None
        self.depends_on = depends_on or []
        self.blocked_by = blocked_by or []
        self.subtasks = subtasks or []
        self.create_remote_issue = bool(create_remote_issue)

    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary representation."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "type": self.type,
            "component": self.component,
            "priority": self.priority,
            "status": self.status,
            "assignee": self.assignee,
            "labels": self.labels,
            "parent_id": self.parent_id,
            "project_id": self.project_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "metadata": self.metadata,
            "depends_on": self.depends_on,
            "blocked_by": self.blocked_by,
            "subtasks": self.subtasks,
            "github_issue_number": self.github_issue_number,
        }


class TaskProject:
    """Represents a project containing tasks."""

    def __init__(self, name: str, description: str = ""):
        self.id = str(uuid.uuid4())
        self.name = name
        self.description = description
        self.created_at = datetime.utcnow()
        self.updated_at = self.created_at
        self.status = "active"  # "active", "completed", "archived"

    def to_dict(self) -> Dict[str, Any]:
        """Convert project to dictionary representation."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


class TaskDatabase:
    """SQLite database wrapper for task management."""

    def __init__(self, db_path: str = "./data/tasks.db"):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Initialize database schema."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    status TEXT DEFAULT 'active',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT,
                    type TEXT DEFAULT 'task',
                    component TEXT,
                    priority TEXT DEFAULT 'medium',
                    status TEXT DEFAULT 'open',
                    assignee TEXT,
                    labels TEXT,  -- JSON array
                    parent_id TEXT,
                    project_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    completed_at TEXT,
                    metadata TEXT,  -- JSON object
                    depends_on TEXT,  -- JSON array
                    blocked_by TEXT,  -- JSON array
                    subtasks TEXT,  -- JSON array
                    create_remote_issue INTEGER DEFAULT 1,
                    FOREIGN KEY (parent_id) REFERENCES tasks (id),
                    FOREIGN KEY (project_id) REFERENCES projects (id)
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks (status)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks (priority)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_project ON tasks (project_id)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_assignee ON tasks (assignee)
            """)

            # Ensure the create_remote_issue column exists for legacy databases
            existing_columns = {
                row[1] for row in conn.execute("PRAGMA table_info(tasks)")
            }
            if "create_remote_issue" not in existing_columns:
                conn.execute(
                    "ALTER TABLE tasks ADD COLUMN create_remote_issue INTEGER DEFAULT 1"
                )

    def save_task(self, task: Task) -> bool:
        """Save task to database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO tasks
                    (id, title, description, type, component, priority, status, assignee, labels,
                     parent_id, project_id, created_at, updated_at, completed_at, metadata,
                     depends_on, blocked_by, subtasks, create_remote_issue)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    task.id,
                    task.title,
                    task.description,
                    task.type,
                    getattr(task, 'component', None),
                    task.priority,
                    task.status,
                    task.assignee,
                    json.dumps(task.labels),
                    task.parent_id,
                    task.project_id,
                    task.created_at.isoformat(),
                    task.updated_at.isoformat(),
                    task.completed_at.isoformat() if task.completed_at else None,
                    json.dumps(task.metadata),
                    json.dumps(task.depends_on),
                    json.dumps(task.blocked_by),
                    json.dumps(task.subtasks),
                    int(bool(getattr(task, "create_remote_issue", True))),
                ))
                return True
        except Exception as e:
            logging.error(f"Error saving task: {e}")
            return False

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
                row = cursor.fetchone()

                if row:
                    return self._row_to_task(row)
        except Exception as e:
            logging.error(f"Error getting task: {e}")

        return None

    def list_tasks(self, filters: Dict[str, Any] = None) -> List[Task]:
        """List tasks with optional filters."""
        tasks = []
        query = "SELECT * FROM tasks"
        params = []

        if filters:
            conditions = []

            if "status" in filters:
                conditions.append("status = ?")
                params.append(filters["status"])

            if "priority" in filters:
                conditions.append("priority = ?")
                params.append(filters["priority"])

            if "project_id" in filters:
                conditions.append("project_id = ?")
                params.append(filters["project_id"])

            if "assignee" in filters:
                conditions.append("assignee = ?")
                params.append(filters["assignee"])

            if "parent_id" in filters:
                conditions.append("parent_id = ?")
                params.append(filters["parent_id"])

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY created_at DESC"

        if "limit" in filters:
            query += " LIMIT ?"
            params.append(filters["limit"])

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(query, params)

                for row in cursor:
                    tasks.append(self._row_to_task(row))

        except Exception as e:
            logging.error(f"Error listing tasks: {e}")

        return tasks

    def delete_task(self, task_id: str) -> bool:
        """Delete task from database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
                return cursor.rowcount > 0
        except Exception as e:
            logging.error(f"Error deleting task: {e}")
            return False
        """Save project to database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO projects
                    (id, name, description, status, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    project.id,
                    project.name,
                    project.description,
                    project.status,
                    project.created_at.isoformat(),
                    project.updated_at.isoformat()
                ))
                return True
        except Exception as e:
            logging.error(f"Error saving project: {e}")
            return False

    def get_project(self, project_id: str) -> Optional[TaskProject]:
        """Get project by ID."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
                row = cursor.fetchone()

                if row:
                    return self._row_to_project(row)
        except Exception as e:
            logging.error(f"Error getting project: {e}")

        return None

    def list_projects(self) -> List[TaskProject]:
        """List all projects."""
        projects = []
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("SELECT * FROM projects ORDER BY created_at DESC")

                for row in cursor:
                    projects.append(self._row_to_project(row))

        except Exception as e:
            logging.error(f"Error listing projects: {e}")

        return projects

    def _row_to_task(self, row: sqlite3.Row) -> Task:
        """Convert database row to Task object."""
        component_value = row["component"] if "component" in row.keys() else None

        task = Task(
            title=row["title"],
            description=row["description"],
            task_type=row["type"],
            component=component_value,
            priority=row["priority"],
            status=row["status"],
            assignee=row["assignee"],
            labels=json.loads(row["labels"]) if row["labels"] else [],
            parent_id=row["parent_id"],
            project_id=row["project_id"]
        )

        # Override auto-generated fields with database values
        task.id = row["id"]
        task.created_at = datetime.fromisoformat(row["created_at"])
        task.updated_at = datetime.fromisoformat(row["updated_at"])
        task.completed_at = datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None
        task.metadata = json.loads(row["metadata"]) if row["metadata"] else {}
        task.depends_on = json.loads(row["depends_on"]) if row["depends_on"] else []
        task.blocked_by = json.loads(row["blocked_by"]) if row["blocked_by"] else []
        task.subtasks = json.loads(row["subtasks"]) if row["subtasks"] else []
        if "create_remote_issue" in row.keys():
            task.create_remote_issue = bool(row["create_remote_issue"])
        else:
            task.create_remote_issue = True

        return task

    def _row_to_project(self, row: sqlite3.Row) -> TaskProject:
        """Convert database row to TaskProject object."""
        project = TaskProject(name=row["name"], description=row["description"])
        project.id = row["id"]
        project.created_at = datetime.fromisoformat(row["created_at"])
        project.updated_at = datetime.fromisoformat(row["updated_at"])
        project.status = row["status"]
        return project


class TaskMasterMCPServer(MCPServer):
    """Task Master MCP Server implementation with cascade rules support."""

    def __init__(self, db_path: str = "./data/tasks.db"):
        super().__init__("task-master", "1.0.0")

        self.logger = logging.getLogger(__name__)
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.repo_config = self._load_repo_config()
        self._enforce_remote_issues = bool(
            self.repo_config.get("enforce_remote_issues", True)
        )
        self.remote_issue_trigger_labels = {
            label.lower() for label in REMOTE_ISSUE_TRIGGER_LABELS
        }
        self.database = TaskDatabase(db_path)  # Initialize the database
        self.cascade_rules = self._load_cascade_rules()
        self._init_database()
        self._github_helper: Optional["github_mcp.GithubMCP"] = None if github_mcp else None

    def _init_database(self):
        """Additional database initialization if needed."""
        # The TaskDatabase class handles schema creation
        pass

    def _load_repo_config(self) -> Dict[str, Any]:
        """Load repository configuration from disk."""
        if not REPO_CONFIG_PATH.exists():
            self.logger.debug(
                "Repo config not found at %s; using defaults", REPO_CONFIG_PATH
            )
            return {}

        try:
            data = json.loads(REPO_CONFIG_PATH.read_text())
            if not isinstance(data, dict):
                self.logger.warning(
                    "Unexpected repo config structure in %s; using defaults",
                    REPO_CONFIG_PATH,
                )
                return {}
            return data
        except json.JSONDecodeError as exc:
            self.logger.warning(
                "Failed to parse repo config %s: %s", REPO_CONFIG_PATH, exc
            )
            return {}
        except OSError as exc:
            self.logger.warning(
                "Unable to read repo config %s: %s", REPO_CONFIG_PATH, exc
            )
            return {}

    def _should_create_remote_issue(
        self, requested_flag: bool, labels: List[str]
    ) -> bool:
        """Determine whether remote issue creation should be enabled."""
        if self._enforce_remote_issues:
            return True

        normalized_labels = {label.lower() for label in labels if isinstance(label, str)}
        if normalized_labels & self.remote_issue_trigger_labels:
            return True

        return bool(requested_flag)

    def _github_repo(self) -> Optional[str]:
        """Return the configured GitHub repository if available."""

        repo = self.repo_config.get("default_repo")
        if isinstance(repo, str) and repo:
            return repo

        env_repo = os.getenv("MCP_GITHUB_DEFAULT_REPO")
        if env_repo:
            return env_repo

        return None

    def _github_default_labels(self) -> List[str]:
        """Return default labels configured for GitHub issues."""

        labels = self.repo_config.get("default_labels", [])
        if not isinstance(labels, list):
            return []
        return [str(label) for label in labels if isinstance(label, str) and label]

    def _github_cli_ready(self) -> bool:
        """Check whether GitHub CLI interactions are possible."""

        if github_mcp is None:
            return False

        repo = self._github_repo()
        if not repo:
            self.logger.debug("GitHub automation skipped: no default repository configured")
            return False

        try:
            github_mcp._assert_gh_auth()
        except Exception as exc:  # pragma: no cover - relies on gh CLI
            self.logger.warning("GitHub CLI authentication missing: %s", exc)
            return False

        return True

    def _get_github_helper(self) -> Optional["github_mcp.GithubMCP"]:
        """Return a lazily initialized GitHub MCP helper."""

        if github_mcp is None:
            return None

        if self._github_helper is None:
            self._github_helper = github_mcp.GithubMCP()

        return self._github_helper

    def _ensure_github_labels(self, repo: str, labels: List[str]) -> None:
        """Ensure labels exist on the remote repository."""

        if not labels or github_mcp is None:
            return

        helper = self._get_github_helper()
        if helper is None:
            return

        try:
            helper._ensure_label_state(repo, labels)
        except Exception as exc:  # pragma: no cover - defensive guard
            self.logger.warning("Failed to ensure GitHub labels %s: %s", labels, exc)

    def _safe_run_github(self, command: str, context: str) -> Optional[subprocess.CompletedProcess]:
        """Execute a GitHub CLI command safely, logging failures."""

        if github_mcp is None:
            return None

        try:
            return github_mcp._run(command)
        except Exception as exc:  # pragma: no cover - requires gh CLI
            self.logger.warning("GitHub %s command failed: %s", context, exc)
            return None

    def _render_issue_body(self, task: "Task") -> str:
        """Render a markdown body for the GitHub issue."""

        description = task.description.strip() if task.description else "_No description provided._"
        lines = [description, "", "## Task Metadata", f"- Task ID: `{task.id}`"]

        if task.component:
            lines.append(f"- Component: `{task.component}`")
        lines.append(f"- Status: `{task.status}`")
        lines.append(f"- Priority: `{task.priority}`")
        if task.labels:
            labels = ", ".join(sorted({label for label in task.labels if label}))
            if labels:
                lines.append(f"- Labels: {labels}")

        return "\n".join(lines)

    def _create_remote_issue_for_task(self, task: "Task") -> Optional[Dict[str, Any]]:
        """Create (or reuse) a GitHub issue for the given task."""

        if not task.create_remote_issue or github_mcp is None:
            return None

        metadata = task.metadata.setdefault("github", {})
        if metadata.get("issue_number"):
            return metadata

        if not self._github_cli_ready():
            return None

        repo = self._github_repo()
        if not repo:
            return None

        labels = sorted(set((task.labels or []) + self._github_default_labels()))
        if labels:
            self._ensure_github_labels(repo, labels)

        title = task.title
        body = self._render_issue_body(task)

        existing_number: Optional[int] = None
        try:
            existing_number = github_mcp._search_issue_by_title(repo, title)
        except Exception:
            existing_number = None

        reused = False
        issue_url = ""
        issue_number: Optional[int] = None

        if existing_number:
            reused = True
            issue_number = existing_number
            issue_url = f"https://github.com/{repo}/issues/{existing_number}"
        else:
            command = f'gh issue create --repo "{repo}" --title {shlex.quote(title)} --body {shlex.quote(body)}'
            for label in labels:
                command += f' --label "{label}"'

            proc = self._safe_run_github(command, "issue create")
            if proc is None or not proc.stdout:
                return None

            issue_url = proc.stdout.strip().splitlines()[-1]
            try:
                issue_number = int(issue_url.rstrip("/").split("/")[-1])
            except (ValueError, IndexError):  # pragma: no cover - defensive
                self.logger.warning("Unable to parse issue number from %s", issue_url)
                return None

        metadata.update(
            {
                "repo": repo,
                "issue_number": issue_number,
                "issue_url": issue_url,
                "reused": reused,
                "labels": labels,
                "last_sync": datetime.utcnow().isoformat(),
            }
        )

        self.database.save_task(task)
        return metadata

    def _sync_remote_issue_on_update(
        self,
        task: "Task",
        old_status: Optional[str],
        status_changed: bool,
        title_changed: bool,
        description_changed: bool,
    ) -> None:
        """Update remote GitHub issue when task metadata changes."""

        if github_mcp is None or not task.create_remote_issue:
            return

        metadata = task.metadata.get("github") or self._create_remote_issue_for_task(task)
        if not metadata or not metadata.get("issue_number"):
            return

        repo = metadata.get("repo") or self._github_repo()
        issue_number = metadata.get("issue_number")
        if not repo or not issue_number:
            return

        base_command = f'gh issue edit {issue_number} --repo "{repo}"'
        command = base_command

        if title_changed:
            command += f' --title {shlex.quote(task.title)}'
        if description_changed:
            command += f' --body {shlex.quote(self._render_issue_body(task))}'

        current_labels = sorted({label for label in (task.labels or []) if label})
        previous_labels = sorted({label for label in metadata.get("labels", []) if label})
        labels_added = sorted(set(current_labels) - set(previous_labels))
        labels_removed = sorted(set(previous_labels) - set(current_labels))

        if labels_added:
            self._ensure_github_labels(repo, labels_added)
            for label in labels_added:
                command += f' --add-label "{label}"'
        if labels_removed:
            for label in labels_removed:
                command += f' --remove-label "{label}"'

        if command != base_command:
            self._safe_run_github(command, "issue edit")
            metadata["labels"] = current_labels

        if status_changed:
            comment_lines = [
                f"Task status changed from **{old_status or 'unknown'}** to **{task.status}**",
                f"Timestamp: {datetime.utcnow().isoformat()}Z",
            ]
            comment = "\n\n".join(comment_lines)
            self._safe_run_github(
                f'gh issue comment {issue_number} --repo "{repo}" --body {shlex.quote(comment)}',
                "issue comment",
            )

            if task.status == "completed":
                self._safe_run_github(
                    f'gh issue close {issue_number} --repo "{repo}" --reason completed',
                    "issue close",
                )
                metadata["closed_at"] = datetime.utcnow().isoformat()
            elif old_status == "completed":
                self._safe_run_github(
                    f'gh issue reopen {issue_number} --repo "{repo}"',
                    "issue reopen",
                )
                metadata.pop("closed_at", None)

            metadata["last_status"] = task.status

        metadata["last_sync"] = datetime.utcnow().isoformat()
        self.database.save_task(task)
    def _load_cascade_rules(self) -> List[Dict[str, Any]]:
        """Load cascade rules from YAML configuration."""
        if yaml is None:
            self.logger.debug("PyYAML not available; skipping cascade rules load")
            return []

        try:
            rules_path = Path.cwd() / ".windsurf" / "cascade-rules.yaml"
            if rules_path.exists():
                with open(rules_path, 'r') as f:
                    config = yaml.safe_load(f)
                    return config.get('cascadeRules', [])
            else:
                self.logger.warning(f"Cascade rules not found at {rules_path}")
                return []
        except Exception as e:
            self.logger.error(f"Failed to load cascade rules: {e}")
            return []

    def _check_cascade_rules(self, task: Task) -> List[Task]:
        """Check if task creation should trigger cascade rules."""
        generated_tasks = []

        for rule in self.cascade_rules:
            if self._matches_rule(task, rule):
                self.logger.info(f"Task {task.id} matches cascade rule: {rule['name']}")
                subtasks = self._generate_subtasks(task, rule)
                generated_tasks.extend(subtasks)

        return generated_tasks

    def _matches_rule(self, task: Task, rule: Dict[str, Any]) -> bool:
        """Check if a task matches a cascade rule."""
        trigger = rule.get('trigger', {})

        # Check tool match
        if trigger.get('whenTool') != 'task-master.task_create':
            return False

        # Check condition
        condition = trigger.get('condition', {})

        # For service component, check if task type or title matches
        if 'component' in condition:
            component = condition['component']
            if component == 'service':
                # Check if task title contains "service" or if type is service
                if 'service' not in task.title.lower() and task.type != 'service':
                    return False
            elif task.type != component:
                return False

        if 'descriptionContains' in condition:
            if condition['descriptionContains'] not in task.description:
                return False

        return True

    def _generate_subtasks(self, parent_task: Task, rule: Dict[str, Any]) -> List[Task]:
        """Generate subtasks based on cascade rule."""
        generated_tasks = []

        for action in rule.get('actions', []):
            if 'createTask' in action:
                task_data = action['createTask']

                # Interpolate variables
                title = self._interpolate_variables(task_data.get('description', ''), parent_task)
                description = title

                metadata = {
                    'cascade_generated': True,
                    'cascade_rule': rule['name'],
                    'parent_task': parent_task.id
                }

                extra_metadata = task_data.get('metadata', {})
                if isinstance(extra_metadata, dict):
                    metadata = self._deep_merge_dicts(
                        metadata,
                        self._interpolate_structure(extra_metadata, parent_task)
                    )

                # Create subtask
                subtask = Task(
                    title=title,
                    description=description,
                    task_type=task_data.get('component', 'task'),
                    component=task_data.get('component'),
                    priority=task_data.get('priority', 'medium'),
                    labels=task_data.get('labels', []),
                    parent_id=parent_task.id,
                    create_remote_issue=parent_task.create_remote_issue,
                    metadata=metadata
                )

                # Add dependency relationship
                parent_task.subtasks.append(subtask.id)
                subtask.depends_on.append(parent_task.id)

                # Save to database
                self._save_task(subtask)
                generated_tasks.append(subtask)

        return generated_tasks

    def _interpolate_structure(self, data: Any, task: Task) -> Any:
        """Recursively interpolate template variables in cascade metadata."""
        if isinstance(data, str):
            return self._interpolate_variables(data, task)

        if isinstance(data, list):
            return [self._interpolate_structure(item, task) for item in data]

        if isinstance(data, dict):
            return {key: self._interpolate_structure(value, task) for key, value in data.items()}

        return data

    def _deep_merge_dicts(self, base: Dict[str, Any], extra: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries, preferring values from the extra dict."""
        merged = dict(base)

        for key, value in extra.items():
            if (
                key in merged
                and isinstance(merged[key], dict)
                and isinstance(value, dict)
            ):
                merged[key] = self._deep_merge_dicts(merged[key], value)
            else:
                merged[key] = value

        return merged

    def _interpolate_variables(self, template: str, task: Task) -> str:
        """Interpolate variables in cascade rule templates."""
        # Simple variable interpolation
        return template.replace('${component}', task.component or 'unknown')

    def _save_task(self, task: Task):
        """Save task to database."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()

            cursor.execute('''
                INSERT OR REPLACE INTO tasks
                (id, title, description, type, component, priority, status, assignee, labels,
                 parent_id, project_id, created_at, updated_at, completed_at, metadata, depends_on, blocked_by, subtasks, create_remote_issue)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                task.id, task.title, task.description, task.type, task.component, task.priority,
                task.status, task.assignee, json.dumps(task.labels),
                task.parent_id, task.project_id, task.created_at.isoformat() if task.created_at else None,
                task.updated_at.isoformat() if task.updated_at else None,
                task.completed_at.isoformat() if task.completed_at else None,
                json.dumps(task.metadata), json.dumps(task.depends_on),
                json.dumps(task.blocked_by), json.dumps(task.subtasks),
                int(bool(getattr(task, "create_remote_issue", True)))
            ))

            conn.commit()
        finally:
            conn.close()

    async def setup_tools(self):
        """Setup task management tools."""
        # Task CRUD operations
        self.register_tool(Tool(
            "task_create",
            "Create a new task",
            {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Task title"
                    },
                    "description": {
                        "type": "string",
                        "description": "Task description"
                    },
                    "type": {
                        "type": "string",
                        "description": "Task type",
                        "enum": ["task", "issue", "bug", "feature", "epic"],
                        "default": "task"
                    },
                    "priority": {
                        "type": "string",
                        "description": "Task priority",
                        "enum": ["low", "medium", "high", "critical"],
                        "default": "medium"
                    },
                    "assignee": {
                        "type": "string",
                        "description": "Task assignee"
                    },
                    "labels": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Task labels"
                    },
                    "project_id": {
                        "type": "string",
                        "description": "Project ID"
                    },
                    "parent_id": {
                        "type": "string",
                        "description": "Parent task ID for subtasks"
                    },
                    "depends_on": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Task IDs this task depends on"
                    },
                    "create_remote_issue": {
                        "type": "boolean",
                        "description": "Whether to open a remote issue",
                        "default": True
                    },
                    "github_issue_number": {
                        "type": "integer",
                        "description": "GitHub issue number associated with this task"
                    },
                },
                "required": ["title"]
            },
            self.task_create
        ))

        self.register_tool(Tool(
            "task_get",
            "Get task details",
            {
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "Task ID"
                    }
                },
                "required": ["task_id"]
            },
            self.task_get
        ))

        self.register_tool(Tool(
            "task_update",
            "Update task information",
            {
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "Task ID"
                    },
                    "title": {
                        "type": "string",
                        "description": "Task title"
                    },
                    "description": {
                        "type": "string",
                        "description": "Task description"
                    },
                    "status": {
                        "type": "string",
                        "description": "Task status",
                        "enum": ["open", "in_progress", "completed", "cancelled"]
                    },
                    "priority": {
                        "type": "string",
                        "description": "Task priority",
                        "enum": ["low", "medium", "high", "critical"]
                    },
                    "assignee": {
                        "type": "string",
                        "description": "Task assignee"
                    },
                    "labels": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Task labels"
                    },
                    "depends_on": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Task IDs this task depends on"
                    },
                    "github_issue_number": {
                        "type": "integer",
                        "description": "GitHub issue number associated with this task"
                    },
                },
                "required": ["task_id"]
            },
            self.task_update
        ))

        self.register_tool(Tool(
            "task_list",
            "List tasks with optional filtering",
            {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "description": "Filter by status",
                        "enum": ["open", "in_progress", "completed", "cancelled"]
                    },
                    "priority": {
                        "type": "string",
                        "description": "Filter by priority",
                        "enum": ["low", "medium", "high", "critical"]
                    },
                    "assignee": {
                        "type": "string",
                        "description": "Filter by assignee"
                    },
                    "project_id": {
                        "type": "string",
                        "description": "Filter by project"
                    },
                    "parent_id": {
                        "type": "string",
                        "description": "Filter by parent task"
                    },
                    "labels": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Filter by labels (must have all specified labels)"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum tasks to return",
                        "minimum": 1,
                        "maximum": 1000,
                        "default": 50
                    }
                }
            },
            self.task_list
        ))

        self.register_tool(Tool(
            "task_delete",
            "Delete a task",
            {
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "Task ID to delete"
                    }
                },
                "required": ["task_id"]
            },
            self.task_delete
        ))

        # Task relationships
        self.register_tool(Tool(
            "task_link",
            "Create dependency relationship between tasks",
            {
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "Task ID"
                    },
                    "depends_on": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Task IDs this task depends on"
                    },
                    "blocks": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Task IDs this task blocks"
                    }
                },
                "required": ["task_id"]
            },
            self.task_link
        ))

        # Project management
        self.register_tool(Tool(
            "project_create",
            "Create a new project",
            {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Project name"
                    },
                    "description": {
                        "type": "string",
                        "description": "Project description"
                    }
                },
                "required": ["name"]
            },
            self.project_create
        ))

        self.register_tool(Tool(
            "project_list",
            "List all projects",
            {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "description": "Filter by status",
                        "enum": ["active", "completed", "archived"]
                    }
                }
            },
            self.project_list
        ))

    async def task_create(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new task with cascade rule processing."""
        title = params["title"]
        description = params.get("description", "")
        task_type = params.get("type", "task")
        component = params.get("component")
        priority = params.get("priority", "medium")
        assignee = params.get("assignee")
        labels = params.get("labels") or []
        project_id = params.get("project_id")
        parent_id = params.get("parent_id")
        github_issue_number = params.get("github_issue_number")
        depends_on = params.get("depends_on", [])
        metadata = params.get("metadata", {})
        requested_remote_issue = params.get("create_remote_issue", True)
        create_remote_issue = self._should_create_remote_issue(
            requested_remote_issue, labels
        )

        # Create task object
        task = Task(
            title=title,
            description=description,
            task_type=task_type,
            component=component,
            priority=priority,
            assignee=assignee,
            labels=labels,
            parent_id=parent_id,
            project_id=project_id,
            metadata=metadata,
            create_remote_issue=create_remote_issue,
        )

        # Set github issue number if provided
        if github_issue_number:
            task.github_issue_number = github_issue_number

        # Set dependencies
        task.depends_on = depends_on

        # Validate parent exists if specified
        if parent_id:
            parent_task = self.database.get_task(parent_id)
            if not parent_task:
                raise MCPError("INVALID_PARENT", f"Parent task not found: {parent_id}")

            # Add this task to parent's subtasks
            parent_task.subtasks.append(task.id)
            self.database.save_task(parent_task)

        # Validate project exists if specified
        if project_id:
            project = self.database.get_project(project_id)
            if not project:
                raise MCPError("INVALID_PROJECT", f"Project not found: {project_id}")

        # Save task
        if not self.database.save_task(task):
            raise MCPError("DATABASE_ERROR", "Failed to save task")

        # Check and apply cascade rules
        generated_tasks = self._check_cascade_rules(task)
        for generated_task in generated_tasks:
            self.logger.info(f"Generated cascade task: {generated_task.title}")
            # Save generated tasks to database
            self.database.save_task(generated_task)

        if task.create_remote_issue:
            self._create_remote_issue_for_task(task)

        for generated_task in generated_tasks:
            if generated_task.create_remote_issue:
                self._create_remote_issue_for_task(generated_task)

        persisted_task = self.database.get_task(task.id) or task
        persisted_cascades: List[Task] = []
        for generated_task in generated_tasks:
            persisted = self.database.get_task(generated_task.id) or generated_task
            persisted_cascades.append(persisted)

        return {
            "created": True,
            "task": persisted_task.to_dict(),
            "cascade_generated": len(generated_tasks),
            "cascade_tasks": [t.to_dict() for t in persisted_cascades]
        }

    async def task_get(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get task details."""
        task_id = params["task_id"]

        task = self.database.get_task(task_id)
        if not task:
            raise MCPError("TASK_NOT_FOUND", f"Task not found: {task_id}")

        return {
            "task": task.to_dict()
        }

    async def task_update(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Update task information."""
        task_id = params["task_id"]

        task = self.database.get_task(task_id)
        if not task:
            raise MCPError("TASK_NOT_FOUND", f"Task not found: {task_id}")

        requested_remote_issue = params.get("create_remote_issue", task.create_remote_issue)

        old_title = task.title
        old_description = task.description
        old_status = task.status

        # Update fields if provided
        if "title" in params:
            task.title = params["title"]
        if "description" in params:
            task.description = params["description"]
        if "status" in params:
            old_status = task.status
            task.status = params["status"]

            # Set completed timestamp if newly completed
            if old_status != "completed" and params["status"] == "completed":
                task.completed_at = datetime.utcnow()

        if "priority" in params:
            task.priority = params["priority"]
        if "assignee" in params:
            task.assignee = params["assignee"]
        if "labels" in params:
            task.labels = params["labels"]
        if "github_issue_number" in params:
            task.github_issue_number = params["github_issue_number"]
        if "metadata" in params:
            task.metadata.update(params["metadata"])

        task.create_remote_issue = self._should_create_remote_issue(
            requested_remote_issue, task.labels
        )

        task.updated_at = datetime.utcnow()

        # Save updated task
        if not self.database.save_task(task):
            raise MCPError("DATABASE_ERROR", "Failed to update task")

        status_changed = "status" in params and params["status"] != old_status
        title_changed = "title" in params and params["title"] != old_title
        description_changed = "description" in params and params["description"] != old_description

        if task.create_remote_issue:
            self._sync_remote_issue_on_update(
                task,
                old_status,
                status_changed,
                title_changed,
                description_changed,
            )

        persisted_task = self.database.get_task(task.id) or task

        return {
            "updated": True,
            "task": persisted_task.to_dict()
        }

    async def task_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List tasks with optional filtering."""
        filters = {k: v for k, v in params.items() if v is not None}

        tasks = self.database.list_tasks(filters)

        return {
            "tasks": [task.to_dict() for task in tasks],
            "count": len(tasks),
            "filters": filters
        }

    async def task_delete(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Delete a task."""
        task_id = params["task_id"]

        task = self.database.get_task(task_id)
        if not task:
            raise MCPError("TASK_NOT_FOUND", f"Task not found: {task_id}")

        # Delete the task
        deleted = self.database.delete_task(task_id)

        return {
            "deleted": deleted,
            "task_id": task_id
        }

    async def task_link(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create dependency relationship between tasks."""
        task_id = params["task_id"]
        depends_on = params.get("depends_on", [])
        blocks = params.get("blocks", [])

        task = self.database.get_task(task_id)
        if not task:
            raise MCPError("TASK_NOT_FOUND", f"Task not found: {task_id}")

        # Validate dependency tasks exist
        for dep_id in depends_on:
            dep_task = self.database.get_task(dep_id)
            if not dep_task:
                raise MCPError("INVALID_DEPENDENCY", f"Dependency task not found: {dep_id}")

        # Validate blocked tasks exist
        for block_id in blocks:
            block_task = self.database.get_task(block_id)
            if not block_task:
                raise MCPError("INVALID_BLOCKED_TASK", f"Blocked task not found: {block_id}")

            # Add this task to the blocked task's dependencies
            if task_id not in block_task.depends_on:
                block_task.depends_on.append(task_id)
                self.database.save_task(block_task)

        # Update current task dependencies
        task.depends_on = depends_on
        task.updated_at = datetime.utcnow()

        # Save updated task
        if not self.database.save_task(task):
            raise MCPError("DATABASE_ERROR", "Failed to update task dependencies")

        return {
            "linked": True,
            "task_id": task_id,
            "depends_on": depends_on,
            "blocks": blocks
        }

    async def project_create(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new project."""
        name = params["name"]
        description = params.get("description", "")

        project = TaskProject(name=name, description=description)

        if not self.database.save_project(project):
            raise MCPError("DATABASE_ERROR", "Failed to save project")

        return {
            "created": True,
            "project": project.to_dict()
        }

    async def project_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List all projects."""
        status_filter = params.get("status")

        projects = self.database.list_projects()

        # Apply status filter if provided
        if status_filter:
            projects = [p for p in projects if p.status == status_filter]

        return {
            "projects": [project.to_dict() for project in projects],
            "count": len(projects),
            "status_filter": status_filter
        }


async def main():
    """Main server entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Task Master MCP Server")
    parser.add_argument(
        "--db-path",
        default="./data/tasks.db",
        help="Database file path (default: ./data/tasks.db)"
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
        server = TaskMasterMCPServer(db_path=args.db_path)

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
