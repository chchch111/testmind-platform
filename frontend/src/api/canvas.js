import request from './request'

export function getCaseSetMetas(caseSetId) {
  return request.get(`/api/case-sets/${caseSetId}/metas`)
}

export function saveCaseSetMetas(caseSetId, items) {
  return request.put(`/api/case-sets/${caseSetId}/metas`, { items })
}

export function createSnapshot(caseSetId, data) {
  return request.post(`/api/case-sets/${caseSetId}/snapshots`, data)
}

export function listSnapshots(caseSetId) {
  return request.get(`/api/case-sets/${caseSetId}/snapshots`)
}

export function deleteSnapshot(caseSetId, snapshotId) {
  return request.delete(`/api/case-sets/${caseSetId}/snapshots/${snapshotId}`)
}

export function createReview(caseSetId, data) {
  return request.post(`/api/case-sets/${caseSetId}/reviews`, data)
}

export function listReviews(caseSetId) {
  return request.get(`/api/case-sets/${caseSetId}/reviews`)
}
