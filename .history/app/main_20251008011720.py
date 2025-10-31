from fastapi import FastAPI

from app.api.auth import router as auth_router
from app.api.me import router as me_router
from app.api.projects import router as project_router  # istersen korumayı sonra ekle
from app.core.db import Base, engine

app = FastAPI(title="Final Project API")
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

app.include_router(auth_router)
app.include_router(me_router)
app.include_router(project_router)

@app.get("/health")
def health(): return {"status": "ok"}
