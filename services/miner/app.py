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

from aiohttp import web

# Add kafka-python dependency
try:
    import kafka
    from kafka import KafkaConsumer, KafkaProducer
except ImportError:
    print("kafka-python not installed. Install with: pip install kafka-python")
    exit(1)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MinerService:
    """Miner service with Kafka integration."""

    def __init__(self):
        self.app = web.Application()
        self.start_time = time.time()
        self.files_processed = 0
        self.messages_consumed = 0
        
        # Kafka configuration
        kafka_brokers = os.getenv('KAFKA_BROKERS', 'localhost:9092')
        
        # Kafka consumer for repos.ingested topic
        self.consumer = KafkaConsumer(
            'repos.ingested',
            bootstrap_servers=[kafka_brokers],
            group_id='miner-service-group',
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='earliest',
            enable_auto_commit=True
        )
        
        # Kafka producer for code.mined topic
        self.producer = KafkaProducer(
            bootstrap_servers=[kafka_brokers],
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None,
            acks='all',
            retries=3
        )
        
        # Setup routes
        self.app.router.add_get('/health', self.health)
        self.app.router.add_get('/metrics', self.metrics)
        self.app.router.add_get('/', self.index)
        self.app.router.add_post('/process', self.process)
        
        # Start Kafka consumer in background
        import threading
        self.consumer_thread = threading.Thread(target=self._consume_messages, daemon=True)
        self.consumer_thread.start()
        
    def _consume_messages(self):
        """Consume messages from repos.ingested topic."""
        logger.info("Starting Kafka consumer for repos.ingested topic")
        try:
            for message in self.consumer:
                self.messages_consumed += 1
                logger.info(f"Consumed message: {message.value}")
                
                # Process the repository data and mine files
                self._process_repo_data(message.value)
                
        except Exception as e:
            logger.error(f"Error in Kafka consumer: {e}")
            
    def _process_repo_data(self, repo_data):
        """Process repository data and mine code files."""
        try:
            repo = repo_data.get('repo', 'unknown')
            path = repo_data.get('path', '/data')
            
            # Simulate file mining (in real implementation, scan actual files)
            mined_files = self._scan_and_mine_files(repo, path)
            
            # Publish each mined file to code.mined topic
            for file_info in mined_files:
                future = self.producer.send('code.mined', value=file_info, key=file_info['file'])
                record_metadata = future.get(timeout=10)
                logger.info(f"Published mined file to code.mined: {record_metadata.topic} partition {record_metadata.partition} offset {record_metadata.offset}")
                self.files_processed += 1
                
        except Exception as e:
            logger.error(f"Error processing repo data: {e}")
            
    def _scan_and_mine_files(self, repo, path):
        """Scan and mine code files (simulated)."""
        # In a real implementation, this would scan the actual repository
        # For demo purposes, we'll simulate some common file types
        files = [
            {
                "repo": repo,
                "file": f"{path}/models/orders.sql",
                "lang": "sql",
                "size": 1234,
                "hash": "sha256-abc123",
                "ts": datetime.utcnow().isoformat()
            },
            {
                "repo": repo,
                "file": f"{path}/models/customers.py",
                "lang": "python",
                "size": 567,
                "hash": "sha256-def456",
                "ts": datetime.utcnow().isoformat()
            }
        ]
        return files
    async def index(self, request):
        """Service index page."""
        return web.Response(
            text="FreshPOC Miner Service\n\n"
                 "Endpoints:\n"
                 "- GET /health - Health check\n"
                 "- GET /metrics - Prometheus metrics\n"
                 "- POST /process - Manually trigger file processing\n"
                 "\nKafka Integration:\n"
                 f"- Consuming from: repos.ingested ({self.messages_consumed} messages)\n"
                 f"- Publishing to: code.mined ({self.files_processed} files)\n",
            content_type='text/plain'
        )

    async def health(self, request):
        """Health check endpoint."""
        return web.json_response({
            "status": "healthy",
            "service": "miner",
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": int(time.time() - self.start_time),
            "messages_consumed": self.messages_consumed,
            "files_processed": self.files_processed,
            "kafka_consumer_running": self.consumer_thread.is_alive()
        })

    async def metrics(self, request):
        """Prometheus metrics endpoint."""
        uptime = time.time() - self.start_time

        metrics = [
            "# HELP miner_service_uptime_seconds Service uptime in seconds",
            "# TYPE miner_service_uptime_seconds gauge",
            f"miner_service_uptime_seconds {uptime}",

            "# HELP miner_messages_consumed_total Total messages consumed from Kafka",
            "# TYPE miner_messages_consumed_total counter",
            f"miner_messages_consumed_total {self.messages_consumed}",

            "# HELP miner_files_processed_total Total files processed and published",
            "# TYPE miner_files_processed_total counter",
            f"miner_files_processed_total {self.files_processed}",

            "# HELP miner_service_info Service information",
            "# TYPE miner_service_info gauge",
            "miner_service_info{service=\"miner\",version=\"1.0.0\"} 1"
        ]

        return web.Response(
            text="\n".join(metrics) + "\n",
            content_type='text/plain'
        )

    async def process(self, request):
        """Manually trigger file processing."""
        try:
            data = await request.json() if request.content_type == 'application/json' else {}
            
            # Process the request
            repo = data.get('repo', 'manual')
            path = data.get('path', '/data')
            
            # Mine files and publish to Kafka
            mined_files = self._scan_and_mine_files(repo, path)
            
            for file_info in mined_files:
                future = self.producer.send('code.mined', value=file_info, key=file_info['file'])
                record_metadata = future.get(timeout=10)
                logger.info(f"Published mined file to code.mined: {record_metadata.topic} partition {record_metadata.partition} offset {record_metadata.offset}")
                self.files_processed += 1
            
            return web.json_response({
                "status": "success",
                "files_processed": len(mined_files),
                "total_files_processed": self.files_processed,
                "files": mined_files
            })
            
        except Exception as e:
            logger.error(f"Error in manual processing: {e}")
            return web.json_response(
                {"status": "error", "message": str(e)},
                status=500
            )


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
