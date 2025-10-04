#!/usr/bin/env python3
"""
Analyzer Service Stub

Provides a basic HTTP server for the analyzer service with:
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

# Add weaviate-client dependency
try:
    import weaviate
except ImportError:
    print("weaviate-client not installed. Install with: pip install weaviate-client")
    exit(1)



# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AnalyzerService:
    """Analyzer service with Kafka integration."""

    def __init__(self):
        self.app = web.Application()
        self.start_time = time.time()
        self.files_analyzed = 0
        self.messages_consumed = 0
        
        # Kafka configuration
        kafka_brokers = os.getenv('KAFKA_BROKERS', 'localhost:9092')
        
        # Kafka consumer for code.mined topic
        self.consumer = KafkaConsumer(
            'code.mined',
            bootstrap_servers=[kafka_brokers],
            group_id='analyzer-service-group',
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='earliest',
            enable_auto_commit=True
        )
        
        # Kafka producer for code.analyzed topic
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
        self.app.router.add_post('/analyze', self.analyze)
        
        # Start Kafka consumer in background
        import threading
        self.consumer_thread = threading.Thread(target=self._consume_messages, daemon=True)
        self.consumer_thread.start()
        
    def _consume_messages(self):
        """Consume messages from code.mined topic."""
        logger.info("Starting Kafka consumer for code.mined topic")
        try:
            for message in self.consumer:
                self.messages_consumed += 1
                logger.info(f"Consumed mined file: {message.value}")
                
                # Analyze the file and publish results
                self._analyze_file(message.value)
                
        except Exception as e:
            logger.error(f"Error in Kafka consumer: {e}")
            
    def _analyze_file(self, file_data):
        """Analyze a mined file and publish findings."""
        try:
            # Extract basic analysis (in real implementation, this would do deeper analysis)
            analysis = {
                "repo": file_data.get('repo'),
                "file": file_data.get('file'),
                "lang": file_data.get('lang'),
                "findings": self._extract_findings(file_data),
                "ts": datetime.utcnow().isoformat()
            }
            
            # Publish analysis to code.analyzed topic
            future = self.producer.send('code.analyzed', value=analysis, key=file_data['file'])
            record_metadata = future.get(timeout=10)
            logger.info(f"Published analysis to code.analyzed: {record_metadata.topic} partition {record_metadata.partition} offset {record_metadata.offset}")
            self.files_analyzed += 1
            
        except Exception as e:
            logger.error(f"Error analyzing file: {e}")
            
    def _extract_findings(self, file_data):
        """Extract findings from file data (simplified analysis)."""
        lang = file_data.get('lang', '')
        filename = file_data.get('file', '')
        
        findings = {
            "functions": [],
            "classes": [],
            "imports": [],
            "tables": [],
            "complexity": "low"
        }
        
        if lang == 'python':
            # Simulate Python analysis
            findings["functions"] = ["process_data", "validate_input"]
            findings["classes"] = ["DataProcessor"]
            findings["imports"] = ["pandas", "numpy"]
        elif lang == 'sql':
            # Simulate SQL analysis
            findings["tables"] = ["orders", "customers", "products"]
            
        return findings

    async def index(self, request):
        """Service index page."""
        return web.Response(
            text="FreshPOC Analyzer Service\n\n"
                 "Endpoints:\n"
                 "- GET /health - Health check\n"
                 "- GET /metrics - Prometheus metrics\n"
                 "- POST /analyze - Manually trigger file analysis\n"
                 "\nKafka Integration:\n"
                 f"- Consuming from: code.mined ({self.messages_consumed} messages)\n"
                 f"- Publishing to: code.analyzed ({self.files_analyzed} files)\n",
            content_type='text/plain'
        )

    async def health(self, request):
        """Health check endpoint."""
        return web.json_response({
            "status": "healthy",
            "service": "analyzer",
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": int(time.time() - self.start_time),
            "messages_consumed": self.messages_consumed,
            "files_analyzed": self.files_analyzed,
            "kafka_consumer_running": self.consumer_thread.is_alive()
        })

    async def metrics(self, request):
        """Prometheus metrics endpoint."""
        uptime = time.time() - self.start_time

        metrics = [
            "# HELP analyzer_service_uptime_seconds Service uptime in seconds",
            "# TYPE analyzer_service_uptime_seconds gauge",
            f"analyzer_service_uptime_seconds {uptime}",

            "# HELP analyzer_messages_consumed_total Total messages consumed from Kafka",
            "# TYPE analyzer_messages_consumed_total counter",
            f"analyzer_messages_consumed_total {self.messages_consumed}",

            "# HELP analyzer_files_analyzed_total Total files analyzed and published",
            "# TYPE analyzer_files_analyzed_total counter",
            f"analyzer_files_analyzed_total {self.files_analyzed}",

            "# HELP analyzer_service_info Service information",
            "# TYPE analyzer_service_info gauge",
            "analyzer_service_info{service=\"analyzer\",version=\"1.0.0\"} 1"
        ]

        return web.Response(
            text="\n".join(metrics) + "\n",
            content_type='text/plain'
        )

    async def analyze(self, request):
        """Manually trigger file analysis."""
        try:
            data = await request.json() if request.content_type == 'application/json' else {}
            
            # Analyze the file data
            file_data = {
                'repo': data.get('repo', 'manual'),
                'file': data.get('file', '/data/test.py'),
                'lang': data.get('lang', 'python')
            }
            
            # Perform analysis
            analysis = {
                "repo": file_data['repo'],
                "file": file_data['file'],
                "lang": file_data['lang'],
                "findings": self._extract_findings(file_data),
                "ts": datetime.utcnow().isoformat()
            }
            
            # Publish to Kafka
            future = self.producer.send('code.analyzed', value=analysis, key=file_data['file'])
            record_metadata = future.get(timeout=10)
            logger.info(f"Published analysis to code.analyzed: {record_metadata.topic} partition {record_metadata.partition} offset {record_metadata.offset}")
            self.files_analyzed += 1
            
            return web.json_response({
                "status": "success",
                "analysis": analysis,
                "total_analyzed": self.files_analyzed
            })
            
        except Exception as e:
            logger.error(f"Error in manual analysis: {e}")
            return web.json_response(
                {"status": "error", "message": str(e)},
                status=500
            )


async def init_app():
    """Initialize the application."""
    service = AnalyzerService()
    return service.app


def main():
    """Main entry point."""
    port = int(os.getenv('PORT', 8080))
    host = os.getenv('HOST', '0.0.0.0')

    logger.info(f"Starting Analyzer Service on {host}:{port}")

    app = init_app()
    web.run_app(app, host=host, port=port)


if __name__ == '__main__':
    main()
