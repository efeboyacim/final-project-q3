from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

engine = create_engine(settings.sqlalchemy_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

# --- Bu fonksiyon dependency olarak kullanılacak ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
