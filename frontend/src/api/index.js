import axios from 'axios'

const api = axios.create({
  baseURL: '',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Response interceptor for error handling
api.interceptors.response.use(
  response => response,
  error => {
    console.error('API Error:', error.response?.data || error.message)
    return Promise.reject(error)
  }
)

export default api

// API helper functions
export const connectionsApi = {
  list: () => api.get('/api/connections'),
  get: (id) => api.get(`/api/connections/${id}`),
  create: (data) => api.post('/api/connections', data),
  update: (id, data) => api.put(`/api/connections/${id}`, data),
  delete: (id) => api.delete(`/api/connections/${id}`),
  test: (id) => api.post(`/api/connections/${id}/test`),
}

export const trackersApi = {
  list: () => api.get('/api/trackers'),
  get: (id) => api.get(`/api/trackers/${id}`),
  create: (data) => api.post('/api/trackers', data),
  update: (id, data) => api.put(`/api/trackers/${id}`, data),
  delete: (id) => api.delete(`/api/trackers/${id}`),
  discover: () => api.post('/api/trackers/discover'),
  stats: (id) => api.get(`/api/trackers/${id}/stats`),
  updateStats: (id) => api.post(`/api/trackers/${id}/update-stats`),
  toggle: (id) => api.post(`/api/trackers/${id}/toggle`),
  togglePermaseed: (id) => api.post(`/api/trackers/${id}/permaseed`),
  zoneSummary: () => api.get('/api/trackers/zone-summary'),
}

export const rulesApi = {
  list: () => api.get('/api/rules'),
  get: (id) => api.get(`/api/rules/${id}`),
  create: (data) => api.post('/api/rules', data),
  update: (id, data) => api.put(`/api/rules/${id}`, data),
  delete: (id) => api.delete(`/api/rules/${id}`),
  reorder: (ruleIds) => api.put('/api/rules/reorder', { rule_ids: ruleIds }),
  test: (id) => api.post(`/api/rules/${id}/test`),
  execute: (id, dryRun = true) => api.post(`/api/rules/${id}/execute?dry_run=${dryRun}`),
}

export const torrentsApi = {
  list: (params) => api.get('/api/torrents', { params }),
  get: (hash) => api.get(`/api/torrents/${hash}`),
  protect: (hash, protected_) => api.put(`/api/torrents/${hash}/protect`, { protected: protected_ }),
  delete: (hash, deleteFiles = true) => api.delete(`/api/torrents/${hash}?delete_files=${deleteFiles}`),
  history: (hash) => api.get(`/api/torrents/${hash}/history`),
  refresh: () => api.post('/api/torrents/refresh'),
  categories: () => api.get('/api/torrents/categories/list'),
  states: () => api.get('/api/torrents/states/list'),
}

export const systemApi = {
  health: () => api.get('/api/health'),
  stats: () => api.get('/api/stats'),
  statsHistory: (days = 30) => api.get(`/api/stats/history?days=${days}`),
  logs: (params) => api.get('/api/logs', { params }),
  scan: (dryRun = false) => api.post(dryRun ? '/api/scan/dry-run' : '/api/scan'),
  settings: () => api.get('/api/settings'),
  updateSettings: (data) => api.put('/api/settings', data),
  exportBackup: () => api.post('/api/backup/export'),
  importBackup: (data) => api.post('/api/backup/import', data),
}
