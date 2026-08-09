<template>
  <div class="executor-page">
    <div class="page-card">
      <div class="page-header-row">
        <div>
          <h1 class="page-title">执行工作台</h1>
          <p class="page-desc">输入执行人ID后同步任务，点击执行记录可弹出圆形状态快捷菜单，快速标记通过、失败、阻塞等状态。</p>
        </div>
        <div class="executor-tools">
          <span>执行人ID</span>
          <el-input-number v-model="executorId" :min="1" />
          <el-select v-model="executionFilter" clearable placeholder="全部执行状态" class="status-filter">
            <el-option v-for="option in executionStatusOptions" :key="option.value" :label="option.label" :value="option.value" />
          </el-select>
          <el-button @click="executionFilter = 'failed'">只看失败</el-button>
          <el-button @click="executionFilter = 'blocked'">只看阻塞</el-button>
          <el-button type="primary" :loading="loading" @click="loadExecutorTasks">批量同步任务</el-button>
        </div>
      </div>
    </div>

    <div v-if="tasks.length" class="task-list">
      <div v-for="item in tasks" :key="item.task.task_id" class="page-card task-card">
        <div class="task-header">
          <div>
            <h2>{{ item.task.task_name }}</h2>
            <p>{{ item.task.description || '暂无任务描述' }}</p>
          </div>
          <el-tag type="success">{{ STATUS_TEXT[item.task.status] || item.task.status }}</el-tag>
        </div>

        <div class="execution-summary">
          <el-tag>全部 {{ item.executions.length }}</el-tag>
          <el-tag type="info">未执行 {{ countExecutionStatus(item.executions, 'not_run') }}</el-tag>
          <el-tag type="success">通过 {{ countExecutionStatus(item.executions, 'passed') }}</el-tag>
          <el-tag type="danger">失败 {{ countExecutionStatus(item.executions, 'failed') }}</el-tag>
          <el-tag type="warning">阻塞 {{ countExecutionStatus(item.executions, 'blocked') }}</el-tag>
        </div>

        <el-table :data="filteredExecutions(item.executions)" border @selection-change="rows => handleSelectionChange(item.task.task_id, rows)">
          <el-table-column type="selection" width="48" />
          <el-table-column prop="execution_id" label="执行ID" width="90" />
          <el-table-column prop="case_node_id" label="用例节点ID" width="110" />
          <el-table-column label="执行状态" width="120">
            <template #default="{ row }">
              <el-tag :type="statusTagType(row.execution_status)">{{ EXECUTION_STATUS_TEXT[row.execution_status] || row.execution_status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="actual_result" label="实际结果" min-width="240" />
          <el-table-column prop="bug_description" label="缺陷描述" min-width="200" />
          <el-table-column prop="sync_version" label="同步版本" width="90" />
          <el-table-column label="操作" width="150" fixed="right">
            <template #default="{ row }">
              <el-button size="small" type="primary" @click="openRadialMenu($event, row)">状态菜单</el-button>
            </template>
          </el-table-column>
        </el-table>

        <div class="batch-actions">
          <span>批量修改选中记录：</span>
          <el-button size="small" type="success" @click="batchUpdate(item.task.task_id, 'passed')">通过</el-button>
          <el-button size="small" type="danger" @click="batchUpdate(item.task.task_id, 'failed')">失败</el-button>
          <el-button size="small" type="warning" @click="batchUpdate(item.task.task_id, 'blocked')">阻塞</el-button>
        </div>
      </div>
    </div>

    <div v-else class="page-card">
      <el-empty description="暂无同步任务，请确认后端已有分配给该执行人的任务" />
    </div>

    <ExecutionRadialMenu
      :visible="radialVisible"
      :x="radialPosition.x"
      :y="radialPosition.y"
      @close="radialVisible = false"
      @action="handleRadialAction"
    />
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { getExecutorTasks, updateExecution } from '../api/task'
import ExecutionRadialMenu from '../components/ExecutionRadialMenu.vue'
import { EXECUTION_STATUS_TEXT, STATUS_TEXT } from '../utils/constants'
import { showSuccess, showWarning } from '../utils/message'
import { getCurrentUserId } from '../utils/storage'

const executorId = ref(getCurrentUserId())
const executionFilter = ref('')
const loading = ref(false)
const tasks = ref([])
const selectedRowsMap = reactive({})
const activeExecution = ref(null)
const radialVisible = ref(false)
const radialPosition = reactive({ x: 600, y: 360 })
const executionStatusOptions = [
  { label: '未执行', value: 'not_run' },
  { label: '通过', value: 'passed' },
  { label: '失败', value: 'failed' },
  { label: '阻塞', value: 'blocked' },
  { label: '不适用', value: 'skipped' }
]

async function loadExecutorTasks() {
  loading.value = true
  try {
    tasks.value = await getExecutorTasks(executorId.value)
    showSuccess(`同步完成，共 ${tasks.value.length} 个任务`)
  } finally {
    loading.value = false
  }
}

function handleSelectionChange(taskId, rows) {
  selectedRowsMap[taskId] = rows
}

function filteredExecutions(executions) {
  if (!executionFilter.value) {
    return executions
  }
  return executions.filter(row => row.execution_status === executionFilter.value)
}

function countExecutionStatus(executions, status) {
  return executions.filter(row => row.execution_status === status).length
}

function openRadialMenu(event, row) {
  activeExecution.value = row
  radialPosition.x = event.clientX
  radialPosition.y = event.clientY
  radialVisible.value = true
}

async function handleRadialAction(action) {
  if (!activeExecution.value) {
    return
  }
  if (action === 'remove') {
    radialVisible.value = false
    showWarning('当前演示版不物理移除执行记录，可在后端扩展删除接口。')
    return
  }
  if (action === 'bug') {
    await updateSingleExecution(activeExecution.value, 'failed', activeExecution.value.actual_result || '执行发现缺陷', '通过圆形菜单标记缺陷')
  } else if (action === 'note') {
    await updateSingleExecution(activeExecution.value, activeExecution.value.execution_status, '通过圆形菜单添加备注', activeExecution.value.bug_description)
  } else if (action === 'skipped') {
    await updateSingleExecution(activeExecution.value, 'skipped', '该用例当前不适用，暂按不适用处理', '不适用')
  } else {
    await updateSingleExecution(activeExecution.value, action, defaultActualResult(action), action === 'failed' ? '通过圆形菜单标记失败' : null)
  }
  radialVisible.value = false
}

async function batchUpdate(taskId, status) {
  const rows = selectedRowsMap[taskId] || []
  if (!rows.length) {
    showWarning('请先勾选执行记录')
    return
  }
  let successCount = 0
  for (const row of rows) {
    try {
      await updateExecution(row.execution_id, {
        executor_id: executorId.value,
        execution_status: status,
        actual_result: defaultActualResult(status),
        bug_description: status === 'failed' ? '批量标记失败' : null,
        sync_version: row.sync_version
      })
      successCount += 1
    } catch (error) {
      // 全局拦截器已经提示错误，这里继续处理下一条。
    }
  }
  showSuccess(`批量更新完成，成功 ${successCount} 条`)
  await loadExecutorTasks()
}

async function updateSingleExecution(row, status, actualResult, bugDescription) {
  await updateExecution(row.execution_id, {
    executor_id: executorId.value,
    execution_status: status,
    actual_result: actualResult,
    bug_description: bugDescription,
    sync_version: row.sync_version
  })
  showSuccess(`执行状态已更新为：${EXECUTION_STATUS_TEXT[status] || status}`)
  await loadExecutorTasks()
}

function defaultActualResult(status) {
  if (status === 'passed') return '执行通过，实际结果符合预期。'
  if (status === 'failed') return '执行失败，实际结果不符合预期。'
  if (status === 'blocked') return '执行阻塞，当前环境或条件不满足。'
  if (status === 'skipped') return '用例不适用，跳过执行。'
  return '已更新执行记录。'
}

function statusTagType(status) {
  if (status === 'passed') return 'success'
  if (status === 'failed') return 'danger'
  if (status === 'blocked') return 'warning'
  if (status === 'skipped') return 'info'
  return 'info'
}

onMounted(loadExecutorTasks)
</script>

<style scoped>
.executor-page {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.page-header-row,
.task-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
}

.executor-tools {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}

.status-filter {
  width: 150px;
}

.task-list {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.task-card h2 {
  margin: 0 0 8px;
}

.task-card p {
  margin: 0 0 14px;
  color: #64748b;
}

.execution-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 8px 0 12px;
}

.batch-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 14px;
}
</style>
