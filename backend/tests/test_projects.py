from fastapi.testclient import TestClient


def _create_project(client: TestClient, headers: dict, title: str = "My Movie Review") -> dict:
    resp = client.post(
        "/api/v1/projects",
        json={"title": title, "description": "First project", "max_cost_per_video": 15.5},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_create_project(client: TestClient, auth_headers: dict) -> None:
    data = _create_project(client, auth_headers)
    assert data["title"] == "My Movie Review"
    assert data["status"] == "draft"
    assert data["max_cost_per_video"] == 15.5
    assert data["jobs"] == []


def test_create_project_requires_auth(client: TestClient) -> None:
    resp = client.post("/api/v1/projects", json={"title": "Nope"})
    assert resp.status_code == 401


def test_create_project_validates_title(client: TestClient, auth_headers: dict) -> None:
    resp = client.post("/api/v1/projects", json={"title": "  "}, headers=auth_headers)
    assert resp.status_code == 422


def test_list_and_get_project(client: TestClient, auth_headers: dict) -> None:
    created = _create_project(client, auth_headers, title="List Me")
    listing = client.get("/api/v1/projects", headers=auth_headers)
    assert listing.status_code == 200
    assert any(p["title"] == "List Me" for p in listing.json())

    detail = client.get(f"/api/v1/projects/{created['id']}", headers=auth_headers)
    assert detail.status_code == 200
    assert detail.json()["id"] == created["id"]
    assert detail.json()["jobs"] == []


def test_project_not_found_for_other_user(client: TestClient, auth_headers: dict) -> None:
    other = _create_project(client, auth_headers, title="Other")
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": "second@example.com", "display_name": "Second", "password": "another-pass-123"},
    )
    other_headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}
    resp2 = client.get(f"/api/v1/projects/{other['id']}", headers=other_headers)
    assert resp2.status_code == 404


def test_idempotent_project_creation(client: TestClient, auth_headers: dict) -> None:
    headers = {**auth_headers, "Idempotency-Key": "create-proj-abc-123"}
    first = _create_project(client, headers, title="Idem")
    second = client.post(
        "/api/v1/projects",
        json={"title": "Idem", "description": "First project", "max_cost_per_video": 15.5},
        headers=headers,
    )
    assert second.status_code == 201
    assert second.json()["id"] == first["id"]
    assert second.json()["jobs"] == []


def test_get_job_and_jobs_list(client: TestClient, auth_headers: dict) -> None:
    project = _create_project(client, auth_headers, title="Jobs")
    via_detail = client.get(f"/api/v1/projects/{project['id']}/jobs", headers=auth_headers)
    assert via_detail.status_code == 200
    assert via_detail.json() == []