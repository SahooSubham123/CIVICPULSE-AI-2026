import { useEffect, useRef, useState } from 'react'
import { FileSearch, Info, Printer, ShieldCheck, Upload } from 'lucide-react'
import { Badge, Button, EmptyState, PageTitle, Panel, SectionHeading } from '../../../components/ui.jsx'
import { apiJson } from '../../../lib/api/client.js'
import { useSession } from '../../grievance_management/hooks/useSession.js'
import { SessionPanel } from '../../grievance_management/components/SessionPanel.jsx'

const modes = [
  { value: 'claim', label: 'Text claim' },
  { value: 'image', label: 'Image' },
  { value: 'audio', label: 'Audio' },
  { value: 'video', label: 'Video' },
]

const acceptTypes = {
  image: 'image/jpeg,image/png,image/webp',
  audio: 'audio/mpeg,audio/wav,audio/x-wav,audio/mp4,audio/ogg,audio/webm',
  video: 'video/mp4,video/quicktime,video/webm',
}

function assessmentLabel(assessment) {
  return ({
    supported: 'Evidence supports',
    contradicted: 'Evidence conflicts',
    inconclusive: 'Inconclusive',
    needs_human_review: 'Human review needed',
    possible_manipulation_indicators: 'Indicators to review',
  })[assessment] || assessment
}

function assessmentTone(assessment) {
  if (assessment === 'supported') return 'green'
  if (assessment === 'contradicted' || assessment === 'possible_manipulation_indicators') return 'orange'
  return 'blue'
}

export function FactVerification() {
  const session = useSession()
  const fileInputRef = useRef(null)
  const [mode, setMode] = useState('claim')
  const [claim, setClaim] = useState('')
  const [context, setContext] = useState('')
  const [sourceUrls, setSourceUrls] = useState('')
  const [file, setFile] = useState(null)
  const [report, setReport] = useState(null)
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(false)
  const [historyLoading, setHistoryLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!session.user) return undefined
    let active = true
    setHistoryLoading(true)
    apiJson('/verification')
      .then((items) => { if (active) setHistory(items) })
      .catch((requestError) => { if (active) setError(requestError.message) })
      .finally(() => { if (active) setHistoryLoading(false) })
    return () => { active = false }
  }, [session.user])

  const submit = async (event) => {
    event.preventDefault()
    if (!session.user) return
    setLoading(true)
    setError('')
    setReport(null)
    try {
      let result
      if (mode === 'claim') {
        const urls = sourceUrls.split(/\r?\n/).map((url) => url.trim()).filter(Boolean)
        if (urls.length > 5) throw new Error('Provide no more than five trusted-source URLs.')
        result = await apiJson('/verification/claims', {
          method: 'POST',
          body: JSON.stringify({
            claim: claim.trim(),
            context: context.trim() || null,
            source_urls: urls,
          }),
        })
      } else {
        if (!file) throw new Error('Choose a media file to analyze.')
        const formData = new FormData()
        formData.append('file', file)
        formData.append('context', context.trim())
        const route = mode === 'image' ? 'images' : mode === 'audio' ? 'audio' : 'videos'
        result = await apiJson(`/media-analysis/${route}`, { method: 'POST', body: formData })
      }
      setReport(result)
      setHistory((items) => [result, ...items.filter((item) => item.id !== result.id)].slice(0, 50))
      setFile(null)
      if (fileInputRef.current) fileInputRef.current.value = ''
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <PageTitle
        eyebrow="TRUSTED INFORMATION"
        title="Fact verification"
        description="Review claims and media using cited evidence, clear limitations, and human oversight."
      />
      <div className="verify-banner">
        <div className="verify-badge"><ShieldCheck size={22} /></div>
        <div>
          <strong>Evidence first. Human judgment always.</strong>
          <p>AI findings are preliminary. Confidence is uncalibrated; a score alone never proves media is fake.</p>
        </div>
      </div>

      {session.error && <p className="grievance-error" role="alert">{session.error}</p>}
      {!session.user && !session.loading && <SessionPanel onAuthenticated={session.setUser} />}
      {session.loading && <p className="grievance-help-text">Loading your secure account…</p>}

      {session.user && (
        <>
          <div className="verify-grid">
            <Panel className="verify-form-panel">
              <div className="verify-heading">
                <span className="eyebrow">START A CHECK</span>
                <h2>What would you like to review?</h2>
                <p>Uploaded media is sent to the configured AI provider for analysis. Original files are not retained, but reports and audio transcripts are saved to your private account. Avoid sensitive or confidential material.</p>
              </div>
              <form onSubmit={submit}>
                <label className="field-label">
                  Review type
                  <select value={mode} onChange={(event) => { setMode(event.target.value); setFile(null); setReport(null); setError('') }}>
                    {modes.map((item) => <option value={item.value} key={item.value}>{item.label}</option>)}
                  </select>
                </label>
                {mode === 'claim' ? (
                  <>
                    <label className="field-label">
                      Claim or statement
                      <textarea rows="4" required minLength={8} maxLength={8000} value={claim} onChange={(event) => setClaim(event.target.value)} placeholder="Paste the claim and keep its meaning intact…" />
                    </label>
                    <label className="field-label">
                      Trusted-source URLs <small>(one per line; only administrator-configured domains are fetched)</small>
                      <textarea rows="3" maxLength={5000} value={sourceUrls} onChange={(event) => setSourceUrls(event.target.value)} placeholder="https://trusted.example.gov/article" />
                    </label>
                  </>
                ) : (
                  <label className="field-label">
                    Upload {mode}
                    <span className="upload-zone verify-upload">
                      <Upload size={18} />
                      <strong>{file?.name || `Choose ${mode} file`}</strong>
                      <small>Maximum upload size is set by the service.</small>
                      <input
                        ref={fileInputRef}
                        type="file"
                        required
                        accept={acceptTypes[mode]}
                        onChange={(event) => setFile(event.target.files?.[0] || null)}
                      />
                    </span>
                  </label>
                )}
                <label className="field-label">
                  Context <small>(optional; treated as unverified)</small>
                  <textarea rows="2" maxLength={4000} value={context} onChange={(event) => setContext(event.target.value)} placeholder="Where did you encounter this?" />
                </label>
                <Button type="submit" disabled={loading}>
                  <ShieldCheck size={16} /> {loading ? 'Reviewing…' : 'Review evidence'}
                </Button>
              </form>
              {error && <p className="grievance-error" role="alert">{error}</p>}
            </Panel>

            <Panel className="verification-principles">
              <SectionHeading title="What this can tell you" subtitle="A transparent review, not a verdict." />
              <div className="principle-list">
                <div className="principle"><span>1</span><div><strong>Evidence</strong><p>Claims are compared only with readable pages from configured trusted domains.</p></div></div>
                <div className="principle"><span>2</span><div><strong>Limitations</strong><p>Transcriptions, sampled frames, and model interpretations can be incomplete or wrong.</p></div></div>
                <div className="principle"><span>3</span><div><strong>Human review</strong><p>Verify the original material and sources before sharing or acting on a result.</p></div></div>
              </div>
            </Panel>
          </div>

          {report && <VerificationReport report={report} />}

          <Panel className="verification-history">
            <SectionHeading title="Your recent reports" subtitle="Visible only to your signed-in account." />
            {historyLoading && <p className="grievance-help-text">Loading reports…</p>}
            {!historyLoading && !history.length && <EmptyState icon={FileSearch} title="No verification reports yet" description="Reports you create will be saved here for you to revisit." />}
            {history.map((item) => (
              <button className="verification-history-item" key={item.id} onClick={() => setReport(item)}>
                <span><strong>{item.subject_type} review</strong><small>{new Date(item.created_at).toLocaleString()}</small></span>
                <Badge tone={assessmentTone(item.assessment)}>{assessmentLabel(item.assessment)}</Badge>
              </button>
            ))}
          </Panel>
        </>
      )}
      <div className="responsible-note"><Info size={15} /> Never label media fake based only on an AI detection score.</div>
    </>
  )
}

