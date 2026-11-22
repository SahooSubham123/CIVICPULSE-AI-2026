import { useEffect, useRef, useState } from 'react'
import { BookOpenCheck, ExternalLink, FileText, Info, LoaderCircle, LockKeyhole, Send, Upload } from 'lucide-react'
import { Badge, Button, EmptyState, PageTitle, Panel, SectionHeading } from '../../../components/ui.jsx'
import { SessionPanel } from '../../grievance_management/components/SessionPanel.jsx'
import { useSession } from '../../grievance_management/hooks/useSession.js'
import {
  askPolicyQuestion,
  listPolicyDocuments,
  setPolicyPublication,
  uploadPolicyDocument,
} from '../services/api.js'

const LANGUAGES = [
  { value: 'en', label: 'English' },
  { value: 'hi', label: 'Hindi' },
  { value: 'or', label: 'Odia' },
]

export function PolicyExplainer() {
  const session = useSession()
  const uploadInput = useRef(null)
  const [documents, setDocuments] = useState([])
  const [documentsLoading, setDocumentsLoading] = useState(false)
  const [documentsError, setDocumentsError] = useState('')
  const [question, setQuestion] = useState('')
  const [language, setLanguage] = useState('en')
  const [answer, setAnswer] = useState(null)
  const [asking, setAsking] = useState(false)
  const [questionError, setQuestionError] = useState('')
  const [title, setTitle] = useState('')
  const [authority, setAuthority] = useState('')
  const [sourceUrl, setSourceUrl] = useState('')
  const [documentLanguage, setDocumentLanguage] = useState('en')
  const [publishOnUpload, setPublishOnUpload] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState('')
  const [uploadMessage, setUploadMessage] = useState('')
  const [updatingDocument, setUpdatingDocument] = useState('')

  useEffect(() => {
    if (!session.user) return undefined
    let active = true
    setDocumentsLoading(true)
    setDocumentsError('')
    listPolicyDocuments()
      .then((items) => { if (active) setDocuments(items) })
      .catch((requestError) => { if (active) setDocumentsError(requestError.message) })
      .finally(() => { if (active) setDocumentsLoading(false) })
    return () => { active = false }
  }, [session.user])

  const submitQuestion = async (event) => {
    event.preventDefault()
    setAsking(true)
    setQuestionError('')
    setAnswer(null)
    try {
      setAnswer(await askPolicyQuestion(question.trim(), language))
    } catch (requestError) {
      setQuestionError(requestError.message)
    } finally {
      setAsking(false)
    }
  }

  const uploadDocument = async (event) => {
    event.preventDefault()
    const file = uploadInput.current?.files?.[0]
    if (!file) {
      setUploadError('Choose a searchable PDF document.')
      return
    }
    setUploading(true)
    setUploadError('')
    setUploadMessage('')
    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('title', title.trim())
      formData.append('issuing_authority', authority.trim())
      formData.append('language', documentLanguage)
      formData.append('is_published', String(publishOnUpload))
      if (sourceUrl.trim()) formData.append('source_url', sourceUrl.trim())
      const result = await uploadPolicyDocument(formData)
      setUploadMessage(result.message)
      setTitle('')
      setAuthority('')
      setSourceUrl('')
      setPublishOnUpload(false)
      if (uploadInput.current) uploadInput.current.value = ''
      try {
        setDocuments(await listPolicyDocuments())
      } catch (requestError) {
        setDocumentsError(`Document uploaded, but the list could not be refreshed: ${requestError.message}`)
      }
    } catch (requestError) {
      setUploadError(requestError.message)
    } finally {
      setUploading(false)
    }
  }

  const togglePublication = async (document) => {
    setUpdatingDocument(document.id)
    setDocumentsError('')
    try {
      const updated = await setPolicyPublication(document.id, !document.is_published)
      setDocuments((items) => items.map((item) => item.id === updated.id ? updated : item))
    } catch (requestError) {
      setDocumentsError(requestError.message)
    } finally {
      setUpdatingDocument('')
    }
  }

  if (session.loading) {
    return <PageTitle eyebrow="GOVERNMENT POLICY EXPLAINER" title="Understand official guidance" description="Loading your secure account…" />
  }
  if (!session.user) {
    return (
      <>
        <PageTitle
          eyebrow="GOVERNMENT POLICY EXPLAINER"
          title="Understand official guidance"
          description="Sign in to ask questions about published government documents."
        />
        {session.error && <p className="grievance-error" role="alert">{session.error}</p>}
        <SessionPanel
          onAuthenticated={session.setUser}
          accountName="CIVICPULSE account"
          description="Sign in to ask policy questions. Administrator accounts can also upload and publish documents."
        />
      </>
    )
  }

  const isAdmin = session.user.role === 'admin'

  return (
    <>
      <PageTitle
        eyebrow="GOVERNMENT POLICY EXPLAINER"
        title="Understand official guidance"
        description="Ask in English, Hindi, or Odia. Answers are grounded in published policy documents and cite their pages."
        action={<Button variant="light" onClick={session.logout}>Sign out</Button>}
      />
      <div className="policy-explainer-banner">
        <span><BookOpenCheck size={19} /></span>
        <div><strong>Evidence-grounded explanations</strong><p>Answers cite the published government documents used. If the documents do not contain the answer, the assistant abstains.</p></div>
      </div>

      <div className="policy-explainer-grid">
        <Panel className="policy-question-panel">
          <SectionHeading title="Ask about a policy" subtitle="Use one clear question at a time." />
          <form onSubmit={submitQuestion}>
            <label className="field-label">Question
              <textarea required minLength={3} maxLength={2000} rows="4" value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="What documents are required to apply?" />
            </label>
            <label className="field-label">Answer language
              <select value={language} onChange={(event) => setLanguage(event.target.value)}>
                {LANGUAGES.map((item) => <option value={item.value} key={item.value}>{item.label}</option>)}
              </select>
            </label>
            {questionError && <p className="grievance-error" role="alert">{questionError}</p>}
            <Button type="submit" disabled={asking}>
              {asking ? <><LoaderCircle className="service-spinner" size={15} /> Finding cited guidance…</> : <><Send size={15} /> Ask policy assistant</>}
            </Button>
          </form>

          {answer && (
            <div className={`policy-answer ${answer.abstained ? 'policy-answer-abstained' : ''}`} aria-live="polite">
              <div className="policy-answer-heading">
                <strong>{answer.abstained ? 'No answer found in published sources' : 'Policy explanation'}</strong>
                <Badge tone={answer.abstained ? 'amber' : 'green'}>{answer.abstained ? 'Inconclusive' : 'Cited answer'}</Badge>
              </div>
              <p>{answer.answer}</p>
              {answer.sources.length > 0 && <div className="policy-citations">
                <strong>Sources</strong>
                {answer.sources.map((source, index) => (
                  <div className="policy-citation" key={`${source.document_id}-${source.page_number}-${index}`}>
                    <FileText size={14} />
                    <span><b>{source.title}</b><small>{source.issuing_authority} · page {source.page_number}</small></span>
                    {source.source_url && <a href={source.source_url} target="_blank" rel="noreferrer" aria-label={`Open ${source.title}`}><ExternalLink size={13} /></a>}
                  </div>
                ))}
              </div>}
              <p className="policy-disclaimer"><Info size={13} /> {answer.disclaimer}</p>
            </div>
          )}
        </Panel>

        <Panel className="policy-documents-panel">
          <SectionHeading title="Available policy sources" subtitle={isAdmin ? 'Draft and published documents' : 'Published documents used for answers'} />
          {documentsError && <p className="grievance-error" role="alert">{documentsError}</p>}
          {documentsLoading ? <p className="grievance-help-text">Loading policy sources…</p>
            : documents.length ? <div className="policy-document-list">{documents.map((document) => (
              <article className="policy-document" key={document.id}>
                <div className="policy-document-main">
                  <span><FileText size={15} /></span>
                  <div><strong>{document.title}</strong><small>{document.issuing_authority} · {document.language.toUpperCase()} · {document.page_count || 0} pages</small></div>
                  <Badge tone={document.is_published ? 'green' : 'amber'}>{document.is_published ? 'Published' : 'Draft'}</Badge>
                </div>
                {document.source_url && <a className="policy-document-link" href={document.source_url} target="_blank" rel="noreferrer">Official source <ExternalLink size={12} /></a>}
                {isAdmin && <Button
                  type="button"
                  variant="outline"
                  disabled={updatingDocument === document.id}
                  onClick={() => togglePublication(document)}
                >{updatingDocument === document.id ? 'Saving…' : document.is_published ? 'Unpublish' : 'Publish'}</Button>}
              </article>
            ))}</div> : <EmptyState icon={FileText} title="No policy documents available" description={isAdmin ? 'Upload a searchable government PDF to begin.' : 'An administrator must upload and publish policy documents first.'} />}
          {!isAdmin && <p className="policy-privacy-note"><LockKeyhole size={13} /> Answers use only the published sources shown here; they are informational, not official decisions.</p>}
        </Panel>
      </div>

      {isAdmin && <Panel className="policy-upload-panel">
        <SectionHeading title="Manage policy documents" subtitle="PDFs are processed into page-aware search chunks; original files are not retained." />
        <form className="policy-upload-form" onSubmit={uploadDocument}>
          <label className="field-label">Document title
            <input required minLength={3} maxLength={240} value={title} onChange={(event) => setTitle(event.target.value)} />
          </label>
          <label className="field-label">Issuing authority
            <input required minLength={2} maxLength={180} value={authority} onChange={(event) => setAuthority(event.target.value)} />
          </label>
          <label className="field-label">Document language
            <select value={documentLanguage} onChange={(event) => setDocumentLanguage(event.target.value)}>
              {LANGUAGES.map((item) => <option value={item.value} key={item.value}>{item.label}</option>)}
            </select>
          </label>
          <label className="field-label">Official source URL <small>(optional)</small>
            <input type="url" maxLength={1000} value={sourceUrl} onChange={(event) => setSourceUrl(event.target.value)} placeholder="https://department.gov.in/policy.pdf" />
          </label>
          <label className="field-label policy-pdf-field">Searchable PDF
            <span className="upload-zone"><Upload size={17} /><strong>Choose a PDF document</strong><small>PDF upload and page limits are configured by the service.</small>
              <input ref={uploadInput} type="file" accept="application/pdf" required />
            </span>
          </label>
          <label className="policy-publish-choice"><input type="checkbox" checked={publishOnUpload} onChange={(event) => setPublishOnUpload(event.target.checked)} /> Publish immediately after processing</label>
          {uploadError && <p className="grievance-error" role="alert">{uploadError}</p>}
          {uploadMessage && <p className="policy-upload-message" role="status">{uploadMessage}</p>}
          <Button type="submit" disabled={uploading}>{uploading ? <><LoaderCircle className="service-spinner" size={15} /> Processing PDF…</> : <><Upload size={15} /> Upload policy PDF</>}</Button>
        </form>
      </Panel>}

      <div className="responsible-note"><Info size={14} /> Confirm requirements, eligibility, fees, and deadlines with the cited authority before acting.</div>
    </>
  )
}
