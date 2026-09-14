# Database Schema

Core tables:
users, projects,
movies, movie_sources, movie_analysis,
opportunities, content_angles, competitors, competitor_videos,
research_sources, facts,
scripts, script_segments,
voice_profiles, voice_providers, voice_generations,
assets, asset_sources, copyright_reviews,
video_projects, video_timeline, render_jobs, subtitles, thumbnails,
metadata, published_videos, youtube_metrics,
experiments, analytics_insights, kpi_snapshots,
cost_records, system_logs.

Mỗi asset cần provenance/license/risk metadata.
Mỗi voice profile cần provider/model/language/style/speed/emotion/commercial_use/license_url/cloning_permission/status.
Mỗi job cần status, retry count, timestamps, error/log reference và idempotency key.
