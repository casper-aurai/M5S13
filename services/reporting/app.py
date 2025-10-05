#!/usr/bin/env python3
"""
Reporting Service Stub

Provides a basic HTTP server for the reporting service with:
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

# Dgraph integration
try:
    from pydgraph import DgraphClient, DgraphClientStub
except ImportError:
    print("pydgraph not installed. Install with: pip install pydgraph")
    exit(1)

# MinIO integration
import io
try:
    from minio import Minio
except ImportError:
    print("minio not installed. Install with: pip install minio")
    exit(1)

class ReportingService:
    """Reporting service with Dgraph and MinIO integration."""

    def __init__(self):
        self.app = web.Application()
        self.start_time = time.time()
        self.reports_generated = 0
        
        # Dgraph configuration
        dgraph_host = os.getenv('DGRAPH_HOST', 'localhost:9080')
        self.dgraph_client = None
        
        try:
            stub = DgraphClientStub(dgraph_host)
            self.dgraph_client = DgraphClient(stub)
            logger.info("Dgraph client initialized")
        except Exception as e:
            logger.warning(f"Dgraph not available: {e}")
        
        # MinIO configuration
        minio_endpoint = os.getenv('MINIO_ENDPOINT', 'localhost:9000')
        minio_access_key = os.getenv('MINIO_ACCESS_KEY', 'minioadmin')
        minio_secret_key = os.getenv('MINIO_SECRET_KEY', 'minioadmin')
        self.minio_client = None
        
        try:
            self.minio_client = Minio(
                minio_endpoint,
                access_key=minio_access_key,
                secret_key=minio_secret_key,
                secure=False
            )
            logger.info("MinIO client initialized")
        except Exception as e:
            logger.warning(f"MinIO not available: {e}")
        
        # Setup routes
        self.app.router.add_get('/health', self.health)
        self.app.router.add_get('/metrics', self.metrics)
        self.app.router.add_get('/', self.index)
        self.app.router.add_post('/generate', self.generate_report)
        self.app.router.add_get('/list-reports', self.list_reports)

    def _query_dgraph(self, query):
        """Query Dgraph and return results."""
        if not self.dgraph_client:
            raise Exception("Dgraph client not available")
        
        try:
            res = self.dgraph_client.txn(read_only=True).query(query)
            return json.loads(res.json)
        except Exception as e:
            logger.error(f"Dgraph query failed: {e}")
            raise
    
    def _generate_mermaid_diagram(self, data):
        """Generate Mermaid diagram from data."""
        # Simple example: create a flowchart based on repos and files
        mermaid = "graph TD\n"
        
        repos = data.get('repos', [])
        for repo in repos:
            repo_name = repo.get('name', 'unknown')
            files = repo.get('files', [])
            mermaid += f"    A[{repo_name}] --> B[Files]\n"
            for file_info in files:
                file_path = file_info.get('path', '')
                mermaid += f"    B --> C[{file_path}]\n"
        
        return mermaid
    
    def _generate_markdown_report(self, data):
        """Generate Markdown report with Mermaid diagram."""
        report = "# Repository Analysis Report\n\n"
        report += f"Generated at: {datetime.utcnow().isoformat()}\n\n"
        
        # Add summary
        repos = data.get('repos', [])
        total_files = sum(len(repo.get('files', [])) for repo in repos)
        report += f"## Summary\n- Total Repositories: {len(repos)}\n- Total Files: {total_files}\n\n"
        
        # Add Mermaid diagram
        mermaid = self._generate_mermaid_diagram(data)
        report += "## Architecture Diagram\n```mermaid\n" + mermaid + "\n```\n\n"
        
        # Add details
        report += "## Repository Details\n"
        for repo in repos:
            repo_name = repo.get('name', 'unknown')
            report += f"### {repo_name}\n"
            files = repo.get('files', [])
            for file_info in files:
                path = file_info.get('path', '')
                lang = file_info.get('language', 'unknown')
                report += f"- **{path}** ({lang})\n"
            report += "\n"
        
        return report
    
    def _upload_to_minio(self, report_content, filename):
        """Upload report to MinIO."""
        if not self.minio_client:
            raise Exception("MinIO client not available")
        
        bucket_name = os.getenv('MINIO_BUCKET', 'reports')
        
        # Ensure bucket exists
        if not self.minio_client.bucket_exists(bucket_name):
            self.minio_client.make_bucket(bucket_name)
        
        # Upload report
        self.minio_client.put_object(
            bucket_name,
            filename,
            io.BytesIO(report_content.encode('utf-8')),
            length=len(report_content.encode('utf-8')),
            content_type='text/markdown'
        )
        
        return f"{bucket_name}/{filename}"

    async def index(self, request):
        """Service index page."""
        return web.Response(
            text="FreshPOC Reporting Service\n\n"
                 "Endpoints:\n"
                 "- GET /health - Health check\n"
                 "- GET /metrics - Prometheus metrics\n"
                 "- POST /generate - Generate and upload report\n"
                 "- GET /list-reports - List uploaded reports\n",
            content_type='text/plain'
        )

    async def health(self, request):
        """Health check endpoint."""
        return web.json_response({
            "status": "healthy",
            "service": "reporting",
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": int(time.time() - self.start_time),
            "reports_generated": self.reports_generated,
            "dgraph_available": self.dgraph_client is not None,
            "minio_available": self.minio_client is not None
        })

    async def metrics(self, request):
        """Prometheus metrics endpoint."""
        uptime = time.time() - self.start_time

        metrics = [
            "# HELP reporting_service_uptime_seconds Service uptime in seconds",
            "# TYPE reporting_service_uptime_seconds gauge",
            f"reporting_service_uptime_seconds {uptime}",

            "# HELP reporting_reports_generated_total Total reports generated",
            "# TYPE reporting_reports_generated_total counter",
            f"reporting_reports_generated_total {self.reports_generated}",

            "# HELP reporting_service_info Service information",
            "# TYPE reporting_service_info gauge",
            "reporting_service_info{service=\"reporting\",version=\"1.0.0\"} 1"
        ]

        return web.Response(
            text="\n".join(metrics) + "\n",
            content_type='text/plain'
        )

    async def generate_report(self, request):
        """Generate Markdown report and upload to MinIO."""
        try:
            # Query Dgraph for data
            query = """
                {
                    repos(func: has(name)) {
                        name
                        files {
                            path
                            language
                        }
                    }
                }
            """
            data = self._query_dgraph(query)
            
            # Generate report
            report_content = self._generate_markdown_report(data)
            
            # Upload to MinIO
            filename = f"report_{int(time.time())}.md"
            minio_path = self._upload_to_minio(report_content, filename)
            
            self.reports_generated += 1
            
            return web.json_response({
                "status": "success",
                "report_generated": True,
                "minio_path": minio_path,
                "reports_total": self.reports_generated
            })
            
        except Exception as e:
            logger.error(f"Error generating report: {e}")
            return web.json_response(
                {"status": "error", "message": str(e)},
                status=500
            )

    async def list_reports(self, request):
        """List uploaded reports from MinIO."""
        if not self.minio_client:
            return web.json_response(
                {"status": "error", "message": "MinIO not available"},
                status=503
            )
        
        try:
            bucket_name = os.getenv('MINIO_BUCKET', 'reports')
            objects = self.minio_client.list_objects(bucket_name)
            reports = [obj.object_name for obj in objects]
            
            return web.json_response({
                "status": "success",
                "reports": reports,
                "total": len(reports)
            })
        except Exception as e:
            logger.error(f"Error listing reports: {e}")
            return web.json_response(
                {"status": "error", "message": str(e)},
                status=500
            )


async def init_app():
    """Initialize the application."""
    service = ReportingService()
    return service.app


def main():
    """Main entry point."""
    port = int(os.getenv('PORT', 8080))
    host = os.getenv('HOST', '0.0.0.0')

    logger.info(f"Starting Reporting Service on {host}:{port}")

    app = init_app()
    web.run_app(app, host=host, port=port)


if __name__ == '__main__':
    main()
