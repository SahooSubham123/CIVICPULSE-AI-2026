import { useEffect, useMemo, useState } from 'react'
import { Link, Navigate, Route, Routes } from 'react-router-dom'
import {
  Activity, ArrowDownRight, ArrowRight, ArrowUpRight, BadgeCheck, Banknote, Bot, BriefcaseBusiness,
  Building, Check, CheckCircle2, ChevronDown, ChevronRight, CircleAlert, Clock3, FileCheck2,
  FileSearch, FileText, Filter, Flag, Globe2, HeartHandshake, HelpCircle, Home, Info, MapPin,
  MessageCircle, MessageSquare, MoreHorizontal, Plus, Search, Send, ShieldCheck, Sparkles,
  TrendingUp, Upload, Users, Waves, X,
} from 'lucide-react'
import { AppLayout } from './components/Layout.jsx'
import { Badge, Button, EmptyState, PageTitle, Panel, SectionHeading, StatCard } from './components/ui.jsx'
import { AdminGrievances } from './features/grievance_management/components/AdminGrievances.jsx'
import { CitizenTracking } from './features/grievance_management/components/CitizenTracking.jsx'
import { GrievanceSubmission } from './features/grievance_management/components/GrievanceSubmission.jsx'
import { FactVerification } from './features/fact_verification/components/FactVerification.jsx'
import { PolicyExplainer } from './features/policy_explainer/components/PolicyExplainer.jsx'
import { apiJson, getToken } from './features/grievance_management/services/api.js'
import { GovernmentServiceAssistant } from './features/service_assistant/components/GovernmentServiceAssistant.jsx'

const schemes = [
  { name: 'PM Kisan Samman Nidhi', category: 'Agriculture', detail: 'Income support for eligible farmer families across India.', benefit: '₹6,000 / year', eligibility: 'Small and marginal landholding farmer families', icon: Waves, color: 'green', match: 'Likely eligible' },
  { name: 'Ayushman Bharat PM-JAY', category: 'Healthcare', detail: 'Health cover for secondary and tertiary care hospitalization.', benefit: 'Up to ₹5 lakh', eligibility: 'Eligible low-income and vulnerable families', icon: HeartHandshake, color: 'blue', match: 'Check eligibility' },
  { name: 'PM Awas Yojana – Urban', category: 'Housing', detail: 'Support for eligible urban households to access pucca housing.', benefit: 'Housing assistance', eligibility: 'Urban households without a pucca house', icon: Home, color: 'purple', match: 'Likely eligible' },
  { name: 'Sukanya Samriddhi Yojana', category: 'Family', detail: 'A savings scheme for the future of a girl child.', benefit: 'Tax-advantaged savings', eligibility: 'Guardians of a girl child under 10 years', icon: Sparkles, color: 'orange', match: 'Check eligibility' },
  { name: 'National Scholarship Portal', category: 'Education', detail: 'A single-window platform for multiple student scholarships.', benefit: 'Varies by scholarship', eligibility: 'Students meeting scheme-specific criteria', icon: FileText, color: 'blue', match: 'Explore schemes' },
  { name: 'PM SVANidhi', category: 'Livelihood', detail: 'Working-capital loans for eligible street vendors.', benefit: 'Loan up to ₹50,000', eligibility: 'Street vendors with required local documentation', icon: Banknote, color: 'green', match: 'Explore scheme' },
]

const complaintSeed = [
  { id: 'CP-2025-08421', title: 'Streetlight not working', location: 'Indiranagar, Bengaluru', date: '12 Jun 2025', status: 'In progress', tone: 'amber', progress: 66 },
  { id: 'CP-2025-07108', title: 'Garbage collection missed', location: 'Indiranagar, Bengaluru', date: '04 Jun 2025', status: 'Resolved', tone: 'green', progress: 100 },
  { id: 'CP-2025-06377', title: 'Pothole on 12th Main Road', location: 'Indiranagar, Bengaluru', date: '29 May 2025', status: 'Received', tone: 'blue', progress: 25 },
]

const categories = ['All schemes', 'Agriculture', 'Healthcare', 'Housing', 'Education', 'Livelihood', 'Family']

