<template>
  <div class="executor-task-page">
    <div class="page-card editor-header">
      <div>
        <div class="breadcrumb">执行工作台 / {{ parentName || '任务' }} / {{ taskName }}</div>
        <h1 class="page-title">用例执行</h1>
        <p class="page-desc">思维导图展示全部执行人的用例执行进度，点击用例节点弹出状态菜单标记通过 / 失败 / 阻塞 / 不适用（仅标记自己认领的用例）。</p>
      </div>
      <div class="header-actions">
        <el-tag type="info" v-if="assigneeNames.length">执行人：{{ assigneeNames.join('、') }}</el-tag>
        <el-tag :type="isClaimed ? 'success' : 'warning'">{{ isClaimed ? '已认领' : '待认领' }}</el-tag>
        <el-tag v-if="treeData.length" type="info">用例 {{ totalCases }}</el-tag>
        <el-tag type="success">通过 {{ passedCount }}</el-tag>
        <el-tag type="danger">失败 {{ failedCount }}</el-tag>
        <el-tag type="warning">阻塞 {{ blockedCount }}</el-tag>
        <el-tag type="info">不适用 {{ skippedCount }}</el-tag>
        <el-tag type="info" effect="plain">未测 {{ notRunCount }}</el-tag>
        <el-button v-if="!isClaimed" type="primary" @click="handleAssignTask">认领任务</el-button>
        <el-button @click="$router.push('/executor')">返回目录</el-button>
      </div>
    </div>

    <div class="page-card progress-card" v-if="totalCases > 0">
      <div class="progress-head">
        <span class="progress-label">执行进度</span>
        <span class="progress-text">{{ testedCount }} / {{ totalCases }} 已测 · {{ progressPercent }}%</span>
      </div>
      <div class="stacked-progress" :style="{ '--total': totalCases }">
        <div
          v-for="item in statusProgress"
          :key="item.label"
          class="stacked-segment"
          :style="{ width: item.percent + '%', background: item.color }"
          :title="`${item.label} ${item.value} 条`"
        />
      </div>
      <div class="progress-legend">
        <span v-for="item in statusProgress" :key="item.label" class="legend-item">
          <i class="legend-dot" :style="{ background: item.color }" />
          {{ item.label }} {{ item.value }}
        </span>
        <span v-if="notRunCount > 0" class="legend-item">
          <i class="legend-dot" style="background: #e5e7eb" />
          未测 {{ notRunCount }}
        </span>
      </div>
    </div>

    <div class="canvas-shell page-card">
      <div class="canvas-toolbar">
        <el-button size="small" @click="expandAll">展开全部</el-button>
        <el-button size="small" @click="collapseAll">收起全部</el-button>
        <el-divider direction="vertical" />
        <span class="filter-label">优先级</span>
        <el-select v-model="priorityFilter" size="small" clearable placeholder="全部" class="filter-select" @change="handleFilterChange">
          <el-option label="P0 高危" value="P0" />
          <el-option label="P1 重要" value="P1" />
          <el-option label="P2 一般" value="P2" />
          <el-option label="P3 较低" value="P3" />
        </el-select>
        <span class="filter-label">执行状态</span>
        <el-select v-model="statusFilter" size="small" clearable placeholder="全部" class="filter-select" @change="handleFilterChange">
          <el-option label="未执行" value="not_run" />
          <el-option label="通过" value="passed" />
          <el-option label="失败" value="failed" />
          <el-option label="阻塞" value="blocked" />
          <el-option label="不适用" value="skipped" />
        </el-select>
        <span class="mind-tip">点击 case 节点（绿色圆点）标记执行状态；目录节点仅用于分组。</span>
      </div>

      <MindMapCanvas
        ref="mindMapCanvasRef"
        :tree-data="filteredTreeData"
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
        @box-select="handleBoxSelect"
        @box-select-preview="handleBoxSelect"
        @viewport-change="handleViewportChange"
      />

      <div v-if="!filteredTreeData.length" class="empty-tip">{{ treeData.length ? '没有符合筛选条件的用例' : '该任务还没有可执行的用例' }}</div>

      <div class="mini-map" title="拖动框选可移动视野，点击可定位">
        <svg v-if="miniMapLayout.nodes.length" class="mini-map-svg" viewBox="0 0 118 88" aria-label="脑图迷你地图">
          <circle
            v-for="node in miniMapLayout.nodes"
            :key="node.id"
            :cx="node.x"
            :cy="node.y"
            :r="node.selected ? 3.2 : 2.4"
            :class="['mini-map-node-dot', { selected: node.selected, case: node.nodeType === 'case' }]"
          />
        </svg>
        <div v-else class="mini-map-empty">暂无节点</div>
        <div
          class="mini-map-window"
          :style="miniMapWindowStyle"
          @mousedown.prevent="startMiniMapPan"
        />
      </div>
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
import { ElMessageBox } from 'element-plus'
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
const assigneeNames = ref([])
const assigneeIds = ref([])
const totalCases = ref(0)
const selectedNodeId = ref(null)
const selectedNodeIds = ref([])
const collapsedNodeIds = ref([])
const priorityFilter = ref('')
const statusFilter = ref('')
const radialVisible = ref(false)
const radialPosition = reactive({ x: 600, y: 360 })
const zoom = ref(1)
const mindMapCanvasRef = ref(null)
const viewportState = reactive({
  scrollLeft: 0,
  scrollTop: 0,
  clientWidth: 1,
  clientHeight: 1,
  scrollWidth: 1,
  scrollHeight: 1,
  nodes: []
})
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

