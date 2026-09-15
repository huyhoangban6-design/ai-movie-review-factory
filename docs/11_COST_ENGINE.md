# Cost Engine

Modes:
FREE — tối thiểu chi phí
BALANCED — cân bằng
PREMIUM — chất lượng tối đa

Trước job:
estimate cost → nếu > MAX_COST_PER_VIDEO: STOP + approval.

Sau job:
record actual cost theo provider/model/job.

Cache kết quả có thể tái sử dụng.
Có budget theo project và cost alerts.

## Implementation note (Phase 8)

- Cost mode multiplier: `COST_MODE_MULTIPLIER` FREE=0.5 / BALANCED=1.0 / PREMIUM=1.5. Project chọn mode qua `projects.cost_mode` (migration `20260915_0008`), mặc định `balanced` (config `COST_MODE_DEFAULT`); `PATCH /projects/{id}/budget` đổi `max_cost_per_video` + `cost_mode`.
- Đơn giá: `DEFAULT_RATES` đủ 17 JobType, offline-safe (voice theo 1k ký tự, render theo phút render, asset theo cái, …); đơn vị chuẩn per-job_type. Rate voice/render đè qua env `COST_RATE_VOICE_PER_1K_CHARS` (default 0.0001 USD) và `COST_RATE_RENDER_PER_MINUTE` (default 0.001 USD).
- Budget gate (`check_budget`): pre-job `estimate_cost + total_actual_cost` > `max_cost_per_video` → `HTTP 402` "cần duyệt" (chạy pipeline có chi phí thật mới chặn). Không set max → `no_limit` (không bao giờ 402). Khi spent ≥ `COST_ALERT_THRESHOLD_PCT` (default 80%) → ghi `system_logs` event `budget_alert`.
- Ghi cost (`record_cost`): mọi job qua `record_job_cost` trước điểm commit — ghi bản ghi (mode nhân estimate, `cost_usd` unit, `provider.name`, model) + set `jobs.cost_usd`/`jobs.provider_name`. Chia loại `voice|render|assets|upload|publish|analytics`.
- Fallback + retry + circuit breaker (`services/fallback.py`, docs/00 #8): `run_with_fallback(primary, fallbacks, provider_name, max_retries, backoff_base, backoff_max)` — retry primary exponential backoff (`max_retries_default=3`), fallback mỗi provider đúng 1 lần; thất bại toàn bộ → `ProviderUnavailableError` → HTTP 503 + circuit increment. Circuit `CIRCUIT_BREAKER_THRESHOLD` (5) lỗi liên tiếp → mở trong `CIRCUIT_BREAKER_RESET_SECONDS` (60s, fast-fail không gọi provider), success đóng lại (half-open per call). Đang gắn cho voice + render (fallback offline deterministic). `sleep` injectable để test chạy nhanh, không chờ backoff thật.
- Retry lifecycle job: `mark_job_running` → thất bại → `should_retry` (FAILED dưới cap) → `mark_job_retry_pending` (PENDING + `next_retry_at` = now + backoff, bqd qua `get_retry_delay`) → chạy lại; `mark_job_success/failed` đóng `completed_at`. `request_id` truyền qua `X-Request-Id` (tracing từ middleware).
- Bảng mới: `cost_records`, `system_logs` (xem `docs/03_DATABASE_SCHEMA.md`).