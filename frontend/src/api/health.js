import request from './request'

export function checkHealth() {
  return request.get('/health')
}

export function checkDatabaseHealth() {
  return request.get('/health/db')
}
