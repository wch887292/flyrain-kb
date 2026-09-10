<template>
  <div>
    <div class="toolbar">
      <h3 style="margin:0">MCP 服务器管理</h3>
      <el-button type="primary" @click="openCreate">
        <el-icon><Plus /></el-icon> 添加 MCP 服务器
      </el-button>
    </div>

    <el-tabs v-model="activeTab">
      <el-tab-pane label="我的服务器" name="servers">
        <el-table :data="list" border>
          <el-table-column prop="name" label="名称" width="160" />
          <el-table-column prop="transport" label="传输方式" width="100">
            <template #default="{ row }">
              <el-tag size="small">{{ row.transport === 'http' ? 'HTTP/SSE' : 'stdio' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="url" label="地址" show-overflow-tooltip />
          <el-table-column label="工具数" width="80" align="center">
            <template #default="{ row }">{{ row.tools_cache?.length || 0 }}</template>
          </el-table-column>
          <el-table-column label="状态" width="80">
            <template #default="{ row }">
              <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
                {{ row.is_active ? '启用' : '禁用' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="240">
            <template #default="{ row }">
              <el-button link type="primary" @click="testConnection(row)">测试</el-button>
              <el-button link type="warning" @click="refreshTools(row)">刷新工具</el-button>
              <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
              <el-button link type="danger" @click="remove(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-if="!list.length" description="暂无 MCP 服务器，点击右上角添加或从市场选择" />
      </el-tab-pane>

      <el-tab-pane label="工具市场" name="market">
        <div class="market-filter">
          <el-radio-group v-model="marketCategory" size="small" @change="filterMarket">
            <el-radio-button label="">全部</el-radio-button>
            <el-radio-button v-for="c in marketCategories" :key="c" :label="c">{{ c }}</el-radio-button>
          </el-radio-group>
        </div>
        <div class="template-grid">
          <div v-for="t in filteredMarket" :key="t.id" class="template-card">
            <div class="card-header">
              <div class="card-icon">{{ t.icon }}</div>
              <div class="card-title">
                <div class="name">{{ t.name }}</div>
                <el-tag size="small" type="info">{{ t.category }}</el-tag>
              </div>
            </div>
            <div class="card-desc">{{ t.description }}</div>
            <div class="card-meta">
              <el-tag size="small">{{ t.transport === 'http' ? 'HTTP/SSE' : 'stdio' }}</el-tag>
            </div>
            <div class="card-footer">
              <el-button type="primary" size="small" @click="addFromTemplate(t)">
                一键添加
              </el-button>
            </div>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="dialog" :title="editing ? '编辑 MCP 服务器' : '添加 MCP 服务器'" width="560px">
      <el-form label-width="100px">
        <el-form-item label="名称">
          <el-input v-model="form.name" placeholder="服务器名称" />
        </el-form-item>
        <el-form-item label="传输方式">
          <el-radio-group v-model="form.transport">
            <el-radio value="http">HTTP/SSE</el-radio>
            <el-radio value="stdio">标准输入输出</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="服务器地址" v-if="form.transport === 'http'">
          <el-input v-model="form.url" placeholder="https://mcp.example.com" />
        </el-form-item>
        <el-form-item label="启动命令" v-if="form.transport === 'stdio'">
          <el-input v-model="form.command" placeholder="npx @modelcontextprotocol/server-filesystem" />
        </el-form-item>
        <el-form-item label="请求头" v-if="form.transport === 'http'">
          <el-input v-model="headersText" type="textarea" :rows="3"
            placeholder='{"Authorization": "Bearer xxx"}' />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="form.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import request from '@/api/request'

const list = ref<any[]>([])
const dialog = ref(false)
const editing = ref<any>(null)
const saving = ref(false)
const activeTab = ref('servers')

const marketTemplates = ref<any[]>([])
const marketCategories = ref<string[]>([])
const marketCategory = ref('')

const form = ref<any>({
  name: '', transport: 'http', url: '', command: '',
  headers: {}, is_active: true,
})

const headersText = computed({
  get: () => JSON.stringify(form.value.headers || {}, null, 2),
  set: (v: string) => {
    try { form.value.headers = JSON.parse(v) } catch { form.value.headers = {} }
  }
})

const filteredMarket = computed(() => {
  if (!marketCategory.value) return marketTemplates.value
  return marketTemplates.value.filter(t => t.category === marketCategory.value)
})

async function load() {
  list.value = await request.get('/mcp-servers/')
}

async function loadMarket() {
  try {
    const data = await request.get('/mcp-market/templates/')
    marketCategories.value = data.categories || []
    marketTemplates.value = data.templates || []
  } catch {
    marketTemplates.value = []
  }
}

function filterMarket() { }

function openCreate() {
  editing.value = null
  form.value = { name: '', transport: 'http', url: '', command: '', headers: {}, is_active: true }
  dialog.value = true
}

function openEdit(row: any) {
  editing.value = row
  form.value = { ...row }
  dialog.value = true
}

async function save() {
  if (!form.value.name) {
    ElMessage.warning('请填写名称')
    return
  }
  saving.value = true
  try {
    if (editing.value) {
      await request.put(`/mcp-servers/${editing.value.id}/`, form.value)
      ElMessage.success('已更新')
    } else {
      await request.post('/mcp-servers/', form.value)
      ElMessage.success('已添加')
    }
    dialog.value = false
    load()
  } finally {
    saving.value = false
  }
}

async function testConnection(row: any) {
  try {
    const r = await request.post(`/mcp-servers/${row.id}/test_connection/`)
    ElMessage.success(`连接成功，发现 ${r.tools_count} 个工具`)
    load()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '连接失败')
  }
}

async function refreshTools(row: any) {
  try {
    const r = await request.post(`/mcp-servers/${row.id}/refresh_tools/`)
    ElMessage.success(`已刷新，共 ${r.count} 个工具`)
    load()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '刷新失败')
  }
}

async function remove(row: any) {
  await request.delete(`/mcp-servers/${row.id}/`)
  ElMessage.success('已删除')
  load()
}

async function addFromTemplate(t: any) {
  try {
    const r = await request.post('/mcp-market/add/', { template_id: t.id })
    ElMessage.success(r.message || '已添加')
    activeTab.value = 'servers'
    load()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '添加失败')
  }
}

onMounted(() => { load(); loadMarket() })
</script>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.market-filter { margin-bottom: 16px; }
.template-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; }
.template-card { background: #fff; border: 1px solid #e5e7eb; border-radius: 10px; padding: 16px; transition: all 0.2s; display: flex; flex-direction: column; }
.template-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.1); transform: translateY(-2px); border-color: #3b82f6; }
.card-header { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
.card-icon { font-size: 28px; width: 44px; height: 44px; display: flex; align-items: center; justify-content: center; background: #f3f4f6; border-radius: 10px; }
.card-title { flex: 1; }
.name { font-size: 15px; font-weight: 600; margin-bottom: 4px; }
.card-desc { font-size: 13px; color: #6b7280; line-height: 1.5; margin-bottom: 12px; flex: 1; }
.card-meta { margin-bottom: 12px; }
.card-footer { }
</style>
