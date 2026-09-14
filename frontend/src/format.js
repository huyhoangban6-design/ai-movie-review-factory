export function formatDate(value) {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return value
  const now = Date.now()
  const diff = now - d.getTime()
  if (diff < 60_000) return 'vừa xong'
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)} phút trước`
  if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)} giờ trước`
  return d.toLocaleString('vi-VN', { dateStyle: 'short', timeStyle: 'short' })
}

export function formatDuration(seconds) {
  if (seconds == null || Number.isNaN(seconds)) return '—'
  const total = Math.round(seconds)
  const m = Math.floor(total / 60)
  const s = total % 60
  return m > 0 ? `${m}:${String(s).padStart(2, '0')}` : `${s}s`
}

export const SCRIPT_SECTION_LABEL = {
  hook: 'Hook (mở hấp dẫn)',
  thesis: 'Luận điểm chính',
  context: 'Bối cảnh phim',
  analysis: 'Phân tích',
  evidence: 'Bằng chứng / ví dụ',
  character_theme: 'Nhân vật & chủ đề',
  critique: 'Phê bình',
  conclusion: 'Kết luận',
  cta: 'Kêu gọi hành động',
}

export const STATUS_LABEL = {
  pending: 'Chờ xử lý',
  running: 'Đang chạy',
  succeeded: 'Thành công',
  failed: 'Thất bại',
  cancelled: 'Đã huỷ',
}

export const JOB_TYPE_LABEL = {
  movie_research: 'Nghiên cứu phim',
  opportunity_score: 'Điểm cơ hội',
  content_angle: 'Góc nội dung',
  script: 'Kịch bản',
  voice: 'Giọng đọc',
  timeline: 'Timeline',
  assets: 'Assets',
  copyright: 'Bản quyền',
  render: 'Render',
  qa: 'QA',
  upload: 'Upload',
  publish: 'Xuất bản',
}