import request from './request'

export function listRoles() {
  return request.get('/api/permissions/roles')
}

export function listPermissionUsers(params) {
  return request.get('/api/permissions/users', { params })
}

export function getPermissionUserDetail(userId) {
  return request.get(`/api/permissions/users/${userId}`)
}

export function updateUserPermission(userId, data) {
  return request.patch(`/api/permissions/users/${userId}`, data)
}

export function createUser(data) {
  return request.post('/api/permissions/users', data)
}

export function resetUserPassword(userId, newPassword) {
  return request.post(`/api/permissions/users/${userId}/reset-password`, { new_password: newPassword })
}
