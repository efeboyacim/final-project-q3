from pydantic import BaseModel, Field


class RegisterIn(BaseModel):
    login: str = Field(min_length=3, max_length=150)
    password: str = Field(min_length=6)
    repeat_password: str

class UserOut(BaseModel):
    id: int
    login: str
    class Config: orm_mode = True

class LoginIn(BaseModel):
    login: str
    password: str

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
