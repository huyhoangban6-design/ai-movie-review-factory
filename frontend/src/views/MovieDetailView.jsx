import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { apiFetch } from '../api'
import { formatDate } from '../format'

export default function MovieDetailView() {
  const { id } = useParams()
  const [movie, setMovie] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    try {
      const data = await apiFetch(`/api/v1/movies/${id}`)
      setMovie(data)
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
  if (!movie) return <div className="error-banner">{error}</div>

  return (
    <div className="page">
      <Link to="/" className="back-link">← Quay lại dashboard</Link>

      <section className="card">
        <div className="project-head">
          <div>
            <h1>{movie.title} <span className="muted small">{movie.year ? `(${movie.year})` : ''}</span></h1>
            {movie.director && <p className="muted">Đạo diễn: {movie.director}</p>}
            {movie.genres?.length > 0 && (
              <p className="muted">Thể loại: {movie.genres.join(', ')}</p>
            )}
          </div>
          <span className="badge badge-succeeded">{movie.status}</span>
        </div>
        {movie.synopsis && <p className="muted">{movie.synopsis}</p>}
      </section>

      {movie.opportunity && (
        <section className="card">
          <h2>Điểm cơ hội</h2>
          <div className="score-big">{movie.opportunity.overall}</div>
          <div className="kv">
            <div className="muted small">Demand {movie.opportunity.sub_scores?.demand} · Competition {movie.opportunity.sub_scores?.competition}</div>
            <div className="muted small">Trend {movie.opportunity.sub_scores?.trend} · Audience fit {movie.opportunity.sub_scores?.audience_fit}</div>
            <div className="muted small">Evergreen {movie.opportunity.sub_scores?.evergreen} · Difficulty {movie.opportunity.sub_scores?.difficulty}</div>
            <div className="muted small">Confidence {movie.opportunity.confidence} · {formatDate(movie.opportunity.created_at)}</div>
            {movie.opportunity.rationale && (
              <details>
                <summary className="small">Lý do chấm điểm</summary>
                <p className="muted small">{movie.opportunity.rationale}</p>
              </details>
            )}
          </div>
        </section>
      )}

      {movie.summaries?.length > 0 && (
        <section className="card">
          <h2>Tóm tắt nghiên cứu</h2>
          {movie.summaries.map((s, i) => (
            <p key={i} className="muted">{s}</p>
          ))}
        </section>
      )}

      <section className="card">
        <h2>Góc nội dung (CP1)</h2>
        {movie.angles?.length ? (
          <ul className="angle-list">
            {movie.angles.map((a, i) => (
              <li key={i} className="angle-item">
                <div className="strong">{a.title}</div>
                <div className="muted small">{a.hook}</div>
              </li>
            ))}
          </ul>
        ) : (
          <div className="muted">Chưa có góc nội dung.</div>
        )}
      </section>
    </div>
  )
}