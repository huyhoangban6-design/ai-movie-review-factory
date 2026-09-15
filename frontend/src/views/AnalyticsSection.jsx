import { useCallback, useEffect, useState } from 'react'
import { apiFetch } from '../api'
import { formatNumber, formatPercent, formatDuration } from '../format'

const WEIGHT_LABEL = {
  demand: 'Nhu cầu',
  trend: 'Xu hướng',
  audience_fit: 'Khớp khán giả',
  evergreen: 'Tính dài lâu',
  competition: 'Cạnh tranh',
  difficulty: 'Độ khó',
}

const TRAFFIC_LABEL = {
  search: 'Tìm kiếm',
  suggested: 'Gợi ý',
  browse: 'Duyệt kênh',
  external: 'Ngoài YouTube',
  shorts_other: 'Shorts/khác',
}

const STATUS_NOTE = {
  proposed: 'Đề xuất',
  active: 'Đang áp dụng',
  archived: 'Đã lưu trữ',
}

export default function AnalyticsSection({ movieId, publicationId }) {
  const [summary, setSummary] = useState(null)
  const [strategy, setStrategy] = useState(null)
  const [experiments, setExperiments] = useState([])
  const [insights, setInsights] = useState([])
  const [competitors, setCompetitors] = useState(null)
  const [video, setVideo] = useState(null)
  const [busy, setBusy] = useState({ refresh: false, research: false, learn: false, activate: 0 })
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    try {
      const [s, st, ex, insightsData, comps, v] = await Promise.all([
        apiFetch('/api/v1/analytics/summary'),
        apiFetch('/api/v1/analytics/strategy'),
        apiFetch('/api/v1/analytics/experiments'),
        apiFetch('/api/v1/analytics/insights'),
        movieId
          ? apiFetch(`/api/v1/analytics/competitors?movie_id=${movieId}`).catch(() => null)
          : Promise.resolve(null),
        publicationId
          ? apiFetch(`/api/v1/analytics/video/${publicationId}`).catch(() => null)
          : Promise.resolve(null),
      ])
      setSummary(s)
      setStrategy(st)
      setExperiments(ex)
      setInsights(insightsData)
      setCompetitors(comps)
      setVideo(v)
      setError('')
    } catch (err) {
      setError(err.message)
    }
  }, [movieId, publicationId])

  useEffect(() => { load() }, [load])

  function run(key, fn, then) {
    setBusy(b => ({ ...b, [key]: true }))
    setError('')
    Promise.resolve()
      .then(fn)
      .then(() => load())
      .then(then)
      .catch(err => setError(err.message))
      .finally(() => setBusy(b => ({ ...b, [key]: false })))
  }

  function onRefresh() {
    if (!publicationId) return
    run('refresh', () => apiFetch(`/api/v1/analytics/video/${publicationId}/refresh`, { method: 'POST', body: {} }))
  }
  function onResearch() {
    if (!movieId) return
    run('research', () =>
      apiFetch('/api/v1/analytics/competitors/research', { method: 'POST', body: { movie_id: movieId } }),
    )
  }
  function onLearn() {
    run('learn', () => apiFetch('/api/v1/analytics/learn', { method: 'POST', body: {} }))
  }
  function onActivate(experimentId) {
    run('activate', () =>
      apiFetch(`/api/v1/analytics/experiments/${experimentId}/activate`, { method: 'POST' }),
    )
  }

  const metrics = video?.metrics || null
  const total = summary || {}

  return (
    <section className='card'>
      <h2>Analytics & vòng học hỏi</h2>

      <div className='pipeline-grid'>
        <button className='btn btn-primary' disabled={busy.refresh || !publicationId} onClick={onRefresh}>
          {busy.refresh ? 'Đang kéo metrics…' : 'Kéo metrics video'}
        </button>
        <button className='btn btn-primary' disabled={busy.research || !movieId} onClick={onResearch}>
          {busy.research ? 'Đang nghiên cứu…' : 'Nghiên cứu đối thủ'}
        </button>
        <button className='btn btn-primary' disabled={busy.learn} onClick={onLearn}>
          {busy.learn ? 'Đang học hỏi…' : 'Chạy học hỏi'}
        </button>
      </div>
      {error && <div className='error-banner' style={{ marginTop: '0.5rem' }}>{error}</div>}

      <div className='analytics-grid'>
        <div className='analytics-cols'>
          <h3>Tổng kênh</h3>
          <div className='metric-grid'>
            <div className='metric-card'>
              <div className='metric-value'>{total.video_count ?? '—'}</div>
              <div className='metric-label'>Video đo</div>
            </div>
            <div className='metric-card'>
              <div className='metric-value'>{formatNumber(total.total_views)}</div>
              <div className='metric-label'>Tổng views</div>
            </div>
            <div className='metric-card'>
              <div className='metric-value'>{formatPercent(total.avg_ctr_pct)}</div>
              <div className='metric-label'>CTR trung bình</div>
            </div>
            <div className='metric-card'>
              <div className='metric-value'>{formatNumber(total.total_watch_time_hours)}h</div>
              <div className='metric-label'>Watch time</div>
            </div>
            <div className='metric-card'>
              <div className='metric-value'>${formatNumber(total.total_revenue_usd)}</div>
              <div className='metric-label'>Doanh thu</div>
            </div>
          </div>

          <h3>Chiến lược đang áp dụng</h3>
          {strategy ? (
            <div className='strategy-box'>
              <div className='kv'>
                <div className='muted small'>
                  <span className='badge badge-succeeded'>{strategy.strategy_version}</span>{' '}
                  {strategy.source === 'experiment' ? `Từ experiment #${strategy.experiment_id}` : 'Mặc định (v1)'} ·
                  áp dụng cho opportunity scoring
                </div>
                {Object.entries(strategy.weights).map(([k, w]) => (
                  <div key={k} className='weight-row'>
                    <span className='muted small'>{WEIGHT_LABEL[k] || k}</span>
                    <span className='weight-bar'><span style={{ width: `${Math.round(w * 100)}%` }} /></span>
                    <span className='muted small strong'>{Math.round(w * 100)}%</span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className='muted'>Chưa tải được chiến lược.</div>
          )}
        </div>

        <div className='analytics-cols'>
          <h3>Metrics video gần nhất</h3>
          {metrics ? (
            <div>
              <div className='muted small' style={{ marginBottom: '0.5rem' }}>
                {video.title} · {video.video_id} · nguồn {video.source === 'derived' ? 'ước tính (chưa refresh)' : 'đã lưu'}
              </div>
              <div className='metric-grid'>
                <div className='metric-card'><div className='metric-value'>{formatNumber(metrics.views)}</div><div className='metric-label'>Views</div></div>
                <div className='metric-card'><div className='metric-value'>{formatNumber(metrics.likes)}</div><div className='metric-label'>Likes</div></div>
                <div className='metric-card'><div className='metric-value'>{formatNumber(metrics.comments)}</div><div className='metric-label'>Comments</div></div>
                <div className='metric-card'><div className='metric-value'>{formatPercent(metrics.ctr_pct)}</div><div className='metric-label'>CTR</div></div>
                <div className='metric-card'><div className='metric-value'>{formatPercent(metrics.retention_avg_pct)}</div><div className='metric-label'>Retention</div></div>
                <div className='metric-card'><div className='metric-value'>{formatDuration(metrics.avg_view_duration_s)}</div><div className='metric-label'>Xem TB</div></div>
                <div className='metric-card'><div className='metric-value'>{formatNumber(metrics.watch_time_hours)}h</div><div className='metric-label'>Watch time</div></div>
                <div className='metric-card'><div className='metric-value'>${formatNumber(metrics.revenue_usd)}</div><div className='metric-label'>Doanh thu</div></div>
                <div className='metric-card'><div className='metric-value'>${metrics.rpm_usd ?? '—'}</div><div className='metric-label'>RPM</div></div>
              </div>
              {metrics.traffic_sources && (
                <ul className='traffic-list'>
                  {Object.entries(metrics.traffic_sources).map(([k, v]) => (
                    <li key={k} className='timeline-item'>
                      <span className='strong'>{TRAFFIC_LABEL[k] || k}</span>
                      <span className='muted small' style={{ marginLeft: 'auto' }}>{formatPercent(v)}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          ) : (
            <div className='muted'>Chưa có video xuất bản để đo. Sau khi publish hãy bấm “Kéo metrics video”.</div>
          )}

          <h3>Insights từ learning (Phase 7)</h3>
          {insights.length ? (
            <ul className='timeline-list'>
              {insights.map((ins, i) => (
                <li key={i} className='timeline-item'>
                  <span className='badge badge-small badge-pending'>{ins.category}</span>
                  <div>
                    <div className='strong'>{ins.insight}</div>
                    {ins.suggestion && <div className='muted small'>{ins.suggestion}</div>}
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <div className='muted'>Chưa có insights. Chạy “Học hỏi” sau khi có metrics.</div>
          )}
        </div>
      </div>

      <h3>Experiments (calibration trọng số)</h3>
      {experiments.length ? (
        <ul className='timeline-list'>
          {experiments.map(exp => (
            <li key={exp.id} className='timeline-item'>
              <span className={`badge badge-small ${exp.status === 'active' ? 'badge-succeeded' : 'badge-pending'}`}>{STATUS_NOTE[exp.status] || exp.status}</span>
              <div>
                <div className='strong'>{exp.name} <span className='muted small'>{exp.strategy_version}</span></div>
                {exp.weights && (
                  <div className='muted small'>
                    {Object.entries(exp.weights).map(([k, w]) => `${WEIGHT_LABEL[k] || k} ${Math.round(w * 100)}%`).join(' · ')}
                  </div>
                )}
              </div>
              {exp.status !== 'active' && (
                <button className='btn btn-primary btn-small' disabled={busy.activate === exp.id} onClick={() => onActivate(exp.id)} style={{ marginLeft: 'auto' }}>
                  {busy.activate === exp.id ? 'Đang kích hoạt…' : 'Kích hoạt'}
                </button>
              )}
            </li>
          ))}
        </ul>
      ) : (
        <div className='muted'>Chưa có experiment. Chạy “Học hỏi” để sinh đề xuất v2.</div>
      )}

      <h3>Đối thủ cùng phim</h3>
      {competitors?.competitors?.length ? (
        <ul className='timeline-list'>
          {competitors.competitors.map(comp => (
            <li key={comp.id} className='timeline-item'>
              <span className='badge badge-small'>{comp.influence ?? '—'}</span>
              <div>
                <div className='strong'>{comp.channel} <span className='muted small'>{comp.genre}</span></div>
                {comp.videos?.length > 0 && (
                  <div className='muted small'>
                    Video tham khảo: {formatNumber(comp.videos[0].view_count)} views
                    {comp.videos[0].retrieval_url ? (<span> · <a href={comp.videos[0].retrieval_url} target='_blank' rel='noreferrer'>tìm trên YT</a></span>) : ''}
                  </div>
                )}
              </div>
            </li>
          ))}
        </ul>
      ) : (
        <div className='muted'>Chưa có dữ liệu đối thủ. Bấm “Nghiên cứu đối thủ”.</div>
      )}
    </section>
  )
}