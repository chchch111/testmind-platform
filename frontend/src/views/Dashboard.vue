<template>
  <div class="dashboard">
    <div class="page-card">
      <h1 class="page-title">系统首页</h1>
      <p class="page-desc">
        本平台用于管理思维导图式测试用例，支持XMind导入导出、RAG知识库、DeepSeek-v4-flash自动生成测试用例和测试任务执行同步。
      </p>
    </div>

    <div class="overview-grid">
      <div class="overview-card page-card">
        <span>用例集数量</span>
        <strong>{{ stats.caseSetCount }}</strong>
        <small>支持手动、XMind、AI生成</small>
      </div>
      <div class="overview-card page-card">
        <span>知识库数量</span>
        <strong>{{ stats.knowledgeBaseCount }}</strong>
        <small>LangChain + FAISS 持久化</small>
      </div>
      <div class="overview-card page-card">
        <span>测试任务数量</span>
        <strong>{{ stats.taskCount }}</strong>
        <small>任务下发、执行同步、报告导出</small>
      </div>
      <div class="overview-card page-card">
        <span>AI生成记录</span>
        <strong>{{ stats.generationCount }}</strong>
        <small>RAG检索链路可追溯</small>
      </div>
    </div>

    <div class="page-card demo-card">
      <div class="demo-header">
        <div>
          <h2>快速导航</h2>
          <p>覆盖“知识库 → RAG → AI生成 → 脑图编辑 → 任务执行”的完整业务闭环。</p>
        </div>
        <el-button type="primary" @click="$router.push('/ai-generate')">从AI生成开始</el-button>
      </div>
      <div class="demo-grid">
        <div v-for="item in navItems" :key="item.title" class="demo-item" @click="$router.push(item.path)">
          <strong>{{ item.title }}</strong>
          <span>{{ item.desc }}</span>
        </div>
      </div>
    </div>

    <div class="page-card flow-card">
      <h2>平台功能流程</h2>
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
import { onMounted, reactive } from 'vue'
import { listGenerationRecords } from '../api/ai'
import { listCaseSets } from '../api/case'
import { listKnowledgeBases } from '../api/rag'
import { listTasks } from '../api/task'

const stats = reactive({
  caseSetCount: 0,
  knowledgeBaseCount: 0,
  taskCount: 0,
  generationCount: 0
})

const navItems = [
  { title: '1. 知识库管理', desc: '录入资料、构建FAISS索引、检索命中片段', path: '/knowledge-bases' },
  { title: '2. AI生成用例', desc: 'DeepSeek结合RAG上下文生成树形用例', path: '/ai-generate' },
  { title: '3. 脑图编辑器', desc: '标签筛选、层级展开、迷你地图、撤销重做', path: '/case-sets' },
  { title: '4. 测试任务管理', desc: '绑定用例集、分配执行人、导出执行报告', path: '/tasks' }
]

async function loadStats() {
  const [caseSetResult, knowledgeBaseResult, taskResult, generationResult] = await Promise.allSettled([
    listCaseSets({ page: 1, page_size: 1 }),
    listKnowledgeBases(),
    listTasks({ page: 1, page_size: 100 }),
    listGenerationRecords()
  ])
  if (caseSetResult.status === 'fulfilled') {
    stats.caseSetCount = caseSetResult.value.total || caseSetResult.value.items?.length || 0
  }
  if (knowledgeBaseResult.status === 'fulfilled') {
    stats.knowledgeBaseCount = knowledgeBaseResult.value.length
  }
  if (taskResult.status === 'fulfilled') {
    stats.taskCount = Array.isArray(taskResult.value) ? taskResult.value.length : taskResult.value.total || 0
  }
  if (generationResult.status === 'fulfilled') {
    stats.generationCount = generationResult.value.length
  }
}

onMounted(loadStats)
</script>

<style scoped>
.dashboard {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.overview-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.overview-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.overview-card span,
.overview-card small {
  color: #64748b;
}

.overview-card strong {
  color: #2563eb;
  font-size: 30px;
}

.demo-card h2 {
  margin: 0 0 8px;
}

.demo-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.demo-header p {
  margin: 0;
  color: #64748b;
  line-height: 1.7;
}

.demo-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-top: 18px;
}

.demo-item {
  display: flex;
  min-height: 92px;
  flex-direction: column;
  gap: 8px;
  padding: 14px;
  border: 1px solid #dbeafe;
  border-radius: 12px;
  background: linear-gradient(135deg, #eff6ff, #ffffff);
  cursor: pointer;
  transition: 0.18s ease;
}

.demo-item:hover {
  border-color: #2563eb;
  box-shadow: 0 10px 24px rgba(37, 99, 235, 0.16);
  transform: translateY(-2px);
}

.demo-item span {
  color: #64748b;
  line-height: 1.6;
}

.flow-card h2 {
  margin-top: 0;
  margin-bottom: 20px;
}
</style>
