from datetime import datetime, timedelta

import pytest
from sqlmodel import Session, SQLModel, create_engine

from app import services
from app.schemas import (
    ResourceCreate,
    ResourceStatus,
    ResourceUpdate,
    StudySessionBase,
)

# --- Fixtures: test database + session ---


@pytest.fixture
def engine():
    # In-memory SQLite database for unit tests
    engine = create_engine(
      "sqlite://",
      connect_args={"check_same_thread": False}
    )
    # make sure models are registered
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture
def session(engine):
    # New session per test
    with Session(engine) as session:
        yield session
    # no need to drop tables; in-memory DB disappears after engine is GC'd

def test_create_and_get_resource(session: Session):
    payload = ResourceCreate(
        title="FastAPI – The Complete Guide",
        resource_type="course",
        provider="Udemy",
        url="https://example.com/fastapi",
        total_units=20,
        tags=["backend", "python"],
        target_skills=["fastapi", "rest-api"],
    )

    created = services.create_resource(payload, session)

    assert created.id is not None
    assert created.title == "FastAPI – The Complete Guide"
    assert created.status == ResourceStatus.not_started
    assert created.completed_units == 0
    assert created.progress_percent == 0.0

    fetched = services.get_resource_by_id(created.id, session)
    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.title == created.title

def test_update_resource_progress_and_auto_complete(session: Session):
    # create
    created = services.create_resource(
        ResourceCreate(
            title="Algorithms Book",
            resource_type="book",
            provider="Book",
            total_units=10,
            tags=["algorithms"],
            target_skills=["algorithms"],
        ),
        session,
    )

    # half-way
    updated_half = services.update_resource(
        resource_id=created.id,
        payload=ResourceUpdate(completed_units=5),
        session=session,
    )
    assert updated_half is not None
    assert updated_half.completed_units == 5
    assert updated_half.progress_percent == 50.0
    assert updated_half.status != ResourceStatus.completed

    # full completion => status auto-completes
    updated_full = services.update_resource(
        resource_id=created.id,
        payload=ResourceUpdate(completed_units=10),
        session=session,
    )
    assert updated_full is not None
    assert updated_full.completed_units == 10
    assert updated_full.progress_percent == 100.0
    assert updated_full.status == ResourceStatus.completed

def test_list_resources_with_filters(session: Session):
    # two resources with different types/tags/status
    r1 = services.create_resource(
        ResourceCreate(
            title="FastAPI Course",
            resource_type="course",
            provider="Udemy",
            total_units=20,
            tags=["backend"],
            target_skills=["fastapi"],
        ),
        session,
    )
    r2 = services.create_resource(
        ResourceCreate(
            title="Algorithms Book",
            resource_type="book",
            provider="Book",
            total_units=10,
            tags=["algorithms"],
            target_skills=["algorithms"],
        ),
        session,
    )

    # mark first as in_progress
    services.update_resource(
        resource_id=r1.id,
        payload=ResourceUpdate(status=ResourceStatus.in_progress),
        session=session,
    )

    all_resources = services.list_resources(session=session)
    assert len(all_resources) == 2
    titles = {r.title for r in all_resources}
    assert r1.title in titles
    assert r2.title in titles 

    only_courses = services.list_resources(
        session=session, resource_type="course"
    )
    assert len(only_courses) == 1
    assert only_courses[0].title == "FastAPI Course"

    backend_tag = services.list_resources(session=session, tag="backend")
    assert len(backend_tag) == 1
    assert backend_tag[0].title == "FastAPI Course"

    only_in_progress = services.list_resources(
        session=session, status=ResourceStatus.in_progress
    )
    assert len(only_in_progress) == 1
    assert only_in_progress[0].id == r1.id

def test_create_and_list_study_sessions(session: Session):
    # create a resource first
    resource = services.create_resource(
        ResourceCreate(
            title="CS50x",
            resource_type="course",
            provider="edX",
            total_units=50,
            tags=["cs", "foundations"],
            target_skills=["computer-science"],
        ),
        session,
    )

    start = datetime.utcnow()
    end = start + timedelta(hours=1, minutes=30)

    created_session = services.create_study_session(
        StudySessionBase(
            resource_id=resource.id,
            started_at=start,
            ended_at=end,
            notes="Worked through week 1.",
        ),
        session=session,
    )

    assert created_session is not None
    assert created_session.id is not None
    assert created_session.resource_id == resource.id

    all_sessions = services.list_study_sessions(session=session)
    assert len(all_sessions) == 1

    by_resource = services.list_study_sessions(
        session=session, resource_id=resource.id
    )
    assert len(by_resource) == 1
    assert by_resource[0].id == created_session.id

def test_compute_overview_stats(session: Session):
    # 1 backend course + 1 algorithms book
    backend_course = services.create_resource(
        ResourceCreate(
            title="FastAPI Course",
            resource_type="course",
            provider="Udemy",
            total_units=20,
            tags=["backend"],
            target_skills=["fastapi", "rest-api"],
        ),
        session,
    )
    algo_book = services.create_resource(
        ResourceCreate(
            title="Algorithms Book",
            resource_type="book",
            provider="Book",
            total_units=10,
            tags=["algorithms"],
            target_skills=["algorithms"],
        ),
        session,
    )

    # mark backend course as in progress, algorithms book completed
    services.update_resource(
        backend_course.id,
        ResourceUpdate(status=ResourceStatus.in_progress),
        session,
    )
    services.update_resource(
        algo_book.id,
        ResourceUpdate(completed_units=10),
        session,
    )

    # log 2h on backend course, 1h on algorithms
    now = datetime.utcnow()
    services.create_study_session(
        StudySessionBase(
            resource_id=backend_course.id,
            started_at=now,
            ended_at=now + timedelta(hours=2),
            notes="FastAPI + REST basics",
        ),
        session,
    )
    services.create_study_session(
        StudySessionBase(
            resource_id=algo_book.id,
            started_at=now,
            ended_at=now + timedelta(hours=1),
            notes="First chapter of algorithms",
        ),
        session,
    )

    stats = services.compute_overview_stats(session)

    assert stats["total_resources"] == 2
    assert stats["completed_resources"] == 1
    assert stats["in_progress_resources"] == 1
    assert stats["total_study_hours"] >= 3.0

    # type breakdown
    by_type = stats["by_type"]
    assert by_type["course"]["count"] == 1
    assert by_type["book"]["count"] == 1

    # skill breakdown
    by_skill = stats["by_skill"]
    assert "fastapi" in by_skill
    assert "algorithms" in by_skill
    assert by_skill["algorithms"]["completed"] == 1
