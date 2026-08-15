import { createRouter, createWebHistory } from 'vue-router'
import Layout from '@/layout/Layout.vue'
import { useUserStore } from '@/store/user'

const routes = [
  { path: '/login', name: 'Login', component: () => import('@/views/Login.vue') },
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
  // 已登录访问登录页 -> 跳首页
  if (to.path === '/login') {
    return next(token ? '/' : undefined)
  }
  if (to.meta.requiresAuth && !token) {
    return next('/login')
  }
  // 已登录但用户态未加载，先拉取资料（含角色）
  const userStore = useUserStore()
  if (token && !userStore.user) {
    try {
      await userStore.fetchProfile()
    } catch {
      localStorage.removeItem('access_token')
      return next('/login')
    }
  }
  // 角色校验
  const roles = to.meta.roles as string[] | undefined
  if (roles && userStore.role && !roles.includes(userStore.role)) {
    return next('/')
  }
  next()
})

export default router
