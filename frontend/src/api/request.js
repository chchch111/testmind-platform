import axios from 'axios'
import { showError } from '../utils/message'
import { clearAuth, getAuthToken } from '../utils/storage'

function getErrorMessage(error) {
  if (!error.response) {
    return '网络连接失败，请检查后端服务是否启动，或检查外网连接。'
  }

  const status = error.response.status
  const detail = error.response.data?.detail || error.response.data?.message

  if (detail) {
    return typeof detail === 'string' ? detail : JSON.stringify(detail)
  }

  if (status === 401 || status === 403) {
    return '没有权限或登录状态失效。'
  }
  if (status === 404) {
    return '请求资源不存在。'
  }
  if (status === 409) {
    return '数据版本冲突，请重新同步后再提交。'
  }
  if (status >= 500) {
    return '服务器内部错误，请检查后端日志；如果是AI生成失败，请检查外网和DeepSeek API配置。'
  }
  return '请求失败，请稍后重试。'
}

const request = axios.create({
  baseURL: '',
  timeout: 240000
})

request.interceptors.request.use(config => {
  const token = getAuthToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

request.interceptors.response.use(
  response => response.data,
  error => {
    const message = getErrorMessage(error)
    const status = error.response?.status
    showError(message)
    if (status === 401 && window.location.pathname !== '/login') {
      clearAuth()
      const redirect = encodeURIComponent(`${window.location.pathname}${window.location.search}`)
      window.location.href = `/login?redirect=${redirect}`
    }
    if (status === 403 && !['/login', '/403'].includes(window.location.pathname)) {
      window.location.href = '/403'
    }
    return Promise.reject(new Error(message))
  }
)

export default request
