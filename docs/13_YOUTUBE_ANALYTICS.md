# YouTube Publishing & Analytics

Publishing:
Approved package → upload Private → check → Schedule/Public sau human approval.

Analytics:
CTR
Views
Watch time
Average view duration
Retention
Subscribers
Likes
Comments
Revenue
Traffic source

Learning loop:
metrics → insights → strategy version → opportunity/angle/script/hook library updates.

Implementation note (Phase 7):
- `GET /analytics/video/{id}` (docs/04) triển khai với `id` = `publication_id` (id hệ thống; `youtube_video_id` có trong response). Trả snapshot `stored` gần nhất; chưa có snapshot thì tính deterministic `derived` read-only.
- Metric tham số: views/impressions/clicks → `ctr_pct = clicks/impressions*100`; retention curve 12 điểm; `watch_time_hours`; revenue từ `views/1000*rpm_usd`. Provider offline deterministic (cùng input → cùng số) để test.
- Calibration: weighted opportunity score nhận bộ trọng số từ active `Experiment` (chiếm ưu thế so với v1 mặc định); `analytics_insights` đẩy đề xuất sửa hook/script.
