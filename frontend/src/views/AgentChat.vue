<template>
  <div class="agent-chat">
    <!-- 左侧：智能体 + 会话列表 -->
    <div class="sidebar">
      <div class="sidebar-header">
        <el-button type="primary" size="small" style="width:100%" @click="newChat">
          <el-icon><Plus /></el-icon> 新对话
        </el-button>
      </div>
      <div class="sidebar-section">
        <div class="section-title">智能体</div>
        <div v-for="a in agents" :key="a.id"
          class="agent-item" :class="{ active: currentAgent?.id === a.id }"
          @click="selectAgent(a)">
          <el-avatar :size="32" :src="a.avatar">{{ a.name.charAt(0) }}</el-avatar>
          <div class="agent-info">
            <div class="agent-name">{{ a.name }}</div>
            <div class="agent-role">{{ a.role || a.description }}</div>
          </div>
        </div>
      </div>
      <div class="sidebar-section" style="flex:1;overflow-y:auto">
        <div class="section-title">历史会话</div>
        <div v-for="c in conversations" :key="c.id"
          class="conv-item" :class="{ active: currentSessionId === c.session_id }"
          @click="selectConversation(c)">
          <div class="conv-title">{{ c.title }}</div>
          <div class="conv-time">{{ c.update_time }}</div>
        </div>
        <el-empty v-if="!conversations.length" description="暂无历史会话" :image-size="40" />
      </div>
    </div>

    <!-- 右侧：对话区域 -->
    <div class="chat-area">
      <div class="chat-header">
        <el-avatar :size="36" :src="currentAgent?.avatar">
          {{ currentAgent?.name?.charAt(0) }}
        </el-avatar>
        <div>
          <div style="font-weight:600">{{ currentAgent?.name || '选择智能体' }}</div>
          <div style="font-size:12px;color:#9ca3af">{{ currentAgent?.role }}</div>
        </div>
      </div>

      <div class="messages" ref="messagesRef">
        <div v-if="messages.length === 0 && currentAgent" class="welcome">
          <div class="welcome-text">{{ currentAgent.opening_message }}</div>
          <div class="suggested" v-if="currentAgent.suggested_questions?.length">
            <el-button v-for="q in currentAgent.suggested_questions" :key="q"
              size="small" plain @click="sendQuery(q)">{{ q }}</el-button>
          </div>
        </div>

        <div v-for="(m, idx) in messages" :key="idx" class="message-row" :class="m.role">
          <template v-if="m.role === 'user'">
            <div class="msg-bubble user">{{ m.content }}</div>
          </template>
          <template v-else-if="m.role === 'assistant'">
            <!-- 思考过程 -->
            <div v-if="m.reasoning && currentAgent?.enable_reasoning" class="reasoning-block">
              <div class="reasoning-header" @click="m.showReasoning = !m.showReasoning">
                <el-icon><ArrowRight v-if="!m.showReasoning" /><ArrowDown v-else /></el-icon>
                思考过程
              </div>
              <div v-if="m.showReasoning" class="reasoning-content">{{ m.reasoning }}</div>
            </div>
            <!-- 工具调用 -->
            <div v-for="(tc, ti) in m.tool_calls" :key="ti" class="tool-call-block">
              <el-tag size="small" type="warning">
                <el-icon><Tools /></el-icon> 调用工具：{{ tc.tool }}
              </el-tag>
              <pre v-if="tc.code" class="code-block">{{ tc.input }}</pre>
              <div v-else class="tool-input">{{ tc.input }}</div>
            </div>
            <!-- 最终回答 -->
            <div class="msg-bubble assistant" v-html="renderMarkdown(m.content)"></div>
          </template>
          <template v-else-if="m.role === 'tool'">
            <div class="tool-result-block">
              <el-tag size="small" type="success">
                <el-icon><Check /></el-icon> {{ m.tool_name }} 返回结果
              </el-tag>
              <div class="tool-result">{{ m.content }}</div>
              <div v-if="m.images && m.images.length" class="tool-images">
                <img v-for="(img, ii) in m.images" :key="ii"
                  :src="'data:image/png;base64,' + img" class="chart-img" />
              </div>
            </div>
          </template>
        </div>

        <!-- 流式输出中 -->
        <div v-if="streaming" class="message-row assistant">
          <div v-if="currentReasoning" class="reasoning-block">
            <div class="reasoning-header">
              <el-icon><Loading /></el-icon> 思考中...
            </div>
            <div class="reasoning-content">{{ currentReasoning }}</div>
          </div>
          <div v-if="currentToolCall" class="tool-call-block">
            <el-tag size="small" type="warning">
              <el-icon><Loading /></el-icon> 调用工具：{{ currentToolCall.tool }}
            </el-tag>
            <pre v-if="currentToolCall.code" class="code-block">{{ currentToolCall.input }}</pre>
            <div v-else class="tool-input">{{ currentToolCall.input }}</div>
          </div>
          <div v-if="currentAnswer" class="msg-bubble assistant" v-html="renderMarkdown(currentAnswer)"></div>
          <div v-else class="typing">
            <span></span><span></span><span></span>
          </div>
        </div>
      </div>

      <div class="input-area">
        <el-upload :show-file-list="false" :before-upload="beforeUpload"
          :http-request="customUpload" accept=".csv,.xlsx,.xls,.txt,.json,.xml,.md,.py,.pdf">
          <el-button :disabled="streaming || !currentAgent">
            <el-icon><Upload /></el-icon>
          </el-button>
        </el-upload>
        <el-input v-model="inputText" type="textarea" :rows="2"
          placeholder="输入消息，Enter 发送，Shift+Enter 换行。支持上传 CSV/Excel 供代码分析"
          @keydown.enter.exact.prevent="send" :disabled="streaming || !currentAgent" style="margin-left:8px" />
        <el-button type="primary" :loading="streaming" :disabled="!inputText.trim() || !currentAgent"
          @click="send" style="margin-left:8px">发送</el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick, computed } from 'vue'
