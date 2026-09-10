import request from './request'
import type { AuditLog } from '@/types'

export function listAuditLogs(params: {
  page?: number
  page_size?: number
  action?: string
  resource_type?: string
  user_id?: number
} = {}) {
  return request.get<{ count: number; results: AuditLog[] }>('/common/audit-logs/', { params })
}

export function getAuditStats() {
  return request.get<{ action: string; count: number }[]>('/common/audit-logs/stats/')
}
