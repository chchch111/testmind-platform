<template>
  <div class="case-detail editor-page" @click="closeContextMenu">
    <div class="editor-header page-card">
      <div>
        <div class="breadcrumb">用例管理 / 用例详情 / {{ caseSetId }}</div>
        <h1 class="page-title">思维导图测试用例编辑器</h1>
        <p class="page-desc">参考 XMind 风格展示：横向展开、多层连接线、彩色标签、点击节点后在右侧查看和编辑。</p>
      </div>
      <div class="header-actions">
        <el-button type="primary" @click="createCanvasSnapshot">创建版本</el-button>
        <el-button type="primary" @click="snapshotDialogVisible = true">版本快照</el-button>
        <el-button type="primary" @click="showSuccess('已提交用例评审流程')">发起用例评审</el-button>
        <el-button type="primary" @click="openSearchDialog">搜索用例</el-button>
        <el-button type="primary" @click="versionDrawerVisible = true" :disabled="!selectedNode">历史</el-button>
        <el-button @click="shortcutDialogVisible = true">快捷键</el-button>
        <el-button @click="loadTree">刷新</el-button>
        <el-button @click="$router.push('/case-sets')">返回列表</el-button>
      </div>
    </div>

    <div class="editor-tabs page-card">
      <div class="tab-row">
        <el-tabs v-model="activeTab" class="editor-tab">
          <el-tab-pane label="思路" name="mind" />
          <el-tab-pane label="外观" name="style" />
        </el-tabs>
        <div class="collapse-tip">收起</div>
      </div>

      <div v-if="activeTab === 'mind'" class="toolbar-grid">
        <div class="toolbar-block">
          <el-button text :disabled="!undoStack.length" @click="undoLastAction">撤销</el-button>
          <el-button text :disabled="!redoStack.length" @click="redoLastAction">重做</el-button>
          <el-button text :disabled="!selectedNode" @click="openLinkDialog(selectedNode)">链接</el-button>
          <el-button text :disabled="!selectedNode" @click="openImageDialog(selectedNode)">图片</el-button>
        </div>
        <div class="toolbar-block priority-tools">
          <span class="priority-dot p0">P0</span>
          <span class="priority-dot p1">P1</span>
          <span class="priority-dot p2">P2</span>
          <span class="priority-dot p3">P3</span>
        </div>
        <div class="toolbar-block">
          <el-button text :disabled="!selectedNodeIds.length && !selectedNode" @click="clearSelectedTags">清除样式</el-button>
          <el-button text @click="openSearchDialog">搜索</el-button>
        </div>
        <div class="toolbar-block label-tools tag-palette">
          <div class="tag-tab-row">
            <span class="label-title" :class="{ active: labelTab === 'system' }" @click="labelTab = 'system'">系统标签</span>
            <span class="label-title" :class="{ active: labelTab === 'business' }" @click="labelTab = 'business'">业务标签</span>
          </div>
          <div class="tag-row">
            <span
              v-for="tag in visibleToolbarTags"
              :key="tag.text"
              class="tag clickable-tag"
              :style="{ background: tag.color }"
              @click.stop="addTagToSelectedNode(tag)"
            >{{ tag.text }}</span>
            <el-select
              v-model="customTagValue"
              class="custom-tag-select"
              filterable
              allow-create
              clearable
              placeholder="请输入/选择自定义标签"
              @change="handleCustomTagChange"
            >
              <el-option v-for="tag in allToolbarTags" :key="tag.text" :label="tag.text" :value="tag.text" />
            </el-select>
          </div>
        </div>
      </div>

      <div v-else class="toolbar-grid style-toolbar-grid">
        <div class="toolbar-block style-block">
          <span class="style-label">主题</span>
          <el-radio-group v-model="appearanceForm.theme" size="small" @change="applyAppearanceTheme">
            <el-radio-button v-for="theme in appearanceThemes" :key="theme.name" :label="theme.name">
              {{ theme.label }}
            </el-radio-button>
          </el-radio-group>
        </div>
        <div class="toolbar-block style-block">
          <span class="style-label">连线颜色</span>
          <el-color-picker v-model="appearanceForm.connectorColor" size="small" @change="saveAppearanceSettings" />
        </div>
        <div class="toolbar-block style-block">
          <span class="style-label">节点大小</span>
          <el-radio-group v-model="appearanceForm.nodeSize" size="small" @change="saveAppearanceSettings">
            <el-radio-button label="compact">紧凑</el-radio-button>
            <el-radio-button label="normal">标准</el-radio-button>
            <el-radio-button label="large">宽松</el-radio-button>
          </el-radio-group>
        </div>
        <div class="toolbar-block style-block">
          <span class="style-label">显示标签</span>
          <el-switch v-model="appearanceForm.showTags" @change="saveAppearanceSettings" />
        </div>
        <div class="toolbar-block style-block">
          <span class="style-label">显示图标</span>
          <el-switch v-model="appearanceForm.showMetaIcons" @change="saveAppearanceSettings" />
        </div>
        <div class="toolbar-block style-block filter-style-block">
          <span class="style-label">按标签筛选</span>
          <el-select
            v-model="appearanceForm.filterTag"
            class="style-select"
            clearable
            placeholder="全部标签"
            @change="handleFilterTagChange"
          >
            <el-option v-for="tag in availableFilterTags" :key="tag" :label="tag" :value="tag" />
          </el-select>
        </div>
        <div class="toolbar-block style-block filter-style-block">
          <span class="style-label">展开层级</span>
          <el-select v-model="appearanceForm.expandLevel" class="level-select" @change="applyExpandLevel">
            <el-option label="全部展开" value="all" />
            <el-option v-for="level in 6" :key="level" :label="`${level} 层`" :value="String(level)" />
          </el-select>
        </div>
        <div class="toolbar-block style-block">
          <el-button text @click="resetAppearanceSettings">恢复默认外观</el-button>
        </div>
      </div>
    </div>

    <div class="canvas-shell page-card">
      <div class="canvas-toolbar">
        <el-button type="primary" size="small" @click="openCreateRoot">新增根节点</el-button>
        <el-button size="small" :disabled="!selectedNode" @click="openCreateChild">新增子节点</el-button>
        <el-button size="small" :disabled="!selectedNodeHasChildren" @click="toggleSelectedNodeCollapse">展开/收起</el-button>
        <el-button size="small" @click="expandAllNodes">展开全部</el-button>
        <el-button size="small" @click="collapseAllNodes">收起全部</el-button>
        <span class="mind-tip">Alt + 鼠标拖动画布移动视野，Ctrl + 滚轮仅在脑图区域缩放</span>
      </div>

      <MindMapCanvas
        :tree-data="filteredTreeData"
        :selected-node-id="selectedNode?.node_id"
        :selected-node-ids="selectedNodeIds"
        :editing-node-id="editingNodeId"
        :node-tags-map="nodeTagsMap"
        :node-notes-map="nodeNotesMap"
        :node-links-map="nodeLinksMap"
        :node-images-map="nodeImagesMap"
        :node-reviews-map="nodeReviewsMap"
        :collapsed-node-ids="collapsedNodeIds"
        :appearance="appearanceConfig"
        :zoom="zoom"
        @select="handleSelectNode"
        @node-contextmenu="openContextMenu"
        @title-save="handleTitleSave"
        @edit-cancel="editingNodeId = null"
        @edit-request="handleEditRequest"
        @note-click="openNoteDialog"
        @link-click="openLinkDialog"
        @image-click="openImageDialog"
        @review-click="openReviewDialog"
        @toggle-collapse="toggleNodeCollapse"
        @box-select="handleBoxSelect"
        @box-select-preview="handleBoxSelectPreview"
        @zoom-in="zoomIn"
        @zoom-out="zoomOut"
        @reset-view="resetZoom"
        @viewport-active-change="isMindmapViewportActive = $event"
      />

      <div class="viewer-badge">1人正在查看</div>
      <div class="map-tools">
        <el-button circle size="small" title="适应画布" @click="resetZoom">适</el-button>
        <el-button circle size="small" title="放大" @click="zoomIn">＋</el-button>
        <div class="zoom-line"><span :style="zoomDotStyle" /></div>
        <el-button circle size="small" title="缩小" @click="zoomOut">－</el-button>
        <el-button circle size="small" title="居中" @click="resetZoom">中</el-button>
        <div class="zoom-value">{{ Math.round(zoom * 100) }}%</div>
      </div>
      <div class="mini-map">
        <div class="mini-map-lines" />
        <div class="mini-map-window" :style="miniMapWindowStyle" />
      </div>
      <div v-if="contextMenuVisible" class="quick-node-menu" :style="contextMenuStyle" @click.stop>
        <div class="quick-ring" />
        <el-button class="quick-button primary" circle @click="runContextAction(openEditNode)">
          <span class="quick-text">编辑</span>
        </el-button>
        <el-button class="quick-button" circle @click="runContextAction(openCreateChild)">
          <span class="quick-text">下级</span>
        </el-button>
        <el-button class="quick-button" circle @click="runContextAction(openSiblingNode)">
          <span class="quick-text">同级</span>
        </el-button>
        <el-button class="quick-button" circle @click="runContextAction(handleDeleteNode)">
          <span class="quick-text">删除</span>
        </el-button>
        <el-button class="quick-button" circle :disabled="!selectedNodeParent" @click="runContextAction(() => selectRelativeNode('parent'))">
          <span class="quick-text">上级</span>
        </el-button>
        <el-button class="quick-button" circle :disabled="!canMoveSelectedNode('up')" @click="runContextAction(() => moveSelectedNode('up'))">
          <span class="quick-text">前移</span>
        </el-button>
        <el-button class="quick-button" circle :disabled="!canMoveSelectedNode('down')" @click="runContextAction(() => moveSelectedNode('down'))">
          <span class="quick-text">后移</span>
        </el-button>
        <div class="quick-extra-actions">
          <el-button round @click="runContextAction(() => openNoteDialog(selectedNode))">备注</el-button>
          <el-button round @click="runContextAction(() => openReviewDialog(selectedNode))">评审</el-button>
          <el-button round disabled>自动化</el-button>
        </div>
      </div>
      <el-button class="floating-save" type="primary" @click="handleSaveCanvas">保存</el-button>
    </div>

    <el-drawer v-model="detailDrawerVisible" title="节点详情" size="34%">
      <template v-if="selectedNode">
        <div class="node-header">
          <h2>{{ selectedNode.title }}</h2>
          <div class="node-actions">
            <el-button size="small" type="primary" @click="openEditNode">编辑</el-button>
            <el-button size="small" type="warning" @click="versionDrawerVisible = true">历史版本</el-button>
            <el-button size="small" type="danger" @click="handleDeleteNode">删除</el-button>
          </div>
        </div>
        <el-descriptions border :column="1">
          <el-descriptions-item label="节点ID">{{ selectedNode.node_id }}</el-descriptions-item>
          <el-descriptions-item label="节点类型">{{ NODE_TYPE_TEXT[selectedNode.node_type] }}</el-descriptions-item>
          <el-descriptions-item label="优先级">{{ selectedNode.priority }}</el-descriptions-item>
          <el-descriptions-item label="前置条件">{{ selectedNode.precondition || '无' }}</el-descriptions-item>
          <el-descriptions-item label="测试步骤">{{ selectedNode.test_steps || '无' }}</el-descriptions-item>
          <el-descriptions-item label="预期结果">{{ selectedNode.expected_result || '无' }}</el-descriptions-item>
        </el-descriptions>
      </template>
      <el-empty v-else description="请先点击一个节点" />
    </el-drawer>

    <el-dialog v-model="nodeDialogVisible" :title="nodeDialogTitle" width="680px">
      <CaseNodeForm v-model="nodeForm" :show-change-note="dialogMode === 'edit'" />
      <template #footer>
        <el-button @click="nodeDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingNode" @click="handleSaveNode">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="noteDialogVisible" title="节点备注" width="560px">
      <div v-if="noteEditingNode" class="note-dialog-body">
        <div class="note-node-title">当前节点：{{ noteEditingNode.title }}</div>
        <el-input
          v-model="noteDraft"
          type="textarea"
          :rows="7"
          maxlength="500"
          show-word-limit
          placeholder="请输入这个节点的备注内容"
        />
        <div v-if="currentNodeNote" class="note-preview">
          <div class="note-preview-title">当前备注预览</div>
          <div class="note-preview-content">{{ currentNodeNote }}</div>
        </div>
      </div>
      <template #footer>
        <el-button :disabled="!noteEditingNode || !currentNodeNote" @click="clearNodeNote">删除备注</el-button>
        <el-button @click="noteDialogVisible = false">关闭</el-button>
        <el-button type="primary" @click="saveNodeNote">保存备注</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="linkDialogVisible" title="节点链接" width="560px">
      <div v-if="linkEditingNode" class="meta-dialog-body">
        <div class="note-node-title">当前节点：{{ linkEditingNode.title }}</div>
        <el-input v-model="linkForm.title" placeholder="链接名称，例如：需求文档" />
        <el-input v-model="linkForm.url" placeholder="链接地址，例如：https://example.com/doc" />
        <div v-if="currentNodeLink?.url" class="meta-preview">
          <div class="note-preview-title">当前链接</div>
          <a :href="currentNodeLink.url" target="_blank" rel="noreferrer">{{ currentNodeLink.title || currentNodeLink.url }}</a>
        </div>
      </div>
      <template #footer>
        <el-button :disabled="!linkEditingNode || !currentNodeLink" @click="clearNodeLink">删除链接</el-button>
        <el-button @click="linkDialogVisible = false">关闭</el-button>
        <el-button type="primary" @click="saveNodeLink">保存链接</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="imageDialogVisible" title="节点图片" width="620px">
      <div v-if="imageEditingNode" class="meta-dialog-body">
        <div class="note-node-title">当前节点：{{ imageEditingNode.title }}</div>
        <el-input v-model="imageForm.title" placeholder="图片说明，例如：测试环境截图" />
        <el-input v-model="imageForm.url" placeholder="图片地址，支持 http:// 或 https://" />
        <div v-if="currentNodeImage?.url" class="image-preview-box">
          <div class="note-preview-title">当前图片预览</div>
          <div class="image-preview-title">{{ currentNodeImage.title }}</div>
          <img :src="currentNodeImage.url" :alt="currentNodeImage.title || '节点图片'" />
        </div>
      </div>
      <template #footer>
        <el-button :disabled="!imageEditingNode || !currentNodeImage" @click="clearNodeImage">删除图片</el-button>
        <el-button @click="imageDialogVisible = false">关闭</el-button>
        <el-button type="primary" @click="saveNodeImage">保存图片</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="reviewDialogVisible" title="节点评审" width="560px">
      <div v-if="reviewEditingNode" class="meta-dialog-body">
        <div class="note-node-title">当前节点：{{ reviewEditingNode.title }}</div>
        <el-input
          v-model="reviewDraft"
          type="textarea"
          :rows="5"
          maxlength="300"
          show-word-limit
          placeholder="请输入评审意见，例如：待补充边界条件"
        />
        <div v-if="currentNodeReview" class="meta-preview">
          <div class="note-preview-title">当前评审意见</div>
          <div class="note-preview-content">{{ currentNodeReview.text }}</div>
          <small>评审人ID：{{ currentNodeReview.reviewer_id }}，更新时间：{{ currentNodeReview.updated_at }}</small>
        </div>
      </div>
      <template #footer>
        <el-button :disabled="!reviewEditingNode || !currentNodeReview" @click="clearNodeReview">删除评审</el-button>
        <el-button @click="reviewDialogVisible = false">关闭</el-button>
        <el-button type="primary" @click="saveNodeReview">保存评审</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="searchDialogVisible" title="查找节点" width="520px">
      <el-input v-model="searchKeyword" placeholder="输入节点标题关键字" clearable @keyup.enter="selectSearchResult(0)" />
      <div class="search-result-list">
        <div
          v-for="(node, index) in searchResults"
          :key="node.node_id"
          class="search-result-item"
          @click="selectSearchResult(index)"
        >
          <span>{{ node.title }}</span>
          <small>#{{ node.node_id }}</small>
        </div>
        <el-empty v-if="searchKeyword && !searchResults.length" description="没有匹配节点" />
      </div>
    </el-dialog>

    <el-dialog v-model="snapshotDialogVisible" title="脑图版本快照" width="760px">
      <el-table :data="canvasSnapshots" border max-height="360">
        <el-table-column prop="name" label="快照名称" min-width="180" />
        <el-table-column prop="created_at" label="创建时间" width="190" />
        <el-table-column label="内容" min-width="220">
          <template #default="{ row }">
            标签 {{ Object.keys(row.data.nodeTagsMap || {}).length }} 个节点，备注 {{ Object.keys(row.data.nodeNotesMap || {}).length }} 个节点，评审 {{ Object.keys(row.data.nodeReviewsMap || {}).length }} 个节点
          </template>
        </el-table-column>
        <el-table-column label="操作" width="190">
          <template #default="{ row }">
            <el-button size="small" type="primary" @click="restoreCanvasSnapshot(row)">恢复</el-button>
            <el-button size="small" type="danger" @click="deleteCanvasSnapshot(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!canvasSnapshots.length" description="暂无快照，请先点击创建版本" />
      <template #footer>
        <el-button @click="snapshotDialogVisible = false">关闭</el-button>
        <el-button type="primary" @click="createCanvasSnapshot">创建新快照</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="shortcutDialogVisible" title="快捷键" width="590px" class="shortcut-dialog">
      <div class="shortcut-content">
        <section v-for="group in shortcutGroups" :key="group.title" class="shortcut-section">
          <h3>{{ group.title }}</h3>
          <div v-for="item in group.items" :key="item.label" class="shortcut-row">
            <div class="shortcut-keys">
              <template v-for="(key, index) in item.keys" :key="`${item.label}-${key}-${index}`">
                <span v-if="index > 0" class="key-plus">{{ item.separator || '+' }}</span>
                <kbd>{{ key }}</kbd>
              </template>
            </div>
            <div class="shortcut-label">{{ item.label }}</div>
          </div>
        </section>
      </div>
    </el-dialog>

    <VersionDrawer
      v-model="versionDrawerVisible"
      :current-node="selectedNode"
      @rollback-success="handleRollbackSuccess"
    />
  </div>
