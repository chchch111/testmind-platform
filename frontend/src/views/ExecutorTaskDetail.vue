<template>
  <div class="executor-task-page">
    <div class="page-card editor-header">
      <div>
        <div class="breadcrumb">执行工作台 / {{ parentName || '任务' }} / {{ taskName }}</div>
        <h1 class="page-title">用例执行</h1>
        <p class="page-desc">思维导图展示用例树，点击用例节点弹出状态菜单，标记通过 / 失败 / 阻塞 / 不适用。</p>
      </div>
      <div class="header-actions">
        <el-tag :type="isClaimed ? 'success' : 'warning'">{{ isClaimed ? '已认领' : '待认领' }}</el-tag>
        <el-tag v-if="treeData.length" type="info">用例 {{ totalCases }}</el-tag>
        <el-tag type="success">通过 {{ passedCount }}</el-tag>
        <el-tag type="danger">失败 {{ failedCount }}</el-tag>
        <el-tag type="warning">阻塞 {{ blockedCount }}</el-tag>
        <el-button v-if="!isClaimed" type="primary" @click="handleAssignTask">认领任务</el-button>
        <el-button @click="$router.push('/executor')">返回目录</el-button>
      </div>
    </div>

    <div class="canvas-shell page-card">
      <div class="canvas-toolbar">
        <el-button size="small" @click="expandAll">展开全部</el-button>
        <el-button size="small" @click="collapseAll">收起全部</el-button>
        <span class="mind-tip">点击 case 节点（绿色圆点）标记执行状态；目录节点仅用于分组。</span>
      </div>

      <MindMapCanvas
        :tree-data="treeData"
        :selected-node-id="selectedNodeId"
        :selected-node-ids="selectedNodeIds"
        :node-execution-status-map="statusMap"
        :collapsed-node-ids="collapsedNodeIds"
        :appearance="appearance"
        @select="handleSelect"
        @node-contextmenu="openContextMenu"
        @toggle-collapse="toggleNodeCollapse"
        @zoom-in="zoomIn"
        @zoom-out="zoomOut"
        @reset-view="resetZoom"
      />

      <div v-if="!treeData.length" class="empty-tip">该任务还没有可执行的用例</div>
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
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { assignTask, getSubtaskExecutionTree, listTaskExecutions, updateExecution } from '../api/task'
import ExecutionRadialMenu from '../components/ExecutionRadialMenu.vue'
import MindMapCanvas from '../components/MindMapCanvas.vue'
import { showSuccess, showWarning } from '../utils/message'
import { getCurrentUserId } from '../utils/storage'

const route = useRoute()
const taskId = Number(route.params.id)

const loading = ref(false)
const treeData = ref([])
const statusMap = ref({})
const taskName = ref('')
const parentName = ref('')
const isClaimed = ref(false)
const assignStatus = ref('assigned')
const totalCases = ref(0)
const passedCount = ref(0)
const failedCount = ref(0)
const blockedCount = ref(0)
const selectedNodeId = ref(null)
const selectedNodeIds = ref([])
const collapsedNodeIds = ref([])
const radialVisible = ref(false)
const radialPosition = reactive({ x: 600, y: 360 })
const zoom = ref(1)
const appearance = reactive({
  theme: 'blue',
  rootColor: '#6ea4c8',
  nodeBorderColor: '#8db7d6',
  connectorColor: '#7faed0',
  nodeSize: 'normal',
  showTags: false,
  showMetaIcons: false
})

// node_id → 当前执行人的执行记录（含 execution_id / sync_version）
const nodeToExecution = ref({})

const countedStatus = computed(() => {
  const values = Object.values(statusMap.value)
  return {
    passed: values.filter(v => v === 'passed').length,
    failed: values.filter(v => v === 'failed').length,
    blocked: values.filter(v => v === 'blocked').length
  }
})

async function loadPage() {
  loading.value = true
  try {
    const [treeResult, executions] = await Promise.all([
      getSubtaskExecutionTree(taskId),
      listTaskExecutions(taskId)
    ])
    taskName.value = treeResult.task_name || ''
    parentName.value = treeResult.parent_name || ''
    assignStatus.value = treeResult.assign_status || 'assigned'
    isClaimed.value = assignStatus.value === 'accepted'
    treeData.value = treeResult.tree || []
    // 后端 status_map 键是字符串，转成数字键，与 node.node_id（数字）匹配
    const numericStatusMap = {}
    for (const [key, value] of Object.entries(treeResult.status_map || {})) {
      numericStatusMap[Number(key)] = value
    }
    statusMap.value = numericStatusMap
    totalCases.value = treeResult.total_cases || 0
    passedCount.value = treeResult.passed_count || 0

    // 当前执行人的执行记录映射
    const map = {}
    const currentUserId = getCurrentUserId()
    for (const item of executions || []) {
      if (item.executor_id === currentUserId) {
        map[item.case_node_id] = item
      }
    }
    nodeToExecution.value = map
  } finally {
    loading.value = false
  }
}

