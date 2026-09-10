<template>
  <div>
    <div class="bar">
      <h3 style="margin:0">API Key 管理</h3>
      <el-button type="primary" @click="showCreate = true">
        <el-icon><Plus /></el-icon> 新建 API Key
      </el-button>
    </div>

    <el-alert type="info" :closable="false" style="margin:16px 0"
      title="对外 API 接口：POST /api/v1/chat/（流式对话）、POST /api/v1/search/（知识库检索）。认证方式：Header Authorization: Bearer &lt;api_key&gt; 或 X-API-Key: &lt;api_key&gt;" />

    <el-table :data="apiKeys" border style="margin-top:16px">
      <el-table-column prop="name" label="名称" min-width="150" />
      <el-table-column prop="key_prefix" label="Key 前缀" width="200">
        <template #default="{ row }">
          <code>{{ row.key_prefix }}...</code>
        </template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="100" align="center">
        <template #default="{ row }">
          <el-tag size="small" :type="row.status === 'active' ? 'success' : 'info'">
            {{ row.status === 'active' ? '启用' : '禁用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="call_count" label="调用次数" width="100" align="center" />
      <el-table-column prop="last_used_at" label="最后使用" width="170" />
      <el-table-column prop="create_time" label="创建时间" width="170" />
      <el-table-column label="操作" width="150" align="center">
        <template #default="{ row }">
          <el-button link type="warning" @click="toggleKey(row)">
            {{ row.status === 'active' ? '禁用' : '启用' }}
          </el-button>
          <el-button link type="danger" @click="deleteKey(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-empty v-if="!apiKeys.length" description="暂无 API Key，点击右上角新建" :image-size="60" />

    <!-- 新建对话框 -->
    <el-dialog v-model="showCreate" title="新建 API Key" width="480px">
      <el-form label-width="80px">
        <el-form-item label="名称">
          <el-input v-model="newName" placeholder="给这个 API Key 起个名字" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" @click="createKey">创建</el-button>
      </template>
    </el-dialog>

    <!-- 创建成功显示完整 Key -->
    <el-dialog v-model="showKey" title="API Key 已创建（请妥善保存，仅显示一次）" width="560px">
      <el-alert type="warning" :closable="false" style="margin-bottom:16px"
        title="此 Key 仅显示一次，请立即复制保存。关闭后无法再次查看完整 Key。" />
      <el-input v-model="createdKey" type="textarea" :rows="2" readonly />
      <div style="margin-top:12px; text-align:right">
        <el-button type="primary" @click="copyKey">复制</el-button>
        <el-button @click="showKey = false">我已保存</el-button>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import request from '@/api/request'

const apiKeys = ref<any[]>([])
const showCreate = ref(false)
const newName = ref('')
const showKey = ref(false)
const createdKey = ref('')

async function load() {
  apiKeys.value = await request.get('/users/api-keys/')
}

async function createKey() {
  if (!newName.value.trim()) {
    ElMessage.warning('请输入名称')
    return
  }
  const data: any = await request.post('/users/api-keys/', { name: newName.value })
  createdKey.value = data.key
  showCreate.value = false
  showKey.value = true
  newName.value = ''
  load()
}

async function toggleKey(row: any) {
  await request.post(`/users/api-keys/${row.id}/toggle/`)
  ElMessage.success(row.status === 'active' ? '已禁用' : '已启用')
  load()
}

async function deleteKey(row: any) {
  try {
    await ElMessageBox.confirm('确定删除该 API Key？删除后无法恢复。', '删除', { type: 'warning' })
  } catch {
    return
  }
  await request.delete(`/users/api-keys/${row.id}/`)
  ElMessage.success('已删除')
  load()
}

function copyKey() {
  navigator.clipboard.writeText(createdKey.value)
  ElMessage.success('已复制到剪贴板')
}

onMounted(load)
</script>

<style scoped>
.bar { display: flex; justify-content: space-between; align-items: center; }
code { background: #f5f7fa; padding: 2px 6px; border-radius: 4px; font-size: 12px; }
</style>
