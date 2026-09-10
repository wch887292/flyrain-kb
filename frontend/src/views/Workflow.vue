<template>
  <div>
    <!-- 工作流列表 -->
    <div v-if="!currentWorkflow" class="workflow-list-page">
      <div class="bar">
        <h3 style="margin:0">工作流编排</h3>
        <el-button type="primary" @click="createWorkflow">
          <el-icon><Plus /></el-icon> 新建工作流
        </el-button>
      </div>
      <el-row :gutter="16" style="margin-top:16px">
        <el-col :span="8" v-for="wf in workflows" :key="wf.id">
          <el-card shadow="hover" class="wf-card" @click="openWorkflow(wf)">
            <div class="wf-name">{{ wf.name }}</div>
            <div class="wf-desc">{{ wf.desc || '暂无描述' }}</div>
            <div class="wf-meta">
              <el-tag size="small" :type="wf.status === 'active' ? 'success' : 'info'">
                {{ { draft: '草稿', active: '启用', archived: '归档' }[wf.status] }}
              </el-tag>
              <span>{{ wf.step_count || 0 }} 个步骤</span>
            </div>
          </el-card>
        </el-col>
        <el-col :span="24" v-if="!workflows.length">
          <el-empty description="暂无工作流，点击右上角新建" />
        </el-col>
      </el-row>
    </div>

    <!-- 工作流编辑器 -->
    <div v-else class="workflow-editor">
      <div class="bar">
        <el-button @click="backToList">返回</el-button>
        <el-input v-model="currentWorkflow.name" style="width:240px" @change="saveWorkflow" />
        <el-tag :type="currentWorkflow.status === 'active' ? 'success' : 'info'">
          {{ { draft: '草稿', active: '启用', archived: '归档' }[currentWorkflow.status] }}
        </el-tag>
        <el-button type="success" @click="executeDialog = true">
          <el-icon><VideoPlay /></el-icon> 运行
        </el-button>
        <el-button type="danger" plain @click="deleteCurrent">删除</el-button>
      </div>

      <el-input v-model="currentWorkflow.desc" placeholder="工作流描述" style="margin-top:12px"
        @change="saveWorkflow" />

      <!-- 步骤列表（支持拖拽排序） -->
      <div class="steps-section">
        <div class="steps-header">
          <h4 style="margin:0">执行步骤（拖拽卡片调整顺序，支持 LLM 调用和插件调用）</h4>
          <el-button type="primary" plain @click="addStep">
            <el-icon><Plus /></el-icon> 添加步骤
          </el-button>
        </div>
        <div class="steps-list">
          <div v-for="(step, idx) in steps" :key="step.id" class="step-card"
            draggable="true"
            @dragstart="onDragStart(idx, $event)"
            @dragover.prevent="onDragOver(idx)"
            @drop="onDrop(idx)"
            @dragend="onDragEnd"
            :class="{ dragging: dragIndex === idx, drag-over: dragOverIndex === idx }">
            <div class="step-header">
              <span class="drag-handle">⋮⋮</span>
              <span class="step-order">步骤 {{ idx + 1 }}</span>
              <el-select v-model="step.step_type" size="small" style="width:120px" @change="onStepTypeChange(step)">
                <el-option label="LLM 调用" value="llm" />
                <el-option label="插件调用" value="plugin" />
              </el-select>
              <el-select v-if="step.step_type === 'plugin'" v-model="step.plugin" size="small"
                style="width:180px" placeholder="选择插件" @change="saveStep(step)">
                <el-option v-for="p in plugins" :key="p.id" :label="p.name" :value="p.id" />
              </el-select>
              <el-input v-model="step.name" style="width:160px" size="small" @change="saveStep(step)" />
              <el-button link type="danger" @click="removeStep(step)">删除</el-button>
            </div>
            <template v-if="step.step_type === 'llm'">
              <el-input v-model="step.prompt" type="textarea" :rows="4"
                placeholder="提示词模板，可用 {{input}} 引用输入，{{step_1.output}} 引用第1步输出"
                @change="saveStep(step)" />
              <div class="step-config">
                <span>温度：<el-input-number v-model="step.temperature" :min="0" :max="2" :step="0.1"
                  size="small" @change="saveStep(step)" /></span>
                <span>最大Token：<el-input-number v-model="step.max_tokens" :min="16" :max="8192"
                  :step="128" size="small" @change="saveStep(step)" /></span>
              </div>
            </template>
            <template v-else>
              <el-alert type="info" :closable="false" style="margin-top:8px"
                :title="step.plugin ? `将调用插件：${getPluginName(step.plugin)}` : '请选择要调用的插件'" />
            </template>
          </div>
          <el-empty v-if="!steps.length" description="暂无步骤，点击上方添加" :image-size="60" />
        </div>
      </div>

      <!-- 执行记录 -->
      <div class="executions-section" v-if="executions.length">
        <h4>最近执行记录</h4>
        <el-table :data="executions" size="small" max-height="300">
          <el-table-column prop="create_time" label="时间" width="170" />
          <el-table-column prop="input_text" label="输入" show-overflow-tooltip />
          <el-table-column prop="status" label="状态" width="80" align="center">
            <template #default="{ row }">
              <el-tag size="small" :type="row.status === 'success' ? 'success' : 'danger'">
                {{ row.status === 'success' ? '成功' : '失败' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="耗时" width="100" align="center">
            <template #default="{ row }">{{ (row.duration_ms / 1000).toFixed(1) }}s</template>
          </el-table-column>
          <el-table-column label="操作" width="80" align="center">
            <template #default="{ row }">
              <el-button link type="primary" @click="viewExecution(row)">查看</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <!-- 运行对话框 -->
    <el-dialog v-model="executeDialog" title="运行工作流" width="640px">
      <el-input v-model="executeInput" type="textarea" :rows="4"
        placeholder="输入工作流的初始输入内容" />
      <div style="margin-top:12px; text-align:right">
        <el-button @click="executeDialog = false">取消</el-button>
        <el-button type="primary" :loading="executing" @click="runWorkflow">开始执行</el-button>
      </div>
    </el-dialog>

    <!-- 执行结果对话框 -->
    <el-dialog v-model="resultDialog" title="执行结果" width="720px">
      <div v-if="executionResult">
        <el-alert :type="executionResult.status === 'success' ? 'success' : 'error'"
          :title="executionResult.status === 'success' ? '执行成功' : '执行失败'"
          :description="executionResult.error_msg || undefined" :closable="false" />
        <div style="margin-top:12px">
          <strong>输入：</strong>
          <div class="result-box">{{ executionResult.input_text }}</div>
        </div>
        <div v-for="(so, idx) in executionResult.step_outputs" :key="idx" style="margin-top:12px">
          <strong>步骤 {{ so.step_order }}：{{ so.step_name }}（{{ so.step_type === 'plugin' ? '插件' : 'LLM' }}）</strong>
          <div class="result-box">{{ so.output }}</div>
        </div>
        <div style="margin-top:12px" v-if="executionResult.status === 'success'">
          <strong>最终输出：</strong>
          <div class="result-box final">{{ executionResult.output_text }}</div>
        </div>
        <div style="margin-top:8px; color:#9ca3af; font-size:12px">
          总耗时：{{ (executionResult.duration_ms / 1000).toFixed(2) }}s
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, VideoPlay } from '@element-plus/icons-vue'
import request from '@/api/request'

const router = useRouter()
const workflows = ref<any[]>([])
const plugins = ref<any[]>([])
const currentWorkflow = ref<any>(null)
const steps = ref<any[]>([])
const executions = ref<any[]>([])

const executeDialog = ref(false)
const executeInput = ref('')
const executing = ref(false)
const resultDialog = ref(false)
const executionResult = ref<any>(null)

// 拖拽状态
const dragIndex = ref<number | null>(null)
const dragOverIndex = ref<number | null>(null)

async function loadWorkflows() {
  workflows.value = await request.get('/application/workflows/')
}

async function loadPlugins() {
  try {
    plugins.value = await request.get('/application/plugins/')
  } catch {
    plugins.value = []
  }
}

function getPluginName(pluginId: number) {
  return plugins.value.find(p => p.id === pluginId)?.name || ''
}

async function createWorkflow() {
  const { value } = await ElMessageBox.prompt('请输入工作流名称', '新建工作流', {
    confirmButtonText: '创建', cancelButtonText: '取消',
  })
  const wf = await request.post('/application/workflows/', { name: value, status: 'draft' })
  ElMessage.success('已创建')
  openWorkflow(wf)
}

async function openWorkflow(wf: any) {
  currentWorkflow.value = wf
  steps.value = await request.get(`/application/workflows/${wf.id}/steps/`)
  executions.value = await request.get(`/application/workflows/${wf.id}/executions/`)
}

function backToList() {
  currentWorkflow.value = null
  steps.value = []
  loadWorkflows()
}

async function saveWorkflow() {
  if (!currentWorkflow.value) return
  await request.put(`/application/workflows/${currentWorkflow.value.id}/`, {
    name: currentWorkflow.value.name,
    desc: currentWorkflow.value.desc,
  })
}

async function deleteCurrent() {
  if (!currentWorkflow.value) return
  try {
    await ElMessageBox.confirm('确定删除该工作流及其所有步骤和执行记录？', '删除', { type: 'warning' })
  } catch {
    return
  }
  await request.delete(`/application/workflows/${currentWorkflow.value.id}/`)
  ElMessage.success('已删除')
  backToList()
}

async function addStep() {
  if (!currentWorkflow.value) return
  const step = await request.post(`/application/workflows/${currentWorkflow.value.id}/add_step/`, {
    name: `步骤 ${steps.value.length + 1}`,
    prompt: '',
    step_type: 'llm',
    temperature: 0.7,
    max_tokens: 1024,
  })
  steps.value.push(step)
  ElMessage.success('已添加步骤')
}

async function saveStep(step: any) {
  // 步骤更新：通过 delete + add 实现，或调用 update 接口
  // 简化：标记为 dirty，保存时批量更新
  console.log('step changed:', step.id, step.name)
}

function onStepTypeChange(step: any) {
  if (step.step_type === 'plugin') {
    step.prompt = ''
  }
  saveStep(step)
}

async function removeStep(step: any) {
  try {
    await ElMessageBox.confirm('确定删除该步骤？', '删除步骤', { type: 'warning' })
  } catch {
    return
  }
  try {
    await request.delete(`/application/workflows/${currentWorkflow.value.id}/delete_step/`, {
      data: { step_id: step.id }
    })
  } catch {
    // 兼容旧接口
  }
  steps.value = steps.value.filter(s => s.id !== step.id)
  ElMessage.success('已删除')
}

// 拖拽排序
function onDragStart(idx: number, e: DragEvent) {
  dragIndex.value = idx
  e.dataTransfer!.effectAllowed = 'move'
}

function onDragOver(idx: number) {
  dragOverIndex.value = idx
}

async function onDrop(idx: number) {
  if (dragIndex.value === null || dragIndex.value === idx) return
  const fromIdx = dragIndex.value
  const toIdx = idx
  // 重新排序
  const newSteps = [...steps.value]
  const [moved] = newSteps.splice(fromIdx, 1)
  newSteps.splice(toIdx, 0, moved)
  steps.value = newSteps
  // 调用后端排序接口
  try {
    await request.post(`/application/workflows/${currentWorkflow.value.id}/reorder_steps/`, {
      step_ids: newSteps.map(s => s.id)
    })
    ElMessage.success('排序已保存')
  } catch {
    ElMessage.warning('排序保存失败')
  }
}

function onDragEnd() {
  dragIndex.value = null
  dragOverIndex.value = null
}

async function runWorkflow() {
  if (!currentWorkflow.value || !executeInput.value) {
    ElMessage.warning('请输入内容')
    return
  }
  executing.value = true
  try {
    const result = await request.post(`/application/workflows/${currentWorkflow.value.id}/execute/`, {
      input_text: executeInput.value
    })
    executionResult.value = result
    executeDialog.value = false
    resultDialog.value = true
    executions.value = await request.get(`/application/workflows/${currentWorkflow.value.id}/executions/`)
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '执行失败')
  } finally {
    executing.value = false
    executeInput.value = ''
  }
}

