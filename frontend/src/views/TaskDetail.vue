<template>
  <div class="task-detail-page">
    <div class="page-card">
      <div class="page-header-row">
        <div>
          <h1 class="page-title">测试任务详情</h1>
          <p class="page-desc">查看任务绑定范围、执行人分配、通过/失败/阻塞统计和执行记录明细。</p>
        </div>
        <div class="header-actions">
          <el-button @click="$router.push('/tasks')">返回任务列表</el-button>
          <el-button type="primary" :loading="loading" @click="loadDetail">刷新</el-button>
          <el-button type="success" @click="$router.push('/executor')">进入执行工作台</el-button>
          <el-button type="warning" :loading="reportLoading" :disabled="!task" @click="openReport">查看报告</el-button>
          <el-button type="warning" :disabled="!task || task.status === 'cancelled' || task.status === 'finished'" @click="handleCancelTask">取消任务</el-button>
          <el-button type="danger" :disabled="!task" @click="handleDeleteTask">删除任务</el-button>
        </div>
      </div>
    </div>

    <div v-loading="loading" class="detail-content">
      <template v-if="task">
        <div class="summary-grid">
          <div class="summary-card page-card">
            <span>执行总数</span>
            <strong>{{ task.total_executions }}</strong>
          </div>
          <div class="summary-card page-card success-card">
            <span>通过</span>
            <strong>{{ task.passed_count }}</strong>
          </div>
          <div class="summary-card page-card danger-card">
            <span>失败</span>
            <strong>{{ task.failed_count }}</strong>
          </div>
          <div class="summary-card page-card warning-card">
            <span>阻塞</span>
            <strong>{{ task.blocked_count }}</strong>
          </div>
          <div class="summary-card page-card info-card">
            <span>未执行</span>
            <strong>{{ task.not_run_count }}</strong>
          </div>
        </div>

        <div class="page-card detail-card">
          <div class="task-title-row">
            <div>
              <h2>#{{ task.task_id }} {{ task.task_name }}</h2>
              <p>{{ task.description || '暂无任务描述' }}</p>
            </div>
            <el-tag size="large" :type="taskStatusTagType(task.status)">{{ STATUS_TEXT[task.status] || task.status }}</el-tag>
          </div>

          <el-progress :percentage="progressPercent" :stroke-width="14" />

          <el-descriptions :column="2" border>
            <el-descriptions-item label="创建人ID">{{ task.created_by }}</el-descriptions-item>
            <el-descriptions-item label="更新人ID">{{ task.updated_by || '-' }}</el-descriptions-item>
            <el-descriptions-item label="开始时间">{{ formatDateTime(task.start_time) }}</el-descriptions-item>
            <el-descriptions-item label="结束时间">{{ formatDateTime(task.end_time) }}</el-descriptions-item>
            <el-descriptions-item label="创建时间">{{ formatDateTime(task.created_at) }}</el-descriptions-item>
            <el-descriptions-item label="更新时间">{{ formatDateTime(task.updated_at) }}</el-descriptions-item>
          </el-descriptions>

          <div class="tag-section">
            <div>
              <span class="section-label">绑定用例集</span>
              <el-tag v-for="caseSetId in task.case_set_ids" :key="caseSetId" type="info">#{{ caseSetId }}</el-tag>
            </div>
            <div>
              <span class="section-label">执行人</span>
              <el-tag v-for="assigneeId in task.assignee_ids" :key="assigneeId" type="success">用户 {{ assigneeId }}</el-tag>
            </div>
          </div>
        </div>

        <div class="page-card">
          <div class="table-toolbar">
            <div>
              <h2>执行记录</h2>
              <p>可按执行人和执行状态筛选，也可以直接在详情页快速更新执行结果。</p>
            </div>
            <div class="filter-tools">
              <el-button type="primary" @click="exportExecutionCsv">导出CSV</el-button>
              <el-select v-model="filters.executorId" clearable placeholder="全部执行人" class="filter-select">
                <el-option v-for="executorId in executorOptions" :key="executorId" :label="`用户 ${executorId}`" :value="executorId" />
              </el-select>
              <el-select v-model="filters.status" clearable placeholder="全部状态" class="filter-select">
                <el-option v-for="option in executionStatusOptions" :key="option.value" :label="option.label" :value="option.value" />
              </el-select>
            </div>
          </div>

          <el-table :data="filteredExecutions" border>
            <el-table-column prop="execution_id" label="执行ID" width="90" />
            <el-table-column label="用例节点" min-width="180" show-overflow-tooltip>
              <template #default="{ row }">
                <span v-if="row.case_node_title">{{ row.case_node_title }}</span>
                <span v-else>#{{ row.case_node_id }}</span>
                <el-tag v-if="row.case_node_deleted" size="small" type="danger" class="deleted-tag">已删除</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="executor_id" label="执行人ID" width="110" />
            <el-table-column label="执行状态" width="120">
              <template #default="{ row }">
                <el-tag :type="executionStatusTagType(row.execution_status)">{{ EXECUTION_STATUS_TEXT[row.execution_status] || row.execution_status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="actual_result" label="实际结果" min-width="240" show-overflow-tooltip />
            <el-table-column prop="bug_description" label="缺陷描述" min-width="220" show-overflow-tooltip />
            <el-table-column label="同步状态" width="110">
              <template #default="{ row }">
                <el-tag :type="row.sync_status === 'synced' ? 'success' : 'danger'">{{ row.sync_status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="sync_version" label="版本" width="80" />
            <el-table-column prop="executed_at" label="执行时间" width="190">
              <template #default="{ row }">{{ formatDateTime(row.executed_at) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="120" fixed="right">
              <template #default="{ row }">
                <el-button size="small" type="primary" @click="openExecutionDialog(row)">更新</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </template>

      <div v-else class="page-card">
        <el-empty description="未找到任务详情" />
      </div>
    </div>

    <el-dialog v-model="executionDialogVisible" title="更新执行记录" width="620px">
      <el-form label-width="90px">
        <el-form-item label="执行状态">
          <el-radio-group v-model="executionForm.execution_status">
            <el-radio-button label="not_run">未执行</el-radio-button>
            <el-radio-button label="passed">通过</el-radio-button>
            <el-radio-button label="failed">失败</el-radio-button>
            <el-radio-button label="blocked">阻塞</el-radio-button>
            <el-radio-button label="skipped">不适用</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="实际结果">
          <el-input v-model="executionForm.actual_result" type="textarea" :rows="3" placeholder="填写实际执行结果" />
        </el-form-item>
        <el-form-item label="缺陷描述">
          <el-input v-model="executionForm.bug_description" type="textarea" :rows="3" placeholder="失败或阻塞时填写缺陷、环境或前置条件问题" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="executionDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="updating" @click="handleUpdateExecution">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="reportVisible" title="测试报告" width="820px">
      <template v-if="report">
        <div class="report-overview">
          <div class="report-stat"><span>总用例</span><strong>{{ report.total }}</strong></div>
          <div class="report-stat success-stat"><span>通过</span><strong>{{ report.passed }}</strong></div>
          <div class="report-stat danger-stat"><span>失败</span><strong>{{ report.failed }}</strong></div>
          <div class="report-stat warning-stat"><span>阻塞</span><strong>{{ report.blocked }}</strong></div>
          <div class="report-stat info-stat"><span>未执行</span><strong>{{ report.not_run }}</strong></div>
          <div class="report-stat"><span>通过率</span><strong>{{ (report.pass_rate * 100).toFixed(1) }}%</strong></div>
        </div>

        <h3 class="report-section-title">按执行人统计</h3>
        <el-table :data="report.per_executor" border size="small">
          <el-table-column prop="executor_id" label="执行人ID" width="110" />
          <el-table-column prop="total" label="总数" width="80" />
          <el-table-column label="通过" width="90">
            <template #default="{ row }"><span class="success-text">{{ row.passed }}</span></template>
          </el-table-column>
          <el-table-column label="失败" width="90">
            <template #default="{ row }"><span class="danger-text">{{ row.failed }}</span></template>
          </el-table-column>
          <el-table-column label="阻塞" width="90">
            <template #default="{ row }"><span class="warning-text">{{ row.blocked }}</span></template>
          </el-table-column>
          <el-table-column label="通过率">
            <template #default="{ row }">{{ row.total ? ((row.passed / row.total) * 100).toFixed(1) : 0 }}%</template>
          </el-table-column>
        </el-table>

        <h3 class="report-section-title">缺陷汇总（{{ report.defects.length }} 条）</h3>
        <el-table v-if="report.defects.length" :data="report.defects" border size="small">
          <el-table-column label="用例节点" min-width="180" show-overflow-tooltip>
            <template #default="{ row }">{{ row.case_node_title || `#${row.case_node_id}` }}</template>
          </el-table-column>
          <el-table-column label="优先级" width="90">
            <template #default="{ row }">{{ row.case_node_priority || '-' }}</template>
          </el-table-column>
          <el-table-column label="执行人" width="90">
            <template #default="{ row }">{{ row.executor_id }}</template>
          </el-table-column>
          <el-table-column label="状态" width="80">
            <template #default="{ row }">
              <el-tag :type="row.execution_status === 'failed' ? 'danger' : 'warning'">{{ row.execution_status === 'failed' ? '失败' : '阻塞' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="bug_description" label="缺陷描述" min-width="200" show-overflow-tooltip />
        </el-table>
        <el-empty v-else description="暂无缺陷" />
      </template>
      <template #footer>
        <el-button @click="reportVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { cancelTask, deleteTask, getTaskDetail, getTaskReport, listTaskExecutions, updateExecution } from '../api/task'
import { EXECUTION_STATUS_TEXT, STATUS_TEXT } from '../utils/constants'
import { confirmAction, showSuccess, showWarning } from '../utils/message'

const route = useRoute()
const router = useRouter()
const taskId = Number(route.params.id)
const loading = ref(false)
const updating = ref(false)
const reportLoading = ref(false)
const reportVisible = ref(false)
const report = ref(null)
const task = ref(null)
const executions = ref([])
const executionDialogVisible = ref(false)
const activeExecution = ref(null)
const filters = reactive({
  executorId: null,
  status: ''
})
const executionForm = reactive({
  execution_status: 'not_run',
  actual_result: '',
  bug_description: ''
})

const executionStatusOptions = [
  { label: '未执行', value: 'not_run' },
  { label: '通过', value: 'passed' },
  { label: '失败', value: 'failed' },
  { label: '阻塞', value: 'blocked' },
  { label: '不适用', value: 'skipped' }
]

const progressPercent = computed(() => {
  if (!task.value?.total_executions) {
    return 0
  }
  const finishedCount = task.value.total_executions - task.value.not_run_count
  return Math.round((finishedCount / task.value.total_executions) * 100)
})

const executorOptions = computed(() => Array.from(new Set(executions.value.map(item => item.executor_id))))
const filteredExecutions = computed(() => executions.value.filter(item => {
  const executorMatches = !filters.executorId || item.executor_id === filters.executorId
  const statusMatches = !filters.status || item.execution_status === filters.status
  return executorMatches && statusMatches
}))

async function loadDetail() {
  loading.value = true
  try {
    const [taskDetail, executionList] = await Promise.all([
      getTaskDetail(taskId),
      listTaskExecutions(taskId)
    ])
    task.value = taskDetail
    executions.value = executionList
  } finally {
    loading.value = false
  }
}

async function openReport() {
  reportLoading.value = true
  try {
    report.value = await getTaskReport(taskId)
    reportVisible.value = true
  } finally {
    reportLoading.value = false
  }
}

async function handleCancelTask() {
  if (!task.value) {
    return
  }
  await confirmAction(`确认取消任务「${task.value.task_name}」吗？`, '取消测试任务')
  await cancelTask(taskId)
  showSuccess('测试任务已取消')
  await loadDetail()
}

async function handleDeleteTask() {
  if (!task.value) {
    return
  }
  await confirmAction(`确认删除任务「${task.value.task_name}」吗？删除后任务将不再出现在列表中。`, '删除测试任务')
  await deleteTask(taskId)
  showSuccess('测试任务已删除')
  router.replace('/tasks')
}

function openExecutionDialog(row) {
  activeExecution.value = row
  executionForm.execution_status = row.execution_status
  executionForm.actual_result = row.actual_result || ''
  executionForm.bug_description = row.bug_description || ''
  executionDialogVisible.value = true
}

async function handleUpdateExecution() {
  if (!activeExecution.value) {
    showWarning('请先选择一条执行记录')
    return
  }
  updating.value = true
  try {
    await updateExecution(activeExecution.value.execution_id, {
      executor_id: activeExecution.value.executor_id,
      execution_status: executionForm.execution_status,
      actual_result: executionForm.actual_result.trim() || null,
      bug_description: executionForm.bug_description.trim() || null,
      sync_version: activeExecution.value.sync_version
    })
    showSuccess('执行记录已更新')
    executionDialogVisible.value = false
    await loadDetail()
  } finally {
    updating.value = false
  }
}

function taskStatusTagType(status) {
  if (status === 'finished') return 'success'
  if (status === 'running') return 'warning'
  if (status === 'assigned') return 'info'
  if (status === 'cancelled') return 'danger'
  return 'info'
}

function executionStatusTagType(status) {
  if (status === 'passed') return 'success'
  if (status === 'failed') return 'danger'
  if (status === 'blocked') return 'warning'
  if (status === 'skipped') return 'info'
  return 'info'
}

function exportExecutionCsv() {
  if (!task.value || !filteredExecutions.value.length) {
    showWarning('当前没有可导出的执行记录')
    return
  }
  const rows = [
    ['任务ID', '任务名称', '任务状态', '执行ID', '用例节点', '用例节点ID', '优先级', '执行人ID', '执行状态', '实际结果', '缺陷描述', '同步状态', '同步版本', '执行时间', '创建时间'],
    ...filteredExecutions.value.map(row => [
      task.value.task_id,
      task.value.task_name,
      STATUS_TEXT[task.value.status] || task.value.status,
      row.execution_id,
      row.case_node_title || `#${row.case_node_id}`,
      row.case_node_id,
      row.case_node_priority || '',
      row.executor_id,
      EXECUTION_STATUS_TEXT[row.execution_status] || row.execution_status,
      row.actual_result || '',
      row.bug_description || '',
      row.sync_status,
      row.sync_version,
      formatDateTime(row.executed_at),
      formatDateTime(row.created_at)
    ])
  ]
  const csvContent = rows.map(row => row.map(escapeCsvCell).join(',')).join('\n')
  const blob = new Blob([`﻿${csvContent}`], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = `测试任务_${task.value.task_id}_执行报告.csv`
  link.click()
  URL.revokeObjectURL(link.href)
  showSuccess(`已导出 ${filteredExecutions.value.length} 条执行记录`)
}

function escapeCsvCell(value) {
  const text = String(value ?? '')
  if (/[",\n\r]/.test(text)) {
    return `"${text.replace(/"/g, '""')}"`
  }
  return text
}

function formatDateTime(value) {
  if (!value) {
    return '-'
  }
  return String(value).replace('T', ' ').slice(0, 19)
}

onMounted(loadDetail)
</script>

<style scoped>
.task-detail-page,
.detail-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.page-header-row,
.task-title-row,
.table-toolbar {
  display: flex;
  justify-content: space-between;
  gap: 16px;
}

.header-actions,
.filter-tools,
.tag-section,
.tag-section > div {
  display: flex;
  align-items: center;
  gap: 8px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
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

.success-card strong {
  color: #16a34a;
}

.danger-card strong {
  color: #dc2626;
}

.warning-card strong {
  color: #d97706;
}

.info-card strong {
  color: #2563eb;
}

.detail-card {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.task-title-row h2,
.table-toolbar h2 {
  margin: 0 0 8px;
}

.task-title-row p,
.table-toolbar p {
  margin: 0;
  color: #64748b;
}

.tag-section {
  flex-wrap: wrap;
  justify-content: space-between;
}

.section-label {
  color: #475569;
  font-weight: 700;
}

.filter-select {
  width: 150px;
}

.report-overview {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 18px;
}

.report-stat {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 12px;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  background: #f8fafc;
}

.report-stat span {
  color: #64748b;
  font-size: 13px;
}

.report-stat strong {
  color: #1f2937;
  font-size: 22px;
}

.report-stat.success-stat strong { color: #16a34a; }
.report-stat.danger-stat strong { color: #dc2626; }
.report-stat.warning-stat strong { color: #d97706; }
.report-stat.info-stat strong { color: #2563eb; }

.report-section-title {
  margin: 18px 0 10px;
  color: #334155;
  font-size: 16px;
}

.success-text { color: #16a34a; font-weight: 700; }
.danger-text { color: #dc2626; font-weight: 700; }
.warning-text { color: #d97706; font-weight: 700; }

.deleted-tag {
  margin-left: 6px;
}
</style>
