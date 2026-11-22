import { useState } from 'react'
import { ArrowRight, LockKeyhole } from 'lucide-react'
import { Button, Panel } from '../../../components/ui.jsx'
import { login, registerAndLogin } from '../services/api.js'

export function SessionPanel({
  onAuthenticated,
  allowRegistration = true,
  accountName = allowRegistration ? 'citizen account' : 'administrator account',
  description = allowRegistration
    ? 'Sign in to submit a complaint and see reports connected to your account.'
    : 'Use an authorized administrator account to continue.',
}) {
  const [registering, setRegistering] = useState(false)
  const [email, setEmail] = useState('')
  const [fullName, setFullName] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (event) => {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      const user = registering
        ? await registerAndLogin({ email, fullName, password })
        : await login(email, password)
      onAuthenticated(user)
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Panel className="grievance-auth-panel">
      <span className="grievance-auth-icon"><LockKeyhole size={20} /></span>
      <h2>{registering ? 'Create your citizen account' : `Sign in to your ${accountName}`}</h2>
      <p>{description}</p>
      <form onSubmit={submit} className="grievance-auth-form">
        {registering && (
          <label className="field-label">Full name
            <input required minLength={2} maxLength={120} value={fullName} onChange={(event) => setFullName(event.target.value)} />
          </label>
        )}
        <label className="field-label">Email
          <input required type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} />
        </label>
        <label className="field-label">Password
          <input required type="password" autoComplete={registering ? 'new-password' : 'current-password'} minLength={registering ? 10 : 1} value={password} onChange={(event) => setPassword(event.target.value)} />
        </label>
        {error && <p className="grievance-error" role="alert">{error}</p>}
        <Button type="submit" disabled={busy}>{busy ? 'Please wait…' : registering ? 'Create account' : 'Sign in'} <ArrowRight size={15} /></Button>
      </form>
      {allowRegistration && <button className="grievance-text-button" type="button" onClick={() => { setRegistering(!registering); setError('') }}>
        {registering ? 'Already have an account? Sign in' : 'New to CIVICPULSE? Create an account'}
      </button>}
    </Panel>
  )
}