</template>

<script setup>
import { ElMessageBox } from 'element-plus'
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { createCaseNode, deleteCaseNode, getCaseTree, updateCaseNode } from '../api/case'
import CaseNodeForm from '../components/CaseNodeForm.vue'
import MindMapCanvas from '../components/MindMapCanvas.vue'
import VersionDrawer from '../components/VersionDrawer.vue'
import { NODE_TYPE_TEXT } from '../utils/constants'
import { confirmAction, showSuccess, showWarning } from '../utils/message'
import { getCurrentUserId } from '../utils/storage'

const route = useRoute()
const caseSetId = Number(route.params.id)
const customTagStorageKey = `rag_mindmap_custom_tags_${caseSetId}`
const nodeTagStorageKey = `rag_mindmap_node_tags_${caseSetId}`
const nodeNoteStorageKey = `rag_mindmap_node_notes_${caseSetId}`
const nodeLinkStorageKey = `rag_mindmap_node_links_${caseSetId}`
const nodeImageStorageKey = `rag_mindmap_node_images_${caseSetId}`
const nodeReviewStorageKey = `rag_mindmap_node_reviews_${caseSetId}`
const collapsedNodeStorageKey = `rag_mindmap_collapsed_nodes_${caseSetId}`
const appearanceStorageKey = `rag_mindmap_appearance_${caseSetId}`
const canvasSnapshotStorageKey = `rag_mindmap_snapshots_${caseSetId}`
const activeTab = ref('mind')
const labelTab = ref('system')
const customTagValue = ref('')
const customToolbarTags = ref([])
const treeData = ref([])
const selectedNode = ref(null)
const selectedNodeIds = ref([])
const editingNodeId = ref(null)
const nodeTagsMap = reactive({})
const nodeNotesMap = reactive({})
const nodeLinksMap = reactive({})
const nodeImagesMap = reactive({})
const nodeReviewsMap = reactive({})
const collapsedNodeIds = ref([])
const canvasSnapshots = ref([])
const zoom = ref(1)
const isMindmapViewportActive = ref(false)
const contextMenuVisible = ref(false)
const contextMenuPosition = reactive({ x: 0, y: 0 })
const detailDrawerVisible = ref(false)
const nodeDialogVisible = ref(false)
const versionDrawerVisible = ref(false)
const shortcutDialogVisible = ref(false)
const snapshotDialogVisible = ref(false)
const searchDialogVisible = ref(false)
const noteDialogVisible = ref(false)
const linkDialogVisible = ref(false)
const imageDialogVisible = ref(false)
const reviewDialogVisible = ref(false)
const noteEditingNode = ref(null)
const linkEditingNode = ref(null)
const imageEditingNode = ref(null)
const reviewEditingNode = ref(null)
const noteDraft = ref('')
const reviewDraft = ref('')
const linkForm = reactive({ title: '', url: '' })
const imageForm = reactive({ title: '', url: '' })
const searchKeyword = ref('')
const clipboardNode = ref(null)
const undoStack = ref([])
const redoStack = ref([])
const applyingHistory = ref(false)
const nodeDialogTitle = ref('新增节点')
const savingNode = ref(false)
const dialogMode = ref('create')
const parentIdForCreate = ref(null)
const nodeForm = reactive({
  title: '',
  node_type: 'folder',
  priority: 'P1',
  precondition: '',
  test_steps: '',
  expected_result: '',
  change_note: ''
})
const appearanceForm = reactive({
  theme: 'blue',
  rootColor: '#6ea4c8',
  nodeBorderColor: '#8db7d6',
  connectorColor: '#7faed0',
  nodeSize: 'normal',
  showTags: true,
  showMetaIcons: true,
  filterTag: '',
  expandLevel: 'all'
})

