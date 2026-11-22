import { useEffect, useState } from 'react'
import { Clock3, FileSearch, Flag, Info, MapPin, Search } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Badge, Button, EmptyState, PageTitle, Panel } from '../../../components/ui.jsx'
import { useSession } from '../hooks/useSession.js'
import { apiJson } from '../services/api.js'
import { SessionPanel } from './SessionPanel.jsx'

function statusLabel(status) {
  return ({ received: 'Received', in_progress: 'In progress', resolved: 'Resolved', rejected: 'Rejected' })[status] || status
}

function statusTone(status) {
  return ({ received: 'blue', in_progress: 'amber', resolved: 'green', rejected: 'red' })[status] || 'blue'
}

export function CitizenTracking() {
  const session = useSession()
  const [reports, setReports] = useState([])
  const [reference, setReference] = useState('')
  const [trackedReport, setTrackedReport] = useState(null)
  const [filter, setFilter] = useState('all')
  const [error, setError] = useState('')
  const [loadingReports, setLoadingReports] = useState(false)
  const [searching, setSearching] = useState(false)

  useEffect(() => {
    if (!session.user || session.user.role !== 'citizen') return
    let active = true
    setLoadingReports(true)
    apiJson('/grievances?limit=100')
      .then((response) => { if (active) setReports(response.items) })
      .catch((requestError) => { if (active) setError(requestError.message) })
      .finally(() => { if (active) setLoadingReports(false) })
    return () => { active = false }
  }, [session.user])

  const search = async (event) => {
    event.preventDefault()
    if (!reference.trim()) return
    setSearching(true)
    setError('')
    setTrackedReport(null)
    try {
      setTrackedReport(await apiJson(`/tracking/${encodeURIComponent(reference.trim())}`))
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setSearching(false)
    }
  }
  const visibleReports = reports.filter((report) => filter === 'all' || report.status === filter)

  return (
    <>
      <PageTitle eyebrow="CITIZEN SERVICES" title="Track a complaint" description="Follow your reports and see the latest update from the team." action={<div className="tracking-title-actions">{session.user?.role === 'citizen' && <Button variant="light" onClick={session.logout}>Sign out</Button>}<Link to="/grievances/new" className="button button-primary">New report</Link></div>} />
      <Panel className="tracking-search-panel">
        <div className="tracking-search-copy"><span className="search-art-icon"><FileSearch size={22} /></span><div><h2>Track with a reference number</h2><p>Anyone with the reference can view basic status; personal details stay private.</p></div></div>
        <form className="tracking-search-form" onSubmit={search}>
          <input aria-label="Complaint reference number" value={reference} onChange={(event) => setReference(event.target.value)} placeholder="e.g. CP-…" required />
          <Button type="submit" disabled={searching}><Search size={15} /> {searching ? 'Searching…' : 'Track report'}</Button>
        </form>
      </Panel>
      {trackedReport && <TrackingCard report={trackedReport} publicView />}
      {error && <p className="grievance-error" role="alert">{error}</p>}
      {!session.user && !session.loading && <SessionPanel onAuthenticated={session.setUser} />}
      {session.loading && <p className="grievance-help-text">Loading your secure account…</p>}
      {session.user?.role === 'citizen' && (
        <>
          <div className="list-toolbar">
            <div><h2>Your reports <span className="count-pill">{visibleReports.length}</span></h2><p>Reports submitted from your citizen account</p></div>
            <div className="filter-select"><select value={filter} onChange={(event) => setFilter(event.target.value)} aria-label="Filter reports">
              <option value="all">All reports</option><option value="received">Received</option><option value="in_progress">In progress</option><option value="resolved">Resolved</option><option value="rejected">Rejected</option>
            </select></div>
          </div>
          {loadingReports ? <p className="grievance-help-text">Loading your reports…</p> : visibleReports.length
            ? <div className="tracking-list">{visibleReports.map((report) => <TrackingCard key={report.id} report={report} />)}</div>
            : <Panel><EmptyState icon={FileSearch} title="No complaints yet" description="Your submitted reports will appear here." /></Panel>}
        </>
      )}
      {session.user?.role === 'admin' && <Panel><p>Signed in as an administrator. Citizen reports are shown in the admin workspace.</p><Link className="button button-primary" to="/admin">Open admin workspace</Link></Panel>}
      <div className="tracking-footnote"><Info size={14} /> AI triage is advisory. Classification, priority, and case outcomes require staff review.</div>
    </>
  )
}

function TrackingCard({ report, publicView = false }) {
  const steps = ['received', 'in_progress', 'resolved']
  const progress = report.status === 'resolved' ? 100 : report.status === 'in_progress' ? 66 : 25
  const createdDate = new Date(report.created_at).toLocaleDateString()
  return (
    <Panel className="tracking-card">
      <div className="tracking-card-head">
        <span className={`tracking-category-icon icon-${statusTone(report.status)}`}><Flag size={18} /></span>
        <div className="tracking-main">
          <div className="tracking-title-line"><h3>{report.title}</h3><Badge tone={statusTone(report.status)}>{statusLabel(report.status)}</Badge></div>
          <div className="tracking-details">
            <span>Ref: {report.reference_number}</span><span><MapPin size={13} /> {report.location}</span><span><Clock3 size={13} /> Reported {createdDate}</span>
          </div>
        </div>
      </div>
      <div className="progress-track"><span style={{ width: `${progress}%` }} /></div>
      <div className="tracking-card-foot">
        <span>{report.resolution_note || (report.status === 'resolved' ? 'Your report has been resolved.' : 'Your report is awaiting or undergoing staff review.')}</span>
        {!publicView && report.ai_suggested_category && <span>AI suggested: {report.ai_suggested_category} · {report.ai_suggested_priority}</span>}
      </div>
      {report.department && <p className="grievance-help-text">Responsible department: {report.department}</p>}
      {steps.includes(report.status) && <span className="sr-only">Progress {progress}%</span>}
    </Panel>
  )
}
