import { useEffect, useState } from 'react'
import { clearSession, getToken, loadCurrentUser } from '../services/api.js'

export function useSession() {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(Boolean(getToken()))
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    if (!getToken()) return undefined
    loadCurrentUser()
      .then((currentUser) => { if (active) setUser(currentUser) })
      .catch((requestError) => { if (active) setError(requestError.message) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [])

  const logout = () => {
    clearSession()
    setUser(null)
    setError('')
  }

  return { user, setUser, loading, error, logout }
}