import { useRoute } from 'vue-router'
import { Plus, ArrowRight, ArrowDown, Tools, Check, Loading, Upload } from '@element-plus/icons-vue'
import {
  listAgents, listAgentConversations, getAgentHistory, agentChat,
  type Agent, type AgentConversation, type AgentMessage
} from '@/api/agent'

const route = useRoute()
const agents = ref<Agent[]>([])
const conversations = ref<AgentConversation[]>([])
const currentAgent = ref<Agent | null>(null)
const currentSessionId = ref<string>('')
const messages = ref<any[]>([])
const inputText = ref('')
const streaming = ref(false)
const messagesRef = ref<HTMLElement>()

// 流式状态
const currentReasoning = ref('')
const currentToolCall = ref<{ tool: string; input: string } | null>(null)
const currentAnswer = ref('')
const toolCalls = ref<any[]>([])

function renderMarkdown(text: string): string {
  // 简单的 Markdown 渲染：代码块、加粗、换行
  let html = text
    .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br>')
  return html
}

async function scrollBottom() {
  await nextTick()
  if (messagesRef.value) {
    messagesRef.value.scrollTop = messagesRef.value.scrollHeight
  }
}

async function loadAgents() {
  agents.value = await listAgents()
  const agentId = Number(route.params.id)
  if (agentId && agents.value.length) {
    const found = agents.value.find(a => a.id === agentId)
    if (found) {
      currentAgent.value = found
    }
  }
  if (!currentAgent.value && agents.value.length) {
    currentAgent.value = agents.value[0]
  }
}

async function loadConversations() {
  conversations.value = await listAgentConversations()
}

function selectAgent(agent: Agent) {
  currentAgent.value = agent
  currentSessionId.value = ''
  messages.value = []
  loadConversations()
}

function newChat() {
  currentSessionId.value = ''
  messages.value = []
}

async function selectConversation(conv: AgentConversation) {
  currentSessionId.value = conv.session_id
  const agent = agents.value.find(a => a.id === conv.agent_id)
  if (agent) currentAgent.value = agent
  const history = await getAgentHistory(conv.session_id)
  messages.value = history.map(m => ({ ...m, showReasoning: false }))
  scrollBottom()
}

