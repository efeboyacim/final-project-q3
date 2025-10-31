import os

import boto3
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.permissions import require_owner_or_access
from app.dependencies import get_current_user
from app.models.document import Document
from app.models.project import Project
from app.models.user import User
from app.schemas.document import DocumentRead
from app.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate

load_dotenv()  
router = APIRouter(prefix="/projects", tags=["Projects"])
# S3 client
s3 = boto3.client(
    "s3",
    region_name=os.getenv("AWS_REGION"),
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
)
BUCKET = os.getenv("S3_BUCKET")

def s3_key(project_id: int, name: str) -> str:
    return f"project-docs/{project_id}/{name}"

def ensure_access(db: Session, user_id: int, project_id: int):
    # owner mı?
    if db.query(Project).filter(Project.id==project_id, Project.owner_id==user_id).first():
        return
    # participant mı?
    if not db.query(ProjectAccess).filter(
        ProjectAccess.project_id==project_id,
        ProjectAccess.user_id==user_id,
        ProjectAccess.can_access.is_(True)
    ).first():
        raise HTTPException(403, "Not authorized")

@router.post("/{project_id}/documents", status_code=201)
def upload_documents(
    project_id: int,
    files: list[UploadFile] = File(...),       # çoklu yükleme
    overwrite: bool = Form(False),             # aynı isim varsa: False=409, True=üzerine yaz
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_access(db, current_user.id, project_id)

    created: list[dict] = []
    for f in files:
        name = f.filename
        key = s3_key(project_id, name)

        # var mı?
        existing = db.query(Document).filter_by(project_id=project_id, name=name).first()
        if existing and not overwrite:
            raise HTTPException(409, f"File already exists: {name}")

        # S3’e yükle
        s3.upload_fileobj(
            f.file, BUCKET, key,
            ExtraArgs={"ContentType": f.content_type or "application/octet-stream"}
        )

        # DB kaydı (yoksa ekle)
        if not existing:
            doc = Document(project_id=project_id, name=name)
            db.add(doc)
            db.commit(); db.refresh(doc)
            created.append({"id": doc.id, "name": doc.name})
        else:
            created.append({"id": existing.id, "name": existing.name})

    return {"project_id": project_id, "files": created}

# 🔒 Tüm endpointler giriş zorunluluğu ister
@router.post("/", response_model=ProjectRead)
def create_project(
    payload: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    new_project = Project(
        name=payload.name,
        description=payload.description,
        owner_id=current_user.id  # otomatik atanır
    )
    db.add(new_project)
    db.commit()
    db.refresh(new_project)
    return new_project


# app/api/projects.py
from sqlalchemy import and_, or_

from app.models.project import ProjectAccess


@router.get("/", response_model=list[ProjectRead])
def list_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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



from app.core.permissions import require_owner


# 🔹 Projeyi sadece erişimi olan veya sahibi görebilir
@router.get("/{project_id}", response_model=ProjectRead)
def get_project(
    project: Project = Depends(require_owner_or_access)
):
    return project



@router.put("/{project_id}", response_model=ProjectRead)
def update_project(
    project_id: int,
    payload: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
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

@router.get("/download/{project_name}")
def download_document(project_name:str):
    try:
        # S3'ten dosyayı stream olarak getir
        obj = s3.get_object(Bucket=BUCKET, Key=project_name)
        return StreamingResponse(
            obj["Body"],
            media_type="application/octet-stream",
            headers={"Content-Disposition": f"attachment; filename={project_name}"}
        )
    except s3.exceptions.NoSuchKey:
        raise HTTPException(status_code=404, detail="Dosya bulunamadı.")
    
@router.put("/document/{document_id}")
def update_document(document_id: str, file: UploadFile = File(...)):
    try:
        s3.upload_fileobj(file.file, BUCKET, document_id)
        return {"message": f"{document_id} başarıyla güncellendi."}
    except s3.exceptions.NoSuchKey:
        raise HTTPException(status_code=404, detail="Belge bulunamadı.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    


# 🔹 Sadece owner silebilir
@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project: Project = Depends(require_owner),
    db: Session = Depends(get_db)
):
    db.delete(project)
    db.commit()
    return None


@router.post("/{project_id}/access/{user_id}", status_code=201)
def grant_access(
    project_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # sadece owner erişim verebilir
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    access = (
        db.query(ProjectAccess)
        .filter(ProjectAccess.project_id == project_id, ProjectAccess.user_id == user_id)
        .first()
    )
    if access:
        access.can_access = True
    else:
        access = ProjectAccess(project_id=project_id, user_id=user_id, can_access=True)
        db.add(access)
    db.commit()
    return {"message": "Access granted"}

from app.core.permissions import require_owner
from app.models.user import User as UserModel
from app.schemas.access import AccessGrantIn, AccessOut


@router.get("/{project_id}/access", response_model=list[AccessOut])
def list_access(
    project: Project = Depends(require_owner),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(ProjectAccess, UserModel)
        .join(UserModel, UserModel.id == ProjectAccess.user_id)
        .filter(ProjectAccess.project_id == project.id)
        .all()
    )

    # owner satırı eklenir
    owner_user = db.query(UserModel).filter(UserModel.id == project.owner_id).first()
    result = [
        AccessOut(user_id=owner_user.id, login=owner_user.login, can_access=True)
    ]

    result += [
        AccessOut(user_id=u.id, login=u.login, can_access=pa.can_access)
        for pa, u in rows
    ]
    return result


# Grant / update access (sadece owner)
@router.post("/{project_id}/access", status_code=status.HTTP_204_NO_CONTENT)
def grant_access(
    project: Project = Depends(require_owner),
    payload: AccessGrantIn = ...,
    db: Session = Depends(get_db),
):
    target = db.query(UserModel).filter(UserModel.login == payload.login).first()
    if not target:
        raise HTTPException(status_code=404, detail="user not found")
    if target.id == project.owner_id:
        return  # owner’a gerek yok

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

# Revoke access (sadece owner)
@router.delete("/{project_id}/access/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_access(
    project: Project = Depends(require_owner),
    user_id: int = ...,
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
