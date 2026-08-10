import { createRouter, createWebHistory } from 'vue-router'

import { getCurrentUser, isLoggedIn } from '../utils/storage'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      component: () => import('../views/Login.vue'),
      meta: { title: '登录' }
    },
    {
      path: '/',
      component: () => import('../layout/MainLayout.vue'),
      children: [
        { path: '', redirect: '/dashboard' },
        { path: 'dashboard', component: () => import('../views/Dashboard.vue'), meta: { title: '首页概览' } },
        { path: 'case-sets', component: () => import('../views/CaseSetList.vue'), meta: { title: '用例集管理' } },
        { path: 'case-sets/:id', component: () => import('../views/CaseSetDetail.vue'), meta: { title: '用例集详情' } },
        { path: 'knowledge-bases', component: () => import('../views/KnowledgeBase.vue'), meta: { title: '知识库管理' } },
        { path: 'ai-generate', component: () => import('../views/AiGenerate.vue'), meta: { title: 'AI生成用例' } },
        { path: 'permissions', component: () => import('../views/PermissionManagement.vue'), meta: { title: '权限管理', requiresAdmin: true } },
        { path: '403', component: () => import('../views/Forbidden.vue'), meta: { title: '无权限访问' } },
        { path: 'tasks', component: () => import('../views/TaskList.vue'), meta: { title: '测试任务管理' } },
        { path: 'tasks/:id', component: () => import('../views/TaskDetail.vue'), meta: { title: '测试任务详情' } },
        { path: 'executor', component: () => import('../views/ExecutorDirectory.vue'), meta: { title: '执行工作台' } },
        { path: 'executor/tasks/:id', component: () => import('../views/ExecutorTaskDetail.vue'), meta: { title: '用例执行' } }
      ]
    }
  ]
})

router.beforeEach(to => {
  const loggedIn = isLoggedIn()
  if (to.path === '/login') {
    return loggedIn ? '/dashboard' : true
  }
  if (!loggedIn) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  if (to.meta.requiresAdmin && getCurrentUser()?.role_code !== 'admin') {
    return '/403'
  }
  return true
})

router.afterEach(to => {
  document.title = `${to.meta.title || '首页'} - RAG思维导图测试用例平台`
})

export default router
