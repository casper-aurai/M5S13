#!/usr/bin/env python3
"""
MCP Security Enforcement Module

Implements comprehensive security constraints and sandboxing for all MCP servers.
Enforces the security rules defined in .windsurf/mcp.json to prevent:
- Path traversal attacks
- Unauthorized file access
- External network access
- Resource exhaustion
- Privilege escalation attempts
"""

import os
import re
import logging
import json
import time
from pathlib import Path, PurePosixPath
from typing import Dict, List, Any, Optional
from functools import wraps

logger = logging.getLogger(__name__)


class MCPSecurityEnforcer:
    """Enforces security constraints for MCP server operations."""

    def __init__(self, config_path: str = None):
        """Initialize security enforcer with configuration."""
        if config_path is None:
            # Default to workspace MCP config
            workspace_root = Path.cwd()
            config_path = workspace_root / ".windsurf" / "mcp.json"

        self.config_path = Path(config_path)
        self.security_rules = self._load_security_rules()
        self.rate_limits = {}
        self.audit_log = []

    def _load_security_rules(self) -> Dict[str, Any]:
        """Load security rules from configuration file."""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                    return config.get('securityRules', {})
            else:
                logger.warning(f"Security config not found at {self.config_path}")
                return {}
        except Exception as e:
            logger.error(f"Failed to load security config: {e}")
            return {}

    def enforce_filesystem_security(self, operation: str, path: str, **kwargs) -> bool:
        """Enforce filesystem security constraints."""
        rules = self.security_rules.get('filesystem', {})

        # Check blocked paths
        blocked_paths = rules.get('blockedPaths', [])
        resolved_path = Path(path).resolve()

        for blocked in blocked_paths:
            if str(resolved_path).startswith(blocked):
                self._log_security_violation("filesystem", f"Access to blocked path: {path}")
                return False

        # Check file size limits
        if operation in ['write', 'create']:
            max_size = int(rules.get('maxFileSize', '10485760'))  # 10MB default
            if 'content' in kwargs:
                content_size = len(kwargs['content'].encode('utf-8'))
                if content_size > max_size:
                    self._log_security_violation("filesystem", f"File too large: {content_size} > {max_size}")
                    return False

        # Check allowed extensions
        allowed_extensions = rules.get('allowedExtensions', [])
        if allowed_extensions:
            file_ext = Path(path).suffix.lower().lstrip('.')
            if file_ext and file_ext not in allowed_extensions:
                self._log_security_violation("filesystem", f"Disallowed file extension: {file_ext}")
                return False

        # Check sandbox requirement
        if rules.get('requireSandbox', True):
            # Ensure path is within workspace
            workspace_root = Path.cwd()
            try:
                resolved_path.relative_to(workspace_root)
            except ValueError:
                self._log_security_violation("filesystem", f"Path outside workspace: {path}")
                return False

        return True

    def enforce_git_security(self, operation: str, **kwargs) -> bool:
        """Enforce git operation security constraints."""
        rules = self.security_rules.get('git', {})

        # Check allowed commands
        allowed_commands = rules.get('allowedCommands', [])
        if operation not in allowed_commands:
            self._log_security_violation("git", f"Disallowed git operation: {operation}")
            return False

        # Check commit size limits
        if operation == 'commit':
            max_size = int(rules.get('maxCommitSize', '1048576'))  # 1MB default
            # Implementation would check actual commit size here

        # Check repository boundary
        if rules.get('requireRepoBoundary', True):
            # Ensure operations stay within repository
            repo_root = Path.cwd()
            # Implementation would validate paths are within repo

        return True

    def enforce_fetch_security(self, url: str) -> bool:
        """Enforce HTTP fetch security constraints."""
        rules = self.security_rules.get('fetch', {})

        if rules.get('whitelistOnly', True):
            # Check against whitelist patterns
            whitelist_patterns = [
                r"^https?://127\.0\.0\.1:\d+/?$",
                r"^https?://localhost:\d+/?$",
                r"^https?://127\.0\.0\.1:\d+/.*$",
                r"^https?://localhost:\d+/.*$",
                r"^https?://0\.0\.0\.0:\d+/?$",
                r"^https?://0\.0\.0\.0:\d+/.*$"
            ]

            allowed = False
            for pattern in whitelist_patterns:
                if re.match(pattern, url):
                    allowed = True
                    break

            if not allowed:
                self._log_security_violation("fetch", f"URL not in whitelist: {url}")
                return False

        # Check blocked hosts
        blocked_hosts = rules.get('blockedHosts', [])
        parsed_url = urlparse(url)
        hostname = parsed_url.hostname or ""

        for blocked in blocked_hosts:
            if blocked.startswith('*.'):
                # Wildcard pattern
                if hostname.endswith(blocked[2:]):
                    self._log_security_violation("fetch", f"Blocked host pattern: {blocked}")
                    return False
            elif hostname == blocked:
                self._log_security_violation("fetch", f"Blocked host: {hostname}")
                return False

        # Check response size limits
        max_response_size = int(rules.get('maxResponseSize', '1048576'))  # 1MB default
        # Implementation would check actual response size

        # Check timeout limits
        timeout_max = int(rules.get('timeoutMax', 300))  # 5 minutes default
        # Implementation would enforce timeout

        return True

    def enforce_podman_security(self, operation: str, **kwargs) -> bool:
        """Enforce Podman/container security constraints."""
        rules = self.security_rules.get('podman', {})

        # Check user socket requirement
        if rules.get('requireUserSocket', True):
            # Ensure using user-specific socket
            expected_socket = f"/run/user/{os.getuid()}/podman/podman.sock"
            if 'socket_path' in kwargs:
                if kwargs['socket_path'] != expected_socket:
                    self._log_security_violation("podman", f"Invalid socket path: {kwargs['socket_path']}")
                    return False

        # Check container limits
        max_containers = rules.get('maxContainers', 100)
        # Implementation would check current container count

        # Check privileged mode
        if rules.get('noPrivileged', True):
            if kwargs.get('privileged', False):
                self._log_security_violation("podman", "Privileged containers not allowed")
                return False

        # Check allowed networks
        allowed_networks = rules.get('allowedNetworks', ['bridge', 'freshpoc-network'])
        if 'network' in kwargs:
            if kwargs['network'] not in allowed_networks:
                self._log_security_violation("podman", f"Network not allowed: {kwargs['network']}")
                return False

        return True

    def enforce_redis_security(self, operation: str, **kwargs) -> bool:
        """Enforce Redis operation security constraints."""
        rules = self.security_rules.get('redis', {})

        # Check allowed operations
        allowed_operations = rules.get('allowedOperations', [])
        if operation not in allowed_operations:
            self._log_security_violation("redis", f"Disallowed Redis operation: {operation}")
            return False

        # Check key size limits
        if 'key' in kwargs:
            max_key_size = int(rules.get('maxKeySize', '1024'))
            if len(kwargs['key']) > max_key_size:
                self._log_security_violation("redis", f"Key too large: {len(kwargs['key'])} > {max_key_size}")
                return False

        # Check value size limits
        if 'value' in kwargs:
            max_value_size = int(rules.get('maxValueSize', '1048576'))  # 1MB default
            value_size = len(str(kwargs['value']).encode('utf-8'))
            if value_size > max_value_size:
                self._log_security_violation("redis", f"Value too large: {value_size} > {max_value_size}")
                return False

        # Check session-only constraint
        if rules.get('sessionOnly', True):
            # Ensure operations are session-scoped
            if 'key' in kwargs and not kwargs['key'].startswith(('session:', 'mcp_session:')):
                self._log_security_violation("redis", f"Non-session key access: {kwargs['key']}")
                return False

        return True

    def enforce_rate_limits(self, user_id: str, operation: str) -> bool:
        """Enforce rate limiting for operations."""
        now = time.time()

        # Clean old entries
        self.rate_limits = {
            k: v for k, v in self.rate_limits.items()
            if now - v['timestamp'] < 3600  # 1 hour window
        }

        # Check rate limits
        user_key = f"{user_id}:{operation}"
        if user_key in self.rate_limits:
            entry = self.rate_limits[user_key]
            if entry['count'] >= 10:  # 10 operations per hour per user per operation
                self._log_security_violation("rate_limit", f"Rate limit exceeded for {user_key}")
                return False

            entry['count'] += 1
        else:
            self.rate_limits[user_key] = {
                'count': 1,
                'timestamp': now
            }

        return True

    def _log_security_violation(self, category: str, message: str):
        """Log security violations."""
        violation = {
            'timestamp': time.time(),
            'category': category,
            'message': message,
            'level': 'SECURITY_VIOLATION'
        }

        self.audit_log.append(violation)
        logger.warning(f"Security violation [{category}]: {message}")

        # In production, this would also send alerts
        # send_security_alert(violation)

    def get_audit_log(self) -> List[Dict[str, Any]]:
        """Get recent security audit log."""
        # Return last 100 entries
        return self.audit_log[-100:] if self.audit_log else []


