#!/usr/bin/env python3
"""
Comprehensive tests for Podman MCP Server

Tests all container operations including lifecycle management, image operations, and compose functionality.
"""
import asyncio
import json
import pytest
import tempfile
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

# Import the Podman MCP Server
import sys
sys.path.append(str(Path(__file__).parent.parent))

from servers.podman_server import PodmanMCPServer, MCPError


class TestPodmanMCPServer:
    """Test suite for Podman MCP Server functionality."""

    @pytest.fixture
    def mock_podman_client(self):
        """Create a mock Podman client for testing."""
        mock_client = MagicMock()

        # Mock containers
        mock_container = MagicMock()
        mock_container.id = "abc123def456"
        mock_container.name = "test-container"
        mock_container.status = "running"
        mock_container.image.tags = ["nginx:latest"]
        mock_container.ports = [
            {"IP": "", "PrivatePort": 80, "PublicPort": 8080, "Type": "tcp"}
        ]
        mock_container.labels = {"app": "web"}
        mock_container.attrs = {
            "Created": "2024-01-15T10:00:00Z",
            "Config": {"Cmd": ["nginx", "-g", "daemon off;"]},
            "NetworkSettings": {"Networks": {"bridge": {}}},
            "Mounts": []
        }

        mock_client.containers.list.return_value = [mock_container]
        mock_client.containers.get.return_value = mock_container
        mock_client.containers.create.return_value = mock_container

        # Mock images
        mock_image = MagicMock()
        mock_image.id = "sha256:abcdef123456"
        mock_image.tags = ["nginx:latest", "nginx:1.21"]
        mock_image.attrs = {
            "Created": "2024-01-10T08:00:00Z",
            "Size": 142345678,
            "Architecture": "amd64",
            "Os": "linux"
        }
        mock_image.labels = {"maintainer": "nginx"}

        mock_client.images.list.return_value = [mock_image]
        mock_client.images.pull.return_value = mock_image

        return mock_client

    @pytest.fixture
    def podman_server(self, mock_podman_client):
        """Create Podman MCP Server instance with mocked client."""
        with patch('podman.PodmanClient') as mock_podman_class:
            mock_podman_class.return_value = mock_podman_client

            server = PodmanMCPServer()
            server.client = mock_podman_client  # Inject mock client
            return server

    def test_server_initialization(self):
        """Test server initialization."""
        with patch('podman.PodmanClient') as mock_client:
            mock_client.return_value = MagicMock()

            server = PodmanMCPServer()
            assert server.server_name == "podman"
            assert server.server_version == "1.0.0"
            assert server.max_containers == 100

    def test_invalid_podman_dependency(self):
        """Test server initialization without podman-py."""
        with patch.dict('sys.modules', {'podman': None}):
            with pytest.raises(MCPError, match="podman-py package is required"):
                PodmanMCPServer()

    @pytest.mark.asyncio
    async def test_podman_ps_all_containers(self, podman_server, mock_podman_client):
        """Test listing all containers."""
        result = await podman_server.podman_ps({"all": True})

        assert "containers" in result
        assert "count" in result
        assert result["count"] == 1
        assert result["all"] is True
        assert len(result["containers"]) == 1

        # Verify container data structure
        container = result["containers"][0]
        assert "id" in container
        assert "name" in container
        assert "status" in container
        assert "image" in container

    @pytest.mark.asyncio
    async def test_podman_ps_with_filters(self, podman_server, mock_podman_client):
        """Test listing containers with filters."""
        result = await podman_server.podman_ps({
            "all": False,
            "filters": {"status": "running", "name": "test"},
            "limit": 10
        })

        assert result["filters"]["status"] == "running"
        assert result["count"] == 1  # Mock returns 1 container

    @pytest.mark.asyncio
    async def test_podman_run_basic(self, podman_server, mock_podman_client):
        """Test creating and running a basic container."""
        result = await podman_server.podman_run({
            "image": "nginx:latest",
            "name": "test-web",
            "detach": True
        })

        assert result["created"] is True
        assert "container" in result
        assert result["name"] == "test-web"

        # Verify container.create was called
        mock_podman_client.containers.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_podman_run_with_ports_and_env(self, podman_server, mock_podman_client):
        """Test creating container with ports and environment variables."""
        result = await podman_server.podman_run({
            "image": "nginx:latest",
            "ports": ["8080:80", "8443:443"],
            "env": ["NGINX_PORT=80", "SSL_PORT=443"],
            "restart": "always"
        })

        assert result["created"] is True

        # Verify container configuration
        call_args = mock_podman_client.containers.create.call_args[1]
        assert call_args["image"] == "nginx:latest"
        assert "ports" in call_args
        assert "restart_policy" in call_args

    @pytest.mark.asyncio
    async def test_podman_stop_containers(self, podman_server, mock_podman_client):
        """Test stopping containers."""
        result = await podman_server.podman_stop({
            "containers": ["test-container", "web-server"],
            "timeout": 30
        })

        assert "containers" in result
        assert "stopped_count" in result
        assert len(result["containers"]) == 2

        # Verify stop was called for each container
        assert mock_podman_client.containers.get.call_count == 2

    @pytest.mark.asyncio
    async def test_podman_start_containers(self, podman_server, mock_podman_client):
        """Test starting containers."""
        result = await podman_server.podman_start({
            "containers": ["test-container", "web-server"]
        })

        assert "containers" in result
        assert "started_count" in result
        assert len(result["containers"]) == 2

    @pytest.mark.asyncio
    async def test_podman_logs_basic(self, podman_server, mock_podman_client):
        """Test getting container logs."""
        # Mock logs response
        mock_logs = b"2024-01-15 10:00:00 [INFO] Server started\n2024-01-15 10:00:01 [INFO] Listening on port 80"
        mock_podman_client.containers.get.return_value.logs.return_value = mock_logs

        result = await podman_server.podman_logs({
            "container": "test-container",
            "tail": 50,
            "timestamps": True
        })

        assert result["container"] == "test-container"
        assert "logs" in result
        assert result["tail"] == 50
        assert result["timestamps"] is True

    @pytest.mark.asyncio
    async def test_podman_inspect(self, podman_server, mock_podman_client):
        """Test container inspection."""
        # Mock inspect response
        mock_inspect = {
            "Id": "abc123def456",
            "Config": {"Image": "nginx:latest"},
            "State": {"Running": True},
            "NetworkSettings": {"IPAddress": "172.17.0.2"}
        }
        mock_podman_client.containers.get.return_value.inspect.return_value = mock_inspect

        result = await podman_server.podman_inspect({"container": "test-container"})

        assert result["container"] == "test-container"
        assert "inspection" in result
        assert "formatted" in result

    @pytest.mark.asyncio
    async def test_podman_images_list(self, podman_server, mock_podman_client):
        """Test listing images."""
        result = await podman_server.podman_images({"all": True})

        assert "images" in result
        assert "count" in result
        assert result["count"] == 1
        assert result["all"] is True

        # Verify image data structure
        image = result["images"][0]
        assert "id" in image
        assert "tags" in image
        assert "created" in image
        assert "size" in image

    @pytest.mark.asyncio
    async def test_podman_pull_image(self, podman_server, mock_podman_client):
        """Test pulling an image."""
        result = await podman_server.podman_pull({"image": "redis:7-alpine"})

        assert result["pulled"] is True
        assert result["image"] == "redis:7-alpine"
        assert "image_info" in result

    @pytest.mark.asyncio
    async def test_podman_compose_up_placeholder(self, podman_server, mock_podman_client):
        """Test compose up (placeholder implementation)."""
        result = await podman_server.podman_compose_up({
            "file": "docker-compose.yml",
            "project_name": "test-project"
        })

        assert result["started"] is True
        assert result["file"] == "docker-compose.yml"
        assert "note" in result  # Should contain placeholder note

    @pytest.mark.asyncio
    async def test_podman_compose_down_placeholder(self, podman_server, mock_podman_client):
        """Test compose down (placeholder implementation)."""
        result = await podman_server.podman_compose_down({
            "file": "docker-compose.yml",
            "volumes": True
        })

        assert result["stopped"] is True
        assert result["volumes"] is True

    def test_validate_container_name(self, podman_server):
        """Test container name validation."""
        # Valid names should pass
        assert podman_server.validate_container_name("valid-name") is True
        assert podman_server.validate_container_name("test_container") is True
        assert podman_server.validate_container_name("my-container-123") is True

        # Invalid names should fail
        assert podman_server.validate_container_name("INVALID") is False  # Uppercase
        assert podman_server.validate_container_name("invalid name") is False  # Spaces
        assert podman_server.validate_container_name("invalid@name") is False  # Special chars

    @pytest.mark.asyncio
    async def test_error_handling_invalid_params(self, podman_server):
        """Test error handling for invalid parameters."""
        with pytest.raises(MCPError):
            await podman_server.podman_run({})  # Missing required image

    @pytest.mark.asyncio
    async def test_health_check_endpoint(self, podman_server):
        """Test health check functionality."""
        request = {"method": "health", "id": "test"}
        response = await podman_server.handle_request(request)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == "test"
        assert "result" in response
        assert response["result"]["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_metrics_endpoint(self, podman_server):
        """Test metrics functionality."""
        request = {"method": "metrics", "id": "test"}
        response = await podman_server.handle_request(request)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == "test"
        assert "result" in response
        assert "uptime_seconds" in response["result"]
        assert "total_requests" in response["result"]


class TestPodmanServerIntegration:
    """Integration tests for the complete Podman MCP Server."""

    def test_container_lifecycle_workflow(self, mock_podman_client):
        """Test complete container lifecycle: run -> inspect -> stop."""
        with patch('podman.PodmanClient') as mock_podman_class:
            mock_podman_class.return_value = mock_podman_client

            async def run_workflow():
                server = PodmanMCPServer()
                server.client = mock_podman_client

                # 1. List containers (should be empty initially)
                status = await server.podman_ps({"all": True})
                initial_count = status["count"]

                # 2. Create and run container
                run_result = await server.podman_run({
                    "image": "nginx:latest",
                    "name": "lifecycle-test",
                    "ports": ["8080:80"]
                })
                assert run_result["created"] is True

                # 3. Check container is running
                status_after = await server.podman_ps({"all": True})
                assert status_after["count"] == initial_count + 1

                # 4. Inspect container
                inspect_result = await server.podman_inspect({"container": "lifecycle-test"})
                assert "inspection" in inspect_result

                # 5. Stop container
                stop_result = await server.podman_stop({"containers": ["lifecycle-test"]})
                assert stop_result["stopped_count"] >= 1

            asyncio.run(run_workflow())

    @pytest.mark.asyncio
    async def test_error_recovery(self, mock_podman_client):
        """Test error handling and recovery."""
        mock_podman_client.containers.list.side_effect = Exception("Connection failed")

        with patch('podman.PodmanClient') as mock_podman_class:
            mock_podman_class.return_value = mock_podman_client

            server = PodmanMCPServer()
            server.client = mock_podman_client

            with pytest.raises(MCPError, match="Failed to list containers"):
                await server.podman_ps({"all": True})

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, mock_podman_client):
        """Test concurrent container operations."""
        with patch('podman.PodmanClient') as mock_podman_class:
            mock_podman_class.return_value = mock_podman_client

            server = PodmanMCPServer()
            server.client = mock_podman_client

            async def create_container(name):
                return await server.podman_run({
                    "image": "nginx:latest",
                    "name": name
                })

            async def run_concurrent():
                tasks = [
                    create_container("container-1"),
                    create_container("container-2"),
                    create_container("container-3")
                ]
                results = await asyncio.gather(*tasks)

                for result in results:
                    assert result["created"] is True

            await run_concurrent()


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "--tb=short"])
