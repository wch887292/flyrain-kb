<template>
  <div class="chat-page">
    <div class="app-bar">
      <el-select v-model="selectedApp" placeholder="选择 AI 应用" style="width:240px"
        @change="onAppChange">
        <el-option v-for="a in apps" :key="a.id" :label="a.name" :value="a.id" />
      </el-select>
      <el-button @click="newSession">新会话</el-button>
    </div>
    <ChatWindow v-if="selectedApp" :app-id="selectedApp" :session-id="sessionId" />
    <el-empty v-else description="请先选择一个 AI 应用开始对话" />
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { listApps } from '@/api/chat'
import type { Application } from '@/types'
import ChatWindow from '@/components/ChatWindow.vue'

const route = useRoute()
const apps = ref<Application[]>([])
const selectedApp = ref<number | null>(null)
const sessionId = ref('')

async function loadApps() {
  apps.value = await listApps()
  const fromRoute = route.params.appId ? Number(route.params.appId) : null
  if (fromRoute) selectedApp.value = fromRoute
  else if (apps.value.length) selectedApp.value = apps.value[0].id
}

function onAppChange() {
  sessionId.value = ''
}
function newSession() {
  sessionId.value = ''
}

onMounted(loadApps)
</script>

<style scoped>
.chat-page { height: 100%; }
.app-bar { display: flex; gap: 8px; margin-bottom: 12px; }
</style>
