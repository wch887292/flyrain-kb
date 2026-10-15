<template>
  <div>
    <div class="toolbar">
      <el-button type="primary" @click="dialog = true">
        <el-icon><Plus /></el-icon> 新增模型配置
      </el-button>
    </div>

    <el-table :data="list" border>
      <el-table-column prop="name" label="名称" />
      <el-table-column prop="type" label="类型" width="120">
        <template #default="{ row }">
          <el-tag :type="row.type === 'llm' ? 'primary' : 'warning'">
            {{ row.type === 'llm' ? '对话大模型' : '向量模型' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="base_url" label="Base URL" show-overflow-tooltip />
      <el-table-column prop="model_name" label="模型" width="160" />
      <el-table-column prop="dimensions" label="维度" width="80" />
      <el-table-column label="视觉" width="80" align="center">
        <template #default="{ row }">
          <el-tag v-if="row.supports_vision" size="small" type="success">支持</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="默认" width="80">
        <template #default="{ row }">
          <el-icon v-if="row.is_default" color="#67c23a"><CircleCheck /></el-icon>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="160">
        <template #default="{ row }">
          <el-button link type="primary" @click="test(row)">测试</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialog" title="新增模型配置" width="520px">
      <el-form label-width="100px">
        <el-form-item label="名称"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="类型">
          <el-select v-model="form.type" style="width:100%">
            <el-option label="对话大模型" value="llm" />
            <el-option label="向量模型" value="embedding" />
          </el-select>
        </el-form-item>
        <el-form-item label="Base URL"><el-input v-model="form.base_url" /></el-form-item>
        <el-form-item label="API Key"><el-input v-model="form.api_key" show-password /></el-form-item>
        <el-form-item label="模型名称"><el-input v-model="form.model_name" /></el-form-item>
        <el-form-item label="向量维度" v-if="form.type === 'embedding'">
          <el-input-number v-model="form.dimensions" :min="64" :max="4096" :step="64" />
        </el-form-item>
        <el-form-item label="支持视觉理解" v-if="form.type === 'llm'">
          <el-switch v-model="form.supports_vision" />
          <span style="margin-left:8px; font-size:12px; color:#9ca3af">
            开启后可用于 PDF 图片内容理解
          </span>
        </el-form-item>
        <el-form-item label="输入单价" v-if="form.type === 'llm'">
          <el-input-number v-model="form.price_input_per_1m" :min="0" :step="0.1" />
          <span style="margin-left:8px; font-size:12px; color:#9ca3af">$/1M tokens</span>
        </el-form-item>
        <el-form-item label="输出单价" v-if="form.type === 'llm'">
          <el-input-number v-model="form.price_output_per_1m" :min="0" :step="0.1" />
          <span style="margin-left:8px; font-size:12px; color:#9ca3af">$/1M tokens</span>
        </el-form-item>
        <el-form-item label="设为默认">
          <el-switch v-model="form.is_default" />
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
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { listProviders, createProvider, testProviderById } from '@/api/chat'
import type { ModelProvider } from '@/types'

const list = ref<ModelProvider[]>([])
const dialog = ref(false)
const saving = ref(false)
const form = reactive<Partial<ModelProvider>>({
  name: '', type: 'llm', base_url: '', api_key: '', model_name: '',
  dimensions: 1024, supports_vision: false,
  price_input_per_1m: 0, price_output_per_1m: 0, is_default: false
})

async function load() {
  list.value = await listProviders()
}

async function save() {
  if (!form.name || !form.base_url || !form.model_name) {
    ElMessage.warning('请填写完整')
    return
  }
  saving.value = true
  try {
    await createProvider(form)
    dialog.value = false
    await load()
  } finally {
    saving.value = false
  }
}

async function test(row: ModelProvider) {
  try {
    const r = await testProviderById(row.id)
    ElMessage.success(r.success ? '连通成功' : `失败：${r.message}`)
  } catch { /* 拦截器提示 */ }
}

onMounted(load)
</script>

<style scoped>
.toolbar { margin-bottom: 16px; }
</style>
