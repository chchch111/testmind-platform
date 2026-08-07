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

export function getExecutorTasks(executorId) {
  return request.get(`/api/executors/${executorId}/tasks`)
}

export function updateExecution(executionId, data) {
  return request.put(`/api/executions/${executionId}`, data)
}
