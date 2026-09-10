<template>
  <div class="chat-page">
    <div class="chat-layout">
      <!-- 会话列表侧边栏 -->
      <div class="session-sidebar">
        <div class="sidebar-header">
          <el-select v-model="selectedApp" placeholder="选择 AI 应用" style="width:100%"
            @change="onAppChange">
            <el-option v-for="a in apps" :key="a.id" :label="a.name" :value="a.id" />
          </el-select>
        </div>
        <el-button class="new-session-btn" type="primary" plain @click="newSession">
          <el-icon><Plus /></el-icon> 新会话
        </el-button>
        <div class="session-list">
          <div
            v-for="s in sessions"
            :key="s.session_id"
            class="session-item"
            :class="{ active: s.session_id === sessionId }"
            @click="selectSession(s.session_id)"
          >
            <div class="session-title">{{ s.last_content.slice(0, 30) || '新会话' }}</div>
            <div class="session-meta">
              <span>{{ s.msg_count }} 条</span>
              <span>{{ formatTime(s.last_time) }}</span>
            </div>
            <el-dropdown trigger="click" @command="(cmd) => onExport(cmd, s.session_id)"
              @click.stop>
              <el-button class="export-btn" link type="primary" title="导出">
                <el-icon><Download /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="md">导出 Markdown</el-dropdown-item>
                  <el-dropdown-item command="pdf">导出 PDF</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
            <el-button class="delete-btn" link type="danger" @click.stop="removeSession(s.session_id)">
              <el-icon><Delete /></el-icon>
            </el-button>
          </div>
          <el-empty v-if="!sessions.length" description="暂无会话" :image-size="60" />
        </div>
      </div>

      <!-- 对话区域 -->
      <div class="chat-main">
        <ChatWindow
          v-if="selectedApp"
          :app-id="selectedApp"
          :session-id="sessionId"
          @session-created="onSessionCreated"
        />
        <el-empty v-else description="请先选择一个 AI 应用开始对话" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Delete, Download } from '@element-plus/icons-vue'
import { listApps, listSessions, deleteSession, exportSession } from '@/api/chat'
import request from '@/api/request'
import type { Application, SessionSummary } from '@/types'
import ChatWindow from '@/components/ChatWindow.vue'

const route = useRoute()
const apps = ref<Application[]>([])
const sessions = ref<SessionSummary[]>([])
const selectedApp = ref<number | null>(null)
const sessionId = ref('')

async function loadApps() {
  apps.value = await listApps()
  const fromRoute = route.params.appId ? Number(route.params.appId) : null
  if (fromRoute) selectedApp.value = fromRoute
  else if (apps.value.length) selectedApp.value = apps.value[0].id
  if (selectedApp.value) loadSessions()
}

async function loadSessions() {
  if (!selectedApp.value) return
  sessions.value = await listSessions(selectedApp.value)
}

function onAppChange() {
  sessionId.value = ''
  loadSessions()
}

function newSession() {
  sessionId.value = ''
}

function selectSession(sid: string) {
  sessionId.value = sid
}

function onSessionCreated(sid: string) {
  sessionId.value = sid
  loadSessions()
}

async function removeSession(sid: string) {
  try {
    await ElMessageBox.confirm('确定删除该会话及其全部消息？', '删除会话', { type: 'warning' })
  } catch {
    return
  }
  await deleteSession(sid)
  ElMessage.success('会话已删除')
  if (sessionId.value === sid) sessionId.value = ''
  loadSessions()
}

async function onExport(format: string, sid: string) {
  if (format === 'md') {
    exportChat(sid)
  } else {
    exportPdf(sid)
  }
}

async function exportChat(sid: string) {
  try {
    const blob: any = await exportSession(sid)
    const url = window.URL.createObjectURL(new Blob([blob], { type: 'text/markdown' }))
    const a = document.createElement('a')
    a.href = url
    a.download = `chat_${sid.slice(0, 8)}.md`
    a.click()
    window.URL.revokeObjectURL(url)
    ElMessage.success('已导出 Markdown 文件')
  } catch {
    ElMessage.error('导出失败')
  }
}

async function exportPdf(sid: string) {
  try {
    const blob: any = await request.get('/chat/export/pdf/', {
      params: { session_id: sid },
      responseType: 'blob',
    })
    const url = window.URL.createObjectURL(new Blob([blob], { type: 'application/pdf' }))
    const a = document.createElement('a')
    a.href = url
    a.download = `chat_${sid.slice(0, 8)}.pdf`
    a.click()
    window.URL.revokeObjectURL(url)
    ElMessage.success('已导出 PDF 文件')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || 'PDF 导出失败（需要安装 reportlab）')
  }
}

function formatTime(t: string) {
  const d = new Date(t)
  const now = new Date()
  const sameDay = d.toDateString() === now.toDateString()
  if (sameDay) return d.toTimeString().slice(0, 5)
  return `${d.getMonth() + 1}/${d.getDate()}`
}

onMounted(loadApps)
</script>

<style scoped>
.chat-page { height: 100%; }
.chat-layout { display: flex; height: calc(100vh - 120px); gap: 12px; }
.session-sidebar {
  width: 260px; flex-shrink: 0; background: #fff; border-radius: 8px;
  border: 1px solid #e5e7eb; display: flex; flex-direction: column; overflow: hidden;
}
.sidebar-header { padding: 12px; border-bottom: 1px solid #f0f0f0; }
.new-session-btn { margin: 10px 12px; }
.session-list { flex: 1; overflow-y: auto; padding: 0 8px 8px; }
.session-item {
  position: relative; padding: 10px 12px; border-radius: 6px; cursor: pointer;
  margin-bottom: 4px; transition: background 0.15s;
}
.session-item:hover { background: #f5f7fa; }
.session-item.active { background: #ecf5ff; }
.session-title { font-size: 13px; font-weight: 500; color: #1f2937;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; padding-right: 48px; }
.session-meta { display: flex; justify-content: space-between; margin-top: 4px;
  font-size: 11px; color: #9ca3af; }
.delete-btn { position: absolute; top: 8px; right: 4px; padding: 2px; }
.export-btn { position: absolute; top: 8px; right: 28px; padding: 2px; }
.chat-main { flex: 1; background: #fff; border-radius: 8px; border: 1px solid #e5e7eb;
  overflow: hidden; }
</style>