const filteredTreeData = computed(() => filterTree(treeData.value))

function filterTree(nodes) {
  const hasPriorityFilter = Boolean(priorityFilter.value)
  const hasStatusFilter = Boolean(statusFilter.value)
  if (!hasPriorityFilter && !hasStatusFilter) {
    return nodes
  }
  const result = []
  for (const node of nodes) {
    const nodeStatus = statusMap.value[node.node_id] || 'not_run'
    const priorityMatched = !hasPriorityFilter || (node.priority || 'P1') === priorityFilter.value
    const statusMatched = !hasStatusFilter || nodeStatus === statusFilter.value
    if (priorityMatched && statusMatched) {
      result.push({ ...node, children: node.children ? filterTree(node.children) : [] })
    } else if (node.children?.length) {
      const filteredChildren = filterTree(node.children)
      if (filteredChildren.length) {
        result.push({ ...node, children: filteredChildren })
      }
    }
  }
  return result
}

function handleFilterChange() {
  // 清空选中与折叠，避免旧视图状态干扰筛选结果
  selectedNodeId.value = null
  selectedNodeIds.value = []
  collapsedNodeIds.value = []
}

const countedStatus = computed(() => {
  const values = Object.values(statusMap.value)
  return {
    passed: values.filter(v => v === 'passed').length,
    failed: values.filter(v => v === 'failed').length,
    blocked: values.filter(v => v === 'blocked').length,
    skipped: values.filter(v => v === 'skipped').length,
    not_run: values.filter(v => v === 'not_run' || v === undefined || v === null || v === '').length
  }
})

const passedCount = computed(() => countedStatus.value.passed)
const failedCount = computed(() => countedStatus.value.failed)
const blockedCount = computed(() => countedStatus.value.blocked)
const skippedCount = computed(() => countedStatus.value.skipped)
const notRunCount = computed(() => Math.max(0, totalCases.value - testedCount.value))
const testedCount = computed(() => countedStatus.value.passed + countedStatus.value.failed + countedStatus.value.blocked + countedStatus.value.skipped)
const progressPercent = computed(() => (totalCases.value ? Math.round((testedCount.value / totalCases.value) * 100) : 0))
const statusProgress = computed(() => {
  const total = totalCases.value || 1
  return [
    { label: '通过', value: countedStatus.value.passed, percent: Math.round((countedStatus.value.passed / total) * 100), color: '#16a34a' },
    { label: '失败', value: countedStatus.value.failed, percent: Math.round((countedStatus.value.failed / total) * 100), color: '#ef4444' },
    { label: '阻塞', value: countedStatus.value.blocked, percent: Math.round((countedStatus.value.blocked / total) * 100), color: '#9333ea' },
    { label: '不适用', value: countedStatus.value.skipped, percent: Math.round((countedStatus.value.skipped / total) * 100), color: '#334155' }
  ].filter(item => item.value > 0)
})

