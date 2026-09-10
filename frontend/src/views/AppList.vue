<template>
  <div>
    <div class="toolbar">
      <el-button type="primary" v-if="canWrite" @click="openDialog()">
        <el-icon><Plus /></el-icon> 新建 AI 应用
      </el-button>
    </div>

    <el-row :gutter="16">
      <el-col v-for="a in list" :key="a.id" :span="8">
        <el-card class="app-card" shadow="hover">
          <div class="app-name">{{ a.name }}</div>
          <div class="app-desc">{{ a.desc || '暂无描述' }}</div>
          <div class="app-meta">
            知识库：{{ a.kb_names.join('、') || '未绑定' }}
          </div>
          <div class="app-actions">
            <el-button link type="primary" @click="openDialog(a)">编辑</el-button>
            <el-button link type="success" @click="goChat(a.id)">对话</el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-dialog v-model="dialog" :title="editing ? '编辑应用' : '新建应用'" width="520px">
      <el-form label-width="90px">
        <el-form-item label="名称"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="form.desc" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="关联知识库">
          <el-select v-model="form.kb_ids" multiple placeholder="选择知识库" style="width:100%">
            <el-option v-for="kb in bases" :key="kb.id" :label="kb.name" :value="kb.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="系统提示词">
          <el-input v-model="form.system_prompt" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="温度">
          <el-slider v-model="form.temperature" :min="0" :max="1" :step="0.1" style="width:100%" />
        </el-form-item>
        <el-form-item label="向量检索权重">
          <el-slider v-model="form.vector_weight" :min="0" :max="1" :step="0.1" style="width:100%" />
          <div class="form-tip">向量检索 {{ Math.round((form.vector_weight || 0) * 100) }}% / 关键词检索 {{ Math.round((1 - (form.vector_weight || 0)) * 100) }}%</div>
        </el-form-item>
        <el-form-item label="最大Token">
          <el-input-number v-model="form.max_tokens" :min="256" :max="4096" :step="256" />
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
import { onMounted, reactive, ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { listApps, createApp, updateApp } from '@/api/chat'
import { listBases } from '@/api/knowledge'
import type { Application, KnowledgeBase } from '@/types'
import { useUserStore } from '@/store/user'

const router = useRouter()
const userStore = useUserStore()
const canWrite = computed(() => ['admin', 'editor'].includes(userStore.role))
const list = ref<Application[]>([])
const bases = ref<KnowledgeBase[]>([])
const dialog = ref(false)
const editing = ref<Application | null>(null)
const saving = ref(false)

const form = reactive<Partial<Application>>({
  name: '', desc: '', kb_ids: [], system_prompt: '',
  temperature: 0.7, vector_weight: 0.7, max_tokens: 1024
})

async function load() {
  list.value = await listApps()
  bases.value = await listBases()
}

function openDialog(app?: Application) {
  editing.value = app || null
  form.name = app?.name || ''
  form.desc = app?.desc || ''
  form.kb_ids = app?.kb_ids || []
  form.system_prompt = app?.system_prompt || ''
  form.temperature = app?.temperature ?? 0.7
  form.vector_weight = app?.vector_weight ?? 0.7
  form.max_tokens = app?.max_tokens ?? 1024
  dialog.value = true
}

async function save() {
  if (!form.name) { ElMessage.warning('请输入名称'); return }
  saving.value = true
  try {
    if (editing.value) await updateApp(editing.value.id, form)
    else await createApp(form)
    dialog.value = false
    await load()
  } finally {
    saving.value = false
  }
}

function goChat(id: number) {
  router.push(`/chat/${id}`)
}

onMounted(load)
</script>

<style scoped>
.toolbar { margin-bottom: 16px; }
.app-card { height: 180px; }
.app-name { font-weight: 600; margin-bottom: 6px; }
.app-desc { color: #6b7280; font-size: 13px; height: 38px; overflow: hidden; }
.app-meta { color: #9ca3af; font-size: 12px; margin: 10px 0; }
.app-actions { text-align: right; }
.form-tip { font-size: 12px; color: #9ca3af; margin-top: 4px; }
</style>
