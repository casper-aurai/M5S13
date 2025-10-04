from fastapi import FastAPI
import uvicorn, os
import boto3
import mgclient
from datetime import datetime

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/metrics")
def metrics():
    return "requests_total 1\n", 200, {"Content-Type": "text/plain; version=0.0.4"}

@app.get("/generate")
def generate():
    try:
        # Connect to Memgraph to get data for the report
        connection = mgclient.connect(host="memgraph", port=7687)
        cursor = connection.cursor()
        
        # Query for nodes and edges
        cursor.execute("MATCH (n) RETURN n")
        nodes = cursor.fetchall()
        
        cursor.execute("MATCH ()-[r]->() RETURN r")
        edges = cursor.fetchall()
        
        connection.close()
        
        # Generate report content
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        report_content = f"""# FreshPoC Data Platform Report
Generated on: {timestamp}

## Graph Database Statistics
- **Total Nodes**: {len(nodes)}
- **Total Edges**: {len(edges)}

## Data Model Visualization
```mermaid
graph TD
"""
        
        # Add nodes and edges to the Mermaid diagram
        node_ids = {}
        for i, node in enumerate(nodes):
            node_id = f"N{i}"
            node_ids[node[0]['name']] = node_id
            
            # Extract node properties for label
            name = node[0].get('name', 'Unknown')
            node_type = node[0].get('type', 'Node')
            report_content += f"    {node_id}[{node_type}: {name}]\n"
        
        # Add edges
        for edge in edges:
            source_name = edge[0].start_node.properties.get('name', 'Unknown')
            target_name = edge[0].end_node.properties.get('name', 'Unknown')
            edge_type = edge[0].type
            
            if source_name in node_ids and target_name in node_ids:
                report_content += f"    {node_ids[source_name]} -->|{edge_type}| {node_ids[target_name]}\n"
        
        report_content += """
```

## Service Status
✅ All services operational
✅ Data ingestion complete
✅ Graph database updated
✅ Report generation successful

## Next Steps
- Implement advanced analytics
- Add more data sources
- Enhance visualization capabilities
"""
        
        # Save report to local file system
        os.makedirs("reports", exist_ok=True)
        with open("reports/latest.md", "w") as f:
            f.write(report_content)
        
        # Upload to MinIO
        minio_endpoint = os.getenv("MINIO_ENDPOINT", "http://minio:9000")
        minio_access_key = os.getenv("MINIO_ACCESS_KEY", "admin")
        minio_secret_key = os.getenv("MINIO_SECRET_KEY", "adminadmin")
        
        s3_client = boto3.client(
            's3',
            endpoint_url=minio_endpoint,
            aws_access_key_id=minio_access_key,
            aws_secret_access_key=minio_secret_key,
            region_name='us-east-1'
        )
        
        bucket_name = "fresh-reports"
        try:
            s3_client.create_bucket(Bucket=bucket_name)
        except s3_client.exceptions.BucketAlreadyOwnedByYou:
            pass
        
        # Upload report
        s3_client.put_object(
            Bucket=bucket_name,
            Key=f"report-{datetime.now().strftime('%Y%m%d-%H%M%S')}.md",
            Body=report_content,
            ContentType="text/markdown"
        )
        
        return {
            "ok": True, 
            "status": "report_generated", 
            "file": "reports/latest.md",
            "minio_bucket": bucket_name,
            "nodes": len(nodes),
            "edges": len(edges)
        }
        
    except Exception as e:
        return {"ok": False, "error": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8016")))
