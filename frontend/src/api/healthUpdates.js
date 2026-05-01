import { api } from './client.js'

export const healthUpdatesApi = {
  list: ({ category, limit = 20 } = {}) => {
    const params = new URLSearchParams()
    if (category && category !== 'All') params.set('category', category)
    params.set('limit', limit)
    return api.get(`/health-updates?${params}`)
  },
  refresh: () => api.post('/health-updates/refresh'),
}
