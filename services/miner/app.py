#!/usr/bin/env python3
"""
Miner Service Stub

Provides a basic HTTP server for the miner service with:
- /health endpoint for health checks
- /metrics endpoint for Prometheus metrics
- Placeholder endpoints for service-specific functionality
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime
from typing import Dict, Any

try:
    from aiohttp import web
except ImportError:
    print("aiohttp not installed. Install with: pip install aiohttp")
    exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MinerService:
    """Miner service stub."""

    def __init__(self):
        self.app = web.Application()
        self.start_time = time.time()

        # Setup routes
        self.app.router.add_get('/health', self.health)
        self.app.router.add_get('/metrics', self.metrics)
        self.app.router.add_get('/', self.index)
        # Add service-specific routes here

    async def index(self, request):
        """Service index page."""
        return web.Response(
            text="FreshPOC Miner Service\n\n"
                 "Endpoints:\n"
                 "- GET /health - Health check\n"
                 "- GET /metrics - Prometheus metrics\n"
                 "# Add service-specific endpoints here\n",
            content_type='text/plain'
        )

    async def health(self, request):
        """Health check endpoint."""
        return web.json_response({
            "status": "healthy",
            "service": "miner",
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": int(time.time() - self.start_time)
        })

    async def metrics(self, request):
        """Prometheus metrics endpoint."""
        uptime = time.time() - self.start_time

        metrics = [
            "# HELP miner_service_uptime_seconds Service uptime in seconds",
            "# TYPE miner_service_uptime_seconds gauge",
            f"miner_service_uptime_seconds {uptime}",

            "# HELP miner_service_info Service information",
            "# TYPE miner_service_info gauge",
            "miner_service_info{service=\"miner\",version=\"1.0.0\"} 1"
        ]

        return web.Response(
            text="\n".join(metrics) + "\n",
            content_type='text/plain'
        )

    # Add service-specific methods here


async def init_app():
    """Initialize the application."""
    service = MinerService()
    return service.app


def main():
    """Main entry point."""
    port = int(os.getenv('PORT', 8080))
    host = os.getenv('HOST', '0.0.0.0')

    logger.info(f"Starting Miner Service on {host}:{port}")

    app = init_app()
    web.run_app(app, host=host, port=port)


if __name__ == '__main__':
    main()
