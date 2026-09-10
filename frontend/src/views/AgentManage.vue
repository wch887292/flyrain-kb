<template>
  <div>
    <div class="toolbar">
      <h3 style="margin:0">智能体管理</h3>
      <el-button type="primary" @click="openCreate">
        <el-icon><Plus /></el-icon> 新建智能体
      </el-button>
    </div>

    <el-table :data="list" border>
      <el-table-column label="智能体" min-width="200">
        <template #default="{ row }">
          <div style="display:flex;align-items:center;gap:10px">
            <el-avatar :size="40" :src="row.avatar">
              {{ row.name.charAt(0) }}
            </el-avatar>
            <div>
              <div style="font-weight:600">{{ row.name }}</div>
              <div style="font-size:12px;color:#9ca3af">{{ row.role || row.description }}</div>
            </div>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="知识库" width="120">
        <template #default="{ row }">
          <el-tag size="small">{{ row.kb_names?.length || 0 }} 个</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="工具" width="100">
        <template #default="{ row }">
          <el-tag size="small" type="warning">{{ row.tool_names?.length || 0 }} 个</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="最大轮次" width="100" align="center">
        <template #default="{ row }">{{ row.max_iterations }}</template>
      </el-table-column>
      <el-table-column label="操作" width="340">
        <template #default="{ row }">
          <el-button link type="primary" @click="goChat(row)">对话</el-button>
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button link type="success" @click="openShare(row)">分享</el-button>
          <el-button link type="warning" @click="openVersions(row)">版本</el-button>
          <el-button link type="danger" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-empty v-if="!list.length" description="暂无智能体，点击右上角新建" />

    <!-- 新建/编辑对话框 -->
    <el-dialog v-model="dialog" :title="editing ? '编辑智能体' : '新建智能体'" width="720px">
      <el-form label-width="110px">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="名称">
              <el-input v-model="form.name" placeholder="智能体名称" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="角色设定">
              <el-input v-model="form.role" placeholder="如：资深产品经理、中医顾问" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" placeholder="智能体简介" />
        </el-form-item>
        <el-form-item label="系统提示词">
          <el-input v-model="form.system_prompt" type="textarea" :rows="5"
            placeholder="定义智能体的行为、回答风格、约束等" />
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="关联知识库">
              <el-select v-model="form.kb_ids" multiple style="width:100%" placeholder="选择知识库">
                <el-option v-for="kb in kbList" :key="kb.id" :label="kb.name" :value="kb.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="可用工具">
              <el-select v-model="form.tool_ids" multiple style="width:100%" placeholder="选择插件工具">
                <el-option v-for="t in toolList" :key="t.id" :label="t.name" :value="t.id" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="MCP 服务器">
              <el-select v-model="form.mcp_server_ids" multiple style="width:100%" placeholder="选择 MCP 服务器">
                <el-option v-for="s in mcpList" :key="s.id" :label="s.name" :value="s.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="子智能体">
              <el-select v-model="form.sub_agent_ids" multiple style="width:100%" placeholder="选择子智能体">
                <el-option v-for="a in agentList.filter(a => a.id !== editing?.id)" :key="a.id" :label="a.name" :value="a.id" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="温度">
              <el-slider v-model="form.temperature" :min="0" :max="2" :step="0.1" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="最大Token">
              <el-input-number v-model="form.max_tokens" :min="256" :max="8192" :step="256" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="最大推理轮次">
              <el-input-number v-model="form.max_iterations" :min="1" :max="10" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="开场白">
          <el-input v-model="form.opening_message" type="textarea" :rows="2" placeholder="用户进入对话时的欢迎语" />
        </el-form-item>
        <el-form-item label="建议问题">
          <el-input v-model="suggestedText" type="textarea" :rows="2"
            placeholder="每行一个建议问题，用户可点击快速提问" />
        </el-form-item>
        <el-form-item label="展示思考过程">
          <el-switch v-model="form.enable_reasoning" />
          <span style="margin-left:8px;font-size:12px;color:#9ca3af">开启后对话中显示智能体的思考和工具调用过程</span>
        </el-form-item>
        <el-form-item label="启用代码执行">
          <el-switch v-model="form.enable_code_interpreter" />
          <span style="margin-left:8px;font-size:12px;color:#9ca3af">开启后智能体可执行 Python 代码进行计算、数据分析和图表生成</span>
        </el-form-item>
        <el-form-item label="自动优化">
          <el-switch v-model="form.enable_auto_optimize" />
          <span style="margin-left:8px;font-size:12px;color:#9ca3af">对话结束后自动评价并生成优化建议</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
    <!-- 分享对话框 -->
    <el-dialog v-model="shareDialog" title="分享智能体" width="480px">
      <div v-if="shareAgent">
        <p>智能体：<strong>{{ shareAgent.name }}</strong></p>
        <el-form label-width="100px">
          <el-form-item label="公开访问">
            <el-switch v-model="isPublic" />
            <span style="margin-left:8px;font-size:12px;color:#9ca3af">开启后任何人可通过链接访问</span>
          </el-form-item>
        </el-form>
        <div v-if="shareUrl" class="share-result">
          <el-alert type="success" :closable="false" title="分享链接已生成" />
          <div class="share-url">{{ shareUrl }}</div>
          <el-button type="primary" size="small" @click="copyUrl">复制链接</el-button>
        </div>
      </div>
      <template #footer>
        <el-button @click="shareDialog = false">关闭</el-button>
        <el-button type="primary" @click="doShare">生成分享链接</el-button>
      </template>
    </el-dialog>
    <!-- 版本管理弹窗 -->
    <el-dialog v-model="versionDialog" :title="`版本管理：${versionAgent?.name || ''}`" width="640px">
      <div class="version-toolbar">
        <el-button type="primary" size="small" @click="publishDialog = true">
          发布新版本
        </el-button>
        <span style="font-size:12px;color:#9ca3af;margin-left:auto">
          当前版本：{{ currentVersion || '未发布' }}
        </span>
      </div>
      <el-table :data="versions" size="small" max-height="400">
        <el-table-column label="版本" width="100">
          <template #default="{ row }">
            <el-tag size="small" :type="row.is_current ? 'success' : 'info'">v{{ row.version }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="name" label="名称" width="140" />
        <el-table-column prop="description" label="说明" show-overflow-tooltip />
        <el-table-column prop="created_by" label="发布者" width="100" />
        <el-table-column prop="create_time" label="发布时间" width="160" />
        <el-table-column label="操作" width="140">
          <template #default="{ row }">
            <el-button v-if="!row.is_current" link type="primary" @click="rollback(row)">回滚</el-button>
            <el-tag v-if="row.is_current" size="small" type="success">当前</el-tag>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!versions.length" description="暂无版本，点击上方发布新版本" :image-size="60" />
    </el-dialog>

    <!-- 发布版本弹窗 -->
    <el-dialog v-model="publishDialog" title="发布新版本" width="480px">
      <el-form label-width="80px">
        <el-form-item label="版本号">
          <el-input v-model="newVersion" placeholder="如：1.0.0" />
        </el-form-item>
        <el-form-item label="名称">
          <el-input v-model="newVersionName" placeholder="版本名称（可选）" />
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="newVersionDesc" type="textarea" :rows="3" placeholder="本次更新说明（可选）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="publishDialog = false">取消</el-button>
        <el-button type="primary" :loading="publishing" @click="doPublish">发布</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { listAgents, createAgent, updateAgent, deleteAgent, type Agent } from '@/api/agent'
import request from '@/api/request'

const router = useRouter()
const list = ref<Agent[]>([])
const kbList = ref<any[]>([])
const toolList = ref<any[]>([])
const mcpList = ref<any[]>([])
const agentList = ref<Agent[]>([])
const dialog = ref(false)
const editing = ref<Agent | null>(null)
const saving = ref(false)
const shareDialog = ref(false)
const shareAgent = ref<Agent | null>(null)
const shareUrl = ref('')
const isPublic = ref(false)

// 版本管理
const versionDialog = ref(false)
const versionAgent = ref<Agent | null>(null)
const versions = ref<any[]>([])
const currentVersion = ref('')
const publishDialog = ref(false)
const newVersion = ref('')
const newVersionName = ref('')
const newVersionDesc = ref('')
const publishing = ref(false)

const form = reactive<Partial<Agent>>({
  name: '', role: '', description: '', system_prompt: '',
  kb_ids: [], tool_ids: [], mcp_server_ids: [], sub_agent_ids: [],
  temperature: 0.7, max_tokens: 2048,
  max_iterations: 5, opening_message: '', suggested_questions: [],
  enable_reasoning: true, enable_code_interpreter: false, enable_auto_optimize: false,
})

const suggestedText = computed({
  get: () => (form.suggested_questions || []).join('\n'),
  set: (v: string) => { form.suggested_questions = v.split('\n').filter(s => s.trim()) }
})

async function load() {
  list.value = await listAgents()
}

async function loadOptions() {
  try { kbList.value = await request.get('/knowledge/') } catch { kbList.value = [] }
  try { toolList.value = await request.get('/plugins/') } catch { toolList.value = [] }
  try { mcpList.value = await request.get('/mcp-servers/') } catch { mcpList.value = [] }
  try { agentList.value = await listAgents() } catch { agentList.value = [] }
}

function openCreate() {
  editing.value = null
  Object.assign(form, {
    name: '', role: '', description: '', system_prompt: '',
    kb_ids: [], tool_ids: [], mcp_server_ids: [], sub_agent_ids: [],
    temperature: 0.7, max_tokens: 2048,
    max_iterations: 5, opening_message: '', suggested_questions: [],
    enable_reasoning: true, enable_code_interpreter: false, enable_auto_optimize: false,
  })
  dialog.value = true
}

function openEdit(row: Agent) {
  editing.value = row
  Object.assign(form, {
    name: row.name, role: row.role, description: row.description,
    system_prompt: row.system_prompt, kb_ids: row.kb_ids || [],
    tool_ids: row.tool_ids || [], mcp_server_ids: row.mcp_server_ids || [],
    sub_agent_ids: row.sub_agent_ids || [],
    temperature: row.temperature, max_tokens: row.max_tokens,
    max_iterations: row.max_iterations, opening_message: row.opening_message,
    suggested_questions: row.suggested_questions || [],
    enable_reasoning: row.enable_reasoning,
    enable_code_interpreter: row.enable_code_interpreter,
    enable_auto_optimize: row.enable_auto_optimize,
  })
  dialog.value = true
}

async function save() {
  if (!form.name) {
    ElMessage.warning('请填写名称')
    return
  }
  saving.value = true
  try {
    if (editing.value) {
      await updateAgent(editing.value.id, form)
      ElMessage.success('已更新')
    } else {
      await createAgent(form)
      ElMessage.success('已创建')
    }
    dialog.value = false
    load()
  } finally {
    saving.value = false
  }
}

async function remove(row: Agent) {
  try {
    await ElMessageBox.confirm(`确定删除智能体「${row.name}」？`, '删除', { type: 'warning' })
  } catch { return }
  await deleteAgent(row.id)
  ElMessage.success('已删除')
  load()
}

function goChat(row: Agent) {
  router.push(`/agent/chat/${row.id}`)
}

function openShare(row: Agent) {
  shareAgent.value = row
  isPublic.value = row.is_public || false
  shareUrl.value = row.share_code ? `${window.location.origin}/agent/share/${row.share_code}` : ''
  shareDialog.value = true
}

async function doShare() {
  if (!shareAgent.value) return
  try {
    const r = await request.post('/agent/share/', {
      agent_id: shareAgent.value.id,
      is_public: isPublic.value,
    })
    shareUrl.value = `${window.location.origin}/agent/share/${r.share_code}`
    ElMessage.success('分享链接已生成')
    load()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '分享失败')
  }
}