const miniMapLayout = computed(() => buildMiniMapLayout())
const miniMapWindowStyle = computed(() => {
  const bounds = getMiniMapBounds()
  if (!bounds) {
    return { left: '0px', top: '0px', width: '118px', height: '88px' }
  }
  const padding = 8
  const mapWidth = 118 - padding * 2
  const mapHeight = 88 - padding * 2
  const width = Math.max(16, Math.min(mapWidth, (viewportState.clientWidth / bounds.width) * mapWidth))
  const height = Math.max(12, Math.min(mapHeight, (viewportState.clientHeight / bounds.height) * mapHeight))
  const left = Math.min(118 - width, Math.max(0, padding + ((viewportState.scrollLeft - bounds.minX) / bounds.width) * mapWidth))
  const top = Math.min(88 - height, Math.max(0, padding + ((viewportState.scrollTop - bounds.minY) / bounds.height) * mapHeight))
  return {
    left: `${left}px`,
    top: `${top}px`,
    width: `${width}px`,
    height: `${height}px`
  }
})

function handleViewportChange(payload) {
  Object.assign(viewportState, payload)
}

function buildMiniMapLayout() {
  const bounds = getMiniMapBounds()
  if (!bounds) {
    return { nodes: [] }
  }
  const padding = 8
  const mapWidth = 118 - padding * 2
  const mapHeight = 88 - padding * 2
  return {
    nodes: bounds.visibleNodes.map(node => {
      const meta = bounds.nodeMetaMap.get(node.id)
      return {
        id: node.id,
        nodeType: meta.nodeType,
        x: padding + ((node.x - bounds.minX) / bounds.width) * mapWidth,
        y: padding + ((node.y - bounds.minY) / bounds.height) * mapHeight,
        selected: node.id === selectedNodeId.value || selectedNodeIds.value.includes(node.id)
      }
    })
  }
}

function getMiniMapBounds() {
  const nodeMetaMap = new Map()
  collectMiniMapNodeMeta(treeData.value, nodeMetaMap)
  const visibleNodes = viewportState.nodes.filter(node => nodeMetaMap.has(node.id))
  if (!visibleNodes.length) {
    return null
  }
  const minX = Math.min(...visibleNodes.map(node => node.x))
  const maxX = Math.max(...visibleNodes.map(node => node.x))
  const minY = Math.min(...visibleNodes.map(node => node.y))
  const maxY = Math.max(...visibleNodes.map(node => node.y))
  return {
    nodeMetaMap,
    visibleNodes,
    minX,
    minY,
    width: Math.max(1, maxX - minX),
    height: Math.max(1, maxY - minY)
  }
}

function collectMiniMapNodeMeta(nodes, result) {
  for (const node of nodes) {
    result.set(node.node_id, { nodeType: node.node_type })
    if (!collapsedNodeIds.value.includes(node.node_id)) {
      collectMiniMapNodeMeta(node.children || [], result)
    }
  }
}

let miniMapDragging = false
let miniMapDragStart = { x: 0, y: 0, scrollLeft: 0, scrollTop: 0 }

function startMiniMapPan(event) {
  if (!mindMapCanvasRef.value) {
    return
  }
  const bounds = getMiniMapBounds()
  if (!bounds) {
    return
  }
  miniMapDragging = true
  miniMapDragStart = {
    x: event.clientX,
    y: event.clientY,
    scrollLeft: viewportState.scrollLeft,
    scrollTop: viewportState.scrollTop
  }
  window.addEventListener('mousemove', handleMiniMapPan)
  window.addEventListener('mouseup', stopMiniMapPan)
}

function handleMiniMapPan(event) {
  if (!miniMapDragging || !mindMapCanvasRef.value) {
    return
  }
  const bounds = getMiniMapBounds()
  if (!bounds) {
    return
  }
  const padding = 8
  const mapWidth = 118 - padding * 2
  const mapHeight = 88 - padding * 2
  const dx = (event.clientX - miniMapDragStart.x) / mapWidth * bounds.width
  const dy = (event.clientY - miniMapDragStart.y) / mapHeight * bounds.height
  mindMapCanvasRef.value.scrollTo(miniMapDragStart.scrollLeft + dx, miniMapDragStart.scrollTop + dy)
}

