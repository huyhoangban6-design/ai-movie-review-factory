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