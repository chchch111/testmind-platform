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
          <span>当前模拟用户ID</span>
          <el-input-number v-model="currentUserId" :min="1" size="small" @change="saveUserId" />
        </div>
      </el-header>

      <el-main class="app-main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { ref } from 'vue'
import { getCurrentUserId, setCurrentUserId } from '../utils/storage'

const currentUserId = ref(getCurrentUserId())

function saveUserId(value) {
  setCurrentUserId(value)
}
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
  gap: 10px;
  color: #475569;
}

.app-main {
  padding: 22px;
}
</style>