const systemToolbarTags = [
  { text: '主流程', color: '#bde7ff' },
  { text: '兼容性', color: '#bdf7df' },
  { text: '性能', color: '#9be8f0' },
  { text: '安全', color: '#a7a4ff' }
]

const businessToolbarTags = [
  { text: '前置条件', color: '#fff3b0' },
  { text: '执行步骤', color: '#ff9cf2' },
  { text: '预期结果', color: '#e6ff9b' },
  { text: '通用', color: '#bdf7df' },
  { text: 'WEB', color: '#ffb4b4' },
  { text: '单端测试', color: '#ffd9b5' },
  { text: 'UI测试', color: '#c4b5fd' }
]

const appearanceThemes = [
  { name: 'blue', label: '蓝色', rootColor: '#6ea4c8', nodeBorderColor: '#8db7d6', connectorColor: '#7faed0' },
  { name: 'green', label: '绿色', rootColor: '#16a34a', nodeBorderColor: '#86efac', connectorColor: '#22c55e' },
  { name: 'purple', label: '紫色', rootColor: '#7c3aed', nodeBorderColor: '#c4b5fd', connectorColor: '#8b5cf6' },
  { name: 'orange', label: '橙色', rootColor: '#f97316', nodeBorderColor: '#fdba74', connectorColor: '#fb923c' }
]

const visibleToolbarTags = computed(() => (labelTab.value === 'system' ? systemToolbarTags : businessToolbarTags.slice(0, 3)))
const allToolbarTags = computed(() => [...systemToolbarTags, ...businessToolbarTags, ...customToolbarTags.value])
const currentNodeNote = computed(() => String(nodeNotesMap[noteEditingNode.value?.node_id] || '').trim())
const currentNodeLink = computed(() => nodeLinksMap[linkEditingNode.value?.node_id] || null)
const currentNodeImage = computed(() => nodeImagesMap[imageEditingNode.value?.node_id] || null)
const currentNodeReview = computed(() => nodeReviewsMap[reviewEditingNode.value?.node_id] || null)
const selectedNodeParent = computed(() => (selectedNode.value ? findParentNode(treeData.value, selectedNode.value.node_id) : null))
const selectedNodeHasChildren = computed(() => Boolean(selectedNode.value?.children?.length))
const appearanceConfig = computed(() => ({ ...appearanceForm }))
const availableFilterTags = computed(() => {
  const tagSet = new Set()
  allToolbarTags.value.forEach(tag => tagSet.add(tag.text))
  Object.values(nodeTagsMap).forEach(tags => {
    ;(tags || []).forEach(tag => {
      if (tag?.text) {
        tagSet.add(tag.text)
      }
    })
  })
  return Array.from(tagSet)
})
const filteredTreeData = computed(() => filterTreeByTag(treeData.value, appearanceForm.filterTag))
const flatNodes = computed(() => flattenNodes(treeData.value))
const searchResults = computed(() => {
  const keyword = searchKeyword.value.trim().toLowerCase()
  if (!keyword) {
    return []
  }
  return flatNodes.value.filter(node => String(node.title || '').toLowerCase().includes(keyword)).slice(0, 20)
})

const shortcutGroups = [
  {
    title: '节点操作',
    items: [
      { keys: ['Enter'], label: '插入兄弟节点' },
      { keys: ['Tab'], label: '插入子节点' },
      { keys: ['Shift', 'Tab'], label: '选择父节点' },
      { keys: ['Delete', 'Backspace'], separator: '/', label: '删除节点' },
      { keys: ['Up', 'Down', 'Left', 'Right'], separator: '/', label: '节点导航' },
      { keys: ['Alt', 'Up', 'Down'], separator: '/', label: '向上/下调整顺序' },
      { keys: ['F2'], label: '编辑文本' },
      { keys: ['Ctrl', 'A'], label: '全选节点' },
      { keys: ['Ctrl', 'C'], label: '复制节点' },
      { keys: ['Ctrl', 'X'], label: '剪切暂存节点' },
      { keys: ['Ctrl', 'V'], label: '粘贴为子节点' },
      { keys: ['Ctrl', 'F'], label: '查找节点' },
      { keys: ['Ctrl', 'Z'], label: '撤销上一步' },
      { keys: ['/'], label: '展开/收起当前节点' },
      { keys: ['Ctrl', 'Y'], label: '重做上一步' },
      { keys: ['Ctrl', '1', '2', '3'], separator: '/', label: '添加前置条件、执行步骤、预期结果' },
      { keys: ['Ctrl', '0'], label: '清除当前节点展示标签' }
    ]
  },
  {
    title: '视野控制',
    items: [
      { keys: ['Alt', '拖动'], label: '拖动视野' },
      { keys: ['Alt', '右键拖动'], label: '拖动视野' },
      { keys: ['滚轮'], label: '移动视野' },
      { keys: ['触摸板'], label: '移动视野' },
      { keys: ['双击空白处'], label: '居中根节点' },
      { keys: ['Ctrl', '+', '-'], separator: '/', label: '放大/缩小视野' }
    ]
  }
]

const zoomDotStyle = computed(() => ({
  top: `${12 + (zoom.value - 0.6) * 75}px`
}))

const miniMapWindowStyle = computed(() => ({
  width: `${34 + (1.2 - zoom.value) * 18}px`,
  height: `${20 + (1.2 - zoom.value) * 10}px`
}))

const contextMenuStyle = computed(() => ({
  left: `${contextMenuPosition.x}px`,
  top: `${contextMenuPosition.y}px`
}))

function pushHistory(action) {
  if (applyingHistory.value) {
    return
  }
  undoStack.value = [...undoStack.value, action].slice(-50)
  redoStack.value = []
}

function cloneTagsMap() {
  return Object.fromEntries(
    Object.entries(nodeTagsMap).map(([nodeId, tags]) => [nodeId, (tags || []).map(tag => ({ ...tag }))])
  )
}

function restoreTagsMap(tagsMap) {
  Object.keys(nodeTagsMap).forEach(nodeId => {
    delete nodeTagsMap[nodeId]
  })
  Object.entries(tagsMap || {}).forEach(([nodeId, tags]) => {
    nodeTagsMap[nodeId] = (tags || []).map(tag => ({ ...tag }))
  })
  saveNodeTags()
}

function remapTagsMapNodeId(tagsMap, oldNodeId, newNodeId) {
  const nextMap = { ...(tagsMap || {}) }
  const oldKey = String(oldNodeId)
  const newKey = String(newNodeId)
  if (nextMap[oldKey]) {
    nextMap[newKey] = nextMap[oldKey]
    delete nextMap[oldKey]
  }
  return nextMap
}

function remapActionNodeId(action, oldNodeId, newNodeId) {
  if (action.nodeId === oldNodeId) {
    action.nodeId = newNodeId
  }
  if (action.before?.node_id === oldNodeId) {
    action.before.node_id = newNodeId
  }
  if (action.after?.node_id === oldNodeId) {
    action.after.node_id = newNodeId
  }
  if (Array.isArray(action.before)) {
    action.before.forEach(snapshot => {
      if (snapshot.node_id === oldNodeId) {
        snapshot.node_id = newNodeId
      }
    })
  }
  if (Array.isArray(action.after)) {
    action.after.forEach(snapshot => {
      if (snapshot.node_id === oldNodeId) {
        snapshot.node_id = newNodeId
      }
    })
  }
  if (action.type === 'tags') {
    action.before = remapTagsMapNodeId(action.before, oldNodeId, newNodeId)
    action.after = remapTagsMapNodeId(action.after, oldNodeId, newNodeId)
  }
}

function remapHistoryNodeId(oldNodeId, newNodeId) {
  ;[...undoStack.value, ...redoStack.value].forEach(action => remapActionNodeId(action, oldNodeId, newNodeId))
  restoreTagsMap(remapTagsMapNodeId(cloneTagsMap(), oldNodeId, newNodeId))
  saveNodeTags()
  const oldKey = String(oldNodeId)
  const newKey = String(newNodeId)
  if (nodeNotesMap[oldKey]) {
    nodeNotesMap[newKey] = nodeNotesMap[oldKey]
    delete nodeNotesMap[oldKey]
    saveNodeNotes()
  }
  if (nodeLinksMap[oldKey]) {
    nodeLinksMap[newKey] = nodeLinksMap[oldKey]
    delete nodeLinksMap[oldKey]
    saveNodeLinks()
  }
  if (nodeImagesMap[oldKey]) {
    nodeImagesMap[newKey] = nodeImagesMap[oldKey]
    delete nodeImagesMap[oldKey]
    saveNodeImages()
  }
  if (nodeReviewsMap[oldKey]) {
    nodeReviewsMap[newKey] = nodeReviewsMap[oldKey]
    delete nodeReviewsMap[oldKey]
    saveNodeReviews()
  }
}

