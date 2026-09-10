<template>
  <div class="share-page">
    <div class="share-container" v-if="agent">
      <div class="share-header">
        <el-avatar :size="48" :src="agent.avatar">{{ agent.name?.charAt(0) }}</el-avatar>
        <div>
          <h2 style="margin:0">{{ agent.name }}</h2>
          <div style="font-size:13px;color:#9ca3af">{{ agent.role || agent.description }}</div>
        </div>
      </div>

      <div class="chat-area">
        <div class="messages" ref="messagesRef">
          <div v-if="messages.length === 0" class="welcome">
            <div class="welcome-text">{{ agent.opening_message }}</div>
            <div class="suggested" v-if="agent.suggested_questions?.length">
              <el-button v-for="q in agent.suggested_questions" :key="q"
                size="small" plain @click="sendQuery(q)">{{ q }}</el-button>
            </div>
          </div>

          <div v-for="(m, idx) in messages" :key="idx" class="message-row" :class="m.role">
            <div v-if="m.role === 'user'" class="msg-bubble user">{{ m.content }}</div>
            <div v-else class="msg-bubble assistant" v-html="renderMarkdown(m.content)"></div>
          </div>

          <div v-if="streaming" class="message-row assistant">
            <div v-if="currentAnswer" class="msg-bubble assistant" v-html="renderMarkdown(currentAnswer)"></div>
            <div v-else class="typing"><span></span><span></span><span></span></div>
          </div>
        </div>

        <div class="input-area">
          <el-input v-model="inputText" type="textarea" :rows="2"
            placeholder="输入消息..." @keydown.enter.exact.prevent="send" :disabled="streaming" />
          <el-button type="primary" :loading="streaming" :disabled="!inputText.trim()"
            @click="send" style="margin-left:8px">发送</el-button>
        </div>
      </div>
    </div>

    <el-empty v-else-if="!loading" description="分享不存在或已失效" />
    <div v-else class="loading">加载中...</div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import request from '@/api/request'

const route = useRoute()
const agent = ref<any>(null)
const loading = ref(true)
const messages = ref<any[]>([])
const inputText = ref('')
const streaming = ref(false)
const currentAnswer = ref('')
const messagesRef = ref<HTMLElement>()
let sessionId = ''

function renderMarkdown(text: string): string {
  return text
    .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br>')
}

async function scrollBottom() {
  await nextTick()
  if (messagesRef.value) {
    messagesRef.value.scrollTop = messagesRef.value.scrollHeight
  }
}

async function loadAgent() {
  const shareCode = route.params.shareCode
  try {
    agent.value = await request.get(`/agent/shared/${shareCode}/`)
  } catch {
    agent.value = null
  } finally {
    loading.value = false
  }
}

function sendQuery(q: string) {
  inputText.value = q
  send()
}

async function send() {
  const query = inputText.value.trim()
  if (!query || !agent.value || streaming.value) return

  inputText.value = ''
  messages.value.push({ role: 'user', content: query })
  streaming.value = true
  currentAnswer.value = ''
  scrollBottom()

  try {
    const token = localStorage.getItem('token') || ''
    const resp = await fetch('/api/agent/chat/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify({ agent_id: agent.value.id, query, session_id: sessionId || undefined }),
    })

    if (!resp.ok || !resp.body) throw new Error('请求失败')

    const reader = resp.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        try {
          const evt = JSON.parse(line.slice(6))
          if (evt.type === 'token') {
            currentAnswer.value += evt.content
          } else if (evt.type === 'done') {
            currentAnswer.value = evt.answer || currentAnswer.value
            sessionId = evt.session_id || sessionId
            messages.value.push({ role: 'assistant', content: currentAnswer.value })
          } else if (evt.type === 'error') {
            currentAnswer.value = `错误：${evt.message}`
            messages.value.push({ role: 'assistant', content: currentAnswer.value })
          }
          scrollBottom()
        } catch { }
      }
    }
  } catch (e: any) {
    messages.value.push({ role: 'assistant', content: `请求失败：${e.message}` })
  } finally {
    streaming.value = false
    currentAnswer.value = ''
    scrollBottom()
  }
}

onMounted(loadAgent)
</script>

<style scoped>
.share-page { min-height: 100vh; background: #f5f7fa; display: flex; justify-content: center; padding: 20px; }
.share-container { width: 100%; max-width: 800px; background: #fff; border-radius: 12px; box-shadow: 0 2px 12px rgba(0,0,0,0.08); display: flex; flex-direction: column; height: calc(100vh - 40px); }
.share-header { padding: 20px; border-bottom: 1px solid #e5e7eb; display: flex; align-items: center; gap: 12px; }
.chat-area { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
.messages { flex: 1; overflow-y: auto; padding: 20px; }
.welcome { text-align: center; padding: 40px 20px; }
.welcome-text { font-size: 16px; color: #374151; margin-bottom: 16px; }
.suggested { display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; }
.message-row { margin-bottom: 16px; display: flex; }
.message-row.user { justify-content: flex-end; }
.msg-bubble { max-width: 75%; padding: 12px 16px; border-radius: 12px; line-height: 1.6; }
.msg-bubble.user { background: #3b82f6; color: white; }
.msg-bubble.assistant { background: #f3f4f6; color: #1f2937; }
.input-area { padding: 12px 20px; border-top: 1px solid #e5e7eb; display: flex; align-items: flex-end; }
.typing { display: flex; gap: 4px; padding: 12px 16px; background: #f3f4f6; border-radius: 12px; }
.typing span { width: 8px; height: 8px; background: #9ca3af; border-radius: 50%; animation: bounce 1.4s infinite; }
.typing span:nth-child(2) { animation-delay: 0.2s; }
.typing span:nth-child(3) { animation-delay: 0.4s; }
@keyframes bounce { 0%, 60%, 100% { transform: translateY(0); } 30% { transform: translateY(-8px); } }
.loading { text-align: center; padding: 60px; color: #9ca3af; }
</style>
