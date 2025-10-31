from pydantic import BaseModel, Field, field_validator


class RegisterIn(BaseModel):
    login: str = Field(min_length=3, max_length=150)
    password: str = Field(min_length=6, max_length=72)
    repeat_password: str

    @field_validator("repeat_password")
    @classmethod
    def passwords_match(cls, v, info):
        if "password" in info.data and v != info.data["password"]:
            raise ValueError("passwords do not match")
        return v


class UserOut(BaseModel):
    id: int
    login: str

    class Config:
        orm_mode = True


class LoginIn(BaseModel):
    login: str
    password: str = Field(min_length=6, max_length=72)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
