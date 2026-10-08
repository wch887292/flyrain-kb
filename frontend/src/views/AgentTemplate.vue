<template>
  <div>
    <div class="toolbar">
      <h3 style="margin:0">智能体模板市场</h3>
      <div class="filter">
        <el-radio-group v-model="activeCategory" size="small" @change="filterTemplates">
          <el-radio-button label="">全部</el-radio-button>
          <el-radio-button v-for="c in categories" :key="c" :label="c">{{ c }}</el-radio-button>
        </el-radio-group>
      </div>
    </div>

    <div class="template-grid">
      <div v-for="t in filteredTemplates" :key="t.id" class="template-card">
        <div class="card-header">
          <div class="card-icon">{{ t.icon }}</div>
          <div class="card-title">
            <div class="name">{{ t.name }}</div>
            <el-tag size="small" type="info">{{ t.category }}</el-tag>
          </div>
        </div>
        <div class="card-desc">{{ t.description }}</div>
        <div class="card-meta">
          <el-tag v-if="t.enable_code_interpreter" size="small" type="success">代码执行</el-tag>
          <el-tag v-if="t.enable_fhcode" size="small" type="primary">飞虹Code引擎</el-tag>
          <el-tag v-if="t.enable_reasoning" size="small" type="warning">思考过程</el-tag>
          <span class="iterations">最大 {{ t.max_iterations }} 轮</span>
        </div>
        <div class="card-footer">
          <el-button size="small" type="primary" @click="createFromTemplate(t)">
            使用模板创建
          </el-button>
          <el-button size="small" @click="previewTemplate(t)">查看详情</el-button>
        </div>
      </div>
    </div>

    <el-empty v-if="!filteredTemplates.length" description="该分类下暂无模板" />

    <!-- 创建对话框 -->
    <el-dialog v-model="createDialog" title="基于模板创建智能体" width="480px">
      <el-form label-width="80px">
        <el-form-item label="模板">
          <el-tag>{{ selectedTemplate?.name }}</el-tag>
        </el-form-item>
        <el-form-item label="名称">
          <el-input v-model="customName" placeholder="自定义智能体名称（可选）" />
        </el-form-item>
        <el-form-item label="关联知识库" v-if="kbList.length">
          <el-select v-model="selectedKbs" multiple style="width:100%" placeholder="选择知识库（可选）">
            <el-option v-for="kb in kbList" :key="kb.id" :label="kb.name" :value="kb.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialog = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="confirmCreate">创建</el-button>
      </template>
    </el-dialog>

    <!-- 详情对话框 -->
    <el-dialog v-model="detailDialog" :title="selectedTemplate?.name" width="600px">
      <div v-if="selectedTemplate" class="detail">
        <div class="detail-row">
          <span class="label">角色：</span>
          <span>{{ selectedTemplate.role }}</span>
        </div>
        <div class="detail-row">
          <span class="label">描述：</span>
          <span>{{ selectedTemplate.description }}</span>
        </div>
        <div class="detail-row">
          <span class="label">系统提示词：</span>
        </div>
        <pre class="detail-prompt">{{ selectedTemplate.system_prompt }}</pre>
        <div class="detail-row">
          <span class="label">开场白：</span>
          <span>{{ selectedTemplate.opening_message }}</span>
        </div>
        <div class="detail-row">
          <span class="label">建议问题：</span>
        </div>
        <ul class="detail-questions">
          <li v-for="q in selectedTemplate.suggested_questions" :key="q">{{ q }}</li>
        </ul>
        <div class="detail-row">
          <span class="label">能力：</span>
          <el-tag v-if="selectedTemplate.enable_code_interpreter" size="small" type="success" style="margin-right:4px">代码执行</el-tag>
          <el-tag v-if="selectedTemplate.enable_fhcode" size="small" type="primary" style="margin-right:4px">飞虹Code引擎</el-tag>
          <el-tag v-if="selectedTemplate.enable_reasoning" size="small" type="warning">思考过程</el-tag>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import request from '@/api/request'

const router = useRouter()
const categories = ref<string[]>([])
const templates = ref<any[]>([])
const activeCategory = ref('')
const createDialog = ref(false)
const detailDialog = ref(false)
const selectedTemplate = ref<any>(null)
const customName = ref('')
const selectedKbs = ref<number[]>([])
const kbList = ref<any[]>([])
const creating = ref(false)

const filteredTemplates = computed(() => {
  if (!activeCategory.value) return templates.value
  return templates.value.filter(t => t.category === activeCategory.value)
})

async function load() {
  try {
    const data = await request.get('/agent/templates/')
    categories.value = data.categories || []
    templates.value = data.templates || []
  } catch {
    templates.value = []
  }
  try {
    kbList.value = await request.get('/knowledge/')
  } catch {
    kbList.value = []
  }
}

function filterTemplates() {
  // computed 自动处理
}

function createFromTemplate(t: any) {
  selectedTemplate.value = t
  customName.value = ''
  selectedKbs.value = []
  createDialog.value = true
}

function previewTemplate(t: any) {
  selectedTemplate.value = t
  detailDialog.value = true
}

async function confirmCreate() {
  if (!selectedTemplate.value) return
  creating.value = true
  try {
    const result = await request.post('/agent/templates/create/', {
      template_id: selectedTemplate.value.id,
      name: customName.value || undefined,
      kb_ids: selectedKbs.value,
    })
    ElMessage.success(result.message || '创建成功')
    createDialog.value = false
    router.push(`/agent/chat/${result.id}`)
  } finally {
    creating.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.filter { }
.template-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px; }
.template-card { background: #fff; border: 1px solid #e5e7eb; border-radius: 10px; padding: 16px; transition: all 0.2s; display: flex; flex-direction: column; }
.template-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.1); transform: translateY(-2px); border-color: #3b82f6; }
.card-header { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
.card-icon { font-size: 32px; width: 48px; height: 48px; display: flex; align-items: center; justify-content: center; background: #f3f4f6; border-radius: 10px; }
.card-title { flex: 1; }
.name { font-size: 16px; font-weight: 600; margin-bottom: 4px; }
.card-desc { font-size: 13px; color: #6b7280; line-height: 1.5; margin-bottom: 12px; flex: 1; }
.card-meta { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; }
.iterations { font-size: 12px; color: #9ca3af; margin-left: auto; }
.card-footer { display: flex; gap: 8px; }
.card-footer .el-button { flex: 1; }

.detail { }
.detail-row { margin-bottom: 10px; font-size: 14px; }
.detail-row .label { font-weight: 600; color: #374151; }
.detail-prompt { background: #f9fafb; padding: 12px; border-radius: 6px; font-size: 13px; white-space: pre-wrap; max-height: 200px; overflow-y: auto; margin-bottom: 10px; }
.detail-questions { margin: 0 0 10px 0; padding-left: 20px; }
.detail-questions li { font-size: 13px; color: #6b7280; margin-bottom: 4px; }
</style>