function isSameTagsMap(before, after) {
  return JSON.stringify(before || {}) === JSON.stringify(after || {})
}

function getNodeSnapshot(node) {
  return {
    node_id: node.node_id,
    parent_id: findParentNode(treeData.value, node.node_id)?.node_id ?? null,
    title: node.title,
    node_type: node.node_type,
    precondition: node.precondition || null,
    test_steps: node.test_steps || null,
    expected_result: node.expected_result || null,
    priority: node.priority || 'P1',
    sort_order: node.sort_order ?? 0
  }
}

async function updateNodeBySnapshot(snapshot, changeNote) {
  return updateCaseNode(snapshot.node_id, {
    title: snapshot.title,
    node_type: snapshot.node_type,
    precondition: snapshot.precondition || null,
    test_steps: snapshot.test_steps || null,
    expected_result: snapshot.expected_result || null,
    priority: snapshot.priority || 'P1',
    sort_order: snapshot.sort_order,
    updated_by: getCurrentUserId(),
    change_note: changeNote
  })
}

async function undoLastAction() {
  if (applyingHistory.value) {
    return
  }
  const action = undoStack.value.at(-1)
  if (!action) {
    showWarning('暂无可撤销操作')
    return
  }
  applyingHistory.value = true
  try {
    await applyHistoryAction(action, 'undo')
    undoStack.value = undoStack.value.slice(0, -1)
    redoStack.value = [...redoStack.value, action]
    showSuccess('已撤销上一步操作')
  } finally {
    applyingHistory.value = false
  }
}

async function redoLastAction() {
  if (applyingHistory.value) {
    return
  }
  const action = redoStack.value.at(-1)
  if (!action) {
    showWarning('暂无可重做操作')
    return
  }
  applyingHistory.value = true
  try {
    await applyHistoryAction(action, 'redo')
    redoStack.value = redoStack.value.slice(0, -1)
    undoStack.value = [...undoStack.value, action]
    showSuccess('已重做上一步操作')
  } finally {
    applyingHistory.value = false
  }
}

async function applyHistoryAction(action, direction) {
  if (action.type === 'tags') {
    restoreTagsMap(direction === 'undo' ? action.before : action.after)
    return
  }
  if (action.type === 'title') {
    await updateNodeBySnapshot(direction === 'undo' ? action.before : action.after, direction === 'undo' ? '撤销标题编辑' : '重做标题编辑')
    await loadTree()
    selectNodeOnly(findNodeById(treeData.value, action.nodeId))
    return
  }
  if (action.type === 'create') {
    if (direction === 'undo') {
      const node = findNodeById(treeData.value, action.nodeId)
      if (node) {
        await deleteCaseNode(action.nodeId, { operator_id: getCurrentUserId() })
        await loadTree()
      }
      selectedNode.value = null
      selectedNodeIds.value = []
      editingNodeId.value = null
      return
    }
    const oldNodeId = action.nodeId
    const createdNode = await createCaseNode({
      case_set_id: caseSetId,
      parent_id: action.parentId,
      node_type: action.nodeType,
      title: action.title,
      precondition: null,
      test_steps: null,
      expected_result: null,
      priority: 'P1',
      created_by: getCurrentUserId()
    })
    remapHistoryNodeId(oldNodeId, createdNode.node_id)
    action.nodeId = createdNode.node_id
    await loadTree()
    selectNodeOnly(findNodeById(treeData.value, createdNode.node_id) || createdNode)
    return
  }
  if (action.type === 'sort') {
    const snapshots = direction === 'undo' ? action.before : action.after
    await Promise.all(snapshots.map(snapshot => updateNodeBySnapshot(snapshot, direction === 'undo' ? '撤销节点排序' : '重做节点排序')))
    await loadTree()
    selectNodeOnly(findNodeById(treeData.value, action.nodeId))
  }
}

async function loadTree() {
  treeData.value = await getCaseTree(caseSetId)
  syncCollapsedNodesWithExpandLevel()
  if (selectedNode.value) {
    selectedNode.value = findNodeById(treeData.value, selectedNode.value.node_id)
  }
}

function handleSelectNode(node) {
  selectedNode.value = node
  selectedNodeIds.value = [node.node_id]
  editingNodeId.value = null
  detailDrawerVisible.value = false
}

function handleBoxSelect(nodeIds) {
  updateBoxSelection(nodeIds)
}

function handleBoxSelectPreview(nodeIds) {
  updateBoxSelection(nodeIds)
}

function updateBoxSelection(nodeIds) {
  selectedNodeIds.value = nodeIds
  selectedNode.value = nodeIds.length ? findNodeById(treeData.value, nodeIds[0]) : null
  editingNodeId.value = null
  detailDrawerVisible.value = false
  contextMenuVisible.value = false
}

function handleEditRequest(node) {
  selectedNode.value = node
  selectedNodeIds.value = [node.node_id]
  editingNodeId.value = node.node_id
  detailDrawerVisible.value = false
}

function openContextMenu(payload) {
  selectedNode.value = payload.node
  selectedNodeIds.value = [payload.node.node_id]
  detailDrawerVisible.value = false
  contextMenuPosition.x = Math.max(16, Math.min(window.innerWidth - 320, payload.x - 150))
  contextMenuPosition.y = Math.max(16, Math.min(window.innerHeight - 360, payload.y - 120))
  contextMenuVisible.value = true
}

function closeContextMenu() {
  contextMenuVisible.value = false
}

function runContextAction(action) {
  contextMenuVisible.value = false
  action()
}

function addTagToSelectedNode(tag) {
  const targetNodeIds = selectedNodeIds.value.length ? selectedNodeIds.value : selectedNode.value ? [selectedNode.value.node_id] : []
  if (!targetNodeIds.length) {
    showWarning('请先选择一个或多个节点')
    return
  }
  const before = cloneTagsMap()
  const shouldRemove = targetNodeIds.every(nodeId => (nodeTagsMap[nodeId] || []).some(item => item.text === tag.text))
  targetNodeIds.forEach(nodeId => {
    const currentTags = nodeTagsMap[nodeId] || []
    if (shouldRemove) {
      nodeTagsMap[nodeId] = currentTags.filter(item => item.text !== tag.text)
      return
    }
    if (!currentTags.some(item => item.text === tag.text)) {
      nodeTagsMap[nodeId] = [...currentTags, tag]
    }
  })
  const after = cloneTagsMap()
  if (!isSameTagsMap(before, after)) {
    pushHistory({ type: 'tags', before, after })
    saveNodeTags()
  }
}

function handleCustomTagChange(value) {
  const tagText = String(value || '').trim()
  if (!tagText) {
    return
  }
  let tag = allToolbarTags.value.find(item => item.text === tagText)
  if (!tag) {
    tag = { text: tagText, color: '#dbeafe' }
    customToolbarTags.value = [...customToolbarTags.value, tag]
    saveCustomTags()
  }
  addTagToSelectedNode(tag)
  customTagValue.value = ''
}

function loadCustomTags() {
  try {
    const savedTags = JSON.parse(window.localStorage.getItem(customTagStorageKey) || '[]')
    customToolbarTags.value = Array.isArray(savedTags) ? savedTags.filter(tag => tag?.text) : []
  } catch {
    customToolbarTags.value = []
  }
}

function saveCustomTags() {
  window.localStorage.setItem(customTagStorageKey, JSON.stringify(customToolbarTags.value))
}

function loadNodeTags() {
  try {
    const savedTagsMap = JSON.parse(window.localStorage.getItem(nodeTagStorageKey) || '{}')
    Object.keys(nodeTagsMap).forEach(nodeId => {
      delete nodeTagsMap[nodeId]
    })
    Object.entries(savedTagsMap || {}).forEach(([nodeId, tags]) => {
      const validTags = Array.isArray(tags) ? tags.filter(tag => tag?.text) : []
      if (validTags.length) {
        nodeTagsMap[nodeId] = validTags
      }
    })
  } catch {
    Object.keys(nodeTagsMap).forEach(nodeId => {
      delete nodeTagsMap[nodeId]
    })
  }
}

function saveNodeTags() {
  const normalizedTagsMap = Object.fromEntries(
    Object.entries(nodeTagsMap)
      .map(([nodeId, tags]) => [nodeId, Array.isArray(tags) ? tags.filter(tag => tag?.text) : []])
      .filter(([, tags]) => tags.length)
  )
  window.localStorage.setItem(nodeTagStorageKey, JSON.stringify(normalizedTagsMap))
}

function loadNodeNotes() {
  try {
    const savedNotes = JSON.parse(window.localStorage.getItem(nodeNoteStorageKey) || '{}')
    Object.keys(nodeNotesMap).forEach(nodeId => {
      delete nodeNotesMap[nodeId]
    })
    Object.entries(savedNotes || {}).forEach(([nodeId, note]) => {
      const noteText = String(note || '').trim()
      if (noteText) {
        nodeNotesMap[nodeId] = noteText
      }
    })
  } catch {
    Object.keys(nodeNotesMap).forEach(nodeId => {
      delete nodeNotesMap[nodeId]
    })
  }
}

function saveNodeNotes() {
  window.localStorage.setItem(nodeNoteStorageKey, JSON.stringify(nodeNotesMap))
}

function loadPersistedMap(storageKey, targetMap) {
  try {
    const savedMap = JSON.parse(window.localStorage.getItem(storageKey) || '{}')
    Object.keys(targetMap).forEach(nodeId => {
      delete targetMap[nodeId]
    })
    Object.entries(savedMap || {}).forEach(([nodeId, value]) => {
      if (value) {
        targetMap[nodeId] = value
      }
    })
  } catch {
    Object.keys(targetMap).forEach(nodeId => {
      delete targetMap[nodeId]
    })
  }
}

function savePersistedMap(storageKey, targetMap) {
  window.localStorage.setItem(storageKey, JSON.stringify(targetMap))
}

