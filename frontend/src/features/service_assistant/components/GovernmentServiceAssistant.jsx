import { useEffect, useState } from 'react'
import {
  BookOpenCheck, Check, ClipboardList, ExternalLink, FileText, Globe2, Info,
  LoaderCircle, LockKeyhole, Search, ShieldCheck,
} from 'lucide-react'
import { Badge, Button, EmptyState, PageTitle, Panel, SectionHeading } from '../../../components/ui.jsx'
import { SessionPanel } from '../../grievance_management/components/SessionPanel.jsx'
import { useSession } from '../../grievance_management/hooks/useSession.js'
import { getServiceAssistance, getServicePlans, inspectPortal } from '../services/api.js'

const FIELD_TYPES = new Set(['text', 'date', 'number', 'textarea'])

export function GovernmentServiceAssistant() {
  const session = useSession()
  const [serviceRequest, setServiceRequest] = useState('')
  const [jurisdiction, setJurisdiction] = useState('')
  const [assistance, setAssistance] = useState(null)
  const [answers, setAnswers] = useState({})
  const [showDraft, setShowDraft] = useState(false)
  const [plans, setPlans] = useState([])
  const [planError, setPlanError] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!session.user || session.user.role !== 'citizen') return undefined
    let active = true
    getServicePlans()
      .then((response) => { if (active) setPlans(response.items) })
      .catch((requestError) => { if (active) setPlanError(requestError.message) })
    return () => { active = false }
  }, [session.user])

  const requestAssistance = async (event) => {
    event.preventDefault()
    setLoading(true)
    setError('')
    setShowDraft(false)
    setAssistance(null)
    setAnswers({})
    try {
      const result = await getServiceAssistance(serviceRequest, jurisdiction)
      setAssistance(result)
      setPlans((items) => [{
        task_id: result.task_id,
        service_name: result.service_name,
        status: 'planned',
        steps: result.procedure,
        created_at: new Date().toISOString(),
      }, ...items])
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setLoading(false)
    }
  }

  if (session.loading) {
    return <PageTitle eyebrow="GOVERNMENT SERVICE ASSISTANCE" title="A clear path to public services" description="Loading your secure account…" />
  }
  if (!session.user) {
    return (
      <>
        <PageTitle eyebrow="GOVERNMENT SERVICE ASSISTANCE" title="Sign in to prepare a service plan" description="Plans are private to your account. Application details are not saved." />
        {session.error && <p className="grievance-error" role="alert">{session.error}</p>}
        <SessionPanel onAuthenticated={session.setUser} />
      </>
    )
  }
  if (session.user.role !== 'citizen') {
    return <><PageTitle eyebrow="GOVERNMENT SERVICE ASSISTANCE" title="Citizen account required" /><Panel><p>Sign out of the administrator account and use a citizen account to prepare a service plan.</p><Button variant="light" onClick={session.logout}>Sign out</Button></Panel></>
  }

  const setAnswer = (fieldId, value) => {
    setAnswers((current) => ({ ...current, [fieldId]: value }))
    setShowDraft(false)
  }
  const logout = () => {
    setAnswers({})
    setAssistance(null)
    setShowDraft(false)
    session.logout()
  }

  return (
    <>
      <PageTitle eyebrow="GOVERNMENT SERVICE ASSISTANCE" title="A clear path to public services" description="Understand the procedure, prepare a draft, and open configured official portals. You remain in control of every application." action={<Button variant="light" onClick={logout}>Sign out</Button>} />
      <div className="service-agent-banner"><span><ShieldCheck size={18} /></span><div><strong>Guidance and preparation only</strong><p>No application is submitted and no legal declaration is made. Portal passwords, PINs, and one-time codes are never collected or stored.</p></div></div>
      <div className="service-agent-layout">
        <div className="service-agent-main">
          <Panel className="service-agent-intake">
            <SectionHeading title="What service do you need?" subtitle="Describe the service and where you are applying." />
            <form onSubmit={requestAssistance}>
              <label className="field-label">Service request
                <textarea required minLength={5} maxLength={2000} rows="3" value={serviceRequest} onChange={(event) => setServiceRequest(event.target.value)} placeholder="For example: I need to apply for a birth certificate for a child born in Bengaluru." />
                <small className="service-field-help">Do not include passwords, PINs, one-time codes, or sensitive personal identifiers. Your service description is sent to the configured AI provider for guidance.</small>
              </label>
              <label className="field-label">City, state, or jurisdiction
                <input required minLength={2} maxLength={120} value={jurisdiction} onChange={(event) => setJurisdiction(event.target.value)} placeholder="e.g. Bengaluru, Karnataka" />
              </label>
              {error && <p className="grievance-error" role="alert">{error}</p>}
              <Button type="submit" disabled={loading}>{loading ? <><LoaderCircle className="service-spinner" size={15} /> Preparing guidance…</> : <><Search size={15} /> Understand this service</>}</Button>
            </form>
          </Panel>

          {assistance && (
            <div className="service-agent-results">
              <Panel className="service-agent-procedure">
                <div className="service-agent-result-title"><span className="service-agent-icon"><BookOpenCheck size={19} /></span><div><span className="eyebrow">ASSISTANCE PLAN · {assistance.task_id.slice(0, 8)}</span><h2>{assistance.service_name}</h2></div><Badge tone="blue">Guidance only</Badge></div>
                <SectionHeading title="Application procedure" subtitle="Verify current steps with the responsible department before proceeding." />
                <ol className="service-procedure-list">{assistance.procedure.map((step, index) => <li key={`${index}-${step}`}><span>{index + 1}</span><p>{step}</p></li>)}</ol>
                <div className="service-agent-notice"><Info size={15} /><span>{assistance.safety_notice}</span></div>
              </Panel>

              {assistance.required_documents.length > 0 && <Panel className="service-document-panel">
                <SectionHeading title="Documents to check" subtitle="AI-generated suggestions; confirm the official current checklist." />
                <ul className="service-document-list">{assistance.required_documents.map((document) => <li key={document}><Check size={14} />{document}</li>)}</ul>
              </Panel>}

              <Panel className="service-draft-panel">
                <SectionHeading title="Prepare a private draft" subtitle="Entered details stay in this page's temporary memory and are not sent back or saved." />
                {assistance.form_fields.length ? (
                  <>
                    <div className="service-draft-fields">{assistance.form_fields.map((field) => <DraftField key={field.field_id} field={field} value={answers[field.field_id] || ''} onChange={(value) => setAnswer(field.field_id, value)} />)}</div>
                    <div className="service-draft-actions">
                      <Button type="button" variant="outline" onClick={() => setShowDraft(!showDraft)}><FileText size={15} /> {showDraft ? 'Hide draft review' : 'Review draft'}</Button>
                      <Button type="button" variant="light" onClick={() => { setAnswers({}); setShowDraft(false) }}>Clear entered details</Button>
                    </div>
                    {showDraft && <div className="service-draft-review" aria-live="polite">
                      <strong>Review your draft before using it</strong>
                      <dl>{assistance.form_fields.map((field) => <div key={field.field_id}><dt>{field.label}</dt><dd>{answers[field.field_id] || 'Not provided'}</dd></div>)}</dl>
                      <p>These details are not submitted or saved. Review them yourself and enter them directly on the official portal if you choose.</p>
                    </div>}
                  </>
                ) : <p className="service-agent-muted">No draft fields were identified. Check the document list and official portal for current requirements.</p>}
                <div className="service-agent-notice"><LockKeyhole size={15} /><span>{assistance.privacy_notice}</span></div>
                <div className="service-agent-notice service-declaration-notice"><ShieldCheck size={15} /><span>Read and confirm all legal declarations yourself on the official portal. The assistant does not draft or agree to declarations.</span></div>
              </Panel>

              <Panel className="service-tracking-panel">
                <SectionHeading title="How to track an application" subtitle={assistance.tracking_notice} />
                {assistance.tracking_guidance.length
                  ? <ol className="service-tracking-list">{assistance.tracking_guidance.map((step, index) => <li key={`${index}-${step}`}>{step}</li>)}</ol>
                  : <p className="service-agent-muted">Use the acknowledgement number and tracking instructions provided by the official department. Do not share passwords or one-time codes here.</p>}
              </Panel>

              <PortalInspector portals={assistance.supported_portals} />
            </div>
          )}
        </div>

        <aside className="service-agent-sidebar">
          <Panel className="service-agent-plan-list">
            <SectionHeading title="Your assistance plans" subtitle="Saved guidance only, not an application status." />
            {planError && <p className="grievance-error" role="alert">{planError}</p>}
            {plans.length ? plans.map((plan) => <div className="service-plan-history" key={plan.task_id}>
              <span><ClipboardList size={15} /></span><div><strong>{plan.service_name}</strong><small>{new Date(plan.created_at).toLocaleDateString()} · {plan.status}</small></div>
            </div>) : <p className="service-agent-muted">Your plans will appear here after you request assistance.</p>}
          </Panel>
          <Panel className="service-agent-safety">
            <span><Globe2 size={17} /></span><strong>Use official sources</strong>
            <p>Portal pages and AI guidance can change. Confirm fees, eligibility, timelines, and required documents with the responsible government office.</p>
            <p>Never provide portal credentials, PINs, or one-time codes. The assistant cannot submit your application.</p>
          </Panel>
        </aside>
      </div>
    </>
  )
}