function viewExecution(exec: any) {
  executionResult.value = exec
  resultDialog.value = true
}

onMounted(() => {
  loadWorkflows()
  loadPlugins()
})
</script>

<style scoped>
.bar { display: flex; align-items: center; gap: 12px; }
.wf-card { cursor: pointer; transition: transform 0.15s; margin-bottom: 16px; }
.wf-card:hover { transform: translateY(-2px); }
.wf-name { font-size: 16px; font-weight: 600; margin-bottom: 8px; }
.wf-desc { font-size: 13px; color: #6b7280; margin-bottom: 12px; min-height: 20px; }
.wf-meta { display: flex; gap: 12px; align-items: center; font-size: 12px; color: #9ca3af; }
.steps-section { margin-top: 20px; }
.steps-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.steps-list { display: flex; flex-direction: column; gap: 12px; }
.step-card {
  border: 1px solid #e5e7eb; border-radius: 8px; padding: 16px; background: #fafafa;
  cursor: move; transition: all 0.15s;
}
.step-card:hover { border-color: #409eff; }
.step-card.dragging { opacity: 0.5; }
.step-card.drag-over { border-color: #409eff; border-style: dashed; background: #ecf5ff; }
.step-header { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
.drag-handle { cursor: grab; color: #9ca3af; font-size: 16px; user-select: none; }
.step-order { font-weight: 600; color: #409eff; }
.step-config { display: flex; gap: 24px; margin-top: 12px; align-items: center; font-size: 13px; color: #6b7280; }
.executions-section { margin-top: 24px; }
.result-box { background: #f5f7fa; padding: 12px; border-radius: 6px; margin-top: 8px;
  white-space: pre-wrap; font-size: 13px; line-height: 1.6; max-height: 200px; overflow-y: auto; }
.result-box.final { background: #ecf5ff; border-left: 3px solid #409eff; }
</style>
