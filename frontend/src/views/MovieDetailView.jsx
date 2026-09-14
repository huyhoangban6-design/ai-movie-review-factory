import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { apiFetch } from '../api'
import { formatDate, formatDuration, SCRIPT_SECTION_LABEL } from '../format'

const SCORE_WEIGHTS = { demand: 0.25, trend: 0.20, audience_fit: 0.15, evergreen: 0.15, competition: 0.15, difficulty: 0.10 }

export default function MovieDetailView() {
  const { id } = useParams()
  const [movie, setMovie] = useState(null)
  const [scriptDetail, setScriptDetail] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState({ score: false, angles: false, script: false, voice: false, timeline: false, visualPlan: false, assets: false, copyright: false, render: false, subtitle: false, qa: false })

  const load = useCallback(async () => {
    try {
      const data = await apiFetch(`/api/v1/movies/${id}`)
      setMovie(data)
      setError('')
      // load latest script detail nếu có
      if (data.scripts?.length) {
        const latest = data.scripts[0]
        const sd = await apiFetch(`/api/v1/scripts/${latest.id}`)
        setScriptDetail(sd)
      } else {
        setScriptDetail(null)
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [id])

  const loadScript = useCallback(async (scriptId) => {
    if (!scriptId) { setScriptDetail(null); return }
    try {
      const sd = await apiFetch(`/api/v1/scripts/${scriptId}`)
      setScriptDetail(sd)
    } catch { /* ignore — movie load đã có scripts list */ }
  }, [])

  useEffect(() => { load() }, [load])

  async function withBusy(key, fn) {
    setBusy(b => ({ ...b, [key]: true }))
    setError('')
    try {
      await fn()
      await load()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(b => ({ ...b, [key]: false }))
    }
  }

  function onScore() { return withBusy('score', () => apiFetch('/api/v1/opportunities/score', { method: 'POST', body: { movie_id: movie.id } })) }
  function onAngles() { return withBusy('angles', () => apiFetch('/api/v1/content/angles', { method: 'POST', body: { movie_id: movie.id } })) }
  async function onScript() {
    setBusy(b => ({ ...b, script: true }))
    setError('')
    try {
      const data = await apiFetch('/api/v1/scripts/generate', { method: 'POST', body: { movie_id: movie.id } })
      await loadScript(data.script_id)
      await load()
    } catch (err) { setError(err.message) }
    finally { setBusy(b => ({ ...b, script: false })) }
  }
  async function onVoice() {
    if (!scriptDetail) return
    setBusy(b => ({ ...b, voice: true }))
    setError('')
    try {
      await apiFetch('/api/v1/voice/generate', { method: 'POST', body: { script_id: scriptDetail.id } })
      await loadScript(scriptDetail.id)
      await load()
    } catch (err) { setError(err.message) }
    finally { setBusy(b => ({ ...b, voice: false })) }
  }
  async function onTimeline() {
    if (!scriptDetail) return
    setBusy(b => ({ ...b, timeline: true }))
    setError('')
    try {
      await apiFetch('/api/v1/timeline/build', { method: 'POST', body: { script_id: scriptDetail.id } })
      await loadScript(scriptDetail.id)
      await load()
    } catch (err) { setError(err.message) }
    finally { setBusy(b => ({ ...b, timeline: false })) }
  }

  async function onVisualPlan() {
    if (!scriptDetail) return
    setBusy(b => ({ ...b, visualPlan: true }))
    setError('')
    try {
      await apiFetch('/api/v1/visual/plan', { method: 'POST', body: { script_id: scriptDetail.id } })
      await loadScript(scriptDetail.id)
      await load()
    } catch (err) { setError(err.message) }
    finally { setBusy(b => ({ ...b, visualPlan: false })) }
  }

  async function onAssets() {
    if (!scriptDetail?.visual_plan) return
    setBusy(b => ({ ...b, assets: true }))
    setError('')
    try {
      await apiFetch('/api/v1/assets/generate', { method: 'POST', body: { script_id: scriptDetail.id } })
      await loadScript(scriptDetail.id)
      await load()
    } catch (err) { setError(err.message) }
    finally { setBusy(b => ({ ...b, assets: false })) }
  }

  async function onCopyright() {
    if (!scriptDetail?.assets?.length) return
    setBusy(b => ({ ...b, copyright: true }))
    setError('')
    try {
      await apiFetch('/api/v1/copyright/evaluate', { method: 'POST', body: { script_id: scriptDetail.id } })
      await loadScript(scriptDetail.id)
      await load()
    } catch (err) { setError(err.message) }
    finally { setBusy(b => ({ ...b, copyright: false })) }
  }

  async function onRender() {
    if (!scriptDetail) return
    setBusy(b => ({ ...b, render: true }))
    setError('')
    try {
      await apiFetch('/api/v1/video/render', { method: 'POST', body: { script_id: scriptDetail.id } })
      await loadScript(scriptDetail.id)
      await load()
    } catch (err) { setError(err.message) }
    finally { setBusy(b => ({ ...b, render: false })) }
  }

  async function onSubtitle() {
    if (!scriptDetail) return
    setBusy(b => ({ ...b, subtitle: true }))
    setError('')
    try {
      await apiFetch('/api/v1/video/subtitle', { method: 'POST', body: { script_id: scriptDetail.id } })
      await loadScript(scriptDetail.id)
      await load()
    } catch (err) { setError(err.message) }
    finally { setBusy(b => ({ ...b, subtitle: false })) }
  }

  async function onQA() {
    if (!scriptDetail) return
    setBusy(b => ({ ...b, qa: true }))
    setError('')
    try {
      await apiFetch('/api/v1/video/qa', { method: 'POST', body: { script_id: scriptDetail.id } })
      await loadScript(scriptDetail.id)
      await load()
    } catch (err) { setError(err.message) }
    finally { setBusy(b => ({ ...b, qa: false })) }
  }

  if (loading) return <div className='muted'>Đang tải…</div>
  if (!movie) return <div className='error-banner'>{error || 'Không tìm thấy phim'}</div>

  return (
    <div className='page'>
      <Link to='/' className='back-link'>← Quay lại dashboard</Link>

      <section className='card'>
        <div className='project-head'>
          <div>
            <h1>{movie.title} <span className='muted small'>{movie.year ? `(${movie.year})` : ''}</span></h1>
            {movie.director && <p className='muted'>Đạo diễn: {movie.director}</p>}
            {movie.genres?.length > 0 && (
              <p className='muted'>Thể loại: {movie.genres.join(', ')}</p>
            )}
          </div>
          <span className='badge badge-succeeded'>{movie.status}</span>
        </div>
        {movie.synopsis && <p className='muted'>{movie.synopsis}</p>}
      </section>

      <section className='card'>
        <h2>Pipeline</h2>
        <div className='pipeline-grid'>
          <button className='btn btn-primary' disabled={busy.score || !!movie.opportunity} onClick={onScore}>
            {movie.opportunity ? `Điểm cơ hội: ${movie.opportunity.overall}` : busy.score ? 'Đang chấm…' : 'Chấm điểm cơ hội'}
          </button>
          <button className='btn btn-primary' disabled={busy.angles || (movie.angles?.length > 0)} onClick={onAngles}>
            {movie.angles?.length > 0 ? `Góc nội dung: ${movie.angles.length}` : busy.angles ? 'Đang sinh…' : 'Sinh góc nội dung'}
          </button>
          <button className='btn btn-primary' disabled={busy.script} onClick={onScript}>
            {busy.script ? 'Đang viết…' : scriptDetail ? `Viết lại kịch bản v${scriptDetail.version}` : 'Viết kịch bản'}
          </button>
          <button className='btn btn-primary' disabled={busy.voice || !scriptDetail} onClick={onVoice}>
            {busy.voice ? 'Đang tạo giọng…' : scriptDetail?.latest_generation ? 'Tạo giọng đọc lại' : 'Tạo giọng đọc'}
          </button>
          <button className='btn btn-primary' disabled={busy.timeline || !scriptDetail?.latest_generation} onClick={onTimeline}>
            {busy.timeline ? 'Đang dựng…' : scriptDetail?.timeline ? 'Dựng timeline lại' : 'Dựng timeline'}
          </button>
          <button className='btn btn-primary' disabled={busy.visualPlan || !scriptDetail} onClick={onVisualPlan}>
            {busy.visualPlan ? 'Đang phân plan…' : scriptDetail?.visual_plan ? 'Phân plan lại' : 'Phân plan hình ảnh'}
          </button>
          <button className='btn btn-primary' disabled={busy.assets || !scriptDetail?.visual_plan} onClick={onAssets}>
            {busy.assets ? 'Đang tìm hình…' : scriptDetail?.assets?.length ? 'Tạo hình lại' : 'Tạo hình ảnh'}
          </button>
          <button className='btn btn-primary' disabled={busy.copyright || !scriptDetail?.assets?.length} onClick={onCopyright}>
            {busy.copyright ? 'Đang kiểm bản quyền…' : scriptDetail?.copyright_reviews?.length ? 'Kiểm lại bản quyền' : 'Kiểm bản quyền'}
          </button>
          <button className='btn btn-primary' disabled={busy.render || !scriptDetail?.copyright_reviews?.length} onClick={onRender}>
            {busy.render ? 'Đang render…' : scriptDetail?.renders?.length ? 'Render lại' : 'Render video'}
          </button>
          <button className='btn btn-primary' disabled={busy.subtitle || !scriptDetail?.timeline} onClick={onSubtitle}>
            {busy.subtitle ? 'Đang làm phụ đề…' : scriptDetail?.subtitles?.length ? 'Làm phụ đề lại' : 'Làm phụ đề'}
          </button>
          <button className='btn btn-primary' disabled={busy.qa || !scriptDetail?.renders?.length || !scriptDetail?.subtitles?.length} onClick={onQA}>
            {busy.qa ? 'Đang QA…' : 'Chạy QA'}
          </button>
        </div>
        {error && <div className='error-banner' style={{ marginTop: '0.5rem' }}>{error}</div>}
      </section>

      {movie.opportunity && (
        <section className='card'>
          <h2>Điểm cơ hội</h2>
          <div className='score-big'>{movie.opportunity.overall}</div>
          <div className='kv'>
            {Object.entries(SCORE_WEIGHTS).map(([k, w]) => (
              <div key={k} className='muted small'>
                {k.replace('_', ' ')} {movie.opportunity.sub_scores?.[k]} · ({Math.round(w * 100)}%)
              </div>
            ))}
            <div className='muted small'>Confidence {movie.opportunity.confidence} · {formatDate(movie.opportunity.created_at)}</div>
            {movie.opportunity.rationale && (
              <details>
                <summary className='small'>Lý do chấm điểm</summary>
                <p className='muted small'>{movie.opportunity.rationale}</p>
              </details>
            )}
          </div>
        </section>
      )}

      {movie.summaries?.length > 0 && (
        <section className='card'>
          <h2>Tóm tắt nghiên cứu</h2>
          {movie.summaries.map((s, i) => (
            <p key={i} className='muted'>{s}</p>
          ))}
        </section>
      )}

      <section className='card'>
        <h2>Góc nội dung (CP1)</h2>
        {movie.angles?.length ? (
          <ul className='angle-list'>
            {movie.angles.map((a, i) => (
              <li key={i} className='angle-item'>
                <div className='strong'>{a.title}</div>
                <div className='muted small'>{a.hook}</div>
              </li>
            ))}
          </ul>
        ) : (
          <div className='muted'>Chưa có góc nội dung.</div>
        )}
      </section>

      {scriptDetail && (
        <section className='card'>
          <div className='project-head'>
            <h2>Kịch bản v{scriptDetail.version} <span className='muted small'>{scriptDetail.word_count} từ · {formatDuration(scriptDetail.estimated_duration_s)}</span></h2>
            <span className={`badge badge-${scriptDetail.status === 'draft' ? 'pending' : 'succeeded'}`}>{scriptDetail.status}</span>
          </div>
          <ul className='segments-list'>
            {scriptDetail.segments?.map((seg) => (
              <li key={seg.id} className='segment-item'>
                <div className='segment-header'>
                  <span className='strong'>{SCRIPT_SECTION_LABEL[seg.section] || seg.section}</span>
                  {seg.duration_estimate_s && <span className='muted small'>~{formatDuration(seg.duration_estimate_s)}</span>}
                </div>
                <p className='segment-text'>{seg.text}</p>
              </li>
            ))}
          </ul>

          {scriptDetail.latest_generation && (
            <div className='voice-info'>
              <h3>Giọng đọc</h3>
              <div className='kv'>
                <div className='muted small'>{scriptDetail.latest_generation.provider} / {scriptDetail.latest_generation.model} · {scriptDetail.latest_generation.language} · x{scriptDetail.latest_generation.speed}</div>
                <div className='muted small'>Audio: {formatDuration(scriptDetail.latest_generation.audio_duration_s)} · Thương mại: {scriptDetail.latest_generation.license_info?.commercial_use}</div>
              </div>
            </div>
          )}

          {scriptDetail.timeline && (
            <div className='timeline-info'>
              <h3>Timeline <span className='muted small'>tổng {formatDuration(scriptDetail.timeline.total_duration_s)}</span></h3>
              <ul className='timeline-list'>
                {scriptDetail.timeline.segments?.map((ts) => (
                  <li key={ts.segment_id || ts.position} className='timeline-item'>
                    <span className='badge badge-small'>{ts.position}</span>
                    <span className='strong'>{SCRIPT_SECTION_LABEL[ts.section] || ts.section}</span>
                    <span className='muted small' style={{ marginLeft: 'auto', whiteSpace: 'nowrap' }}>
                      {formatDuration(ts.start_s)} → {formatDuration(ts.end_s)}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {scriptDetail.visual_plan && (
            <div className='visual-plan-info'>
              <h3>Visual plan <span className='muted small'>v{scriptDetail.visual_plan.strategy_version} · {formatDuration(scriptDetail.visual_plan.total_planned_duration_s)}</span></h3>
              <ul className='timeline-list'>
                {scriptDetail.visual_plan.segments?.map((vp) => (
                  <li key={vp.segment_index} className='timeline-item'>
                    <span className='badge badge-small'>{vp.segment_index + 1}</span>
                    <span className='strong'>{SCRIPT_SECTION_LABEL[vp.section] || vp.section}</span>
                    <span className='muted small' style={{ marginLeft: 'auto' }}>{vp.purpose} · {formatDuration(vp.duration_s)}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {scriptDetail.assets?.length > 0 && (
            <div className='assets-info'>
              <h3>Hình ảnh ({scriptDetail.assets.length})</h3>
              <ul className='timeline-list'>
                {scriptDetail.assets.map((asset) => (
                  <li key={asset.id} className='timeline-item'>
                    <span className='badge badge-small'>{asset.segment_index + 1}</span>
                    <span className='strong'>{asset.asset_type}</span>
                    <span className='muted small' style={{ marginLeft: 'auto' }}>
                      {asset.source} · {asset.license || 'thiếu'} · {asset.commercial_use || 'unknown'}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {scriptDetail.copyright_reviews?.length > 0 && (
            <div className='copyright-info'>
              <h3>Đánh giá bản quyền</h3>
              <ul className='timeline-list'>
                {scriptDetail.copyright_reviews.map((rev) => (
                  <li key={rev.asset_id} className='timeline-item'>
                    <span className='badge badge-small'>#{rev.asset_id}</span>
                    <span className={`strong ${rev.decision === 'block' ? 'error-banner' : ''}`}>{rev.decision}</span>
                    <span className='muted small' style={{ marginLeft: 'auto' }}>
                      {rev.risk_level} {rev.duration_warning ? '· clip > 3s' : ''} {rev.human_review_required ? '· cần review' : ''}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {scriptDetail.renders?.length > 0 && (
            <div className='render-info'>
              <h3>Video đã render</h3>
              <ul className='timeline-list'>
                {scriptDetail.renders.map((r) => (
                  <li key={r.id} className='timeline-item'>
                    <span className='strong'>{r.resolution}@{r.fps}fps</span>
                    <span className='muted small' style={{ marginLeft: 'auto', whiteSpace: 'nowrap' }}>
                      {formatDuration(r.duration_s)} · {(r.file_size_bytes / 1024 / 1024).toFixed(1)} MB · {r.video_codec}/{r.audio_codec}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {scriptDetail.subtitles?.length > 0 && (
            <div className='subtitle-info'>
              <h3>Phụ đề ({scriptDetail.subtitles.length})</h3>
              <ul className='timeline-list'>
                {scriptDetail.subtitles.map((s) => (
                  <li key={s.id} className='timeline-item'>
                    <span className='strong'>{s.format.toUpperCase()}</span>
                    <span className='muted small' style={{ marginLeft: 'auto', whiteSpace: 'nowrap' }}>
                      {s.cue_count} cue · {formatDuration(s.duration_s)} · {s.language}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {scriptDetail.qa_reports?.length > 0 && (
            <div className='qa-info'>
              <h3>Báo cáo QA</h3>
              <ul className='timeline-list'>
                {scriptDetail.qa_reports.map((rep) => (
                  <li key={rep.id} className='timeline-item'>
                    <span className={`badge badge-small ${rep.passed ? '' : 'error-banner'}`}>{rep.passed ? 'PASS' : 'FAIL'}</span>
                    <span className='strong'>{rep.gate}</span>
                    {rep.severity !== 'pass' && <span className='muted small'>· {rep.severity}</span>}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </section>
      )}
    </div>
  )
}