function handleSelect(node) {
  selectedNodeId.value = node.node_id
  selectedNodeIds.value = [node.node_id]
}

function openContextMenu(payload) {
  const node = payload.node
  handleSelect(node)
  // 只有 case 节点可以标记执行状态
  if (node.node_type !== 'case') {
    showWarning('目录节点不能标记执行状态')
    return
  }
  radialPosition.x = payload.x
  radialPosition.y = payload.y
  radialVisible.value = true
}

async function handleAssignTask() {
  await assignTask(taskId)
  showSuccess('任务已认领')
  isClaimed.value = true
  assignStatus.value = 'accepted'
}

async function handleRadialAction(action) {
  radialVisible.value = false
  if (action === 'remove' || action === 'note' || action === 'bug') {
    return
  }
  if (!isClaimed.value) {
    showWarning('请先认领任务')
    return
  }
  const nodeId = selectedNodeId.value
  const execution = nodeToExecution.value[nodeId]
  if (!execution) {
    showWarning('未找到对应的执行记录')
    return
  }
  try {
    await updateExecution(execution.execution_id, {
      executor_id: execution.executor_id,
      execution_status: action,
      actual_result: defaultActualResult(action),
      bug_description: action === 'failed' ? '执行失败，实际结果不符合预期。' : null,
      sync_version: execution.sync_version
    })
    // 局部更新 statusMap，不整页重载
    statusMap.value = { ...statusMap.value, [nodeId]: action }
    execution.sync_version += 1
    showSuccess(`已标记为：${statusText(action)}`)
    refreshCounts()
  } catch {
    // 全局拦截器已提示
  }
}

function refreshCounts() {
  const c = countedStatus.value
  passedCount.value = c.passed
  failedCount.value = c.failed
  blockedCount.value = c.blocked
}

function statusText(status) {
  const map = { passed: '通过', failed: '失败', blocked: '阻塞', skipped: '不适用', not_run: '未执行' }
  return map[status] || status
}

function defaultActualResult(status) {
  if (status === 'passed') return '执行通过，实际结果符合预期。'
  if (status === 'failed') return '执行失败，实际结果不符合预期。'
  if (status === 'blocked') return '执行阻塞，当前环境或条件不满足。'
  if (status === 'skipped') return '用例不适用，跳过执行。'
  return '已更新执行记录。'
}

function toggleNodeCollapse(node) {
  if (collapsedNodeIds.value.includes(node.node_id)) {
    collapsedNodeIds.value = collapsedNodeIds.value.filter(id => id !== node.node_id)
  } else {
    collapsedNodeIds.value = [...collapsedNodeIds.value, node.node_id]
  }
}

function expandAll() {
  collapsedNodeIds.value = []
}

function collapseAll() {
  collapsedNodeIds.value = collectNodeIds(treeData.value)
}

function collectNodeIds(nodes, result = []) {
  for (const node of nodes) {
    if (node.children && node.children.length) {
      result.push(node.node_id)
      collectNodeIds(node.children, result)
    }
  }
  return result
}

function zoomIn() {
  zoom.value = Math.min(1.4, Number((zoom.value + 0.1).toFixed(1)))
}

function zoomOut() {
  zoom.value = Math.max(0.6, Number((zoom.value - 0.1).toFixed(1)))
}

function resetZoom() {
  zoom.value = 1
}

onMounted(loadPage)
</script>

<style scoped>
.executor-task-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.editor-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  padding-top: 12px;
  padding-bottom: 12px;
}

.breadcrumb {
  margin-bottom: 10px;
  color: #64748b;
  font-size: 13px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.canvas-shell {
  position: relative;
  padding: 16px;
  min-height: 720px;
}

.canvas-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.mind-tip {
  color: #64748b;
  font-size: 13px;
}

.empty-tip {
  padding: 60px 0;
  text-align: center;
  color: #94a3b8;
}
</style>
