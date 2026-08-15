<template>
  <div>
    <div class="bar">
      <h3 style="margin:0">用户管理</h3>
      <el-button type="primary" style="margin-left:auto" @click="openCreate">新建用户</el-button>
    </div>

    <el-table :data="users" border style="margin-top:16px">
      <el-table-column prop="username" label="用户名" />
      <el-table-column prop="nickname" label="昵称" />
      <el-table-column prop="role" label="角色" width="140">
        <template #default="{ row }">
          <el-tag :type="row.role === 'admin' ? 'danger' : row.role === 'editor' ? 'warning' : 'info'">
            {{ ROLE_LABELS[row.role] || row.role }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="tenant" label="租户" />
      <el-table-column prop="create_time" label="创建时间" width="180" />
      <el-table-column label="操作" width="200">
        <template #default="{ row }">
          <el-button link type="primary" :disabled="row.id === currentUser.id"
            @click="openRole(row)">改角色</el-button>
          <el-popconfirm title="确认删除该用户？" @confirm="remove(row)">
            <template #reference>
              <el-button link type="danger" :disabled="row.id === currentUser.id">删除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <!-- 新建用户 -->
    <el-dialog v-model="createVisible" title="新建用户" width="460px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="用户名" required>
          <el-input v-model="form.username" placeholder="登录用户名" />
        </el-form-item>
        <el-form-item label="密码" required>
          <el-input v-model="form.password" type="password" placeholder="至少 6 位" />
        </el-form-item>
        <el-form-item label="昵称">
          <el-input v-model="form.nickname" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="form.email" />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="form.role" style="width:100%">
            <el-option v-for="r in roleOptions" :key="r.value" :label="r.label" :value="r.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="租户">
          <el-input v-model="form.tenant_name" placeholder="默认租户" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitCreate">确定</el-button>
      </template>
    </el-dialog>

    <!-- 改角色 -->
    <el-dialog v-model="roleVisible" title="修改角色" width="420px">
      <p>用户：<b>{{ editing?.username }}</b></p>
      <el-form label-width="80px">
        <el-form-item label="角色">
          <el-select v-model="editingRole" style="width:100%">
            <el-option v-for="r in roleOptions" :key="r.value" :label="r.label" :value="r.value" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="roleVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitRole">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { listUsers, createUser, updateUser, deleteUser } from '@/api/user'
import { ROLE_LABELS } from '@/types'
import type { User } from '@/types'
import { useUserStore } from '@/store/user'

const userStore = useUserStore()
const currentUser = computed(() => userStore.user as User)

const users = ref<User[]>([])
const roleOptions = [
  { value: 'admin', label: '管理员' },
  { value: 'editor', label: '知识库维护' },
  { value: 'user', label: '普通用户' },
]

const createVisible = ref(false)
const roleVisible = ref(false)
const saving = ref(false)
const editing = ref<User | null>(null)
const editingRole = ref('user')

const form = reactive({
  username: '',
  password: '',
  nickname: '',
  email: '',
  role: 'user',
  tenant_name: '默认租户',
})

async function load() {
  users.value = await listUsers()
}

function openCreate() {
  Object.assign(form, {
    username: '', password: '', nickname: '', email: '',
    role: 'user', tenant_name: '默认租户',
  })
  createVisible.value = true
}

async function submitCreate() {
  if (!form.username || !form.password) {
    ElMessage.warning('用户名与密码必填')
    return
  }
  saving.value = true
  try {
    await createUser({ ...form })
    ElMessage.success('已创建')
    createVisible.value = false
    load()
  } finally {
    saving.value = false
  }
}

function openRole(row: User) {
  editing.value = row
  editingRole.value = row.role
  roleVisible.value = true
}

async function submitRole() {
  if (!editing.value) return
  saving.value = true
  try {
    await updateUser(editing.value.id, { role: editingRole.value })
    ElMessage.success('角色已更新')
    roleVisible.value = false
    load()
  } finally {
    saving.value = false
  }
}

async function remove(row: User) {
  try {
    await deleteUser(row.id)
    ElMessage.success('已删除')
    load()
  } catch {
    /* 错误提示已由拦截器处理 */
  }
}

onMounted(load)
</script>

<style scoped>
.bar { display: flex; align-items: center; gap: 8px; }
</style>
