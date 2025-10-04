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

@app.get("/query")
def query(q: str = ""):
    try:
        dgraph_url = os.getenv("DGRAPH_URL", "http://dgraph:8080")
        
        # Default query if none provided
        if not q:
            q = "{ all(func: has(repo)) { uid repo name } }"
        
        query_payload = {
            "query": q
        }
        
        response = requests.post(
            f"{dgraph_url}/query",
            headers={"Content-Type": "application/json"},
            json=query_payload
        )
        
        if response.status_code != 200:
            return {"ok": False, "error": f"Query failed: {response.text}"}
        
        query_data = response.json()
        
        return {
            "ok": True,
            "query": q,
            "results": query_data.get("data", {}),
            "extensions": query_data.get("extensions", {})
        }
        
    except Exception as e:
        return {"ok": False, "error": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8015")))
