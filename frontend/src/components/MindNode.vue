<template>
  <div class="mind-node-wrap">
    <div
      class="mind-node"
      :class="nodeClass"
      :data-node-id="node.node_id"
      :draggable="!isEditing"
      @click.stop="handleSelect"
      @dblclick.stop="handleEdit"
      @contextmenu.prevent.stop="handleContextMenu"
      @dragstart.stop="handleDragStart"
      @dragover.prevent.stop="handleDragOver"
      @dragleave.stop="handleDragLeave"
      @drop.prevent.stop="handleDrop"
      @dragend.stop="handleDragEnd"
    >
      <div class="node-main-line">
        <input
          v-if="isEditing"
          ref="titleInputRef"
          v-model="draftTitle"
          class="node-title-input"
          @click.stop
          @blur="commitTitle"
          @keydown.enter.prevent="commitTitle"
          @keydown.esc.prevent="cancelEdit"
        />
        <span v-else class="node-title">{{ node.title }}</span>
        <button
          v-if="children.length"
          class="node-collapse-toggle"
          :title="isCollapsed ? '展开子节点' : '收起子节点'"
          @click.stop="handleToggleCollapse"
        >{{ isCollapsed ? '+' : '−' }}</button>
        <span v-if="isCollapsed" class="collapsed-count">{{ children.length }}</span>
        <span v-if="node.node_type === 'case'" class="case-dot" />
        <span v-if="nodeExecutionStatus" class="node-status-badge" :class="`status-${nodeExecutionStatus}`">
          {{ EXECUTION_STATUS_SHORT[nodeExecutionStatus] || nodeExecutionStatus }}
        </span>
        <button v-if="appearance.showMetaIcons !== false && nodeNote" class="node-note-icon" title="查看备注" @click.stop="handleNoteClick">注</button>
        <button v-if="appearance.showMetaIcons !== false && nodeLink" class="node-meta-icon link-icon" title="查看链接" @click.stop="handleLinkClick">链</button>
        <button v-if="appearance.showMetaIcons !== false && nodeImage" class="node-meta-icon image-icon" title="查看图片" @click.stop="handleImageClick">图</button>
        <span v-for="tag in visibleNodeTags" :key="tag.text" class="node-tag" :style="{ background: tag.color }">
          {{ tag.text }}
        </span>
      </div>
    </div>

    <template v-if="visibleChildren.length">
      <div class="connector horizontal" />
      <div class="children-group">
        <div v-for="child in visibleChildren" :key="child.node_id" class="child-row">
          <div class="connector branch" />
          <MindNode
            :node="child"
            :selected-node-id="selectedNodeId"
            :selected-node-ids="selectedNodeIds"
            :editing-node-id="editingNodeId"
            :node-tags-map="nodeTagsMap"
            :node-notes-map="nodeNotesMap"
            :node-links-map="nodeLinksMap"
            :node-images-map="nodeImagesMap"
            :node-execution-status-map="nodeExecutionStatusMap"
            :collapsed-node-ids="collapsedNodeIds"
            :appearance="appearance"
            @select="$emit('select', $event)"
            @node-contextmenu="$emit('node-contextmenu', $event)"
            @title-save="$emit('title-save', $event)"
            @edit-cancel="$emit('edit-cancel')"
            @edit-request="$emit('edit-request', $event)"
            @note-click="$emit('note-click', $event)"
            @link-click="$emit('link-click', $event)"
            @image-click="$emit('image-click', $event)"
            @toggle-collapse="$emit('toggle-collapse', $event)"
            @node-drag-start="$emit('node-drag-start', $event)"
            @node-drop="$emit('node-drop', $event)"
            @node-drag-end="$emit('node-drag-end')"
          />
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'

const EXECUTION_STATUS_SHORT = {
  passed: '通过',
  failed: '失败',
  blocked: '阻塞',
  skipped: '不适用',
  not_run: '未执行'
}