function stopMiniMapPan() {
  if (!miniMapDragging) {
    return
  }
  miniMapDragging = false
  window.removeEventListener('mousemove', handleMiniMapPan)
  window.removeEventListener('mouseup', stopMiniMapPan)
}

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
    assigneeNames.value = treeResult.assignee_names || []
    assigneeIds.value = treeResult.assignee_ids || []
    treeData.value = treeResult.tree || []
    // 后端 status_map 键是字符串，转成数字键，与 node.node_id（数字）匹配
    const numericStatusMap = {}
    for (const [key, value] of Object.entries(treeResult.status_map || {})) {
      numericStatusMap[Number(key)] = value
    }
    statusMap.value = numericStatusMap
    totalCases.value = treeResult.total_cases || 0

    // 执行记录映射：只保留当前登录用户自己的记录，保证"所有人可看，但只能标记自己的用例"。
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

function handleBoxSelect(nodeIds) {
  selectedNodeIds.value = nodeIds
  selectedNodeId.value = nodeIds.length ? nodeIds[0] : null
}

function openContextMenu(payload) {
  const node = payload.node
  // 右击节点：若已被框选则保持多选，否则单选
  if (!selectedNodeIds.value.includes(node.node_id)) {
    handleSelect(node)
  }
  radialPosition.x = payload.x
  radialPosition.y = payload.y
  radialVisible.value = true
}

// 把选中的节点列表展开为最下层的 case 节点 id：目录节点会级联到其所有子用例。
function expandToCaseNodeIds(nodeIds) {
  const result = new Set()
  for (const nodeId of nodeIds) {
    collectCaseNodeIds(treeData.value, nodeId, result)
  }
  return Array.from(result)
}

function collectCaseNodeIds(nodes, targetId, result) {
  for (const node of nodes) {
    if (node.node_id === targetId) {
      if (node.node_type === 'case') {
        result.add(node.node_id)
      } else {
        collectAllCaseIds(node.children || [], result)
      }
      return
    }
    if (node.children?.length) {
      collectCaseNodeIds(node.children, targetId, result)
    }
  }
}

function collectAllCaseIds(nodes, result) {
  for (const node of nodes) {
    if (node.node_type === 'case') {
      result.add(node.node_id)
    } else if (node.children?.length) {
      collectAllCaseIds(node.children, result)
    }
  }
}

async function handleAssignTask() {
  if (!assigneeIds.value.includes(getCurrentUserId())) {
    showWarning('你不是该任务的执行人，无法认领')
    return
  }
  await assignTask(taskId)
  showSuccess('任务已认领')
  isClaimed.value = true
  assignStatus.value = 'accepted'
}

async function handleRadialAction(action) {
  radialVisible.value = false
  if (!isClaimed.value) {
    showWarning('请先认领任务')
    return
  }
  const targetNodeIds = selectedNodeIds.value.length ? selectedNodeIds.value : [selectedNodeId.value]
  // 目录节点级联展开为子用例；只保留有执行记录的 case 节点。
  const caseNodeIds = expandToCaseNodeIds(targetNodeIds).filter(id => nodeToExecution.value[id])
  if (!caseNodeIds.length) {
    showWarning('未找到对应的执行记录')
    return
  }

  if (action === 'remove') {
    await markStatus(caseNodeIds, 'not_run')
    return
  }
  if (action === 'bug') {
    await addBug(caseNodeIds)
    return
  }
  if (action === 'note') {
    await addNote(caseNodeIds)
    return
  }
  // passed / failed / blocked / skipped
  await markStatus(caseNodeIds, action)
}

async function markStatus(caseNodeIds, status) {
  let successCount = 0
  const nextStatusMap = { ...statusMap.value }
  for (const nodeId of caseNodeIds) {
    const execution = nodeToExecution.value[nodeId]
    try {
      await updateExecution(execution.execution_id, {
        executor_id: execution.executor_id,
        execution_status: status,
        actual_result: defaultActualResult(status),
        bug_description: null,
        sync_version: execution.sync_version
      })
      nextStatusMap[nodeId] = status
      execution.sync_version += 1
      successCount += 1
    } catch {
      // 单条失败继续处理下一条
    }
  }
  statusMap.value = nextStatusMap
  showSuccess(`已标记 ${successCount} 个节点为：${statusText(status)}`)
}

