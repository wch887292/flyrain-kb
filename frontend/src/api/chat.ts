import request from './request'
import type { Application, ModelProvider } from '@/types'

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
