# PROGRESS.md

Nhật ký trạng thái dự án AI Movie Review Factory. Cập nhật sau mỗi phase.

## Tổng quan
| Phase | Nội dung | Trạng thái |
|---|---|---|
| 0 | Docs thiết kế (00–15) | ✅ Hoàn tất |
| 1 | Skeleton + DB + auth + dashboard | 🚧 Đang triển khai (xem bên dưới) |
| 2 | Movie research → opportunity → angle | ⬜ Chưa bắt đầu |
| 3 | Script → voice → timestamps | ⬜ Chưa bắt đầu |
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

## Phase 1 — còn thiếu / lưu ý
- Môi trường sandbox hiện tại **không có pip/node/docker**, nên:
  - Backend mới được syntax-check bằng `compileall` (OK); **chưa chạy `pytest` hay import toàn app**.
  - Frontend chưa chạy `npm install` / `npm run build` / `vitest`.
  → Cần người dùng chạy local theo README (hoặc Docker) để xác nhận test pass.
- Chưa có email verification, reset password (ngoài MVP Phase 1).
- Worker/queue (Redis) mới là scaffold — job `movie_research` đang dừng ở trạng thái `pending` cho tới Phase 2/3.
- Rate limit auth đang dùng bộ nhớ trong-memory (dự kiến chuyển Redis Phase 8).

## Manual setup cần người dùng
1. Copy `.env.example` → `.env`, đặt `SECRET_KEY` mạnh.
2. Cài Python 3.12 + Node 20, hoặc Docker.
3. Chạy migration rồi khởi động theo README.