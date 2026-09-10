import request from './request'
import type { KnowledgeBase, DocumentItem, SearchResult } from '@/types'

export function listBases() {
  return request.get<KnowledgeBase[]>('/knowledge/bases/')
}

export function createBase(payload: { name: string; desc?: string }) {
  return request.post<KnowledgeBase>('/knowledge/bases/', payload)
}

export function listDocuments(kbId: number) {
  return request.get<DocumentItem[]>(`/knowledge/bases/${kbId}/documents/`)
}

export function uploadDoc(kbId: number, file: File) {
  const form = new FormData()
  form.append('file', file)
  return request.post(`/knowledge/bases/${kbId}/upload/`, form, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

export function search(kbId: number, query: string, topK = 5) {
  return request.post<SearchResult[]>('/knowledge/search/', {
    kb_id: kbId,
    query,
    top_k: topK
  })
}

export function getParagraphs(
  docId: number,
  params: { page?: number; page_size?: number } = {}
) {
  return request.get<{
    count: number
    page: number
    page_size: number
    results: Paragraph[]
  }>(`/knowledge/documents/${docId}/paragraphs/`, { params })
}

export function reparseDocument(docId: number) {
  return request.post(`/knowledge/documents/${docId}/reparse/`)
}

export function exportKnowledgeBase(kbId: number) {
  return request.get(`/knowledge/bases/${kbId}/export/`, { responseType: 'blob' })
}

export function importKnowledgeBase(payload: {
  name?: string
  desc?: string
  documents: { name: string; source_type?: string }[]
}) {
  return request.post('/knowledge/bases/import_kb/', payload)
}

/** 知识库权限管理 */
export function getAuthorizedUsers(kbId: number) {
  return request.get<{ id: number; username: string; nickname: string; role: string }[]>(
    `/knowledge/bases/${kbId}/authorized_users/`
  )
}

export function grantAccess(kbId: number, userIds: number[]) {
  return request.post(`/knowledge/bases/${kbId}/grant_access/`, { user_ids: userIds })
}

export function revokeAccess(kbId: number, userIds: number[]) {
  return request.post(`/knowledge/bases/${kbId}/revoke_access/`, { user_ids: userIds })
}

export function setKbPublic(kbId: number) {
  return request.post(`/knowledge/bases/${kbId}/set_public/`)
}

/** 文档级权限管理 */
export function getDocAuthorizedUsers(docId: number) {
  return request.get<{ id: number; username: string; nickname: string; role: string }[]>(
    `/knowledge/documents/${docId}/authorized_users/`
  )
}

export function grantDocAccess(docId: number, userIds: number[]) {
  return request.post(`/knowledge/documents/${docId}/grant_access/`, { user_ids: userIds })
}

export function revokeDocAccess(docId: number, userIds: number[]) {
  return request.post(`/knowledge/documents/${docId}/revoke_access/`, { user_ids: userIds })
}

export function inheritKbAccess(docId: number) {
  return request.post(`/knowledge/documents/${docId}/inherit_kb_access/`)
}
