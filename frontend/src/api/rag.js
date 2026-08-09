import request from './request'

export function listKnowledgeBases() {
  return request.get('/api/rag/knowledge-bases')
}

export function createKnowledgeBase(data) {
  return request.post('/api/rag/knowledge-bases', data)
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

export function buildIndex(knowledgeBaseId) {
  return request.post(`/api/rag/knowledge-bases/${knowledgeBaseId}/build-index`)
}

export function searchKnowledgeBase(knowledgeBaseId, data) {
  return request.post(`/api/rag/knowledge-bases/${knowledgeBaseId}/search`, data)
}
