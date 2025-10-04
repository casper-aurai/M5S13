#!/usr/bin/env python3
"""
MCP Servers Validation Script

Tests all 8 MCP servers to ensure they're working correctly:
1. filesystem - File operations with sandboxing
2. git - Repository operations
3. redis - State management (if Redis is running)
4. fetch - HTTP operations (if services are running)
5. podman - Container operations (if Podman is available)
6. sequential-thinking - Chain-of-thought sessions
7. task-master - Task and project management
8. http-mcp - HTTP endpoint validation

Usage: python validate_mcp_servers.py
"""

import asyncio
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Any, List

class MCPServerValidator:
    """Validates MCP server functionality."""

    def __init__(self):
        self.workspace_root = Path.cwd()
        self.results = []
        self.errors = []

    def log_result(self, server: str, test: str, success: bool, details: str = ""):
        """Log test result."""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"[{status}] {server}.{test}: {details}")
        self.results.append({
            'server': server,
            'test': test,
            'success': success,
            'details': details
        })

    async def test_filesystem_server(self):
        """Test filesystem MCP server."""
        print("\n🧪 Testing filesystem server...")
        server = "filesystem"

        try:
            # Test 1: Read README.md
            result = subprocess.run([
                "python", str(self.workspace_root / "servers" / "filesystem_server.py")
            ], input='{"jsonrpc": "2.0", "id": 1, "method": "fs_read", "params": {"path": "README.md"}}\n',
               capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                self.log_result(server, "fs_read", True, "Successfully read README.md")
            else:
                self.log_result(server, "fs_read", False, f"Exit code: {result.returncode}")

        except Exception as e:
            self.log_result(server, "fs_read", False, str(e))

        try:
            # Test 2: List services directory
            result = subprocess.run([
                "python", str(self.workspace_root / "servers" / "filesystem_server.py")
            ], input='{"jsonrpc": "2.0", "id": 2, "method": "fs_list", "params": {"path": "services"}}\n',
               capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                self.log_result(server, "fs_list", True, "Successfully listed services directory")
            else:
                self.log_result(server, "fs_list", False, f"Exit code: {result.returncode}")

        except Exception as e:
            self.log_result(server, "fs_list", False, str(e))

    async def test_git_server(self):
        """Test git MCP server."""
        print("\n🧪 Testing git server...")
        server = "git"

        try:
            # Test 1: Git status
            result = subprocess.run([
                "python", str(self.workspace_root / "servers" / "git_server.py")
            ], input='{"jsonrpc": "2.0", "id": 1, "method": "git_status", "params": {}}\n',
               capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                self.log_result(server, "git_status", True, "Successfully got git status")
            else:
                self.log_result(server, "git_status", False, f"Exit code: {result.returncode}")

        except Exception as e:
            self.log_result(server, "git_status", False, str(e))

        try:
            # Test 2: Git branch
            result = subprocess.run([
                "python", str(self.workspace_root / "servers" / "git_server.py")
            ], input='{"jsonrpc": "2.0", "id": 2, "method": "git_branch", "params": {}}\n',
               capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                self.log_result(server, "git_branch", True, "Successfully got current branch")
            else:
                self.log_result(server, "git_branch", False, f"Exit code: {result.returncode}")

        except Exception as e:
            self.log_result(server, "git_branch", False, str(e))

    async def test_redis_server(self):
        """Test redis MCP server."""
        print("\n🧪 Testing redis server...")
        server = "redis"

        try:
            # Test 1: Redis ping
            result = subprocess.run([
                "python", str(self.workspace_root / "servers" / "redis_server.py")
            ], input='{"jsonrpc": "2.0", "id": 1, "method": "redis_ping", "params": {}}\n',
               capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                self.log_result(server, "redis_ping", True, "Successfully pinged Redis")
            else:
                self.log_result(server, "redis_ping", False, f"Exit code: {result.returncode} (Redis may not be running)")

        except Exception as e:
            self.log_result(server, "redis_ping", False, str(e))

    async def test_fetch_server(self):
        """Test fetch MCP server."""
        print("\n🧪 Testing fetch server...")
        server = "fetch"

        try:
            # Test 1: Health check (this should work if our services are running)
            result = subprocess.run([
                "python", str(self.workspace_root / "servers" / "fetch_server.py")
            ], input='{"jsonrpc": "2.0", "id": 1, "method": "http_health", "params": {"url": "http://localhost:8080/health"}}\n',
               capture_output=True, text=True, timeout=15)

            if result.returncode == 0:
                self.log_result(server, "http_health", True, "Successfully checked service health")
            else:
                self.log_result(server, "http_health", False, f"Exit code: {result.returncode} (Services may not be running)")

        except Exception as e:
            self.log_result(server, "http_health", False, str(e))

    async def test_podman_server(self):
        """Test podman MCP server."""
        print("\n🧪 Testing podman server...")
        server = "podman"

        try:
            # Test 1: Podman ps (list containers)
            result = subprocess.run([
                "python", str(self.workspace_root / "servers" / "podman_server.py")
            ], input='{"jsonrpc": "2.0", "id": 1, "method": "podman_ps", "params": {}}\n',
               capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                self.log_result(server, "podman_ps", True, "Successfully listed containers")
            else:
                self.log_result(server, "podman_ps", False, f"Exit code: {result.returncode} (Podman may not be available)")

        except Exception as e:
            self.log_result(server, "podman_ps", False, str(e))

    async def test_sequential_thinking_server(self):
        """Test sequential thinking MCP server."""
        print("\n🧪 Testing sequential-thinking server...")
        server = "sequential-thinking"

        try:
            # Test 1: Create session
            result = subprocess.run([
                "python", str(self.workspace_root / "servers" / "sequential_thinking_server.py")
            ], input='{"jsonrpc": "2.0", "id": 1, "method": "session_create", "params": {"name": "test_session"}}\n',
               capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                self.log_result(server, "session_create", True, "Successfully created session")
            else:
                self.log_result(server, "session_create", False, f"Exit code: {result.returncode}")

        except Exception as e:
            self.log_result(server, "session_create", False, str(e))

    async def test_task_master_server(self):
        """Test task master MCP server."""
        print("\n🧪 Testing task-master server...")
        server = "task-master"

        try:
            # Test 1: List projects
            result = subprocess.run([
                "python", str(self.workspace_root / "servers" / "task_master_server.py")
            ], input='{"jsonrpc": "2.0", "id": 1, "method": "project_list", "params": {}}\n',
               capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                self.log_result(server, "project_list", True, "Successfully listed projects")
            else:
                self.log_result(server, "project_list", False, f"Exit code: {result.returncode}")

        except Exception as e:
            self.log_result(server, "project_list", False, str(e))

    async def test_http_mcp_server(self):
        """Test http-mcp server."""
        print("\n🧪 Testing http-mcp server...")
        server = "http-mcp"

        try:
            # Test 1: Validate endpoint
            result = subprocess.run([
                "python", str(self.workspace_root / "servers" / "http_mcp_server.py")
            ], input='{"jsonrpc": "2.0", "id": 1, "method": "validate_endpoint", "params": {"url": "http://localhost:8080/health"}}\n',
               capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                self.log_result(server, "validate_endpoint", True, "Successfully validated endpoint")
            else:
                self.log_result(server, "validate_endpoint", False, f"Exit code: {result.returncode}")

        except Exception as e:
            self.log_result(server, "validate_endpoint", False, str(e))

    async def run_all_tests(self):
        """Run all MCP server tests."""
        print("🚀 Starting MCP Server Validation Suite")
        print("=" * 50)

        # Run tests sequentially to avoid overwhelming the system
        await self.test_filesystem_server()
        await self.test_git_server()
        await self.test_redis_server()
        await self.test_fetch_server()
        await self.test_podman_server()
        await self.test_sequential_thinking_server()
        await self.test_task_master_server()
        await self.test_http_mcp_server()

        # Summary
        print("\n" + "=" * 50)
        print("📊 VALIDATION SUMMARY")
        print("=" * 50)

        passed = sum(1 for r in self.results if r['success'])
        total = len(self.results)

        print(f"✅ Passed: {passed}/{total}")
        print(f"❌ Failed: {total - passed}/{total}")

        if passed == total:
            print("🎉 All MCP servers are working correctly!")
        else:
            print("⚠️  Some MCP servers have issues that need attention.")
            print("\n❌ FAILURES:")
            for result in self.results:
                if not result['success']:
                    print(f"  - {result['server']}.{result['test']}: {result['details']}")

        return passed == total

    def save_results(self):
        """Save test results to file."""
        output_file = self.workspace_root / "mcp_validation_results.json"
        with open(output_file, 'w') as f:
            json.dump({
                'timestamp': time.time(),
                'results': self.results,
                'summary': {
                    'passed': sum(1 for r in self.results if r['success']),
                    'total': len(self.results)
                }
            }, f, indent=2)

        print(f"\n💾 Results saved to: {output_file}")


async def main():
    """Main validation function."""
    validator = MCPServerValidator()
    success = await validator.run_all_tests()
    validator.save_results()
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
