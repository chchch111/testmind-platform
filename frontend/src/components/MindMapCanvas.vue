<template>
  <div
    ref="scrollRef"
    class="mindmap-scroll"
    :class="{ 'is-dragging': dragging, 'is-selecting': selectionVisible }"
    @mouseenter="emit('viewport-active-change', true)"
    @mouseleave="handleMouseLeave"
    @mousedown="handleMouseDown"
    @wheel="handleWheel"
    @dblclick.self="resetView"
  >
    <div v-if="selectionVisible" class="selection-rect" :style="selectionRectStyle" />
    <div v-if="treeData.length" class="mindmap-canvas-viewport">
      <div class="mindmap-canvas" :style="canvasStyle">
        <div v-for="root in treeData" :key="root.node_id" class="mind-row root-row">
          <MindNode
            :node="root"
            root
            :selected-node-id="selectedNodeId"
            :selected-node-ids="selectedNodeIds"
            :editing-node-id="editingNodeId"
            :node-tags-map="nodeTagsMap"
            :node-notes-map="nodeNotesMap"
            :node-links-map="nodeLinksMap"
            :node-images-map="nodeImagesMap"
            :node-reviews-map="nodeReviewsMap"
            :collapsed-node-ids="collapsedNodeIds"
            :appearance="appearance"
            @select="emitSelect"
            @node-contextmenu="emitContextMenu"
            @title-save="emitTitleSave"
            @edit-cancel="emitEditCancel"
            @edit-request="emitEditRequest"
            @note-click="emitNoteClick"
            @link-click="emitLinkClick"
            @image-click="emitImageClick"
            @review-click="emitReviewClick"
            @toggle-collapse="emitToggleCollapse"
          />
        </div>
      </div>
    </div>
    <el-empty v-else description="暂无思维导图节点" />
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, reactive, ref, watch } from 'vue'
import MindNode from './MindNode.vue'

const props = defineProps({
  treeData: {
    type: Array,
    default: () => []
  },
  selectedNodeId: {
    type: Number,
    default: null
  },
  selectedNodeIds: {
    type: Array,
    default: () => []
  },
  editingNodeId: {
    type: Number,
    default: null
  },
  nodeTagsMap: {
    type: Object,
    default: () => ({})
  },
  nodeNotesMap: {
    type: Object,
    default: () => ({})
  },
  nodeLinksMap: {
    type: Object,
    default: () => ({})
  },
  nodeImagesMap: {
    type: Object,
    default: () => ({})
  },
  nodeReviewsMap: {
    type: Object,
    default: () => ({})
  },
  collapsedNodeIds: {
    type: Array,
    default: () => []
  },
  appearance: {
    type: Object,
    default: () => ({})
  },
  zoom: {
    type: Number,
    default: 1
  }
})

const emit = defineEmits([
  'select',
  'node-contextmenu',
  'title-save',
  'edit-cancel',
  'edit-request',
  'note-click',
  'link-click',
  'image-click',
  'review-click',
  'toggle-collapse',
  'box-select',
  'box-select-preview',
  'zoom-in',
  'zoom-out',
  'reset-view',
  'viewport-active-change'
])

const scrollRef = ref(null)
const dragging = ref(false)
const selectionVisible = ref(false)
const dragState = reactive({
  startX: 0,
  startY: 0,
  scrollLeft: 0,
  scrollTop: 0
})
const selectionState = reactive({
  startX: 0,
  startY: 0,
  currentX: 0,
  currentY: 0
})

const canvasStyle = computed(() => ({
  transform: `scale(${props.zoom})`,
  '--mind-root-color': props.appearance.rootColor || '#6ea4c8',
  '--mind-root-border-color': props.appearance.rootColor || '#4b88b5',
  '--mind-node-border-color': props.appearance.nodeBorderColor || '#8db7d6',
  '--mind-connector-color': props.appearance.connectorColor || '#7faed0'
}))

const selectionRectStyle = computed(() => ({
  left: `${Math.min(selectionState.startX, selectionState.currentX)}px`,
  top: `${Math.min(selectionState.startY, selectionState.currentY)}px`,
  width: `${Math.abs(selectionState.currentX - selectionState.startX)}px`,
  height: `${Math.abs(selectionState.currentY - selectionState.startY)}px`
}))

function emitSelect(node) {
  emit('select', node)
}

function emitContextMenu(payload) {
  emit('node-contextmenu', payload)
}

function emitTitleSave(payload) {
  emit('title-save', payload)
}

function emitEditCancel() {
  emit('edit-cancel')
}

function emitEditRequest(node) {
  emit('edit-request', node)
}

function emitNoteClick(node) {
  emit('note-click', node)
}

function emitLinkClick(node) {
  emit('link-click', node)
}

function emitImageClick(node) {
  emit('image-click', node)
}

function emitReviewClick(node) {
  emit('review-click', node)
}

function emitToggleCollapse(node) {
  emit('toggle-collapse', node)
}

function centerRootNode() {
  if (!scrollRef.value) {
    return
  }
  const rootNode = scrollRef.value.querySelector('.root-row .mind-node')
  if (!rootNode) {
    return
  }
  scrollRef.value.scrollLeft = rootNode.offsetLeft - scrollRef.value.clientWidth / 2 + rootNode.offsetWidth / 2
  scrollRef.value.scrollTop = rootNode.offsetTop - scrollRef.value.clientHeight / 2 + rootNode.offsetHeight / 2
}

