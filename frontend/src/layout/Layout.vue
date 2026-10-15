<template>
  <el-container class="layout">
    <el-aside width="220px" class="aside">
      <div class="logo">FHZSK</div>
      <el-menu :default-active="activeMenu" router class="menu">
        <el-menu-item index="/knowledge">
          <el-icon><Collection /></el-icon><span>知识库</span>
        </el-menu-item>
        <el-menu-item index="/apps" v-if="['admin', 'editor'].includes(role)">
          <el-icon><ChatDotRound /></el-icon><span>AI 应用</span>
        </el-menu-item>
        <el-menu-item index="/chat">
          <el-icon><ChatLineSquare /></el-icon><span>对话</span>
        </el-menu-item>
        <el-menu-item index="/agent/chat">
          <el-icon><MagicStick /></el-icon><span>智能体对话</span>
        </el-menu-item>
        <el-menu-item index="/agents" v-if="['admin', 'editor'].includes(role)">
          <el-icon><Cpu /></el-icon><span>智能体管理</span>
        </el-menu-item>
        <el-menu-item index="/agent-templates">
          <el-icon><Shop /></el-icon><span>智能体模板</span>
        </el-menu-item>
        <el-menu-item index="/mcp-servers" v-if="['admin', 'editor'].includes(role)">
          <el-icon><Connection /></el-icon><span>MCP 服务器</span>
        </el-menu-item>
        <el-menu-item index="/workflow" v-if="['admin', 'editor'].includes(role)">
          <el-icon><Connection /></el-icon><span>工作流编排</span>
        </el-menu-item>
        <el-menu-item index="/plugins" v-if="['admin', 'editor'].includes(role)">
          <el-icon><Plug /></el-icon><span>插件管理</span>
        </el-menu-item>
        <el-menu-item index="/dashboard" v-if="['admin', 'editor'].includes(role)">
          <el-icon><DataAnalysis /></el-icon><span>数据分析</span>
        </el-menu-item>
        <el-menu-item index="/model" v-if="role === 'admin'">
          <el-icon><Setting /></el-icon><span>模型配置</span>
        </el-menu-item>
        <el-menu-item index="/users" v-if="role === 'admin'">
          <el-icon><User /></el-icon><span>用户管理</span>
        </el-menu-item>
        <el-menu-item index="/api-keys">
          <el-icon><Key /></el-icon><span>API Key</span>
        </el-menu-item>
        <el-menu-item index="/audit" v-if="role === 'admin'">
          <el-icon><Notebook /></el-icon><span>审计日志</span>
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
              <el-dropdown-item command="change-password">修改密码</el-dropdown-item>
              <el-dropdown-item command="logout">退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </el-header>
      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>

    <!-- 首次登录强制修改密码 -->
    <el-dialog
      v-model="pwdDialogVisible"
      title="请修改初始密码"
      :close-on-click-modal="false"
      :close-on-press-escape="false"
      width="420px"
    >
      <el-form :model="pwdForm" label-width="80px">
        <el-form-item label="旧密码">
          <el-input v-model="pwdForm.old_password" type="password" show-password />
        </el-form-item>
        <el-form-item label="新密码">
          <el-input v-model="pwdForm.new_password" type="password" show-password placeholder="至少6位" />
        </el-form-item>
        <el-form-item label="确认密码">
          <el-input v-model="pwdForm.confirm_password" type="password" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button type="primary" :loading="pwdSaving" @click="submitPassword">确认修改</el-button>
      </template>
    </el-dialog>
  </el-container>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/store/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const activeMenu = computed(() => '/' + (route.path.split('/')[1] || 'knowledge'))
const title = computed(() => (route.meta.title as string) || 'FHZSK')
const role = computed(() => userStore.user?.role || '')

// 修改密码对话框
const pwdDialogVisible = ref(false)
const pwdSaving = ref(false)
const pwdForm = ref({ old_password: '', new_password: '', confirm_password: '' })

// 监听 mustChangePassword，首次登录时强制弹出
watch(
  () => userStore.mustChangePassword,
  (val) => {
    if (val) pwdDialogVisible.value = true
  },
  { immediate: true }
)

async function submitPassword() {
  if (!pwdForm.value.old_password || !pwdForm.value.new_password) {
    ElMessage.warning('请填写完整')
    return
  }
  if (pwdForm.value.new_password.length < 6) {
    ElMessage.warning('新密码至少6位')
    return
  }
  if (pwdForm.value.new_password !== pwdForm.value.confirm_password) {
    ElMessage.warning('两次输入的新密码不一致')
    return
  }
  pwdSaving.value = true
  try {
    await userStore.changePassword(pwdForm.value.old_password, pwdForm.value.new_password)
    ElMessage.success('密码修改成功')
    pwdDialogVisible.value = false
    pwdForm.value = { old_password: '', new_password: '', confirm_password: '' }
  } finally {
    pwdSaving.value = false
  }
}

function onCommand(cmd: string) {
  if (cmd === 'logout') {
    userStore.logout()
    router.push('/login')
  } else if (cmd === 'change-password') {
    pwdDialogVisible.value = true
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
