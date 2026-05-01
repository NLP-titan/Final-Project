import { api, API_BASE } from './client.js'

async function uploadFile(path, file) {
  const token = localStorage.getItem('nhis_token')
  const headers = {}
  if (token) headers['Authorization'] = `Bearer ${token}`
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${API_BASE}${path}`, { method: 'POST', body: form, headers })
  if (!res.ok) {
    let detail = `HTTP ${res.status}`
    try {
      const body = await res.json()
      detail = body.detail || detail
    } catch {}
    throw new Error(detail)
  }
  return res.json()
}

export const prescriptionsApi = {
  analyze: (file) => uploadFile('/prescriptions/analyze', file),
}

export const medicinesIdentifyApi = {
  identify: (file) => uploadFile('/medicines/identify', file),
}

// Re-export `api` so this module can also do JSON calls if needed.
export { api }
