import request from './request'

export function listCaseSets(params = {}) {
  return request.get('/api/case-sets', { params })
}

export function createCaseSet(data) {
  return request.post('/api/case-sets', data)
}

export function deleteCaseSet(caseSetId, data) {
  return request.delete(`/api/case-sets/${caseSetId}`, { data })
}

export function publishCaseSet(caseSetId) {
  return request.post(`/api/case-sets/${caseSetId}/publish`)
}

export function getCaseTree(caseSetId) {
  return request.get(`/api/case-sets/${caseSetId}/tree`)
}

export function createCaseNode(data) {
  return request.post('/api/case-nodes', data)
}

export function getCaseNode(nodeId) {
  return request.get(`/api/case-nodes/${nodeId}`)
}

export function updateCaseNode(nodeId, data) {
  return request.put(`/api/case-nodes/${nodeId}`, data)
}

export function deleteCaseNode(nodeId, data) {
  return request.delete(`/api/case-nodes/${nodeId}`, { data })
}

export function listNodeVersions(nodeId) {
  return request.get(`/api/case-nodes/${nodeId}/versions`)
}

export function rollbackNode(nodeId, versionId, data) {
  return request.post(`/api/case-nodes/${nodeId}/rollback/${versionId}`, data)
}
