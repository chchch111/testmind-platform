import request from './request'

export function importXmind(file, createdBy = 1) {
  const formData = new FormData()
  formData.append('file', file)
  return request.post('/api/xmind/import', formData, {
    params: { created_by: createdBy },
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

export function exportXmind(caseSetId, operatorId = 1, nodeTagsMap = {}) {
  return request.post(
    `/api/xmind/export/${caseSetId}`,
    {
      operator_id: operatorId,
      node_tags_map: nodeTagsMap
    },
    {
      responseType: 'blob',
      timeout: 120000
    }
  )
}
