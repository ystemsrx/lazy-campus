import axios from 'axios'

function resolveApiBaseUrl() {
  const override = import.meta.env.VITE_API_BASE_URL
  if (override) return override

  const appEnv = (import.meta.env.VITE_APP_ENV || '').toLowerCase()
  const mode = import.meta.env.MODE
  const isProduction = appEnv === 'production' || appEnv === 'prod' || mode === 'production'

  if (isProduction) {
    return import.meta.env.VITE_API_BASE_URL_PROD || 'https://api.example.com/api/v1'
  }
  return import.meta.env.VITE_API_BASE_URL_DEV || 'http://127.0.0.1:8000/api/v1'
}

const api = axios.create({
  baseURL: resolveApiBaseUrl()
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export default api
