import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from fob_api import get_session
from fob_api.main import app, engine
from fob_api.auth import hash_password
from fob_api.managers import TokenManager
from fob_api.models import database as db
from random import randint
from string import ascii_letters

def random_string(length: int) -> str:
    return "".join(
        [ascii_letters[randint(0, len(ascii_letters) - 1)] for _ in range(length)]
    )

@pytest.fixture(name="session", scope="session")
def session_fixture():
    #engine = create_engine(
    #    "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    #)

    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

@pytest.fixture(name="client", scope="session")
def client_fixture(session: Session):
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()

@pytest.fixture(name="random_run_suffix", scope="session")
def random_run_suffix():
    """
    Fixture to generate a random suffix for test data.
    """
    random_suffix = random_string(5)
    yield random_suffix

@pytest.fixture(name="random_run_password", scope="session")
def random_run_password():
    """
    Fixture to generate a random password for test data.
    """
    random_password = random_string(12)
    yield random_password

@pytest.fixture(name="client_admin", scope="session")
def client_admin_fixture(client: TestClient, session: Session, random_run_suffix: str, random_run_password: str):
    """
    Fixture to create a test client with admin privileges.
    """
    random_username = "test_admin_" + random_run_suffix
    user: db.User = db.User(
        username=random_username,
        email=f"{random_username}@laboinfra.net",
        password=hash_password(random_run_password),
        is_admin=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    yield user
    session.delete(user)
    session.commit()

@pytest.fixture(name="client_user", scope="session")
def client_user_fixture(client: TestClient, session: Session, random_run_suffix: str, random_run_password: str):
    """
    Fixture to create a test client with admin privileges.
    """
    random_username = "test_user_" + random_run_suffix
    user: db.User = db.User(
        username=random_username,
        email=f"{random_username}@laboinfra.net",
        password=hash_password(random_run_password),
        is_admin=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    yield user
    session.delete(user)
    session.commit()

@pytest.fixture(name="admin_token", scope="session")
def admin_token_fixture(session: Session, client_admin: db.User):
    """
    Fixture to create a test client with admin privileges.
    """
    return TokenManager(session).create_token(client_admin)

@pytest.fixture(name="user_token", scope="session")
def user_token_fixture(session: Session, client_user: db.User):
    """
    Fixture to create a test client without admin privileges.
    """
    return TokenManager(session).create_token(client_user)
