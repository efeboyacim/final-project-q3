from pydantic import BaseModel


class ProjectBase(BaseModel):
    name: str
    description: str = "No description provided."

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None

class ProjectRead(ProjectBase):
    id: int

    class Config:
        orm_mode = True  # SQLAlchemy objelerini JSON’a çevirmek için gerekli
