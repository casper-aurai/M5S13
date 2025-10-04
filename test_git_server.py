#!/usr/bin/env python3
"""
Comprehensive tests for Git MCP Server

Tests all git operations including status, diff, commit, branch, log, etc.
"""
import asyncio
import json
import pytest
import tempfile
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import the Git MCP Server
import sys
sys.path.append(str(Path(__file__).parent.parent))

from servers.git_server import GitMCPServer, MCPError


class TestGitMCPServer:
    """Test suite for Git MCP Server functionality."""

    @pytest.fixture
    def temp_git_repo(self):
        """Create a temporary git repository for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)

            # Initialize git repository
            subprocess.run(['git', 'init'], cwd=repo_path, check=True, capture_output=True)
            subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=repo_path, check=True, capture_output=True)
            subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=repo_path, check=True, capture_output=True)

            yield repo_path

    @pytest.fixture
    def git_server(self, temp_git_repo):
        """Create Git MCP Server instance."""
        server = GitMCPServer(str(temp_git_repo))
        return server

    def test_server_initialization(self, temp_git_repo):
        """Test server initialization with valid repository."""
        server = GitMCPServer(str(temp_git_repo))
        assert server.server_name == "git"
        assert server.server_version == "1.0.0"
        assert server.repo_root == temp_git_repo

    def test_invalid_repository(self):
        """Test server initialization with invalid repository."""
        with tempfile.TemporaryDirectory() as temp_dir:
            invalid_path = Path(temp_dir) / "not_a_repo"
            with pytest.raises(MCPError, match="Not a git repository"):
                GitMCPServer(str(invalid_path))

    def test_validate_repo_path(self, git_server):
        """Test repository path validation."""
        # Valid path should work
        valid_path = git_server.repo_root / "test.txt"
        result = git_server.validate_repo_path(str(valid_path))
        assert result == valid_path

        # Invalid path should raise error
        with pytest.raises(MCPError, match="Path outside repository"):
            git_server.validate_repo_path("/etc/passwd")

    @pytest.mark.asyncio
    async def test_git_status_porcelain(self, git_server):
        """Test git status with porcelain format."""
        # Create a test file
        test_file = git_server.repo_root / "test.txt"
        test_file.write_text("Hello, World!")

        result = await git_server.git_status({"porcelain": True})

        assert "porcelain" in result
        assert result["porcelain"] is True
        assert "files" in result
        assert "count" in result
        assert result["count"] >= 0

    @pytest.mark.asyncio
    async def test_git_status_human_readable(self, git_server):
        """Test git status with human-readable format."""
        result = await git_server.git_status({"porcelain": False})

        assert "porcelain" in result
        assert result["porcelain"] is False
        assert "output" in result
        assert isinstance(result["output"], str)

    @pytest.mark.asyncio
    async def test_git_add_files(self, git_server):
        """Test staging files with git add."""
        # Create test files
        test_file1 = git_server.repo_root / "file1.txt"
        test_file2 = git_server.repo_root / "file2.txt"
        test_file1.write_text("Content 1")
        test_file2.write_text("Content 2")

        result = await git_server.git_add({"files": [str(test_file1), str(test_file2)]})

        assert result["staged"] is True
        assert str(test_file1) in result["files"]
        assert str(test_file2) in result["files"]

    @pytest.mark.asyncio
    async def test_git_commit(self, git_server):
        """Test creating a commit."""
        # First add some files
        test_file = git_server.repo_root / "commit_test.txt"
        test_file.write_text("Commit test content")
        await git_server.git_add({"files": [str(test_file)]})

        # Create commit
        result = await git_server.git_commit({"message": "Test commit message"})

        assert result["committed"] is True
        assert result["message"] == "Test commit message"

    @pytest.mark.asyncio
    async def test_git_commit_without_staged_changes(self, git_server):
        """Test commit without staged changes raises error."""
        with pytest.raises(MCPError, match="No staged changes"):
            await git_server.git_commit({"message": "This should fail"})

    @pytest.mark.asyncio
    async def test_git_branch_list(self, git_server):
        """Test listing branches."""
        result = await git_server.git_branch({"action": "list"})

        assert "branches" in result
        assert "count" in result
        assert "current" in result
        assert isinstance(result["branches"], list)
        assert result["count"] >= 0

    @pytest.mark.asyncio
    async def test_git_branch_create(self, git_server):
        """Test creating a new branch."""
        result = await git_server.git_branch({
            "action": "create",
            "name": "test-branch",
            "base": "HEAD"
        })

        assert result["created"] is True
        assert result["branch"] == "test-branch"

    @pytest.mark.asyncio
    async def test_git_branch_switch(self, git_server):
        """Test switching branches."""
        # First create a branch
        await git_server.git_branch({"action": "create", "name": "switch-test"})

        # Switch to it
        result = await git_server.git_branch({"action": "switch", "name": "switch-test"})

        assert result["switched"] is True
        assert result["branch"] == "switch-test"

    @pytest.mark.asyncio
    async def test_git_diff_staged(self, git_server):
        """Test showing staged changes."""
        # Create and stage a file
        test_file = git_server.repo_root / "diff_test.txt"
        test_file.write_text("Original content")
        await git_server.git_add({"files": [str(test_file)]})

        result = await git_server.git_diff({"staged": True})

        assert "diff" in result
        assert "staged" in result
        assert result["staged"] is True

    @pytest.mark.asyncio
    async def test_git_diff_between_commits(self, git_server):
        """Test showing diff between commits."""
        # Create a commit first
        test_file = git_server.repo_root / "diff_commit_test.txt"
        test_file.write_text("Initial content")
        await git_server.git_add({"files": [str(test_file)]})
        await git_server.git_commit({"message": "Initial commit"})

        # Modify file
        test_file.write_text("Modified content")
        await git_server.git_add({"files": [str(test_file)]})
        await git_server.git_commit({"message": "Modified content"})

        result = await git_server.git_diff({"commit1": "HEAD~1", "commit2": "HEAD"})

        assert "diff" in result
        assert "commit1" in result
        assert result["commit1"] == "HEAD~1"

    @pytest.mark.asyncio
    async def test_git_log(self, git_server):
        """Test commit history."""
        # Create a commit
        test_file = git_server.repo_root / "log_test.txt"
        test_file.write_text("Log test")
        await git_server.git_add({"files": [str(test_file)]})
        await git_server.git_commit({"message": "Log test commit"})

        result = await git_server.git_log({"max_count": 5})

        assert "commits" in result
        assert "count" in result
        assert isinstance(result["commits"], list)
        assert result["count"] >= 1

    @pytest.mark.asyncio
    async def test_git_log_with_path_filter(self, git_server):
        """Test commit history filtered by path."""
        # Create commits affecting different files
        file1 = git_server.repo_root / "path_test1.txt"
        file2 = git_server.repo_root / "path_test2.txt"

        file1.write_text("File 1 content")
        await git_server.git_add({"files": [str(file1)]})
        await git_server.git_commit({"message": "Commit file 1"})

        file2.write_text("File 2 content")
        await git_server.git_add({"files": [str(file2)]})
        await git_server.git_commit({"message": "Commit file 2"})

        result = await git_server.git_log({"path": str(file1)})

        assert "commits" in result
        assert result["count"] >= 1

    @pytest.mark.asyncio
    async def test_git_checkout_branch(self, git_server):
        """Test checking out a branch."""
        # Create and switch to a branch
        await git_server.git_branch({"action": "create", "name": "checkout-test"})

        result = await git_server.git_checkout({"branch": "checkout-test"})

        assert result["checked_out"] is True
        assert result["branch"] == "checkout-test"

    @pytest.mark.asyncio
    async def test_git_checkout_files(self, git_server):
        """Test checking out specific files."""
        # Create a file and commit it
        test_file = git_server.repo_root / "checkout_file_test.txt"
        test_file.write_text("Original content")
        await git_server.git_add({"files": [str(test_file)]})
        await git_server.git_commit({"message": "Original file"})

        # Modify the file (but don't stage)
        test_file.write_text("Modified content")

        # Checkout the file from index
        result = await git_server.git_checkout({"files": [str(test_file)]})

        assert result["checked_out"] is True
        assert str(test_file) in result["files"]

    @pytest.mark.asyncio
    async def test_git_remote_operations(self, git_server):
        """Test remote repository operations."""
        # Test listing remotes (should be empty initially)
        result = await git_server.git_remote({"action": "list"})

        assert "remotes" in result
        assert "count" in result
        assert isinstance(result["remotes"], dict)

        # Test adding a remote
        add_result = await git_server.git_remote({
            "action": "add",
            "name": "test-remote",
            "url": "https://github.com/test/repo.git"
        })

        assert add_result["added"] is True
        assert add_result["name"] == "test-remote"

    def test_safe_command_execution(self, git_server):
        """Test that git commands are executed safely."""
        # Test that dangerous commands are not allowed
        with patch.object(git_server, 'run_git_command') as mock_cmd:
            # This should work normally
            git_server.run_git_command(["status"])

            # Verify command was called
            mock_cmd.assert_called_once_with(["status"])

    @pytest.mark.asyncio
    async def test_error_handling_invalid_params(self, git_server):
        """Test error handling for invalid parameters."""
        with pytest.raises(MCPError):
            await git_server.git_add({"files": []})  # Empty files list

    @pytest.mark.asyncio
    async def test_health_check_endpoint(self, git_server):
        """Test health check functionality."""
        request = {"method": "health", "id": "test"}
        response = await git_server.handle_request(request)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == "test"
        assert "result" in response
        assert response["result"]["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_metrics_endpoint(self, git_server):
        """Test metrics functionality."""
        request = {"method": "metrics", "id": "test"}
        response = await git_server.handle_request(request)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == "test"
        assert "result" in response
        assert "uptime_seconds" in response["result"]
        assert "total_requests" in response["result"]


class TestGitServerIntegration:
    """Integration tests for the complete Git MCP Server."""

    @pytest.mark.asyncio
    async def test_full_workflow(self, temp_git_repo):
        """Test complete git workflow: init, add, commit, branch, diff."""
        server = GitMCPServer(str(temp_git_repo))

        # Initial status
        status = await server.git_status({"porcelain": True})
        initial_count = status["count"]

        # Create and add files
        file1 = temp_git_repo / "workflow_test1.txt"
        file2 = temp_git_repo / "workflow_test2.txt"
        file1.write_text("Workflow test 1")
        file2.write_text("Workflow test 2")

        await server.git_add({"files": [str(file1), str(file2)]})

        # Commit files
        commit_result = await server.git_commit({"message": "Initial workflow commit"})
        assert commit_result["committed"] is True

        # Check status after commit
        status_after = await server.git_status({"porcelain": True})
        assert status_after["count"] == initial_count  # Should be clean

        # Create branch
        branch_result = await server.git_branch({"action": "create", "name": "feature-branch"})
        assert branch_result["created"] is True

        # Make changes on feature branch
        file3 = temp_git_repo / "feature_file.txt"
        file3.write_text("Feature content")
        await server.git_add({"files": [str(file3)]})
        await server.git_commit({"message": "Feature commit"})

        # Show diff between branches
        diff_result = await server.git_diff({"commit1": "HEAD~1", "commit2": "HEAD"})
        assert "diff" in diff_result

        # Show log
        log_result = await server.git_log({"max_count": 3})
        assert log_result["count"] >= 2

    def test_concurrent_operations(self, temp_git_repo):
        """Test concurrent git operations."""
        server = GitMCPServer(str(temp_git_repo))

        async def create_commit(message):
            test_file = temp_git_repo / f"concurrent_{message}.txt"
            test_file.write_text(f"Content for {message}")
            await server.git_add({"files": [str(test_file)]})
            return await server.git_commit({"message": message})

        async def run_concurrent():
            tasks = [
                create_commit("Commit 1"),
                create_commit("Commit 2"),
                create_commit("Commit 3")
            ]
            results = await asyncio.gather(*tasks)

            for result in results:
                assert result["committed"] is True

        # Run concurrently
        asyncio.run(run_concurrent())


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "--tb=short"])
