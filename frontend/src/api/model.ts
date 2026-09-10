import request from './request'

export interface ModelProvider {
  id: number
  name: string
  type: 'llm' | 'embedding'
  base_url: string
  api_key: string
  model_name: string
  dimensions: number
  price_input_per_1m: number
  price_output_per_1m: number
  is_default: boolean
  create_time: string
}

export function listProviders() {
  return request.get<ModelProvider[]>('/model-providers/')
}

export function createProvider(data: Partial<ModelProvider>) {
  return request.post('/model-providers/', data)
}

export function updateProvider(id: number, data: Partial<ModelProvider>) {
  return request.put(`/model-providers/${id}/`, data)
}

export function deleteProvider(id: number) {
  return request.delete(`/model-providers/${id}/`)
}

export function testProvider(data: { type: string; base_url?: string; api_key?: string; model_name?: string }) {
  return request.post('/model-providers/test/', data)
}

/** 模型调用成本分析统计 */
export function getUsageStats(params: { days?: number; model_type?: string } = {}) {
  return request.get('/model-providers/usage_stats/', { params })
}
