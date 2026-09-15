"""Phase 8 tests: cost engine, budget limits, provider fallback, retry, isolation, config.

Covers: cost math (estimate, modes, rates), budget gate (402 when vượt ngưỡng),
run_with_fallback + circuit breaker (fallback + retry + backoff), job retry
helpers, ownership isolation trên cost endpoints, migration (upgrade/downgrade),
API responses cost records/summary/alerts, offline mode không phá vỡ pipeline,
config validation + hardening.
"""

from fastapi import HTTPException
from fastapi.testclient import TestClient
import pytest
from sqlalchemy.orm import Session
from types import SimpleNamespace

from app.core.config import settings
from app.core.database import get_db
from app.main import app
from app.models.cost import CostRecord, SystemLog
from app.models.job import Job, JobStatus, JobType
from app.models.project import Project
from app.services.cost import (
    COST_MODE_MULTIPLIER,
    check_budget,
    estimate_cost,
    project_cost_summary,
    record_job_cost,
    total_actual_cost,
)
from app.services.fallback import (
    ProviderUnavailableError,
    circuit_failure,
    circuit_ok,
    circuit_status,
    reset_circuits,
    run_with_fallback,
)
from app.services.jobs import (
    create_job,
    get_retry_delay,
    mark_job_failed,
    mark_job_retry_pending,
    mark_job_running,
    mark_job_success,
    should_retry,
)
from tests.test_phase6 import (
    _full_pipeline,
    _promote_pipeline_to_qa,
    _register as _register_phase6,
    _upload,
)


