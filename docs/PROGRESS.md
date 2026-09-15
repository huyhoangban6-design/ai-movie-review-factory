# PROGRESS.md

Nhật ký trạng thái dự án AI Movie Review Factory. Cập nhật sau mỗi phase.

## Tổng quan
| Phase | Nội dung | Trạng thái |
|---|---|---|
| 0 | Docs thiết kế (00–15) | ✅ Hoàn tất |
| 1 | Skeleton + DB + auth + dashboard | ✅ Hoàn tất (commit `7aedf8c`) |
| 2 | Movie research → opportunity → angle | ✅ Hoàn tất (commit `85d7c4d`) |
| 3 | Script → voice → timestamps | ✅ Hoàn tất (commit `ce7b366`) |
| 4 | Visual plan → assets → copyright gate | ✅ Hoàn tất (commit `ad904f0`) |
| 5 | FFmpeg render → subtitle → QA | ✅ Hoàn tất (offline providers + full test, sandbox 2026-09-14) |
| 6 | YouTube private upload → approval → publish | ✅ Hoàn tất (commit `0c161f3`) |
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

## Phase 4 — đã làm
- Models mới (migration `20260914_0004`): `assets` (+ `asset_sources` provenance/license/risk metadata), `copyright_reviews` (risk_level low/medium/high, duration_warning, human_review_required, decision block/human_review/approved). Script model mở rộng thêm `visual_plan` (JSON list VisualPlanSegment) + `pipeline_status` (script → visual_plan → assets → copyright).
- Provider layer Phase 4: `VisualPlannerProvider` / `AssetProvider` / `CopyrightProvider` + offline deterministic.
  - Visual planner: map từng script segment → section-appropriate plan (asset_types, duration_s, purpose), deterministic.
  - Asset provider: tạo placeholder CC0 hoặc theo source_hint; replacement-based (xóa asset cũ trước khi tạo mới).
  - Copyright provider: risk scoring — commercial_use=no → +0.6 block, missing license → +0.2, clip > 3.0s → duration_warning +0.3 human_review_required.
- API mới (auth + job lifecycle):
  - `POST /visual/plan` → sinh visual plan từ script segments; lưu vào `scripts.visual_plan`, cập nhật `pipeline_status`.
  - `POST /assets/generate` / `POST /assets/search` → tạo asset theo visual plan; lưu `assets`, set `pipeline_status=assets`.
  - `POST /copyright/evaluate` → đánh giá bản quyền; lưu `copyright_reviews`, set `pipeline_status=copyright`, trả human_review_count + blocked_count.
  - `GET /scripts/{id}` mở rộng trả `visual_plan`, `assets`, `copyright_reviews`, `pipeline_status`.
- Frontend `MovieDetailView`: thêm 3 nút pipeline (Phân plan → Tạo hình → Kiểm bản quyền), hiển thị visual plan segments + assets list + copyright risk badges.
- Tests offline: visual plan mapping, asset generation + replacement, 3-second rule, commercial_use block, copyright ownership isolation.

## Phase 2 — còn thiếu / lưu ý
- Provider thật (TMDB/web/LLM) chưa cắm — cần key ở `.env` (xem `.env.example`). Cấu trúc adapter đã sẵn sàng.
- CP1 confirm (chọn/bỏ góc nội dung) chưa có UI — hiện mặc định giữ nguyên 6 góc đầu.
- `competitors`/`competitor_videos` chưa được viết bởi endpoint (dự kiến Phase 7 nghiên cứu đối thủ qua analytics).

## Phase 1 — còn thiếu / lưu ý
- Môi trường sandbox hiện tại **không có pip/node/docker**, nên:
  - Backend mới được syntax-check bằng `compileall` (OK); **chưa chạy `pytest` hay import toàn app**.
  - Frontend chưa chạy `npm install` / `npm run build` / `vitest`.
  → Cần người dùng chạy local theo README (hoặc Docker) để xác nhận test pass.
- Chưa có email verification, reset password (ngoài MVP Phase 1).
- Worker/queue (Redis) mới là scaffold — nghiên cứu/score/angles chạy đồng bộ trong request; job lưu trạng thái đầy đủ để worker Phase 8 nối sau.
- Rate limit auth đang dùng bộ nhớ trong-memory (dự kiến chuyển Redis Phase 8).
- Ghi chú: `create_project` không tạo job; job được tạo bởi research/score/angles endpoints.

## Phase 4 — còn thiếu / lưu ý
- Provider thật (DALL-E/Midjourney/Unsplash) chưa cắm — offline deterministic placeholder. Cấu trúc adapter đã sẵn sàng.
- CP5 (chọn/reject asset) chưa có UI — hiện auto-generate toàn bộ.
- Asset search offline chỉ trả CC0 placeholder; cần provider thật để tìm footage thực.

