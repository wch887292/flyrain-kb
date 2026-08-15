<template>
  <div class="login-wrap">
    <el-card class="login-card">
      <h2 class="title">飞虹智知识库</h2>
      <el-tabs v-model="mode">
        <el-tab-pane label="登录" name="login" />
        <el-tab-pane label="注册" name="register" />
      </el-tabs>
      <el-form :model="form" label-width="0" @submit.prevent>
        <el-input v-model="form.username" placeholder="用户名" class="field" />
        <el-input v-model="form.password" type="password" placeholder="密码"
          class="field" show-password />
        <template v-if="mode === 'register'">
          <el-input v-model="form.email" placeholder="邮箱(可选)" class="field" />
          <el-input v-model="form.tenant_name" placeholder="租户名称(可选)" class="field" />
        </template>
        <el-button type="primary" class="btn" :loading="loading" @click="submit">
          {{ mode === 'login' ? '登录' : '注册并登录' }}
        </el-button>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/store/user'
import { register } from '@/api/user'

const router = useRouter()
const userStore = useUserStore()
const mode = ref<'login' | 'register'>('login')
const loading = ref(false)

const form = reactive({
  username: '',
  password: '',
  email: '',
  tenant_name: ''
})

async function submit() {
  if (!form.username || !form.password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }
  loading.value = true
  try {
    if (mode.value === 'register') {
      await register({
        username: form.username,
        password: form.password,
        email: form.email || undefined,
        tenant_name: form.tenant_name || undefined
      })
      await userStore.login(form.username, form.password)
    } else {
      await userStore.login(form.username, form.password)
    }
    router.push('/')
  } catch {
    /* 错误已在拦截器提示 */
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-wrap { height: 100%; display: flex; align-items: center; justify-content: center;
  background: linear-gradient(135deg, #1f2937, #374151); }
.login-card { width: 360px; padding: 8px 16px; }
.title { text-align: center; margin: 8px 0 16px; }
.field { margin-bottom: 14px; }
.btn { width: 100%; }
</style>
