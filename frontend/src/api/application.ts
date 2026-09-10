import request from './request'

export interface Application {
  id: number
  name: string
  desc: string
  kb_ids?: number[]
  kb_names?: string[]
  system_prompt: string
  temperature: number
  max_tokens: number
  vector_weight: number
  is_active: boolean
  create_time: string
}

export function listApps() {
  return request.get<Application[]>('/apps/')
}

export function createApp(data: Partial<Application>) {
  return request.post('/apps/', data)
}

export function updateApp(id: number, data: Partial<Application>) {
  return request.put(`/apps/${id}/`, data)
}

export function deleteApp(id: number) {
  return request.delete(`/apps/${id}/`)
}

// ---- 工作流 ----
export interface WorkflowStep {
  id: number
  workflow: number
  order: number
  name: string
  prompt: string
  temperature: number
  max_tokens: number
  create_time: string
}

export interface Workflow {
  id: number
  name: string
  desc: string
  status: 'draft' | 'active' | 'archived'
  steps?: WorkflowStep[]
  step_count?: number
  create_time: string
  update_time: string
}

export interface WorkflowExecution {
  id: number
  workflow: number
  workflow_name: string
  input_text: string
  output_text: string
  step_outputs: { step_order: number; step_name: string; output: string }[]
  status: 'running' | 'success' | 'failed'
  error_msg: string
  duration_ms: number
  create_time: string
}

export function listWorkflows() {
  return request.get<Workflow[]>('/workflows/')
}

export function createWorkflow(data: Partial<Workflow>) {
  return request.post('/workflows/', data)
}

export function updateWorkflow(id: number, data: Partial<Workflow>) {
  return request.put(`/workflows/${id}/`, data)
}

export function deleteWorkflow(id: number) {
  return request.delete(`/workflows/${id}/`)
}

export function getWorkflowSteps(id: number) {
  return request.get<WorkflowStep[]>(`/workflows/${id}/steps/`)
}

export function addWorkflowStep(id: number, data: Partial<WorkflowStep>) {
  return request.post(`/workflows/${id}/add_step/`, data)
}

export function reorderWorkflowSteps(id: number, stepIds: number[]) {
  return request.post(`/workflows/${id}/reorder_steps/`, { step_ids: stepIds })
}

export function executeWorkflow(id: number, inputText: string) {
  return request.post<WorkflowExecution>(`/workflows/${id}/execute/`, { input_text: inputText })
}

export function getWorkflowExecutions(id: number) {
  return request.get<WorkflowExecution[]>(`/workflows/${id}/executions/`)
}
