# PROGRESS.md

Nhật ký trạng thái dự án AI Movie Review Factory. Cập nhật sau mỗi phase.

## Tổng quan
| Phase | Nội dung | Trạng thái |
|---|---|---|
| 0 | Docs thiết kế (00–15) | ✅ Hoàn tất |
| 1 | Skeleton + DB + auth + dashboard | ✅ Hoàn tất (commit `7aedf8c`) |
| 2 | Movie research → opportunity → angle | ✅ Hoàn tất (commit `85d7c4d`) |
| 3 | Script → voice → timestamps | ✅ Hoàn tất (commit `ce7b366`) |
| 4 | Visual plan → assets → copyright gate | ⬜ Chưa bắt đầu |
| 5 | FFmpeg render → subtitle → QA | ⬜ Chưa bắt đầu |
| 6 | YouTube private upload → approval → publish | ⬜ Chưa bắt đầu |
| 7 | Analytics → experiments → learning | ⬜ Chưa bắt đầu |
| 8 | Cost engine + fallback + production hardening | ⬜ Chưa bắt đầu |

## Phase 1 — đã làm
- Skeleton thư mục theo docs/02 (`backend/`, `frontend/`, `docs/`).
- Backend FastAPI:
  - `app/core`: config (pydantic-settings, đọc `.env`), database (SQLAlchemy 2, hỗ trợ SQLite/PG), security (bcrypt + JWT).
  - `app/models`: `User`, `Project`, `Job` (job_type/status/retry/idempotency_key/log ref), `MediaSource` (provenance/license/risk sẵn sàng cho Phase 4).
  - `app/api`: auth (register/login/me + rate limit in-memory), projects (list/create/detail + `Idempotency-Key`), jobs (trạng thái).
  - `main.py`: health check, CORS, mount frontend build nếu có, `create_all` cho dev.
- Alembic: migration `20260914_0001_initial` (users, projects, jobs, media_sources). `alembic/env.py` tự đọc `DATABASE_URL`.
- Tests backend (pytest + SQLite in-memory): auth, register/login/me, tạo project tự kickoff job `movie_research`, idempotency, phân quyền (404 cho user khác).
- Frontend React + Vite + PWA (phone-first):
  - `AuthView` (đăng nhập/đăng ký), `DashboardView` (danh sách + tạo project), `ProjectDetailView` (pipeline jobs + lỗi).
  - api client có token, xử lý 401, báo lỗi tiếng Việt; `manifest.json` + `sw.js` (cache GET, bỏ qua `/api`).
  - Unit test nhỏ cho `format.js` (Vitest).
- Docker: `docker-compose.yml` (postgres 16, redis 7, backend, migrate, frontend dev), Dockerfile backend + frontend (nginx), `nginx.conf` proxy `/api`.

## Phase 2 — đã làm
- Models mới (migration `20260914_0002`): `movies`, `movie_sources` (provenance/nguồn), `movies_analysis` (facts/themes), `opportunities` (overall + sub_scores + confidence + strategy_version), `content_angles` (CP1), `competitors` + `competitor_videos`.
- Provider layer theo `docs/02` + `docs/05`:
  - Interface `ResearchProvider` / `OpportunityProvider` / `AngleProvider`.
  - Factory theo env (`RESEARCH_PROVIDER`/`OPPORTUNITY_PROVIDER`/`ANGLE_PROVIDER`), mặc định `offline` (không network, deterministic để test).
  - Scoring dùng trọng số (được calibrate lại Phase 7), hàm `weighted_opportunity_score` thuần + test.
- API mới (auth + tạo job theo dõi trạng thái):
  - `POST /movies/research` → tạo `movies` + `movie_sources` + `movies_analysis` + job `movie_research`.
  - `POST /opportunities/score` → upsert `opportunities` + job `opportunity_score`.
  - `POST /content/angles` → replace `content_angles` (góc nội dung, CP1) + job `content_angle`.
  - `GET /movies/{id}` → detail + sources + summaries + score + angles.
  - `GET /jobs/{id}` truy vấn trạng thái job.
- Job lifecycle đầy đủ: pending → succeeded/failed, có `idempotency_key`, `input_payload`, `output_summary`, `error_message`, `retry_count`. (Worker/queue Redis ghép nối Phase 8; hiện chạy đồng bộ trong request để dễ test.)
- Frontend: form "Nghiên cứu phim" trên dashboard, `MovieDetailView` hiện điểm cơ hội + góc nội dung (CP1).
- `create_project` không còn tạo job kickoff giả (nghiên cứu có endpoint riêng).

