import axios from 'axios'

export const http = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
})

http.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('[API Error]', error.response?.status, error.message)
    return Promise.reject(error)
  },
)
