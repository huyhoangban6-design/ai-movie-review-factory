from fastapi.testclient import TestClient


def _register(client: TestClient) -> dict:
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": "phase2@example.com", "display_name": "Phase Two", "password": "phase2-pass-123"},
    )
    assert resp.status_code == 201, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _research(client: TestClient, headers: dict, title: str = "Inception") -> dict:
    resp = client.post("/api/v1/movies/research", json={"title": title, "year": 2010}, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_research_creates_movie_and_job(client: TestClient) -> None:
    headers = _register(client)
    result = _research(client, headers, "Parasite")
    assert result["title"] == "Parasite"
    assert result["year"] == 2010
    assert result["output"]["genres"] == []
    assert result["movie_id"] > 0

    detail = client.get(f"/api/v1/movies/{result['movie_id']}", headers=headers)
    assert detail.status_code == 200
    body = detail.json()
    assert body["title"] == "Parasite"
    assert body["status"] == "verified"
    assert len(body["sources"]) == 1
    assert body["sources"][0]["source_type"] == "offline"
    assert body["summaries"] == ["(offline research) Dữ liệu mẫu do provider offline tạo để test pipeline."]


def test_opportunity_score_is_weighted(client: TestClient) -> None:
    headers = _register(client)
    movie = _research(client, headers, "Inception")
    resp = client.post(
        "/api/v1/opportunities/score", json={"movie_id": movie["movie_id"]}, headers=headers
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["opportunity_id"] > 0
    score = body["score"]
    assert 0 <= score["overall"] <= 100
    assert score["confidence"] == 0.5
    expected = (
        score["demand"] * 0.25
        + score["trend"] * 0.20
        + score["audience_fit"] * 0.15
        + score["evergreen"] * 0.15
        + score["competition"] * 0.15
        + score["difficulty"] * 0.10
    )
    assert abs(score["overall"] - round(expected, 1)) < 0.01


def test_angles_cp1_generated(client: TestClient) -> None:
    headers = _register(client)
    movie = _research(client, headers, "Dune")
    resp = client.post(
        "/api/v1/content/angles", json={"movie_id": movie["movie_id"]}, headers=headers
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert len(body["angles"]) >= 5
    angle = body["angles"][0]
    assert angle["title"]
    assert angle["hook"]
    assert angle["rationale"]


def test_research_requires_auth(client: TestClient) -> None:
    resp = client.post("/api/v1/movies/research", json={"title": "X", "year": 2024})
    assert resp.status_code == 401


def test_score_unknown_movie_404(client: TestClient) -> None:
    headers = _register(client)
    resp = client.post("/api/v1/opportunities/score", json={"movie_id": 9999}, headers=headers)
    assert resp.status_code == 404


def test_angles_unknown_movie_404(client: TestClient) -> None:
    headers = _register(client)
    resp = client.post("/api/v1/content/angles", json={"movie_id": 9999}, headers=headers)
    assert resp.status_code == 404


def test_movie_scope_isolated_between_users(client: TestClient) -> None:
    owner = _register(client)
    movie = _research(client, owner, "Tenet")
    other_resp = client.post(
        "/api/v1/auth/register",
        json={"email": "other-phase2@example.com", "display_name": "Other", "password": "other-pass-123"},
    )
    other_headers = {"Authorization": f"Bearer {other_resp.json()['access_token']}"}
    resp = client.get(f"/api/v1/movies/{movie['movie_id']}", headers=other_headers)
    assert resp.status_code == 404