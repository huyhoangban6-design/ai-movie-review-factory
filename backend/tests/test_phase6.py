from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient


def _register(client: TestClient, email: str = "phase6@example.com") -> dict:
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": email, "display_name": "Phase Six", "password": "phase6-pass-123"},
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


def _promote_pipeline_to_qa(client: TestClient, headers: dict, script_id: int) -> None:
    _ = client.post("/api/v1/video/render", json={"script_id": script_id}, headers=headers)
    _ = client.post("/api/v1/video/subtitle", json={"script_id": script_id}, headers=headers)
    resp = client.post("/api/v1/video/qa", json={"script_id": script_id}, headers=headers)
    assert resp.status_code == 201, resp.text
    assert resp.json()["final_passed"] is True


def _upload(client: TestClient, headers: dict, script_id: int, **extra) -> dict:
    resp = client.post("/api/v1/youtube/upload", json={"script_id": script_id, **extra}, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_upload_requires_final_qa(client: TestClient) -> None:
    headers = _register(client)
    # Pipeline đủ render + subtitle nhưng chưa chạy Final QA → upload phải bị 422.
    _, script = _full_pipeline(client, headers, "The Father")
    _ = client.post("/api/v1/video/render", json={"script_id": script["script_id"]}, headers=headers)
    _ = client.post("/api/v1/video/subtitle", json={"script_id": script["script_id"]}, headers=headers)

    resp = client.post("/api/v1/youtube/upload", json={"script_id": script["script_id"]}, headers=headers)
    assert resp.status_code == 422


def test_upload_private_success(client: TestClient) -> None:
    headers = _register(client)
    _, script = _full_pipeline(client, headers, "Dune")
    _promote_pipeline_to_qa(client, headers, script["script_id"])

    body = _upload(client, headers, script["script_id"], title="Review Dune (2021)", tags=["review", "phim"])
    assert body["publication_id"] > 0
    assert body["script_id"] == script["script_id"]
    assert body["job_id"] > 0
    upload = body["upload"]
    assert upload["youtube_video_id"]
    assert upload["privacy_status"] == "private"
    assert upload["video_url"]
    assert upload["upload_metadata"]["simulated"] is True
    assert upload["upload_metadata"]["title"] == "Review Dune (2021)"

    detail = client.get(f"/api/v1/scripts/{script['script_id']}", headers=headers)
    assert detail.status_code == 200
    assert len(detail.json()["publications"]) == 1
    pub = detail.json()["publications"][0]
    assert pub["status"] == "private_uploaded"
    assert pub["title"] == "Review Dune (2021)"
    assert pub["tags"] == ["review", "phim"]
    assert pub["approved"] is False
    assert detail.json()["pipeline_status"] == "upload"


def test_upload_respects_custom_title_default(client: TestClient) -> None:
    headers = _register(client)
    _, script = _full_pipeline(client, headers, "Sparkle Movie")
    _promote_pipeline_to_qa(client, headers, script["script_id"])

    body = _upload(client, headers, script["script_id"])
    detail = client.get(f"/api/v1/scripts/{script['script_id']}", headers=headers)
    pub = detail.json()["publications"][0]
    assert body["upload"]["upload_metadata"]["title"] == pub["title"]
    assert pub["title"].startswith("Review Sparkle Movie")


def test_approve_marks_ready_to_publish(client: TestClient) -> None:
    headers = _register(client)
    _, script = _full_pipeline(client, headers, "Oppenheimer")
    _promote_pipeline_to_qa(client, headers, script["script_id"])
    uploaded = _upload(client, headers, script["script_id"])

    resp = client.post(
        "/api/v1/youtube/approve",
        json={"publication_id": uploaded["publication_id"], "approved": True, "note": "OK bản nháp cuối"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "ready_to_publish"
    assert resp.json()["approved"] is True


def test_approve_reject_marks_rejected(client: TestClient) -> None:
    headers = _register(client)
    _, script = _full_pipeline(client, headers, "Joker")
    _promote_pipeline_to_qa(client, headers, script["script_id"])
    uploaded = _upload(client, headers, script["script_id"])

    resp = client.post(
        "/api/v1/youtube/approve",
        json={"publication_id": uploaded["publication_id"], "approved": False, "note": "Thiếu giấy phép"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "rejected"
    assert resp.json()["approved"] is False

    # Publish sau khi bị từ chối phải 422.
    pub = client.post(
        "/api/v1/youtube/publish",
        json={"publication_id": uploaded["publication_id"]},
        headers=headers,
    )
    assert pub.status_code == 422


def test_publish_requires_approval(client: TestClient) -> None:
    headers = _register(client)
    _, script = _full_pipeline(client, headers, "Tenet")
    _promote_pipeline_to_qa(client, headers, script["script_id"])
    uploaded = _upload(client, headers, script["script_id"])

    resp = client.post(
        "/api/v1/youtube/publish",
        json={"publication_id": uploaded["publication_id"], "privacy": "public"},
        headers=headers,
    )
    assert resp.status_code == 422, resp.text


def test_publish_after_approval_public(client: TestClient) -> None:
    headers = _register(client)
    _, script = _full_pipeline(client, headers, "Fargo")
    _promote_pipeline_to_qa(client, headers, script["script_id"])
    uploaded = _upload(client, headers, script["script_id"])

    approve = client.post(
        "/api/v1/youtube/approve",
        json={"publication_id": uploaded["publication_id"], "approved": True},
        headers=headers,
    )
    assert approve.status_code == 200

    resp = client.post(
        "/api/v1/youtube/publish",
        json={"publication_id": uploaded["publication_id"], "privacy": "public"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["publish"]["status"] == "published"
    assert body["publish"]["privacy_status"] == "public"
    assert body["publish"]["video_url"]

    pub = client.get(f"/api/v1/youtube/publications/{uploaded['publication_id']}", headers=headers)
    assert pub.status_code == 200
    assert pub.json()["status"] == "published"
    assert pub.json()["approved"] is True
    assert pub.json()["privacy_status"] == "public"

    detail = client.get(f"/api/v1/scripts/{script['script_id']}", headers=headers)
    assert detail.json()["pipeline_status"] == "published"


def test_publish_scheduled_in_future(client: TestClient) -> None:
    headers = _register(client)
    _, script = _full_pipeline(client, headers, "Arrival")
    _promote_pipeline_to_qa(client, headers, script["script_id"])
    uploaded = _upload(client, headers, script["script_id"])

    approve = client.post(
        "/api/v1/youtube/approve",
        json={"publication_id": uploaded["publication_id"], "approved": True},
        headers=headers,
    )
    assert approve.status_code == 200

    future = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    resp = client.post(
        "/api/v1/youtube/publish",
        json={"publication_id": uploaded["publication_id"], "privacy": "public", "publish_at": future},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["publish"]["status"] == "scheduled"

    pub = client.get(f"/api/v1/youtube/publications/{uploaded['publication_id']}", headers=headers)
    assert pub.json()["status"] == "scheduled"
    assert pub.json()["publish_at"] is not None


def test_publication_ownership_isolation(client: TestClient) -> None:
    headers_a = _register(client, "owner6@example.com")
    _, script = _full_pipeline(client, headers_a, "Nope")
    _promote_pipeline_to_qa(client, headers_a, script["script_id"])
    uploaded = _upload(client, headers_a, script["script_id"])

    headers_b = _register(client, "intruder6@example.com")
    assert (
        client.post(
            "/api/v1/youtube/approve",
            json={"publication_id": uploaded["publication_id"], "approved": True},
            headers=headers_b,
        ).status_code
        == 404
    )
    assert (
        client.post(
            "/api/v1/youtube/publish",
            json={"publication_id": uploaded["publication_id"]},
            headers=headers_b,
        ).status_code
        == 404
    )
    assert (
        client.get(f"/api/v1/youtube/publications/{uploaded['publication_id']}", headers=headers_b).status_code
        == 404
    )


def test_upload_creates_upload_job(client: TestClient) -> None:
    headers = _register(client)
    _, script = _full_pipeline(client, headers, "Brutalist")
    _promote_pipeline_to_qa(client, headers, script["script_id"])
    uploaded = _upload(client, headers, script["script_id"])

    job = client.get(f"/api/v1/jobs/{uploaded['job_id']}", headers=headers)
    assert job.status_code == 200, job.text
    assert job.json()["job_type"] == "upload"
    assert job.json()["status"] == "succeeded"
