from fastapi.testclient import TestClient

from fob_api.models import database as db
from fob_api.tests.conftest import DEFAULT_PASSWORD

def test_get_token(client: TestClient, client_admin: db.User):
    username = client_admin.username
    correct_password = DEFAULT_PASSWORD
    response = client.post(
        "/token",
        data={"username": username, "password": correct_password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "token_type" in data
    assert data["token_type"] == "bearer"

def client_fixture(session: Session):
    def get_session_override():
        return session
    response = client.post(
        "/test/", json={"name": "Deadpond", "secret_name": "Dive Wilson"}
    )
    data = response.json()

    #assert response.status_code == 200
    #assert data["name"] == "Deadpond"