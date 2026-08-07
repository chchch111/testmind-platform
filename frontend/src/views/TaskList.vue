<template>
  <div class="task-page">
    <div class="page-card">
      <div class="page-header-row">
        <div>
          <h1 class="page-title">测试任务管理</h1>
          <p class="page-desc">创建测试任务、绑定用例集、分配执行人，并跟踪执行进度。</p>
        </div>
        <div class="header-actions">
          <el-button type="primary" @click="openCreateDialog">创建测试任务</el-button>
          <el-button @click="loadTasks">刷新</el-button>
        </div>
      </div>
    </div>

    <div class="summary-grid">
      <div class="summary-card page-card">
        <span>任务总数</span>
        <strong>{{ tasks.length }}</strong>
      </div>
      <div class="summary-card page-card">
        <span>执行中</span>
        <strong>{{ countByStatus('running') }}</strong>
      </div>
      <div class="summary-card page-card">
        <span>已分配</span>
        <strong>{{ countByStatus('assigned') }}</strong>
      </div>
      <div class="summary-card page-card">
        <span>已完成</span>
        <strong>{{ countByStatus('finished') }}</strong>
      </div>
    </div>

    <div class="page-card">
      <el-table v-loading="loading" :data="tasks" border>
        <el-table-column prop="task_id" label="ID" width="80" />
        <el-table-column prop="task_name" label="任务名称" min-width="220" />
        <el-table-column prop="description" label="任务描述" min-width="260" show-overflow-tooltip />
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="taskStatusTagType(row.status)">{{ STATUS_TEXT[row.status] || row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="start_time" label="开始时间" width="190" />
        <el-table-column prop="end_time" label="结束时间" width="190" />
        <el-table-column prop="created_at" label="创建时间" width="190" />
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" @click="$router.push(`/tasks/${row.task_id}`)">详情</el-button>
            <el-button size="small" @click="$router.push('/executor')">执行工作台</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="createDialogVisible" title="创建测试任务" width="720px">
      <el-form label-width="100px">
        <el-form-item label="任务名称">
          <el-input v-model="createForm.task_name" placeholder="例如：夜视功能回归测试任务" />
        </el-form-item>
        <el-form-item label="任务描述">
          <el-input v-model="createForm.description" type="textarea" :rows="3" placeholder="请输入本次测试目标、范围或注意事项" />
        </el-form-item>
        <el-form-item label="绑定用例集">
          <el-select v-model="createForm.case_set_ids" multiple filterable placeholder="请选择一个或多个用例集" class="wide-select">
            <el-option
              v-for="caseSet in caseSets"
              :key="caseSet.case_set_id"
              :label="`#${caseSet.case_set_id} ${caseSet.name}`"
              :value="caseSet.case_set_id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="执行人ID">
          <el-select
            v-model="assigneeInputValues"
            multiple
            filterable
            allow-create
            default-first-option
            placeholder="输入执行人ID后回车，例如 1、2、3"
            class="wide-select"
          />
        </el-form-item>
        <el-form-item label="起止时间">
          <el-date-picker
            v-model="dateRange"
            type="datetimerange"
            range-separator="至"
            start-placeholder="开始时间"
            end-placeholder="结束时间"
            value-format="YYYY-MM-DDTHH:mm:ss"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="handleCreateTask">创建任务</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { listCaseSets } from '../api/case'
import { createTask, listTasks } from '../api/task'
import { STATUS_TEXT } from '../utils/constants'
import { showSuccess, showWarning } from '../utils/message'
import { getCurrentUserId } from '../utils/storage'

const loading = ref(false)
const creating = ref(false)
const createDialogVisible = ref(false)
const tasks = ref([])
const caseSets = ref([])
const assigneeInputValues = ref([String(getCurrentUserId())])
const dateRange = ref([])
const createForm = reactive({
  task_name: '',
  description: '',
  case_set_ids: []
})

async function loadTasks() {
  loading.value = true
  try {
    tasks.value = await listTasks({ page: 1, page_size: 100 })
  } finally {
    loading.value = false
  }
}

async function loadCaseSets() {
  const result = await listCaseSets({ page: 1, page_size: 100 })
  caseSets.value = result.items || []
}

async function openCreateDialog() {
  resetCreateForm()
  await loadCaseSets()
  createDialogVisible.value = true
}

function resetCreateForm() {
  createForm.task_name = ''
  createForm.description = ''
  createForm.case_set_ids = []
  assigneeInputValues.value = [String(getCurrentUserId())]
  dateRange.value = []
}

async function handleCreateTask() {
  const assigneeIds = normalizeAssigneeIds()
  if (!createForm.task_name.trim()) {
    showWarning('请填写任务名称')
    return
  }
  if (!createForm.case_set_ids.length) {
    showWarning('请至少选择一个用例集')
    return
  }
  if (!assigneeIds.length) {
    showWarning('请至少填写一个执行人ID')
    return
  }

  creating.value = true
  try {
    const created = await createTask({
      task_name: createForm.task_name.trim(),
      description: createForm.description.trim() || null,
      case_set_ids: createForm.case_set_ids,
      assignee_ids: assigneeIds,
      start_time: dateRange.value?.[0] || null,
      end_time: dateRange.value?.[1] || null,
      created_by: getCurrentUserId()
    })
    showSuccess(`测试任务创建成功，生成 ${created.total_executions} 条执行记录`)
    createDialogVisible.value = false
    await loadTasks()
  } finally {
    creating.value = false
  }
}

function normalizeAssigneeIds() {
  return Array.from(new Set(
    assigneeInputValues.value
      .map(value => Number(String(value).trim()))
      .filter(value => Number.isInteger(value) && value > 0)
  ))
}

function countByStatus(status) {
  return tasks.value.filter(task => task.status === status).length
}

function taskStatusTagType(status) {
  if (status === 'finished') return 'success'
  if (status === 'running') return 'warning'
  if (status === 'assigned') return 'info'
  if (status === 'cancelled') return 'danger'
  return 'info'
}

onMounted(async () => {
  await Promise.all([loadTasks(), loadCaseSets()])
})
</script>

<style scoped>
.task-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.page-header-row {
  display: flex;
  justify-content: space-between;
  gap: 16px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.summary-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.summary-card span {
  color: #64748b;
  font-size: 13px;
}

.summary-card strong {
  color: #1f2937;
  font-size: 28px;
}

.wide-select {
  width: 100%;
}
</style>