async function centerRootNodeAfterRender() {
  await nextTick()
  window.requestAnimationFrame(centerRootNode)
}

function handleWheel(event) {
  if (!event.ctrlKey && !event.metaKey) {
    return
  }
  event.preventDefault()
  if (event.deltaY < 0) {
    emit('zoom-in')
  } else {
    emit('zoom-out')
  }
}

function handleMouseDown(event) {
  if (!scrollRef.value || event.target.closest('.mind-node, input, button, .el-button')) {
    return
  }
  if (event.altKey && event.button <= 2) {
    event.preventDefault()
    dragging.value = true
    dragState.startX = event.clientX
    dragState.startY = event.clientY
    dragState.scrollLeft = scrollRef.value.scrollLeft
    dragState.scrollTop = scrollRef.value.scrollTop
    window.addEventListener('mousemove', handleMouseMove)
    window.addEventListener('mouseup', stopDragging)
    return
  }
  if (event.button === 0) {
    event.preventDefault()
    startBoxSelection(event)
  }
}

function handleMouseMove(event) {
  if (!dragging.value || !scrollRef.value) {
    return
  }
  scrollRef.value.scrollLeft = dragState.scrollLeft - (event.clientX - dragState.startX)
  scrollRef.value.scrollTop = dragState.scrollTop - (event.clientY - dragState.startY)
}

function startBoxSelection(event) {
  selectionState.startX = event.clientX
  selectionState.startY = event.clientY
  selectionState.currentX = event.clientX
  selectionState.currentY = event.clientY
  selectionVisible.value = true
  emit('box-select-preview', [])
  window.addEventListener('mousemove', handleSelectionMove)
  window.addEventListener('mouseup', stopBoxSelection)
}

function handleSelectionMove(event) {
  if (!selectionVisible.value || !scrollRef.value) {
    return
  }
  selectionState.currentX = event.clientX
  selectionState.currentY = event.clientY
  emit('box-select-preview', getBoxSelectedNodeIds())
}

function stopBoxSelection() {
  if (!selectionVisible.value || !scrollRef.value) {
    return
  }
  const selectedIds = getBoxSelectedNodeIds()
  selectionVisible.value = false
  window.removeEventListener('mousemove', handleSelectionMove)
  window.removeEventListener('mouseup', stopBoxSelection)
  emit('box-select', selectedIds)
}

function getBoxSelectedNodeIds() {
  const selectionRect = {
    left: Math.min(selectionState.startX, selectionState.currentX),
    right: Math.max(selectionState.startX, selectionState.currentX),
    top: Math.min(selectionState.startY, selectionState.currentY),
    bottom: Math.max(selectionState.startY, selectionState.currentY)
  }
  if (selectionRect.right - selectionRect.left < 6 || selectionRect.bottom - selectionRect.top < 6) {
    return []
  }
  return Array.from(scrollRef.value.querySelectorAll('.mind-node[data-node-id]'))
    .filter(element => isIntersecting(selectionRect, element.getBoundingClientRect()))
    .map(element => Number(element.dataset.nodeId))
}

function isIntersecting(a, b) {
  return a.left <= b.right && a.right >= b.left && a.top <= b.bottom && a.bottom >= b.top
}

function stopDragging() {
  dragging.value = false
  window.removeEventListener('mousemove', handleMouseMove)
  window.removeEventListener('mouseup', stopDragging)
}

function handleMouseLeave() {
  emit('viewport-active-change', false)
}

function resetView() {
  emit('reset-view')
  centerRootNodeAfterRender()
}

watch(
  () => props.treeData.map(node => node.node_id).join(','),
  value => {
    if (value) {
      centerRootNodeAfterRender()
    }
  },
  { immediate: true }
)

onBeforeUnmount(() => {
  stopDragging()
  window.removeEventListener('mousemove', handleSelectionMove)
  window.removeEventListener('mouseup', stopBoxSelection)
})
</script>

<style scoped>
.mindmap-scroll {
  position: relative;
  min-height: 560px;
  max-height: 720px;
  overflow: auto;
  padding: 0;
  background: #fbfdff;
  border: 1px solid #dbeafe;
  border-radius: 12px;
  cursor: default;
}

.mindmap-scroll.is-dragging {
  cursor: grabbing;
  user-select: none;
}

.mindmap-scroll.is-selecting {
  cursor: crosshair;
  user-select: none;
}

.selection-rect {
  position: fixed;
  z-index: 3001;
  border: 1px solid #2563eb;
  background: rgba(37, 99, 235, 0.16);
  box-shadow: 0 0 0 1px rgba(37, 99, 235, 0.12);
  pointer-events: none;
}

.mindmap-canvas-viewport {
  width: max-content;
  min-width: 2600px;
  min-height: 1500px;
  padding: 520px 900px 560px 900px;
  box-sizing: border-box;
}

.mindmap-canvas {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 42px;
  min-width: max-content;
  transform-origin: left top;
  transition: transform 0.18s ease;
}

.mind-row {
  display: flex;
  align-items: center;
}
</style>
