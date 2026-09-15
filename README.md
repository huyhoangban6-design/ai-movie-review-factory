# AI Movie Review Factory

Ứng dụng web/PWA phone-first vận hành kênh YouTube review phim bằng AI.

- Docs thiết kế đầy đủ: [`docs/`](docs/00_START_HERE.md)
- Trạng thái dự án: [`docs/PROGRESS.md`](docs/PROGRESS.md)

## Stack
- Frontend: React + Vite + PWA
- Backend: Python + FastAPI + SQLAlchemy + Alembic
- Database: PostgreSQL (dev/test có thể dùng SQLite)
- Queue: Redis (ghép vào Phase 8)

## Phát triển local (cách A — cần Node + Python 3.12)
```bash
# Backend
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example ../.env
alembic upgrade head            # chạy migration
python scripts/seed.py          # tạo user demo (tuỳ chọn)
python run.py                   # http://localhost:8000, docs tại /docs

# Frontend (terminal 2)
cd frontend
npm install
npm run dev                     # http://localhost:5173 (proxy /api -> :8000)
```

Demo account (nếu chạy seed): `demo@example.com` / `demo-password-123`

## Phát triển local (cách B — Docker Compose)
```bash
docker compose up -d db redis
docker compose run --rm migrate
docker compose up backend frontend
```
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000/docs

## Test
```bash
cd backend && source .venv/bin/activate && pytest       # backend
cd frontend && npm test                                  # frontend (vitest)
```

## API (Phase 1)
- `POST /api/v1/auth/register` — tạo tài khoản
- `POST /api/v1/auth/login` — lấy token
- `GET  /api/v1/auth/me` — thông tin user
- `GET  /api/v1/projects` — danh sách project
- `POST /api/v1/projects` — tạo project (hỗ trợ header `Idempotency-Key`)
- `GET  /api/v1/projects/{id}` — chi tiết project + pipeline jobs
- `GET  /api/v1/projects/{id}/jobs` — danh sách jobs
- `GET  /api/v1/jobs/{id}` — trạng thái job
- `GET  /health` — health check

## API (Phase 2 — pipeline nghiên cứu)
- `POST /api/v1/movies/research` — nghiên cứu phim (title + năm) → Movie, mặc định provider `offline`
- `POST /api/v1/opportunities/score` — chấm điểm cơ hội (weighted) cho movie
- `POST /api/v1/content/angles` — sinh góc nội dung (CP1), thay thế góc cũ của movie
- `GET  /api/v1/movies/{id}` — chi tiết movie: sources, research, score, angles, scripts
- Provider thật (TMDB/LLM/web search) cắm qua `.env`: `RESEARCH_PROVIDER`/`OPPORTUNITY_PROVIDER`/`ANGLE_PROVIDER` + keys

## API (Phase 3 — kịch bản, giọng đọc, timestamps)
- `POST /api/v1/scripts/generate` — viết kịch bản (HOOK→THESIS→…→CTA, CP2), version mỗi lần chạy
- `GET  /api/v1/scripts/{id}` — chi tiết script: segments, voice mới nhất, timeline, visual plan, assets, copyright reviews
- `POST /api/v1/voice/generate` — TTS theo voice profile (license gate thương mại); tự tạo profile mặc định
- `POST /api/v1/timeline/build` — căn từng segment theo timestamps của voice (chuẩn bị cho Visual Planner Phase 4)
- Provider thật (TTS) cắm qua `.env`: `SCRIPT_PROVIDER`/`VOICE_PROVIDER`/`TIMELINE_PROVIDER` + keys

## API (Phase 4 — visual plan, assets, copyright gate)
- `POST /api/v1/visual/plan` — sinh visual plan (9 segments, deterministic planner) từ script segments
- `POST /api/v1/assets/generate` — tạo asset placeholder (CC0 hoặc theo source hint) cho mọi segment
- `POST /api/v1/assets/search` — tương tự generate nhưng dùng source hint `licensed_stock`
- `POST /api/v1/copyright/evaluate` — đánh giá bản quyền: 3-second rule, commercial_use gate, risk scoring
- Provider cắm qua `.env`: `VISUAL_PROVIDER`/`ASSET_PROVIDER`/`COPYRIGHT_PROVIDER` + `ASSET_SOURCE_HINT`

## API (Phase 6 — YouTube private upload → approval → publish)
- `POST /api/v1/youtube/upload` — upload Private (precondition: Final QA pass + render + subtitle)
- `POST /api/v1/youtube/approve` — checkpoint CP6: `approved=true` → `ready_to_publish`; `false` → `rejected`
- `POST /api/v1/youtube/publish` — public/schedule (bắt buộc đã duyệt CP6); `publish_at` → `scheduled`
- `GET  /api/v1/youtube/publications/{id}` — trạng thái publication
- Provider cắm qua `.env`: `YOUTUBE_PROVIDER` (mặc định `offline`, giả lập video id deterministic)

## Nguyên tắc bảo mật
- Không commit secrets. Tạo `SECRET_KEY` mạnh khi deploy.
- `Idempotency-Key` giúp retry an toàn (job không chạy trùng).