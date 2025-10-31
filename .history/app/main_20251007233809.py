from fastapi import FastAPI

from app.api.projects import router as project_router
from app.core.db import Base, engine

app = FastAPI(title="Final Project API")

Base.metadata.create_all(bind=engine)

app.include_router(project_router)

@app.get("/health")
def health():
    return {"status": "ok"}
