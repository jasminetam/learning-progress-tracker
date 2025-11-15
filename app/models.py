from datetime import datetime
from typing import List, Optional

from sqlmodel import JSON, Column, Field, SQLModel

from .schemas import ResourceStatus, ResourceType


class ResourceDB(SQLModel, table=True):
    __tablename__ = "resources"

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str

    resource_type: ResourceType
    provider: Optional[str] = None
    url: Optional[str] = None

    total_units: Optional[int] = None
    completed_units: int = 0
    progress_percent: float = 0.0

    status: ResourceStatus = Field(default=ResourceStatus.not_started)

    # store tags / skills as JSON arrays
    tags: List[str] = Field(
        sa_column=Column(JSON, nullable=False, default=list)
    )
    target_skills: List[str] = Field(
        sa_column=Column(JSON, nullable=False, default=list)
    )


class StudySessionDB(SQLModel, table=True):
    __tablename__ = "study_sessions"

    id: Optional[int] = Field(default=None, primary_key=True)
    resource_id: int = Field(foreign_key="resources.id")

    started_at: datetime
    ended_at: datetime
    notes: Optional[str] = None
