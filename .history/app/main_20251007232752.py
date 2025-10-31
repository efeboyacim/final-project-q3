from fastapi import Depends, FastAPI
from sqlalchemy.orm import Session

from app.core.db import Base, engine, get_db
from app.models.project import Project

app = FastAPI(title="Final Project API")

# tabloyu ilk çalıştırmada otomatik oluştur
Base.metadata.create_all(bind=engine)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/projects")
def get_projects(db: Session = Depends(get_db)):
    return db.query(Project).all()
