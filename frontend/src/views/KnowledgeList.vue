<template>
  <div>
    <div class="toolbar">
      <el-button type="primary" v-if="canWrite" @click="dialog = true">
        <el-icon><FolderAdd /></el-icon> 新建知识库
      </el-button>
      <el-button v-if="canWrite" @click="importDialog = true">
        <el-icon><Upload /></el-icon> 导入知识库
      </el-button>
    </div>

    <el-row :gutter="16">
      <el-col v-for="kb in list" :key="kb.id" :span="6">
        <el-card class="kb-card" shadow="hover">
          <div class="kb-card-body" @click="open(kb.id)">
            <div class="kb-name">{{ kb.name }}</div>
            <div class="kb-desc">{{ kb.desc || '暂无描述' }}</div>
            <div class="kb-meta">文档数：{{ kb.doc_count }}</div>
          </div>
          <div class="kb-actions">
            <el-button link type="primary" @click.stop="exportKb(kb)">
              <el-icon><Download /></el-icon> 导出
            </el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-dialog v-model="dialog" title="新建知识库" width="420px">
      <el-form label-width="80px">
        <el-form-item label="名称">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.desc" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">确定</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="importDialog" title="导入知识库" width="520px">
      <el-alert type="info" :closable="false" style="margin-bottom:12px"
        title="导入 JSON 格式的知识库配置文件，文档记录将被创建但需重新上传文件后解析。" />
      <el-upload
        drag
        :auto-upload="false"
        :on-change="onImportFileChange"
        accept=".json"
        :limit="1">
        <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
        <div class="el-upload__text">将 JSON 文件拖到此处，或<em>点击上传</em></div>
      </el-upload>
      <div v-if="importPreview" class="import-preview">
        <div>知识库：{{ importPreview.knowledge_base?.name }}</div>
        <div>文档数：{{ importPreview.documents?.length || 0 }}</div>
      </div>
      <template #footer>
        <el-button @click="importDialog = false">取消</el-button>
        <el-button type="primary" :loading="importing" :disabled="!importPreview"
          @click="doImport">确认导入</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import { listBases, createBase, exportKnowledgeBase, importKnowledgeBase } from '@/api/knowledge'
import type { KnowledgeBase } from '@/types'
import { useUserStore } from '@/store/user'

const router = useRouter()
const userStore = useUserStore()
const canWrite = computed(() => ['admin', 'editor'].includes(userStore.role))
const list = ref<KnowledgeBase[]>([])
const dialog = ref(false)
const saving = ref(false)
const form = reactive({ name: '', desc: '' })

const importDialog = ref(false)
const importing = ref(false)
const importPreview = ref<any>(null)
const importFile = ref<File | null>(null)

async function load() {
  list.value = await listBases()
}

function open(id: number) {
  router.push(`/knowledge/${id}`)
}

async function save() {
  if (!form.name) {
    ElMessage.warning('请输入名称')
    return
  }
  saving.value = true
  try {
    await createBase({ name: form.name, desc: form.desc })
    dialog.value = false
    form.name = ''
    form.desc = ''
    await load()
  } finally {
    saving.value = false
  }
}

onMounted(load)

async function exportKb(kb: KnowledgeBase) {
  try {
    const blob = await exportKnowledgeBase(kb.id)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `kb_${kb.id}_${kb.name}.json`
    a.click()
    URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch {
    /* 错误已由拦截器提示 */
  }
}

function onImportFileChange(file: any) {
  importFile.value = file.raw
  const reader = new FileReader()
  reader.onload = (e) => {
    try {
      importPreview.value = JSON.parse(e.target?.result as string)
    } catch {
      ElMessage.error('JSON 格式错误')
      importPreview.value = null
    }
  }
  reader.readAsText(file.raw)
}

async function doImport() {
  if (!importPreview.value) return
  importing.value = true
  try {
    const data = importPreview.value
    await importKnowledgeBase({
      name: data.knowledge_base?.name || '导入的知识库',
      desc: data.knowledge_base?.desc || '',
      documents: data.documents || [],
    })
    importDialog.value = false
    importPreview.value = null
    importFile.value = null
    ElMessage.success('导入成功')
    await load()
  } finally {
    importing.value = false
  }
}
</script>

<style scoped>
.toolbar { margin-bottom: 16px; }
.kb-card { cursor: pointer; height: 160px; display: flex; flex-direction: column; }
.kb-card-body { flex: 1; }
.kb-name { font-weight: 600; font-size: 15px; margin-bottom: 8px; }
.kb-desc { color: #6b7280; font-size: 13px; height: 40px; overflow: hidden; }
.kb-meta { margin-top: 12px; color: #9ca3af; font-size: 12px; }
.kb-actions { border-top: 1px solid #f0f0f0; padding-top: 8px; text-align: right; }
.import-preview { margin-top: 12px; padding: 8px 12px; background: #f5f7fa; border-radius: 4px; font-size: 13px; color: #6b7280; }
</style>
