import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy.pool import StaticPool

from app.routers import graph as graph_router
from app.models.auth import Agent, Role
from app.models.graph import VerificationLevel
from app.services.auth import hash_api_key


@pytest.fixture(scope="session")
def engine():
    # In-memory SQLite shared across connections
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture()
def session(engine):
    with Session(engine) as session:
        yield session


@pytest.fixture()
def test_role():
    return Role(name="tester", highest_verification_allowed=VerificationLevel.VERIFIED)


@pytest.fixture()
def test_agent(test_role):
    # Note: we don't rely on this being persisted unless the fixture user adds it to a session.
    return Agent(id=1, name="test-agent", api_key_hash="dummy", role=test_role)


@pytest.fixture()
def app(session, test_agent):
    """FastAPI app with dependency overrides (no real auth, no real DB engines)."""
    app = FastAPI()
    app.include_router(graph_router.router)

    def _get_session_override():
        yield session

    app.dependency_overrides[graph_router.get_session] = _get_session_override
    app.dependency_overrides[graph_router.get_current_agent] = lambda: test_agent

    return app


@pytest.fixture()
def client(app):
    return TestClient(app)


@pytest.fixture()
def app_real_auth(session):
    """FastAPI app that uses real `get_current_agent` against the in-memory SQL DB."""
    app = FastAPI()
    app.include_router(graph_router.router)

    def _get_session_override():
        yield session

    app.dependency_overrides[graph_router.get_session] = _get_session_override
    return app


@pytest.fixture()
def client_real_auth(app_real_auth):
    return TestClient(app_real_auth)


@pytest.fixture()
def seeded_agent_in_db(session):
    """Persist an Agent+Role with a known API key into the SQL DB."""
    api_key = "secret-api-key"
    role = Role(name="seeded-role", highest_verification_allowed=VerificationLevel.VERIFIED)
    session.add(role)
    session.commit()
    session.refresh(role)

    agent = Agent(name="seeded-agent", api_key_hash=hash_api_key(api_key), role_id=role.id)
    session.add(agent)
    session.commit()
    session.refresh(agent)

    return agent, api_key
