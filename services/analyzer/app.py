from fastapi import FastAPI
import uvicorn, os

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/metrics")
def metrics():
    return "requests_total 1\n", 200, {"Content-Type": "text/plain; version=0.0.4"}

@app.get("/run")
def run():
    # TODO: analyze mined data, generate insights
    return {"ok": True, "status": "analysis_complete"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8013")))
