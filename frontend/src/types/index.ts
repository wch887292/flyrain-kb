export interface User {
  id: number
  username: string
  email: string
  nickname: string
  role: string
  tenant: string | null
  create_time: string
}

export interface KnowledgeBase {
  id: number
  name: string
  desc: string
  tenant: string
  doc_count: number
  create_time: string
}

export interface DocumentItem {
  id: number
  kb: number
  name: string
  source_type: string
  status: string
  char_count: number
  error_msg: string
  create_time: string
}

export interface Paragraph {
  id: number
  doc: number
  doc_name: string
  content: string
  page_no: number
  index: number
  hit_count: number
}

export interface Application {
  id: number
  name: string
  desc: string
  kb_ids: number[]
  kb_names: string[]
  system_prompt: string
  temperature: number
  max_tokens: number
  vector_weight: number
  is_active: boolean
  create_time: string
}

export interface SessionSummary {
  session_id: string
  app_id: number | null
  app_name: string
  msg_count: number
  last_content: string
  last_time: string
}

export interface ModelProvider {
  id: number
  name: string
  type: 'llm' | 'embedding'
  base_url: string
  api_key?: string  // write_only
  api_key_masked?: string  // 只读掩码
  model_name: string
  dimensions: number
  is_default: boolean
  create_time: string
}

export const ROLE = {
  ADMIN: 'admin',
  EDITOR: 'editor',
  USER: 'user',
} as const

export const ROLE_LABELS: Record<string, string> = {
  admin: '管理员',
  editor: '知识库维护',
  user: '普通用户',
}

export interface SearchResult {
  content: string
  score: number
  doc_name: string
  page_no: number
}

export interface AuditLog {
  id: number
  user: number | null
  username: string
  action: string
  action_display: string
  resource_type: string
  resource_id: number | null
  detail: string
  ip: string
  path: string
  method: string
  status_code: number | null
  create_time: string
}
