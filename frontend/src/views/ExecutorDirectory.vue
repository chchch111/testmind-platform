<template>
  <div class="executor-directory-page">
    <div class="page-card">
      <div class="page-header-row">
        <div>
          <h1 class="page-title">执行工作台</h1>
          <p class="page-desc">按任务目录查看分配给你的子任务，点击「进入执行」用思维导图标记用例执行状态。</p>
        </div>
        <div class="header-actions">
          <span class="executor-label">执行人ID</span>
          <el-input-number v-model="executorId" :min="1" />
          <el-button type="primary" :loading="loading" @click="loadDirectories">刷新任务</el-button>
        </div>
      </div>
    </div>

    <div class="page-card">
      <div class="directory-list" v-loading="loading">
        <template v-if="directories.length">
          <div v-for="dir in directories" :key="dir.task_id" class="directory-block">
            <div class="directory-head">
              <div class="directory-title">
                <el-tag type="info" size="small">目录</el-tag>
                <strong>{{ dir.task_name }}</strong>
                <span class="directory-meta">
                  负责人：{{ dir.owner_name || '-' }} · 子任务 {{ dir.subtask_count }} 个 · 通过率 {{ (dir.pass_rate * 100).toFixed(1) }}%（已测 {{ dir.tested_count }}/{{ dir.total_cases }}）
                </span>
              </div>
              <el-tag :type="directoryStatusType(dir)">{{ directoryStatusText(dir) }}</el-tag>
            </div>

            <el-table :data="dir.subtasks" border empty-text="该目录下还没有子任务">
              <el-table-column prop="task_id" label="任务ID" width="90" />
              <el-table-column prop="task_name" label="子任务名称" min-width="200" show-overflow-tooltip />
              <el-table-column prop="dir_name" label="目录名称" min-width="160" show-overflow-tooltip>
                <template #default="{ row }">{{ dir.task_name }}</template>
              </el-table-column>
              <el-table-column label="负责人" width="120">
                <template #default="{ row }">{{ row.owner_name || '-' }}</template>
              </el-table-column>
              <el-table-column label="执行人" min-width="140" show-overflow-tooltip>
                <template #default="{ row }">{{ (row.assignee_names || []).join('、') || '-' }}</template>
              </el-table-column>
              <el-table-column label="通过率" width="180">
                <template #default="{ row }">
                  <div class="rate-cell">
                    <el-progress :percentage="row.pass_rate ? Math.round(row.pass_rate * 100) : 0" :stroke-width="8" />
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="已测用例" width="120">
                <template #default="{ row }">{{ row.tested_count || 0 }} / {{ row.total_cases || 0 }}</template>
              </el-table-column>
              <el-table-column label="操作" width="110" fixed="right">
                <template #default="{ row }">
                  <el-button size="small" type="primary" @click="$router.push(`/executor/tasks/${row.task_id}`)">进入执行</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </template>
        <el-empty v-else description="暂无任务，请确认该执行人已被分配任务" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { listSubtasks, listTaskDirectories } from '../api/task'
import { getCurrentUserId } from '../utils/storage'
import { showSuccess } from '../utils/message'

const executorId = ref(getCurrentUserId())
const loading = ref(false)
const directories = ref([])

async function loadDirectories() {
  loading.value = true
  try {
    const result = await listTaskDirectories({ page: 1, page_size: 100 })
    const dirs = result.items || []
    // 并行加载每个目录的子任务（限定当前执行人）
    const withSubtasks = await Promise.all(
      dirs.map(async dir => {
        let subtasks = []
        try {
          const subResult = await listSubtasks(dir.task_id, {
            page: 1,
            page_size: 100,
            executor_id: executorId.value
          })
          subtasks = (subResult.items || []).map(item => ({
            ...item,
            dir_name: dir.task_name
          }))
        } catch {
          subtasks = []
        }
        return { ...dir, subtasks }
      })
    )
    directories.value = withSubtasks
    showSuccess(`同步完成，共 ${directories.value.length} 个目录`)
  } finally {
    loading.value = false
  }
}

function directoryStatusType(dir) {
  if (dir.subtask_count === 0) return 'info'
  if (dir.pass_rate === 1) return 'success'
  if (dir.tested_count > 0) return 'warning'
  return 'info'
}

function directoryStatusText(dir) {
  if (dir.subtask_count === 0) return '空目录'
  if (dir.pass_rate === 1 && dir.tested_count === dir.total_cases) return '已完成'
  if (dir.tested_count > 0) return '执行中'
  return '未开始'
}

onMounted(loadDirectories)
</script>

<style scoped>
.executor-directory-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.page-header-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.executor-label {
  color: #475569;
  font-weight: 700;
}

.directory-list {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.directory-block {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 14px;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  background: #f8fafc;
}

.directory-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.directory-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.directory-title strong {
  color: #1f2937;
  font-size: 16px;
}

.directory-meta {
  color: #64748b;
  font-size: 13px;
}

.rate-cell {
  min-width: 120px;
}
</style>