function Dashboard() {
  const [complaints, setComplaints] = useState([])
  const [complaintsLoading, setComplaintsLoading] = useState(Boolean(getToken()))
  const [complaintsError, setComplaintsError] = useState('')

  useEffect(() => {
    if (!getToken()) return undefined
    let active = true
    apiJson('/grievances?limit=5')
      .then((response) => { if (active) setComplaints(response.items) })
      .catch((error) => { if (active) setComplaintsError(error.message) })
      .finally(() => { if (active) setComplaintsLoading(false) })
    return () => { active = false }
  }, [])

  const activeComplaints = complaints.filter((item) => item.status === 'received' || item.status === 'in_progress').length
  return (
    <>
      <PageTitle eyebrow="TUESDAY, 17 JUNE 2025" title={<>Good morning, Arjun <span className="title-wave">✳</span></>} description="Your civic life, all in one place. Here's what needs your attention." action={<Button variant="light" onClick={() => window.print()}><FileText size={16} /> Download overview</Button>} />
      <div className="welcome-strip">
        <div className="welcome-art"><span className="art-sun" /><span className="art-building art-one" /><span className="art-building art-two" /><span className="art-building art-three" /><span className="art-path" /></div>
        <div className="welcome-copy">
          <div className="welcome-kicker"><span className="live-dot" /> YOUR CIVIC PULSE</div>
          <h2>Making your city<br />work better for you.</h2>
          <p>Access trusted services, track what matters, and make your voice count.</p>
          <Link to="/services" className="welcome-link">Explore services <ArrowRight size={15} /></Link>
        </div>
        <div className="welcome-side-note"><span>YOUR CITY AT A GLANCE</span><strong>Bengaluru</strong><small><MapPin size={13} /> Karnataka, India</small></div>
      </div>
      <div className="stats-grid">
        <StatCard label="Active complaints" value={getToken() ? activeComplaints : '—'} note={getToken() ? 'From your reports' : 'Sign in to see your reports'} icon={MessageSquare} tone="blue" />
        <StatCard label="Services explored" value="08" note="Across 4 categories" icon={Building} tone="purple" />
        <StatCard label="Schemes you may qualify for" value="04" note="Based on your profile" icon={BadgeCheck} tone="green" />
        <StatCard label="Community impact" value="#12" note="In your ward this month" icon={TrendingUp} tone="orange" />
      </div>
      <div className="content-grid dashboard-grid">
        <Panel>
          <SectionHeading title="Your recent activity" subtitle="Stay on top of things that matter" action={<Link className="subtle-link" to="/tracking">View all <ArrowRight size={14} /></Link>} />
          <div className="activity-list">
            {complaintsLoading && <p className="grievance-help-text">Loading your complaints…</p>}
            {complaintsError && <p className="grievance-error" role="alert">{complaintsError}</p>}
            {!getToken() && <div className="activity-item"><span className="activity-symbol icon-blue"><FileSearch size={17} /></span><div className="activity-copy"><strong>Complaint updates appear here</strong><span>Sign in through the tracking page to view your reports</span></div></div>}
            {getToken() && !complaintsLoading && !complaintsError && !complaints.length && <div className="activity-item"><span className="activity-symbol icon-blue"><FileSearch size={17} /></span><div className="activity-copy"><strong>No complaints submitted yet</strong><span>Reports you submit will be listed here</span></div><Link className="subtle-link" to="/grievances/new">Report an issue</Link></div>}
            {complaints.map((item) => <div className="activity-item" key={item.id}>
              <span className={`activity-symbol icon-${item.status === 'resolved' ? 'green' : item.status === 'in_progress' ? 'amber' : 'blue'}`}><Flag size={17} /></span>
              <div className="activity-copy"><strong>{item.title}</strong><span>{item.reference_number} · {item.location}</span></div>
              <Badge tone={item.status === 'resolved' ? 'green' : item.status === 'in_progress' ? 'amber' : 'blue'}>{item.status.replace('_', ' ')}</Badge>
            </div>)}
            <div className="activity-item">
              <span className="activity-symbol icon-purple"><FileSearch size={17} /></span>
              <div className="activity-copy"><strong>Explored Ayushman Bharat PM-JAY</strong><span>Government schemes · 10 Jun 2025</span></div>
              <Badge tone="purple">Saved</Badge>
            </div>
          </div>
        </Panel>
        <Panel className="assistant-promo">
          <div className="assistant-orbit"><div className="orbit-dot" /><Bot size={25} /></div>
          <div className="promo-label"><Sparkles size={13} /> YOUR AI CIVIC ASSISTANT</div>
          <h3>Not sure where<br />to start?</h3>
          <p>Ask a question in your language. We'll help you find the right service.</p>
          <Link to="/assistant" className="button button-primary promo-button">Ask Civic AI <ArrowRight size={15} /></Link>
          <div className="promo-foot"><ShieldCheck size={14} /> Private, secure, and here to help</div>
        </Panel>
      </div>
      <Panel className="scheme-highlight">
        <div className="scheme-highlight-icon"><HeartHandshake size={22} /></div>
        <div className="scheme-highlight-copy"><span className="eyebrow">PERSONALIZED FOR YOU</span><h3>Benefits you might be missing</h3><p>We found 4 government schemes that could be relevant to you.</p></div>
        <Link to="/schemes" className="button button-light">Explore schemes <ArrowRight size={15} /></Link>
      </Panel>
    </>
  )
}

function ComplaintRow({ item, compact = false }) {
  return (
    <div className="complaint-row">
      <span className={`activity-symbol icon-${item.tone}`}><Flag size={17} /></span>
      <div className="activity-copy"><strong>{item.title}</strong><span>{item.id} <i>·</i> {item.location}</span></div>
      <div className="complaint-meta">{!compact && <small>{item.date}</small>}<Badge tone={item.tone}>{item.status}</Badge></div>
    </div>
  )
}

