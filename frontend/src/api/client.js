// Resolve the API base. In dev, we leave this as a relative path so the Vite
// proxy can forward /api to the backend. In a production build, set
// `VITE_API_BASE_URL=https://api.your-domain.com` and the absolute URL is used
// — including for multipart uploads in api/prescriptions.js.
const BASE = (import.meta.env.VITE_API_BASE_URL || '') + '/api'
const REQUEST_TIMEOUT_MS = Number(import.meta.env.VITE_API_TIMEOUT_MS || 60000)
export const API_BASE = BASE

function getToken() {
  return localStorage.getItem('nhis_token')
}

async function request(path, options = {}) {
  const token = getToken()
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) }
  if (token) headers['Authorization'] = `Bearer ${token}`

  const timeout = options.timeout ?? REQUEST_TIMEOUT_MS
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeout)

  const { timeout: _omit, ...fetchOptions } = options

  let res
  try {
    res = await fetch(`${BASE}${path}`, { ...fetchOptions, headers, signal: controller.signal, credentials: 'include' })
  } catch (err) {
    if (err.name === 'AbortError') throw new Error('Request timed out. The server is taking too long — please try again.')
    throw err
  } finally {
    clearTimeout(timer)
  }

  if (res.status === 401) {
    localStorage.removeItem('nhis_token')
    localStorage.removeItem('nhis_user')
    window.location.reload()
    return
  }

  if (!res.ok) {
    let detail = `HTTP ${res.status}`
    try {
      const body = await res.json()
      detail = body.detail || detail
    } catch {}
    throw new Error(detail)
  }

  if (res.status === 204) return null
  return res.json()
}

export const api = {
  get: (path, opts) => request(path, opts),
  post: (path, body, opts) => request(path, { method: 'POST', body: JSON.stringify(body), ...opts }),
  patch: (path, body, opts) => request(path, { method: 'PATCH', body: JSON.stringify(body), ...opts }),
  delete: (path, opts) => request(path, { method: 'DELETE', ...opts }),
}
