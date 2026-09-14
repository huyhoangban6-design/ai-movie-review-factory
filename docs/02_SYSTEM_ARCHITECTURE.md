# System Architecture

## Layers
1. Phone Control Center
2. Intelligence
3. Content
4. Production
5. Safety/QA
6. Growth/Analytics

## Suggested stack
Frontend: responsive PWA
Backend: Python + FastAPI
Database: PostgreSQL
Queue: Redis + worker system
Storage: S3-compatible
AI: configurable LLM/TTS/image/vision providers
Speech recognition: Whisper
Video: FFmpeg + Python
Deployment: Docker + cloud server + optional serverless GPU

## Project tree
frontend/
backend/
services/
workers/
database/
storage/
docker/
tests/
docs/

Services:
movie-research, opportunity-engine, content-engine, voice-manager,
visual-engine, copyright-engine, video-engine, subtitle-engine,
qa-engine, publishing-engine, analytics-engine, cost-engine.

Phone chỉ là control UI; AI/render nặng chạy cloud.
