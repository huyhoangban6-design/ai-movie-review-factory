from fastapi.testclient import TestClient

from app.services.providers import OfflineVoiceProvider


def _register(client: TestClient, email: str = "phase3@example.com") -> dict:
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": email, "display_name": "Phase Three", "password": "phase3-pass-123"},
    )
    assert resp.status_code == 201, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _research(client: TestClient, headers: dict, title: str = "Inception") -> dict:
    resp = client.post("/api/v1/movies/research", json={"title": title, "year": 2010}, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _angles(client: TestClient, headers: dict, movie_id: int) -> dict:
    resp = client.post("/api/v1/content/angles", json={"movie_id": movie_id}, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _script(client: TestClient, headers: dict, movie_id: int) -> dict:
    resp = client.post("/api/v1/scripts/generate", json={"movie_id": movie_id}, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _voice(client: TestClient, headers: dict, script_id: int) -> dict:
    resp = client.post("/api/v1/voice/generate", json={"script_id": script_id}, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _timeline(client: TestClient, headers: dict, script_id: int, generation_id: int) -> dict:
    resp = client.post(
        "/api/v1/timeline/build",
        json={"script_id": script_id, "generation_id": generation_id},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_script_generation_full_structure(client: TestClient) -> None:
    headers = _register(client)
    movie = _research(client, headers, "Parasite")
    _angles(client, headers, movie["movie_id"])

    resp = client.post("/api/v1/scripts/generate", json={"movie_id": movie["movie_id"]}, headers=headers)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["script_id"] > 0
    assert body["version"] == 1
    sections = [s["section"] for s in body["script"]["segments"]]
    assert sections == [
        "hook",
        "thesis",
        "context",
        "analysis",
        "evidence",
        "character_theme",
        "critique",
        "conclusion",
        "cta",
    ]
    assert all(len(s["text"]) > 8 for s in body["script"]["segments"])
    assert 0 < body["script"]["estimated_duration_s"] < 3600


def test_script_increments_version(client: TestClient) -> None:
    headers = _register(client)
    movie = _research(client, headers, "Dune")
    first = _script(client, headers, movie["movie_id"])
    second = _script(client, headers, movie["movie_id"])
    assert first["version"] == 1
    assert second["version"] == 2


def test_voice_generates_with_default_profile(client: TestClient) -> None:
    headers = _register(client)
    movie = _research(client, headers, "Tenet")
    script = _script(client, headers, movie["movie_id"])

    resp = client.post("/api/v1/voice/generate", json={"script_id": script["script_id"]}, headers=headers)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["generation_id"] > 0
    assert body["voice"]["provider"] == "offline"
    assert body["voice"]["license"]["commercial_use"] == "yes"
    assert body["voice"]["duration_s"] > 0
    assert len(body["voice"]["sentences"]) >= 9
    assert len(body["voice"]["words"]) > 0


def test_voice_requires_script(client: TestClient) -> None:
    headers = _register(client)
    resp = client.post("/api/v1/voice/generate", json={"script_id": 9999}, headers=headers)
    assert resp.status_code == 404


def test_voice_license_gate_blocks_commercial_no(client: TestClient) -> None:
    provider = OfflineVoiceProvider()
    try:
        provider.synthesize(
            "Xin chào",
            provider="offline",
            model="m",
            voice_id="v",
            language="vi",
            speed=1.0,
            commercial_use="no",
            license_url=None,
            cloning_permission=False,
        )
        raise AssertionError("expected license gate to block commercial_use=no")
    except ValueError:
        pass


def test_timeline_requires_voice_first(client: TestClient) -> None:
    headers = _register(client)
    movie = _research(client, headers, "Interstellar")
    script = _script(client, headers, movie["movie_id"])
    resp = client.post("/api/v1/timeline/build", json={"script_id": script["script_id"]}, headers=headers)
    assert resp.status_code == 422


def test_timeline_builds_segments(client: TestClient) -> None:
    headers = _register(client)
    movie = _research(client, headers, "Inception")
    script = _script(client, headers, movie["movie_id"])
    voice = _voice(client, headers, script["script_id"])
    timeline = _timeline(client, headers, script["script_id"], voice["generation_id"])

    segs = timeline["timeline"]["segments"]
    assert len(segs) == 9
    assert segs[0]["position"] == 1
    assert segs[-1]["end_s"] <= timeline["timeline"]["total_duration_s"] + 0.01
    # Timeline tham chiếu đúng generation để Visual Planner (Phase 4) căn theo voice.
    assert timeline["generation_id"] == voice["generation_id"]


def test_script_detail_endpoint(client: TestClient) -> None:
    headers = _register(client)
    movie = _research(client, headers, "Oppenheimer")
    script = _script(client, headers, movie["movie_id"])
    voice = _voice(client, headers, script["script_id"])
    _timeline(client, headers, script["script_id"], voice["generation_id"])

    resp = client.get(f"/api/v1/scripts/{script['script_id']}", headers=headers)
    assert resp.status_code == 200
    detail = resp.json()
    assert detail["status"] == "draft"
    assert len(detail["segments"]) == 9
    assert detail["latest_generation"]["id"] == voice["generation_id"]
    assert detail["timeline"]["total_duration_s"] > 0


def test_movie_detail_includes_scripts(client: TestClient) -> None:
    headers = _register(client)
    movie = _research(client, headers, "Arrival")
    _script(client, headers, movie["movie_id"])

    resp = client.get(f"/api/v1/movies/{movie['movie_id']}", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()["scripts"]) == 1
    assert resp.json()["scripts"][0]["title"]


def test_phase3_ownership_isolated(client: TestClient) -> None:
    owner = _register(client)
    movie = _research(client, owner, "Joker")
    script = _script(client, owner, movie["movie_id"])

    other = _register(client, email="phase3-other@example.com")
    resp = client.get(f"/api/v1/scripts/{script['script_id']}", headers=other)
    assert resp.status_code == 404
    resp = client.post(
        "/api/v1/voice/generate", json={"script_id": script["script_id"]}, headers=other
    )
    assert resp.status_code == 404