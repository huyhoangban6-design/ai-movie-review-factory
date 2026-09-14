import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { apiFetch } from '../api'
import { formatDate } from '../format'

export default function DashboardView() {
  const navigate = useNavigate()
  const [projects, setProjects] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [creating, setCreating] = useState(false)
  const [form, setForm] = useState({ title: '', description: '', maxCost: '' })
  const [research, setResearch] = useState({ title: '', year: '' })
  const [researching, setResearching] = useState(false)

  const load = useCallback(async () => {
    try {
      const data = await apiFetch('/api/v1/projects')
      setProjects(data)
      setError('')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  async function onSubmit(e) {
    e.preventDefault()
    setCreating(true)
    setError('')
    try {
      await apiFetch('/api/v1/projects', {
        method: 'POST',
        body: {
          title: form.title.trim(),
          description: form.description.trim() || null,
          max_cost_per_video: form.maxCost ? Number(form.maxCost) : null,
        },
      })
      setForm({ title: '', description: '', maxCost: '' })
      await load()
    } catch (err) {
      setError(err.message)
    } finally {
      setCreating(false)
    }
  }

  async function onResearch(e) {
    e.preventDefault()
    setResearching(true)
    setError('')
    try {
      const data = await apiFetch('/api/v1/movies/research', {
        method: 'POST',
        body: {
          title: research.title.trim(),
          year: research.year ? Number(research.year) : null,
        },
      })
      setResearch({ title: '', year: '' })
      navigate(`/movies/${data.movie_id}`)
    } catch (err) {
      setError(err.message)
    } finally {
      setResearching(false)
    }
  }

  return (
    <div className="page">
      <section className="card">
        <h2>Nghiên cứu phim mới</h2>
        <form onSubmit={onResearch} className="form-grid">
          <label>
            Tên phim
            <input
              type="text"
              value={research.title}
              onChange={(e) => setResearch({ ...research, title: e.target.value })}
              placeholder="VD: Interstellar"
              required
              minLength={2}
            />
          </label>
          <label>
            Năm sản xuất (không bắt buộc)
            <input
              type="number"
              inputMode="numeric"
              min="1880"
              max="2100"
              value={research.year}
              onChange={(e) => setResearch({ ...research, year: e.target.value })}
              placeholder="VD: 2014"
            />
          </label>
          <button className="btn btn-primary" type="submit" disabled={researching}>
            {researching ? 'Đang nghiên cứu…' : 'Nghiên cứu'}
          </button>
        </form>
      </section>

      <section className="card create-card">
        <h2>Project mới</h2>
        <form onSubmit={onSubmit} className="form-grid">
          <label>
            Tên phim / dự án
            <input
              type="text"
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
              placeholder="VD: Inception Review"
              required
              minLength={2}
            />
          </label>
          <label>
            Mô tả (không bắt buộc)
            <input
              type="text"
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              placeholder="Ý tưởng sơ bộ…"
            />
          </label>
          <label>
            Ngân sách tối đa / video (USD, không bắt buộc)
            <input
              type="number"
              inputMode="decimal"
              min="0"
              step="0.01"
              value={form.maxCost}
              onChange={(e) => setForm({ ...form, maxCost: e.target.value })}
              placeholder="VD: 15"
            />
          </label>
          <button className="btn btn-primary" type="submit" disabled={creating}>
            {creating ? 'Đang tạo…' : 'Tạo project'}
          </button>
        </form>
      </section>

      {error && <div className="error-banner">{error}</div>}

      <section>
        <h2 className="section-title">Projects của bạn</h2>
        {loading ? (
          <div className="muted">Đang tải…</div>
        ) : projects.length === 0 ? (
          <div className="card muted">Chưa có project nào. Tạo project đầu tiên ở trên.</div>
        ) : (
          <ul className="project-list">
            {projects.map((p) => (
              <li key={p.id}>
                <Link to={`/projects/${p.id}`} className="card project-link">
                  <div>
                    <div className="project-title">{p.title}</div>
                    <div className="muted small">
                      Trạng thái: {p.status || 'draft'} · Tạo {formatDate(p.created_at)}
                    </div>
                  </div>
                  <span className="chevron">›</span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}