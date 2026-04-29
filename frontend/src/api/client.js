const BASE = '/api'

function getToken() {
  return localStorage.getItem('nhis_token')
}

async function request(path, options = {}) {
  const token = getToken()
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) }
  if (token) headers['Authorization'] = `Bearer ${token}`

  const timeout = options.timeout ?? 60000
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeout)

  const { timeout: _omit, ...fetchOptions } = options

  let res
  try {
    res = await fetch(`${BASE}${path}`, { ...fetchOptions, headers, signal: controller.signal })
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
