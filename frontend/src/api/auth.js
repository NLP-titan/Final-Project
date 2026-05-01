import { api } from './client.js'

export const authApi = {
  register: (data) => api.post('/auth/register', data),
  login: (data) => api.post('/auth/login', data),
  me: () => api.get('/auth/me'),
  updateMe: (data) => api.patch('/auth/me', data),
  logout: () => api.post('/auth/logout', {}),
}
