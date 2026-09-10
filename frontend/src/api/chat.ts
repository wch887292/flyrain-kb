import request from './request'
import type { Application, ModelProvider, SessionSummary } from '@/types'

export function listApps() {
  return request.get<Application[]>('/application/apps/')
}

export function createApp(payload: Partial<Application>) {
  return request.post<Application>('/application/apps/', payload)
}

export function updateApp(id: number, payload: Partial<Application>) {
  return request.put<Application>(`/application/apps/${id}/`, payload)
}

export function listProviders() {
  return request.get<ModelProvider[]>('/model/providers/')
}

export function createProvider(payload: Partial<ModelProvider>) {
  return request.post<ModelProvider>('/model/providers/', payload)
}

export function testProvider(payload: {
  type: 'llm' | 'embedding'
  base_url: string
  api_key: string
  model_name: string
}) {
  return request.post('/model/providers/test/', payload)
}

/** 会话列表 */
export function listSessions(appId?: number) {
  const params = appId ? { app_id: appId } : {}
  return request.get<SessionSummary[]>('/chat/sessions/', { params })
}

/** 删除会话 */
export function deleteSession(sessionId: string) {
  return request.delete('/chat/sessions/delete/', { data: { session_id: sessionId } })
}

/** 会话历史消息 */
export function listHistory(sessionId: string) {
  return request.get<{ id: number; role: string; content: string; feedback?: string | null; create_time: string }[]>(
    '/chat/history/',
    { params: { session_id: sessionId } }
  )
}

/** 提交消息反馈（点赞/点踩） */
export function submitFeedback(messageId: number, feedback: 'like' | 'dislike') {
  return request.post('/chat/feedback/', { message_id: messageId, feedback })
}

/** 对话命中率分析统计 */
export function getChatStats(params: { days?: number; app_id?: number } = {}) {
  return request.get('/chat/stats/', { params })
}

/** 导出会话为 Markdown */
export function exportSession(sessionId: string) {
  return request.get('/chat/export/', {
    params: { session_id: sessionId },
    responseType: 'blob',
  })
}

/**
 * SSE 流式对话：解析后端 text/event-stream 输出。
 * 后端每帧格式：data: {"type":"token"|"done"|"error","content":...}
 */
export function chatStream(
  payload: { app_id: number; query: string; session_id?: string },
  handlers: {
    onToken: (text: string) => void
    onDone: (data: any) => void
    onError: (msg: string) => void
  }
) {
  const token = localStorage.getItem('access_token')
  return fetch('/api/chat/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {})
    },
    body: JSON.stringify(payload)
  }).then(async (resp) => {
    if (!resp.ok) {
      handlers.onError(`请求失败(${resp.status})`)
      return
    }
    const reader = resp.body!.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n\n')
      for (const line of lines) {
        const trimmed = line.trim()
        if (!trimmed.startsWith('data:')) continue
        const jsonStr = trimmed.slice(5).trim()
        if (!jsonStr) continue
        try {
          const evt = JSON.parse(jsonStr)
          if (evt.type === 'token') handlers.onToken(evt.content)
          else if (evt.type === 'done') handlers.onDone(evt)
          else if (evt.type === 'error') handlers.onError(evt.message)
        } catch {
          /* ignore malformed frame */
        }
      }
      buffer = ''
    }
  })
}