function copyUrl() {
  navigator.clipboard.writeText(shareUrl.value)
  ElMessage.success('已复制到剪贴板')
}

// ---- 版本管理 ----
async function openVersions(row: Agent) {
  versionAgent.value = row
  versionDialog.value = true
  try {
    versions.value = await request.get('/agent/versions/', { params: { agent_id: row.id } })
    const current = versions.value.find(v => v.is_current)
    currentVersion.value = current ? `v${current.version}` : ''
  } catch {
    versions.value = []
  }
}

async function doPublish() {
  if (!versionAgent.value || !newVersion.value.trim()) {
    ElMessage.warning('请填写版本号')
    return
  }
  publishing.value = true
  try {
    const r = await request.post('/agent/versions/publish/', {
      agent_id: versionAgent.value.id,
      version: newVersion.value.trim(),
      name: newVersionName.value,
      description: newVersionDesc.value,
    })
    ElMessage.success(r.message || '发布成功')
    publishDialog.value = false
    newVersion.value = ''
    newVersionName.value = ''
    newVersionDesc.value = ''
    openVersions(versionAgent.value)
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '发布失败')
  } finally {
    publishing.value = false
  }
}

async function rollback(row: any) {
  try {
    await ElMessageBox.confirm(`确定回滚到版本 v${row.version}？当前配置将被替换。`, '回滚版本', { type: 'warning' })
  } catch { return }
  try {
    const r = await request.post('/agent/versions/rollback/', { version_id: row.id })
    ElMessage.success(r.message || '回滚成功')
    openVersions(versionAgent.value!)
    load()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '回滚失败')
  }
}

onMounted(() => { load(); loadOptions() })
</script>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.share-result { margin-top: 16px; }
.share-url { background: #f3f4f6; padding: 10px; border-radius: 6px; font-size: 13px; word-break: break-all; margin: 10px 0; }
.version-toolbar { display: flex; align-items: center; margin-bottom: 12px; gap: 12px; }
</style>
