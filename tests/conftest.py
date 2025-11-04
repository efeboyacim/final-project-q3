# tests/conftest.py
import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from passlib.context import CryptContext
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.db import Base, get_db
from app.main import app
from app.models.project import Project as ProjectModel
from app.models.user import User as UserModel

# -------------------------
# Test DB: SQLite in-memory
# -------------------------
TEST_DATABASE_URL = "sqlite+pysqlite:///:memory:"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

@pytest.fixture(scope="session", autouse=True)
def _create_schema():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db():
    conn = engine.connect()
    txn = conn.begin()
    session = TestingSessionLocal(bind=conn)
    try:
        yield session
    finally:
        session.close()
        txn.rollback()
        conn.close()

# FastAPI dependency override: get_db
@pytest.fixture(autouse=True)
def _override_db_dependency(db):
    app.dependency_overrides[get_db] = lambda: db
    yield
    app.dependency_overrides.pop(get_db, None)

# -------------------------
# Auth: current_user override
# -------------------------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@pytest.fixture
def user(db: Session):
    u = UserModel(
        login="tester",
        password_hash=pwd_context.hash("testpass"),
    )
    db.add(u)
    db.flush()
    db.refresh(u)
    return u

@pytest.fixture(autouse=True)
def override_current_user(user):
    import app.core.auth_dep as auth_dep
    app.dependency_overrides[auth_dep.get_current_user] = lambda: user
    yield
    app.dependency_overrides.pop(auth_dep.get_current_user, None)

# -------------------------
# Permissions bypass: orijinal callable -> dummy
# -------------------------
@pytest.fixture(autouse=True)
def relax_permissions():
    import app.core.auth_dep as auth_dep
    import app.core.permissions as perms

    # İMZA ÖNEMLİ: Orijinal dependency gibi db ve current_user Depends ile alınır.
    def _dummy_dependency(
        project_id: int,
        db: Session = Depends(get_db),
        current_user: UserModel = Depends(auth_dep.get_current_user),
    ):
        proj = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
        if proj is None:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Project not found")
        return proj

    app.dependency_overrides[perms.require_owner_or_access] = _dummy_dependency
    app.dependency_overrides[perms.require_owner] = _dummy_dependency
    yield
    app.dependency_overrides.pop(perms.require_owner_or_access, None)
    app.dependency_overrides.pop(perms.require_owner, None)

# -------------------------
# S3: Moto mock ve env setup
# -------------------------
@pytest.fixture
def s3_env(monkeypatch):
    bucket = "test-bucket"
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.setenv("S3_BUCKET", bucket)
    monkeypatch.setenv("S3_EVENT_SHARED_SECRET", "test-secret")

    import boto3
    from moto import mock_aws

    with mock_aws():
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket=bucket)

        # Router modüllerindeki client ve BUCKET sabitlerini güncelle
        import app.api.internal as internal_api
        import app.api.projects as proj_api

        proj_api.s3 = s3
        proj_api.BUCKET = bucket

        internal_api.s3 = s3
        internal_api.BUCKET = bucket
        internal_api.SHARED = "test-secret"

        yield s3

# -------------------------
# FastAPI TestClient
# -------------------------
@pytest.fixture
def client():
    return TestClient(app)
