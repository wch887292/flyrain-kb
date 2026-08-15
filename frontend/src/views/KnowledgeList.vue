<template>
  <div>
    <div class="toolbar">
      <el-button type="primary" v-if="canWrite" @click="dialog = true">
        <el-icon><FolderAdd /></el-icon> 新建知识库
      </el-button>
    </div>

    <el-row :gutter="16">
      <el-col v-for="kb in list" :key="kb.id" :span="6">
        <el-card class="kb-card" shadow="hover" @click="open(kb.id)">
          <div class="kb-name">{{ kb.name }}</div>
          <div class="kb-desc">{{ kb.desc || '暂无描述' }}</div>
          <div class="kb-meta">文档数：{{ kb.doc_count }}</div>
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
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { listBases, createBase } from '@/api/knowledge'
import type { KnowledgeBase } from '@/types'
import { useUserStore } from '@/store/user'

const router = useRouter()
const userStore = useUserStore()
const canWrite = computed(() => ['admin', 'editor'].includes(userStore.role))
const list = ref<KnowledgeBase[]>([])
const dialog = ref(false)
const saving = ref(false)
const form = reactive({ name: '', desc: '' })

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
</script>

<style scoped>
.toolbar { margin-bottom: 16px; }
.kb-card { cursor: pointer; height: 140px; }
.kb-name { font-weight: 600; font-size: 15px; margin-bottom: 8px; }
.kb-desc { color: #6b7280; font-size: 13px; height: 40px; overflow: hidden; }
.kb-meta { margin-top: 12px; color: #9ca3af; font-size: 12px; }
</style>
