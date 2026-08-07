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

export function buildIndex(knowledgeBaseId, operatorId = 1) {
  return request.post(`/api/rag/knowledge-bases/${knowledgeBaseId}/build-index`, null, {
    params: { operator_id: operatorId }
  })
}

export function searchKnowledgeBase(knowledgeBaseId, data) {
  return request.post(`/api/rag/knowledge-bases/${knowledgeBaseId}/search`, data)
}