function DraftField({ field, value, onChange }) {
  const fieldType = FIELD_TYPES.has(field.field_type) ? field.field_type : 'text'
  const commonProps = {
    id: `draft-${field.field_id}`,
    required: field.required,
    value,
    onChange: (event) => onChange(event.target.value),
    maxLength: 2000,
  }
  return (
    <label className="field-label" htmlFor={commonProps.id}>
      {field.label}{field.required && <span> *</span>}
      {fieldType === 'textarea'
        ? <textarea {...commonProps} rows="3" />
        : <input {...commonProps} type={fieldType} />}
      {field.help_text && <small className="service-field-help">{field.help_text}</small>}
    </label>
  )
}

function PortalInspector({ portals }) {
  const [paths, setPaths] = useState({})
  const [results, setResults] = useState({})
  const [errors, setErrors] = useState({})
  const [loading, setLoading] = useState({})
  if (!portals.length) {
    return <Panel className="service-portals-panel"><SectionHeading title="Supported government portals" /><EmptyState icon={Globe2} title="No portals configured" description="Portal navigation is available only for HTTPS sites configured by the service administrator." /></Panel>
  }
  const inspect = async (portal) => {
    setLoading((current) => ({ ...current, [portal.portal_id]: true }))
    setErrors((current) => ({ ...current, [portal.portal_id]: '' }))
    try {
      const result = await inspectPortal(portal.portal_id, paths[portal.portal_id] || '')
      setResults((current) => ({ ...current, [portal.portal_id]: result }))
    } catch (error) {
      setErrors((current) => ({ ...current, [portal.portal_id]: error.message }))
    } finally {
      setLoading((current) => ({ ...current, [portal.portal_id]: false }))
    }
  }
  return (
    <Panel className="service-portals-panel">
      <SectionHeading title="Supported government portals" subtitle="Playwright inspects public HTTPS pages only. Sign-in, downloads, form entry, and submission are blocked." />
      <div className="service-portal-list">{portals.map((portal) => {
        const result = results[portal.portal_id]
        return <article className="service-portal-card" key={portal.portal_id}>
          <div className="service-portal-heading"><span><Globe2 size={16} /></span><div><strong>{portal.portal_id.replaceAll('_', ' ')}</strong><a href={portal.url} target="_blank" rel="noreferrer">Open official portal <ExternalLink size={12} /></a></div></div>
          <label className="field-label">Path within this portal (optional)
            <input value={paths[portal.portal_id] || ''} onChange={(event) => setPaths((current) => ({ ...current, [portal.portal_id]: event.target.value }))} placeholder="/public-services" />
          </label>
          <Button type="button" variant="outline" disabled={Boolean(loading[portal.portal_id])} onClick={() => inspect(portal)}>
            {loading[portal.portal_id] ? <><LoaderCircle className="service-spinner" size={14} /> Inspecting…</> : <><Search size={14} /> Inspect public page</>}
          </Button>
          {errors[portal.portal_id] && <p className="grievance-error" role="alert">{errors[portal.portal_id]}</p>}
          {result && <div className="portal-inspection-result">
            <div className="portal-inspection-status"><Badge tone={result.navigation_status === 'ok' ? 'green' : 'amber'}>{result.navigation_status.replace('_', ' ')}</Badge>{result.http_status && <span>HTTP {result.http_status}</span>}</div>
            <strong>{result.title || 'Portal page'}</strong>
            {result.warnings.map((warning) => <p className="portal-warning" key={warning}>{warning}</p>)}
            {result.excerpt && <pre>{result.excerpt}</pre>}
          </div>}
        </article>
      })}</div>
      <div className="service-agent-notice"><ShieldCheck size={15} /><span>Portal content is unverified public information. Inspecting it does not sign in, store credentials, fill forms, or submit anything.</span></div>
    </Panel>
  )
}

