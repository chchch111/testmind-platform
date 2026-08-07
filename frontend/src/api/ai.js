import request from './request'

export function generateCaseSet(data) {
  return request.post('/api/ai/generate-case-set', data)
}

export function listGenerationRecords() {
  return request.get('/api/ai/generation-records')
}
