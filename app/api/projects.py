from __future__ import annotations

import os

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.core.auth_dep import get_current_user
from app.core.db import get_db
from app.core.permissions import require_owner, require_owner_or_access
from app.models.document import Document
from app.models.project import Project, ProjectAccess
from app.models.user import User as UserModel
from app.schemas.access import AccessGrantIn, AccessOut
from app.schemas.document import DocumentRead
from app.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate

load_dotenv()
router = APIRouter(prefix="/projects", tags=["Projects"])
s3 = boto3.client(
    "s3",
    region_name=os.getenv("AWS_REGION"),
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
)
BUCKET = os.getenv("S3_BUCKET")
if not BUCKET:
    raise RuntimeError("S3_BUCKET env değişkeni gerekli (S3_BUCKET).")


def s3_key(project_id: int, name: str) -> str:
    return f"project-docs/{project_id}/{name}"


def ensure_project_access(db: Session, user_id: int, project_id: int) -> None:
    if db.query(Project).filter(Project.id == project_id, Project.owner_id == user_id).first():
        return
    pa = (
        db.query(ProjectAccess)
        .filter(
            ProjectAccess.project_id == project_id,
            ProjectAccess.user_id == user_id,
            ProjectAccess.can_access.is_(True),
        )
        .first()
    )
    if not pa:
        raise HTTPException(status_code=403, detail="Not authorized")


