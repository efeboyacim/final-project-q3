from fastapi import FastAPI
from sqlalchemy import text

from app.api import auth, projects
from app.core.db import Base, engine
from app.api import internal
import os

app = FastAPI(title="Final Project API")
Base.metadata.create_all(bind=engine)

script_path = "Database-Scripts/lamda-database.txt"
if os.path.exists(script_path):
    with open(script_path, "r", encoding="utf-8") as f:
        sql = f.read().strip()
    if sql:
        with engine.begin() as conn:
            conn.execute(text(sql))
        print(f"[INFO] SQL script executed: {script_path}")
    else:
        print(f"[INFO] SQL script is empty: {script_path}")
else:
    print(f"[INFO] SQL script not found: {script_path}")
app = FastAPI()


app.include_router(internal.router)
app.include_router(auth.router)
app.include_router(projects.router)

@app.get("/health")
def health(): return {"status": "ok"}
