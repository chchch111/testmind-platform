import request from './request'

export function listTasks(params = {}) {
  return request.get('/api/tasks', { params })
}

export function createTask(data) {
  return request.post('/api/tasks', data)
}

export function getTaskDetail(taskId) {
  return request.get(`/api/tasks/${taskId}`)
}

export function listTaskExecutions(taskId) {
  return request.get(`/api/tasks/${taskId}/executions`)
}

export function getTaskReport(taskId) {
  return request.get(`/api/tasks/${taskId}/report`)
}

export function listTaskDirectories(params = {}) {
  return request.get('/api/tasks/directories', { params })
}

export function listSubtasks(parentId, params = {}) {
  return request.get(`/api/tasks/${parentId}/subtasks`, { params })
}

export function getSubtaskExecutionTree(taskId) {
  return request.get(`/api/tasks/${taskId}/execution-tree`)
}

export function updateExecution(executionId, data) {
  return request.put(`/api/executions/${executionId}`, data)
}

export function cancelTask(taskId) {
  return request.post(`/api/tasks/${taskId}/cancel`)
}

export function assignTask(taskId) {
  return request.post(`/api/tasks/${taskId}/assign`)
}

export function deleteTask(taskId) {
  return request.delete(`/api/tasks/${taskId}`)
}
