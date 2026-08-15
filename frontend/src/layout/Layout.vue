<template>
  <el-container class="layout">
    <el-aside width="220px" class="aside">
      <div class="logo">飞虹智知识库</div>
      <el-menu :default-active="activeMenu" router class="menu">
        <el-menu-item index="/knowledge">
          <el-icon><Collection /></el-icon><span>知识库</span>
        </el-menu-item>
        <el-menu-item index="/apps" v-if="['admin', 'editor'].includes(role)">
          <el-icon><ChatDotRound /></el-icon><span>AI 应用</span>
        </el-menu-item>
        <el-menu-item index="/model" v-if="role === 'admin'">
          <el-icon><Setting /></el-icon><span>模型配置</span>
        </el-menu-item>
        <el-menu-item index="/users" v-if="role === 'admin'">
          <el-icon><User /></el-icon><span>用户管理</span>
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="header">
        <span class="title">{{ title }}</span>
        <el-dropdown @command="onCommand">
          <span class="user">{{ userStore.user?.nickname || userStore.user?.username }}</span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="logout">退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </el-header>
      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/store/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const activeMenu = computed(() => '/' + (route.path.split('/')[1] || 'knowledge'))
const title = computed(() => (route.meta.title as string) || '飞虹智知识库')
const role = computed(() => userStore.user?.role || '')

function onCommand(cmd: string) {
  if (cmd === 'logout') {
    userStore.logout()
    router.push('/login')
  }
}
</script>

<style scoped>
.layout { height: 100%; }
.aside { background: #1f2937; color: #fff; }
.logo { height: 56px; display: flex; align-items: center; justify-content: center;
  font-weight: 700; font-size: 16px; color: #fff; border-bottom: 1px solid #374151; }
.menu { border-right: none; background: #1f2937; }
.menu :deep(.el-menu-item) { color: #cbd5e1; }
.menu :deep(.el-menu-item.is-active) { background: #374151; color: #fff; }
.header { display: flex; align-items: center; justify-content: space-between;
  background: #fff; border-bottom: 1px solid #e5e7eb; }
.title { font-weight: 600; }
.user { cursor: pointer; }
.main { background: #f5f7fa; }
</style>