function Assistant() {
  const [messages, setMessages] = useState([
    { from: 'assistant', text: 'Namaste, Arjun! I’m Civic AI, your guide to public services. What can I help you with today?' },
    { from: 'user', text: 'How can I apply for a ration card?' },
    { from: 'assistant', text: 'I can help you with that. In Karnataka, ration card applications are handled through the Ahara portal. You’ll generally need identity and address proof for each family member. Would you like a step-by-step guide, or should I first help check which documents you have ready?' },
  ])
  const [draft, setDraft] = useState('')
  const sendMessage = (event) => {
    event.preventDefault()
    const text = draft.trim()
    if (!text) return
    setMessages((items) => [...items, { from: 'user', text }, { from: 'assistant', text: 'I can help you find trusted information and the next steps for that. Tell me your state or city if you would like guidance specific to your location.' }])
    setDraft('')
  }
  return (
    <>
      <PageTitle eyebrow="CIVIC AI" title="Your civic assistant" description="A little help navigating public services goes a long way." />
      <div className="assistant-layout">
        <Panel className="chat-panel">
          <div className="chat-head"><div className="chat-avatar"><Bot size={20} /></div><div><strong>Civic AI assistant</strong><span><i className="live-dot" /> Available now · English</span></div><button className="icon-quiet" aria-label="More options"><MoreHorizontal size={20} /></button></div>
          <div className="chat-context"><ShieldCheck size={15} /><span>Answers are based on trusted public information. Always verify requirements with the official department.</span></div>
          <div className="chat-messages">
            <div className="chat-date">TODAY, 17 JUNE</div>
            {messages.map((message, index) => <div key={`${index}-${message.text}`} className={`message-row ${message.from === 'user' ? 'message-user' : ''}`}>
              {message.from === 'assistant' && <span className="mini-bot"><Bot size={14} /></span>}
              <div className="message-bubble">{message.text}</div>
            </div>)}
          </div>
          <div className="suggestion-row"><span>TRY ASKING</span>{['Find a nearby service center', 'Check my scheme eligibility'].map((suggestion) => <button key={suggestion} onClick={() => setDraft(suggestion)}>{suggestion} <ArrowUpRight size={12} /></button>)}</div>
          <form className="chat-composer" onSubmit={sendMessage}><input value={draft} onChange={(event) => setDraft(event.target.value)} placeholder="Ask anything about public services..." aria-label="Your question" /><button type="button" className="composer-attach" aria-label="Attach a file"><Upload size={17} /></button><button type="submit" className="send-button" aria-label="Send message" disabled={!draft.trim()}><Send size={17} /></button></form>
          <div className="chat-disclaimer">Civic AI can make mistakes. Please double-check important information.</div>
        </Panel>
        <div className="assistant-side">
          <Panel className="quick-help"><SectionHeading title="What I can help with" /><div className="help-topic-list">
            {[['Government schemes', 'Find benefits you may be eligible for', Building], ['Civic complaints', 'Report and track local issues', Flag], ['Public services', 'Understand how to access services', BadgeCheck], ['Official information', 'Get clear, sourced explanations', FileSearch]].map(([title, detail, Icon]) => <div className="help-topic" key={title}><span><Icon size={17} /></span><div><strong>{title}</strong><small>{detail}</small></div><ChevronRight size={15} /></div>)}
          </div></Panel>
          <div className="privacy-card"><ShieldCheck size={18} /><div><strong>Your privacy matters</strong><p>Your conversations are private and are not used to make decisions about your access to services.</p><Link to="/services">Learn about our approach <ArrowRight size={13} /></Link></div></div>
        </div>
      </div>
    </>
  )
}

