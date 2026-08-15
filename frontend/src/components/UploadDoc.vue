<template>
  <el-upload
    :show-file-list="false"
    :before-upload="beforeUpload"
    :http-request="handleUpload"
    accept=".pdf,.docx,.txt,.md,.xlsx,.xls"
  >
    <el-button type="primary" :loading="loading">
      <el-icon><Upload /></el-icon> 上传文档
    </el-button>
  </el-upload>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { uploadDoc } from '@/api/knowledge'

const props = defineProps<{ kbId: number }>()
const emit = defineEmits<{ (e: 'uploaded'): void }>()
const loading = ref(false)

function beforeUpload(file: File) {
  const okTypes = ['.pdf', '.docx', '.txt', '.md', '.xlsx', '.xls']
  const ext = '.' + file.name.split('.').pop()?.toLowerCase()
  if (!okTypes.includes(ext)) {
    ElMessage.error('不支持的文件类型')
    return false
  }
  if (file.size > 50 * 1024 * 1024) {
    ElMessage.error('文件不能超过 50MB')
    return false
  }
  return true
}

async function handleUpload(options: { file: File }) {
  loading.value = true
  try {
    await uploadDoc(props.kbId, options.file)
    ElMessage.success('已加入解析队列')
    emit('uploaded')
  } catch {
    /* 拦截器已提示 */
  } finally {
    loading.value = false
  }
}
</script>
