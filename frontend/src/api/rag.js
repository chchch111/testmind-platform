import request from './request'

export function listKnowledgeBases() {
  return request.get('/api/rag/knowledge-bases')
}

export function createKnowledgeBase(data) {
  return request.post('/api/rag/knowledge-bases', data)
}

export function updateKnowledgeBase(knowledgeBaseId, data) {
  return request.put(`/api/rag/knowledge-bases/${knowledgeBaseId}`, data)
}

export function deleteKnowledgeBase(knowledgeBaseId) {
  return request.delete(`/api/rag/knowledge-bases/${knowledgeBaseId}`)
}

export function addManualSource(knowledgeBaseId, data) {
  return request.post(`/api/rag/knowledge-bases/${knowledgeBaseId}/sources/manual`, data)
}

export function uploadKnowledgeSourceFile(knowledgeBaseId, file) {
  const formData = new FormData()
  formData.append('file', file)
  return request.post(`/api/rag/knowledge-bases/${knowledgeBaseId}/sources/upload`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

export function importCaseSetAsSource(knowledgeBaseId, caseSetId) {
  return request.post(`/api/rag/knowledge-bases/${knowledgeBaseId}/sources/import-case-set`, null, {
    params: { case_set_id: caseSetId }
  })
}

export function listKnowledgeSources(knowledgeBaseId) {
  return request.get(`/api/rag/knowledge-bases/${knowledgeBaseId}/sources`)
}

export function deleteKnowledgeSource(sourceId) {
  return request.delete(`/api/rag/sources/${sourceId}`)
}

export function buildIndex(knowledgeBaseId) {
  return request.post(`/api/rag/knowledge-bases/${knowledgeBaseId}/build-index`)
}

export function getBuildProgress(knowledgeBaseId, taskId) {
  return request.get(`/api/rag/knowledge-bases/${knowledgeBaseId}/build-index/${taskId}`)
}

export function searchKnowledgeBase(knowledgeBaseId, data) {
  return request.post(`/api/rag/knowledge-bases/${knowledgeBaseId}/search`, data)
}
