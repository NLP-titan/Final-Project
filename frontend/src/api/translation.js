import { api } from './client.js'

export const translationApi = {
  // POST /api/translate/batch — returns translated array in same order
  batch: ({ texts, target_lang }) => api.post('/translate/batch', { texts, target_lang }),
  one: ({ text, target_lang }) => api.post('/translate', { text, target_lang }),
  languages: () => api.get('/translate/languages'),
}
