import request from './request'

export function importXmind(file) {
  const formData = new FormData()
  formData.append('file', file)
  return request.post('/api/xmind/import', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

export function exportXmind(caseSetId, nodeTagsMap = {}) {
  return request.post(
    `/api/xmind/export/${caseSetId}`,
    {
      node_tags_map: nodeTagsMap
    },
    {
      responseType: 'blob',
      timeout: 120000
    }
  )
}
