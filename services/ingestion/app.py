from fastapi import FastAPI, Query
import uvicorn, os

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/metrics")
def metrics():
    return "requests_total 1\n", 200, {"Content-Type": "text/plain; version=0.0.4"}

@app.get("/trigger")
def trigger(repo: str = Query(...)):
    # TODO: clone repo to /data or MinIO presigned upload, then emit Kafka event
    return {"ok": True, "repo": repo}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8011")))
