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
        <strong>{{ total }}</strong>
      </div>
      <div class="summary-card page-card">
        <span>本页执行中</span>
        <strong>{{ countByStatus('running') }}</strong>
      </div>
      <div class="summary-card page-card">
        <span>本页已分配</span>
        <strong>{{ countByStatus('assigned') }}</strong>
      </div>
      <div class="summary-card page-card">
        <span>本页已完成</span>
        <strong>{{ countByStatus('finished') }}</strong>
      </div>
    </div>

    <div class="page-card">
      <div class="filter-bar">
        <el-input v-model="filters.keyword" clearable placeholder="按任务名称/描述搜索" class="keyword-input" @keyup.enter="search" @clear="search" />
        <el-select v-model="filters.status" clearable placeholder="全部状态" class="filter-select" @change="search">
          <el-option v-for="option in taskStatusOptions" :key="option.value" :label="option.label" :value="option.value" />
        </el-select>
        <el-button @click="resetFilters">重置筛选</el-button>
        <span class="filter-count">共 {{ total }} 条</span>
      </div>
      <el-table v-loading="loading" :data="tasks" border>
        <el-table-column prop="task_id" label="ID" width="80" />
        <el-table-column prop="task_name" label="任务名称" min-width="220" />
        <el-table-column prop="description" label="任务描述" min-width="260" show-overflow-tooltip />
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="taskStatusTagType(row.status)">{{ STATUS_TEXT[row.status] || row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="开始时间" width="190">
          <template #default="{ row }">{{ formatDateTime(row.start_time) }}</template>
        </el-table-column>
        <el-table-column label="结束时间" width="190">
          <template #default="{ row }">{{ formatDateTime(row.end_time) }}</template>
        </el-table-column>
        <el-table-column label="创建时间" width="190">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" @click="$router.push(`/tasks/${row.task_id}`)">详情</el-button>
            <el-button size="small" @click="$router.push('/executor')">执行工作台</el-button>
            <el-button size="small" type="warning" :disabled="row.status === 'cancelled' || row.status === 'finished'" @click="handleCancelTask(row)">取消</el-button>
            <el-button size="small" type="danger" @click="handleDeleteTask(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination
        class="pager"
        background
        layout="prev, pager, next, total"
        :total="total"
        :page-size="pageSize"
        v-model:current-page="page"
      />
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
import { onMounted, reactive, ref, watch } from 'vue'
import { listCaseSets } from '../api/case'
import { cancelTask, createTask, deleteTask, listTasks } from '../api/task'
import { STATUS_TEXT } from '../utils/constants'
import { formatDateTime } from '../utils/format'
import { confirmAction, showSuccess, showWarning } from '../utils/message'
import { getCurrentUserId } from '../utils/storage'

const loading = ref(false)
const creating = ref(false)
const createDialogVisible = ref(false)
const tasks = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const caseSets = ref([])
const assigneeInputValues = ref([String(getCurrentUserId())])
const dateRange = ref([])
const filters = reactive({ keyword: '', status: '' })
const createForm = reactive({
  task_name: '',
  description: '',
  case_set_ids: []
})

const taskStatusOptions = ['assigned', 'running', 'finished', 'cancelled'].map(value => ({ value, label: STATUS_TEXT[value] || value }))

async function loadTasks() {
  loading.value = true
  try {
    const result = await listTasks({
      page: page.value,
      page_size: pageSize.value,
      keyword: filters.keyword.trim() || undefined,
      status: filters.status || undefined
    })
    tasks.value = Array.isArray(result) ? result : result.items || []
    total.value = Array.isArray(result) ? result.length : result.total || 0
  } finally {
    loading.value = false
  }
}

function search() {
  page.value = 1
  loadTasks()
}

watch(page, () => {
  loadTasks()
})

async function loadCaseSets() {
  const result = await listCaseSets({ page: 1, page_size: 100, status: 'active' })
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

async function handleCancelTask(row) {
  await confirmAction(`确认取消任务「${row.task_name}」吗？取消后任务状态将变为已取消。`, '取消测试任务')
  await cancelTask(row.task_id)
  showSuccess('测试任务已取消')
  await loadTasks()
}

async function handleDeleteTask(row) {
  await confirmAction(`确认删除任务「${row.task_name}」吗？删除后任务将不再出现在列表中。`, '删除测试任务')
  await deleteTask(row.task_id)
  showSuccess('测试任务已删除')
  await loadTasks()
}

function resetFilters() {
  filters.keyword = ''
  filters.status = ''
  search()
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

.pager {
  margin-top: 16px;
  justify-content: flex-end;
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

.filter-bar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 14px;
}

.keyword-input {
  width: 260px;
}

.filter-select {
  width: 150px;
}

.filter-count {
  color: #64748b;
  font-size: 13px;
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