function clonePlainObject(value) {
  return JSON.parse(JSON.stringify(value || {}))
}

function loadCanvasSnapshots() {
  try {
    const savedSnapshots = JSON.parse(window.localStorage.getItem(canvasSnapshotStorageKey) || '[]')
    canvasSnapshots.value = Array.isArray(savedSnapshots) ? savedSnapshots : []
  } catch {
    canvasSnapshots.value = []
  }
}

function saveCanvasSnapshots() {
  window.localStorage.setItem(canvasSnapshotStorageKey, JSON.stringify(canvasSnapshots.value))
}

async function createCanvasSnapshot() {
  handleSaveCanvas()
  const defaultName = `快照-${new Date().toLocaleString()}`
  const result = await ElMessageBox.prompt('请输入快照名称', '创建脑图版本快照', {
    confirmButtonText: '创建',
    cancelButtonText: '取消',
    inputValue: defaultName,
    inputPlaceholder: defaultName
  }).catch(() => null)
  if (!result) {
    return
  }
  const snapshot = {
    id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
    name: String(result.value || defaultName).trim() || defaultName,
    created_at: new Date().toLocaleString(),
    data: {
      nodeTagsMap: clonePlainObject(nodeTagsMap),
      nodeNotesMap: clonePlainObject(nodeNotesMap),
      nodeLinksMap: clonePlainObject(nodeLinksMap),
      nodeImagesMap: clonePlainObject(nodeImagesMap),
      nodeReviewsMap: clonePlainObject(nodeReviewsMap),
      collapsedNodeIds: [...collapsedNodeIds.value],
      appearance: clonePlainObject(appearanceForm)
    }
  }
  canvasSnapshots.value = [snapshot, ...canvasSnapshots.value].slice(0, 20)
  saveCanvasSnapshots()
  snapshotDialogVisible.value = true
  showSuccess('脑图版本快照已创建')
}

async function restoreCanvasSnapshot(snapshot) {
  await confirmAction(`确认恢复快照「${snapshot.name}」吗？当前页面标签、备注、链接、图片、评审和外观会被覆盖。`, '恢复脑图快照')
  restoreTagsMap(snapshot.data.nodeTagsMap || {})
  restorePersistedMap(nodeNotesMap, snapshot.data.nodeNotesMap || {})
  restorePersistedMap(nodeLinksMap, snapshot.data.nodeLinksMap || {})
  restorePersistedMap(nodeImagesMap, snapshot.data.nodeImagesMap || {})
  restorePersistedMap(nodeReviewsMap, snapshot.data.nodeReviewsMap || {})
  collapsedNodeIds.value = Array.isArray(snapshot.data.collapsedNodeIds) ? snapshot.data.collapsedNodeIds : []
  Object.assign(appearanceForm, snapshot.data.appearance || {})
  handleSaveCanvas()
  showSuccess('脑图版本快照已恢复')
}

async function deleteCanvasSnapshot(snapshotId) {
  await confirmAction('确认删除这个脑图版本快照吗？')
  canvasSnapshots.value = canvasSnapshots.value.filter(snapshot => snapshot.id !== snapshotId)
  saveCanvasSnapshots()
  showSuccess('脑图版本快照已删除')
}

function restorePersistedMap(targetMap, sourceMap) {
  Object.keys(targetMap).forEach(key => {
    delete targetMap[key]
  })
  Object.entries(sourceMap || {}).forEach(([key, value]) => {
    if (value) {
      targetMap[key] = value
    }
  })
}

function applyAppearanceTheme() {
  const theme = appearanceThemes.find(item => item.name === appearanceForm.theme)
  if (!theme) {
    return
  }
  appearanceForm.rootColor = theme.rootColor
  appearanceForm.nodeBorderColor = theme.nodeBorderColor
  appearanceForm.connectorColor = theme.connectorColor
  saveAppearanceSettings()
}

function loadAppearanceSettings() {
  try {
    const savedSettings = JSON.parse(window.localStorage.getItem(appearanceStorageKey) || '{}')
    Object.assign(appearanceForm, {
      theme: savedSettings.theme || appearanceForm.theme,
      rootColor: savedSettings.rootColor || appearanceForm.rootColor,
      nodeBorderColor: savedSettings.nodeBorderColor || appearanceForm.nodeBorderColor,
      connectorColor: savedSettings.connectorColor || appearanceForm.connectorColor,
      nodeSize: savedSettings.nodeSize || appearanceForm.nodeSize,
      showTags: typeof savedSettings.showTags === 'boolean' ? savedSettings.showTags : appearanceForm.showTags,
      showMetaIcons: typeof savedSettings.showMetaIcons === 'boolean' ? savedSettings.showMetaIcons : appearanceForm.showMetaIcons,
      filterTag: savedSettings.filterTag || '',
      expandLevel: savedSettings.expandLevel || 'all'
    })
  } catch {
    resetAppearanceSettings(false)
  }
}

function saveAppearanceSettings() {
  window.localStorage.setItem(appearanceStorageKey, JSON.stringify(appearanceForm))
}

function handleFilterTagChange() {
  if (selectedNode.value && !findNodeById(filteredTreeData.value, selectedNode.value.node_id)) {
    selectedNode.value = null
    selectedNodeIds.value = []
  }
  saveAppearanceSettings()
}

function applyExpandLevel(level) {
  appearanceForm.expandLevel = String(level || 'all')
  if (appearanceForm.expandLevel === 'all') {
    expandAllNodes(false)
    saveAppearanceSettings()
    showSuccess('已展开全部层级')
    return
  }
  syncCollapsedNodesWithExpandLevel()
  saveAppearanceSettings()
  showSuccess(`已展开到 ${Number(appearanceForm.expandLevel)} 层`)
}

function syncCollapsedNodesWithExpandLevel() {
  if (appearanceForm.expandLevel === 'all') {
    return
  }
  const maxDepth = Number(appearanceForm.expandLevel)
  if (!Number.isFinite(maxDepth) || maxDepth < 1) {
    return
  }
  collapsedNodeIds.value = getCollapsedNodeIdsByLevel(treeData.value, maxDepth)
  saveCollapsedNodes()
}

function getCollapsedNodeIdsByLevel(nodes, maxDepth, depth = 1) {
  const result = []
  for (const node of nodes) {
    if (node.children?.length && depth >= maxDepth) {
      result.push(node.node_id)
      continue
    }
    result.push(...getCollapsedNodeIdsByLevel(node.children || [], maxDepth, depth + 1))
  }
  return result
}

function filterTreeByTag(nodes, filterTag) {
  if (!filterTag) {
    return nodes
  }
  return nodes
    .map(node => filterNodeByTag(node, filterTag))
    .filter(Boolean)
}

function filterNodeByTag(node, filterTag) {
  const currentNodeMatches = nodeHasTag(node.node_id, filterTag)
  const filteredChildren = filterTreeByTag(node.children || [], filterTag)
  if (!currentNodeMatches && !filteredChildren.length) {
    return null
  }
  return {
    ...node,
    children: currentNodeMatches ? node.children || [] : filteredChildren
  }
}

function nodeHasTag(nodeId, tagText) {
  return (nodeTagsMap[nodeId] || []).some(tag => tag.text === tagText)
}

function resetAppearanceSettings(showMessage = true) {
  Object.assign(appearanceForm, {
    theme: 'blue',
    rootColor: '#6ea4c8',
    nodeBorderColor: '#8db7d6',
    connectorColor: '#7faed0',
    nodeSize: 'normal',
    showTags: true,
    showMetaIcons: true,
    filterTag: '',
    expandLevel: 'all'
  })
  saveAppearanceSettings()
  if (showMessage) {
    showSuccess('已恢复默认外观')
  }
}

function loadCollapsedNodes() {
  try {
    const savedNodeIds = JSON.parse(window.localStorage.getItem(collapsedNodeStorageKey) || '[]')
    collapsedNodeIds.value = Array.isArray(savedNodeIds) ? savedNodeIds.map(Number).filter(Boolean) : []
  } catch {
    collapsedNodeIds.value = []
  }
}

function saveCollapsedNodes() {
  window.localStorage.setItem(collapsedNodeStorageKey, JSON.stringify(collapsedNodeIds.value))
}

function loadNodeLinks() {
  loadPersistedMap(nodeLinkStorageKey, nodeLinksMap)
}

function saveNodeLinks() {
  savePersistedMap(nodeLinkStorageKey, nodeLinksMap)
}

function loadNodeImages() {
  loadPersistedMap(nodeImageStorageKey, nodeImagesMap)
}

function saveNodeImages() {
  savePersistedMap(nodeImageStorageKey, nodeImagesMap)
}

function loadNodeReviews() {
  loadPersistedMap(nodeReviewStorageKey, nodeReviewsMap)
}

function saveNodeReviews() {
  savePersistedMap(nodeReviewStorageKey, nodeReviewsMap)
}

function isHttpUrl(url) {
  try {
    const parsedUrl = new URL(url)
    return parsedUrl.protocol === 'http:' || parsedUrl.protocol === 'https:'
  } catch {
    return false
  }
}

function openNoteDialog(node) {
  if (!node) {
    showWarning('请先选择一个节点')
    return
  }
  selectedNode.value = node
  selectedNodeIds.value = [node.node_id]
  noteEditingNode.value = node
  noteDraft.value = nodeNotesMap[node.node_id] || ''
  noteDialogVisible.value = true
}

function saveNodeNote() {
  if (!noteEditingNode.value) {
    return
  }
  const noteText = noteDraft.value.trim()
  if (noteText) {
    nodeNotesMap[noteEditingNode.value.node_id] = noteText
    showSuccess('备注已保存')
  } else {
    delete nodeNotesMap[noteEditingNode.value.node_id]
    showSuccess('备注已清空')
  }
  saveNodeNotes()
  noteDialogVisible.value = false
}

function clearNodeNote() {
  if (!noteEditingNode.value) {
    return
  }
  delete nodeNotesMap[noteEditingNode.value.node_id]
  noteDraft.value = ''
  saveNodeNotes()
  showSuccess('备注已删除')
  noteDialogVisible.value = false
}

