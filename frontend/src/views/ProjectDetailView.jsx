import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { apiFetch } from '../api'
import { formatDate, formatUsd, JOB_TYPE_LABEL, STATUS_LABEL } from '../format'

const COST_MODE_LABEL = {
  free: 'Tiết kiệm',
  balanced: 'Cân bằng',
  premium: 'Cao cấp',
}

export default function ProjectDetailView() {
  const { id } = useParams()
  const [project, setProject] = useState(null)
  const [cost, setCost] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [saveMsg, setSaveMsg] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await apiFetch(`/api/v1/projects/${id}`)
      setProject(data)
      setError('')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [id])

  const loadCost = useCallback(async () => {
    try {
      const data = await apiFetch(`/api/v1/projects/${id}/cost`)
      setCost(data)
    } catch {
      setCost(null)
    }
  }, [id])

  useEffect(() => {
    load()
    loadCost()
  }, [load, loadCost])

  const onSaveBudget = async (e) => {
    e.preventDefault()
    const form = new FormData(e.currentTarget)
    try {
      await apiFetch(`/api/v1/projects/${id}/budget`, {
        method: 'PATCH',
        body: {
          max_cost_per_video: form.get('max_cost')
            ? Number(form.get('max_cost'))
            : null,
          cost_mode: form.get('cost_mode'),
        },
      })
      setSaveMsg('Đã lưu ngân sách.')
      await load()
      await loadCost()
    } catch (err) {
      setSaveMsg(err.message)
    }
  }

  if (loading) return <div className="muted">Đang tải…</div>
  if (!project) return <div className="error-banner">{error}</div>

  const lastJob = project.jobs?.find((j) => j.status !== 'pending') || project.jobs?.[0]
  const budgetPct = cost && cost.budget_percent_used != null ? Math.min(cost.budget_percent_used, 100) : null

  return (
    <div className="page">
      <Link to="/" className="back-link">← Quay lại danh sách</Link>
      <section className="card">
        <div className="project-head">
          <div>
            <h1>{project.title}</h1>
            {project.description && <p className="muted">{project.description}</p>}
          </div>
          <span className="badge">{project.status}</span>
        </div>
        <div className="kv">
          <div>
            <span className="muted small">Ngân sách tối đa/video:</span> {project.max_cost_per_video ?? '—'} USD
          </div>
          <div>
            <span className="muted small">Chế độ chi phí:</span> {COST_MODE_LABEL[project.cost_mode] || project.cost_mode}
          </div>
          <div>
            <span className="muted small">Tạo lúc:</span> {formatDate(project.created_at)}
          </div>
        </div>
      </section>

      {cost && (
        <section className="card">
          <div className="row-between">
            <h2>Chi phí &amp; ngân sách</h2>
            <span className={`badge badge-${cost.alerts?.length ? 'failed' : 'succeeded'}`}>
              {cost.alerts?.length ? `Cảnh báo ${cost.alerts.length}` : 'Trong ngân sách'}
            </span>
          </div>

          <div className="kv">
            <div>
              <span className="muted small">Tổng chi tiêu (USD):</span>{' '}
              <span className="strong">{formatUsd(cost.total_actual_usd)}</span>
            </div>
            {cost.max_cost_per_video != null && (
              <>
                <div>
                  <span className="muted small">Ngân sách còn lại:</span> {formatUsd(cost.remaining_budget)}
                </div>
                <div>
                  <span className="muted small">Đã dùng:</span> {cost.budget_percent_used}%
                </div>
              </>
            )}
            <div>
              <span className="muted small">Theo nhà cung cấp:</span>{' '}
              {Object.entries(cost.per_provider || {}).length
                ? Object.entries(cost.per_provider)
                    .map(([p, v]) => `${p}: ${formatUsd(v)}`)
                    .join(' · ')
                : 'chưa có'}
            </div>
            <div>
              <span className="muted small">Theo hạng mục:</span>{' '}
              {Object.entries(cost.per_category || {}).length
                ? Object.entries(cost.per_category)
                    .sort((a, b) => b[1] - a[1])
                    .map(([c, v]) => `${c}: ${formatUsd(v)}`)
                    .join(' · ')
                : 'chưa có'}
            </div>
          </div>

          {budgetPct != null && (
            <div className="budget-bar">
              <div className="budget-fill" style={{ width: `${budgetPct}%` }} />
            </div>
          )}

          {cost.alerts?.length > 0 && (
            <ul className="alert-list">
              {cost.alerts.map((a) => (
                <li key={a} className="job-error">
                  {a}
                </li>
              ))}
            </ul>
          )}

          <form className="budget-form" onSubmit={onSaveBudget}>
            <label>
              Ngân sách tối đa/video (USD)
              <input
                name="max_cost"
                type="number"
                min="0"
                step="0.01"
                defaultValue={project.max_cost_per_video ?? ''}
                placeholder="Không giới hạn"
              />
            </label>
            <label>
              Chế độ chi phí
              <select name="cost_mode" defaultValue={project.cost_mode || 'balanced'}>
                {Object.entries(COST_MODE_LABEL).map(([v, l]) => (
                  <option key={v} value={v}>{l}</option>
                ))}
              </select>
            </label>
            <button className="btn btn-sm" type="submit">Lưu ngân sách</button>
            {saveMsg && <span className="muted small">{saveMsg}</span>}
          </form>
        </section>
      )}

      {lastJob && (
        <section className="card">
          <h2>Công việc mới nhất</h2>
          <div className="job-row">
            <div>
              <div className="strong">{JOB_TYPE_LABEL[lastJob.job_type] || lastJob.job_type}</div>
              <div className="muted small">{formatDate(lastJob.created_at)}</div>
            </div>
            <span className={`badge badge-${lastJob.status}`}>
              {STATUS_LABEL[lastJob.status] || lastJob.status}
            </span>
          </div>
          {lastJob.error_message && (
            <details className="job-error">
              <summary>Chi tiết lỗi</summary>
              <pre>{lastJob.error_message}</pre>
            </details>
          )}
        </section>
      )}

      <section className="card">
        <div className="row-between">
          <h2>Pipeline</h2>
          <button className="btn btn-ghost btn-sm" type="button" onClick={() => load()}>
            Làm mới
          </button>
        </div>
        {project.jobs?.length ? (
          <ul className="job-list">
            {project.jobs.map((job) => (
              <li key={job.id} className={`job-line job-${job.status}`}>
                <div>
                  <div className="strong">{JOB_TYPE_LABEL[job.job_type] || job.job_type}</div>
                  <div className="muted small">
                    ID {job.id} · {formatDate(job.created_at)}
                    {job.retry_count > 0 && ` · retry ${job.retry_count}`}
                  </div>
                </div>
                <span className={`badge badge-${job.status}`}>
                  {STATUS_LABEL[job.status] || job.status}
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <div className="muted">Project chưa có job nào.</div>
        )}
      </section>
    </div>
  )
}