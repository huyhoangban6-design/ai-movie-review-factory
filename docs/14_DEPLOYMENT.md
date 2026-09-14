# Deployment

Local development:
Docker Compose cho frontend/backend/PostgreSQL/Redis.

Production:
Cloud app server + PostgreSQL + Redis + S3-compatible storage.
GPU worker on-demand/serverless cho job nặng.
Render worker có thể chạy riêng.

Secrets:
.env / secret manager.
Không commit secrets.

Monitoring:
structured logs, job status, retries, error alerts, cost tracking.

Nguyên tắc:
scale GPU về 0 khi không có job nếu hạ tầng hỗ trợ.
