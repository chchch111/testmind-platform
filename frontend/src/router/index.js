import { createRouter, createWebHistory } from 'vue-router'

import MainLayout from '../layout/MainLayout.vue'
import Dashboard from '../views/Dashboard.vue'
import CaseSetList from '../views/CaseSetList.vue'
import CaseSetDetail from '../views/CaseSetDetail.vue'
import KnowledgeBase from '../views/KnowledgeBase.vue'
import AiGenerate from '../views/AiGenerate.vue'
import Login from '../views/Login.vue'
import PermissionManagement from '../views/PermissionManagement.vue'
import Forbidden from '../views/Forbidden.vue'
import TaskList from '../views/TaskList.vue'
import TaskDetail from '../views/TaskDetail.vue'
import ExecutorWork from '../views/ExecutorWork.vue'
import { getCurrentUser, isLoggedIn } from '../utils/storage'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', component: Login, meta: { title: '登录' } },
    {
      path: '/',
      component: MainLayout,
      children: [
        { path: '', redirect: '/dashboard' },
        { path: 'dashboard', component: Dashboard, meta: { title: '首页概览' } },
        { path: 'case-sets', component: CaseSetList, meta: { title: '用例集管理' } },
        { path: 'case-sets/:id', component: CaseSetDetail, meta: { title: '用例集详情' } },
        { path: 'knowledge-bases', component: KnowledgeBase, meta: { title: '知识库管理' } },
        { path: 'ai-generate', component: AiGenerate, meta: { title: 'AI生成用例' } },
        { path: 'permissions', component: PermissionManagement, meta: { title: '权限管理', requiresAdmin: true } },
        { path: '403', component: Forbidden, meta: { title: '无权限访问' } },
        { path: 'tasks', component: TaskList, meta: { title: '测试任务管理' } },
        { path: 'tasks/:id', component: TaskDetail, meta: { title: '测试任务详情' } },
        { path: 'executor', component: ExecutorWork, meta: { title: '执行工作台' } }
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
