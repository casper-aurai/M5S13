#!/usr/bin/env python3
"""
Ingestion Service Stub

Provides a basic HTTP server for the ingestion service with:
- /trigger endpoint for manual triggering
- /health endpoint for health checks
- /metrics endpoint for Prometheus metrics
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

class IngestionService:
    """Ingestion service stub."""

    def __init__(self):
        self.app = web.Application()
        self.triggers_count = 0
        self.last_trigger = None
        self.start_time = time.time()

        # Setup routes
        self.app.router.add_get('/health', self.health)
        self.app.router.add_get('/metrics', self.metrics)
        self.app.router.add_post('/trigger', self.trigger)
        self.app.router.add_get('/', self.index)

    async def index(self, request):
        """Service index page."""
        return web.Response(
            text="FreshPOC Ingestion Service\n\n"
                 "Endpoints:\n"
                 "- GET /health - Health check\n"
                 "- GET /metrics - Prometheus metrics\n"
                 "- POST /trigger - Trigger ingestion process\n",
            content_type='text/plain'
        )

    async def health(self, request):
        """Health check endpoint."""
        return web.json_response({
            "status": "healthy",
            "service": "ingestion",
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": int(time.time() - self.start_time),
            "triggers_processed": self.triggers_count
        })

    async def metrics(self, request):
        """Prometheus metrics endpoint."""
        uptime = time.time() - self.start_time

        metrics = [
            "# HELP ingestion_service_uptime_seconds Service uptime in seconds",
            "# TYPE ingestion_service_uptime_seconds gauge",
            f"ingestion_service_uptime_seconds {uptime}",

            "# HELP ingestion_triggers_total Total number of triggers processed",
            "# TYPE ingestion_triggers_total counter",
            f"ingestion_triggers_total {self.triggers_count}",

            "# HELP ingestion_service_info Service information",
            "# TYPE ingestion_service_info gauge",
            "ingestion_service_info{service=\"ingestion\",version=\"1.0.0\"} 1"
        ]

        return web.Response(
            text="\n".join(metrics) + "\n",
            content_type='text/plain'
        )

    async def trigger(self, request):
        """Trigger ingestion process."""
        try:
            # Get request body if provided
            data = await request.json() if request.content_type == 'application/json' else {}

            # Process trigger
            self.triggers_count += 1
            self.last_trigger = datetime.utcnow()

            trigger_id = f"trigger_{self.triggers_count}_{int(time.time())}"

            logger.info(f"Trigger {trigger_id} received")

            # Simulate some processing
            await asyncio.sleep(0.1)

            # In a real implementation, this would:
            # 1. Parse the trigger data
            # 2. Send message to Kafka
            # 3. Update status

            return web.json_response({
                "status": "success",
                "trigger_id": trigger_id,
                "message": "Ingestion triggered successfully",
                "timestamp": self.last_trigger.isoformat(),
                "data_received": bool(data),
                "total_triggers": self.triggers_count
            })

        except Exception as e:
            logger.error(f"Error processing trigger: {e}")
            return web.json_response(
                {"status": "error", "message": str(e)},
                status=500
            )


async def init_app():
    """Initialize the application."""
    service = IngestionService()
    return service.app


def main():
    """Main entry point."""
    port = int(os.getenv('PORT', 8080))
    host = os.getenv('HOST', '0.0.0.0')

    logger.info(f"Starting Ingestion Service on {host}:{port}")

    app = init_app()
    web.run_app(app, host=host, port=port)


if __name__ == '__main__':
    main()
