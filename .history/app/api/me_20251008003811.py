from fastapi import APIRouter, Depends

from app.core.auth_dep import get_current_user
from app.models.user import User

router = APIRouter(tags=["Me"])

@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return {"id": user.id, "login": user.login}
