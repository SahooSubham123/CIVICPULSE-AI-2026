import { apiJson, ApiError } from '../../../lib/api/client.js'

export { apiRequest, apiJson } from '../../../lib/api/client.js'

export function getToken() {
  return localStorage.getItem('civicpulse_access_token')
}

export function clearSession() {
  localStorage.removeItem('civicpulse_access_token')
  localStorage.removeItem('civicpulse_user')
}

export async function login(email, password) {
  const body = new URLSearchParams({ username: email, password })
  const response = await apiJson('/auth/login', { method: 'POST', body })
  localStorage.setItem('civicpulse_access_token', response.access_token)
  localStorage.setItem('civicpulse_user', JSON.stringify(response.user))
  return response.user
}

export async function registerAndLogin({ email, fullName, password }) {
  await apiJson('/auth/register', {
    method: 'POST',
    body: JSON.stringify({ email, full_name: fullName, password }),
  })
  return login(email, password)
}

export async function loadCurrentUser() {
  if (!getToken()) return null
  try {
    const user = await apiJson('/auth/me')
    localStorage.setItem('civicpulse_user', JSON.stringify(user))
    return user
  } catch (error) {
    if (error.status === 401) clearSession()
    throw error
  }
}
