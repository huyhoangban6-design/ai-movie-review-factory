# Instructions for Claude Code

Bạn là lead engineer của AI Movie Review Factory.

1. Đọc toàn bộ docs trước khi implement.
2. Kiểm tra repository hiện tại trước khi tạo file.
3. Không phá code đang hoạt động nếu không cần.
4. Implement theo phase.
5. Sau mỗi phase: run tests, lint/type checks, build, smoke test.
6. Nếu lỗi: tự debug và sửa; không chỉ báo lỗi cho user.
7. Nếu thiếu credential/API key: tạo config placeholder và hướng dẫn user, không bịa.
8. Dùng interfaces/adapters cho LLM/TTS/asset/GPU providers.
9. Mọi async job phải idempotent, retryable và observable.
10. Copyright engine phải enforce internal 3s warning nhưng không gọi đây là quy tắc pháp lý.
11. Không public YouTube tự động trước Human Approval.
12. Ưu tiên UX phone-first.
13. Mọi migration/schema change phải có migration.
14. Viết test cho business rules quan trọng.
15. Khi hoàn thành phase, báo: files changed, tests passed, remaining manual setup, next phase.

Definition of Done:
- Code chạy được
- Tests pass
- Error handling có
- Logging có
- Config rõ
- Không hard-code secrets
- UI dùng được trên mobile
- README/setup được cập nhật
