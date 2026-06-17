import { http } from '@/api/http'

/**
 * Lightweight API wrapper that auto-unwraps axios response data.
 * Usage: const status = await api.get('/fidelity/status')
 */
export const api = {
  get<T = any>(url: string, config?: any): Promise<T> {
    return http.get(url, config).then((res) => res.data)
  },
  post<T = any>(url: string, data?: any, config?: any): Promise<T> {
    return http.post(url, data, config).then((res) => res.data)
  },
  put<T = any>(url: string, data?: any, config?: any): Promise<T> {
    return http.put(url, data, config).then((res) => res.data)
  },
  delete<T = any>(url: string, config?: any): Promise<T> {
    return http.delete(url, config).then((res) => res.data)
  },
}