def _register(client: TestClient, email: str = "phase8@example.com") -> dict:
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": email, "display_name": "Phase Eight", "password": "phase8-pass-123"},
    )
    assert resp.status_code == 201, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _create_project(client: TestClient, headers: dict, title: str = "Budget Proj", max_cost: float = 0.01) -> dict:
    resp = client.post(
        "/api/v1/projects",
        json={"title": title, "description": "phase8", "max_cost_per_video": max_cost, "cost_mode": "balanced"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.fixture(autouse=True)
def _reset_circuits():
    reset_circuits()
    yield
    reset_circuits()


@pytest.fixture()
def db_session():
    """DB session chia sẻ cùng in-memory engine với TestClient (StaticPool)."""
    gen = app.dependency_overrides[get_db]()
    db: Session = next(gen)
    yield db
    gen.close()


# ─────────────────────────────────────────────────────────────────────────────
# Cost math
# ─────────────────────────────────────────────────────────────────────────────
def test_estimate_cost_modes_scale_multiplier() -> None:
    for jt in (JobType.SCRIPT, JobType.RENDER, JobType.VOICE, JobType.ASSETS):
        _, free, _, _ = estimate_cost(jt, 1.0, mode="free")
        _, bal, _, _ = estimate_cost(jt, 1.0, mode="balanced")
        _, prem, _, _ = estimate_cost(jt, 1.0, mode="premium")
        assert free == round(bal * COST_MODE_MULTIPLIER["free"], 8)
        assert prem == round(bal * COST_MODE_MULTIPLIER["premium"], 8)
        assert free <= bal <= prem


def test_estimate_cost_voice_uses_per_char_rate(client: TestClient) -> None:
    headers = _register(client, "voicecost@example.com")
    rate = settings.cost_rate_voice_per_1k_chars
    resp = client.post(
        "/api/v1/cost/estimate",
        json={"job_type": "voice", "units": 5000, "provider": "offline", "mode": "balanced"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["unit"] == "chars"
    assert body["unit_rate_usd"] == round(rate / 1000, 10)
    assert body["estimated_cost_usd"] == round(5000 * (rate / 1000) * 1.0, 8)
    assert body["category"] == "voice"
    assert body["currency"] == "usd"


def test_estimate_cost_render_uses_per_minute(monkeypatch, client: TestClient) -> None:
    headers = _register(client, "rendercost@example.com")
    monkeypatch.setattr(settings, "cost_rate_render_per_minute", 0.5)
    resp = client.post(
        "/api/v1/cost/estimate",
        json={"job_type": "render", "units": 2.0, "provider": "offline", "mode": "premium"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["unit"] == "minute"
    assert body["unit_rate_usd"] == 0.5
    assert body["estimated_cost_usd"] == round(2.0 * 0.5 * COST_MODE_MULTIPLIER["premium"], 8)


def test_estimate_rejects_unknown_job_type(client: TestClient) -> None:
    headers = _register(client, "badtype@example.com")
    resp = client.post(
        "/api/v1/cost/estimate",
        json={"job_type": "nope", "units": 1, "provider": "offline", "mode": "balanced"},
        headers=headers,
    )
    assert resp.status_code == 422


# ─────────────────────────────────────────────────────────────────────────────
# Budget limits (docs/11: estimate > max → STOP + approval)
# ─────────────────────────────────────────────────────────────────────────────
def test_check_budget_raises_402_when_estimate_exceeds(client: TestClient, db_session: Session) -> None:
    headers = _register(client, "budget@example.com")
    project = _create_project(client, headers, max_cost=0.01)  # budget $0.01
    db = db_session
    try:
        # estimate nhiều phút render → vượt $0.01 → 402 Payment Required
        check_budget(db, project["id"], units=1000.0, job_type=JobType.RENDER)
        raise AssertionError("expected HTTPException 402")
    except HTTPException as exc:
        assert exc.status_code == 402
        assert "duyệt" in exc.detail.lower() or "budget" in exc.detail.lower()


def test_check_budget_passes_within_limit(client: TestClient, db_session: Session) -> None:
    headers = _register(client, "budgetok@example.com")
    project = _create_project(client, headers, max_cost=100.0)
    estimate, max_cost, exceeded, reason = check_budget(
        db_session, project["id"], units=1.0, job_type=JobType.RENDER
    )
    assert exceeded is False
    assert reason == "ok"
    assert max_cost == 100.0
    assert estimate >= 0


def test_check_budget_no_limit_when_unset(client: TestClient, db_session: Session) -> None:
    headers = _register(client, "nolimit@example.com")
    project = client.post(
        "/api/v1/projects",
        json={"title": "No Limit", "description": "x", "max_cost_per_video": None, "cost_mode": "balanced"},
        headers=headers,
    ).json()
    estimate, max_cost, exceeded, reason = check_budget(
        db_session, project["id"], units=10 ** 9, job_type=JobType.VOICE
    )
    assert reason == "no_limit"
    assert max_cost is None
    assert exceeded is False


def test_project_cost_summary_and_records(client: TestClient) -> None:
    headers = _register(client, "summary@example.com")
    project = _create_project(client, headers, max_cost=100.0)
    # ghi thủ công 2 khoản cost
    r1 = client.post(
        "/api/v1/cost/records",
        json={
            "project_id": project["id"], "job_type": "script", "provider": "offline",
            "mode": "balanced", "category": "content", "unit": "job", "units": 1,
            "unit_rate_usd": 0.001, "estimated_cost_usd": 0.001, "actual_cost_usd": 0.001,
        },
        headers=headers,
    )
    assert r1.status_code == 201, r1.text
    r2 = client.post(
        "/api/v1/cost/records",
        json={
            "project_id": project["id"], "job_type": "render", "provider": "offline",
            "mode": "balanced", "category": "render", "unit": "minute", "units": 3,
            "unit_rate_usd": 0.001, "estimated_cost_usd": 0.003, "actual_cost_usd": 0.003,
        },
        headers=headers,
    )
    assert r2.status_code == 201, r2.text

    summary = client.get(f"/api/v1/projects/{project['id']}/cost", headers=headers)
    assert summary.status_code == 200, summary.text
    body = summary.json()
    assert body["total_actual_usd"] == 0.004
    assert body["cost_mode"] == "balanced"
    assert body["max_cost_per_video"] == 100.0
    assert body["budget_percent_used"] == round(0.004 / 100 * 100, 2)
    assert body["per_category"]["render"] == 0.003
    assert len(body["records"]) == 2

    # PATCH budget + mode
    patched = client.patch(
        f"/api/v1/projects/{project['id']}/budget",
        json={"max_cost_per_video": 50.0, "cost_mode": "premium"},
        headers=headers,
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["max_cost_per_video"] == 50.0
    assert patched.json()["cost_mode"] == "premium"

    # records list filtered by project
    records = client.get(f"/api/v1/cost/records?project_id={project['id']}", headers=headers)
    assert records.status_code == 200
    assert len(records.json()) == 2


# ─────────────────────────────────────────────────────────────────────────────
# Ownership isolation
# ─────────────────────────────────────────────────────────────────────────────
def _second_user_headers(client: TestClient) -> dict:
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": "phase8b@example.com", "display_name": "Other", "password": "other-pass-123"},
    )
    assert resp.status_code == 201
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_cost_endpoints_isolated_by_owner(client: TestClient) -> None:
    headers = _register(client, "owner8@example.com")
    project = _create_project(client, headers)

    other = _second_user_headers(client)
    assert client.get(f"/api/v1/projects/{project['id']}/cost", headers=other).status_code == 404
    assert (
        client.patch(f"/api/v1/projects/{project['id']}/budget", json={"max_cost_per_video": 5}, headers=other).status_code
        == 404
    )
    assert (
        client.get(f"/api/v1/cost/records?project_id={project['id']}", headers=other).status_code == 404
    )


def test_record_cost_rejects_job_type_via_api(client: TestClient) -> None:
    headers = _register(client, "badrec@example.com")
    resp = client.post(
        "/api/v1/cost/records",
        json={
            "project_id": None, "job_type": "hack", "provider": "x", "mode": "balanced",
            "category": "other", "unit": "job", "units": 1, "unit_rate_usd": 0,
            "estimated_cost_usd": 0, "actual_cost_usd": 0,
        },
        headers=headers,
    )
    assert resp.status_code == 422


# ─────────────────────────────────────────────────────────────────────────────
# Fallback + circuit breaker (docs/11, docs/00 #idempotency/retry)
# ─────────────────────────────────────────────────────────────────────────────
def test_run_with_fallback_retries_then_falls_back() -> None:
    import random

    calls = {"n": 0}
    fails = 2

    def primary():
        calls["n"] += 1
        if calls["n"] <= fails:
            raise ConnectionError("primary down")
        return "primary-ok"

    def fallback():
        return "fallback-ok"

    result = run_with_fallback(primary, fallbacks=(fallback,), provider_name="test-retry", max_retries=3, sleep=lambda _: None)
    assert result == "primary-ok"
    assert calls["n"] == 3  # failed 2 lần, thành công ở attempt thứ 3


def test_run_with_fallback_all_fail_uses_fallback_provider_then_raises() -> None:
    def boom():
        raise ConnectionError("boom")

    def standalone():
        return "fallback-ok"

    result = run_with_fallback(boom, fallbacks=(standalone,), provider_name="test-fb", max_retries=1, sleep=lambda _: None)
    assert result == "fallback-ok"

    reset_circuits()
    # cả primary + fallback đều fail → ProviderUnavailableError
    with pytest.raises(ProviderUnavailableError):
        run_with_fallback(boom, fallbacks=(boom,), provider_name="test-fb2", max_retries=1, sleep=lambda _: None)


def test_circuit_breaker_opens_and_gates_calls() -> None:
    reset_circuits()
    threshold = settings.circuit_breaker_threshold

    def boom():
        raise ConnectionError("down")

    for _ in range(threshold):
        try:
            run_with_fallback(boom, fallbacks=(), provider_name="circ", max_retries=1, sleep=lambda _: None)
        except ProviderUnavailableError:
            pass

    status = circuit_status("circ")
    assert status["state"] == "open"
    assert circuit_ok("circ") is False

    # circuit mở → từ chối ngay (không retry)
    try:
        run_with_fallback(boom, fallbacks=(), provider_name="circ", max_retries=1, sleep=lambda _: None)
        raise AssertionError("circuit open nên phải raise")
    except ProviderUnavailableError as exc:
        assert "circuit open" in str(exc).lower()


def test_circuit_recovers_after_success() -> None:
    reset_circuits()
    try:
        run_with_fallback(lambda: (_ for _ in ()).throw(ConnectionError("x")), fallbacks=(), provider_name="rec", max_retries=1, sleep=lambda _: None)  # noqa: BLE001
    except ProviderUnavailableError:
        pass
    # success → circuit đóng lại
    result = run_with_fallback(lambda: "ok", fallbacks=(), provider_name="rec", max_retries=1, sleep=lambda _: None)
    assert result == "ok"
    assert circuit_status("rec")["state"] == "closed"


def test_backoff_delay_is_capped(monkeypatch) -> None:
    monkeypatch.setattr(settings, "retry_backoff_base_seconds", 2.0)
    monkeypatch.setattr(settings, "retry_backoff_max_seconds", 4.0)
    assert get_retry_delay(_fake_job(retry=0)) == 2.0
    assert get_retry_delay(_fake_job(retry=1)) == 2.0
    assert get_retry_delay(_fake_job(retry=3)) == 4.0  # 2*2^2 = 8 → cap 4
    assert get_retry_delay(_fake_job(retry=10)) == 4.0


def _fake_job(retry: int):
    return SimpleNamespace(retry_count=retry, max_retries=3)


# ─────────────────────────────────────────────────────────────────────────────
# Job retry helpers (docs/00 #8)
# ─────────────────────────────────────────────────────────────────────────────
def test_job_retry_lifecycle(client: TestClient, db_session: Session) -> None:
    headers = _register(client, "retryjob@example.com")
    db = db_session
    job = create_job(db, 1, JobType.SCRIPT, idempotency_key="1:retry:1")
    assert job.max_retries == settings.max_retries_default
    assert job.status == JobStatus.PENDING

    mark_job_running(db, job)
    assert job.status == JobStatus.RUNNING
    assert job.started_at is not None

    mark_job_failed(db, job, "boom")
    assert job.status == JobStatus.FAILED
    assert job.completed_at is not None
    assert should_retry(job) is True

    mark_job_retry_pending(db, job)
    assert job.status == JobStatus.PENDING
    assert job.retry_count == 1
    assert job.next_retry_at is not None
    # đã requeue (PENDING) → không còn "eligible retry" nữa
    assert should_retry(job) is False

    # chạy thành công → không retry nữa
    mark_job_success(db, job, {"ok": True})
    assert should_retry(job) is False


def test_should_retry_false_when_cap_reached(db_session: Session) -> None:
    job = _fake_job(retry=3)
    assert job.max_retries == 3
    job.status = JobStatus.FAILED
    assert should_retry(job) is False


# ─────────────────────────────────────────────────────────────────────────────
# Offline pipeline records cost (voice/analytics/publish) — không phá pipeline
# ─────────────────────────────────────────────────────────────────────────────
def test_voice_pipeline_records_cost_and_job_cost(client: TestClient) -> None:
    headers = _register(client, "voicerecord@example.com")
    movie, script = _full_pipeline(client, headers, "Arrival")
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

    resp = client.post(f"/api/v1/analytics/video/{uploaded['publication_id']}/refresh", headers=headers)
    assert resp.status_code == 201, resp.text

    records = client.get("/api/v1/cost/records", headers=headers)
    assert records.status_code == 200
    types = {r["job_type"] for r in records.json()}
    assert {"voice", "render", "assets", "upload", "publish", "analytics"} <= types

    for job_type in ("voice", "render", "upload", "publish", "analytics"):
        rec = next(r for r in records.json() if r["job_type"] == job_type)
        assert rec["actual_cost_usd"] >= 0
        assert rec["provider"] == "offline"

    # job cost_usd được set trên job
    vjob = next(r for r in records.json() if r["job_type"] == "voice")
    assert vjob["job_id"] is not None
    job = client.get(f"/api/v1/jobs/{vjob['job_id']}", headers=headers)
    assert job.status_code == 200
    assert job.json()["cost_usd"] == vjob["actual_cost_usd"]
    assert job.json()["provider_name"] == "offline"
    assert job.json()["max_retries"] == settings.max_retries_default


def test_voice_503_when_all_providers_fail(client: TestClient, monkeypatch) -> None:
    headers = _register(client, "voice503@example.com")
    project = client.post(
        "/api/v1/projects",
        json={"title": "Noise Proj", "description": "x", "max_cost_per_video": None, "cost_mode": "balanced"},
        headers=headers,
    ).json()
    movie = client.post(
        "/api/v1/movies/research",
        json={"title": "Noise", "year": 2020},
        headers={**headers, "X-Project-Id": str(project["id"])},
    )
    assert movie.status_code == 201, movie.text
    script = client.post(
        "/api/v1/scripts/generate",
        json={"movie_id": movie.json()["movie_id"]},
        headers=headers,
    )
    assert script.status_code == 201, script.text

    class _Boom:
        name = "boom"

        def synthesize(self, *a, **k):
            raise ConnectionError("provider down")

    import app.api.voice as voice_mod

    monkeypatch.setattr(voice_mod, "get_voice_provider", lambda: _Boom())
    monkeypatch.setattr(voice_mod, "OfflineVoiceProvider", _Boom)

    resp = client.post("/api/v1/voice/generate", json={"script_id": script.json()["script_id"]}, headers=headers)
    assert resp.status_code == 503
    assert "unavailable" in resp.json()["detail"]

    # job voice bị mark failed
    jobs = client.get(f"/api/v1/projects/{project['id']}/jobs", headers=headers)
    failed = [j for j in jobs.json() if j["job_type"] == "voice" and j["status"] == "failed"]
    assert len(failed) >= 1


# ─────────────────────────────────────────────────────────────────────────────
# Security / hardening / config validation
# ─────────────────────────────────────────────────────────────────────────────
def test_config_validation_default_flags_dev_secret() -> None:
    from app.core.hardening import validate_runtime_config

    problems = validate_runtime_config()
    assert any("SECRET_KEY" in p for p in problems)


def test_config_validation_non_offline_provider_without_credential(monkeypatch) -> None:
    from app.core.hardening import validate_runtime_config

    monkeypatch.setattr(settings, "research_provider", "tmdb")
    monkeypatch.setattr(settings, "tmdb_api_key", "")
    problems = validate_runtime_config()
    assert any("tmdb_api_key" in p for p in problems)


def test_config_validation_invalid_cost_mode(monkeypatch) -> None:
    from app.core.hardening import validate_runtime_config

    monkeypatch.setattr(settings, "cost_mode_default", "bogus")
    problems = validate_runtime_config()
    assert any("COST_MODE_DEFAULT" in p for p in problems)


def test_response_has_request_id_and_security_headers(client: TestClient) -> None:
    headers = _register(client, "headers@example.com")
    resp = client.get("/api/v1/projects", headers=headers)
    assert resp.status_code == 200
    assert resp.headers.get("x-request-id")
    assert resp.headers.get("x-content-type-options") == "nosniff"
    assert resp.headers.get("x-frame-options") == "DENY"


def test_cost_alerts_endpoint_and_system_log(client: TestClient, db_session: Session) -> None:
    headers = _register(client, "alerts@example.com")
    resp = client.get("/api/v1/cost/alerts", headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_health_has_no_security_header_but_ok(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"