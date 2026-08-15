<template>
  <div class="chat-window">
    <div ref="scrollRef" class="messages">
      <div v-for="(m, i) in messages" :key="i" class="msg" :class="m.role">
        <div class="bubble">{{ m.content || '……' }}</div>
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
import { nextTick, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { chatStream } from '@/api/chat'

const props = defineProps<{ appId: number; sessionId?: string }>()

interface Msg { role: 'user' | 'assistant'; content: string }
const messages = ref<Msg[]>([])
const input = ref('')
const streaming = ref(false)
const scrollRef = ref<HTMLElement | null>(null)

function scrollToBottom() {
  nextTick(() => {
    if (scrollRef.value) scrollRef.value.scrollTop = scrollRef.value.scrollHeight
  })
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
      onDone: () => {
        streaming.value = false
        scrollToBottom()
      },
      onError: (msg) => {
        streaming.value = false
        ElMessage.error(msg)
      }
    }
  )
  streaming.value = false
}
</script>

<style scoped>
.chat-window { display: flex; flex-direction: column; height: calc(100vh - 140px); }
.messages { flex: 1; overflow-y: auto; padding: 16px; }
.msg { display: flex; margin-bottom: 12px; }
.msg.user { justify-content: flex-end; }
.bubble { max-width: 70%; padding: 10px 14px; border-radius: 10px; line-height: 1.6;
  white-space: pre-wrap; word-break: break-word; }
.msg.user .bubble { background: #409eff; color: #fff; }
.msg.assistant .bubble { background: #fff; border: 1px solid #e5e7eb; }
.input-bar { display: flex; gap: 8px; padding: 12px; background: #fff; border-top: 1px solid #eee; }
.input-bar .el-input { flex: 1; }
</style>
