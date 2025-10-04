from fastapi import FastAPI
import uvicorn, os
import requests
import json

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
        dgraph_url = os.getenv("DGRAPH_URL", "http://dgraph:8080")
        
        # Step 1: Set up schema
        schema_payload = {
            "schema": """
                name: string @index(term) .
                repo: string @index(exact) .
            """
        }
        
        schema_response = requests.post(
            f"{dgraph_url}/alter",
            headers={"Content-Type": "application/json"},
            json=schema_payload
        )
        
        if schema_response.status_code not in [200, 201]:
            return {"ok": False, "error": f"Schema setup failed: {schema_response.text}"}
        
        # Step 2: Create mutation
        mutation_payload = {
            "set": [
                {
                    "repo": "jaffle-shop-classic"
                },
                {
                    "name": "demo-user",
                    "repo": "jaffle-shop-classic"
                }
            ],
            "commitNow": True
        }
        
        mutation_response = requests.post(
            f"{dgraph_url}/mutate",
            headers={"Content-Type": "application/json"},
            json=mutation_payload
        )
        
        if mutation_response.status_code not in [200, 201]:
            return {"ok": False, "error": f"Mutation failed: {mutation_response.text}"}
        
        mutation_data = mutation_response.json()
        
        return {
            "ok": True, 
            "status": "apply_complete", 
            "uids": mutation_data.get("data", {}).get("uids", {}),
            "nodes_created": len(mutation_payload["set"]),
            "schema_applied": True
        }
        
    except Exception as e:
        return {"ok": False, "error": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8014")))
