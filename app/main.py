from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from sqlmodel import Session

from . import services
from .database import create_db_and_tables, get_session
from .schemas import (
    Resource,
    ResourceCreate,
    ResourceStatus,
    ResourceUpdate,
    StudySession,
    StudySessionBase,
)

app = FastAPI(title="Learning Progress Tracker")


@app.on_event("startup")
def on_startup() -> None:
    create_db_and_tables()


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/docs")


@app.post("/resources", response_model=Resource)
def create_resource(
    payload: ResourceCreate,
    session: Session = Depends(get_session),
) -> Resource:
    return services.create_resource(payload, session)


@app.get("/resources", response_model=List[Resource])
def list_resources(
    status: Optional[ResourceStatus] = None,
    resource_type: Optional[str] = None,
    tag: Optional[str] = None,
    skill: Optional[str] = None,
    session: Session = Depends(get_session),
) -> List[Resource]:
    return services.list_resources(
        session=session,
        status=status,
        resource_type=resource_type,
        tag=tag,
        skill=skill,
    )


@app.get("/resources/{resource_id}", response_model=Resource)
def get_resource(
    resource_id: int,
    session: Session = Depends(get_session),
) -> Resource:
    res = services.get_resource_by_id(resource_id, session)
    if not res:
        raise HTTPException(status_code=404, detail="Resource not found")
    return res


@app.patch("/resources/{resource_id}", response_model=Resource)
def update_resource(
    resource_id: int,
    payload: ResourceUpdate,
    session: Session = Depends(get_session),
) -> Resource:
    updated = services.update_resource(resource_id, payload, session)
    if not updated:
        raise HTTPException(status_code=404, detail="Resource not found")
    return updated


@app.post("/sessions", response_model=StudySession)
def create_session(
    payload: StudySessionBase,
    session: Session = Depends(get_session),
) -> StudySession:
    created = services.create_study_session(payload, session)
    if not created:
        raise HTTPException(status_code=404, detail="Resource not found")
    return created


@app.get("/sessions", response_model=List[StudySession])
def list_sessions(
    resource_id: Optional[int] = None,
    session: Session = Depends(get_session),
) -> List[StudySession]:
    return services.list_study_sessions(session, resource_id=resource_id)


@app.get("/stats/overview")
def get_overview(
    session: Session = Depends(get_session),
) -> Dict[str, Any]:
    return services.compute_overview_stats(session)
