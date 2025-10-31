from pydantic import BaseModel, ConfigDict, Field


class ProjectBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None



class ProjectCreate(ProjectBase):
    pass  



class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None



class ProjectRead(ProjectBase):
    id: int
    owner_id: int 

    model_config = ConfigDict(from_attributes=True)
