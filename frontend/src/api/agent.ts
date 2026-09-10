import request from './request'

export interface Agent {
  id: number
  name: string
  avatar: string
  description: string
  role: string
  system_prompt: string
  kb_ids?: number[]
  kb_names?: string[]
  tool_ids?: number[]
  tool_names?: string[]
  temperature: number
  max_tokens: number
  max_iterations: number
  opening_message: string
  suggested_questions: string[]
  enable_reasoning: boolean
  is_active: boolean
  create_time: string
  update_time: string
}

export interface AgentConversation {
  id: number
  session_id: string
  agent_id: number
  agent_name: string
  title: string
  create_time: string
  update_time: string
}

export interface AgentMessage {
  id: number
  role: 'user' | 'assistant' | 'tool'
  content: string
  reasoning: string
  tool_calls: any[]
  tool_name: string
  create_time: string
}

export function listAgents() {
  return request.get<Agent[]>('/agents/')
}

export function getAgent(id: number) {
  return request.get<Agent>(`/agents/${id}/`)
}

export function createAgent(data: Partial<Agent>) {
  return request.post<Agent>('/agents/', data)
}

export function updateAgent(id: number, data: Partial<Agent>) {
  return request.put<Agent>(`/agents/${id}/`, data)
}

export function deleteAgent(id: number) {
  return request.delete(`/agents/${id}/`)
}

export function listAgentConversations(agentId?: number) {
  const params = agentId ? { agent_id: agentId } : {}
  return request.get<AgentConversation[]>('/agent/conversations/', { params })
}

export function getAgentHistory(sessionId: string) {
  return request.get<AgentMessage[]>('/agent/history/', { params: { session_id: sessionId } })
}

/** 智能体对话（SSE 流式），返回 fetch ReadableStream */
export function agentChat(agentId: number, query: string, sessionId?: string) {
  const token = localStorage.getItem('token')
  return fetch('/api/agent/chat/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify({ agent_id: agentId, query, session_id: sessionId }),
  })
}