function Schemes() {
  const [query, setQuery] = useState('')
  const [category, setCategory] = useState('All schemes')
  const [saved, setSaved] = useState([])
  const filtered = useMemo(() => schemes.filter((scheme) => (category === 'All schemes' || scheme.category === category) && `${scheme.name} ${scheme.category} ${scheme.detail}`.toLowerCase().includes(query.toLowerCase())), [query, category])
  const toggleSaved = (name) => setSaved((current) => current.includes(name) ? current.filter((value) => value !== name) : [...current, name])
  return (
    <>
      <PageTitle eyebrow="DISCOVER YOUR BENEFITS" title="Government schemes" description="Understand the support available to you, in clear and simple language." action={<Button variant="light"><Globe2 size={16} /> English <ChevronDown size={14} /></Button>} />
      <div className="scheme-intro">
        <div><span className="eyebrow">A GOOD PLACE TO BEGIN</span><h2>Benefits, made easier to find.</h2><p>Explore verified central and state government schemes. Eligibility is a guide — final decisions are made by the relevant department.</p></div>
        <div className="scheme-intro-art"><span className="intro-circle circle-back" /><span className="intro-circle circle-front"><Building size={35} /></span><span className="intro-spark"><Sparkles size={18} /></span></div>
      </div>
      <Panel className="schemes-panel"><div className="scheme-tools"><div className="search-field"><Search size={17} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search schemes, benefits, or keywords..." aria-label="Search schemes" />{query && <button onClick={() => setQuery('')} aria-label="Clear search"><X size={15} /></button>}</div><Button variant="outline"><Filter size={15} /> Filters</Button></div>
        <div className="category-tabs" role="tablist" aria-label="Scheme categories">{categories.map((item) => <button role="tab" aria-selected={category === item} className={category === item ? 'category-active' : ''} onClick={() => setCategory(item)} key={item}>{item}</button>)}</div>
        <div className="scheme-grid">{filtered.map((item) => <SchemeCard item={item} saved={saved.includes(item.name)} onSave={() => toggleSaved(item.name)} key={item.name} />)}</div>
        {!filtered.length && <EmptyState icon={Search} title="No schemes found" description="Try another search or choose a different category." />}
        <div className="scheme-note"><Info size={15} /><span>Scheme details are for guidance. Please confirm current eligibility and application requirements on the official portal.</span><a href="https://www.myscheme.gov.in/" target="_blank" rel="noreferrer">myScheme.gov.in <ArrowUpRight size={12} /></a></div>
      </Panel>
    </>
  )
}

function SchemeCard({ item, saved, onSave }) {
  const Icon = item.icon
  const [expanded, setExpanded] = useState(false)
  return <article className="scheme-card"><div className="scheme-card-top"><span className={`scheme-icon scheme-${item.color}`}><Icon size={20} /></span><button className={`save-scheme ${saved ? 'saved' : ''}`} onClick={onSave} aria-label={saved ? 'Remove saved scheme' : 'Save scheme'}>{saved ? <Check size={15} /> : <Plus size={16} />}</button></div><div className="scheme-category">{item.category}</div><h3>{item.name}</h3><p>{item.detail}</p><div className="benefit-line"><span>KEY BENEFIT</span><strong>{item.benefit}</strong></div>{expanded && <div className="eligibility-detail"><strong>Who may be eligible</strong><p>{item.eligibility}</p></div>}<div className="scheme-card-bottom"><Badge tone={item.match === 'Likely eligible' ? 'green' : 'blue'}>{item.match}</Badge><button className="card-arrow" onClick={() => setExpanded(!expanded)} aria-label={expanded ? 'Hide eligibility details' : 'Show eligibility details'}><ArrowRight size={16} /></button></div></article>
}

function GrievanceForm() {
  const [submitted, setSubmitted] = useState(false)
  const [form, setForm] = useState({ category: '', title: '', details: '', location: '' })
  const update = (key) => (event) => setForm((current) => ({ ...current, [key]: event.target.value }))
  const submit = (event) => { event.preventDefault(); setSubmitted(true) }
  if (submitted) return <><PageTitle eyebrow="CITIZEN SERVICES" title="Report an issue" description="Your voice helps make public services better." /><Panel className="success-panel"><span className="success-icon"><CheckCircle2 size={28} /></span><span className="eyebrow">REPORT RECEIVED</span><h2>Thank you for speaking up.</h2><p>Your report has been saved in this demo. In the live service, you’ll receive a reference number and updates from the responsible department.</p><div className="demo-reference"><span>DEMO REFERENCE</span><strong>CP-2025-09124</strong></div><div className="success-actions"><Link className="button button-primary" to="/tracking">Go to complaint tracking <ArrowRight size={15} /></Link><button className="button button-light" onClick={() => { setSubmitted(false); setForm({ category: '', title: '', details: '', location: '' }) }}>Submit another report</button></div></Panel></>
  return <><PageTitle eyebrow="CITIZEN SERVICES" title="Report an issue" description="Tell us what’s happening in your community. We’ll help direct it to the right team." /><div className="form-layout"><Panel className="report-panel"><form onSubmit={submit}><div className="form-section-title"><span>01</span><div><h2>What would you like to report?</h2><p>Choose the option that best describes the issue.</p></div></div><label className="field-label">Issue category <span>*</span><select required value={form.category} onChange={update('category')}><option value="">Select a category</option>{['Roads & infrastructure', 'Waste & sanitation', 'Water supply', 'Street lighting', 'Public safety', 'Other'].map((option) => <option key={option}>{option}</option>)}</select></label><label className="field-label">Short description <span>*</span><input required maxLength={100} value={form.title} onChange={update('title')} placeholder="e.g. Streetlight not working on 12th Main Road" /></label><label className="field-label">Tell us a little more <span>*</span><textarea required rows="4" value={form.details} onChange={update('details')} placeholder="Share what happened, when you noticed it, and any details that might help..." /></label><div className="form-section-title second-section"><span>02</span><div><h2>Where is the issue?</h2><p>A precise location helps the right team respond.</p></div></div><label className="field-label">Address or landmark <span>*</span><div className="input-with-icon"><MapPin size={16} /><input required value={form.location} onChange={update('location')} placeholder="Street, neighborhood, or landmark" /></div></label><div className="field-label"><div>Add a photo <small>(optional)</small></div><label className="upload-zone"><Upload size={19} /><strong>Choose a file or drag it here</strong><small>JPG or PNG, up to 10 MB</small><input type="file" accept="image/png,image/jpeg" /></label></div><div className="form-consent"><ShieldCheck size={16} /><span>Your contact details will only be used to share updates about this report. Please don’t include sensitive personal information.</span></div><div className="form-actions"><span><span className="required-star">*</span> Required fields</span><Button type="submit">Submit report <ArrowRight size={15} /></Button></div></form></Panel><div className="report-sidebar"><div className="report-help-card"><div className="report-help-icon"><HelpCircle size={20} /></div><h3>What happens next?</h3><div className="next-step"><span>1</span><div><strong>We’ll review your report</strong><p>Our team checks the details and routes it to the right department.</p></div></div><div className="next-step"><span>2</span><div><strong>You’ll get a reference ID</strong><p>Use it to check the status of your report at any time.</p></div></div><div className="next-step"><span>3</span><div><strong>We’ll keep you updated</strong><p>Get notified when there’s progress or a resolution.</p></div></div></div><div className="safety-note"><Info size={17} /><div><strong>Is anyone in immediate danger?</strong><p>This portal is not for emergencies. Contact your local emergency services if you need urgent help.</p></div></div></div></div></>
}

