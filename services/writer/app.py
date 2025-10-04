#!/usr/bin/env python3
"""
Writer Service Stub

Provides a basic HTTP server for the writer service with:
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


class WriterService:
    """Writer service with Kafka integration."""

    def __init__(self):
        self.app = web.Application()
        self.start_time = time.time()
        self.graph_operations = 0
        self.messages_consumed = 0
        
        # Kafka configuration
        kafka_brokers = os.getenv('KAFKA_BROKERS', 'localhost:9092')
        
        # Kafka consumer for code.analyzed topic
        self.consumer = KafkaConsumer(
            'code.analyzed',
            bootstrap_servers=[kafka_brokers],
            group_id='writer-service-group',
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='earliest',
            enable_auto_commit=True
        )
        
        # Kafka producer for graph.apply topic
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
        self.app.router.add_post('/apply', self.apply)
        
        # Start Kafka consumer in background
        import threading
        self.consumer_thread = threading.Thread(target=self._consume_messages, daemon=True)
        self.consumer_thread.start()
        
    def _consume_messages(self):
        """Consume messages from code.analyzed topic."""
        logger.info("Starting Kafka consumer for code.analyzed topic")
        try:
            for message in self.consumer:
                self.messages_consumed += 1
                logger.info(f"Consumed analysis: {message.value}")
                
                # Apply the analysis to the graph and publish acknowledgment
                self._apply_to_graph(message.value)
                
        except Exception as e:
            logger.error(f"Error in Kafka consumer: {e}")
            
    def _apply_to_graph(self, analysis_data):
        """Apply analysis data to graph and publish acknowledgment."""
        try:
            # Simulate applying to Dgraph (in real implementation, this would do actual graph operations)
            # For demo, we'll just create a simple acknowledgment
            
            acknowledgment = {
                "repo": analysis_data.get('repo'),
                "file": analysis_data.get('file'),
                "applied": True,
                "graph_operations": self._simulate_graph_operations(analysis_data),
                "ts": datetime.utcnow().isoformat()
            }
            
            # Publish acknowledgment to graph.apply topic
            future = self.producer.send('graph.apply', value=acknowledgment, key=analysis_data['file'])
            record_metadata = future.get(timeout=10)
            logger.info(f"Published acknowledgment to graph.apply: {record_metadata.topic} partition {record_metadata.partition} offset {record_metadata.offset}")
            self.graph_operations += 1
            
        except Exception as e:
            logger.error(f"Error applying to graph: {e}")
            
    def _simulate_graph_operations(self, analysis_data):
        """Simulate graph operations (nodes and edges created)."""
        # In a real implementation, this would create actual Dgraph mutations
        findings = analysis_data.get('findings', {})
        operations = []
        
        # Simulate creating nodes for tables/functions/classes
        for table in findings.get('tables', []):
            operations.append(f"CREATE NODE: table_{table}")
        for function in findings.get('functions', []):
            operations.append(f"CREATE NODE: function_{function}")
        for cls in findings.get('classes', []):
            operations.append(f"CREATE NODE: class_{cls}")
            
        # Simulate creating edges between file and its components
        operations.append(f"CREATE EDGE: file_{analysis_data['file']} -> contains -> table_{findings.get('tables', [''])[0]}")
        
        return operations

    async def index(self, request):
        """Service index page."""
        return web.Response(
            text="FreshPOC Writer Service\n\n"
                 "Endpoints:\n"
                 "- GET /health - Health check\n"
                 "- GET /metrics - Prometheus metrics\n"
                 "- POST /apply - Manually trigger graph application\n"
                 "\nKafka Integration:\n"
                 f"- Consuming from: code.analyzed ({self.messages_consumed} messages)\n"
                 f"- Publishing to: graph.apply ({self.graph_operations} operations)\n",
            content_type='text/plain'
        )

    async def health(self, request):
        """Health check endpoint."""
        return web.json_response({
            "status": "healthy",
            "service": "writer",
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": int(time.time() - self.start_time),
            "messages_consumed": self.messages_consumed,
            "graph_operations": self.graph_operations,
            "kafka_consumer_running": self.consumer_thread.is_alive()
        })

    async def metrics(self, request):
        """Prometheus metrics endpoint."""
        uptime = time.time() - self.start_time

        metrics = [
            "# HELP writer_service_uptime_seconds Service uptime in seconds",
            "# TYPE writer_service_uptime_seconds gauge",
            f"writer_service_uptime_seconds {uptime}",

            "# HELP writer_messages_consumed_total Total messages consumed from Kafka",
            "# TYPE writer_messages_consumed_total counter",
            f"writer_messages_consumed_total {self.messages_consumed}",

            "# HELP writer_graph_operations_total Total graph operations performed",
            "# TYPE writer_graph_operations_total counter",
            f"writer_graph_operations_total {self.graph_operations}",

            "# HELP writer_service_info Service information",
            "# TYPE writer_service_info gauge",
            "writer_service_info{service=\"writer\",version=\"1.0.0\"} 1"
        ]

        return web.Response(
            text="\n".join(metrics) + "\n",
            content_type='text/plain'
        )

    async def apply(self, request):
        """Manually trigger graph application."""
        try:
            data = await request.json() if request.content_type == 'application/json' else {}
            
            # Apply analysis data to graph
            analysis_data = {
                'repo': data.get('repo', 'manual'),
                'file': data.get('file', '/data/test.py'),
                'lang': data.get('lang', 'python'),
                'findings': data.get('findings', {'tables': ['test_table']})
            }
            
            # Perform graph operations
            acknowledgment = {
                "repo": analysis_data['repo'],
                "file": analysis_data['file'],
                "applied": True,
                "graph_operations": self._simulate_graph_operations(analysis_data),
                "ts": datetime.utcnow().isoformat()
            }
            
            # Publish to Kafka
            future = self.producer.send('graph.apply', value=acknowledgment, key=analysis_data['file'])
            record_metadata = future.get(timeout=10)
            logger.info(f"Published acknowledgment to graph.apply: {record_metadata.topic} partition {record_metadata.partition} offset {record_metadata.offset}")
            self.graph_operations += 1
            
            return web.json_response({
                "status": "success",
                "acknowledgment": acknowledgment,
                "total_operations": self.graph_operations
            })
            
        except Exception as e:
            logger.error(f"Error in manual graph application: {e}")
            return web.json_response(
                {"status": "error", "message": str(e)},
                status=500
            )


async def init_app():
    """Initialize the application."""
    service = WriterService()
    return service.app


def main():
    """Main entry point."""
    port = int(os.getenv('PORT', 8080))
    host = os.getenv('HOST', '0.0.0.0')

    logger.info(f"Starting Writer Service on {host}:{port}")

    app = init_app()
    web.run_app(app, host=host, port=port)


if __name__ == '__main__':
    main()
