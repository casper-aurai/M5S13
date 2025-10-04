#!/usr/bin/env python3
"""
Task Master Integration Server

Connects MCP ecosystem with GitHub Issues for task management and tracking.
Provides seamless task creation, tracking, and synchronization using GitHub CLI.
"""
import asyncio
import json
import logging
import os
import re
import subprocess
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

try:
    import aiofiles
    import aiohttp
    from aiohttp import web
except ImportError:
    aiofiles = None
    aiohttp = None
    web = None

try:
    from .base_mcp_server import MCPServer, MCPError, Tool
except ImportError:
    # For standalone execution
    from base_mcp_server import MCPServer, MCPError, Tool


class TaskStatus(Enum):
    """Task status enumeration."""
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    """Task priority enumeration."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class Task:
    """Task data structure."""
    id: str
    title: str
    description: str
    status: TaskStatus
    priority: TaskPriority
    labels: List[str]
    assignee: Optional[str]
    github_issue_number: Optional[int]
    github_repo: Optional[str]
    created_at: str
    updated_at: str
    created_by: str
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary."""
        return {
            **asdict(self),
            "status": self.status.value,
            "priority": self.priority.value,
            "github_issue_number": self.github_issue_number,
            "github_repo": self.github_repo
        }


class TaskMasterIntegrationMCPServer(MCPServer):
    """Task Master Integration Server implementation."""

    def __init__(
        self,
        github_token: Optional[str] = None,
        github_repo: Optional[str] = None,
        storage_path: str = "./task_storage",
        enable_webhooks: bool = True,
        webhook_port: int = 8083
    ):
        super().__init__("task_master_integration", "1.0.0")

        self.github_token = github_token or os.getenv("GITHUB_TOKEN")
        self.github_repo = github_repo or os.getenv("GITHUB_REPOSITORY")
        self.storage_path = Path(storage_path)
        self.enable_webhooks = enable_webhooks
        self.webhook_port = webhook_port

        # Task storage
        self.tasks: Dict[str, Task] = {}
        self.task_labels: Set[str] = set()

        # GitHub integration
        self.github_owner = None
        self.github_repo_name = None

        # Webhook server
        self.webhook_app: Optional[web.Application] = None
        self.webhook_runner: Optional[web.AppRunner] = None
        self.webhook_site: Optional[web.TCPSite] = None

        # Parse GitHub repo if provided
        if self.github_repo:
            self._parse_github_repo()

    def _parse_github_repo(self):
        """Parse GitHub repository owner/name from repo string."""
        if "/" in self.github_repo:
            self.github_owner, self.github_repo_name = self.github_repo.split("/", 1)

    async def connect(self):
        """Initialize storage and test GitHub connection."""
        # Create storage directories
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # Load existing tasks
        await self._load_tasks()

        # Test GitHub connection if token provided
        if self.github_token:
            await self._test_github_connection()

        logging.info(f"Task Master Integration initialized with {len(self.tasks)} tasks")

    async def disconnect(self):
        """Save tasks and cleanup."""
        await self._save_tasks()

        # Stop webhook server if running
        if self.webhook_site:
            await self.webhook_site.stop()

    async def _load_tasks(self):
        """Load tasks from storage."""
        tasks_file = self.storage_path / "tasks.json"

        if tasks_file.exists():
            try:
                async with aiofiles.open(tasks_file, 'r') as f:
                    content = await f.read()
                    data = json.loads(content)

                    for task_data in data.get("tasks", []):
                        task = Task(**{
                            k: v for k, v in task_data.items()
                            if k in ['id', 'title', 'description', 'status', 'priority',
                                   'labels', 'assignee', 'github_issue_number', 'github_repo',
                                   'created_at', 'updated_at', 'created_by', 'metadata']
                        })
                        # Convert enum values
                        task.status = TaskStatus(task_data.get("status", "todo"))
                        task.priority = TaskPriority(task_data.get("priority", "medium"))

                        self.tasks[task.id] = task
                        self.task_labels.update(task.labels)

            except Exception as e:
                logging.error(f"Error loading tasks: {e}")

    async def _save_tasks(self):
        """Save tasks to storage."""
        tasks_file = self.storage_path / "tasks.json"

        try:
            tasks_data = {
                "tasks": [task.to_dict() for task in self.tasks.values()],
                "labels": list(self.task_labels),
                "saved_at": datetime.utcnow().isoformat()
            }

            async with aiofiles.open(tasks_file, 'w') as f:
                await f.write(json.dumps(tasks_data, indent=2))

        except Exception as e:
            logging.error(f"Error saving tasks: {e}")

    async def _test_github_connection(self):
        """Test GitHub connection and authentication."""
        try:
            # Test GitHub CLI authentication
            result = subprocess.run(
                ["gh", "auth", "status"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                logging.warning("GitHub CLI not authenticated")
                return False

            # Parse current repo context
            if not self.github_repo:
                repo_result = subprocess.run(
                    ["gh", "repo", "view", "--json", "owner,name"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                if repo_result.returncode == 0:
                    try:
                        repo_data = json.loads(repo_result.stdout)
                        self.github_owner = repo_data.get("owner", {}).get("login")
                        self.github_repo_name = repo_data.get("name")
                        logging.info(f"GitHub repo context: {self.github_owner}/{self.github_repo_name}")
                    except:
                        pass

            return True

        except Exception as e:
            logging.error(f"GitHub connection test failed: {e}")
            return False

    def _run_github_command(self, cmd: List[str], timeout: int = 30) -> Tuple[int, str, str]:
        """Run GitHub CLI command safely."""
        try:
            env = os.environ.copy()
            if self.github_token:
                env["GITHUB_TOKEN"] = self.github_token

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env
            )

            return result.returncode, result.stdout, result.stderr

        except subprocess.TimeoutExpired:
            return -1, "", "Command timed out"
        except Exception as e:
            return -1, "", str(e)

    async def setup_tools(self):
        """Setup Task Master Integration tools."""
        # Task CRUD operations
        self.register_tool(Tool(
            "task_create",
            "Create a new task",
            {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Task title"},
                    "description": {"type": "string", "description": "Task description"},
                    "priority": {"type": "string", "enum": ["low", "medium", "high", "urgent"], "default": "medium"},
                    "labels": {"type": "array", "items": {"type": "string"}, "description": "Task labels"},
                    "assignee": {"type": "string", "description": "GitHub username to assign"},
                    "github_issue": {"type": "boolean", "description": "Create GitHub issue", "default": True},
                    "created_by": {"type": "string", "description": "Task creator"}
                },
                "required": ["title", "description", "created_by"]
            },
            self.task_create
        ))

        self.register_tool(Tool(
            "task_get",
            "Get a specific task",
            {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID"}
                },
                "required": ["task_id"]
            },
            self.task_get
        ))

        self.register_tool(Tool(
            "task_update",
            "Update an existing task",
            {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID"},
                    "title": {"type": "string", "description": "Task title"},
                    "description": {"type": "string", "description": "Task description"},
                    "status": {"type": "string", "enum": ["todo", "in_progress", "in_review", "completed", "cancelled"]},
                    "priority": {"type": "string", "enum": ["low", "medium", "high", "urgent"]},
                    "labels": {"type": "array", "items": {"type": "string"}, "description": "Task labels"},
                    "assignee": {"type": "string", "description": "GitHub username to assign"},
                    "updated_by": {"type": "string", "description": "User making update"}
                },
                "required": ["task_id", "updated_by"]
            },
            self.task_update
        ))

        self.register_tool(Tool(
            "task_delete",
            "Delete a task",
            {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID"},
                    "deleted_by": {"type": "string", "description": "User deleting task"}
                },
                "required": ["task_id", "deleted_by"]
            },
            self.task_delete
        ))

        # Task listing and filtering
        self.register_tool(Tool(
            "task_list",
            "List tasks with filtering",
            {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["todo", "in_progress", "in_review", "completed", "cancelled"]},
                    "priority": {"type": "string", "enum": ["low", "medium", "high", "urgent"]},
                    "labels": {"type": "array", "items": {"type": "string"}, "description": "Filter by labels"},
                    "assignee": {"type": "string", "description": "Filter by assignee"},
                    "github_issue": {"type": "boolean", "description": "Filter by GitHub issue presence"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 1000, "default": 100},
                    "offset": {"type": "integer", "minimum": 0, "default": 0}
                }
            },
            self.task_list
        ))

        # GitHub integration
        self.register_tool(Tool(
            "task_sync_github",
            "Sync tasks with GitHub issues",
            {
                "type": "object",
                "properties": {
                    "direction": {"type": "string", "enum": ["to_github", "from_github", "bidirectional"], "default": "bidirectional"},
                    "force": {"type": "boolean", "description": "Force sync even if no changes", "default": False}
                }
            },
            self.task_sync_github
        ))

        self.register_tool(Tool(
            "task_github_create",
            "Create GitHub issue from task",
            {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID"},
                    "repo": {"type": "string", "description": "GitHub repository (owner/repo)"},
                    "created_by": {"type": "string", "description": "User creating issue"}
                },
                "required": ["task_id", "created_by"]
            },
            self.task_github_create
        ))

        self.register_tool(Tool(
            "task_github_update",
            "Update GitHub issue from task",
            {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID"},
                    "updated_by": {"type": "string", "description": "User updating issue"}
                },
                "required": ["task_id", "updated_by"]
            },
            self.task_github_update
        ))

        # Bulk operations
        self.register_tool(Tool(
            "task_bulk_create",
            "Create multiple tasks",
            {
                "type": "object",
                "properties": {
                    "tasks": {"type": "array", "items": {"type": "object"}, "description": "List of task objects"},
                    "created_by": {"type": "string", "description": "User creating tasks"}
                },
                "required": ["tasks", "created_by"]
            },
            self.task_bulk_create
        ))

        self.register_tool(Tool(
            "task_bulk_update",
            "Update multiple tasks",
            {
                "type": "object",
                "properties": {
                    "updates": {"type": "array", "items": {"type": "object"}, "description": "List of task updates"},
                    "updated_by": {"type": "string", "description": "User making updates"}
                },
                "required": ["updates", "updated_by"]
            },
            self.task_bulk_update
        ))

        # Migration tools
        self.register_tool(Tool(
            "task_migrate_from_issues",
            "Migrate existing GitHub issues to tasks",
            {
                "type": "object",
                "properties": {
                    "repo": {"type": "string", "description": "GitHub repository (owner/repo)"},
                    "labels": {"type": "array", "items": {"type": "string"}, "description": "Filter by labels"},
                    "state": {"type": "string", "enum": ["open", "closed", "all"], "default": "open"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 1000, "default": 100}
                }
            },
            self.task_migrate_from_issues
        ))

    async def start(self):
        """Start the Task Master Integration server."""
        # Connect to storage and GitHub
        await self.connect()

        # Start webhook server if enabled
        if self.enable_webhooks:
            await self._start_webhook_server()

        try:
            # Call parent start method
            await super().start()
        except Exception:
            # Ensure cleanup on error
            await self.disconnect()
            raise

    def stop(self):
        """Stop the Task Master Integration server."""
        # Stop webhook server if running
        if self.webhook_site:
            asyncio.create_task(self._stop_webhook_server())

        # Call parent stop method
        super().stop()

    async def _start_webhook_server(self):
        """Start webhook server for GitHub events."""
        self.webhook_app = web.Application()

        # Webhook endpoints
        self.webhook_app.router.add_post('/webhooks/github', self._handle_github_webhook)
        self.webhook_app.router.add_get('/webhooks/health', self._handle_webhook_health)

        # Start server
        self.webhook_runner = web.AppRunner(self.webhook_app)
        await self.webhook_runner.setup()

        self.webhook_site = web.TCPSite(self.webhook_runner, 'localhost', self.webhook_port)
        await self.webhook_site.start()

        logging.info(f"Webhook server started on http://localhost:{self.webhook_port}")

    async def _stop_webhook_server(self):
        """Stop webhook server."""
        if self.webhook_site:
            await self.webhook_site.stop()
        if self.webhook_runner:
            await self.webhook_runner.cleanup()

    async def _handle_github_webhook(self, request):
        """Handle GitHub webhook events."""
        try:
            # Verify webhook signature if secret provided
            # For now, accept all webhooks (should add signature verification)

            event_type = request.headers.get('X-GitHub-Event', 'unknown')
            payload = await request.json()

            logging.info(f"Received GitHub webhook: {event_type}")

            # Process webhook based on event type
            if event_type == "issues":
                await self._process_issue_webhook(payload)
            elif event_type == "issue_comment":
                await self._process_issue_comment_webhook(payload)

            return web.Response(text="OK")

        except Exception as e:
            logging.error(f"Webhook processing error: {e}")
            return web.Response(text="Error", status=500)

    async def _handle_webhook_health(self, request):
        """Handle webhook health check."""
        return web.Response(text="OK")

    async def _process_issue_webhook(self, payload):
        """Process GitHub issue webhook."""
        action = payload.get("action")
        issue = payload.get("issue", {})

        if not issue or action not in ["opened", "edited", "closed", "reopened"]:
            return

        issue_number = issue.get("number")
        if not issue_number:
            return

        # Find corresponding task
        for task in self.tasks.values():
            if (task.github_issue_number == issue_number and
                task.github_repo == f"{self.github_owner}/{self.github_repo_name}"):

                # Update task based on issue state
                old_status = task.status

                if action == "closed":
                    task.status = TaskStatus.COMPLETED
                elif action in ["opened", "reopened"]:
                    task.status = TaskStatus.TODO
                elif action == "edited":
                    # Update title and description if changed
                    if task.title != issue.get("title"):
                        task.title = issue.get("title", task.title)
                    if task.description != issue.get("body", ""):
                        task.description = issue.get("body", task.description)

                if task.status != old_status:
                    task.updated_at = datetime.utcnow().isoformat()

                logging.info(f"Updated task {task.id} from GitHub webhook")
                break

    async def _process_issue_comment_webhook(self, payload):
        """Process GitHub issue comment webhook."""
        # Implementation for comment processing
        # Could update task status based on comment content
        pass

    def _create_task_from_issue(self, issue_data: Dict[str, Any]) -> Task:
        """Create task from GitHub issue data."""
        issue = issue_data.get("issue", issue_data)

        # Map GitHub labels to priority
        priority_map = {"urgent": TaskPriority.URGENT, "high": TaskPriority.HIGH}
        priority = TaskPriority.MEDIUM

        for label in issue.get("labels", []):
            label_name = label.get("name", "").lower()
            if label_name in priority_map:
                priority = priority_map[label_name]
                break

        # Map GitHub state to task status
        state_map = {"open": TaskStatus.TODO, "closed": TaskStatus.COMPLETED}
        status = state_map.get(issue.get("state", "open"), TaskStatus.TODO)

        return Task(
            id=str(uuid.uuid4()),
            title=issue.get("title", ""),
            description=issue.get("body", ""),
            status=status,
            priority=priority,
            labels=[label.get("name", "") for label in issue.get("labels", [])],
            assignee=issue.get("assignee", {}).get("login") if issue.get("assignee") else None,
            github_issue_number=issue.get("number"),
            github_repo=f"{self.github_owner}/{self.github_repo_name}",
            created_at=datetime.fromisoformat(issue.get("created_at", datetime.utcnow().isoformat()).replace('Z', '+00:00')).isoformat(),
            updated_at=datetime.fromisoformat(issue.get("updated_at", datetime.utcnow().isoformat()).replace('Z', '+00:00')).isoformat(),
            created_by=f"github:{issue.get('user', {}).get('login', 'unknown')}",
            metadata={"github_url": issue.get("html_url")}
        )

    def _update_issue_from_task(self, task: Task) -> Dict[str, Any]:
        """Create GitHub issue update data from task."""
        # Map task priority to labels
        priority_labels = {
            TaskPriority.URGENT: ["urgent"],
            TaskPriority.HIGH: ["high"],
            TaskPriority.MEDIUM: [],
            TaskPriority.LOW: ["low"]
        }

        # Build issue data
        issue_data = {
            "title": task.title,
            "body": task.description,
            "labels": priority_labels.get(task.priority, []) + task.labels
        }

        # Map task status to state
        status_map = {
            TaskStatus.TODO: "open",
            TaskStatus.IN_PROGRESS: "open",
            TaskStatus.IN_REVIEW: "open",
            TaskStatus.COMPLETED: "closed",
            TaskStatus.CANCELLED: "closed"
        }

        if task.status in status_map:
            issue_data["state"] = status_map[task.status]

        return issue_data

    # Tool implementations
    async def task_create(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new task."""
        title = params["title"]
        description = params["description"]
        priority = TaskPriority(params.get("priority", "medium"))
        labels = params.get("labels", [])
        assignee = params.get("assignee")
        github_issue = params.get("github_issue", True)
        created_by = params["created_by"]

        # Create task
        task = Task(
            id=str(uuid.uuid4()),
            title=title,
            description=description,
            status=TaskStatus.TODO,
            priority=priority,
            labels=labels,
            assignee=assignee,
            github_issue_number=None,
            github_repo=self.github_repo,
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat(),
            created_by=created_by,
            metadata={}
        )

        # Add to storage
        self.tasks[task.id] = task
        self.task_labels.update(labels)

        # Create GitHub issue if requested
        if github_issue and self.github_token:
            await self._create_github_issue(task)

        # Save to disk
        await self._save_tasks()

        return {"created": True, "task": task.to_dict()}

    async def task_get(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get a specific task."""
        task_id = params["task_id"]

        if task_id not in self.tasks:
            raise MCPError("TASK_NOT_FOUND", f"Task not found: {task_id}")

        return {"task": self.tasks[task_id].to_dict()}

    async def task_update(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing task."""
        task_id = params["task_id"]

        if task_id not in self.tasks:
            raise MCPError("TASK_NOT_FOUND", f"Task not found: {task_id}")

        task = self.tasks[task_id]

        # Update fields
        if "title" in params:
            task.title = params["title"]
        if "description" in params:
            task.description = params["description"]
        if "status" in params:
            task.status = TaskStatus(params["status"])
        if "priority" in params:
            task.priority = TaskPriority(params["priority"])
        if "labels" in params:
            old_labels = set(task.labels)
            new_labels = set(params["labels"])
            self.task_labels -= old_labels
            self.task_labels.update(new_labels)
            task.labels = params["labels"]
        if "assignee" in params:
            task.assignee = params["assignee"]

        task.updated_at = datetime.utcnow().isoformat()

        # Update GitHub issue if linked
        if task.github_issue_number and self.github_token:
            await self._update_github_issue(task)

        # Save to disk
        await self._save_tasks()

        return {"updated": True, "task": task.to_dict()}

    async def task_delete(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Delete a task."""
        task_id = params["task_id"]

        if task_id not in self.tasks:
            raise MCPError("TASK_NOT_FOUND", f"Task not found: {task_id}")

        task = self.tasks[task_id]

        # Close GitHub issue if linked
        if task.github_issue_number and self.github_token:
            await self._close_github_issue(task)

        # Remove from storage
        del self.tasks[task_id]
        self.task_labels -= set(task.labels)

        # Save to disk
        await self._save_tasks()

        return {"deleted": True}

    async def task_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List tasks with filtering."""
        status = params.get("status")
        priority = params.get("priority")
        labels = params.get("labels", [])
        assignee = params.get("assignee")
        github_issue = params.get("github_issue")
        limit = params.get("limit", 100)
        offset = params.get("offset", 0)

        filtered_tasks = []
        for task in self.tasks.values():
            if status and task.status.value != status:
                continue
            if priority and task.priority.value != priority:
                continue
            if assignee and task.assignee != assignee:
                continue
            if github_issue is not None:
                has_issue = task.github_issue_number is not None
                if github_issue != has_issue:
                    continue
            if labels and not any(label in task.labels for label in labels):
                continue

            filtered_tasks.append(task.to_dict())

        # Apply pagination
        paginated_tasks = filtered_tasks[offset:offset + limit]

        return {
            "tasks": paginated_tasks,
            "total": len(filtered_tasks),
            "filtered": len(paginated_tasks),
            "limit": limit,
            "offset": offset
        }

    async def task_sync_github(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Sync tasks with GitHub issues."""
        direction = params.get("direction", "bidirectional")
        force = params.get("force", False)

        sync_results = {"synced": 0, "created": 0, "updated": 0, "errors": []}

        if direction in ["to_github", "bidirectional"]:
            # Sync tasks to GitHub issues
            for task in self.tasks.values():
                try:
                    if not task.github_issue_number:
                        # Create new GitHub issue
                        await self._create_github_issue(task)
                        sync_results["created"] += 1
                    elif force:
                        # Update existing GitHub issue
                        await self._update_github_issue(task)
                        sync_results["updated"] += 1

                    sync_results["synced"] += 1

                except Exception as e:
                    sync_results["errors"].append(f"Task {task.id}: {str(e)}")

        if direction in ["from_github", "bidirectional"]:
            # Sync GitHub issues to tasks (placeholder)
            # This would fetch issues and create/update corresponding tasks
            pass

        return sync_results

    async def task_github_create(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create GitHub issue from task."""
        task_id = params["task_id"]

        if task_id not in self.tasks:
            raise MCPError("TASK_NOT_FOUND", f"Task not found: {task_id}")

        task = self.tasks[task_id]

        # Create GitHub issue
        await self._create_github_issue(task)

        return {"created": True, "github_issue": task.github_issue_number}

    async def task_github_update(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Update GitHub issue from task."""
        task_id = params["task_id"]

        if task_id not in self.tasks:
            raise MCPError("TASK_NOT_FOUND", f"Task not found: {task_id}")

        task = self.tasks[task_id]

        if not task.github_issue_number:
            raise MCPError("NO_GITHUB_ISSUE", f"Task {task_id} is not linked to a GitHub issue")

        # Update GitHub issue
        await self._update_github_issue(task)

        return {"updated": True}

    async def task_bulk_create(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create multiple tasks."""
        tasks_data = params["tasks"]
        created_by = params["created_by"]

        created_tasks = []
        errors = []

        for task_data in tasks_data:
            try:
                # Add created_by to task data
                task_data["created_by"] = created_by

                # Create individual task
                result = await self.task_create(task_data)
                created_tasks.append(result["task"])

            except Exception as e:
                errors.append(f"Failed to create task '{task_data.get('title', 'Unknown')}': {str(e)}")

        return {
            "created": len(created_tasks),
            "errors": errors,
            "tasks": created_tasks
        }

    async def task_bulk_update(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Update multiple tasks."""
        updates = params["updates"]
        updated_by = params["updated_by"]

        updated_count = 0
        errors = []

        for update in updates:
            try:
                task_id = update.pop("task_id")
                update["updated_by"] = updated_by

                await self.task_update({"task_id": task_id, **update})
                updated_count += 1

            except Exception as e:
                errors.append(f"Failed to update task {update.get('task_id', 'Unknown')}: {str(e)}")

        return {
            "updated": updated_count,
            "errors": errors
        }

    async def task_migrate_from_issues(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate existing GitHub issues to tasks."""
        repo = params.get("repo") or self.github_repo
        labels = params.get("labels", [])
        state = params.get("state", "open")
        limit = params.get("limit", 100)

        if not repo or not self.github_token:
            raise MCPError("GITHUB_REQUIRED", "GitHub repository and token required for migration")

        try:
            # Build GitHub CLI command
            cmd = ["gh", "issue", "list",
                   "--repo", repo,
                   "--state", state,
                   "--limit", str(limit),
                   "--json", "number,title,body,labels,assignees,createdAt,updatedAt,state"]

            returncode, stdout, stderr = self._run_github_command(cmd)

            if returncode != 0:
                raise MCPError("GITHUB_ERROR", f"Failed to fetch issues: {stderr}")

            issues = json.loads(stdout)
            migrated_count = 0
            errors = []

            for issue in issues:
                try:
                    # Check if task already exists for this issue
                    existing_task = None
                    for task in self.tasks.values():
                        if (task.github_issue_number == issue["number"] and
                            task.github_repo == repo):
                            existing_task = task
                            break

                    if existing_task:
                        continue  # Skip existing tasks

                    # Create task from issue
                    task = self._create_task_from_issue({
                        "issue": {
                            **issue,
                            "user": {"login": "migration"}
                        }
                    })

                    # Override repo if specified
                    if repo:
                        task.github_repo = repo

                    self.tasks[task.id] = task
                    migrated_count += 1

                except Exception as e:
                    errors.append(f"Issue #{issue['number']}: {str(e)}")

            # Save all migrated tasks
            await self._save_tasks()

            return {
                "migrated": migrated_count,
                "errors": errors,
                "total_issues": len(issues)
            }

        except Exception as e:
            raise MCPError("MIGRATION_ERROR", f"Migration failed: {str(e)}")

    async def _create_github_issue(self, task: Task):
        """Create GitHub issue from task."""
        if not self.github_token or not self.github_repo:
            return

        try:
            # Prepare issue data
            issue_data = self._update_issue_from_task(task)

            # Create issue via GitHub CLI
            cmd = ["gh", "issue", "create",
                   "--repo", self.github_repo,
                   "--title", issue_data["title"],
                   "--body", issue_data["body"]]

            # Add labels
            for label in issue_data["labels"]:
                cmd.extend(["--label", label])

            # Add assignee if specified
            if task.assignee:
                cmd.extend(["--assignee", task.assignee])

            returncode, stdout, stderr = self._run_github_command(cmd)

            if returncode == 0:
                # Extract issue number from output
                issue_number_match = re.search(r"#(\d+)", stdout)
                if issue_number_match:
                    task.github_issue_number = int(issue_number_match.group(1))
                    task.updated_at = datetime.utcnow().isoformat()
            else:
                logging.error(f"Failed to create GitHub issue: {stderr}")

        except Exception as e:
            logging.error(f"GitHub issue creation error: {e}")

    async def _update_github_issue(self, task: Task):
        """Update GitHub issue from task."""
        if not self.github_token or not task.github_issue_number:
            return

        try:
            # Prepare issue data
            issue_data = self._update_issue_from_task(task)

            # Update issue via GitHub CLI
            cmd = ["gh", "issue", "edit", str(task.github_issue_number),
                   "--repo", task.github_repo,
                   "--title", issue_data["title"],
                   "--body", issue_data["body"]]

            # Clear existing labels and add new ones
            cmd.append("--remove-label")
            cmd.append("*")  # Remove all labels first

            for label in issue_data["labels"]:
                cmd.extend(["--add-label", label])

            # Update assignee if specified
            if task.assignee:
                cmd.extend(["--assignee", task.assignee])
            else:
                cmd.append("--remove-assignee")  # Remove assignee if not specified

            returncode, stdout, stderr = self._run_github_command(cmd)

            if returncode != 0:
                logging.error(f"Failed to update GitHub issue #{task.github_issue_number}: {stderr}")

        except Exception as e:
            logging.error(f"GitHub issue update error: {e}")

    async def _close_github_issue(self, task: Task):
        """Close GitHub issue."""
        if not self.github_token or not task.github_issue_number:
            return

        try:
            cmd = ["gh", "issue", "close", str(task.github_issue_number),
                   "--repo", task.github_repo]

            returncode, stdout, stderr = self._run_github_command(cmd)

            if returncode != 0:
                logging.error(f"Failed to close GitHub issue #{task.github_issue_number}: {stderr}")

        except Exception as e:
            logging.error(f"GitHub issue close error: {e}")


async def main():
    """Main server entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Task Master Integration Server")
    parser.add_argument(
        "--github-token",
        help="GitHub token (default: GITHUB_TOKEN env var)"
    )
    parser.add_argument(
        "--github-repo",
        help="GitHub repository (owner/repo, default: GITHUB_REPOSITORY env var)"
    )
    parser.add_argument(
        "--storage-path",
        default="./task_storage",
        help="Path for task storage (default: ./task_storage)"
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "websocket"],
        default="websocket",
        help="Transport mechanism (default: websocket)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8084,
        help="Port for WebSocket transport (default: 8084)"
    )
    parser.add_argument(
        "--no-webhooks",
        action="store_true",
        help="Disable webhook server"
    )
    parser.add_argument(
        "--webhook-port",
        type=int,
        default=8083,
        help="Port for webhook server (default: 8083)"
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
        server = TaskMasterIntegrationMCPServer(
            github_token=args.github_token,
            github_repo=args.github_repo,
            storage_path=args.storage_path,
            enable_webhooks=not args.no_webhooks,
            webhook_port=args.webhook_port
        )

        # Configure transport
        if args.transport == "websocket":
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
