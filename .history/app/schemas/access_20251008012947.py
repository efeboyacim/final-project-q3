from pydantic import BaseModel


class AccessGrantIn(BaseModel):
    login: str
    can_access: bool = True

class AccessOut(BaseModel):
    user_id: int
    login: str
    can_access: bool