const props = defineProps({
  node: {
    type: Object,
    required: true
  },
  root: {
    type: Boolean,
    default: false
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
  nodeExecutionStatusMap: {
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
  }
})

const emit = defineEmits(['select', 'node-contextmenu', 'title-save', 'edit-cancel', 'edit-request', 'note-click', 'link-click', 'image-click', 'toggle-collapse', 'node-drag-start', 'node-drop', 'node-drag-end'])
const titleInputRef = ref(null)
const draftTitle = ref(props.node.title || '')
const dragOver = ref(false)

const children = computed(() => props.node.children || [])
const isCollapsed = computed(() => props.collapsedNodeIds.includes(props.node.node_id))
const visibleChildren = computed(() => (isCollapsed.value ? [] : children.value))
const isEditing = computed(() => props.node.node_id === props.editingNodeId)
const nodeTags = computed(() => props.nodeTagsMap[props.node.node_id] || [])
const visibleNodeTags = computed(() => (props.appearance.showTags === false ? [] : nodeTags.value))
const appearance = computed(() => props.appearance || {})
const nodeNote = computed(() => String(props.nodeNotesMap[props.node.node_id] || '').trim())
const nodeLink = computed(() => props.nodeLinksMap[props.node.node_id])
const nodeImage = computed(() => props.nodeImagesMap[props.node.node_id])
const nodeExecutionStatus = computed(() => props.nodeExecutionStatusMap[props.node.node_id] || '')
const nodeClass = computed(() => ({
  'root-node': props.root,
  'case-node': props.node.node_type === 'case',
  'folder-node': props.node.node_type !== 'case',
  'is-collapsed': isCollapsed.value,
  'is-drag-over': dragOver.value,
  [`size-${props.appearance.nodeSize || 'normal'}`]: true,
  'is-selected': props.node.node_id === props.selectedNodeId || props.selectedNodeIds.includes(props.node.node_id),
  'is-editing': isEditing.value
}))

watch(
  () => props.node.title,
  value => {
    draftTitle.value = value || ''
  }
)

watch(isEditing, async value => {
  if (value) {
    draftTitle.value = props.node.title || ''
    await nextTick()
    titleInputRef.value?.focus()
    titleInputRef.value?.select()
  }
})

function handleSelect() {
  emit('select', props.node)
}

function handleEdit() {
  emit('select', props.node)
  emit('edit-request', props.node)
}

function handleContextMenu(event) {
  emit('select', props.node)
  emit('node-contextmenu', { node: props.node, x: event.clientX, y: event.clientY })
}

function handleNoteClick() {
  emit('select', props.node)
  emit('note-click', props.node)
}

function handleLinkClick() {
  emit('select', props.node)
  emit('link-click', props.node)
}

function handleImageClick() {
  emit('select', props.node)
  emit('image-click', props.node)
}

function handleToggleCollapse() {
  emit('select', props.node)
  emit('toggle-collapse', props.node)
}

function handleDragStart(event) {
  event.dataTransfer.effectAllowed = 'move'
  event.dataTransfer.setData('text/plain', String(props.node.node_id))
  emit('select', props.node)
  emit('node-drag-start', props.node)
}

function handleDragOver(event) {
  event.dataTransfer.dropEffect = 'move'
  dragOver.value = true
}

function handleDragLeave() {
  dragOver.value = false
}

function handleDrop() {
  dragOver.value = false
  emit('node-drop', props.node)
}

function handleDragEnd() {
  dragOver.value = false
  emit('node-drag-end')
}

function commitTitle() {
  const title = draftTitle.value.trim()
  if (!title) {
    draftTitle.value = props.node.title || ''
    emit('edit-cancel')
    return
  }
  if (title === props.node.title) {
    emit('edit-cancel')
    return
  }
  emit('title-save', { node: props.node, title })
}

function cancelEdit() {
  draftTitle.value = props.node.title || ''
  emit('edit-cancel')
}
</script>

<style scoped>
.mind-node-wrap {
  display: flex;
  align-items: center;
  position: relative;
}

.mind-node {
  position: relative;
  z-index: 2;
  min-width: 120px;
  max-width: 820px;
  padding: 7px 10px;
  border: 1px solid var(--mind-node-border-color, #8db7d6);
  border-radius: 6px;
  background: #ffffff;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.06);
  cursor: grab;
  transition: 0.18s ease;
}

.mind-node:hover,
.mind-node.is-selected {
  border-color: #2563eb;
  box-shadow: 0 6px 18px rgba(37, 99, 235, 0.22);
  transform: translateY(-1px);
}

.mind-node.is-drag-over {
  border-color: #f97316;
  box-shadow: 0 0 0 4px rgba(249, 115, 22, 0.18), 0 8px 22px rgba(249, 115, 22, 0.26);
}

.mind-node.is-editing {
  cursor: text;
}

.mind-node.is-selected::after {
  content: '';
  position: absolute;
  inset: -5px;
  border: 2px solid rgba(37, 99, 235, 0.5);
  border-radius: 10px;
  background: rgba(37, 99, 235, 0.06);
  pointer-events: none;
}

.root-node {
  padding: 13px 20px;
  color: #ffffff;
  background: var(--mind-root-color, #6ea4c8);
  border-color: var(--mind-root-border-color, #4b88b5);
  font-size: 18px;
  font-weight: 700;
}

.folder-node {
  font-weight: 700;
}

.case-node {
  border-color: var(--mind-node-border-color, #b7c7d8);
}

.mind-node.size-compact {
  min-width: 96px;
  padding: 5px 8px;
  font-size: 13px;
}

.mind-node.size-large {
  min-width: 150px;
  padding: 10px 14px;
  font-size: 16px;
}

.node-main-line {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
}

.node-title {
  white-space: pre-wrap;
  line-height: 1.5;
}

.node-title-input {
  min-width: 120px;
  max-width: 360px;
  height: 28px;
  padding: 0 6px;
  color: inherit;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid #2563eb;
  border-radius: 4px;
  outline: none;
  font: inherit;
  font-weight: inherit;
}

.root-node .node-title-input {
  color: #0f172a;
}

.node-collapse-toggle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  padding: 0;
  color: #2563eb;
  background: #eff6ff;
  border: 1px solid #93c5fd;
  border-radius: 50%;
  cursor: pointer;
  font-size: 15px;
  font-weight: 900;
  line-height: 1;
}

.node-collapse-toggle:hover {
  color: #ffffff;
  background: #2563eb;
}

.collapsed-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  color: #2563eb;
  background: #dbeafe;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 800;
}

.case-dot {
  width: 12px;
  height: 12px;
  border: 1px solid #94a3b8;
  border-radius: 50%;
  background: #fff;
}

.node-status-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 40px;
  height: 20px;
  padding: 0 6px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 800;
  line-height: 1;
}

.node-status-badge.status-passed {
  color: #166534;
  background: #dcfce7;
  border: 1px solid #4ade80;
}

.node-status-badge.status-failed {
  color: #991b1b;
  background: #fee2e2;
  border: 1px solid #f87171;
}

.node-status-badge.status-blocked {
  color: #4c1d95;
  background: #f3e8ff;
  border: 1px solid #c084fc;
}

.node-status-badge.status-skipped {
  color: #0f172a;
  background: #e2e8f0;
  border: 1px solid #64748b;
}

.node-status-badge.status-not_run {
  color: #64748b;
  background: #f8fafc;
  border: 1px dashed #cbd5e1;
}

.node-note-icon,
.node-meta-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  padding: 0;
  border-radius: 50%;
  cursor: pointer;
  font-size: 12px;
  font-weight: 800;
  line-height: 1;
}

.node-note-icon {
  color: #b45309;
  background: #fef3c7;
  border: 1px solid #f59e0b;
}

.node-note-icon:hover {
  color: #ffffff;
  background: #f59e0b;
}

.link-icon {
  color: #1d4ed8;
  background: #dbeafe;
  border: 1px solid #60a5fa;
}

.link-icon:hover {
  color: #ffffff;
  background: #2563eb;
}

.image-icon {
  color: #047857;
  background: #d1fae5;
  border: 1px solid #34d399;
}

.image-icon:hover {
  color: #ffffff;
  background: #059669;
}

.node-tag {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: 0 8px;
  color: #111827;
  border-radius: 0;
  font-size: 13px;
  font-weight: 600;
}

.connector.horizontal {
  width: 36px;
  height: 1px;
  background: var(--mind-connector-color, #7faed0);
}

.children-group {
  display: flex;
  flex-direction: column;
  gap: 18px;
  position: relative;
  padding-left: 0;
}

.child-row {
  display: flex;
  align-items: center;
  position: relative;
}

.child-row::before {
  content: '';
  position: absolute;
  left: 0;
  top: -9px;
  bottom: -9px;
  width: 1px;
  background: var(--mind-connector-color, #7faed0);
}

.child-row:first-child::before {
  top: 50%;
}

.child-row:last-child::before {
  bottom: 50%;
}

.child-row:first-child:last-child::before {
  display: none;
}

.connector.branch {
  position: relative;
  z-index: 1;
  width: 28px;
  height: 1px;
  background: var(--mind-connector-color, #7faed0);
}
</style>
