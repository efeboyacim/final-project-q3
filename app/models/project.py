from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)


    owner_id: Mapped[int] = mapped_column(
    ForeignKey("users.id", ondelete="CASCADE"),
    nullable=False,
    )


    owner = relationship("User")
    accesses = relationship("ProjectAccess", cascade="all, delete-orphan", back_populates="project")

    documents = relationship("Document", cascade="all, delete-orphan", back_populates="project")



class ProjectAccess(Base):
    __tablename__ = "project_accesses"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )


    can_access: Mapped[bool] = mapped_column(default=True, nullable=False)

    project = relationship("Project", back_populates="accesses")

    __table_args__ = (
        UniqueConstraint("project_id", "user_id", name="uq_project_user"),
    )
