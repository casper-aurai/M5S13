from fastapi import FastAPI
import uvicorn, os
import mgclient

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/metrics")
def metrics():
    return "requests_total 1\n", 200, {"Content-Type": "text/plain; version=0.0.4"}

@app.get("/apply")
def apply():
    try:
        # Connect to Memgraph via Bolt
        connection = mgclient.connect(
            host="memgraph",
            port=7687
        )
        
        # Create demo nodes and edges
        cursor = connection.cursor()
        
        # Create a Repo node
        cursor.execute("CREATE (r:Repo {name: 'jaffle-shop-classic', type: 'dbt', url: 'https://github.com/dbt-labs/jaffle-shop-classic'})")
        
        # Create a DataModel node
        cursor.execute("CREATE (d:DataModel {name: 'customer_orders', type: 'star_schema'})")
        
        # Create an edge between them
        cursor.execute("MATCH (r:Repo {name: 'jaffle-shop-classic'}), (d:DataModel {name: 'customer_orders'}) CREATE (r)-[:IMPLEMENTS]->(d)")
        
        # Commit the transaction
        connection.commit()
        
        # Get some stats
        cursor.execute("MATCH (n) RETURN count(n) as node_count")
        node_count = cursor.fetchone()[0]
        
        cursor.execute("MATCH ()-[r]->() RETURN count(r) as edge_count")
        edge_count = cursor.fetchone()[0]
        
        connection.close()
        
        return {
            "ok": True, 
            "status": "apply_complete", 
            "nodes_created": node_count, 
            "edges_created": edge_count
        }
        
    except Exception as e:
        return {"ok": False, "error": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8014")))
