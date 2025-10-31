from pydantic import BaseModel
from pydantic.config import ConfigDict


class DocumentCreate(BaseModel):
    name: str

class DocumentRead(BaseModel):
    id: int
    project_id: int
    name: str
    model_config = ConfigDict(from_attributes=True)
