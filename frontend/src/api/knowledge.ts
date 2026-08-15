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
