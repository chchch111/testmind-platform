import request from './request'

export function generateCaseSet(data) {
  return request.post('/api/ai/generate-case-set', data)
}

export function startGenerateCaseSet(data) {
  return request.post('/api/ai/generate-case-set-async', data)
}

export function getGenerateProgress(taskId) {
  return request.get(`/api/ai/generate-case-set-tasks/${taskId}`)
}

export function listGenerationRecords() {
  return request.get('/api/ai/generation-records')
}

export function getGenerationRecordDetail(generationId) {
  return request.get(`/api/ai/generation-records/${generationId}`)
}