## Phase 5 — đã làm
- Models mới (migration `20260914_0005_render_subtitle_qa`): `video_renders` (status, video_url, thumbnail, output_path, resolution/fps/codec, duration, file_size, render_config, render_log), `subtitles` (format srt/vtt, language, content, duration, cue_count, status), `qa_reports` (gate, passed, mandatory, checks JSON, severity, notes). Migration này cũng thêm `projects.idempotency_key` (unique) và làm `jobs.project_id` nullable.
- Provider layer Phase 5: `RenderProvider` / `SubtitleProvider` / `QAProvider` + offline deterministic.
  - Offline render: tạo metadata `1280x720@30`, h264/aac, `file://offline/render/{id}.mp4`, `file_size = duration * 240_000`, `render_ok=True` (mô phỏng đầu ra của ffmpeg, chưa mã hoá video thật).
  - Offline subtitle: dựng SRT/VTT từ timeline segments (start/end/text), fallback transcript khi thiếu timeline.
  - Offline QA: 8 gate — fact, script (không bắt buộc), voice, visual (đủ asset), subtitle (có + sync với render duration), copyright (không asset bị block), technical (render ok + duration + file + resolution/fps), final (chỉ pass khi mọi gate bắt buộc đạt).
- API mới (auth + job lifecycle):
  - `POST /video/render` → preconditions 422: chưa có voice hoàn tất / thiếu visual plan / thiếu asset / có asset bị block bản quyền; set `pipeline_status=render`.
  - `POST /video/subtitle` → preconditions 422: chưa có timeline / chưa có voice; replace `subtitles`, set `pipeline_status=subtitle`.
  - `POST /video/qa` → preconditions 422: chưa có render / subtitle; replace `qa_reports` mỗi lần chạy, set `pipeline_status=qa`, trả `final_passed`.
  - `GET /scripts/{id}` mở rộng trả thêm `renders`, `subtitles`, `qa_reports`.
- Frontend `MovieDetailView`: thêm 3 nút pipeline (Render video → Làm phụ đề → Chạy QA) + hiển thị video render info / subtitle / báo cáo QA (PASS/FAIL từng gate).
- Tests (48 tests tất cả pass trong sandbox): `tests/test_phase5.py` — render preconditions, render success, block asset gate, subtitle SRT/VTT + replace, QA full pipeline pass, QA block khi asset bị block, script detail bao gồm render/subtitle/QA, ownership isolation.
- Sửa bug cũ để cả suite chạy được: thêm import `SentenceLike`/`AssetLike` (providers), router auth thiếu prefix `/auth`, project idempotency dựa trên `Project.idempotency_key` thay vì job bị bỏ, `jobs.project_id` nullable, convert ORM→schema trong movie detail. Idempotency key giờ có counter per-attempt (`next_attempt_key`) nên các thao tác chạy lại (script v2, asset replace, render lại…) không vướng unique constraint.

## Phase 5 — còn thiếu / lưu ý
- Render chỉ ở mức offline metadata (không ffmpeg thật). Cắm provider thật bằng cách set `RENDER_PROVIDER`, `SUBTITLE_PROVIDER`, `QA_PROVIDER` (xem `.env.example`).
- `job_type` subtitle dùng giá trị `subtitle` mới thêm vào enum `JobType` (không phải `qa`).
- QA `script` gate không bắt buộc trong kết quả cuối; `QA_MANDATORY_GATES` khai báo nhưng kiểm tra dựa trên cờ `mandatory` từng gate.

## Phase 6 — đã làm (YouTube private upload → approval → publish, CP6)
- Model mới (migration `20260914_0006`): `publications` (script_id/render_id/project_id, status private_uploaded/ready_to_publish/scheduled/published/rejected/failed, youtube_video_id, title/description/tags, privacy_status, publish_at, published_url, approved/approval_note/approved_at, upload_metadata, error_message). `JobType` đã có sẵn `upload`/`publish`.
- Provider layer Phase 6: `PublishingProvider` + `OfflinePublishingProvider` deterministic — video id = `offline-{hash11}`, watch URL, simulated upload_metadata; publish trả `published`/`scheduled` + publish_at.
- API mới (auth + job lifecycle như Phase 5):
  - `POST /youtube/upload` → preconditions 422: thiếu Final QA pass (gate `final`)/render chưa RENDERED/subtitle; tạo publication status `private_uploaded`, set `pipeline_status=upload`.
  - `POST /youtube/approve` → CP6: approved=true → `ready_to_publish`, approved=false → `rejected`; không duyệt được publication đã published/scheduled (409).
  - `POST /youtube/publish` → 422 nếu chưa duyệt; có `publish_at` → `scheduled`, không → `published`; set `pipeline_status=published`.
  - `GET /youtube/publications/{id}` → trạng thái publication.
  - `GET /scripts/{id}` mở rộng trả thêm `publications`.
  - Preconditions đúng docs/13 + docs/00 #8: không bao giờ public nếu chưa Final QA + Human Approval.
