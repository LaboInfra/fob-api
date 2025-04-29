
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from fob_api import get_session
from fob_api.main import app

@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def test_create(client: TestClient):
    response = client.post(
        "/test/", json={"name": "Deadpond", "secret_name": "Dive Wilson"}
    )
    data = response.json()

    #assert response.status_code == 200
    #assert data["name"] == "Deadpond"
    #assert data["secret_name"] == "Dive Wilson"
    #assert data["age"] is None
    #assert data["id"] is not None