async function addBug(caseNodeIds) {
  const result = await ElMessageBox.prompt('请输入缺陷描述', '登记缺陷', {
    confirmButtonText: '提交',
    cancelButtonText: '取消',
    inputPlaceholder: '例如：红外灯在低照度下未自动开启',
    inputType: 'textarea'
  }).catch(() => null)
  if (!result) {
    return
  }
  const bugDescription = String(result.value || '').trim()
  let successCount = 0
  const nextStatusMap = { ...statusMap.value }
  for (const nodeId of caseNodeIds) {
    const execution = nodeToExecution.value[nodeId]
    try {
      await updateExecution(execution.execution_id, {
        executor_id: execution.executor_id,
        execution_status: 'failed',
        actual_result: defaultActualResult('failed'),
        bug_description: bugDescription,
        sync_version: execution.sync_version
      })
      nextStatusMap[nodeId] = 'failed'
      execution.sync_version += 1
      successCount += 1
    } catch {
      // 单条失败继续处理下一条
    }
  }
  statusMap.value = nextStatusMap
  showSuccess(`已登记缺陷 ${successCount} 个节点`)
}

async function addNote(caseNodeIds) {
  const result = await ElMessageBox.prompt('请输入执行备注', '填写备注', {
    confirmButtonText: '保存',
    cancelButtonText: '取消',
    inputPlaceholder: '例如：需要在 8 小时老化后复测',
    inputType: 'textarea'
  }).catch(() => null)
  if (!result) {
    return
  }
  const note = String(result.value || '').trim()
  let successCount = 0
  const nextStatusMap = { ...statusMap.value }
  for (const nodeId of caseNodeIds) {
    const execution = nodeToExecution.value[nodeId]
    try {
      await updateExecution(execution.execution_id, {
        executor_id: execution.executor_id,
        execution_status: execution.execution_status,
        actual_result: note,
        bug_description: execution.bug_description,
        sync_version: execution.sync_version
      })
      execution.sync_version += 1
      successCount += 1
    } catch {
      // 单条失败继续处理下一条
    }
  }
  statusMap.value = nextStatusMap
  showSuccess(`已保存备注 ${successCount} 个节点`)
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

.progress-card {
  padding: 12px 16px;
}

.progress-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.progress-label {
  color: #334155;
  font-weight: 700;
}

.progress-text {
  color: #64748b;
  font-size: 13px;
}

.stacked-progress {
  display: flex;
  height: 14px;
  width: 100%;
  border-radius: 7px;
  overflow: hidden;
  background: #e5e7eb;
}

.stacked-segment {
  height: 100%;
  transition: width 0.3s ease;
}

.progress-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  margin-top: 8px;
}

.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  color: #64748b;
  font-size: 12px;
}

.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.mind-tip {
  color: #64748b;
  font-size: 13px;
}

.filter-label {
  color: #475569;
  font-size: 13px;
  font-weight: 600;
}

.filter-select {
  width: 110px;
  margin-right: 8px;
}

.empty-tip {
  padding: 60px 0;
  text-align: center;
  color: #94a3b8;
}

.mini-map {
  position: absolute;
  right: 16px;
  bottom: 16px;
  width: 118px;
  height: 88px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 8px 20px rgba(15, 23, 42, 0.12);
  overflow: hidden;
}

.mini-map-svg {
  width: 100%;
  height: 100%;
}

.mini-map-node-dot {
  fill: #94a3b8;
}

.mini-map-node-dot.case {
  fill: #34d399;
}

.mini-map-node-dot.selected {
  fill: #2563eb;
}

.mini-map-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #94a3b8;
  font-size: 12px;
}

.mini-map-window {
  position: absolute;
  left: 42px;
  top: 30px;
  width: 38px;
  height: 22px;
  border: 2px solid #ef4444;
  cursor: move;
  transition: 0.18s ease;
}
</style>