function Tracking() {
  const [reference, setReference] = useState('')
  const [searched, setSearched] = useState(false)
  const [filter, setFilter] = useState('All reports')
  const results = complaintSeed.filter((item) => (filter === 'All reports' || item.status === filter) && (!searched || !reference || item.id.toLowerCase().includes(reference.toLowerCase())))
  const search = (event) => { event.preventDefault(); setSearched(true) }
  return <><PageTitle eyebrow="CITIZEN SERVICES" title="Track a complaint" description="Follow your reports and see the latest update from your local team." action={<Link to="/grievances/new" className="button button-primary"><Plus size={16} /> New report</Link>} /><Panel className="tracking-search-panel"><div className="tracking-search-copy"><span className="search-art-icon"><FileSearch size={22} /></span><div><h2>Looking for a specific report?</h2><p>Enter your reference number to find its latest status.</p></div></div><form className="tracking-search-form" onSubmit={search}><input aria-label="Complaint reference number" value={reference} onChange={(event) => setReference(event.target.value)} placeholder="e.g. CP-2025-08421" /><Button type="submit"><Search size={15} /> Track report</Button></form></Panel><div className="list-toolbar"><div><h2>Your reports <span className="count-pill">{results.length}</span></h2><p>Reports submitted from your citizen account</p></div><div className="filter-select"><Filter size={15} /><select value={filter} onChange={(event) => setFilter(event.target.value)} aria-label="Filter reports"><option>All reports</option><option>Received</option><option>In progress</option><option>Resolved</option></select><ChevronDown size={13} /></div></div>{results.length ? <div className="tracking-list">{results.map((item) => <TrackingCard key={item.id} item={item} />)}</div> : <Panel><EmptyState icon={FileSearch} title="No matching reports" description="Check the reference number or change your filters." /></Panel>}<div className="tracking-footnote"><Info size={14} /> Status information is a demo and is not connected to a government department.</div></>
}

function TrackingCard({ item }) {
  return <Panel className="tracking-card"><div className="tracking-card-head"><span className={`tracking-category-icon icon-${item.tone}`}><Flag size={18} /></span><div className="tracking-main"><div className="tracking-title-line"><h3>{item.title}</h3><Badge tone={item.tone}>{item.status}</Badge></div><div className="tracking-details"><span><FileText size={13} /> {item.id}</span><span><MapPin size={13} /> {item.location}</span><span><Clock3 size={13} /> Reported {item.date}</span></div></div><button className="icon-quiet" aria-label={`More options for ${item.title}`}><MoreHorizontal size={20} /></button></div><div className="progress-track"><span style={{ width: `${item.progress}%` }} /></div><div className="tracking-card-foot"><span>{item.status === 'Resolved' ? 'Your report has been marked as resolved.' : item.status === 'In progress' ? 'The responsible team is working on your report.' : 'Your report has been received and is awaiting review.'}</span><button className="subtle-link">View updates <ArrowRight size={14} /></button></div></Panel>
}

