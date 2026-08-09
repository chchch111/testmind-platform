<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-brand">RAG思维导图测试用例平台</div>
      <h1>系统登录</h1>
      <p>毕业设计演示系统，登录后可进入用例、知识库、AI生成和任务管理模块。</p>

      <el-form label-position="top" @keyup.enter="handleLogin">
        <el-form-item label="用户名">
          <el-input v-model="form.username" size="large" placeholder="请输入用户名" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" size="large" type="password" show-password placeholder="请输入密码" />
        </el-form-item>
      </el-form>

      <el-alert class="demo-account" title="开发演示账号：admin / admin123456（仅用于本地演示）" type="info" :closable="false" show-icon />
      <el-button class="login-button" type="primary" size="large" :loading="loggingIn" @click="handleLogin">登录系统</el-button>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { login } from '../api/auth'
import { showWarning } from '../utils/message'
import { saveLoginState } from '../utils/storage'

const route = useRoute()
const router = useRouter()
const loggingIn = ref(false)
const form = reactive({
  username: 'admin',
  password: 'admin123456'
})

async function handleLogin() {
  if (!form.username.trim() || !form.password.trim()) {
    showWarning('请输入用户名和密码')
    return
  }
  loggingIn.value = true
  try {
    const result = await login({
      username: form.username.trim(),
      password: form.password
    })
    saveLoginState(result.access_token, result.user)
    router.replace(String(route.query.redirect || '/dashboard'))
  } finally {
    loggingIn.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: radial-gradient(circle at top left, #dbeafe, transparent 34%), linear-gradient(135deg, #0f172a, #1e3a8a);
}

.login-card {
  width: 430px;
  padding: 34px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 24px 80px rgba(15, 23, 42, 0.32);
}

.login-brand {
  color: #2563eb;
  font-size: 15px;
  font-weight: 800;
}

.login-card h1 {
  margin: 12px 0 8px;
  color: #0f172a;
  font-size: 30px;
}

.login-card p {
  margin: 0 0 22px;
  color: #64748b;
  line-height: 1.7;
}

.demo-account {
  margin: 4px 0 18px;
}

.login-button {
  width: 100%;
}
</style>
