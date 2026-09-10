<template>
  <div>
    <div class="bar">
      <h3 style="margin:0">插件管理</h3>
      <el-button type="primary" @click="openCreate">
        <el-icon><Plus /></el-icon> 新建插件
      </el-button>
    </div>

    <el-alert type="info" :closable="false" style="margin:16px 0"
      title="HTTP 插件：可在工作流步骤中调用外部 API。body_template 中可用 {{input}} 引用工作流输入，{{step_N.output}} 引用前面步骤的输出。" />

    <el-table :data="plugins" border style="margin-top:16px">
      <el-table-column prop="name" label="名称" min-width="150" />
      <el-table-column prop="type" label="类型" width="100" align="center">
        <template #default="{ row }">
          <el-tag size="small">{{ row.type === 'http' ? 'HTTP' : row.type }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
      <el-table-column label="请求地址" min-width="250" show-overflow-tooltip>
        <template #default="{ row }">
          <code>{{ row.config?.method || 'POST' }} {{ row.config?.url || '-' }}</code>
        </template>
      </el-table-column>
      <el-table-column prop="is_active" label="状态" width="80" align="center">
        <template #default="{ row }">
          <el-tag size="small" :type="row.is_active ? 'success' : 'info'">
            {{ row.is_active ? '启用' : '禁用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="180" align="center">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button link type="success" @click="testPlugin(row)">测试</el-button>
          <el-button link type="danger" @click="deletePlugin(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-empty v-if="!plugins.length" description="暂无插件，点击右上角新建" :image-size="60" />

    <!-- 编辑对话框 -->
    <el-dialog v-model="showEdit" :title="editing.id ? '编辑插件' : '新建插件'" width="640px">
      <el-form label-width="100px">
        <el-form-item label="名称">
          <el-input v-model="editing.name" placeholder="插件名称" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="editing.description" placeholder="插件描述" />
        </el-form-item>
        <el-form-item label="请求方法">
          <el-select v-model="editing.config.method" style="width:120px">
            <el-option label="POST" value="POST" />
            <el-option label="GET" value="GET" />
            <el-option label="PUT" value="PUT" />
          </el-select>
        </el-form-item>
        <el-form-item label="请求 URL">
          <el-input v-model="editing.config.url" placeholder="https://api.example.com/endpoint" />
        </el-form-item>
        <el-form-item label="请求头 (JSON)">
          <el-input v-model="headersText" type="textarea" :rows="3"
            placeholder='{"Authorization": "Bearer xxx"}' />
        </el-form-item>
        <el-form-item label="请求体模板">
          <el-input v-model="editing.config.body_template" type="textarea" :rows="4"
            placeholder='{"input": "{{input}}"}' />
        </el-form-item>
        <el-form-item label="超时(秒)">
          <el-input-number v-model="editing.config.timeout" :min="5" :max="120" />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="editing.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEdit = false">取消</el-button>
        <el-button type="primary" @click="savePlugin">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import request from '@/api/request'

const plugins = ref<any[]>([])
const showEdit = ref(false)
const editing = ref<any>({
  name: '', description: '', type: 'http', is_active: true,
  config: { method: 'POST', url: '', headers: {}, body_template: '{{input}}', timeout: 30 },
})

const headersText = computed({
  get: () => JSON.stringify(editing.value.config.headers || {}, null, 2),
  set: (val: string) => {
    try {
      editing.value.config.headers = JSON.parse(val)
    } catch {
      editing.value.config.headers = {}
    }
  },
})

async function load() {
  plugins.value = await request.get('/application/plugins/')
}

function openCreate() {
  editing.value = {
    name: '', description: '', type: 'http', is_active: true,
    config: { method: 'POST', url: '', headers: {}, body_template: '{{input}}', timeout: 30 },
  }
  showEdit.value = true
}

function openEdit(row: any) {
  editing.value = JSON.parse(JSON.stringify(row))
  if (!editing.value.config) {
    editing.value.config = { method: 'POST', url: '', headers: {}, body_template: '{{input}}', timeout: 30 }
  }
  showEdit.value = true
}

async function savePlugin() {
  if (!editing.value.name.trim()) {
    ElMessage.warning('请输入名称')
    return
  }
  if (!editing.value.config.url) {
    ElMessage.warning('请输入请求 URL')
    return
  }
  if (editing.value.id) {
    await request.put(`/application/plugins/${editing.value.id}/`, editing.value)
    ElMessage.success('已更新')
  } else {
    await request.post('/application/plugins/', editing.value)
    ElMessage.success('已创建')
  }
  showEdit.value = false
  load()
}

async function testPlugin(row: any) {
  try {
    const data: any = await request.post(`/application/plugins/${row.id}/test/`, { input_text: 'test' })
    ElMessageBox.alert(data.result || '测试成功（无返回内容）', '测试结果', { type: 'success' })
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '测试失败')
  }
}

async function deletePlugin(row: any) {
  try {
    await ElMessageBox.confirm('确定删除该插件？', '删除', { type: 'warning' })
  } catch {
    return
  }
  await request.delete(`/application/plugins/${row.id}/`)
  ElMessage.success('已删除')
  load()
}

onMounted(load)
</script>

<style scoped>
.bar { display: flex; justify-content: space-between; align-items: center; }
code { background: #f5f7fa; padding: 2px 6px; border-radius: 4px; font-size: 12px; }
</style>
