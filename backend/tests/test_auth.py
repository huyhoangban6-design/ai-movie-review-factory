from fastapi.testclient import TestClient


def test_health(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_register_login_me(client: TestClient) -> None:
    email = "alice@example.com"
    password = "correct-horse-battery"
    reg = client.post(
        "/api/v1/auth/register",
        json={"email": email, "display_name": "Alice", "password": password},
    )
    assert reg.status_code == 201
    token = reg.json()["access_token"]
    assert reg.json()["token_type"] == "bearer"

    dup = client.post(
        "/api/v1/auth/register",
        json={"email": email, "display_name": "Alice", "password": password},
    )
    assert dup.status_code == 409

    bad_login = client.post("/api/v1/auth/login", data={"username": email, "password": "wrong"})
    assert bad_login.status_code == 401

    login = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    assert login.status_code == 200
    assert login.json()["access_token"]

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == email

    anon = client.get("/api/v1/auth/me")
    assert anon.status_code == 401


def test_register_requires_strong_password(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": "bob@example.com", "display_name": "Bob", "password": "short"},
    )
    assert resp.status_code == 422