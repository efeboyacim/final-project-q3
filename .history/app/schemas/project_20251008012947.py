from pydantic import BaseModel, Field


# Ortak temel alanlar
class ProjectBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None


# Yeni proje oluştururken kullanılacak
class ProjectCreate(ProjectBase):
    pass  # owner_id istemiyoruz, backend otomatik ekleyecek


# Güncelleme için (isteğe bağlı alanlar)
class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


# Okuma (GET) işlemleri için dönüş modeli
class ProjectRead(ProjectBase):
    id: int
    owner_id: int  # Projeyi kimin oluşturduğunu gösterecek

    class Config:
        orm_mode = True  # SQLAlchemy objesini JSON’a çevirmeyi sağlar
