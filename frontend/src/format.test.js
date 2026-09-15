import { describe, expect, it } from 'vitest'
import { formatDate, formatNumber, formatPercent, STATUS_LABEL, JOB_TYPE_LABEL } from './format'

describe('format', () => {
  it('trả về placeholder khi thiếu giá trị', () => {
    expect(formatDate(null)).toBe('—')
    expect(formatDate('')).toBe('—')
    expect(formatNumber(null)).toBe('—')
    expect(formatNumber(Number.NaN)).toBe('—')
    expect(formatPercent(null)).toBe('—')
  })

  it('định dạng số comp/compact', () => {
    expect(formatNumber(0)).toBe('0')
    expect(formatNumber(999)).toBe('999')
    expect(formatNumber(2_400)).toBe('2.4K')
    expect(formatNumber(3_000)).toBe('3K')
    expect(formatNumber(1_234_567)).toBe('1.2M')
  })

  it('định dạng phần trăm', () => {
    expect(formatPercent(4.56)).toBe('4.6%')
  })

  it('định dạng thời gian hợp lệ', () => {
    expect(formatDate(new Date().toISOString())).toMatch(/vừa xong|phút trước|giờ trước/)
  })

  it('chứa enum status và job type cơ bản', () => {
    expect(STATUS_LABEL.pending).toBe('Chờ xử lý')
    expect(STATUS_LABEL.failed).toBe('Thất bại')
    expect(JOB_TYPE_LABEL.render).toBe('Render')
    expect(JOB_TYPE_LABEL.qa).toBe('QA')
    expect(JOB_TYPE_LABEL.analytics).toBe('Analytics')
    expect(JOB_TYPE_LABEL.learn).toBe('Học hỏi')
  })
})