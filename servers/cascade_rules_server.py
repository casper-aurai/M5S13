#!/usr/bin/env python3
"""
Cascade Rules Management Server

Centralized server for managing and serving cascade rules and patterns.
Provides rule storage, versioning, validation, and distribution for AI agent governance.
"""
import asyncio
import json
import logging
import os
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
    import jsonschema
except ImportError:
    aiofiles = None
    aiohttp = None
    web = None
    jsonschema = None

try:
    from .base_mcp_server import MCPServer, MCPError, Tool
except ImportError:
    # For standalone execution
    from base_mcp_server import MCPServer, MCPError, Tool


class RuleStatus(Enum):
    """Rule status enumeration."""
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class RulePriority(Enum):
    """Rule priority enumeration."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Rule:
    """Rule data structure."""
    id: str
    name: str
    description: str
    category: str
    tags: List[str]
    priority: RulePriority
    status: RuleStatus
    content: Dict[str, Any]
    version: str
    created_at: str
    updated_at: str
    created_by: str
    schema_version: str = "1.0"
    last_change_summary: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert rule to dictionary."""
        return {
            **asdict(self),
            "priority": self.priority.value,
            "status": self.status.value
        }


class CascadeRulesMCPServer(MCPServer):
    """Cascade Rules Management Server implementation."""

    def __init__(
        self,
        storage_path: str = "./rules_storage",
        cache_ttl: int = 300,  # 5 minutes
        max_rules: int = 10000,
        enable_web_ui: bool = True
    ):
        super().__init__("cascade_rules", "1.0.0")

        if not all([aiofiles, aiohttp, jsonschema]):
            raise MCPError(
                "CASCADE_DEPENDENCIES",
                "Required packages not available: aiofiles, aiohttp, jsonschema"
            )

        self.storage_path = Path(storage_path)
        self.cache_ttl = cache_ttl
        self.max_rules = max_rules
        self.enable_web_ui = enable_web_ui

        # Rule storage
        self.rules: Dict[str, Rule] = {}
        self.rule_versions: Dict[str, List[Rule]] = {}
        self.categories: Set[str] = set()
        self.tags: Set[str] = set()

        # Caching
        self.rule_cache: Dict[str, Any] = {}
        self.cache_timestamps: Dict[str, float] = {}

        # Audit logging
        self.audit_log: List[Dict[str, Any]] = []

        # Web server
        self.web_app: Optional[web.Application] = None
        self.web_runner: Optional[web.AppRunner] = None
        self.web_site: Optional[web.TCPSite] = None

        # Rule schema for validation
        self.rule_schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string", "minLength": 1},
                "description": {"type": "string", "minLength": 1},
                "category": {"type": "string", "minLength": 1},
                "tags": {"type": "array", "items": {"type": "string"}},
                "priority": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                "content": {"type": "object"},
                "version": {"type": "string"}
            },
            "required": ["name", "description", "category", "content", "version"]
        }

    async def connect(self):
        """Initialize storage and load existing rules."""
        # Create storage directories
        self.storage_path.mkdir(parents=True, exist_ok=True)
        (self.storage_path / "versions").mkdir(exist_ok=True)
        (self.storage_path / "audit").mkdir(exist_ok=True)

        # Load existing rules
        await self._load_rules()

        # Load audit log
        await self._load_audit_log()

        logging.info(f"Cascade Rules Server initialized with {len(self.rules)} rules")

    async def disconnect(self):
        """Save rules and cleanup."""
        await self._save_rules()
        await self._save_audit_log()

        # Stop web server if running
        if self.web_site:
            await self.web_site.stop()

    async def _load_rules(self):
        """Load rules from storage."""
        rules_file = self.storage_path / "rules.json"

        if rules_file.exists():
            try:
                async with aiofiles.open(rules_file, 'r') as f:
                    content = await f.read()
                    data = json.loads(content)

                    for rule_data in data.get("rules", []):
                        rule = Rule(**{
                            k: v for k, v in rule_data.items()
                            if k in ['id', 'name', 'description', 'category', 'tags',
                                     'priority', 'status', 'content', 'version',
                                     'created_at', 'updated_at', 'created_by', 'schema_version',
                                     'last_change_summary']
                        })
                        # Convert enum values
                        rule.priority = RulePriority(rule_data.get("priority", "medium"))
                        rule.status = RuleStatus(rule_data.get("status", "draft"))

                        self.rules[rule.id] = rule
                        self.categories.add(rule.category)
                        self.tags.update(rule.tags)

                        # Load version history
                        await self._load_rule_versions(rule.id)

            except Exception as e:
                logging.error(f"Error loading rules: {e}")

    async def _load_rule_versions(self, rule_id: str):
        """Load version history for a rule."""
        versions_file = self.storage_path / "versions" / f"{rule_id}.json"

        if versions_file.exists():
            try:
                async with aiofiles.open(versions_file, 'r') as f:
                    content = await f.read()
                    versions_data = json.loads(content)

                    self.rule_versions[rule_id] = []
                    for version_data in versions_data.get("versions", []):
                        rule = Rule(**{
                            k: v for k, v in version_data.items()
                            if k in ['id', 'name', 'description', 'category', 'tags',
                                   'priority', 'status', 'content', 'version',
                                   'created_at', 'updated_at', 'created_by', 'schema_version']
                        })
                        rule.priority = RulePriority(version_data.get("priority", "medium"))
                        rule.status = RuleStatus(version_data.get("status", "draft"))
                        self.rule_versions[rule_id].append(rule)

            except Exception as e:
                logging.error(f"Error loading rule versions for {rule_id}: {e}")

    async def _save_rules(self):
        """Save rules to storage."""
        rules_file = self.storage_path / "rules.json"

        try:
            rules_data = {
                "rules": [rule.to_dict() for rule in self.rules.values()],
                "categories": list(self.categories),
                "tags": list(self.tags),
                "saved_at": datetime.utcnow().isoformat()
            }

            async with aiofiles.open(rules_file, 'w') as f:
                await f.write(json.dumps(rules_data, indent=2))

        except Exception as e:
            logging.error(f"Error saving rules: {e}")

    async def _save_rule_versions(self, rule_id: str):
        """Save version history for a rule."""
        versions_file = self.storage_path / "versions" / f"{rule_id}.json"

        try:
            versions_data = {
                "rule_id": rule_id,
                "versions": [rule.to_dict() for rule in self.rule_versions.get(rule_id, [])],
                "saved_at": datetime.utcnow().isoformat()
            }

            async with aiofiles.open(versions_file, 'w') as f:
                await f.write(json.dumps(versions_data, indent=2))

        except Exception as e:
            logging.error(f"Error saving rule versions for {rule_id}: {e}")

    async def _load_audit_log(self):
        """Load audit log from storage."""
        audit_file = self.storage_path / "audit" / "audit_log.json"

        if audit_file.exists():
            try:
                async with aiofiles.open(audit_file, 'r') as f:
                    content = await f.read()
                    raw_data = json.loads(content)

                    if isinstance(raw_data, dict):
                        entries = raw_data.get("entries", [])
                    else:
                        entries = raw_data

                    for entry in entries:
                        entry.setdefault("summary", "")

                    self.audit_log = entries

            except Exception as e:
                logging.error(f"Error loading audit log: {e}")

    async def _save_audit_log(self):
        """Save audit log to storage."""
        audit_file = self.storage_path / "audit" / "audit_log.json"

        try:
            audit_data = {
                "entries": self.audit_log,
                "saved_at": datetime.utcnow().isoformat()
            }

            async with aiofiles.open(audit_file, 'w') as f:
                await f.write(json.dumps(audit_data, indent=2))

        except Exception as e:
            logging.error(f"Error saving audit log: {e}")

    def _add_audit_entry(
        self,
        action: str,
        rule_id: str,
        details: Dict[str, Any],
        user: str = "system",
        summary: str = ""
    ):
        """Add entry to audit log."""
        entry = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "action": action,
            "rule_id": rule_id,
            "user": user,
            "summary": summary,
            "details": details
        }

        self.audit_log.append(entry)

        # Keep only recent entries (last 1000)
        if len(self.audit_log) > 1000:
            self.audit_log = self.audit_log[-1000:]

    def _validate_rule_content(self, content: Dict[str, Any]) -> bool:
        """Validate rule content against schema."""
        try:
            jsonschema.validate(instance=content, schema=self.rule_schema)
            return True
        except jsonschema.ValidationError as e:
            logging.error(f"Rule validation error: {e.message}")
            return False

    def _check_rule_conflicts(self, new_rule: Rule, existing_rules: List[Rule]) -> List[str]:
        """Check for conflicts with existing rules."""
        conflicts = []

        for existing_rule in existing_rules:
            if (existing_rule.category == new_rule.category and
                existing_rule.status == RuleStatus.ACTIVE and
                new_rule.status == RuleStatus.ACTIVE):

                # Check for overlapping tags or similar names
                overlapping_tags = set(existing_rule.tags) & set(new_rule.tags)
                if overlapping_tags:
                    conflicts.append(
                        f"Tag conflict with rule '{existing_rule.name}': {overlapping_tags}"
                    )

        return conflicts

    async def setup_tools(self):
        """Setup Cascade Rules management tools."""
        # Rule CRUD operations
        self.register_tool(Tool(
            "cascade_rule_create",
            "Create a new cascade rule",
            {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Rule name"},
                    "description": {"type": "string", "description": "Rule description"},
                    "category": {"type": "string", "description": "Rule category"},
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "Rule tags"},
                    "priority": {"type": "string", "enum": ["low", "medium", "high", "critical"], "default": "medium"},
                    "content": {"type": "object", "description": "Rule content"},
                    "created_by": {"type": "string", "description": "Rule creator"},
                    "change_summary": {
                        "type": "string",
                        "description": "Summary of the change",
                        "minLength": 1
                    }
                },
                "required": [
                    "name",
                    "description",
                    "category",
                    "content",
                    "created_by",
                    "change_summary"
                ]
            },
            self.cascade_rule_create
        ))

        self.register_tool(Tool(
            "cascade_rule_get",
            "Get a specific rule",
            {
                "type": "object",
                "properties": {
                    "rule_id": {"type": "string", "description": "Rule ID"},
                    "version": {"type": "string", "description": "Specific version (optional)"}
                },
                "required": ["rule_id"]
            },
            self.cascade_rule_get
        ))

        self.register_tool(Tool(
            "cascade_rule_update",
            "Update an existing rule",
            {
                "type": "object",
                "properties": {
                    "rule_id": {"type": "string", "description": "Rule ID"},
                    "name": {"type": "string", "description": "Rule name"},
                    "description": {"type": "string", "description": "Rule description"},
                    "category": {"type": "string", "description": "Rule category"},
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "Rule tags"},
                    "priority": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                    "content": {"type": "object", "description": "Rule content"},
                    "updated_by": {"type": "string", "description": "User making update"},
                    "change_summary": {
                        "type": "string",
                        "description": "Summary of the change",
                        "minLength": 1
                    }
                },
                "required": ["rule_id", "updated_by", "change_summary"]
            },
            self.cascade_rule_update
        ))

        self.register_tool(Tool(
            "cascade_rule_delete",
            "Delete a rule",
            {
                "type": "object",
                "properties": {
                    "rule_id": {"type": "string", "description": "Rule ID"},
                    "deleted_by": {"type": "string", "description": "User deleting rule"},
                    "change_summary": {
                        "type": "string",
                        "description": "Summary of the change",
                        "minLength": 1
                    }
                },
                "required": ["rule_id", "deleted_by", "change_summary"]
            },
            self.cascade_rule_delete
        ))

        # Rule listing and search
        self.register_tool(Tool(
            "cascade_rule_list",
            "List rules with filtering",
            {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "Filter by category"},
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "Filter by tags"},
                    "status": {"type": "string", "enum": ["draft", "active", "deprecated", "archived"]},
                    "priority": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 1000, "default": 100},
                    "offset": {"type": "integer", "minimum": 0, "default": 0}
                }
            },
            self.cascade_rule_list
        ))

        self.register_tool(Tool(
            "cascade_rule_search",
            "Search rules by content",
            {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "fields": {"type": "array", "items": {"type": "string"}, "description": "Fields to search"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 20}
                },
                "required": ["query"]
            },
            self.cascade_rule_search
        ))

        # Rule lifecycle management
        self.register_tool(Tool(
            "cascade_rule_activate",
            "Activate a rule",
            {
                "type": "object",
                "properties": {
                    "rule_id": {"type": "string", "description": "Rule ID"},
                    "activated_by": {"type": "string", "description": "User activating rule"},
                    "change_summary": {
                        "type": "string",
                        "description": "Summary of the change",
                        "minLength": 1
                    }
                },
                "required": ["rule_id", "activated_by", "change_summary"]
            },
            self.cascade_rule_activate
        ))

        self.register_tool(Tool(
            "cascade_rule_deprecate",
            "Deprecate a rule",
            {
                "type": "object",
                "properties": {
                    "rule_id": {"type": "string", "description": "Rule ID"},
                    "deprecated_by": {"type": "string", "description": "User deprecating rule"},
                    "change_summary": {
                        "type": "string",
                        "description": "Summary of the change",
                        "minLength": 1
                    }
                },
                "required": ["rule_id", "deprecated_by", "change_summary"]
            },
            self.cascade_rule_deprecate
        ))

        # Rule validation and conflicts
        self.register_tool(Tool(
            "cascade_rule_validate",
            "Validate rule content",
            {
                "type": "object",
                "properties": {
                    "content": {"type": "object", "description": "Rule content to validate"}
                },
                "required": ["content"]
            },
            self.cascade_rule_validate
        ))

        self.register_tool(Tool(
            "cascade_rule_check_conflicts",
            "Check for rule conflicts",
            {
                "type": "object",
                "properties": {
                    "rule_id": {"type": "string", "description": "Rule ID to check"}
                },
                "required": ["rule_id"]
            },
            self.cascade_rule_check_conflicts
        ))

        # Categories and tags management
        self.register_tool(Tool(
            "cascade_rule_categories",
            "List all categories",
            {
                "type": "object",
                "properties": {}
            },
            self.cascade_rule_categories
        ))

        self.register_tool(Tool(
            "cascade_rule_tags",
            "List all tags",
            {
                "type": "object",
                "properties": {}
            },
            self.cascade_rule_tags
        ))

        # Audit and history
        self.register_tool(Tool(
            "cascade_rule_history",
            "Get rule version history",
            {
                "type": "object",
                "properties": {
                    "rule_id": {"type": "string", "description": "Rule ID"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 10}
                },
                "required": ["rule_id"]
            },
            self.cascade_rule_history
        ))

        self.register_tool(Tool(
            "cascade_rule_audit",
            "Get audit log entries",
            {
                "type": "object",
                "properties": {
                    "rule_id": {"type": "string", "description": "Filter by rule ID"},
                    "action": {"type": "string", "description": "Filter by action"},
                    "user": {"type": "string", "description": "Filter by user"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 1000, "default": 100}
                }
            },
            self.cascade_rule_audit
        ))

    async def start(self):
        """Start the Cascade Rules server."""
        # Connect to storage
        await self.connect()

        # Start web UI if enabled
        if self.enable_web_ui:
            await self._start_web_server()

        try:
            # Call parent start method
            await super().start()
        except Exception:
            # Ensure cleanup on error
            await self.disconnect()
            raise

    def stop(self):
        """Stop the Cascade Rules server."""
        # Stop web server if running
        if self.web_site:
            asyncio.create_task(self._stop_web_server())

        # Call parent stop method
        super().stop()

    async def _start_web_server(self):
        """Start web server for rule management UI."""
        self.web_app = web.Application()

        # API routes
        self.web_app.router.add_get('/api/rules', self._handle_api_list_rules)
        self.web_app.router.add_get('/api/rules/{rule_id}', self._handle_api_get_rule)
        self.web_app.router.add_post('/api/rules', self._handle_api_create_rule)
        self.web_app.router.add_put('/api/rules/{rule_id}', self._handle_api_update_rule)
        self.web_app.router.add_delete('/api/rules/{rule_id}', self._handle_api_delete_rule)
        self.web_app.router.add_get('/api/categories', self._handle_api_categories)
        self.web_app.router.add_get('/api/tags', self._handle_api_tags)
        self.web_app.router.add_get('/api/audit', self._handle_api_audit)

        # Web UI routes
        self.web_app.router.add_get('/', self._handle_web_ui)
        self.web_app.router.add_get('/rules', self._handle_web_rules)
        self.web_app.router.add_get('/rules/{rule_id}', self._handle_web_rule_detail)
        self.web_app.router.add_static('/static', path=str(self.storage_path / 'static'))

        # Start server
        self.web_runner = web.AppRunner(self.web_app)
        await self.web_runner.setup()

        self.web_site = web.TCPSite(self.web_runner, 'localhost', 8081)
        await self.web_site.start()

        logging.info("Web UI started on http://localhost:8081")

    async def _stop_web_server(self):
        """Stop web server."""
        if self.web_site:
            await self.web_site.stop()
        if self.web_runner:
            await self.web_runner.cleanup()

    async def _handle_api_list_rules(self, request):
        """Handle API request to list rules."""
        try:
            # Parse query parameters
            category = request.query.get('category')
            status = request.query.get('status')
            tags = request.query.getall('tags', [])
            limit = int(request.query.get('limit', 100))
            offset = int(request.query.get('offset', 0))

            # Filter rules
            filtered_rules = []
            for rule in self.rules.values():
                if category and rule.category != category:
                    continue
                if status and rule.status.value != status:
                    continue
                if tags and not any(tag in rule.tags for tag in tags):
                    continue
                filtered_rules.append(rule.to_dict())

            # Apply pagination
            paginated_rules = filtered_rules[offset:offset + limit]

            return web.json_response({
                "rules": paginated_rules,
                "total": len(filtered_rules),
                "limit": limit,
                "offset": offset
            })

        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    async def _handle_api_get_rule(self, request):
        """Handle API request to get specific rule."""
        rule_id = request.match_info['rule_id']

        if rule_id not in self.rules:
            return web.json_response({"error": "Rule not found"}, status=404)

        return web.json_response(self.rules[rule_id].to_dict())

    async def _handle_api_create_rule(self, request):
        """Handle API request to create rule."""
        try:
            data = await request.json()

            # Validate required fields
            required_fields = [
                'name',
                'description',
                'category',
                'content',
                'created_by',
                'change_summary'
            ]
            for field in required_fields:
                if field not in data:
                    return web.json_response({"error": f"Missing field: {field}"}, status=400)

            if not isinstance(data['change_summary'], str) or not data['change_summary'].strip():
                return web.json_response({"error": "Invalid change_summary"}, status=400)

            # Create rule
            rule = await self._create_rule_internal(
                data,
                data['created_by'],
                data['change_summary'].strip()
            )

            return web.json_response(rule.to_dict(), status=201)

        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    async def _handle_api_update_rule(self, request):
        """Handle API request to update rule."""
        try:
            rule_id = request.match_info['rule_id']
            data = await request.json()

            for field in ['updated_by', 'change_summary']:
                if field not in data:
                    return web.json_response({"error": f"Missing field: {field}"}, status=400)

            if not isinstance(data['change_summary'], str) or not data['change_summary'].strip():
                return web.json_response({"error": "Invalid change_summary"}, status=400)

            # Update rule
            rule = await self._update_rule_internal(
                rule_id,
                data,
                data['updated_by'],
                data['change_summary'].strip()
            )

            return web.json_response(rule.to_dict())

        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    async def _handle_api_delete_rule(self, request):
        """Handle API request to delete rule."""
        try:
            rule_id = request.match_info['rule_id']
            query = request.query
            deleted_by = query.get('deleted_by')
            change_summary = query.get('change_summary', '')

            if not deleted_by:
                return web.json_response({"error": "Missing parameter: deleted_by"}, status=400)

            if not isinstance(change_summary, str) or not change_summary.strip():
                return web.json_response({"error": "Missing parameter: change_summary"}, status=400)

            # Delete rule
            await self._delete_rule_internal(rule_id, deleted_by, change_summary.strip())

            return web.json_response({"deleted": True})

        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    async def _handle_api_categories(self, request):
        """Handle API request for categories."""
        return web.json_response({"categories": sorted(list(self.categories))})

    async def _handle_api_tags(self, request):
        """Handle API request for tags."""
        return web.json_response({"tags": sorted(list(self.tags))})

    async def _handle_api_audit(self, request):
        """Handle API request for audit log."""
        limit = int(request.query.get('limit', 100))
        rule_id = request.query.get('rule_id')

        # Filter audit log
        filtered_entries = []
        for entry in reversed(self.audit_log):  # Most recent first
            if rule_id and entry.get('rule_id') != rule_id:
                continue
            filtered_entries.append(entry)
            if len(filtered_entries) >= limit:
                break

        return web.json_response({"entries": filtered_entries})

    async def _handle_web_ui(self, request):
        """Handle web UI root page."""
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Cascade Rules Manager</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                .header { background: #f0f0f0; padding: 20px; border-radius: 5px; }
                .nav { margin: 20px 0; }
                .nav a { margin-right: 20px; text-decoration: none; }
                .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }
                .stat-card { background: #e8f4fd; padding: 15px; border-radius: 5px; text-align: center; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🚀 Cascade Rules Management Server</h1>
                <p>Centralized governance for AI agent rules and patterns</p>
            </div>

            <div class="nav">
                <a href="/rules">📋 Browse Rules</a>
                <a href="/api/categories">🏷️ Categories</a>
                <a href="/api/tags">🏷️ Tags</a>
                <a href="/api/audit">📊 Audit Log</a>
            </div>

            <div class="stats">
                <div class="stat-card">
                    <h3>Total Rules</h3>
                    <div style="font-size: 2em; color: #2563eb;">{len(self.rules)}</div>
                </div>
                <div class="stat-card">
                    <h3>Active Rules</h3>
                    <div style="font-size: 2em; color: #059669;">{len([r for r in self.rules.values() if r.status == RuleStatus.ACTIVE])}</div>
                </div>
                <div class="stat-card">
                    <h3>Categories</h3>
                    <div style="font-size: 2em; color: #7c3aed;">{len(self.categories)}</div>
                </div>
                <div class="stat-card">
                    <h3>Tags</h3>
                    <div style="font-size: 2em; color: #dc2626;">{len(self.tags)}</div>
                </div>
            </div>
        </body>
        </html>
        """
        return web.Response(text=html, content_type='text/html')

    async def _handle_web_rules(self, request):
        """Handle web UI rules listing."""
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Rules - Cascade Rules Manager</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                .header { background: #f0f0f0; padding: 20px; border-radius: 5px; }
                table { width: 100%; border-collapse: collapse; margin: 20px 0; }
                th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
                th { background-color: #f2f2f2; }
                .status-active { color: #059669; }
                .status-draft { color: #6b7280; }
                .priority-high { color: #dc2626; }
                .priority-medium { color: #d97706; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>📋 Cascade Rules</h1>
                <a href="/">← Back to Dashboard</a>
            </div>

            <table>
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>Category</th>
                        <th>Status</th>
                        <th>Priority</th>
                        <th>Version</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
        """

        for rule in self.rules.values():
            html += f"""
                    <tr>
                        <td>{rule.name}</td>
                        <td>{rule.category}</td>
                        <td class="status-{rule.status.value}">{rule.status.value}</td>
                        <td class="priority-{rule.priority.value}">{rule.priority.value}</td>
                        <td>{rule.version}</td>
                        <td><a href="/rules/{rule.id}">View</a></td>
                    </tr>
            """

        html += """
                </tbody>
            </table>
        </body>
        </html>
        """

        return web.Response(text=html, content_type='text/html')

    async def _handle_web_rule_detail(self, request):
        """Handle web UI rule detail page."""
        rule_id = request.match_info['rule_id']

        if rule_id not in self.rules:
            return web.Response(text="Rule not found", status=404)

        rule = self.rules[rule_id]

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{rule.name} - Cascade Rules Manager</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .header {{ background: #f0f0f0; padding: 20px; border-radius: 5px; }}
                .rule-content {{ background: #f8f9fa; padding: 20px; border-radius: 5px; margin: 20px 0; }}
                .tags {{ margin: 10px 0; }}
                .tag {{ display: inline-block; background: #e5e7eb; padding: 4px 8px; margin: 2px; border-radius: 3px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{rule.name}</h1>
                <p>{rule.description}</p>
                <a href="/rules">← Back to Rules</a>
            </div>

            <div class="rule-content">
                <h3>Rule Details</h3>
                <p><strong>Category:</strong> {rule.category}</p>
                <p><strong>Status:</strong> <span class="status-{rule.status.value}">{rule.status.value}</span></p>
                <p><strong>Priority:</strong> <span class="priority-{rule.priority.value}">{rule.priority.value}</span></p>
                <p><strong>Version:</strong> {rule.version}</p>
                <p><strong>Created:</strong> {rule.created_at} by {rule.created_by}</p>

                <div class="tags">
                    <strong>Tags:</strong>
        """

        for tag in rule.tags:
            html += f'<span class="tag">{tag}</span>'

        html += f"""
                </div>

                <h4>Rule Content</h4>
                <pre>{json.dumps(rule.content, indent=2)}</pre>
            </div>
        </body>
        </html>
        """

        return web.Response(text=html, content_type='text/html')

    async def _create_rule_internal(
        self,
        rule_data: Dict[str, Any],
        created_by: str,
        change_summary: str
    ) -> Rule:
        """Internal method to create a rule."""
        # Generate rule ID
        rule_id = str(uuid.uuid4())

        # Validate content
        if not self._validate_rule_content(rule_data):
            raise MCPError("INVALID_RULE", "Rule content validation failed")

        # Check for conflicts
        new_rule = Rule(
            id=rule_id,
            name=rule_data["name"],
            description=rule_data["description"],
            category=rule_data["category"],
            tags=rule_data.get("tags", []),
            priority=RulePriority(rule_data.get("priority", "medium")),
            status=RuleStatus.DRAFT,
            content=rule_data["content"],
            version=rule_data.get("version", "1.0.0"),
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat(),
            created_by=created_by,
            last_change_summary=change_summary
        )

        # Check for conflicts
        existing_rules = [r for r in self.rules.values() if r.category == new_rule.category]
        conflicts = self._check_rule_conflicts(new_rule, existing_rules)

        if conflicts:
            raise MCPError("RULE_CONFLICT", f"Rule conflicts detected: {'; '.join(conflicts)}")

        # Add to storage
        self.rules[rule_id] = new_rule
        self.categories.add(new_rule.category)
        self.tags.update(new_rule.tags)

        # Add to version history
        if rule_id not in self.rule_versions:
            self.rule_versions[rule_id] = []
        self.rule_versions[rule_id].append(new_rule)

        # Audit log
        self._add_audit_entry(
            "create",
            rule_id,
            {"rule_name": new_rule.name},
            created_by,
            summary=change_summary
        )

        # Save to disk
        await self._save_rules()
        await self._save_rule_versions(rule_id)

        return new_rule

    async def _update_rule_internal(
        self,
        rule_id: str,
        update_data: Dict[str, Any],
        updated_by: str,
        change_summary: str
    ) -> Rule:
        """Internal method to update a rule."""
        if rule_id not in self.rules:
            raise MCPError("RULE_NOT_FOUND", f"Rule not found: {rule_id}")

        current_rule = self.rules[rule_id]

        # Create new version
        updated_rule = Rule(
            id=rule_id,
            name=update_data.get("name", current_rule.name),
            description=update_data.get("description", current_rule.description),
            category=update_data.get("category", current_rule.category),
            tags=update_data.get("tags", current_rule.tags),
            priority=RulePriority(update_data.get("priority", current_rule.priority.value)),
            status=current_rule.status,  # Status changes handled separately
            content=update_data.get("content", current_rule.content),
            version=update_data.get("version", current_rule.version),
            created_at=current_rule.created_at,
            updated_at=datetime.utcnow().isoformat(),
            created_by=current_rule.created_by,
            last_change_summary=change_summary
        )

        # Validate updated content
        if not self._validate_rule_content(updated_rule.__dict__):
            raise MCPError("INVALID_RULE", "Updated rule content validation failed")

        # Check for conflicts if category or tags changed
        if (updated_rule.category != current_rule.category or
            set(updated_rule.tags) != set(current_rule.tags)):
            existing_rules = [r for r in self.rules.values()
                            if r.id != rule_id and r.category == updated_rule.category]
            conflicts = self._check_rule_conflicts(updated_rule, existing_rules)

            if conflicts:
                raise MCPError("RULE_CONFLICT", f"Rule conflicts detected: {'; '.join(conflicts)}")

        # Update storage
        self.rules[rule_id] = updated_rule

        # Update categories and tags
        self.categories.discard(current_rule.category)
        self.categories.add(updated_rule.category)

        self.tags -= set(current_rule.tags)
        self.tags.update(updated_rule.tags)

        # Add to version history
        if rule_id not in self.rule_versions:
            self.rule_versions[rule_id] = []
        self.rule_versions[rule_id].append(updated_rule)

        # Audit log
        self._add_audit_entry(
            "update",
            rule_id,
            {"changes": update_data},
            updated_by,
            summary=change_summary
        )

        # Save to disk
        await self._save_rules()
        await self._save_rule_versions(rule_id)

        return updated_rule

    async def _delete_rule_internal(
        self,
        rule_id: str,
        deleted_by: str,
        change_summary: str
    ):
        """Internal method to delete a rule."""
        if rule_id not in self.rules:
            raise MCPError("RULE_NOT_FOUND", f"Rule not found: {rule_id}")

        rule = self.rules[rule_id]

        # Remove from storage
        del self.rules[rule_id]

        # Update categories and tags
        self.categories.discard(rule.category)
        self.tags -= set(rule.tags)

        # Audit log
        self._add_audit_entry(
            "delete",
            rule_id,
            {"rule_name": rule.name},
            deleted_by,
            summary=change_summary
        )

        # Save to disk
        await self._save_rules()

    # Tool implementations
    async def cascade_rule_create(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new rule."""
        summary = params.get("change_summary", "").strip()
        if not summary:
            raise MCPError("MISSING_FIELD", "change_summary is required")

        rule = await self._create_rule_internal(
            params,
            params["created_by"],
            summary
        )
        return {"created": True, "rule": rule.to_dict()}

    async def cascade_rule_get(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get a specific rule."""
        rule_id = params["rule_id"]

        if rule_id not in self.rules:
            raise MCPError("RULE_NOT_FOUND", f"Rule not found: {rule_id}")

        return {"rule": self.rules[rule_id].to_dict()}

    async def cascade_rule_update(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing rule."""
        rule_id = params["rule_id"]
        summary = params.get("change_summary", "").strip()
        if not summary:
            raise MCPError("MISSING_FIELD", "change_summary is required")

        rule = await self._update_rule_internal(
            rule_id,
            params,
            params["updated_by"],
            summary
        )
        return {"updated": True, "rule": rule.to_dict()}

    async def cascade_rule_delete(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Delete a rule."""
        rule_id = params["rule_id"]
        summary = params.get("change_summary", "").strip()
        if not summary:
            raise MCPError("MISSING_FIELD", "change_summary is required")

        await self._delete_rule_internal(rule_id, params["deleted_by"], summary)
        return {"deleted": True}

    async def cascade_rule_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List rules with filtering."""
        category = params.get("category")
        tags = params.get("tags", [])
        status = params.get("status")
        priority = params.get("priority")
        limit = params.get("limit", 100)
        offset = params.get("offset", 0)

        filtered_rules = []
        for rule in self.rules.values():
            if category and rule.category != category:
                continue
            if status and rule.status.value != status:
                continue
            if priority and rule.priority.value != priority:
                continue
            if tags and not any(tag in rule.tags for tag in tags):
                continue
            filtered_rules.append(rule.to_dict())

        # Apply pagination
        paginated_rules = filtered_rules[offset:offset + limit]

        return {
            "rules": paginated_rules,
            "total": len(filtered_rules),
            "filtered": len(paginated_rules),
            "limit": limit,
            "offset": offset
        }

    async def cascade_rule_search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search rules by content."""
        query = params["query"].lower()
        fields = params.get("fields", ["name", "description", "content"])
        limit = params.get("limit", 20)

        matching_rules = []
        for rule in self.rules.values():
            score = 0

            # Search in specified fields
            for field in fields:
                if field == "name" and query in rule.name.lower():
                    score += 3
                elif field == "description" and query in rule.description.lower():
                    score += 2
                elif field == "content":
                    content_str = json.dumps(rule.content).lower()
                    if query in content_str:
                        score += 1

            if score > 0:
                matching_rules.append({
                    "rule": rule.to_dict(),
                    "score": score
                })

        # Sort by score and limit results
        matching_rules.sort(key=lambda x: x["score"], reverse=True)
        limited_rules = matching_rules[:limit]

        return {
            "query": query,
            "results": [{"rule": item["rule"], "score": item["score"]} for item in limited_rules],
            "total_matches": len(matching_rules),
            "returned": len(limited_rules)
        }

    async def cascade_rule_activate(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Activate a rule."""
        rule_id = params["rule_id"]
        summary = params.get("change_summary", "").strip()
        if not summary:
            raise MCPError("MISSING_FIELD", "change_summary is required")

        if rule_id not in self.rules:
            raise MCPError("RULE_NOT_FOUND", f"Rule not found: {rule_id}")

        rule = self.rules[rule_id]
        old_status = rule.status

        # Update status
        rule.status = RuleStatus.ACTIVE
        rule.updated_at = datetime.utcnow().isoformat()

        # Check for conflicts
        existing_rules = [r for r in self.rules.values()
                         if r.id != rule_id and r.category == rule.category and r.status == RuleStatus.ACTIVE]
        conflicts = self._check_rule_conflicts(rule, existing_rules)

        if conflicts:
            # Revert status change
            rule.status = old_status
            raise MCPError("RULE_CONFLICT", f"Cannot activate rule due to conflicts: {'; '.join(conflicts)}")

        rule.last_change_summary = summary

        # Audit log
        self._add_audit_entry(
            "activate",
            rule_id,
            {"old_status": old_status.value},
            params["activated_by"],
            summary=summary
        )

        await self._save_rules()
        return {"activated": True, "rule": rule.to_dict()}

    async def cascade_rule_deprecate(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Deprecate a rule."""
        rule_id = params["rule_id"]
        summary = params.get("change_summary", "").strip()
        if not summary:
            raise MCPError("MISSING_FIELD", "change_summary is required")

        if rule_id not in self.rules:
            raise MCPError("RULE_NOT_FOUND", f"Rule not found: {rule_id}")

        rule = self.rules[rule_id]

        # Update status
        old_status = rule.status
        rule.status = RuleStatus.DEPRECATED
        rule.updated_at = datetime.utcnow().isoformat()

        rule.last_change_summary = summary

        # Audit log
        self._add_audit_entry(
            "deprecate",
            rule_id,
            {"old_status": old_status.value},
            params["deprecated_by"],
            summary=summary
        )

        await self._save_rules()
        return {"deprecated": True, "rule": rule.to_dict()}

    async def cascade_rule_validate(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Validate rule content."""
        content = params["content"]

        is_valid = self._validate_rule_content(content)

        return {
            "valid": is_valid,
            "content": content
        }

    async def cascade_rule_check_conflicts(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Check for rule conflicts."""
        rule_id = params["rule_id"]

        if rule_id not in self.rules:
            raise MCPError("RULE_NOT_FOUND", f"Rule not found: {rule_id}")

        rule = self.rules[rule_id]
        existing_rules = [r for r in self.rules.values() if r.id != rule_id]
        conflicts = self._check_rule_conflicts(rule, existing_rules)

        return {
            "conflicts": conflicts,
            "has_conflicts": len(conflicts) > 0
        }

    async def cascade_rule_categories(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List all categories."""
        return {
            "categories": sorted(list(self.categories)),
            "count": len(self.categories)
        }

    async def cascade_rule_tags(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List all tags."""
        return {
            "tags": sorted(list(self.tags)),
            "count": len(self.tags)
        }

    async def cascade_rule_history(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get rule version history."""
        rule_id = params["rule_id"]
        limit = params.get("limit", 10)

        if rule_id not in self.rule_versions:
            raise MCPError("RULE_NOT_FOUND", f"Rule not found: {rule_id}")

        versions = self.rule_versions[rule_id][-limit:]  # Most recent versions

        return {
            "rule_id": rule_id,
            "versions": [rule.to_dict() for rule in versions],
            "total_versions": len(self.rule_versions[rule_id]),
            "returned": len(versions)
        }

    async def cascade_rule_audit(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get audit log entries."""
        rule_id = params.get("rule_id")
        action = params.get("action")
        user = params.get("user")
        limit = params.get("limit", 100)

        # Filter audit log
        filtered_entries = []
        for entry in reversed(self.audit_log):  # Most recent first
            if rule_id and entry.get("rule_id") != rule_id:
                continue
            if action and entry.get("action") != action:
                continue
            if user and entry.get("user") != user:
                continue

            filtered_entries.append(entry)
            if len(filtered_entries) >= limit:
                break

        return {
            "entries": filtered_entries,
            "total_entries": len(self.audit_log),
            "returned": len(filtered_entries)
        }


async def main():
    """Main server entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Cascade Rules Management Server")
    parser.add_argument(
        "--storage-path",
        default="./rules_storage",
        help="Path for rule storage (default: ./rules_storage)"
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
        default=8082,
        help="Port for WebSocket transport (default: 8082)"
    )
    parser.add_argument(
        "--no-web-ui",
        action="store_true",
        help="Disable web UI"
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
        server = CascadeRulesMCPServer(
            storage_path=args.storage_path,
            enable_web_ui=not args.no_web_ui
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
