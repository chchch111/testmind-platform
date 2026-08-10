<template>
  <div class="task-page">
    <div class="page-card">
      <div class="page-header-row">
        <div>
          <h1 class="page-title">测试任务管理</h1>
          <p class="page-desc">先创建任务目录，再在目录下添加子任务（绑定用例集、分配执行人）。</p>
        </div>
        <div class="header-actions">
          <el-button type="primary" @click="openCreateDirDialog">创建目录</el-button>
          <el-button @click="loadDirectories">刷新</el-button>
        </div>
      </div>
    </div>

    <div class="page-card" v-loading="loading">
      <div class="directory-list">
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
              <div class="directory-actions">
                <el-button size="small" type="primary" @click="openAddSubtaskDialog(dir)">添加子任务</el-button>
                <el-button size="small" type="danger" @click="handleDeleteDir(dir)">删除目录</el-button>
              </div>
            </div>

            <el-table :data="dir.subtasks" border size="small" empty-text="该目录下还没有子任务，点击「添加子任务」创建">
              <el-table-column prop="task_id" label="ID" width="80" />
              <el-table-column prop="task_name" label="子任务名称" min-width="200" show-overflow-tooltip />
              <el-table-column label="执行人" min-width="140" show-overflow-tooltip>
                <template #default="{ row }">{{ (row.assignee_names || []).join('、') || '-' }}</template>
              </el-table-column>
              <el-table-column label="通过率" width="160">
                <template #default="{ row }">
                  <el-progress :percentage="row.pass_rate ? Math.round(row.pass_rate * 100) : 0" :stroke-width="8" />
                </template>
              </el-table-column>
              <el-table-column label="已测用例" width="100">
                <template #default="{ row }">{{ row.tested_count || 0 }} / {{ row.total_cases || 0 }}</template>
              </el-table-column>
              <el-table-column label="状态" width="100">
                <template #default="{ row }">
                  <el-tag :type="taskStatusTagType(row.status)">{{ STATUS_TEXT[row.status] || row.status }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="220" fixed="right">
                <template #default="{ row }">
                  <el-button size="small" type="primary" @click="$router.push(`/tasks/${row.task_id}`)">详情</el-button>
                  <el-button size="small" type="warning" :disabled="row.status === 'cancelled' || row.status === 'finished'" @click="handleCancelSubtask(row)">取消</el-button>
                  <el-button size="small" type="danger" @click="handleDeleteSubtask(row)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </template>
        <el-empty v-else description="暂无目录，点击「创建目录」开始" />
      </div>
    </div>

    <!-- 创建目录 -->
    <el-dialog v-model="createDirDialogVisible" title="创建任务目录" width="520px">
      <el-form label-width="90px">
        <el-form-item label="目录名称">
          <el-input v-model="dirForm.task_name" placeholder="例如：摄像头功能回归测试" />
        </el-form-item>
        <el-form-item label="负责人">
          <el-input-number v-model="dirForm.owner_id" :min="1" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="dirForm.description" type="textarea" :rows="3" placeholder="可选" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDirDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="handleCreateDir">创建目录</el-button>
      </template>
    </el-dialog>

    <!-- 添加子任务 -->
    <el-dialog v-model="addSubtaskDialogVisible" title="添加子任务" width="720px">
      <el-form label-width="100px">
        <el-form-item label="所属目录">
          <el-input :model-value="currentDir?.task_name" disabled />
        </el-form-item>
        <el-form-item label="子任务名称">
          <el-input v-model="subtaskForm.task_name" placeholder="例如：夜视红外灯回归用例执行" />
        </el-form-item>
        <el-form-item label="绑定用例集">
          <el-select v-model="subtaskForm.case_set_ids" multiple filterable placeholder="请选择一个或多个用例集" class="wide-select">
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
      </el-form>
      <template #footer>
        <el-button @click="addSubtaskDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="handleCreateSubtask">创建子任务</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { listCaseSets } from '../api/case'
import { cancelTask, createTask, deleteTask, listSubtasks, listTaskDirectories } from '../api/task'
import { STATUS_TEXT } from '../utils/constants'
import { confirmAction, showSuccess, showWarning } from '../utils/message'
import { getCurrentUserId } from '../utils/storage'

const loading = ref(false)
const creating = ref(false)
const createDirDialogVisible = ref(false)
const addSubtaskDialogVisible = ref(false)
const directories = ref([])
const caseSets = ref([])
const currentDir = ref(null)
const assigneeInputValues = ref([String(getCurrentUserId())])

const dirForm = reactive({
  task_name: '',
  description: '',
  owner_id: getCurrentUserId()
})

const subtaskForm = reactive({
  task_name: '',
  case_set_ids: []
})

async function loadDirectories() {
  loading.value = true
  try {
    const result = await listTaskDirectories({ page: 1, page_size: 100 })
    const dirs = result.items || []
    const withSubtasks = await Promise.all(
      dirs.map(async dir => {
        let subtasks = []
        try {
          const subResult = await listSubtasks(dir.task_id, { page: 1, page_size: 100 })
          subtasks = subResult.items || []
        } catch {
          subtasks = []
        }
        return { ...dir, subtasks }
      })
    )
    directories.value = withSubtasks
  } finally {
    loading.value = false
  }
}

async function loadCaseSets() {
  const result = await listCaseSets({ page: 1, page_size: 100, status: 'active' })
  caseSets.value = result.items || []
}

function openCreateDirDialog() {
  dirForm.task_name = ''
  dirForm.description = ''
  dirForm.owner_id = getCurrentUserId()
  createDirDialogVisible.value = true
}

async function handleCreateDir() {
  if (!dirForm.task_name.trim()) {
    showWarning('请填写目录名称')
    return
  }
  creating.value = true
  try {
    await createTask({
      task_name: dirForm.task_name.trim(),
      description: dirForm.description.trim() || null,
      owner_id: dirForm.owner_id,
      parent_id: null,
      case_set_ids: [],
      assignee_ids: [],
      created_by: getCurrentUserId()
    })
    showSuccess('目录创建成功')
    createDirDialogVisible.value = false
    await loadDirectories()
  } finally {
    creating.value = false
  }
}

async function openAddSubtaskDialog(dir) {
  currentDir.value = dir
  subtaskForm.task_name = ''
  subtaskForm.case_set_ids = []
  assigneeInputValues.value = [String(getCurrentUserId())]
  await loadCaseSets()
  addSubtaskDialogVisible.value = true
}

async function handleCreateSubtask() {
  const assigneeIds = normalizeAssigneeIds()
  if (!subtaskForm.task_name.trim()) {
    showWarning('请填写子任务名称')
    return
  }
  if (!subtaskForm.case_set_ids.length) {
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
      task_name: subtaskForm.task_name.trim(),
      parent_id: currentDir.value.task_id,
      owner_id: dirForm.owner_id,
      case_set_ids: subtaskForm.case_set_ids,
      assignee_ids: assigneeIds,
      created_by: getCurrentUserId()
    })
    showSuccess(`子任务创建成功，生成 ${created.total_executions} 条执行记录`)
    addSubtaskDialogVisible.value = false
    await loadDirectories()
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

async function handleCancelSubtask(row) {
  await confirmAction(`确认取消子任务「${row.task_name}」吗？`, '取消子任务')
  await cancelTask(row.task_id)
  showSuccess('子任务已取消')
  await loadDirectories()
}

async function handleDeleteSubtask(row) {
  await confirmAction(`确认删除子任务「${row.task_name}」吗？`, '删除子任务')
  await deleteTask(row.task_id)
  showSuccess('子任务已删除')
  await loadDirectories()
}

async function handleDeleteDir(dir) {
  await confirmAction(`确认删除目录「${dir.task_name}」吗？其下 ${dir.subtask_count} 个子任务不会被级联删除，但目录删除后子任务变为独立任务。`, '删除目录')
  await deleteTask(dir.task_id)
  showSuccess('目录已删除')
  await loadDirectories()
}

function taskStatusTagType(status) {
  if (status === 'finished') return 'success'
  if (status === 'running') return 'warning'
  if (status === 'assigned') return 'info'
  if (status === 'cancelled') return 'danger'
  return 'info'
}

onMounted(() => {
  loadDirectories()
  loadCaseSets()
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
  flex-wrap: wrap;
}

.directory-title strong {
  color: #1f2937;
  font-size: 16px;
}

.directory-meta {
  color: #64748b;
  font-size: 13px;
}

.directory-actions {
  display: flex;
  gap: 8px;
}

.wide-select {
  width: 100%;
}
</style>
