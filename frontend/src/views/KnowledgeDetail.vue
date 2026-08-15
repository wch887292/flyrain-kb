<template>
  <div>
    <div class="bar">
      <el-button @click="$router.push('/knowledge')">返回</el-button>
      <h3 style="margin:0 12px">{{ kbName }}</h3>
      <UploadDoc v-if="canWrite" :kb-id="kbId" @uploaded="loadDocs" />
      <el-input v-model="searchQuery" placeholder="检索本知识库" style="width:260px;margin-left:auto"
        @keyup.enter="doSearch">
        <template #append><el-button @click="doSearch">检索</el-button></template>
      </el-input>
    </div>

    <el-table :data="docs" border style="margin-top:16px">
      <el-table-column prop="name" label="文档名" />
      <el-table-column prop="status" label="状态" width="120">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)">{{ statusText(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="char_count" label="字符数" width="100" />
      <el-table-column prop="error_msg" label="错误信息" show-overflow-tooltip />
      <el-table-column label="操作" width="120">
        <template #default="{ row }">
          <el-button link type="primary" @click="preview(row)">分段预览</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="previewVisible" title="分段预览" width="720px">
      <el-input v-model="highlightQuery" clearable placeholder="高亮关键词（多个以空格分隔）"
        style="margin-bottom:12px">
        <template #prepend>高亮</template>
      </el-input>
      <el-alert v-if="isSearchMode" :title="`检索命中 ${paragraphs.length} 段`"
        type="success" :closable="false" style="margin-bottom:12px" />
      <div v-loading="paraLoading">
        <div v-for="p in paragraphs" :key="p.id" class="para">
          <div class="para-meta">#{{ p.index }} · 来源《{{ p.doc_name }}》· 第{{ p.page_no }}页 · 命中{{ p.hit_count }}</div>
          <div class="para-content" v-html="highlight(p.content)"></div>
        </div>
        <el-empty v-if="!paraLoading && paragraphs.length === 0"
          description="暂无分段（文档可能仍在解析中）" />
        <el-pagination v-if="!isSearchMode && paraTotal > pageSize" layout="prev, pager, next"
          :total="paraTotal" :page-size="pageSize" :current-page="paraPage"
          @current-change="onPageChange" style="margin-top:12px; justify-content:center" />
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { listDocuments, search, getParagraphs } from '@/api/knowledge'
import type { DocumentItem, Paragraph, SearchResult } from '@/types'
import { useUserStore } from '@/store/user'
import UploadDoc from '@/components/UploadDoc.vue'

const route = useRoute()
const kbId = Number(route.params.id)
const userStore = useUserStore()
const canWrite = computed(() => ['admin', 'editor'].includes(userStore.role))

const kbName = ref('')
const docs = ref<DocumentItem[]>([])
const searchQuery = ref('')

const previewVisible = ref(false)
const paragraphs = ref<Paragraph[]>([])
const paraLoading = ref(false)
const paraPage = ref(1)
const paraTotal = ref(0)
const pageSize = 50
const currentDocId = ref<number | null>(null)
const isSearchMode = ref(false)
const highlightQuery = ref('')

async function loadDocs() {
  docs.value = await listDocuments(kbId)
}

async function doSearch() {
  if (!searchQuery.value) return
  const data = await search(kbId, searchQuery.value, 10)
  isSearchMode.value = true
  currentDocId.value = null
  highlightQuery.value = searchQuery.value
  paragraphs.value = data.map((r: SearchResult, i: number) => ({
    id: i, index: i, doc: 0, doc_name: r.doc_name,
    content: r.content, page_no: r.page_no, hit_count: 0,
  }))
  previewVisible.value = true
  ElMessage.success(`检索到 ${data.length} 段`)
}

async function loadParagraphs(page = 1) {
  if (!currentDocId.value) return
  paraLoading.value = true
  try {
    const data = await getParagraphs(currentDocId.value, { page, page_size: pageSize })
    paragraphs.value = data.results
    paraTotal.value = data.count
    paraPage.value = data.page
  } finally {
    paraLoading.value = false
  }
}

function preview(row: DocumentItem) {
  currentDocId.value = row.id
  isSearchMode.value = false
  highlightQuery.value = ''
  previewVisible.value = true
  loadParagraphs(1)
}

/** 转义 HTML，避免文档内容造成 XSS；再做关键词高亮包裹 */
function escapeHtml(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

function highlight(text: string): string {
  const raw = highlightQuery.value.trim()
  const safe = escapeHtml(text)
  if (!raw) return safe
  const terms = raw.replace(/，/g, ' ').replace(/,/g, ' ').split(/\s+/).filter(t => t.length > 1)
  if (terms.length === 0) return safe
  const pattern = terms
    .map(t => t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
    .join('|')
  return safe.replace(new RegExp(`(${pattern})`, 'gi'), '<mark>$1</mark>')
}

function onPageChange(p: number) {
  loadParagraphs(p)
}

function statusType(s: string) {
  return { pending: 'info', parsing: 'warning', success: 'success', fail: 'danger' }[s] || 'info'
}
function statusText(s: string) {
  return { pending: '待处理', parsing: '解析中', success: '成功', fail: '失败' }[s] || s
}

onMounted(loadDocs)
</script>

<style scoped>
.bar { display: flex; align-items: center; gap: 8px; }
.para { border-bottom: 1px solid #eee; padding: 10px 0; }
.para-meta { color: #9ca3af; font-size: 12px; margin-bottom: 4px; }
.para-content { white-space: pre-wrap; line-height: 1.6; }
.para-content :deep(mark) {
  background: #fff3a3; color: inherit; padding: 0 2px; border-radius: 2px;
  font-weight: 600;
}
</style>
