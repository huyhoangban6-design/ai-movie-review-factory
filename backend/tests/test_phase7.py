from fastapi.testclient import TestClient

# Reuse pipeline helpers đã test kỹ ở phase 6 để đưa 1 video đến published.
from tests.test_phase6 import (
    _full_pipeline,
    _promote_pipeline_to_qa,
    _register as _register_phase6,
    _upload,
)


def _register(client: TestClient, email: str = "phase7@example.com") -> dict:
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": email, "display_name": "Phase Seven", "password": "phase7-pass-123"},
    )
    assert resp.status_code == 201, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _publish(client: TestClient, headers: dict, title: str) -> tuple[dict, dict]:
    _, script = _full_pipeline(client, headers, title)
    _promote_pipeline_to_qa(client, headers, script["script_id"])
    uploaded = _upload(client, headers, script["script_id"])
    approve = client.post(
        "/api/v1/youtube/approve",
        json={"publication_id": uploaded["publication_id"], "approved": True},
        headers=headers,
    )
    assert approve.status_code == 200, approve.text
    publish = client.post(
        "/api/v1/youtube/publish",
        json={"publication_id": uploaded["publication_id"], "privacy": "public"},
        headers=headers,
    )
    assert publish.status_code == 201, publish.text
    return uploaded, script


def test_refresh_stores_metrics_and_job(client: TestClient) -> None:
    headers = _register(client)
    uploaded, _ = _publish(client, headers, "Eternal Sunshine")

    resp = client.post(f"/api/v1/analytics/video/{uploaded['publication_id']}/refresh", headers=headers)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["job_id"] > 0
    assert body["publication_id"] == uploaded["publication_id"]
    assert body["snapshot_id"] > 0

    m = body["metrics"]
    assert m["video_id"] == uploaded["upload"]["youtube_video_id"]
    assert m["views"] > 0
    assert m["impressions"] > 0 and m["clicks"] > 0
    assert m["ctr_pct"] == round(m["clicks"] / m["impressions"] * 100, 2)
    assert m["likes"] > 0 and m["comments"] > 0
    assert m["watch_time_hours"] > 0
    assert m["avg_view_duration_s"] > 0
    assert 0 < m["retention_avg_pct"] <= 100
    assert len(m["retention_curve"]) == 12
    assert sum(m["traffic_sources"].values()) > 99
    assert m["revenue_usd"] >= 0

    job = client.get(f"/api/v1/jobs/{body['job_id']}", headers=headers)
    assert job.status_code == 200
    assert job.json()["job_type"] == "analytics"
    assert job.json()["status"] == "succeeded"

    history = client.get(
        f"/api/v1/analytics/video/{uploaded['publication_id']}/history", headers=headers
    )
    assert history.status_code == 200
    assert len(history.json()["snapshots"]) == 1


def test_metrics_are_deterministic_and_replace_latest(client: TestClient) -> None:
    headers = _register(client)
    uploaded, _ = _publish(client, headers, "Magnolia")

    first = client.post(
        f"/api/v1/analytics/video/{uploaded['publication_id']}/refresh", headers=headers
    ).json()
    second = client.post(
        f"/api/v1/analytics/video/{uploaded['publication_id']}/refresh", headers=headers
    ).json()
    assert first["metrics"]["views"] == second["metrics"]["views"]
    assert first["metrics"]["ctr_pct"] == second["metrics"]["ctr_pct"]

    history = client.get(
        f"/api/v1/analytics/video/{uploaded['publication_id']}/history", headers=headers
    ).json()
    assert len(history["snapshots"]) == 2
    assert history["snapshots"][0]["id"] > history["snapshots"][1]["id"]


def test_get_video_metrics_hits_stored_then_derived(client: TestClient) -> None:
    headers = _register(client)
    uploaded, _ = _publish(client, headers, "Boogie Nights")

    before = client.get(f"/api/v1/analytics/video/{uploaded['publication_id']}", headers=headers)
    assert before.status_code == 200
    assert before.json()["source"] == "derived"
    assert before.json()["metrics"]["views"] > 0

    _ = client.post(f"/api/v1/analytics/video/{uploaded['publication_id']}/refresh", headers=headers)
    after = client.get(f"/api/v1/analytics/video/{uploaded['publication_id']}", headers=headers)
    assert after.status_code == 200
    assert after.json()["source"] == "stored"
    assert after.json()["metrics"]["views"] == before.json()["metrics"]["views"]


