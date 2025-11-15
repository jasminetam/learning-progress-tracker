from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel


class ResourceType(str, Enum):
    course = "course"
    book = "book"
    video_series = "video_series"
    article = "article"
    other = "other"


class ResourceStatus(str, Enum):
    not_started = "not_started"
    in_progress = "in_progress"
    completed = "completed"
    abandoned = "abandoned"


class ResourceBase(BaseModel):
    title: str
    resource_type: ResourceType
    provider: Optional[str] = None
    url: Optional[str] = None
    total_units: Optional[int] = None  # chapters, lessons, etc.
    tags: List[str] = []
    target_skills: List[str] = []


class ResourceCreate(ResourceBase):
    pass

class ResourceUpdate(BaseModel):
    status: Optional[ResourceStatus] = None
    completed_units: Optional[int] = None

class Resource(ResourceBase):
    id: int
    status: ResourceStatus
    completed_units: int = 0
    progress_percent: float = 0.0

    class Config:
        orm_mode = True


class StudySessionBase(BaseModel):
    resource_id: int
    started_at: datetime
    ended_at: datetime
    notes: Optional[str] = None


class StudySession(StudySessionBase):
    id: int

    class Config:
        orm_mode = True
