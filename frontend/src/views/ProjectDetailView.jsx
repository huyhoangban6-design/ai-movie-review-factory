import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { apiFetch } from '../api'
import { formatDate, JOB_TYPE_LABEL, STATUS_LABEL } from '../format'

export default function ProjectDetailView() {
  const { id } = useParams()
  const [project, setProject] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
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

  useEffect(() => {
    load()
  }, [load])

  if (loading) return <div className="muted">Đang tải…</div>
  if (!project) return <div className="error-banner">{error}</div>

  const lastJob = project.jobs?.find((j) => j.status !== 'pending') || project.jobs?.[0]

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
            <span className="muted small">Tạo lúc:</span> {formatDate(project.created_at)}
          </div>
        </div>
      </section>

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