function VerificationReport({ report }) {
  return (
    <Panel className="verification-report" aria-live="polite">
      <div className="verification-report-head">
        <div>
          <span className="eyebrow">VERIFICATION REPORT</span>
          <h2>{report.subject_type[0].toUpperCase() + report.subject_type.slice(1)} analysis</h2>
          <small>{new Date(report.created_at).toLocaleString()} · Provider: {report.provider}</small>
        </div>
        <div className="verification-report-actions">
          <Badge tone={assessmentTone(report.assessment)}>{assessmentLabel(report.assessment)}</Badge>
          <Button type="button" variant="light" onClick={() => window.print()}><Printer size={15} /> Print</Button>
        </div>
      </div>
      <p className="verification-analysis">{report.analysis}</p>
      {report.confidence !== null && report.confidence !== undefined && (
        <p className="verification-confidence">Model score: {(report.confidence * 100).toFixed(0)}% — {report.confidence_note}</p>
      )}
      <p className="verification-disclaimer">{report.disclaimer}</p>
      {report.transcript && <details className="verification-transcript"><summary>Machine-generated transcript</summary><p>{report.transcript}</p></details>}
      <div className="verification-evidence">
        <h3>Evidence and observations</h3>
        {report.evidence.length ? report.evidence.map((item, index) => (
          <div className="verification-evidence-item" key={`${item.kind}-${index}`}>
            <Badge>{item.kind.replaceAll('_', ' ')}</Badge>
            {item.timestamp_seconds !== null && item.timestamp_seconds !== undefined && <small>At {item.timestamp_seconds.toFixed(2)}s</small>}
            <p>{item.description}</p>
            {item.source_url && <a href={item.source_url} target="_blank" rel="noreferrer">Open original source</a>}
          </div>
        )) : <p>No source excerpts or observations were available.</p>}
      </div>
      {report.sources.length > 0 && (
        <div className="verification-sources">
          <h3>Fetched sources</h3>
          {report.sources.map((source) => <a key={source} href={source} target="_blank" rel="noreferrer">{source}</a>)}
        </div>
      )}
      <div className="verification-limitations">
        <h3>Limitations</h3>
        <ul>{report.limitations.map((item) => <li key={item}>{item}</li>)}</ul>
      </div>
    </Panel>
  )
}
