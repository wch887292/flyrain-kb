import { createRouter, createWebHistory } from 'vue-router'
import Layout from '@/layout/Layout.vue'
import { useUserStore } from '@/store/user'

const routes = [
  { path: '/login', name: 'Login', component: () => import('@/views/Login.vue') },
  { path: '/agent/share/:shareCode', name: 'AgentShare', component: () => import('@/views/AgentShare.vue') },
  {
    path: '/',
    component: Layout,
    redirect: '/knowledge',
    meta: { requiresAuth: true },
    children: [
      {
        path: 'knowledge',
        name: 'KnowledgeList',
        component: () => import('@/views/KnowledgeList.vue'),
        meta: { title: '知识库' }
      },
      {
        path: 'knowledge/:id',
        name: 'KnowledgeDetail',
        component: () => import('@/views/KnowledgeDetail.vue'),
        meta: { title: '知识库详情' }
      },
      {
        path: 'apps',
        name: 'AppList',
        component: () => import('@/views/AppList.vue'),
        meta: { title: 'AI 应用', roles: ['admin', 'editor'] }
      },
      {
        path: 'chat/:appId?',
        name: 'Chat',
        component: () => import('@/views/Chat.vue'),
        meta: { title: '对话' }
      },
      {
        path: 'model',
        name: 'ModelSetting',
        component: () => import('@/views/ModelSetting.vue'),
        meta: { title: '模型配置', roles: ['admin'] }
      },
      {
        path: 'users',
        name: 'UserManagement',
        component: () => import('@/views/UserManagement.vue'),
        meta: { title: '用户管理', roles: ['admin'] }
      },
      {
        path: 'audit',
        name: 'AuditLog',
        component: () => import('@/views/AuditLog.vue'),
        meta: { title: '审计日志', roles: ['admin'] }
      },
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/Dashboard.vue'),
        meta: { title: '数据分析', roles: ['admin', 'editor'] }
      },
      {
        path: 'workflow',
        name: 'Workflow',
        component: () => import('@/views/Workflow.vue'),
        meta: { title: '工作流编排', roles: ['admin', 'editor'] }
      },
      {
        path: 'plugins',
        name: 'Plugin',
        component: () => import('@/views/Plugin.vue'),
        meta: { title: '插件管理', roles: ['admin', 'editor'] }
      },
      {
        path: 'api-keys',
        name: 'ApiKey',
        component: () => import('@/views/ApiKey.vue'),
        meta: { title: 'API Key', roles: ['admin', 'editor', 'user'] }
      },
      {
        path: 'agents',
        name: 'AgentManage',
        component: () => import('@/views/AgentManage.vue'),
        meta: { title: '智能体管理', roles: ['admin', 'editor'] }
      },
      {
        path: 'agent/chat/:id?',
        name: 'AgentChat',
        component: () => import('@/views/AgentChat.vue'),
        meta: { title: '智能体对话' }
      },
      {
        path: 'agent-templates',
        name: 'AgentTemplate',
        component: () => import('@/views/AgentTemplate.vue'),
        meta: { title: '智能体模板' }
      },
      {
        path: 'mcp-servers',
        name: 'MCPServer',
        component: () => import('@/views/MCPServer.vue'),
        meta: { title: 'MCP 服务器', roles: ['admin', 'editor'] }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach(async (to, _from, next) => {
  const token = localStorage.getItem('access_token')
  if (to.path === '/login') {
    return next(token ? '/' : undefined)
  }
  if (to.meta.requiresAuth && !token) {
    return next('/login')
  }
  const userStore = useUserStore()
  if (token && !userStore.user) {
    try {
      await userStore.fetchProfile()
    } catch {
      localStorage.removeItem('access_token')
      return next('/login')
    }
  }
  const roles = to.meta.roles as string[] | undefined
  if (roles && userStore.role && !roles.includes(userStore.role)) {
    return next('/')
  }
  next()
})

export default router