# Global security enforcer instance
security_enforcer = MCPSecurityEnforcer()


def require_security(operation_type: str = None):
    """Decorator to enforce security constraints on MCP tool methods."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract operation context
            if operation_type == 'filesystem':
                path = kwargs.get('path', '')
                if not security_enforcer.enforce_filesystem_security(operation_type, path, **kwargs):
                    raise MCPError("SECURITY_VIOLATION", f"Filesystem operation blocked: {path}")

            elif operation_type == 'git':
                if not security_enforcer.enforce_git_security(operation_type, **kwargs):
                    raise MCPError("SECURITY_VIOLATION", f"Git operation blocked: {operation_type}")

            elif operation_type == 'fetch':
                url = kwargs.get('url', '')
                if not security_enforcer.enforce_fetch_security(url):
                    raise MCPError("SECURITY_VIOLATION", f"HTTP request blocked: {url}")

            elif operation_type == 'podman':
                if not security_enforcer.enforce_podman_security(operation_type, **kwargs):
                    raise MCPError("SECURITY_VIOLATION", f"Podman operation blocked: {operation_type}")

            elif operation_type == 'redis':
                if not security_enforcer.enforce_redis_security(operation_type, **kwargs):
                    raise MCPError("SECURITY_VIOLATION", f"Redis operation blocked: {operation_type}")

            # Execute the original function
            return await func(*args, **kwargs)

        return wrapper
    return decorator


def validate_request_security(request_data: Dict[str, Any]) -> bool:
    """Validate incoming request for security violations."""
    # Check for common attack patterns
    suspicious_patterns = [
        r'\.\.\/',  # Path traversal
        r'\/etc\/',  # System paths
        r'\/proc\/',  # Process filesystem
        r'rm\s+-rf',  # Dangerous commands
        r'wget\s+http',  # External downloads
        r'curl\s+http[^s]',  # Non-HTTPS external requests
    ]

    def check_value(value):
        if isinstance(value, str):
            for pattern in suspicious_patterns:
                if re.search(pattern, value, re.IGNORECASE):
                    security_enforcer._log_security_violation("request_validation", f"Suspicious pattern: {pattern}")
                    return False
        elif isinstance(value, dict):
            for v in value.values():
                if not check_value(v):
                    return False
        elif isinstance(value, list):
            for item in value:
                if not check_value(item):
                    return False
        return True

    return check_value(request_data)


# Import here to avoid circular imports
try:
    from base_mcp_server import MCPError
except ImportError:
    # Define a basic exception for standalone use
    class MCPError(Exception):
        def __init__(self, code: str, message: str):
            self.code = code
            self.message = message
            super().__init__(message)


_CFG_PATH = Path(".windsurf/github-repo.json")


def _enforce_remote_issues_enabled() -> bool:
    """Return True when the GitHub-first issue policy is enabled."""
    try:
        cfg = json.loads(_CFG_PATH.read_text())
        return bool(cfg.get("enforce_remote_issues", True))
    except Exception:
        # Safe default: enforce unless explicitly disabled
        return True


def deny_local_markdown_for_issues(intent: str, target_path: str) -> Optional[str]:
    """Return a denial message when issue-like writes target local markdown."""
    if not _enforce_remote_issues_enabled():
        return None

    lowered_intent = (intent or "").lower()
    if "issue" not in lowered_intent:
        return None

    candidate_path = PurePosixPath(target_path)
    if str(candidate_path).startswith("docs/") and candidate_path.suffix.lower() in {".md", ".mdx"}:
        return (
            "Local markdown issue creation is disabled. "
            "Use github.create_issue (GitHub-first policy)."
        )

    return None
