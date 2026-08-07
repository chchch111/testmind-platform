<template>
  <div class="dashboard">
    <div class="page-card">
      <h1 class="page-title">系统首页</h1>
      <p class="page-desc">
        本平台用于管理思维导图式测试用例，支持XMind导入导出、RAG知识库、DeepSeek-v4-flash自动生成测试用例和测试任务执行同步。
      </p>

      <el-row :gutter="16">
        <el-col :span="12">
          <el-card shadow="never">
            <template #header>FastAPI 后端状态</template>
            <div :class="backendOk ? 'status-ok' : 'status-bad'">
              {{ backendStatus }}
            </div>
          </el-card>
        </el-col>
        <el-col :span="12">
          <el-card shadow="never">
            <template #header>MySQL 数据库状态</template>
            <div :class="dbOk ? 'status-ok' : 'status-bad'">
              {{ dbStatus }}
            </div>
          </el-card>
        </el-col>
      </el-row>

      <div class="actions">
        <el-button type="primary" @click="loadStatus">重新检测</el-button>
        <el-button @click="$router.push('/case-sets')">进入用例集管理</el-button>
        <el-button @click="$router.push('/knowledge-bases')">进入知识库管理</el-button>
        <el-button @click="$router.push('/ai-generate')">进入AI生成用例</el-button>
      </div>
    </div>

    <div class="page-card flow-card">
      <h2>毕设演示流程</h2>
      <el-steps :active="6" finish-status="success" align-center>
        <el-step title="用例管理" description="树形用例CRUD" />
        <el-step title="XMind" description="导入导出" />
        <el-step title="知识库" description="切片向量化" />
        <el-step title="RAG检索" description="FAISS相似检索" />
        <el-step title="AI生成" description="DeepSeek生成用例" />
        <el-step title="任务执行" description="下发与同步" />
      </el-steps>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { checkDatabaseHealth, checkHealth } from '../api/health'

const backendOk = ref(false)
const dbOk = ref(false)
const backendStatus = ref('检测中...')
const dbStatus = ref('检测中...')

async function loadStatus() {
  backendStatus.value = '检测中...'
  dbStatus.value = '检测中...'

  try {
    const result = await checkHealth()
    backendOk.value = result.status === 'ok'
    backendStatus.value = result.message || 'FastAPI服务运行正常'
  } catch (error) {
    backendOk.value = false
    backendStatus.value = error.message
  }

  try {
    const result = await checkDatabaseHealth()
    dbOk.value = result.status === 'ok'
    dbStatus.value = result.message || 'MySQL数据库连接正常'
  } catch (error) {
    dbOk.value = false
    dbStatus.value = error.message
  }
}

onMounted(loadStatus)
</script>

<style scoped>
.dashboard {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.actions {
  margin-top: 18px;
  display: flex;
  gap: 10px;
}

.flow-card h2 {
  margin-top: 0;
  margin-bottom: 20px;
}
</style>