@router.post("/{project_id}/documents", status_code=201)
def upload_documents(
    project_id: int,
    files: list[UploadFile] = File(...),
    overwrite: bool = Form(False),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    ensure_project_access(db, current_user.id, project_id)
    created: list[dict] = []
    for f in files:
        name = f.filename
        if not name:
            raise HTTPException(status_code=400, detail="filename missing")
        key = s3_key(project_id, name)
        existing = db.query(Document).filter_by(project_id=project_id, name=name).first()
        if existing and not overwrite:
            raise HTTPException(status_code=409, detail=f"File already exists: {name}")
        s3.upload_fileobj(
            f.file,
            BUCKET,
            key,
            ExtraArgs={"ContentType": f.content_type or "application/octet-stream"},
        )
        if not existing:
            doc = Document(project_id=project_id, name=name)
            db.add(doc)
            db.commit()
            db.refresh(doc)
            created.append({"id": doc.id, "name": doc.name})
        else:
            created.append({"id": existing.id, "name": existing.name})
    return {"project_id": project_id, "files": created}


@router.get("/document/{document_id}")
def download_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    ensure_project_access(db, current_user.id, doc.project_id)
    key = s3_key(doc.project_id, doc.name)
    try:
        obj = s3.get_object(Bucket=BUCKET, Key=key)
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code")
        if code == "NoSuchKey":
            raise HTTPException(status_code=404, detail="File not found in storage")
        raise
    return StreamingResponse(
        obj["Body"],
        media_type=obj.get("ContentType", "application/octet-stream"),
        headers={"Content-Disposition": f'attachment; filename="{doc.name}"'},
    )


@router.put("/document/{document_id}")
def update_document(
    document_id: int,
    file: UploadFile | None = File(None),
    new_name: str | None = Form(None),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    ensure_project_access(db, current_user.id, doc.project_id)
    old_key = s3_key(doc.project_id, doc.name)
    if new_name is None or new_name == doc.name:
        if not file:
            raise HTTPException(status_code=400, detail="No file provided")
        s3.upload_fileobj(
            file.file,
            BUCKET,
            old_key,
            ExtraArgs={"ContentType": file.content_type or "application/octet-stream"},
        )
        return {"message": "content updated", "id": doc.id, "name": doc.name}
    new_key = s3_key(doc.project_id, new_name)
    if file:
        s3.upload_fileobj(
            file.file,
            BUCKET,
            new_key,
            ExtraArgs={"ContentType": file.content_type or "application/octet-stream"},
        )
    else:
        s3.copy_object(Bucket=BUCKET, CopySource={"Bucket": BUCKET, "Key": old_key}, Key=new_key)
    try:
        s3.delete_object(Bucket=BUCKET, Key=old_key)
    except ClientError:
        pass
    doc.name = new_name
    db.commit()
    db.refresh(doc)
    return {"message": "renamed", "id": doc.id, "name": doc.name}


@router.delete("/document/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    ensure_project_access(db, current_user.id, doc.project_id)
    key = s3_key(doc.project_id, doc.name)
    try:
        s3.delete_object(Bucket=BUCKET, Key=key)
    except ClientError:
        pass
    db.delete(doc)
    db.commit()
    return None


@router.post("/", response_model=ProjectRead)
def create_project(
    payload: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    new_project = Project(
        name=payload.name,
        description=payload.description,
        owner_id=current_user.id,
    )
    db.add(new_project)
    db.commit()
    db.refresh(new_project)
    return new_project


@router.get("/", response_model=list[ProjectRead])
def list_projects(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    q = (
        db.query(Project)
        .outerjoin(ProjectAccess, ProjectAccess.project_id == Project.id)
        .filter(
            or_(
                Project.owner_id == current_user.id,
                and_(
                    ProjectAccess.user_id == current_user.id,
                    ProjectAccess.can_access.is_(True),
                ),
            )
        )
        .distinct()
    )
    return q.all()


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(project: Project = Depends(require_owner_or_access)):
    return project


@router.put("/{project_id}", response_model=ProjectRead)
def update_project(
    project_id: int,
    payload: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(project, field, value)
    db.commit()
    db.refresh(project)
    return project


@router.get("/{project_id}/documents", response_model=list[DocumentRead])
def list_project_documents(
    project: Project = Depends(require_owner_or_access),
    db: Session = Depends(get_db),
):
    return db.query(Document).filter(Document.project_id == project.id).all()


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project: Project = Depends(require_owner), db: Session = Depends(get_db)):
    db.delete(project)
    db.commit()
    return None


@router.post("/{project_id}/access/{user_id}", status_code=status.HTTP_201_CREATED)
def grant_access_by_id(
    project_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    pa = (
        db.query(ProjectAccess)
        .filter(ProjectAccess.project_id == project_id, ProjectAccess.user_id == user_id)
        .first()
    )
    if pa:
        pa.can_access = True
    else:
        pa = ProjectAccess(project_id=project_id, user_id=user_id, can_access=True)
        db.add(pa)
    db.commit()
    return {"message": "Access granted"}


@router.get("/{project_id}/access", response_model=list[AccessOut])
def list_access(project: Project = Depends(require_owner), db: Session = Depends(get_db)):
    rows = (
        db.query(ProjectAccess, UserModel)
        .join(UserModel, UserModel.id == ProjectAccess.user_id)
        .filter(ProjectAccess.project_id == project.id)
        .all()
    )

    owner_user = db.query(UserModel).filter(UserModel.id == project.owner_id).first()
    if owner_user is None:
        raise HTTPException(status_code=404, detail="owner not found")

    result = [AccessOut(user_id=owner_user.id, login=owner_user.login, can_access=True)]
    result += [AccessOut(user_id=u.id, login=u.login, can_access=pa.can_access) for pa, u in rows]
    return result




@router.post("/{project_id}/access", status_code=status.HTTP_204_NO_CONTENT)
def grant_or_update_access(
    payload: AccessGrantIn,
    project: Project = Depends(require_owner),
    db: Session = Depends(get_db),
):
    target = db.query(UserModel).filter(UserModel.login == payload.login).first()
    if not target:
        raise HTTPException(status_code=404, detail="user not found")
    if target.id == project.owner_id:
        return
    pa = (
        db.query(ProjectAccess)
        .filter(ProjectAccess.project_id == project.id, ProjectAccess.user_id == target.id)
        .first()
    )
    if not pa:
        pa = ProjectAccess(project_id=project.id, user_id=target.id, can_access=payload.can_access)
        db.add(pa)
    else:
        pa.can_access = payload.can_access
    db.commit()



@router.delete("/{project_id}/access/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_access(
    user_id: int,
    project: Project = Depends(require_owner),
    db: Session = Depends(get_db),
):
    pa = (
        db.query(ProjectAccess)
        .filter(ProjectAccess.project_id == project.id, ProjectAccess.user_id == user_id)
        .first()
    )
    if not pa:
        raise HTTPException(status_code=404, detail="access not found")
    db.delete(pa)
    db.commit()