function sendQuery(q: string) {
  inputText.value = q
  send()
}

function beforeUpload(file: File) {
  const allowed = ['.csv', '.xlsx', '.xls', '.txt', '.json', '.xml', '.md', '.py', '.pdf']
  const ext = '.' + file.name.split('.').pop()?.toLowerCase()
  if (!allowed.includes(ext)) {
    ElMessage.error('不支持的文件类型')
    return false
  }
  if (file.size > 20 * 1024 * 1024) {
    ElMessage.error('文件大小不能超过 20MB')
    return false
  }
  return true
}

async function customUpload(options: any) {
  if (!currentSessionId.value) {
    ElMessage.warning('请先开始对话')
    return
  }
  const formData = new FormData()
  formData.append('session_id', currentSessionId.value)
  formData.append('file', options.file)

  try {
    const token = localStorage.getItem('token') || ''
    const resp = await fetch('/api/agent/upload/', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` },
      body: formData,
    })
    const data = await resp.json()
    if (resp.ok) {
      ElMessage.success(`文件已上传：${data.file_name}`)
      // 自动发送一条消息提示智能体
      inputText.value = `我已上传文件 ${data.file_name}，请用代码执行工具分析这个文件（文件路径：data/${data.file_name}）`
      send()
    } else {
      ElMessage.error(data.detail || '上传失败')
    }
  } catch (e: any) {
    ElMessage.error('上传失败：' + e.message)
  }
}

async function send() {
  const query = inputText.value.trim()
  if (!query || !currentAgent.value || streaming.value) return

  inputText.value = ''
  messages.value.push({ role: 'user', content: query })
  streaming.value = true
  currentReasoning.value = ''
  currentToolCall.value = null
  currentAnswer.value = ''
  toolCalls.value = []
  scrollBottom()

  try {
    const resp = await agentChat(currentAgent.value.id, query, currentSessionId.value || undefined)
    if (!resp.ok || !resp.body) {
      throw new Error('请求失败')
    }

    const reader = resp.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    let assistantMsg: any = null

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
          if (evt.type === 'reasoning') {
            currentReasoning.value += evt.content
          } else if (evt.type === 'tool_call') {
            currentToolCall.value = { tool: evt.tool, input: evt.input }
            toolCalls.value.push({ tool: evt.tool, input: evt.input })
          } else if (evt.type === 'tool_result') {
            // 工具结果作为独立消息
            messages.value.push({
              role: 'tool', tool_name: evt.tool, content: evt.result,
              images: evt.images || []
            })
            currentToolCall.value = null
          } else if (evt.type === 'token') {
            currentAnswer.value += evt.content
          } else if (evt.type === 'done') {
            currentAnswer.value = evt.answer || currentAnswer.value
            currentSessionId.value = evt.session_id || currentSessionId.value
            assistantMsg = {
              role: 'assistant',
              content: currentAnswer.value,
              reasoning: currentReasoning.value,
              tool_calls: toolCalls.value,
              showReasoning: false,
            }
          } else if (evt.type === 'error') {
            currentAnswer.value = `错误：${evt.message}`
            assistantMsg = {
              role: 'assistant', content: currentAnswer.value,
              reasoning: '', tool_calls: [], showReasoning: false,
            }
          }
          scrollBottom()
        } catch (e) { /* 忽略解析错误 */ }
      }
    }

    if (assistantMsg) {
      messages.value.push(assistantMsg)
    }
    loadConversations()
  } catch (e: any) {
    messages.value.push({
      role: 'assistant', content: `请求失败：${e.message}`,
      reasoning: '', tool_calls: [], showReasoning: false,
    })
  } finally {
    streaming.value = false
    currentReasoning.value = ''
    currentToolCall.value = null
    currentAnswer.value = ''
    toolCalls.value = []
    scrollBottom()
  }
}

onMounted(() => { loadAgents(); loadConversations() })
</script>

<style scoped>
.agent-chat { display: flex; height: calc(100vh - 100px); }
.sidebar { width: 260px; border-right: 1px solid #e5e7eb; display: flex; flex-direction: column; padding: 12px; gap: 12px; }
.sidebar-header { padding-bottom: 12px; border-bottom: 1px solid #f3f4f6; }
.sidebar-section { }
.section-title { font-size: 12px; color: #9ca3af; margin-bottom: 8px; font-weight: 600; }
.agent-item { display: flex; align-items: center; gap: 8px; padding: 8px; border-radius: 6px; cursor: pointer; margin-bottom: 4px; }
.agent-item:hover { background: #f3f4f6; }
.agent-item.active { background: #eff6ff; }
.agent-info { flex: 1; min-width: 0; }
.agent-name { font-size: 14px; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.agent-role { font-size: 11px; color: #9ca3af; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.conv-item { padding: 8px; border-radius: 6px; cursor: pointer; margin-bottom: 4px; }
.conv-item:hover { background: #f3f4f6; }
.conv-item.active { background: #eff6ff; }
.conv-title { font-size: 13px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.conv-time { font-size: 11px; color: #9ca3af; }

.chat-area { flex: 1; display: flex; flex-direction: column; }
.chat-header { padding: 12px 20px; border-bottom: 1px solid #e5e7eb; display: flex; align-items: center; gap: 12px; }
.messages { flex: 1; overflow-y: auto; padding: 20px; }
.welcome { text-align: center; padding: 60px 20px; }
.welcome-text { font-size: 18px; color: #374151; margin-bottom: 20px; }
.suggested { display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; }

.message-row { margin-bottom: 16px; display: flex; }
.message-row.user { justify-content: flex-end; }
.msg-bubble { max-width: 75%; padding: 12px 16px; border-radius: 12px; line-height: 1.6; }
.msg-bubble.user { background: #3b82f6; color: white; border-bottom-right-radius: 4px; }
.msg-bubble.assistant { background: #f3f4f6; color: #1f2937; border-bottom-left-radius: 4px; }
.msg-bubble.assistant :deep(pre) { background: #1f2937; color: #e5e7eb; padding: 12px; border-radius: 6px; overflow-x: auto; }
.msg-bubble.assistant :deep(code) { font-family: monospace; }

.reasoning-block { margin-bottom: 8px; max-width: 75%; }
.reasoning-header { display: flex; align-items: center; gap: 4px; font-size: 12px; color: #9ca3af; cursor: pointer; padding: 4px 0; }
.reasoning-content { background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 6px; padding: 8px 12px; font-size: 13px; color: #6b7280; white-space: pre-wrap; }

.tool-call-block { margin-bottom: 8px; max-width: 75%; }
.tool-input { margin-top: 4px; font-size: 13px; color: #92400e; background: #fffbeb; padding: 6px 10px; border-radius: 4px; }
.code-block { margin-top: 4px; font-size: 13px; background: #1f2937; color: #e5e7eb; padding: 10px 12px; border-radius: 6px; overflow-x: auto; white-space: pre-wrap; font-family: 'Consolas', 'Monaco', monospace; max-height: 300px; overflow-y: auto; }

.tool-result-block { margin-bottom: 8px; max-width: 75%; }
.tool-result { margin-top: 4px; font-size: 13px; color: #065f46; background: #ecfdf5; padding: 8px 12px; border-radius: 4px; max-height: 200px; overflow-y: auto; white-space: pre-wrap; }
.tool-images { margin-top: 8px; display: flex; flex-wrap: wrap; gap: 8px; }
.chart-img { max-width: 100%; max-height: 300px; border-radius: 6px; border: 1px solid #e5e7eb; }

.typing { display: flex; gap: 4px; padding: 12px 16px; background: #f3f4f6; border-radius: 12px; }
.typing span { width: 8px; height: 8px; background: #9ca3af; border-radius: 50%; animation: bounce 1.4s infinite; }
.typing span:nth-child(2) { animation-delay: 0.2s; }
.typing span:nth-child(3) { animation-delay: 0.4s; }
@keyframes bounce { 0%, 60%, 100% { transform: translateY(0); } 30% { transform: translateY(-8px); } }

.input-area { padding: 12px 20px; border-top: 1px solid #e5e7eb; display: flex; align-items: flex-end; }
</style>
