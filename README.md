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
- `GET  /api/v1/movies/{id}` — chi tiết movie: sources, research, score, angles
- Provider thật (TMDB/LLM/web search) cắm qua `.env`: `RESEARCH_PROVIDER`/`OPPORTUNITY_PROVIDER`/`ANGLE_PROVIDER` + keys

## Nguyên tắc bảo mật
- Không commit secrets. Tạo `SECRET_KEY` mạnh khi deploy.
- `Idempotency-Key` giúp retry an toàn (job không chạy trùng).