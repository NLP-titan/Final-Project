import { api } from './client.js'

const CHAT_TIMEOUT = 120000  // 2 minutes — LLM + embedding can be slow on first load

export const conversationsApi = {
  list: () => api.get('/conversations'),
  create: (title) => api.post('/conversations', { title }),
  get: (id) => api.get(`/conversations/${id}`),
  rename: (id, title) => api.patch(`/conversations/${id}`, { title }),
  delete: (id) => api.delete(`/conversations/${id}`),
  sendMessage: (id, content) => api.post(`/conversations/${id}/messages`, { content }, { timeout: CHAT_TIMEOUT }),
}
