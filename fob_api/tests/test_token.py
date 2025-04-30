from fastapi.testclient import TestClient

from fob_api.models import database as db

def test_get_token(client: TestClient, client_admin: db.User, random_run_password: str):
    response = client.post(
        "/token",
        data={"username": client_admin.username, "password": random_run_password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "token_type" in data
    assert data["token_type"] == "bearer"

def test_get_token_invalid(client: TestClient):
    response = client.post(
        "/token",
        data={"username": "invalid_user", "password": "invalid_password"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data
    assert data["detail"] == "Invalid credentials"

def test_refresh_token(client: TestClient, admin_token: str):
    response = client.get(
        "/token/refreshtoken",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "token_type" in data
    assert data["token_type"] == "bearer"
    assert data["access_token"] != admin_token