- Frontend `MovieDetailView`: 3 nút pipeline (Upload YouTube (private) → Duyệt/Từ chối (CP6) → Publish (public)) + hiển thị publications (status badge, youtube id, link xem video, ghi chú duyệt).
- Tests (10 mới, tổng 58): `tests/test_phase6.py` — upload cần final QA (422), upload private success + publications trong script detail, title mặc định, approve ready_to_publish, reject, publish cần approval (422), publish public sau approval, schedule trong tương lai, ownership isolation 404, job upload succeeded.
- Sửa bug nền để cả suite chạy được:
  - `JobOut.project_id` thành nullable (jobs.project_id đã nullable từ Phase 5 mà schema bắt int).
  - **Migration chain 0001→0006 giờ chạy được thật** (trước đây chưa từng kiểm tra): 
    - `_now()` sinh cột không tên → đổi thành `"created_at"` (6 file migration, 24 bảng).
    - `alter_column jobs.project_id` không tương thích SQLite → dùng `op.batch_alter_table` (0005).
  - `mark_job_success` ở publish nhận `PublishOutput` (model) thay vì `dict` để `model_dump_json` serialize `datetime` (dòng-json báo lỗi).

## Phase 6 — còn thiếu / lưu ý
- Provider thật (YouTube Data API v3 — OAuth, upload video bytes, set thumbnail, check Content ID) chưa cắm: `YOUTUBE_PROVIDER=offline` giả lập (xem `.env.example`).
- UI chỉ hỗ trợ approval đơn giản (note text); chưa có luồng "kiểm tra sau upload Private" (metadata/thumbnail/audio) như mô tả docs/13 — nằm ở provider thật.
- Publication hiện gắn theo script (mỗi script có thể nhiều publication = các lần upload); chưa có "package" riêng cho thumbnail + SEO title/description ở Phase 6.
- Scheduler đang giả lập ở mức trạng thái `scheduled`; worker auto-publish theo `publish_at` sẽ nối ở Phase 8.

## Kiểm tra test thật (sandbox 2026-09-15)
| Kiểm tra | Kết quả |
|---|---|
| Backend pytest toàn bộ `tests/` (auth + projects + phase2 + phase3 + phase4 + phase5 + phase6) | ✅ 58 passed |
| `tests/test_phase6.py` (YouTube upload/approve/publish) | ✅ 10 passed |
| Import toàn app `from app.main import app` + routes `/api/v1/youtube/*` (4 routes) | ✅ |
| `alembic upgrade head` trên SQLite mới (0001→0006) | ✅ Clean (đã sửa `_now()` cột created_at + batch_alter_column jobs) |
| `alembic downgrade base` chạy ngược toàn bộ chain | ✅ Clean |
| Frontend `npm test` (vitest format) | ✅ 3 passed (Node 20.18.3) |
| Frontend `npm run build` (vite production) | ✅ Built (~192 KB js) |

## Kiểm tra static (Phase 4, sandbox 2026-09-14)
| Kiểm tra | Kết quả |
|---|---|
| `python3 -m compileall` toàn bộ `backend/` | ✅ 0 lỗi (37 files) |
| AST import trace — mỗi Phase 4 file import đúng symbol | ✅ All OK |
| Topological sort module graph (37 modules) | ✅ Acyclic, no circular imports |
| Migration chain 0001→0002→0003→0004 linear | ✅ Clean |
| Migration 0004 columns vs model definitions | ✅ Match (assets: 18 cols, asset_sources: 7 cols, copyright_reviews: 7 cols, scripts add: visual_plan + pipeline_status) |
| `alembic/env.py` imports `Base` → metadata includes new tables | ✅ |
| `requirements.txt` deps sufficient (pydantic, sqlalchemy, alembic, pytest, httpx) | ✅ No new deps needed |
| `main.py` router registration: 13 routers all included | ✅ |
| Frontend JSX bracket balance + handler definitions | ✅ 398 opens = 398 closes, 3 handlers defined |
| `config.py` settings: visual_provider, asset_provider, copyright_provider, asset_source_hint | ✅ |
| `schemas/api.py` ↔ `schemas/visual.py` no circular import | ✅ |
| `CopyrightReviewOutput` field types consistent between providers, routers, detail response | ✅ |

## Chưa kiểm tra được (cần chạy local)
- Migrations trên PostgreSQL thật (đã kiểm tra SQLite; SQLite giờ chạy `upgrade head` và `downgrade base` sạch).
- `pytest`/`npm test`/`npm run build` đã chạy được trong sandbox này (Python 3.12 + Node 20). Vẫn chưa test Docker Compose + Postgres + Redis.

## Lệnh cần chạy trên máy local
```bash
# 1. Backend — install deps + migrate + test
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example ../.env           # chỉnh SECRET_KEY, DATABASE_URL nếu cần
mkdir -p data                        # SQLite fallback
alembic upgrade head                 # chạy migration 0001→0006
pytest tests/ -v                     # 58 tests (auth → phase6)

# 2. Backend — chạy server kiểm tra API
python run.py                        # http://localhost:8000/docs

# 3. Frontend — install + build
cd frontend
npm install
npm run dev                          # http://localhost:5173
```