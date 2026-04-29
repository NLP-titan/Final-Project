import { api } from './client.js'

export const resourcesApi = {
  list: ({ category } = {}) => {
    const params = new URLSearchParams()
    if (category) params.set('category', category)
    return api.get(`/resources?${params}`)
  },
}
