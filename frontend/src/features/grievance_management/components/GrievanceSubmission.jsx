import { useState } from 'react'
import { ArrowRight, CheckCircle2, Info, MapPin, ShieldCheck, Upload } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Button, PageTitle, Panel } from '../../../components/ui.jsx'
import { useSession } from '../hooks/useSession.js'
import { apiJson } from '../services/api.js'
import { SessionPanel } from './SessionPanel.jsx'

const categories = [
  'Roads & infrastructure',
  'Waste & sanitation',
  'Water supply',
  'Street lighting',
  'Public safety',
  'Other',
]
const MAX_IMAGE_BYTES = 10 * 1024 * 1024
const ACCEPTED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp']

export function GrievanceSubmission() {
  const session = useSession()
  const [form, setForm] = useState({ category: '', title: '', description: '', location: '' })
  const [coordinates, setCoordinates] = useState(null)
  const [image, setImage] = useState(null)
  const [locationMessage, setLocationMessage] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [created, setCreated] = useState(null)

  const update = (key) => (event) => setForm((current) => ({ ...current, [key]: event.target.value }))
  const captureLocation = () => {
    setLocationMessage('')
    if (!navigator.geolocation) {
      setLocationMessage('Location capture is not supported by this browser.')
      return
    }
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => {
        setCoordinates({ latitude: coords.latitude, longitude: coords.longitude })
        setLocationMessage('Coordinates captured. Add an address or landmark for the response team.')
      },
      () => setLocationMessage('Location access was not available. You can still enter the address manually.'),
      { enableHighAccuracy: true, timeout: 10000 },
    )
  }

  const chooseImage = (event) => {
    const selected = event.target.files?.[0] || null
    setError('')
    setImage(null)
    if (!selected) {
      return
    }
    if (!ACCEPTED_IMAGE_TYPES.includes(selected.type)) {
      setError('Choose a JPEG, PNG, or WebP image.')
      event.target.value = ''
      return
    }
    if (selected.size > MAX_IMAGE_BYTES) {
      setError('Images must be 10 MB or smaller.')
      event.target.value = ''
      return
    }
    setImage(selected)
  }

  const submit = async (event) => {
    event.preventDefault()
    setError('')
    setBusy(true)
    const body = new FormData()
    Object.entries(form).forEach(([key, value]) => body.append(key, value))
    if (coordinates) {
      body.append('latitude', String(coordinates.latitude))
      body.append('longitude', String(coordinates.longitude))
    }
    if (image) body.append('file', image)
    try {
      const report = await apiJson('/grievances/submit', { method: 'POST', body })
      setCreated(report)
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setBusy(false)
    }
  }

  if (session.loading) return <PageTitle eyebrow="CITIZEN SERVICES" title="Report an issue" description="Loading your secure account…" />
  if (!session.user) {
    return (
      <>
        <PageTitle eyebrow="CITIZEN SERVICES" title="Report an issue" description="Sign in or create a citizen account to securely submit and track a complaint." />
        {(session.error || error) && <p className="grievance-error" role="alert">{session.error || error}</p>}
        <SessionPanel onAuthenticated={session.setUser} />
      </>
    )
  }
  if (session.user.role !== 'citizen') {
    return <><PageTitle eyebrow="CITIZEN SERVICES" title="Report an issue" /><Panel><p>Use a citizen account to submit a complaint.</p><Button variant="light" onClick={session.logout}>Sign out</Button></Panel></>
  }
  if (created) {
    return (
      <>
        <PageTitle eyebrow="CITIZEN SERVICES" title="Report an issue" description="Your report has been saved. A staff member will review it." />
        <Panel className="success-panel grievance-success">
          <span className="success-icon"><CheckCircle2 size={28} /></span>
          <span className="eyebrow">REPORT RECEIVED · HUMAN REVIEW PENDING</span>
          <h2>Thank you for speaking up.</h2>
          <p>Keep this reference number to follow your complaint. AI suggestions are advisory and do not determine the final category, priority, or outcome.</p>
          <div className="demo-reference"><span>COMPLAINT REFERENCE</span><strong>{created.reference_number}</strong></div>
          <div className="grievance-triage-result">
            <strong>AI-assisted triage: {created.ai_triage_status === 'completed' ? 'suggestion ready' : 'unavailable'}</strong>
            {created.ai_suggested_category && <span>Suggested category: {created.ai_suggested_category}</span>}
            {created.ai_suggested_priority && <span>Suggested priority: {created.ai_suggested_priority}</span>}
            <p>{created.ai_rationale || 'A staff member will assess this report.'}</p>
          </div>
          <div className="success-actions">
            <Link className="button button-primary" to="/tracking">Track this complaint <ArrowRight size={15} /></Link>
            <button className="button button-light" onClick={() => { setCreated(null); setForm({ category: '', title: '', description: '', location: '' }); setCoordinates(null); setImage(null) }}>Submit another report</button>
          </div>
        </Panel>
      </>
    )
  }

  return (
    <>
      <PageTitle eyebrow="CITIZEN SERVICES" title="Report an issue" description="Tell us what’s happening. A staff member reviews every report and makes final decisions." action={<Button variant="light" onClick={session.logout}>Sign out</Button>} />
      <div className="form-layout">
        <Panel className="report-panel">
          <form onSubmit={submit}>
            <div className="form-section-title"><span>01</span><div><h2>What would you like to report?</h2><p>AI suggestions help direct your report but are not decisions.</p></div></div>
            <label className="field-label">Issue category <span>*</span>
              <select required value={form.category} onChange={update('category')}>
                <option value="">Select a category</option>
                {categories.map((category) => <option key={category}>{category}</option>)}
              </select>
            </label>
            <label className="field-label">Short description <span>*</span>
              <input required minLength={5} maxLength={180} value={form.title} onChange={update('title')} placeholder="e.g. Streetlight not working on 12th Main Road" />
            </label>
            <label className="field-label">Tell us a little more <span>*</span>
              <textarea required minLength={10} maxLength={10000} rows="4" value={form.description} onChange={update('description')} placeholder="Share what happened, when you noticed it, and details that may help..." />
            </label>
            <div className="form-section-title second-section"><span>02</span><div><h2>Where is the issue?</h2><p>An address and optional device coordinates help staff locate it.</p></div></div>
            <label className="field-label">Address or landmark <span>*</span>
              <div className="input-with-icon"><MapPin size={16} /><input required minLength={3} maxLength={240} value={form.location} onChange={update('location')} placeholder="Street, neighborhood, or landmark" /></div>
            </label>
            <div className="grievance-location-action">
              <Button type="button" variant="outline" onClick={captureLocation}><MapPin size={15} /> Capture my location</Button>
              {coordinates && <span>{coordinates.latitude.toFixed(5)}, {coordinates.longitude.toFixed(5)}</span>}
            </div>
            {locationMessage && <p className="grievance-help-text" role="status">{locationMessage}</p>}
            <div className="field-label">Add a photo <small>(optional)</small>
              <label className="upload-zone"><Upload size={19} /><strong>{image?.name || 'Choose a JPEG, PNG, or WebP image'}</strong><small>Up to 10 MB · stored with this complaint</small>
                <input type="file" accept="image/jpeg,image/png,image/webp" onChange={chooseImage} />
              </label>
            </div>
            <div className="form-consent"><ShieldCheck size={16} /><span>Do not include sensitive personal information. Report text is processed by the configured AI provider for an advisory triage suggestion; a person reviews every report.</span></div>
            {error && <p className="grievance-error" role="alert">{error}</p>}
            <div className="form-actions"><span><span className="required-star">*</span> Required fields</span><Button type="submit" disabled={busy}>{busy ? 'Submitting…' : 'Submit report'} <ArrowRight size={15} /></Button></div>
          </form>
        </Panel>
        <div className="report-sidebar">
          <div className="report-help-card"><div className="report-help-icon"><Info size={20} /></div><h3>What happens next?</h3>
            <div className="next-step"><span>1</span><div><strong>AI suggests a category and priority</strong><p>The suggestion is advisory and may be unavailable.</p></div></div>
            <div className="next-step"><span>2</span><div><strong>A staff member reviews it</strong><p>Important classification and priority decisions remain with a human.</p></div></div>
            <div className="next-step"><span>3</span><div><strong>Track progress by reference</strong><p>Sign in to see your reports or use the complaint reference.</p></div></div>
          </div>
          <div className="safety-note"><Info size={17} /><div><strong>Is anyone in immediate danger?</strong><p>This portal is not for emergencies. Contact local emergency services for urgent help.</p></div></div>
        </div>
      </div>
    </>
  )
}
