from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, create_engine, Session

from app.main import app
from app.database import get_session
from app import models  # noqa: F401  # ensure tables are registered


@pytest.fixture(scope="session")
def engine():
    """Test database engine (in-memory SQLite)."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture(scope="function")
def db_session(engine) -> Iterator[Session]:
    """Provide a new DB session for each test."""
    with Session(engine) as session:
        yield session


@pytest.fixture(scope="session")
def client(engine) -> TestClient:
    """FastAPI TestClient using the test DB via dependency override."""

    def _get_session_override() -> Iterator[Session]:
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = _get_session_override
    return TestClient(app)
