from fastapi.testclient import TestClient


def _register(client: TestClient, email: str = "phase5@example.com") -> dict:
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": email, "display_name": "Phase Five", "password": "phase5-pass-123"},
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


def _assets(client: TestClient, headers: dict, script_id: int) -> dict:
    resp = client.post("/api/v1/assets/generate", json={"script_id": script_id}, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _copyright(client: TestClient, headers: dict, script_id: int) -> dict:
    resp = client.post("/api/v1/copyright/evaluate", json={"script_id": script_id}, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _full_pipeline(client: TestClient, headers: dict, title: str) -> tuple[dict, dict]:
    movie = _research(client, headers, title)
    script = _script(client, headers, movie["movie_id"])
    _voice(client, headers, script["script_id"])
    _timeline(client, headers, script["script_id"])
    _visual_plan(client, headers, script["script_id"])
    _assets(client, headers, script["script_id"])
    _copyright(client, headers, script["script_id"])
    return movie, script


def _promote_pipeline_to_subtitle(client: TestClient, headers: dict, script_id: int) -> None:
    _ = client.post("/api/v1/video/render", json={"script_id": script_id}, headers=headers)
    _ = client.post("/api/v1/video/subtitle", json={"script_id": script_id}, headers=headers)


def test_render_requires_voice_and_assets(client: TestClient) -> None:
    headers = _register(client)
    movie = _research(client, headers, "Parasite")
    script = _script(client, headers, movie["movie_id"])
    resp = client.post("/api/v1/video/render", json={"script_id": script["script_id"]}, headers=headers)
    assert resp.status_code == 422


def test_render_success_after_pipeline(client: TestClient) -> None:
    headers = _register(client)
    _, script = _full_pipeline(client, headers, "Dune")

    resp = client.post("/api/v1/video/render", json={"script_id": script["script_id"]}, headers=headers)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["render_id"] > 0
    render = body["render"]
    assert render["video_url"]
    assert render["duration_s"] > 0
    assert render["resolution"] == "1280x720"
    assert render["fps"] == 30
    assert render["file_size_bytes"] > 0
    assert render["render_ok"] is True


def test_render_gate_blocks_blocked_asset(client: TestClient, monkeypatch) -> None:
    from app.api import copyright as copyright_api
    from app.services.providers import OfflineCopyrightProvider

    class BlockedProvider(OfflineCopyrightProvider):
        def evaluate(self, asset):  # noqa: ANN001
            out = super().evaluate(asset)
            out.decision = "block"
            out.risk_level = "high"
            out.human_review_required = True
            return out

    # copyright endpoint gọi provider trong thời gian chạy, patch đúng chỗ nó import.
    monkeypatch.setattr(copyright_api, "get_copyright_provider", lambda: BlockedProvider())

    headers = _register(client)
    movie = _research(client, headers, "Joker")
    script = _script(client, headers, movie["movie_id"])
    _voice(client, headers, script["script_id"])
    _timeline(client, headers, script["script_id"])
    _visual_plan(client, headers, script["script_id"])
    _assets(client, headers, script["script_id"])
    _copyright(client, headers, script["script_id"])  # giờ mọi asset bị block

    resp = client.post("/api/v1/video/render", json={"script_id": script["script_id"]}, headers=headers)
    assert resp.status_code == 422


def test_subtitle_requires_timeline(client: TestClient) -> None:
    headers = _register(client)
    movie = _research(client, headers, "Oppenheimer")
    script = _script(client, headers, movie["movie_id"])
    resp = client.post("/api/v1/video/subtitle", json={"script_id": script["script_id"]}, headers=headers)
    assert resp.status_code == 422


def test_subtitle_generates_srt(client: TestClient) -> None:
    headers = _register(client)
    movie = _research(client, headers, "Arrival")
    script = _script(client, headers, movie["movie_id"])
    _voice(client, headers, script["script_id"])
    _timeline(client, headers, script["script_id"])

    resp = client.post("/api/v1/video/subtitle", json={"script_id": script["script_id"]}, headers=headers)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["subtitle_id"] > 0
    sub = body["subtitle"]
    assert sub["format"] == "srt"
    assert sub["cue_count"] == 9
    assert "--> " in sub["content"]
    assert sub["content"].startswith("1\n")


def test_subtitle_regenerate_replaces(client: TestClient) -> None:
    headers = _register(client)
    movie = _research(client, headers, "Nope")
    script = _script(client, headers, movie["movie_id"])
    _voice(client, headers, script["script_id"])
    _timeline(client, headers, script["script_id"])

    first = client.post("/api/v1/video/subtitle", json={"script_id": script["script_id"]}, headers=headers)
    assert first.status_code == 201, first.text

    second = client.post(
        "/api/v1/video/subtitle", json={"script_id": script["script_id"], "format": "vtt"}, headers=headers
    )
    assert second.status_code == 201, second.text
    assert second.json()["subtitle"]["format"] == "vtt"

    detail = client.get(f"/api/v1/scripts/{script['script_id']}", headers=headers)
    assert detail.status_code == 200
    subtitles = detail.json()["subtitles"]
    assert len(subtitles) == 1, "subtitle cũ phải được thay thế, không nhân bản"
    assert subtitles[0]["format"] == "vtt"


def test_qa_requires_render_and_subtitle(client: TestClient) -> None:
    headers = _register(client)
    movie = _research(client, headers, "Brutalist")
    script = _script(client, headers, movie["movie_id"])
    resp = client.post("/api/v1/video/qa", json={"script_id": script["script_id"]}, headers=headers)
    assert resp.status_code == 422


def test_qa_full_pipeline_passes(client: TestClient) -> None:
    headers = _register(client)
    _, script = _full_pipeline(client, headers, "Tenet")
    _promote_pipeline_to_subtitle(client, headers, script["script_id"])

    resp = client.post("/api/v1/video/qa", json={"script_id": script["script_id"]}, headers=headers)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["final_passed"] is True
    gates = {r["gate"]: r["passed"] for r in body["reports"]}
    for g in ("fact", "script", "voice", "visual", "subtitle", "copyright", "technical", "final"):
        assert g in gates, f"missing gate {g}"
    assert gates["final"] is True


def test_qa_blocks_when_asset_blocked(client: TestClient, monkeypatch) -> None:
    from app.api import copyright as copyright_api
    from app.services.providers import OfflineCopyrightProvider

    # Pipeline render hoàn tất với copyright approved trước.
    headers = _register(client)
    movie = _research(client, headers, "Tár")
    script = _script(client, headers, movie["movie_id"])
    _voice(client, headers, script["script_id"])
    _timeline(client, headers, script["script_id"])
    _visual_plan(client, headers, script["script_id"])
    _assets(client, headers, script["script_id"])
    _copyright(client, headers, script["script_id"])
    _promote_pipeline_to_subtitle(client, headers, script["script_id"])

    # Sau đó đánh giá lại bản quyền trong chế độ chặn → QA phải fail gate copyright.
    class BlockedProvider(OfflineCopyrightProvider):
        def evaluate(self, asset):  # noqa: ANN001
            out = super().evaluate(asset)
            out.decision = "block"
            out.risk_level = "high"
            return out

    monkeypatch.setattr(copyright_api, "get_copyright_provider", lambda: BlockedProvider())
    _copyright(client, headers, script["script_id"])

    resp = client.post("/api/v1/video/qa", json={"script_id": script["script_id"]}, headers=headers)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    gates = {r["gate"]: r["passed"] for r in body["reports"]}
    assert gates["copyright"] is False
    assert gates["final"] is False
    assert body["final_passed"] is False


def test_script_detail_includes_render_subtitle_qa(client: TestClient) -> None:
    headers = _register(client)
    _, script = _full_pipeline(client, headers, "Fargo")
    _promote_pipeline_to_subtitle(client, headers, script["script_id"])
    _ = client.post("/api/v1/video/qa", json={"script_id": script["script_id"]}, headers=headers)

    detail = client.get(f"/api/v1/scripts/{script['script_id']}", headers=headers)
    assert detail.status_code == 200, detail.text
    body = detail.json()
    assert len(body["renders"]) == 1
    assert len(body["subtitles"]) == 1
    assert len(body["qa_reports"]) >= 6
    assert any(r["gate"] == "final" for r in body["qa_reports"])
    assert body["pipeline_status"] == "qa"