import { useEffect, useState } from 'react'
import { AlertCircle, CheckCircle2, Clock3, Eye, ShieldCheck } from 'lucide-react'
import { Badge, Button, EmptyState, PageTitle, Panel, SectionHeading, StatCard } from '../../../components/ui.jsx'
import { useSession } from '../hooks/useSession.js'
import { apiJson, apiRequest } from '../services/api.js'
import { SessionPanel } from './SessionPanel.jsx'

const statusNames = { received: 'Received', in_progress: 'In progress', resolved: 'Resolved', rejected: 'Rejected' }

export function AdminGrievances() {
  const session = useSession()
  const [overview, setOverview] = useState(null)
  const [reports, setReports] = useState([])
  const [filter, setFilter] = useState('pending')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (session.user?.role !== 'admin') return
    let active = true
    setLoading(true)
    setError('')
    Promise.all([
      apiJson('/admin/overview'),
      apiJson(`/admin/grievances?limit=100${filter === 'all' ? '' : `&review_status=${filter}`}`),
    ])
      .then(([stats, response]) => {
        if (active) { setOverview(stats); setReports(response.items) }
      })
      .catch((requestError) => { if (active) setError(requestError.message) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [session.user, filter])

  const updateReport = (updated) => {
    setReports((items) => items.filter((item) => item.id !== updated.id || filter === 'all' || updated.review_status === filter)
      .map((item) => item.id === updated.id ? updated : item))
    apiJson('/admin/overview')
      .then(setOverview)
      .catch((requestError) => setError(requestError.message))
  }
  if (session.loading) return <PageTitle eyebrow="DEPARTMENT WORKSPACE" title="Complaint management" description="Loading your secure account…" />
  if (!session.user) {
    return <><PageTitle eyebrow="DEPARTMENT WORKSPACE" title="Complaint management" description="Sign in with an administrator account to review and update citizen complaints." />{session.error && <p className="grievance-error" role="alert">{session.error}</p>}<SessionPanel onAuthenticated={session.setUser} allowRegistration={false} /></>
  }
  if (session.user.role !== 'admin') {
    return <><PageTitle eyebrow="DEPARTMENT WORKSPACE" title="Administrator access required" description="This workspace is restricted to authorized staff accounts." /><Panel><p>Sign out of the citizen account and sign in using an administrator account.</p><Button variant="light" onClick={session.logout}>Sign out</Button></Panel></>
  }

  return (
    <>
      <PageTitle eyebrow="DEPARTMENT WORKSPACE" title="Complaint management" description="Review AI-assisted triage and make staff decisions on every report." action={<Button variant="light" onClick={session.logout}>Sign out</Button>} />
      <div className="admin-notice"><ShieldCheck size={16} /><span>Human review required</span><i>·</i><span>AI labels and priorities are advisory only.</span></div>
      {overview && <div className="stats-grid admin-stats">
        <StatCard label="Total complaints" value={overview.total_grievances} note="All citizen reports" icon={CheckCircle2} tone="blue" />
        <StatCard label="Open complaints" value={overview.open_grievances} note="Received or in progress" icon={Clock3} tone="purple" />
        <StatCard label="Resolved" value={overview.resolved_grievances} note="Human-updated status" icon={CheckCircle2} tone="green" />
        <StatCard label="Awaiting review" value={overview.pending_review_grievances} note="Staff action needed" icon={AlertCircle} tone="orange" />
      </div>}
      <Panel className="admin-table-panel grievance-admin-panel">
        <div className="admin-table-toolbar"><SectionHeading title="Incoming complaints" subtitle="Review evidence, location, and AI suggestions before updating each case." /></div>
        <div className="admin-tabs">
          {[['pending', 'Needs review'], ['reviewed', 'Reviewed'], ['all', 'All reports']].map(([value, label]) => <button key={value} className={filter === value ? 'admin-tab-active' : ''} onClick={() => setFilter(value)}>{label}</button>)}
        </div>
        {error && <p className="grievance-error" role="alert">{error}</p>}
        {loading ? <p className="grievance-help-text">Loading complaints…</p> : reports.length
          ? <div className="grievance-admin-list">{reports.map((report) => <AdminComplaintRow key={report.id} report={report} onUpdated={updateReport} />)}</div>
          : <EmptyState icon={AlertCircle} title="No complaints in this view" description="New citizen submissions will appear here." />}
      </Panel>
    </>
  )
}

function AdminComplaintRow({ report, onUpdated }) {
  const [category, setCategory] = useState(report.category)
  const [priority, setPriority] = useState(report.ai_suggested_priority || report.priority)
  const [status, setStatus] = useState(report.status)
  const [department, setDepartment] = useState(report.department || '')
  const [resolutionNote, setResolutionNote] = useState(report.resolution_note || '')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [evidenceUrl, setEvidenceUrl] = useState('')
  const [loadingEvidence, setLoadingEvidence] = useState(false)

  const saveReview = async () => {
    setSaving(true)
    setError('')
    try {
      const updated = await apiJson(`/grievances/${report.id}`, {
        method: 'PATCH',
        body: JSON.stringify({
          category,
          priority,
          status,
          department: department || null,
          resolution_note: resolutionNote || null,
          review_status: 'reviewed',
        }),
      })
      onUpdated(updated)
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setSaving(false)
    }
  }

  const viewEvidence = async () => {
    setLoadingEvidence(true)
    setError('')
    try {
      const response = await apiRequest(`/grievances/${report.id}/evidence`)
      const url = URL.createObjectURL(await response.blob())
      setEvidenceUrl(url)
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setLoadingEvidence(false)
    }
  }

  useEffect(() => () => { if (evidenceUrl) URL.revokeObjectURL(evidenceUrl) }, [evidenceUrl])

  return (
    <article className="admin-grievance-card">
      <div className="admin-grievance-heading">
        <div><span className="eyebrow">{report.reference_number} · {new Date(report.created_at).toLocaleString()}</span><h3>{report.title}</h3></div>
        <Badge tone={report.review_status === 'reviewed' ? 'green' : 'amber'}>{report.review_status === 'reviewed' ? 'Reviewed' : 'Human review pending'}</Badge>
      </div>
      <p className="admin-grievance-description">{report.description}</p>
      <div className="admin-grievance-meta"><span>Citizen category: {report.category}</span><span>Location: {report.location}</span>{report.latitude != null && report.longitude != null && <span>Coordinates: {report.latitude.toFixed(5)}, {report.longitude.toFixed(5)}</span>}</div>
      <div className="admin-ai-triage">
        <strong><ShieldCheck size={15} /> AI triage · {report.ai_triage_status}</strong>
        <span>Category: {report.ai_suggested_category || 'No suggestion'} · Priority: {report.ai_suggested_priority || 'No suggestion'}{report.ai_confidence != null ? ` · Confidence ${Math.round(report.ai_confidence * 100)}%` : ''}</span>
        {report.ai_rationale && <p>{report.ai_rationale}</p>}
        <small>Advisory only. You are responsible for the final classification and priority.</small>
      </div>
      {report.has_evidence && <div className="admin-evidence">
        <Button type="button" variant="outline" onClick={viewEvidence} disabled={loadingEvidence}><Eye size={14} /> {loadingEvidence ? 'Loading…' : 'View attached image'}</Button>
        {evidenceUrl && <img src={evidenceUrl} alt={`Evidence for ${report.reference_number}`} />}
      </div>}
      <div className="admin-review-fields">
        <label className="field-label">Final category<input value={category} onChange={(event) => setCategory(event.target.value)} maxLength={80} /></label>
        <label className="field-label">Final priority<select value={priority} onChange={(event) => setPriority(event.target.value)}>{['low', 'medium', 'high', 'urgent'].map((value) => <option key={value} value={value}>{value}</option>)}</select></label>
        <label className="field-label">Status<select value={status} onChange={(event) => setStatus(event.target.value)}>{Object.entries(statusNames).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
        <label className="field-label">Department<input value={department} onChange={(event) => setDepartment(event.target.value)} maxLength={180} placeholder="Assign responsible team" /></label>
        <label className="field-label admin-resolution-field">Resolution or update note<textarea rows="2" maxLength={5000} value={resolutionNote} onChange={(event) => setResolutionNote(event.target.value)} placeholder="Share a staff update or resolution details" /></label>
      </div>
      {error && <p className="grievance-error" role="alert">{error}</p>}
      <div className="admin-review-actions"><span>{report.reviewed_at ? `Last reviewed ${new Date(report.reviewed_at).toLocaleString()}` : 'A human reviewer must confirm this assessment.'}</span><Button onClick={saveReview} disabled={saving}>{saving ? 'Saving…' : 'Save and confirm review'} <CheckCircle2 size={15} /></Button></div>
    </article>
  )
}
