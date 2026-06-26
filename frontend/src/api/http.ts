import axios from 'axios'

export const http = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
})

http.interceptors.response.use(
  (response) => response,
  (error) => {
    // 不在此处打印日志，避免与各业务调用方 catch 块重复输出
    return Promise.reject(error)
  },
)
