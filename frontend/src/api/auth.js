import request from './request'

export function login(data) {
  return request.post('/api/auth/login', data)
}

export function getCurrentUserProfile() {
  return request.get('/api/auth/me')
}

export function listUsers() {
  return request.get('/api/auth/users')
}

export function logout() {
  return request.post('/api/auth/logout')
}