function openLinkDialog(node) {
  if (!node) {
    showWarning('请先选择一个节点')
    return
  }
  selectedNode.value = node
  selectedNodeIds.value = [node.node_id]
  linkEditingNode.value = node
  const currentLink = nodeLinksMap[node.node_id] || {}
  linkForm.title = currentLink.title || ''
  linkForm.url = currentLink.url || ''
  linkDialogVisible.value = true
}

function saveNodeLink() {
  if (!linkEditingNode.value) {
    return
  }
  const url = linkForm.url.trim()
  if (!url) {
    showWarning('请填写链接地址')
    return
  }
  if (!isHttpUrl(url)) {
    showWarning('链接地址必须以 http:// 或 https:// 开头')
    return
  }
  nodeLinksMap[linkEditingNode.value.node_id] = {
    title: linkForm.title.trim() || url,
    url
  }
  saveNodeLinks()
  showSuccess('链接已保存')
  linkDialogVisible.value = false
}

function clearNodeLink() {
  if (!linkEditingNode.value) {
    return
  }
  delete nodeLinksMap[linkEditingNode.value.node_id]
  linkForm.title = ''
  linkForm.url = ''
  saveNodeLinks()
  showSuccess('链接已删除')
  linkDialogVisible.value = false
}

function openImageDialog(node) {
  if (!node) {
    showWarning('请先选择一个节点')
    return
  }
  selectedNode.value = node
  selectedNodeIds.value = [node.node_id]
  imageEditingNode.value = node
  const currentImage = nodeImagesMap[node.node_id] || {}
  imageForm.title = currentImage.title || ''
  imageForm.url = currentImage.url || ''
  imageDialogVisible.value = true
}

function saveNodeImage() {
  if (!imageEditingNode.value) {
    return
  }
  const url = imageForm.url.trim()
  if (!url) {
    showWarning('请填写图片地址')
    return
  }
  if (!isHttpUrl(url)) {
    showWarning('图片地址必须以 http:// 或 https:// 开头')
    return
  }
  nodeImagesMap[imageEditingNode.value.node_id] = {
    title: imageForm.title.trim() || '节点图片',
    url
  }
  saveNodeImages()
  showSuccess('图片已保存')
  imageDialogVisible.value = false
}

function clearNodeImage() {
  if (!imageEditingNode.value) {
    return
  }
  delete nodeImagesMap[imageEditingNode.value.node_id]
  imageForm.title = ''
  imageForm.url = ''
  saveNodeImages()
  showSuccess('图片已删除')
  imageDialogVisible.value = false
}

function openReviewDialog(node) {
  if (!node) {
    showWarning('请先选择一个节点')
    return
  }
  selectedNode.value = node
  selectedNodeIds.value = [node.node_id]
  reviewEditingNode.value = node
  reviewDraft.value = nodeReviewsMap[node.node_id]?.text || ''
  reviewDialogVisible.value = true
}

function saveNodeReview() {
  if (!reviewEditingNode.value) {
    return
  }
  const reviewText = reviewDraft.value.trim()
  if (!reviewText) {
    showWarning('请填写评审意见')
    return
  }
  nodeReviewsMap[reviewEditingNode.value.node_id] = {
    text: reviewText,
    reviewer_id: getCurrentUserId(),
    updated_at: new Date().toLocaleString()
  }
  saveNodeReviews()
  showSuccess('评审意见已保存')
  reviewDialogVisible.value = false
}

function clearNodeReview() {
  if (!reviewEditingNode.value) {
    return
  }
  delete nodeReviewsMap[reviewEditingNode.value.node_id]
  reviewDraft.value = ''
  saveNodeReviews()
  showSuccess('评审意见已删除')
  reviewDialogVisible.value = false
}

function openSearchDialog() {
  searchDialogVisible.value = true
}

function selectSearchResult(index) {
  const node = searchResults.value[index]
  if (!node) {
    return
  }
  expandNodeAncestors(node.node_id)
  selectNodeOnly(node)
  searchDialogVisible.value = false
}

function selectNodeOnly(node) {
  selectedNode.value = node
  selectedNodeIds.value = node ? [node.node_id] : []
  editingNodeId.value = null
  detailDrawerVisible.value = false
  contextMenuVisible.value = false
}

function toggleNodeCollapse(node) {
  if (!node?.children?.length) {
    return
  }
  if (collapsedNodeIds.value.includes(node.node_id)) {
    collapsedNodeIds.value = collapsedNodeIds.value.filter(nodeId => nodeId !== node.node_id)
  } else {
    collapsedNodeIds.value = [...collapsedNodeIds.value, node.node_id]
  }
  saveCollapsedNodes()
}

function toggleSelectedNodeCollapse() {
  if (!selectedNode.value?.children?.length) {
    showWarning('当前节点没有子节点')
    return
  }
  toggleNodeCollapse(selectedNode.value)
}

function expandAllNodes(showMessage = true) {
  collapsedNodeIds.value = []
  appearanceForm.expandLevel = 'all'
  saveCollapsedNodes()
  saveAppearanceSettings()
  if (showMessage) {
    showSuccess('已展开全部节点')
  }
}

function collapseAllNodes() {
  collapsedNodeIds.value = flatNodes.value.filter(node => node.children?.length).map(node => node.node_id)
  appearanceForm.expandLevel = '1'
  saveCollapsedNodes()
  saveAppearanceSettings()
  showSuccess(`已收起 ${collapsedNodeIds.value.length} 个节点`)
}

function expandNodeAncestors(nodeId) {
  const ancestorIds = []
  let parent = findParentNode(treeData.value, nodeId)
  while (parent) {
    ancestorIds.push(parent.node_id)
    parent = findParentNode(treeData.value, parent.node_id)
  }
  if (!ancestorIds.length) {
    return
  }
  collapsedNodeIds.value = collapsedNodeIds.value.filter(collapsedNodeId => !ancestorIds.includes(collapsedNodeId))
  saveCollapsedNodes()
}

function selectRelativeNode(direction) {
  if (!selectedNode.value || !flatNodes.value.length) {
    return
  }
  const currentIndex = flatNodes.value.findIndex(node => node.node_id === selectedNode.value.node_id)
  if (currentIndex === -1) {
    return
  }
  if (direction === 'previous') {
    selectNodeOnly(flatNodes.value[Math.max(0, currentIndex - 1)])
    return
  }
  if (direction === 'next') {
    selectNodeOnly(flatNodes.value[Math.min(flatNodes.value.length - 1, currentIndex + 1)])
    return
  }
  if (direction === 'child') {
    const child = selectedNode.value.children?.[0]
    if (child) {
      if (collapsedNodeIds.value.includes(selectedNode.value.node_id)) {
        toggleNodeCollapse(selectedNode.value)
      }
      selectNodeOnly(child)
    }
    return
  }
  if (direction === 'parent') {
    const parent = findParentNode(treeData.value, selectedNode.value.node_id)
    if (parent) {
      selectNodeOnly(parent)
    }
  }
}

function addShortcutTag(index) {
  const tag = businessToolbarTags[index]
  if (tag) {
    addTagToSelectedNode(tag)
  }
}

function clearSelectedTags() {
  const targetNodeIds = selectedNodeIds.value.length ? selectedNodeIds.value : selectedNode.value ? [selectedNode.value.node_id] : []
  if (!targetNodeIds.length) {
    showWarning('请先选择一个或多个节点')
    return
  }
  const before = cloneTagsMap()
  targetNodeIds.forEach(nodeId => {
    nodeTagsMap[nodeId] = []
  })
  const after = cloneTagsMap()
  if (!isSameTagsMap(before, after)) {
    pushHistory({ type: 'tags', before, after })
    saveNodeTags()
  }
}

function copySelectedNode() {
  if (!selectedNode.value) {
    return
  }
  clipboardNode.value = cloneNodePayload(selectedNode.value)
  showSuccess('节点已复制')
}

function cutSelectedNode() {
  copySelectedNode()
  showSuccess('节点已剪切到暂存区，粘贴后请手动删除原节点')
}

async function pasteClipboardNode() {
  if (!selectedNode.value || !clipboardNode.value) {
    return
  }
  const created = await createNodeFromClipboard(clipboardNode.value, selectedNode.value.node_id)
  await loadTree()
  selectedNode.value = findNodeById(treeData.value, created.node_id) || created
  selectedNodeIds.value = [selectedNode.value.node_id]
  editingNodeId.value = selectedNode.value.node_id
}

function canMoveSelectedNode(direction) {
  if (!selectedNode.value) {
    return false
  }
  const siblings = getSiblings(selectedNode.value).slice().sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0) || a.node_id - b.node_id)
  const index = siblings.findIndex(node => node.node_id === selectedNode.value.node_id)
  if (direction === 'up') {
    return index > 0
  }
  return index !== -1 && index < siblings.length - 1
}

async function moveSelectedNode(direction) {
  if (!selectedNode.value) {
    return
  }
  const siblings = getSiblings(selectedNode.value).slice().sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0) || a.node_id - b.node_id)
  const index = siblings.findIndex(node => node.node_id === selectedNode.value.node_id)
  const targetIndex = direction === 'up' ? index - 1 : index + 1
  const target = siblings[targetIndex]
  if (!target) {
    return
  }
  const before = [getNodeSnapshot(selectedNode.value), getNodeSnapshot(target)]
  const currentOrder = selectedNode.value.sort_order || index
  const targetOrder = target.sort_order || targetIndex
  await Promise.all([
    updateNodeSortOrder(selectedNode.value, targetOrder),
    updateNodeSortOrder(target, currentOrder)
  ])
  pushHistory({
    type: 'sort',
    nodeId: selectedNode.value.node_id,
    before,
    after: [
      { ...before[0], sort_order: targetOrder },
      { ...before[1], sort_order: currentOrder }
    ]
  })
  await loadTree()
  selectedNode.value = findNodeById(treeData.value, selectedNode.value.node_id)
}

function resetForm() {
  Object.assign(nodeForm, {
    title: '',
    node_type: 'folder',
    priority: 'P1',
    precondition: '',
    test_steps: '',
    expected_result: '',
    change_note: ''
  })
}