## Phase 3 — đã làm
- Models mới (migration `20260914_0003`): `scripts` (+`script_segments` theo sơ đồ HOOK→THESIS→…→CTA), `voice_providers` (tier cloud/gpu/self_hosted/backup + license + cost), `voice_profiles` (voice_id/provider/model/style/speed/emotion/commercial_use/license/cloning_permission), `voice_generations` (text_hash cache, audio, word+sentence timestamps, license_info, cost), `script_timelines` (segment→time để Visual Planner Phase 4 căn theo voice).
- Provider layer mở rộng: `ScriptProvider`/`VoiceProvider`/`TimelineProvider` + offline impl deterministic.
  - Script: 9 segments đúng cấu trúc Script Agent; `estimated_duration_s` theo tốc độ đọc.
  - Voice: license gate `commercial_use=no → block`, `unknown → risk note`; tạo profile mặc định `offline-vi-female` khi chưa có; timestamps giả lập theo độ dài câu/từ + cache hash.
  - Timeline: căn từng segment theo sentence timestamps của voice (char-position alignment), phục vụ Visual Planner.
- API mới (auth + job lifecycle như Phase 2):
  - `POST /scripts/generate` → tạo `scripts` + `script_segments` + job `script`; version tăng dần theo movie.
  - `GET /scripts/{id}` → detail script + segments + voice mới nhất + timeline.
  - `POST /voice/generate` → TTS theo profile (tự tạo mặc định), license gate, job `voice`; sinh `voice_generations`.
  - `POST /timeline/build` → yêu cầu có voice trước (422 nếu chưa), replace `script_timelines` + job `timeline`.
  - `GET /movies/{id}` → có thêm `scripts` (summary).
- Frontend: `MovieDetailView` thêm pipeline buttons (Viết kịch bản → Tạo giọng đọc → Dựng timeline) + hiển thị segments/timeline/voice (xem dưới).
- `.env.example`: thêm `SCRIPT_PROVIDER`/`VOICE_PROVIDER`/`TIMELINE_PROVIDER` + `DEFAULT_VOICE_*`.

## Phase 3 — còn thiếu / lưu ý
- Provider TTS thật (elevenlabs/google/azure) chưa cắm — offline có timestamps giả lập. Cấu trúc adapter + license gate đã sẵn sàng.
- CP2 (duyệt kịch bản script) & CP3 (duyệt voice) chưa có UI/workflow — hiện script tự `draft`.
- Timeline hiện ở mức segment; Visual Planner (Phase 4) sẽ căn từ segment → visual beats.
- Vẫn chưa chạy tests thật trong sandbox — cần chạy local.

## Phase 2 — còn thiếu / lưu ý
- Provider thật (TMDB/web/LLM) chưa cắm — cần key ở `.env` (xem `.env.example`). Cấu trúc adapter đã sẵn sàng.
- CP1 confirm (chọn/bỏ góc nội dung) chưa có UI — hiện mặc định giữ nguyên 6 góc đầu.
- `competitors`/`competitor_videos` chưa được viết bởi endpoint (dự kiến Phase 7 nghiên cứu đối thủ qua analytics).
- Vẫn chưa chạy được tests thật trong sandbox (thiếu pip/node) — cần chạy local.

## Phase 1 — còn thiếu / lưu ý
- Môi trường sandbox hiện tại **không có pip/node/docker**, nên:
  - Backend mới được syntax-check bằng `compileall` (OK); **chưa chạy `pytest` hay import toàn app**.
  - Frontend chưa chạy `npm install` / `npm run build` / `vitest`.
  → Cần người dùng chạy local theo README (hoặc Docker) để xác nhận test pass.
- Chưa có email verification, reset password (ngoài MVP Phase 1).
- Worker/queue (Redis) mới là scaffold — nghiên cứu/score/angles chạy đồng bộ trong request; job lưu trạng thái đầy đủ để worker Phase 8 nối sau.
- Rate limit auth đang dùng bộ nhớ trong-memory (dự kiến chuyển Redis Phase 8).
- Ghi chú: `create_project` không tạo job; job được tạo bởi research/score/angles endpoints.

## Manual setup cần người dùng
1. Copy `.env.example` → `.env`, đặt `SECRET_KEY` mạnh, điền provider keys nếu dùng provider thật.
2. Cài Python 3.12 + Node 20, hoặc Docker.
3. Chạy migration rồi khởi động theo README.
4. Trên một movie, chạy đủ pipeline Phase 3 để kiểm tra: `/movies/research` → `/opportunities/score` → `/content/angles` → `/scripts/generate` → `/voice/generate` → `/timeline/build`, rồi xem `GET /movies/{id}` + `GET /scripts/{id}`.