function Services() {
  const [selected, setSelected] = useState('')
  const [query, setQuery] = useState('')
  const serviceItems = [
    { title: 'Identity & certificates', detail: 'Get help with essential documents and certificates.', icon: FileCheck2, tone: 'blue', services: ['Birth certificate', 'Income certificate', 'Caste certificate'] },
    { title: 'Health & family', detail: 'Explore healthcare, family, and social support services.', icon: HeartHandshake, tone: 'green', services: ['Health coverage', 'Maternity benefits', 'Senior citizen support'] },
    { title: 'Housing & utilities', detail: 'Find housing support and essential utility services.', icon: Home, tone: 'purple', services: ['Housing assistance', 'Water connection', 'Electricity services'] },
    { title: 'Education & skills', detail: 'Discover scholarships, training, and learning resources.', icon: BriefcaseBusiness, tone: 'orange', services: ['Student scholarships', 'Skill development', 'Education loans'] },
    { title: 'Work & livelihoods', detail: 'Find employment support and livelihood programs.', icon: Banknote, tone: 'green', services: ['Job seeker services', 'Small business support', 'Farmer services'] },
    { title: 'Local civic services', detail: 'Connect with the services that keep your community running.', icon: Building, tone: 'blue', services: ['Pay property tax', 'Waste collection', 'Streetlight issue'] },
  ]
  const filteredServices = serviceItems.filter((item) => `${item.title} ${item.detail} ${item.services.join(' ')}`.toLowerCase().includes(query.toLowerCase()))
  const chosen = serviceItems.find((item) => item.title === selected)
  const findService = () => {
    if (filteredServices[0]) setSelected(filteredServices[0].title)
  }
  return <><PageTitle eyebrow="SERVICE ASSISTANT" title="How can we help?" description="Tell us what you need. We’ll help you understand the process and find the right place to start." /><div className="service-search"><Sparkles size={19} /><input aria-label="Describe the service you need" value={query} onChange={(event) => setQuery(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter') findService() }} placeholder="Describe what you’re trying to do..." /><Button onClick={findService} disabled={!filteredServices.length}><Search size={15} /> Find a service</Button></div>{chosen && <Panel className="service-detail-panel"><button className="detail-close" onClick={() => setSelected('')} aria-label="Close service details"><X size={17} /></button><span className="eyebrow">GETTING STARTED</span><h2>{chosen.title}</h2><p>Choose a service below to see a simple checklist. You can always confirm the latest process with the official department.</p><div className="service-options">{chosen.services.map((service, index) => <button key={service} onClick={(event) => { event.currentTarget.classList.toggle('option-selected') }}><span>{index + 1}</span>{service}<ChevronRight size={15} /></button>)}</div></Panel>}{filteredServices.length ? <div className="service-grid">{filteredServices.map((item) => { const Icon = item.icon; return <button className={`service-card ${selected === item.title ? 'service-card-selected' : ''}`} key={item.title} onClick={() => setSelected(selected === item.title ? '' : item.title)}><span className={`service-icon icon-${item.tone}`}><Icon size={20} /></span><h3>{item.title}</h3><p>{item.detail}</p><span className="service-card-foot">{item.services.length} common services <ArrowRight size={14} /></span></button> })}</div> : <Panel><EmptyState icon={Search} title="No matching services" description="Try searching for something else, like health, housing, or certificates." /></Panel>}<div className="service-help-bar"><span className="help-bar-icon"><MessageCircle size={18} /></span><span><strong>Prefer to ask a person?</strong><small>Our AI assistant can guide you in plain language.</small></span><Link to="/assistant" className="button button-outline">Chat with Civic AI <ArrowRight size={14} /></Link></div></>
}

function Verify() {
  const [claim, setClaim] = useState('')
  const [checked, setChecked] = useState(false)
  const [fileName, setFileName] = useState('')
  const verify = (event) => { event.preventDefault(); if (claim.trim() || fileName) setChecked(true) }
  return <><PageTitle eyebrow="TRUSTED INFORMATION" title="Fact verification" description="Check claims and media with transparent context from credible sources." action={<Button variant="light"><Info size={15} /> How it works</Button>} /><div className="verify-banner"><div className="verify-badge"><ShieldCheck size={22} /></div><div><strong>A more informed community starts with a question.</strong><p>Share a claim or media item to see how to check it. This demo provides guidance only and does not connect to a live fact-checking service.</p></div><span className="verify-decoration"><Sparkles size={28} /></span></div><div className="verify-grid"><Panel className="verify-form-panel"><div className="verify-heading"><span className="eyebrow">START A CHECK</span><h2>What would you like to verify?</h2><p>Paste a statement or add a public media link. Avoid uploading private or sensitive material.</p></div><form onSubmit={verify}><label className="field-label">Claim or statement<textarea rows="5" value={claim} onChange={(event) => { setClaim(event.target.value); setChecked(false) }} placeholder="Paste the claim you came across..." /></label><div className="form-divider"><span>OR</span></div><div className="field-label"><div>Add a public link or image</div><label className="upload-zone verify-upload"><Upload size={18} /><strong>{fileName || 'Choose a file to review'}</strong><small>Image or video · Keep personal information private</small><input type="file" accept="image/*,video/*" onChange={(event) => { setFileName(event.target.files?.[0]?.name || ''); setChecked(false) }} /></label></div><Button type="submit" disabled={!claim.trim() && !fileName}><ShieldCheck size={16} /> Review claim</Button></form></Panel><div className="verify-side"><Panel className="verification-principles"><SectionHeading title="A thoughtful check" subtitle="Good verification includes more than a label." /><div className="principle-list">{[['Find the original', 'Look for the earliest source and full context.'], ['Check credible sources', 'Compare with official notices and trusted reporting.'], ['Read beyond the headline', 'Details and dates can change what a claim means.']].map(([title, detail], index) => <div className="principle" key={title}><span>{index + 1}</span><div><strong>{title}</strong><p>{detail}</p></div></div>)}</div></Panel><Panel className="verify-latest"><div className="latest-top"><span><Activity size={15} /> COMMUNITY PULSE</span><Badge tone="green">Updated today</Badge></div><strong>3 claims reviewed</strong><p>in your community this week</p><div className="mini-bars">{[38, 65, 48, 82, 57, 91, 67, 74, 53, 87, 62, 94].map((height, index) => <i key={index} style={{ height: `${height}%` }} />)}</div><span className="bars-labels"><small>MON</small><small>TODAY</small></span></Panel></div></div>{checked && <Panel className="check-result"><span className="result-info"><Info size={18} /></span><div><strong>Your check is ready to investigate</strong><p>This demo does not perform an automated fact check. To evaluate the claim, locate its original source, check the date and context, and compare it with official or independently reported information.</p></div><button onClick={() => setChecked(false)} aria-label="Dismiss result"><X size={17} /></button></Panel>}<div className="responsible-note"><ShieldCheck size={15} /> Avoid resharing a claim until you’ve checked the original source and context.</div></>
}

function PublicDashboard() {
  const [area, setArea] = useState('Indiranagar')
  return <><PageTitle eyebrow="OPEN CIVIC DATA" title="Your community, in focus." description="A transparent look at local reports and service activity. Personal details are never shown." action={<div className="filter-select"><MapPin size={15} /><select value={area} onChange={(event) => setArea(event.target.value)} aria-label="Choose ward"><option>Indiranagar</option><option>Domlur</option><option>Ulsoor</option></select><ChevronDown size={13} /></div>} /><div className="public-banner"><div><span className="public-live"><i className="live-dot" /> LIVE COMMUNITY PULSE</span><h2>Better insight.<br />Stronger neighborhoods.</h2><p>See how residents and local teams are working together in {area}.</p></div><div className="public-banner-art"><span className="pulse-ring ring-one" /><span className="pulse-ring ring-two" /><span className="pulse-center"><Activity size={24} /></span><span className="pulse-point point-one" /><span className="pulse-point point-two" /><span className="pulse-point point-three" /></div></div><div className="stats-grid public-stats"><StatCard label="Reports this month" value="1,284" note={<><ArrowDownRight size={13} /> 8% from last month</>} icon={MessageSquare} tone="blue" /><StatCard label="Resolved this month" value="1,036" note="81% resolution rate" icon={CheckCircle2} tone="green" /><StatCard label="Median response time" value="2.4 days" note="Across all categories" icon={Clock3} tone="purple" /><StatCard label="Active contributors" value="3,812" note="Residents making a difference" icon={Users} tone="orange" /></div><div className="content-grid public-content"><Panel className="chart-panel"><SectionHeading title="Reports over time" subtitle="Community reports · Last 7 days" action={<button className="chart-period">This week <ChevronDown size={13} /></button>} /><div className="chart-legend"><span><i className="legend-blue" /> Reports received</span><span><i className="legend-green" /> Resolved</span></div><div className="bar-chart">{[['MON', 46, 28], ['TUE', 70, 52], ['WED', 56, 42], ['THU', 88, 59], ['FRI', 62, 45], ['SAT', 40, 31], ['SUN', 75, 58]].map(([day, received, resolved]) => <div className="chart-column" key={day}><div className="chart-bars"><i style={{ height: `${received}%` }} /><i style={{ height: `${resolved}%` }} /></div><span>{day}</span></div>)}</div><div className="chart-foot"><span><TrendingUp size={14} /> <strong>+12.8%</strong> more reports resolved this week</span><span>Source: civic reports</span></div></Panel><Panel className="category-panel"><SectionHeading title="Top issue categories" subtitle={`In ${area} this month`} /><div className="category-ranking">{[['Roads & infrastructure', 82, '426'], ['Waste & sanitation', 68, '352'], ['Water supply', 47, '244'], ['Street lighting', 36, '187']].map(([title, percent, count], index) => <div className="rank-item" key={title}><div className="rank-label"><span><i>{String(index + 1).padStart(2, '0')}</i>{title}</span><strong>{count}</strong></div><div className="rank-track"><i style={{ width: `${percent}%` }} /></div></div>)}</div><Link to="/grievances/new" className="subtle-link category-link">Report a local issue <ArrowRight size={14} /></Link></Panel></div><div className="public-footnote"><Info size={14} /> Aggregated demo data shown for illustration. Individual reports are never publicly identifiable.</div></>
}

function AdminDashboard() {
  const [tab, setTab] = useState('All reports')
  const [items, setItems] = useState(complaintSeed.map((item) => ({ ...item, assigned: item.status !== 'Received' })))
  const tabs = ['All reports', 'Needs review', 'In progress', 'Resolved']
  const visible = items.filter((item) => tab === 'All reports' || (tab === 'Needs review' ? item.status === 'Received' : item.status === tab))
  const updateStatus = (id, status) => setItems((current) => current.map((item) => item.id === id ? { ...item, status, tone: status === 'Resolved' ? 'green' : status === 'In progress' ? 'amber' : 'blue', assigned: true } : item))
  return <><PageTitle eyebrow="DEPARTMENT WORKSPACE" title="Service operations" description="A snapshot of incoming reports and your team’s response." action={<Button variant="outline"><DownloadIcon /> Export reports</Button>} /><div className="admin-notice"><ShieldCheck size={16} /><span>Staff workspace</span><i>·</i><span>Demo data only — no live government systems are connected.</span></div><div className="stats-grid admin-stats"><StatCard label="Open reports" value="248" note="Across 12 wards" icon={MessageSquare} tone="blue" /><StatCard label="Needs review" value="36" note="11 received today" icon={CircleAlert} tone="orange" /><StatCard label="In progress" value="157" note="Assigned to your teams" icon={Clock3} tone="purple" /><StatCard label="Resolved this month" value="1,036" note={<><span className="note-up">↑ 8.2%</span> vs last month</>} icon={CheckCircle2} tone="green" /></div><Panel className="admin-table-panel"><div className="admin-table-toolbar"><SectionHeading title="Incoming reports" subtitle="Review and coordinate citizen submissions" /><button className="table-more"><MoreHorizontal size={19} /></button></div><div className="admin-tabs">{tabs.map((item) => <button key={item} className={tab === item ? 'admin-tab-active' : ''} onClick={() => setTab(item)}>{item}{item === 'Needs review' && <span>36</span>}</button>)}</div><div className="report-table-wrap"><table className="report-table"><thead><tr><th>REPORT</th><th>LOCATION</th><th>SUBMITTED</th><th>STATUS</th><th>TEAM</th><th /></tr></thead><tbody>{visible.map((item) => <tr key={item.id}><td><strong>{item.title}</strong><span>{item.id}</span></td><td>{item.location}</td><td>{item.date}</td><td><Badge tone={item.tone}>{item.status}</Badge></td><td>{item.assigned ? <span className="team-pill"><span>SW</span> Ward services</span> : <span className="unassigned">Unassigned</span>}</td><td><button className="row-action" aria-label={`Update status for ${item.id}`} onClick={() => updateStatus(item.id, item.status === 'Received' ? 'In progress' : item.status === 'In progress' ? 'Resolved' : 'Received')}>{item.status === 'Received' ? 'Assign' : item.status === 'In progress' ? 'Resolve' : 'Reopen'} <ChevronRight size={13} /></button></td></tr>)}</tbody></table>{!visible.length && <EmptyState icon={FileSearch} title="No reports in this view" description="Choose another tab to see more reports." />}</div><div className="table-footer"><span>Showing {visible.length} of 248 reports</span><button>View all reports <ArrowRight size={14} /></button></div></Panel><div className="admin-bottom-grid"><Panel><SectionHeading title="Team response" subtitle="This month's service levels" /><div className="team-response"><span className="response-ring"><strong>81%</strong><small>RESOLVED</small></span><div><strong>On track this month</strong><p>Resolution rate is 6% above the city average.</p><span className="response-up"><TrendingUp size={14} /> Improving month over month</span></div></div></Panel><div className="admin-tip"><span><Sparkles size={17} /></span><strong>Small actions, real impact.</strong><p>Reports with a clear location are resolved 2× faster. Consider prompting for location details during intake.</p><button>See response insights <ArrowRight size={14} /></button></div></div></>
}

function DownloadIcon() {
  return <FileText size={16} />
}

export default function App() {
  return <AppLayout><Routes>
    <Route path="/" element={<Dashboard />} />
    <Route path="/assistant" element={<Assistant />} />
    <Route path="/schemes" element={<Schemes />} />
    <Route path="/grievances/new" element={<GrievanceSubmission />} />
    <Route path="/tracking" element={<CitizenTracking />} />
    <Route path="/services" element={<GovernmentServiceAssistant />} />
    <Route path="/policy" element={<PolicyExplainer />} />
    <Route path="/verify" element={<FactVerification />} />
    <Route path="/public-dashboard" element={<PublicDashboard />} />
    <Route path="/admin" element={<AdminGrievances />} />
    <Route path="*" element={<Navigate to="/" replace />} />
  </Routes></AppLayout>
}
