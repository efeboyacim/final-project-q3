from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.schemas.auth import LoginIn, RegisterIn, TokenOut, UserOut

router = APIRouter(tags=["Auth"])

@router.post("/auth", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterIn, db: Session = Depends(get_db)):
    if payload.password != payload.repeat_password:
        raise HTTPException(status_code=400, detail="passwords do not match")
    if db.query(User).filter(User.login == payload.login).first():
        raise HTTPException(status_code=400, detail="login already exists")
    user = User(login=payload.login, password_hash=hash_password(payload.password))
    db.add(user); db.commit(); db.refresh(user)
    return user

@router.post("/login", response_model=TokenOut)
def login(payload: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.login == payload.login).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="invalid credentials")
    token = create_access_token(sub=user.login, expires_minutes=settings.access_token_expire_minutes)
    return {"access_token": token, "token_type": "bearer"}

from fastapi.security import OAuth2PasswordRequestForm

# ...

@router.post("/token", response_model=TokenOut)  # OAuth2 password flow standardı
def token(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.login == form.username).first()
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=401, detail="invalid credentials")
    access = create_access_token(sub=user.login, expires_minutes=settings.access_token_expire_minutes)
    return {"access_token": access, "token_type": "bearer"}