function fillFormFromNode(node) {
  Object.assign(nodeForm, {
    title: node.title || '',
    node_type: node.node_type || 'folder',
    priority: node.priority || 'P1',
    precondition: node.precondition || '',
    test_steps: node.test_steps || '',
    expected_result: node.expected_result || '',
    change_note: ''
  })
}

async function openCreateRoot() {
  await createInstantNode(null, 'folder')
}

async function openCreateChild() {
  if (!selectedNode.value) {
    return
  }
  await createInstantNode(selectedNode.value.node_id, 'case')
}

async function openSiblingNode() {
  if (!selectedNode.value) {
    return
  }
  const parentNode = findParentNode(treeData.value, selectedNode.value.node_id)
  await createInstantNode(parentNode?.node_id ?? null, selectedNode.value.node_type || 'case')
}

function openEditNode() {
  if (selectedNode.value) {
    editingNodeId.value = selectedNode.value.node_id
  }
}

async function createInstantNode(parentId, nodeType) {
  const createdNode = await createCaseNode({
    case_set_id: caseSetId,
    parent_id: parentId,
    node_type: nodeType,
    title: '新建节点',
    precondition: null,
    test_steps: null,
    expected_result: null,
    priority: 'P1',
    created_by: getCurrentUserId()
  })
  pushHistory({
    type: 'create',
    nodeId: createdNode.node_id,
    parentId,
    nodeType,
    title: '新建节点'
  })
  await loadTree()
  selectedNode.value = findNodeById(treeData.value, createdNode.node_id) || createdNode
  selectedNodeIds.value = [selectedNode.value.node_id]
  editingNodeId.value = selectedNode.value.node_id
  detailDrawerVisible.value = false
}

function handleSaveCanvas() {
  saveNodeTags()
  saveCustomTags()
  saveNodeNotes()
  saveNodeLinks()
  saveNodeImages()
  saveNodeReviews()
  saveCollapsedNodes()
  saveAppearanceSettings()
  showSuccess('当前脑图标签、备注、链接、图片、评审、折叠状态和外观已保存')
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

function isEditingTarget(target) {
  const tagName = target?.tagName?.toLowerCase()
  return ['input', 'textarea', 'select'].includes(tagName) || target?.isContentEditable
}

function handleKeydown(event) {
  if (isEditingTarget(event.target)) {
    return
  }
  if (event.key === 'Escape') {
    closeContextMenu()
    shortcutDialogVisible.value = false
    snapshotDialogVisible.value = false
    searchDialogVisible.value = false
    noteDialogVisible.value = false
    linkDialogVisible.value = false
    imageDialogVisible.value = false
    reviewDialogVisible.value = false
    editingNodeId.value = null
    return
  }
  if (shortcutDialogVisible.value || snapshotDialogVisible.value || nodeDialogVisible.value || noteDialogVisible.value || linkDialogVisible.value || imageDialogVisible.value || reviewDialogVisible.value || versionDrawerVisible.value || searchDialogVisible.value) {
    return
  }

  const key = event.key.toLowerCase()
  const isCtrl = event.ctrlKey || event.metaKey

  if (isCtrl && (event.key === '=' || event.key === '+' || event.key === '-')) {
    if (!isMindmapViewportActive.value) {
      return
    }
    event.preventDefault()
    if (event.key === '-') {
      zoomOut()
    } else {
      zoomIn()
    }
    return
  }
  if (isCtrl && key === 'z') {
    event.preventDefault()
    undoLastAction()
    return
  }
  if (isCtrl && key === 'y') {
    event.preventDefault()
    redoLastAction()
    return
  }
  if (isCtrl && key === 'f') {
    event.preventDefault()
    openSearchDialog()
    return
  }
  if (event.key === '/') {
    event.preventDefault()
    toggleSelectedNodeCollapse()
    return
  }
  if (isCtrl && key === 'a') {
    event.preventDefault()
    const nodeIds = flatNodes.value.map(node => node.node_id)
    updateBoxSelection(nodeIds)
    showSuccess(`已全选 ${nodeIds.length} 个节点`)
    return
  }
  if (isCtrl && key === 'c') {
    event.preventDefault()
    copySelectedNode()
    return
  }
  if (isCtrl && key === 'x') {
    event.preventDefault()
    cutSelectedNode()
    return
  }
  if (isCtrl && key === 'v') {
    event.preventDefault()
    pasteClipboardNode()
    return
  }
  if (isCtrl && key === '1') {
    event.preventDefault()
    addShortcutTag(0)
    return
  }
  if (isCtrl && key === '2') {
    event.preventDefault()
    addShortcutTag(1)
    return
  }
  if (isCtrl && key === '3') {
    event.preventDefault()
    addShortcutTag(2)
    return
  }
  if (isCtrl && key === '0') {
    event.preventDefault()
    clearSelectedTags()
    return
  }
  if (!selectedNode.value) {
    return
  }
  if (event.altKey && event.key === 'ArrowUp') {
    event.preventDefault()
    moveSelectedNode('up')
    return
  }
  if (event.altKey && event.key === 'ArrowDown') {
    event.preventDefault()
    moveSelectedNode('down')
    return
  }
  if (event.key === 'ArrowUp') {
    event.preventDefault()
    selectRelativeNode('previous')
    return
  }
  if (event.key === 'ArrowDown') {
    event.preventDefault()
    selectRelativeNode('next')
    return
  }
  if (event.key === 'ArrowLeft') {
    event.preventDefault()
    selectRelativeNode('parent')
    return
  }
  if (event.key === 'ArrowRight') {
    event.preventDefault()
    selectRelativeNode('child')
    return
  }
  if (event.key === 'F2') {
    event.preventDefault()
    openEditNode()
    return
  }
  if (event.key === 'Enter' && !event.altKey) {
    event.preventDefault()
    openSiblingNode()
    return
  }
  if (event.key === 'Tab') {
    event.preventDefault()
    if (event.shiftKey) {
      selectRelativeNode('parent')
    } else {
      openCreateChild()
    }
    return
  }
  if (event.key === 'Delete' || event.key === 'Backspace') {
    event.preventDefault()
    handleDeleteNode()
  }
}

async function updateNodeSortOrder(node, sortOrder) {
  return updateCaseNode(node.node_id, {
    title: node.title,
    node_type: node.node_type,
    precondition: node.precondition || null,
    test_steps: node.test_steps || null,
    expected_result: node.expected_result || null,
    priority: node.priority || 'P1',
    sort_order: sortOrder,
    updated_by: getCurrentUserId(),
    change_note: '快捷键调整节点顺序'
  })
}

async function createNodeFromClipboard(node, parentId) {
  const created = await createCaseNode({
    case_set_id: caseSetId,
    parent_id: parentId,
    node_type: node.node_type || 'case',
    title: `${node.title || '复制节点'}`,
    precondition: node.precondition || null,
    test_steps: node.test_steps || null,
    expected_result: node.expected_result || null,
    priority: node.priority || 'P1',
    sort_order: 0,
    created_by: getCurrentUserId()
  })
  for (const child of node.children || []) {
    await createNodeFromClipboard(child, created.node_id)
  }
  return created
}

function cloneNodePayload(node) {
  return {
    title: node.title,
    node_type: node.node_type,
    precondition: node.precondition,
    test_steps: node.test_steps,
    expected_result: node.expected_result,
    priority: node.priority,
    children: (node.children || []).map(cloneNodePayload)
  }
}

async function handleTitleSave({ node, title }) {
  const before = getNodeSnapshot(node)
  await updateCaseNode(node.node_id, {
    title,
    node_type: node.node_type,
    precondition: node.precondition || null,
    test_steps: node.test_steps || null,
    expected_result: node.expected_result || null,
    priority: node.priority || 'P1',
    updated_by: getCurrentUserId(),
    change_note: '前端直接编辑节点标题'
  })
  pushHistory({
    type: 'title',
    nodeId: node.node_id,
    before,
    after: { ...before, title }
  })
  editingNodeId.value = null
  await loadTree()
  selectedNode.value = findNodeById(treeData.value, node.node_id)
}

async function handleSaveNode() {
  if (!nodeForm.title.trim()) {
    return
  }
  savingNode.value = true
  try {
    if (dialogMode.value === 'create') {
      await createCaseNode({
        case_set_id: caseSetId,
        parent_id: parentIdForCreate.value,
        node_type: nodeForm.node_type,
        title: nodeForm.title,
        precondition: nodeForm.precondition || null,
        test_steps: nodeForm.test_steps || null,
        expected_result: nodeForm.expected_result || null,
        priority: nodeForm.priority,
        created_by: getCurrentUserId()
      })
      showSuccess('节点创建成功')
    } else {
      await updateCaseNode(selectedNode.value.node_id, {
        title: nodeForm.title,
        node_type: nodeForm.node_type,
        precondition: nodeForm.precondition || null,
        test_steps: nodeForm.test_steps || null,
        expected_result: nodeForm.expected_result || null,
        priority: nodeForm.priority,
        updated_by: getCurrentUserId(),
        change_note: nodeForm.change_note || '前端编辑节点'
      })
      showSuccess('节点修改成功，已生成历史版本')
    }
    nodeDialogVisible.value = false
    await loadTree()
  } finally {
    savingNode.value = false
  }
}

async function handleDeleteNode() {
  await confirmAction(`确认删除节点「${selectedNode.value.title}」吗？如果有子节点也会一起逻辑删除。`)
  await deleteCaseNode(selectedNode.value.node_id, { operator_id: getCurrentUserId() })
  showSuccess('节点删除成功，历史版本已保留')
  selectedNode.value = null
  selectedNodeIds.value = []
  detailDrawerVisible.value = false
  await loadTree()
}

async function handleRollbackSuccess() {
  await loadTree()
}

function flattenNodes(nodes) {
  const result = []
  for (const node of nodes) {
    result.push(node)
    result.push(...flattenNodes(node.children || []))
  }
  return result
}

function findNodeById(nodes, nodeId) {
  for (const node of nodes) {
    if (node.node_id === nodeId) {
      return node
    }
    const child = findNodeById(node.children || [], nodeId)
    if (child) {
      return child
    }
  }
  return null
}

function findParentNode(nodes, nodeId, parent = null) {
  for (const node of nodes) {
    if (node.node_id === nodeId) {
      return parent
    }
    const found = findParentNode(node.children || [], nodeId, node)
    if (found) {
      return found
    }
  }
  return null
}

function getSiblings(node) {
  const parent = findParentNode(treeData.value, node.node_id)
  return parent ? parent.children || [] : treeData.value
}

onMounted(() => {
  loadCustomTags()
  loadNodeTags()
  loadNodeNotes()
  loadNodeLinks()
  loadNodeImages()
  loadNodeReviews()
  loadCollapsedNodes()
  loadAppearanceSettings()
  loadCanvasSnapshots()
  loadTree()
  window.addEventListener('keydown', handleKeydown)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleKeydown)
})
</script>

