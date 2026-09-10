<template>
  <div class="chat-window">
    <div ref="scrollRef" class="messages">
      <div v-for="(m, i) in messages" :key="i" class="msg" :class="m.role">
        <div class="bubble">{{ m.content || '……' }}</div>
        <div v-if="m.role === 'assistant' && m.sources && m.sources.length" class="sources">
          <div class="sources-title">引用来源（{{ m.sources.length }}）</div>
          <div class="source-list">
            <span v-for="(s, si) in m.sources" :key="si" class="source-tag">
              <el-icon><Document /></el-icon>
              《{{ s.doc_name }}》{{ s.page_no ? `第${s.page_no}页` : '' }}
            </span>
          </div>
        </div>
        <div v-if="m.role === 'assistant' && m.id" class="feedback-bar">
          <el-button link size="small" :class="{ active: m.feedback === 'like' }"
            @click="submitFeedback(m, 'like')">
            <el-icon><ThumbUp /></el-icon> 有用
          </el-button>
          <el-button link size="small" :class="{ active: m.feedback === 'dislike' }"
            @click="submitFeedback(m, 'dislike')">
            <el-icon><ThumbDown /></el-icon> 无用
          </el-button>
        </div>
      </div>
      <div v-if="streaming" class="msg assistant"><div class="bubble">回答生成中…</div></div>
    </div>
    <div class="input-bar">
      <el-input v-model="input" type="textarea" :rows="2" placeholder="输入问题，Enter 发送"
        @keydown.enter.exact.prevent="send" />
      <el-button type="primary" :disabled="streaming" @click="send">发送</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Document, ThumbUp, ThumbDown } from '@element-plus/icons-vue'
import { chatStream, listHistory, submitFeedback as apiFeedback } from '@/api/chat'

const props = defineProps<{ appId: number; sessionId?: string }>()
const emit = defineEmits<{ (e: 'session-created', sessionId: string): void }>()

interface Source { doc_name: string; page_no: number }
interface Msg {
  id?: number
  role: 'user' | 'assistant'
  content: string
  sources?: Source[]
  feedback?: 'like' | 'dislike' | null
}
const messages = ref<Msg[]>([])
const input = ref('')
const streaming = ref(false)
const scrollRef = ref<HTMLElement | null>(null)

function scrollToBottom() {
  nextTick(() => {
    if (scrollRef.value) scrollRef.value.scrollTop = scrollRef.value.scrollHeight
  })
}

async function loadHistory() {
  if (!props.sessionId) {
    messages.value = []
    return
  }
  try {
    const history = await listHistory(props.sessionId)
    messages.value = history.map(h => ({
      id: h.id,
      role: h.role as 'user' | 'assistant',
      content: h.content,
      feedback: (h as any).feedback || null,
    }))
    scrollToBottom()
  } catch {
    /* 历史加载失败不阻塞对话 */
  }
}

watch(() => props.sessionId, () => {
  if (!streaming.value) loadHistory()
})

async function submitFeedback(msg: Msg, fb: 'like' | 'dislike') {
  if (!msg.id) return
  // 再次点击相同反馈则取消
  const newFb = msg.feedback === fb ? null : fb
  try {
    if (newFb) {
      await apiFeedback(msg.id, newFb)
      msg.feedback = newFb
      ElMessage.success(newFb === 'like' ? '感谢反馈，已标记为有用' : '已标记为无用，我们会持续优化')
    } else {
      // 取消反馈：后端暂不支持删除，这里只更新前端状态
      msg.feedback = null
    }
  } catch {
    /* 错误已由拦截器提示 */
  }
}

async function send() {
  const query = input.value.trim()
  if (!query || streaming.value) return
  if (!props.appId) {
    ElMessage.warning('请先选择一个 AI 应用')
    return
  }
  messages.value.push({ role: 'user', content: query })
  messages.value.push({ role: 'assistant', content: '' })
  input.value = ''
  streaming.value = true
  scrollToBottom()

  await chatStream(
    { app_id: props.appId, query, session_id: props.sessionId },
    {
      onToken: (text) => {
        const last = messages.value[messages.value.length - 1]
        last.content += text
        scrollToBottom()
      },
      onDone: (data) => {
        streaming.value = false
        scrollToBottom()
        const last = messages.value[messages.value.length - 1]
        if (last && last.role === 'assistant') {
          if (data?.message_id) last.id = data.message_id
          if (data?.sources) last.sources = data.sources
        }
        if (data?.session_id && !props.sessionId) {
          emit('session-created', data.session_id)
        }
      },
      onError: (msg) => {
        streaming.value = false
        ElMessage.error(msg)
      }
    }
  )
  streaming.value = false
}

loadHistory()
</script>

<style scoped>
.chat-window { display: flex; flex-direction: column; height: calc(100vh - 140px); }
.messages { flex: 1; overflow-y: auto; padding: 16px; }
.msg { display: flex; margin-bottom: 12px; flex-direction: column; }
.msg.user { align-items: flex-end; }
.bubble { max-width: 70%; padding: 10px 14px; border-radius: 10px; line-height: 1.6;
  white-space: pre-wrap; word-break: break-word; }
.msg.user .bubble { background: #409eff; color: #fff; }
.msg.assistant .bubble { background: #fff; border: 1px solid #e5e7eb; }
.sources { margin-top: 8px; max-width: 70%; }
.sources-title { font-size: 12px; color: #9ca3af; margin-bottom: 4px; }
.source-list { display: flex; flex-wrap: wrap; gap: 6px; }
.source-tag {
  display: inline-flex; align-items: center; gap: 4px;
  font-size: 12px; color: #4b5563; background: #f3f4f6;
  padding: 3px 8px; border-radius: 4px; border: 1px solid #e5e7eb;
}
.source-tag .el-icon { font-size: 12px; }
.feedback-bar { display: flex; gap: 4px; margin-top: 6px; }
.feedback-bar .el-button { color: #9ca3af; padding: 2px 6px; }
.feedback-bar .el-button:hover { color: #409eff; }
.feedback-bar .el-button.active { color: #409eff; font-weight: 600; }
.feedback-bar .el-button.active:last-child { color: #f56c6c; }
.input-bar { display: flex; gap: 8px; padding: 12px; background: #fff; border-top: 1px solid #eee; }
.input-bar .el-input { flex: 1; }
</style>
