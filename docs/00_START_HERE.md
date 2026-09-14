# AI Movie Review Factory — Claude Code Build Package

## Mục tiêu
Xây một ứng dụng web/PWA phone-first để vận hành kênh YouTube review phim bằng AI. Người dùng không cần biết code; Claude Code chịu trách nhiệm tạo, tích hợp, test và sửa code.

## Nguyên tắc làm việc
1. Đọc toàn bộ thư mục `docs/` trước khi code.
2. Không hỏi người dùng ghép code thủ công.
3. Build theo phase, sau mỗi phase phải chạy test và tự sửa lỗi.
4. Không tự bịa API key, credential, license hoặc giá dịch vụ.
5. Provider phải configurable qua environment/config.
6. Không chạy model/render nặng trên điện thoại.
7. Giữ mốc 3 giây như INTERNAL CONSERVATIVE RULE: clip >3.0s -> warning + Human Review; clip <=3.0s vẫn phải đánh giá rủi ro. Không tuyên bố 3 giây là safe harbor.
8. Không tự động public nếu chưa Final QA + Human Approval.
9. Mọi job có retry, logging, idempotency và trạng thái rõ ràng.
10. Ưu tiên kiến trúc modular để thay LLM/TTS/GPU/render provider.

## Thứ tự build
Phase 1: project skeleton + DB + auth + dashboard.
Phase 2: movie research → opportunity → angle.
Phase 3: script → voice → timestamps.
Phase 4: visual plan → assets → copyright gate.
Phase 5: FFmpeg render → subtitle → QA.
Phase 6: YouTube private upload → approval → publish.
Phase 7: analytics → experiments → learning.
Phase 8: cost engine + fallback + production hardening.

## Manual setup cần hướng dẫn người dùng
Khi cần credential, tạo `.env.example`, giải thích từng biến và dừng tại bước cần người dùng cung cấp key. Không yêu cầu họ chỉnh code.
