<template>
  <div>
    <div class="toolbar">
      <el-select v-model="filterAction" placeholder="操作类型" clearable style="width:140px" @change="load">
        <el-option v-for="a in actionOptions" :key="a.value" :label="a.label" :value="a.value" />
      </el-select>
      <el-select v-model="filterResource" placeholder="资源类型" clearable style="width:140px" @change="load">
        <el-option v-for="r in resourceOptions" :key="r" :label="r" :value="r" />
      </el-select>
      <el-button @click="loadStats">统计</el-button>
    </div>

    <el-table :data="list" border v-loading="loading" style="margin-top:12px">
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="username" label="用户" width="120" />
      <el-table-column prop="action_display" label="操作" width="100">
        <template #default="{ row }">
          <el-tag :type="actionTagType(row.action)" size="small">{{ row.action_display }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="resource_type" label="资源类型" width="120" />
      <el-table-column prop="resource_id" label="资源ID" width="80" />
      <el-table-column prop="method" label="方法" width="70" />
      <el-table-column prop="path" label="路径" min-width="200" show-overflow-tooltip />
      <el-table-column prop="ip" label="IP" width="130" />
      <el-table-column prop="status_code" label="状态码" width="80" />
      <el-table-column prop="detail" label="详情" min-width="150" show-overflow-tooltip />
      <el-table-column prop="create_time" label="时间" width="170" />
    </el-table>

    <el-pagination
      v-model:current-page="page"
      v-model:page-size="pageSize"
      :total="total"
      :page-sizes="[20, 50, 100]"
      layout="total, sizes, prev, pager, next"
      @current-change="load"
      @size-change="load"
      style="margin-top:16px; justify-content:center"
    />

    <el-dialog v-model="statsVisible" title="操作统计" width="400px">
      <el-table :data="stats" border>
        <el-table-column prop="action" label="操作类型" />
        <el-table-column prop="count" label="次数" width="100" />
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { listAuditLogs, getAuditStats } from '@/api/audit'
import type { AuditLog } from '@/types'

const list = ref<AuditLog[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(false)
const filterAction = ref('')
const filterResource = ref('')
const statsVisible = ref(false)
const stats = ref<{ action: string; count: number }[]>([])

const actionOptions = [
  { value: 'login', label: '登录' },
  { value: 'create', label: '创建' },
  { value: 'update', label: '更新' },
  { value: 'delete', label: '删除' },
  { value: 'upload', label: '上传' },
  { value: 'reparse', label: '重新解析' },
]
const resourceOptions = ['knowledge_base', 'document', 'application', 'user', 'model_provider', 'other']

function actionTagType(action: string) {
  return { create: 'success', update: 'warning', delete: 'danger', upload: 'primary', reparse: 'info' }[action] || 'info'
}

async function load() {
  loading.value = true
  try {
    const data = await listAuditLogs({
      page: page.value,
      page_size: pageSize.value,
      action: filterAction.value || undefined,
      resource_type: filterResource.value || undefined,
    })
    list.value = data.results
    total.value = data.count
  } finally {
    loading.value = false
  }
}

async function loadStats() {
  stats.value = await getAuditStats()
  statsVisible.value = true
}

onMounted(load)
</script>

<style scoped>
.toolbar { display: flex; gap: 8px; align-items: center; }
</style>
