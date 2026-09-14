import { describe, expect, it } from 'vitest'
import { formatDate, STATUS_LABEL, JOB_TYPE_LABEL } from './format'

describe('format', () => {
  it('trả về placeholder khi thiếu giá trị', () => {
    expect(formatDate(null)).toBe('—')
    expect(formatDate('')).toBe('—')
  })

  it('định dạng thời gian hợp lệ', () => {
    expect(formatDate(new Date().toISOString())).toMatch(/vừa xong|phút trước|giờ trước/)
  })

  it('chứa enum status và job type cơ bản', () => {
    expect(STATUS_LABEL.pending).toBe('Chờ xử lý')
    expect(STATUS_LABEL.failed).toBe('Thất bại')
    expect(JOB_TYPE_LABEL.render).toBe('Render')
    expect(JOB_TYPE_LABEL.qa).toBe('QA')
  })
})