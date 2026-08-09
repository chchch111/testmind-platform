<template>
  <el-container class="app-shell">
    <el-aside width="240px" class="app-aside">
      <div class="brand">
        <div class="brand-title">RAG测试用例平台</div>
        <div class="brand-subtitle">毕业设计演示系统</div>
      </div>
      <el-menu router :default-active="$route.path" class="side-menu">
        <el-menu-item index="/dashboard">首页概览</el-menu-item>
        <el-menu-item index="/case-sets">用例集管理</el-menu-item>
        <el-menu-item index="/knowledge-bases">知识库管理</el-menu-item>
        <el-menu-item index="/ai-generate">AI生成用例</el-menu-item>
        <el-menu-item v-if="isAdmin" index="/permissions">权限管理</el-menu-item>
        <el-menu-item index="/tasks">测试任务管理</el-menu-item>
        <el-menu-item index="/executor">执行工作台</el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="app-header">
        <div>
          <div class="header-title">{{ $route.meta.title || '首页' }}</div>
          <div class="header-desc">基于大模型与RAG的思维导图测试用例自动生成与管理平台</div>
        </div>
        <div class="user-box">
          <div class="user-info">
            <strong>{{ currentUser?.real_name || currentUser?.username || '未登录' }}</strong>
            <span>{{ currentUser?.username }} · {{ currentUser?.role_code }}</span>
          </div>
          <el-button size="small" @click="handleLogout">退出登录</el-button>
        </div>
      </el-header>

      <el-main class="app-main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { getCurrentUserProfile, logout } from '../api/auth'
import { clearAuth, getCurrentUser, setCurrentUser } from '../utils/storage'

const router = useRouter()
const currentUser = ref(getCurrentUser())
const isAdmin = computed(() => currentUser.value?.role_code === 'admin')

async function refreshCurrentUser() {
  try {
    const user = await getCurrentUserProfile()
    setCurrentUser(user)
    currentUser.value = user
  } catch {
    clearAuth()
    router.replace('/login')
  }
}

async function handleLogout() {
  try {
    await logout()
  } finally {
    clearAuth()
    router.replace('/login')
  }
}

onMounted(refreshCurrentUser)
</script>

<style scoped>
.app-shell {
  min-height: 100vh;
}

.app-aside {
  background: #111827;
  color: #fff;
}

.brand {
  padding: 22px 18px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.12);
}

.brand-title {
  font-size: 20px;
  font-weight: 700;
}

.brand-subtitle {
  margin-top: 8px;
  color: #cbd5e1;
  font-size: 13px;
}

.side-menu {
  border-right: 0;
  background: transparent;
}

:deep(.el-menu-item) {
  color: #d1d5db;
}

:deep(.el-menu-item.is-active) {
  color: #fff;
  background: #2563eb;
}

:deep(.el-menu-item:hover) {
  color: #fff;
  background: #1f2937;
}

.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 72px;
  background: #fff;
  border-bottom: 1px solid #e5e7eb;
}

.header-title {
  font-size: 20px;
  font-weight: 700;
}

.header-desc {
  margin-top: 4px;
  color: #64748b;
  font-size: 13px;
}

.user-box {
  display: flex;
  align-items: center;
  gap: 12px;
  color: #475569;
}

.user-info {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
}

.user-info strong {
  color: #0f172a;
  font-size: 14px;
}

.user-info span {
  color: #64748b;
  font-size: 12px;
}

.app-main {
  padding: 22px;
}
</style>
