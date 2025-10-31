from fastapi import FastAPI

from app.core.db import Base, engine

app = FastAPI(title="Final Project API")
Base.metadata.create_all(bind=engine)

from fastapi import FastAPI

from app.api import auth, projects

app = FastAPI()

app.include_router(auth.router)
app.include_router(projects.router)

@app.get("/health")
def health(): return {"status": "ok"}
