from fastapi.testclient import TestClient

from app.services.providers import OfflineCopyrightProvider


def _register(client: TestClient, email: str = "phase4@example.com") -> dict:
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": email, "display_name": "Phase Four", "password": "phase4-pass-123"},
    )
    assert resp.status_code == 201, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _research(client: TestClient, headers: dict, title: str = "Inception") -> dict:
    resp = client.post("/api/v1/movies/research", json={"title": title, "year": 2010}, headers=headers)
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


def _timeline(client: TestClient, headers: dict, script_id: int) -> dict:
    resp = client.post("/api/v1/timeline/build", json={"script_id": script_id}, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _visual_plan(client: TestClient, headers: dict, script_id: int) -> dict:
    resp = client.post("/api/v1/visual/plan", json={"script_id": script_id}, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _generate_assets(client: TestClient, headers: dict, script_id: int) -> dict:
    resp = client.post("/api/v1/assets/generate", json={"script_id": script_id}, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_visual_plan_maps_every_segment(client: TestClient) -> None:
    headers = _register(client)
    movie = _research(client, headers, "Parasite")
    script = _script(client, headers, movie["movie_id"])

    resp = client.post("/api/v1/visual/plan", json={"script_id": script["script_id"]}, headers=headers)
    assert resp.status_code == 201, resp.text
    plan = resp.json()["visual_plan"]
    assert len(plan["segments"]) == 9
    for i, seg in enumerate(plan["segments"]):
        assert seg["segment_index"] == i
        assert seg["purpose"]
        assert seg["asset_types"]
        assert seg["duration_s"] > 0
    assert plan["total_planned_duration_s"] > 0


def test_visual_plan_requires_script(client: TestClient) -> None:
    headers = _register(client)
    resp = client.post("/api/v1/visual/plan", json={"script_id": 9999}, headers=headers)
    assert resp.status_code == 404


def test_assets_generated_from_plan(client: TestClient) -> None:
    headers = _register(client)
    movie = _research(client, headers, "Tenet")
    script = _script(client, headers, movie["movie_id"])
    _visual_plan(client, headers, script["script_id"])

    resp = client.post("/api/v1/assets/generate", json={"script_id": script["script_id"]}, headers=headers)
    assert resp.status_code == 201, resp.text
    result = resp.json()["result"]
    assert result["assets_created"] == 9
    assert len(result["assets"]) == 9
    first = result["assets"][0]
    assert first["asset_type"]
    assert first["commercial_use"] == "yes"
    assert first["license"] == "CC0"
    assert first["file_url"]


def test_assets_require_visual_plan(client: TestClient) -> None:
    headers = _register(client)
    movie = _research(client, headers, "Dune")
    script = _script(client, headers, movie["movie_id"])
    resp = client.post("/api/v1/assets/generate", json={"script_id": script["script_id"]}, headers=headers)
    assert resp.status_code == 422


def test_assets_replaced_not_duplicated(client: TestClient) -> None:
    headers = _register(client)
    movie = _research(client, headers, "Joker")
    script = _script(client, headers, movie["movie_id"])
    _visual_plan(client, headers, script["script_id"])
    _generate_assets(client, headers, script["script_id"])
    _generate_assets(client, headers, script["script_id"])

    detail = client.get(f"/api/v1/scripts/{script['script_id']}", headers=headers)
    assert detail.status_code == 200
    assert len(detail.json()["assets"]) == 9


def test_copyright_evaluate_low_risk_auto_approve(client: TestClient) -> None:
    headers = _register(client)
    movie = _research(client, headers, "Interstellar")
    script = _script(client, headers, movie["movie_id"])
    _visual_plan(client, headers, script["script_id"])
    gen = _generate_assets(client, headers, script["script_id"])

    resp = client.post(
        "/api/v1/copyright/evaluate",
        json={"script_id": script["script_id"]},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()["result"]
    assert len(body["reviews"]) == len(gen["result"]["assets"])
    assert body["human_review_count"] == 0
    assert body["blocked_count"] == 0
    assert all(r["decision"] == "approved" for r in body["reviews"])
    assert all(r["risk_level"] == "low" for r in body["reviews"])


def test_3sec_rule_sets_human_review_warning(client: TestClient) -> None:
    provider = OfflineCopyrightProvider()
    class ClipAsset:
        id = 42
        source = "film_clip"
        commercial_use = "yes"
        duration_s = 4.2
        license = "fan_video_fair_use"
        transformations = ["cropped", "annotated"]

    out = provider.evaluate(ClipAsset())
    assert out.duration_warning is True
    assert out.human_review_required is True
    assert out.risk_level in ("medium", "high")
    assert any("3-second rule" in n for n in out.policy_notes)


def test_copyright_commercial_no_blocks(client: TestClient) -> None:
    provider = OfflineCopyrightProvider()
    class NoLicenseAsset:
        id = 7
        source = "bootleg"
        commercial_use = "no"
        duration_s = 1.0
        license = None
        transformations = None

    out = provider.evaluate(NoLicenseAsset())
    assert out.decision == "block"
    assert out.risk_level == "high"


def test_copyright_requires_assets(client: TestClient) -> None:
    headers = _register(client)
    movie = _research(client, headers, "Oppenheimer")
    script = _script(client, headers, movie["movie_id"])
    _visual_plan(client, headers, script["script_id"])
    resp = client.post(
        "/api/v1/copyright/evaluate",
        json={"script_id": script["script_id"]},
        headers=headers,
    )
    assert resp.status_code == 422


def test_full_phase4_pipeline_in_script_detail(client: TestClient) -> None:
    headers = _register(client)
    movie = _research(client, headers, "Arrival")
    script = _script(client, headers, movie["movie_id"])
    _voice(client, headers, script["script_id"])
    _timeline(client, headers, script["script_id"])
    _visual_plan(client, headers, script["script_id"])
    _generate_assets(client, headers, script["script_id"])
    _ = client.post(
        "/api/v1/copyright/evaluate",
        json={"script_id": script["script_id"]},
        headers=headers,
    )

    detail = client.get(f"/api/v1/scripts/{script['script_id']}", headers=headers)
    assert detail.status_code == 200
    body = detail.json()
    assert body["pipeline_status"] == "copyright"
    assert body["visual_plan"]["segments"]
    assert len(body["assets"]) == 9
    assert len(body["copyright_reviews"]) == 9
    assert body["timeline"]["segments"]
    assert body["latest_generation"]["id"] > 0


def test_phase4_ownership_isolated(client: TestClient) -> None:
    owner = _register(client)
    movie = _research(client, owner, "Gravity")
    script = _script(client, owner, movie["movie_id"])
    _visual_plan(client, owner, script["script_id"])

    other = _register(client, email="phase4-other@example.com")
    resp = client.post("/api/v1/visual/plan", json={"script_id": script["script_id"]}, headers=other)
    assert resp.status_code == 404