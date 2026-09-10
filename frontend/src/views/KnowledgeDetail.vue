<template>
  <div>
    <div class="bar">
      <el-button @click="$router.push('/knowledge')">返回</el-button>
      <h3 style="margin:0 12px">{{ kbName }}</h3>
      <UploadDoc v-if="canWrite" :kb-id="kbId" @uploaded="loadDocs" />
      <el-button v-if="isAdmin" @click="openPermDialog">
        <el-icon><Lock /></el-icon> 权限管理
      </el-button>
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
      <el-table-column label="版本" width="80" align="center">
        <template #default="{ row }">
          <el-tag size="small" type="info">v{{ row.current_version || 1 }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="char_count" label="字符数" width="100" />
      <el-table-column prop="error_msg" label="错误信息" show-overflow-tooltip />
      <el-table-column label="操作" width="320">
        <template #default="{ row }">
          <el-button link type="primary" @click="preview(row)">分段预览</el-button>
          <el-button v-if="canWrite && row.status !== 'parsing'" link type="warning"
            @click="reparse(row)">重新解析</el-button>
          <el-button v-if="canWrite" link type="info" @click="openDocPermDialog(row)">权限</el-button>
          <el-button link type="success" @click="openVersionDialog(row)">版本</el-button>
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

    <el-dialog v-model="permDialog" title="知识库权限管理" width="520px">
      <el-alert type="info" :closable="false" style="margin-bottom:12px"
        :title="permUsers.length ? '已授权用户可访问本知识库' : '当前为公开知识库，所有用户均可访问'" />
      <div class="perm-toolbar">
        <el-select v-model="permSelectedUser" placeholder="选择用户授权" style="width:200px"
          @change="grantUser">
          <el-option v-for="u in allUsers.filter(u => !permUsers.find(p => p.id === u.id))"
            :key="u.id" :label="u.nickname || u.username" :value="u.id" />
        </el-select>
        <el-button v-if="permUsers.length" type="warning" plain @click="setPublic">
          设为公开（清空授权）
        </el-button>
      </div>
      <el-table :data="permUsers" size="small" style="margin-top:12px" max-height="300">
        <el-table-column prop="username" label="用户名" />
        <el-table-column prop="nickname" label="昵称" />
        <el-table-column prop="role" label="角色" width="100">
          <template #default="{ row }">
            <el-tag size="small">{{ { admin: '管理员', editor: '维护', user: '用户' }[row.role] || row.role }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="80" align="center">
          <template #default="{ row }">
            <el-button link type="danger" @click="revokeUser(row.id)">移除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!permUsers.length" description="暂无授权用户（公开状态）" :image-size="60" />
    </el-dialog>

    <el-dialog v-model="docPermDialog" :title="`文档权限：${currentDoc?.name || ''}`" width="520px">
      <el-alert type="info" :closable="false" style="margin-bottom:12px"
        :title="docPermUsers.length ? '已授权用户可访问本文档（覆盖知识库权限）' : '未设置文档级授权，继承知识库权限'" />
      <div class="perm-toolbar">
        <el-select v-model="docPermSelectedUser" placeholder="选择用户授权" style="width:200px"
          @change="grantDocUser">
          <el-option v-for="u in allUsers.filter(u => !docPermUsers.find(p => p.id === u.id))"
            :key="u.id" :label="u.nickname || u.username" :value="u.id" />
        </el-select>
        <el-button v-if="docPermUsers.length" type="warning" plain @click="inheritKb">
          恢复继承知识库权限
        </el-button>
      </div>
      <el-table :data="docPermUsers" size="small" style="margin-top:12px" max-height="300">
        <el-table-column prop="username" label="用户名" />
        <el-table-column prop="nickname" label="昵称" />
        <el-table-column prop="role" label="角色" width="100">
          <template #default="{ row }">
            <el-tag size="small">{{ { admin: '管理员', editor: '维护', user: '用户' }[row.role] || row.role }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="80" align="center">
          <template #default="{ row }">
            <el-button link type="danger" @click="revokeDocUser(row.id)">移除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!docPermUsers.length" description="未设置文档级授权（继承知识库）" :image-size="60" />
    </el-dialog>

    <!-- 版本历史对话框 -->
    <el-dialog v-model="versionDialog" :title="`版本历史：${versionDoc?.name || ''}`" width="640px">
      <el-alert type="info" :closable="false" style="margin-bottom:12px"
        title="上传同名文件会自动创建新版本。回滚会创建一个新版本，内容为指定历史版本。" />
      <el-table :data="versions" size="small" max-height="400">
        <el-table-column prop="version" label="版本" width="80" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="row.is_current ? 'success' : 'info'">v{{ row.version }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="char_count" label="字符数" width="100" align="center" />
        <el-table-column prop="uploader" label="上传者" width="120" />
        <el-table-column prop="create_time" label="上传时间" width="170" />
        <el-table-column prop="remark" label="备注" show-overflow-tooltip />
        <el-table-column label="操作" width="100" align="center">
          <template #default="{ row }">
            <el-button v-if="!row.is_current && canWrite" link type="primary"
              @click="rollback(row)">回滚</el-button>
            <el-tag v-if="row.is_current" size="small" type="success">当前</el-tag>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!versions.length" description="暂无版本记录" :image-size="60" />
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Lock } from '@element-plus/icons-vue'
import { listDocuments, search, getParagraphs, reparseDocument,
  getAuthorizedUsers, grantAccess, revokeAccess, setKbPublic,
  getDocAuthorizedUsers, grantDocAccess, revokeDocAccess, inheritKbAccess } from '@/api/knowledge'
import request from '@/api/request'
import type { DocumentItem, Paragraph, SearchResult } from '@/types'
import { useUserStore } from '@/store/user'
import UploadDoc from '@/components/UploadDoc.vue'

const route = useRoute()
const kbId = Number(route.params.id)
const userStore = useUserStore()
const canWrite = computed(() => ['admin', 'editor'].includes(userStore.role))
const isAdmin = computed(() => userStore.role === 'admin')

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

const permDialog = ref(false)
const permUsers = ref<any[]>([])
const allUsers = ref<any[]>([])
const permSelectedUser = ref<number | null>(null)

const docPermDialog = ref(false)
const docPermUsers = ref<any[]>([])
const docPermSelectedUser = ref<number | null>(null)
const currentDoc = ref<DocumentItem | null>(null)

const versionDialog = ref(false)
const versionDoc = ref<DocumentItem | null>(null)
const versions = ref<any[]>([])

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

async function reparse(row: DocumentItem) {
  try {
    await reparseDocument(row.id)
    ElMessage.success('已重新加入解析队列')
    loadDocs()
  } catch {
    /* 错误已由拦截器提示 */
  }
}

async function openPermDialog() {
  permDialog.value = true
  await Promise.all([loadPermUsers(), loadAllUsers()])
}

async function loadPermUsers() {
  permUsers.value = await getAuthorizedUsers(kbId)
}

async function loadAllUsers() {
  try {
    allUsers.value = await request.get('/users/')
  } catch {
    allUsers.value = []
  }
}

async function grantUser(userId: number) {
  if (!userId) return
  await grantAccess(kbId, [userId])
  ElMessage.success('授权成功')
  permSelectedUser.value = null
  loadPermUsers()
}

async function revokeUser(userId: number) {
  try {
    await ElMessageBox.confirm('确定取消该用户的访问权限？', '取消授权', { type: 'warning' })
  } catch {
    return
  }
  await revokeAccess(kbId, [userId])
  ElMessage.success('已取消授权')
  loadPermUsers()
}

async function setPublic() {
  try {
    await ElMessageBox.confirm('设为公开后所有用户均可访问，确定清空授权列表？', '设为公开', { type: 'warning' })
  } catch {
    return
  }
  await setKbPublic(kbId)
  ElMessage.success('已设为公开')
  loadPermUsers()
}

async function openDocPermDialog(row: DocumentItem) {
  currentDoc.value = row
  docPermDialog.value = true
  await Promise.all([loadDocPermUsers(row.id), loadAllUsers()])
}

async function loadDocPermUsers(docId: number) {
  docPermUsers.value = await getDocAuthorizedUsers(docId)
}

async function grantDocUser(userId: number) {
  if (!userId || !currentDoc.value) return
  await grantDocAccess(currentDoc.value.id, [userId])
  ElMessage.success('授权成功')
  docPermSelectedUser.value = null
  loadDocPermUsers(currentDoc.value.id)
}

async function revokeDocUser(userId: number) {
  if (!currentDoc.value) return
  try {
    await ElMessageBox.confirm('确定取消该用户的文档访问权限？', '取消授权', { type: 'warning' })
  } catch {
    return
  }
  await revokeDocAccess(currentDoc.value.id, [userId])
  ElMessage.success('已取消授权')
  loadDocPermUsers(currentDoc.value.id)
}

async function inheritKb() {
  if (!currentDoc.value) return
  try {
    await ElMessageBox.confirm('恢复继承知识库权限后，文档级授权将被清空，确定？', '恢复继承', { type: 'warning' })
  } catch {
    return
  }
  await inheritKbAccess(currentDoc.value.id)
  ElMessage.success('已恢复继承知识库权限')
  loadDocPermUsers(currentDoc.value.id)
}

// ---- 版本管理 ----
async function openVersionDialog(row: DocumentItem) {
  versionDoc.value = row
  versionDialog.value = true
  try {
    versions.value = await request.get(`/knowledge/documents/${row.id}/versions/`)
  } catch {
    versions.value = []
  }
}

async function rollback(version: any) {
  if (!versionDoc.value) return
  try {
    await ElMessageBox.confirm(`确定回滚到 v${version.version}？将创建一个新版本，内容为该历史版本。`, '回滚版本', { type: 'warning' })
  } catch {
    return
  }
  try {
    await request.post(`/knowledge/documents/${versionDoc.value.id}/rollback/`, {
      version_id: version.id
    })
    ElMessage.success('已回滚，正在重新解析')
    versionDialog.value = false
    loadDocs()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '回滚失败')
  }
}

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
.perm-toolbar { display: flex; gap: 8px; align-items: center; }
</style>
