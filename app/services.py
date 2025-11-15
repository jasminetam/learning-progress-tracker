from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlmodel import Session, select

from .models import ResourceDB, StudySessionDB
from .schemas import (
    Resource,
    ResourceCreate,
    ResourceStatus,
    ResourceUpdate,
    StudySession,
    StudySessionBase,
)

# ---------- Mappers (DB <-> API schema) ----------

def resource_db_to_schema(db: ResourceDB) -> Resource:
    assert db.id is not None, "ResourceDB.id should not be None after commit"

    return Resource(
        id=db.id,
        title=db.title,
        resource_type=db.resource_type,
        provider=db.provider,
        url=db.url,
        total_units=db.total_units,
        tags=db.tags or [],
        target_skills=db.target_skills or [],
        status=db.status,
        completed_units=db.completed_units,
        progress_percent=db.progress_percent,
    )



def session_db_to_schema(db: StudySessionDB) -> StudySession:
    assert db.id is not None, "StudySessionDB.id should not be None after commit"

    return StudySession(
        id=db.id,
        resource_id=db.resource_id,
        started_at=db.started_at,
        ended_at=db.ended_at,
        notes=db.notes,
    )



# ---------- Resource service ----------

def create_resource(
    payload: ResourceCreate,
    session: Session,
) -> Resource:
    db_resource = ResourceDB(
        title=payload.title,
        resource_type=payload.resource_type,
        provider=payload.provider,
        url=payload.url,
        total_units=payload.total_units,
        tags=payload.tags or [],
        target_skills=payload.target_skills or [],
    )
    session.add(db_resource)
    session.commit()
    session.refresh(db_resource)
    return resource_db_to_schema(db_resource)


def list_resources(
    session: Session,
    status: Optional[ResourceStatus] = None,
    resource_type: Optional[str] = None,
    tag: Optional[str] = None,
    skill: Optional[str] = None,
) -> List[Resource]:
    db_resources = session.exec(select(ResourceDB)).all()

    # simple in-Python filters
    if status is not None:
        db_resources = [r for r in db_resources if r.status == status]
    if resource_type is not None:
        db_resources = [r for r in db_resources if r.resource_type == resource_type]
    if tag is not None:
        db_resources = [r for r in db_resources if tag in (r.tags or [])]
    if skill is not None:
        db_resources = [r for r in db_resources if skill in (r.target_skills or [])]

    return [resource_db_to_schema(r) for r in db_resources]


def get_resource_by_id(
    resource_id: int,
    session: Session,
) -> Optional[Resource]:
    db_resource = session.get(ResourceDB, resource_id)
    if not db_resource:
        return None
    return resource_db_to_schema(db_resource)


def update_resource(
    resource_id: int,
    payload: ResourceUpdate,
    session: Session,
) -> Optional[Resource]:
    db_resource = session.get(ResourceDB, resource_id)
    if not db_resource:
        return None

    # status
    if payload.status is not None:
        db_resource.status = payload.status

    # progress / completed_units
    if payload.completed_units is not None:
        completed = max(0, payload.completed_units)
        if db_resource.total_units is not None and db_resource.total_units > 0:
            completed = min(completed, db_resource.total_units)
            db_resource.completed_units = completed
            db_resource.progress_percent = (
                completed / db_resource.total_units * 100.0
            )
            if completed == db_resource.total_units:
                db_resource.status = ResourceStatus.completed
        else:
            db_resource.completed_units = completed

    session.add(db_resource)
    session.commit()
    session.refresh(db_resource)
    return resource_db_to_schema(db_resource)


# ---------- Study session service ----------

def create_study_session(
    payload: StudySessionBase,
    session: Session,
) -> Optional[StudySession]:
    # verify resource exists
    db_resource = session.get(ResourceDB, payload.resource_id)
    if not db_resource:
        return None

    db_session = StudySessionDB(
        resource_id=payload.resource_id,
        started_at=payload.started_at,
        ended_at=payload.ended_at,
        notes=payload.notes,
    )
    session.add(db_session)
    session.commit()
    session.refresh(db_session)
    return session_db_to_schema(db_session)


def list_study_sessions(
    session: Session,
    resource_id: Optional[int] = None,
) -> List[StudySession]:
    db_sessions = session.exec(select(StudySessionDB)).all()
    if resource_id is not None:
        db_sessions = [s for s in db_sessions if s.resource_id == resource_id]
    return [session_db_to_schema(s) for s in db_sessions]


# ---------- Stats service ----------

def compute_overview_stats(session: Session) -> Dict[str, Any]:
    resources = session.exec(select(ResourceDB)).all()
    sessions_db = session.exec(select(StudySessionDB)).all()

    total_resources = len(resources)
    completed_resources = sum(
        1 for r in resources if r.status == ResourceStatus.completed
    )
    in_progress_resources = sum(
        1 for r in resources if r.status == ResourceStatus.in_progress
    )

    # total study time
    total_minutes = 0.0
    for s in sessions_db:
        start = (
            s.started_at
            if isinstance(s.started_at, datetime)
            else datetime.fromisoformat(str(s.started_at))
        )
        end = (
            s.ended_at
            if isinstance(s.ended_at, datetime)
            else datetime.fromisoformat(str(s.ended_at))
        )
        total_minutes += max(0.0, (end - start).total_seconds() / 60.0)

    # by type
    by_type: Dict[str, Dict[str, int]] = {}
    for r in resources:
        t = r.resource_type.value
        if t not in by_type:
            by_type[t] = {"count": 0, "completed": 0}
        by_type[t]["count"] += 1
        if r.status == ResourceStatus.completed:
            by_type[t]["completed"] += 1

    # by skill
    by_skill: Dict[str, Dict[str, float | int]] = {}
    for r in resources:
        for skill in r.target_skills or []:
            if skill not in by_skill:
                by_skill[skill] = {
                    "resources": 0,
                    "completed": 0,
                    "hours": 0.0,
                }
            by_skill[skill]["resources"] += 1
            if r.status == ResourceStatus.completed:
                by_skill[skill]["completed"] += 1

    # attribute hours to skills
    for s in sessions_db:
        resource = next((r for r in resources if r.id == s.resource_id), None)
        if not resource or not resource.target_skills:
            continue

        start = (
            s.started_at
            if isinstance(s.started_at, datetime)
            else datetime.fromisoformat(str(s.started_at))
        )
        end = (
            s.ended_at
            if isinstance(s.ended_at, datetime)
            else datetime.fromisoformat(str(s.ended_at))
        )
        duration_hours = max(0.0, (end - start).total_seconds() / 3600.0)
        share = duration_hours / len(resource.target_skills)
        for skill in resource.target_skills:
            by_skill[skill]["hours"] += share

    return {
        "total_resources": total_resources,
        "completed_resources": completed_resources,
        "in_progress_resources": in_progress_resources,
        "total_study_hours": round(total_minutes / 60.0, 2),
        "by_type": by_type,
        "by_skill": {
            k: {
                "resources": v["resources"],
                "completed": v["completed"],
                "hours": round(v["hours"], 2),
            }
            for k, v in by_skill.items()
        },
    }