def test_refresh_rejected_publication_422(client: TestClient) -> None:
    headers = _register(client)
    _, script = _full_pipeline(client, headers, "Hard Eight")
    _promote_pipeline_to_qa(client, headers, script["script_id"])
    uploaded = _upload(client, headers, script["script_id"])
    resp = client.post(
        "/api/v1/youtube/approve",
        json={"publication_id": uploaded["publication_id"], "approved": False},
        headers=headers,
    )
    assert resp.status_code == 200

    refresh = client.post(
        f"/api/v1/analytics/video/{uploaded['publication_id']}/refresh", headers=headers
    )
    assert refresh.status_code == 422


def test_analytics_ownership_isolation(client: TestClient) -> None:
    owner = _register(client, "owner7@example.com")
    uploaded, _ = _publish(client, owner, "There Will Be Blood")
    intruder = _register(client, "intruder7@example.com")

    assert (
        client.get(f"/api/v1/analytics/video/{uploaded['publication_id']}", headers=intruder).status_code
        == 404
    )
    assert (
        client.post(
            f"/api/v1/analytics/video/{uploaded['publication_id']}/refresh", headers=intruder
        ).status_code
        == 404
    )


def test_competitor_research_and_list(client: TestClient) -> None:
    headers = _register(client)
    movie = client.post(
        "/api/v1/movies/research", json={"title": "No Country", "year": 2007}, headers=headers
    ).json()

    resp = client.post(
        "/api/v1/analytics/competitors/research", json={"movie_id": movie["movie_id"]}, headers=headers
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["job_id"] > 0
    assert len(resp.json()["competitors"]) >= 3

    listing = client.get(
        f"/api/v1/analytics/competitors?movie_id={movie['movie_id']}", headers=headers
    )
    assert listing.status_code == 200
    comps = listing.json()["competitors"]
    assert len(comps) >= 3
    assert all(c["channel"] for c in comps)
    assert all(len(c["videos"]) >= 1 for c in comps)
    assert comps[0]["videos"][0]["view_count"] > 0

    # Re-run replace (không nhân đôi)
    second = client.post(
        "/api/v1/analytics/competitors/research", json={"movie_id": movie["movie_id"]}, headers=headers
    )
    assert second.status_code == 201
    listing2 = client.get(
        f"/api/v1/analytics/competitors?movie_id={movie['movie_id']}", headers=headers
    ).json()
    assert len(listing2["competitors"]) == len(comps)


def test_competitor_research_requires_owner_movie(client: TestClient) -> None:
    owner = _register(client, "owner7b@example.com")
    movie = client.post(
        "/api/v1/movies/research", json={"title": "Killer Joe", "year": 2011}, headers=owner
    ).json()
    intruder = _register(client, "intruder7b@example.com")
    assert (
        client.post(
            "/api/v1/analytics/competitors/research",
            json={"movie_id": movie["movie_id"]},
            headers=intruder,
        ).status_code
        == 404
    )
    assert (
        client.get(
            f"/api/v1/analytics/competitors?movie_id={movie['movie_id']}", headers=intruder
        ).status_code
        == 404
    )


def test_learning_loop_creates_insights_and_experiment(client: TestClient) -> None:
    headers = _register(client)
    uploaded, _ = _publish(client, headers, "Punch Drunk Love")
    _ = client.post(f"/api/v1/analytics/video/{uploaded['publication_id']}/refresh", headers=headers)

    learn = client.post("/api/v1/analytics/learn", json={}, headers=headers)
    assert learn.status_code == 201, learn.text
    body = learn.json()
    assert body["job_id"] > 0
    assert body["scope"] == "global"
    assert body["insight_count"] == len(body["insights"])
    assert body["proposed_strategy"]["strategy_version"] == "v2"
    assert abs(sum(body["proposed_strategy"]["weights"].values()) - 1.0) < 0.01

    experiments = client.get("/api/v1/analytics/experiments", headers=headers)
    assert experiments.status_code == 200
    exp = experiments.json()[0]
    assert exp["status"] == "proposed"
    assert exp["stage"] == "analytics_calibration"

    insights = client.get("/api/v1/analytics/insights", headers=headers)
    assert insights.status_code == 200
    assert len(insights.json()) == body["insight_count"]


def test_learning_loop_no_metrics_still_emits_data_insight(client: TestClient) -> None:
    headers = _register(client)
    learn = client.post("/api/v1/analytics/learn", json={}, headers=headers)
    assert learn.status_code == 201
    body = learn.json()
    assert body["insight_count"] == 1
    assert body["insights"][0]["category"] == "data"


def test_summary_aggregates_only_owner_metrics(client: TestClient) -> None:
    owner = _register(client, "owner7c@example.com")
    uploaded, _ = _publish(client, owner, "Phantom Thread")
    _ = client.post(f"/api/v1/analytics/video/{uploaded['publication_id']}/refresh", headers=owner)

    summary = client.get("/api/v1/analytics/summary", headers=owner)
    assert summary.status_code == 200
    s = summary.json()
    assert s["video_count"] == 1
    assert s["total_views"] > 0
    assert s["avg_ctr_pct"] > 0
    assert s["total_watch_time_hours"] > 0

    intruder = _register(client, "intruder7c@example.com")
    other = client.get("/api/v1/analytics/summary", headers=intruder)
    assert other.status_code == 200
    assert other.json()["video_count"] == 0


def test_default_strategy_is_v1(client: TestClient) -> None:
    headers = _register(client)
    strategy = client.get("/api/v1/analytics/strategy", headers=headers)
    assert strategy.status_code == 200
    body = strategy.json()
    assert body["strategy_version"] == "v1"
    assert body["source"] == "default"
    assert set(body["weights"].keys()) == {
        "demand",
        "trend",
        "audience_fit",
        "evergreen",
        "competition",
        "difficulty",
    }
    assert abs(sum(body["weights"].values()) - 1.0) < 0.001


def test_experiment_create_activate_changes_scoring(client: TestClient) -> None:
    headers = _register(client)
    movie = client.post(
        "/api/v1/movies/research", json={"title": "Licorice Pizza", "year": 2021}, headers=headers
    ).json()

    baseline = client.post(
        "/api/v1/opportunities/score", json={"movie_id": movie["movie_id"]}, headers=headers
    ).json()["score"]["overall"]

    create = client.post(
        "/api/v1/analytics/experiments",
        json={"name": "Demand only", "strategy_version": "v9", "weights": {"demand": 1.0}},
        headers=headers,
    )
    assert create.status_code == 201, create.text
    exp = create.json()
    assert exp["status"] == "proposed"

    activate = client.post(
        f"/api/v1/analytics/experiments/{exp['id']}/activate", headers=headers
    )
    assert activate.status_code == 200
    assert activate.json()["status"] == "active"

    strategy = client.get("/api/v1/analytics/strategy", headers=headers).json()
    assert strategy["strategy_version"] == "v9"
    assert strategy["source"] == "experiment"
    assert abs(sum(strategy["weights"].values()) - 1.0) < 0.001

    rescore = client.post(
        "/api/v1/opportunities/score", json={"movie_id": movie["movie_id"]}, headers=headers
    ).json()["score"]
    assert rescore["overall"] != baseline
    # scoring phải dùng đúng trọng số đã normalized từ experiment (docs/13)
    expected = round(
        sum(rescore[k] * w for k, w in strategy["weights"].items()),
        1,
    )
    assert rescore["overall"] == expected


def test_experiment_requires_weights_and_ownership(client: TestClient) -> None:
    owner = _register(client, "owner7d@example.com")
    create = client.post(
        "/api/v1/analytics/experiments",
        json={"name": "No weights", "strategy_version": "v9", "weights": {}},
        headers=owner,
    )
    assert create.status_code == 422

    exp_id = client.post(
        "/api/v1/analytics/experiments",
        json={"name": "Real", "strategy_version": "v9", "weights": {"trend": 1.0}},
        headers=owner,
    ).json()["id"]

    intruder = _register(client, "intruder7d@example.com")
    assert (
        client.post(f"/api/v1/analytics/experiments/{exp_id}/activate", headers=intruder).status_code
        == 404
    )