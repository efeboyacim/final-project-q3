from fastapi import FastAPI

app = FastAPI(title="Final Project API")

@app.get("/health")
def health():
    return {"status": "ok"}