<style scoped>
.case-detail {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.editor-header,
.page-header-row,
.node-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
}

.editor-header {
  align-items: flex-start;
  padding-top: 12px;
  padding-bottom: 12px;
}

.breadcrumb {
  margin-bottom: 10px;
  color: #64748b;
  font-size: 13px;
}

.header-actions,
.node-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.header-actions {
  justify-content: flex-end;
  flex-wrap: wrap;
  max-width: 720px;
}

.editor-tabs {
  padding-top: 8px;
  padding-bottom: 12px;
}

.tab-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.editor-tab {
  width: 220px;
}

.collapse-tip {
  color: #2563eb;
  font-size: 13px;
}

.toolbar-grid {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 14px;
  border-top: 1px solid #edf2f7;
  padding-top: 10px;
}

.toolbar-block {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-right: 14px;
  border-right: 1px solid #e5e7eb;
}

.toolbar-block:last-child {
  border-right: 0;
}

.style-toolbar-grid {
  align-items: stretch;
}

.style-block {
  min-height: 34px;
}

.style-label {
  color: #475569;
  font-size: 13px;
  font-weight: 700;
  white-space: nowrap;
}

.filter-style-block {
  min-width: 210px;
}

.style-select {
  width: 150px;
}

.level-select {
  width: 120px;
}

.priority-tools {
  gap: 5px;
}

.priority-dot {
  width: 22px;
  height: 22px;
  line-height: 22px;
  color: #fff;
  border-radius: 50%;
  text-align: center;
  font-size: 11px;
  font-weight: 700;
}

.p0 { background: #ef4444; }
.p1 { background: #0ea5e9; }
.p2 { background: #22c55e; }
.p3 { background: #f97316; }

.tag-palette {
  flex-direction: column;
  align-items: flex-start;
  min-width: 520px;
}

.tag-tab-row,
.tag-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.tag-tab-row {
  border-bottom: 1px solid #e5e7eb;
  width: 100%;
}

.label-title {
  padding: 0 10px 8px;
  color: #64748b;
  font-size: 13px;
  cursor: pointer;
}

.label-title.active {
  color: #2563eb;
  border-bottom: 2px solid #2563eb;
}

.custom-tag-select {
  width: 230px;
}

.tag {
  display: inline-flex;
  align-items: center;
  height: 24px;
  padding: 0 9px;
  font-size: 13px;
  font-weight: 700;
}

.tag-blue { background: #bde7ff; }
.tag-green { background: #bdf7df; }
.tag-cyan { background: #9be8f0; }
.tag-purple { background: #a7a4ff; }
.tag-web { background: #ffb4b4; }
.tag-normal { background: #bdf7df; }
.tag-single { background: #ffd9b5; }

.canvas-shell {
  position: relative;
  padding: 16px;
  min-height: 760px;
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

.viewer-badge {
  position: absolute;
  left: 14px;
  top: 122px;
  padding: 8px 14px;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 5px;
  color: #334155;
  box-shadow: 0 2px 10px rgba(15, 23, 42, 0.06);
}

.map-tools {
  position: absolute;
  left: 14px;
  bottom: 34px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 7px;
  padding: 8px 6px;
  background: #ff7c7c;
  border-radius: 5px;
}

.map-tools :deep(.el-button) {
  margin-left: 0;
  color: #ef4444;
  font-size: 12px;
  font-weight: 700;
}

.zoom-value {
  width: 42px;
  text-align: center;
  color: #fff;
  font-size: 12px;
  font-weight: 700;
}

.zoom-line {
  width: 2px;
  height: 58px;
  margin: 0 auto;
  background: #fff;
  position: relative;
}

.zoom-line span {
  position: absolute;
  left: -4px;
  top: 25px;
  width: 10px;
  height: 10px;
  background: #fff;
  border-radius: 50%;
}

.mini-map {
  position: absolute;
  left: 62px;
  bottom: 52px;
  width: 118px;
  height: 88px;
  background: #ffffff;
  border: 1px solid #dbeafe;
  box-shadow: 0 3px 14px rgba(15, 23, 42, 0.12);
}

.mini-map-lines {
  width: 70px;
  height: 76px;
  margin: 6px auto;
  background: repeating-linear-gradient(to bottom, #93c5fd 0, #93c5fd 1px, transparent 1px, transparent 5px);
}

.mini-map-window {
  position: absolute;
  left: 42px;
  top: 30px;
  width: 38px;
  height: 22px;
  border: 2px solid #ef4444;
  transition: 0.18s ease;
}

.quick-node-menu {
  position: fixed;
  width: 300px;
  height: 340px;
  z-index: 3000;
  pointer-events: none;
}

.quick-ring {
  position: absolute;
  left: 66px;
  top: 30px;
  width: 168px;
  height: 168px;
  border: 30px solid rgba(71, 85, 105, 0.34);
  border-radius: 50%;
  box-shadow: 0 16px 36px rgba(15, 23, 42, 0.16);
  pointer-events: none;
}

.quick-button {
  position: absolute;
  width: 68px;
  height: 68px;
  margin-left: 0 !important;
  padding: 0 !important;
  border: 0;
  color: #111827;
  background: rgba(255, 255, 255, 0.98);
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.16);
  pointer-events: auto;
}

.quick-button:hover:not(.is-disabled) {
  color: #fff;
  background: #f05b67;
  transform: translateY(-2px);
  box-shadow: 0 16px 34px rgba(240, 91, 103, 0.28);
}

.quick-button.primary:hover {
  color: #fff;
  background: #f05b67;
  transform: none;
  box-shadow: 0 16px 36px rgba(240, 91, 103, 0.32);
}

.quick-button :deep(.el-button__content) {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  line-height: 1;
}

.quick-text {
  display: block;
  color: inherit;
  font-size: 17px;
  font-weight: 800;
}

.quick-button.primary {
  left: 114px;
  top: 80px;
  width: 72px;
  height: 72px;
  color: #fff;
  background: #f05b67;
  box-shadow: 0 16px 36px rgba(240, 91, 103, 0.32);
}

.quick-button:nth-child(3) { left: 218px; top: 82px; }
.quick-button:nth-child(4) { left: 190px; top: 164px; }
.quick-button:nth-child(5) { left: 42px; top: 164px; }
.quick-button:nth-child(6) { left: 14px; top: 82px; }
.quick-button:nth-child(7) { left: 116px; top: 0; }
.quick-button:nth-child(8) { left: 116px; top: 188px; }

.quick-extra-actions {
  position: absolute;
  left: 6px;
  top: 274px;
  display: flex;
  gap: 14px;
  pointer-events: auto;
}

.quick-extra-actions :deep(.el-button) {
  width: 86px;
  height: 42px;
  margin-left: 0;
  padding: 0 10px;
  color: #111827;
  background: rgba(255, 255, 255, 0.98);
  border: 0;
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.14);
}

.quick-extra-actions :deep(.el-button:hover:not(.is-disabled)) {
  color: #fff;
  background: #f05b67;
  transform: translateY(-1px);
  box-shadow: 0 16px 34px rgba(240, 91, 103, 0.24);
}

.quick-extra-actions :deep(.el-button > span) {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  font-weight: 700;
}

.floating-save {
  position: absolute;
  right: 22px;
  bottom: 22px;
  width: 92px;
}

.note-dialog-body,
.meta-dialog-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.note-node-title {
  color: #334155;
  font-size: 14px;
  font-weight: 700;
}

.note-preview,
.meta-preview,
.image-preview-box {
  padding: 10px 12px;
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: 8px;
}

.meta-preview a {
  color: #2563eb;
  font-weight: 700;
  word-break: break-all;
}

.meta-preview small {
  display: block;
  margin-top: 8px;
  color: #64748b;
}

.image-preview-title {
  color: #334155;
  font-weight: 700;
}

.image-preview-box img {
  display: block;
  max-width: 100%;
  max-height: 260px;
  margin-top: 8px;
  border-radius: 6px;
  object-fit: contain;
}

.note-preview-title {
  margin-bottom: 6px;
  color: #92400e;
  font-size: 13px;
  font-weight: 700;
}

.note-preview-content {
  white-space: pre-wrap;
  color: #475569;
  line-height: 1.6;
}

.search-result-list {
  max-height: 320px;
  overflow: auto;
  margin-top: 14px;
}

.search-result-item {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  margin-bottom: 8px;
  cursor: pointer;
}

.search-result-item:hover {
  color: #2563eb;
  border-color: #93c5fd;
  background: #eff6ff;
}

.search-result-item small {
  color: #94a3b8;
}

.shortcut-content {
  max-height: 430px;
  overflow: auto;
  padding: 6px 28px 10px 0;
}

.shortcut-section {
  padding: 8px 0 14px;
  border-bottom: 1px solid #ebeef5;
}

.shortcut-section h3 {
  margin: 0 0 10px;
  color: #1f2937;
  font-size: 18px;
  font-weight: 700;
}

.shortcut-row {
  display: grid;
  grid-template-columns: 250px 1fr;
  align-items: center;
  min-height: 33px;
  color: #475569;
}

.shortcut-keys {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 7px;
  padding-right: 16px;
}

.shortcut-keys kbd {
  min-width: 38px;
  height: 27px;
  padding: 0 9px;
  line-height: 25px;
  text-align: center;
  color: #6b7280;
  background: #fff;
  border: 1px solid #e7e27f;
  border-radius: 4px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.12);
  font-family: inherit;
  font-size: 13px;
  font-weight: 500;
}

.key-plus {
  color: #64748b;
  font-size: 13px;
}

.shortcut-label {
  color: #64748b;
  font-size: 15px;
}
</style>
