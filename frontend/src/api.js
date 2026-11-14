const API_BASE = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api').replace(/\/$/, '')
const SESSION_KEY = 'librovault.session'

export function readSession() {
  try {
    return JSON.parse(sessionStorage.getItem(SESSION_KEY) || 'null')
  } catch {
    return null
  }
}

export function saveSession(session) {
  sessionStorage.setItem(SESSION_KEY, JSON.stringify(session))
}

export function clearSession() {
  sessionStorage.removeItem(SESSION_KEY)
}

async function parseResponse(response) {
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    const detail = data.detail || Object.values(data).flat().join(' ')
    throw new Error(detail || `Request failed (${response.status})`)
  }
  return data
}

async function refreshAccessToken(session) {
  const response = await fetch(`${API_BASE}/auth/refresh/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh: session.refresh }),
  })
  const refreshed = await parseResponse(response)
  const nextSession = { ...session, ...refreshed }
  saveSession(nextSession)
  return nextSession
}

export async function api(path, options = {}) {
  const { auth = true, retry = true, ...requestOptions } = options
  const session = readSession()
  const headers = new Headers(requestOptions.headers || {})
  if (requestOptions.body && !(requestOptions.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }
  if (auth && session?.access) headers.set('Authorization', `Bearer ${session.access}`)

  const response = await fetch(`${API_BASE}${path}`, { ...requestOptions, headers })
  if (response.status === 401 && auth && retry && session?.refresh) {
    try {
      const nextSession = await refreshAccessToken(session)
      const nextHeaders = new Headers(requestOptions.headers || {})
      nextHeaders.set('Authorization', `Bearer ${nextSession.access}`)
      if (requestOptions.body && !(requestOptions.body instanceof FormData)) {
        nextHeaders.set('Content-Type', 'application/json')
      }
      const retried = await fetch(`${API_BASE}${path}`, { ...requestOptions, headers: nextHeaders })
      return parseResponse(retried)
    } catch {
      clearSession()
      window.dispatchEvent(new Event('librovault:session-expired'))
      throw new Error('Your session expired. Please sign in again.')
    }
  }
  return parseResponse(response)
}

export async function signIn(username, password) {
  const response = await api('/auth/login/', {
    auth: false,
    method: 'POST',
    body: JSON.stringify({ username, password }),
  })
  saveSession(response)
  return response
}

export async function signUp(values) {
  return api('/auth/register/', {
    auth: false,
    method: 'POST',
    body: JSON.stringify(values),
  })
}

export async function signOut() {
  const session = readSession()
  if (session?.refresh) {
    await api('/auth/logout/', {
      method: 'POST',
      body: JSON.stringify({ refresh: session.refresh }),
    }).catch(() => {})
  }
  clearSession()
}
