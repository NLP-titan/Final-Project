import { api } from './client.js'

export const facilitiesApi = {
  list: ({ q, region, accredited, limit = 200, offset = 0 } = {}) => {
    const params = new URLSearchParams()
    if (q) params.set('q', q)
    if (region) params.set('region', region)
    if (accredited !== undefined) params.set('accredited', accredited)
    params.set('limit', limit)
    params.set('offset', offset)
    return api.get(`/facilities?${params}`)
  },
}
