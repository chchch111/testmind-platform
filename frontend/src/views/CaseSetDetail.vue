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
        <el-button type="primary" @click="openCaseReviewDialog">发起用例评审</el-button>
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
          <el-tab-pane label="工具栏" name="tools" />
        </el-tabs>
        <div class="collapse-tip">收起</div>
      </div>

      <div class="toolbar-grid">
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
        ref="mindMapCanvasRef"
        :tree-data="filteredTreeData"
        :selected-node-id="selectedNode?.node_id"
        :selected-node-ids="selectedNodeIds"
        :editing-node-id="editingNodeId"
        :node-tags-map="nodeTagsMap"
        :node-notes-map="nodeNotesMap"
        :node-links-map="nodeLinksMap"
        :node-images-map="nodeImagesMap"
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
        @toggle-collapse="toggleNodeCollapse"
        @box-select="handleBoxSelect"
        @box-select-preview="handleBoxSelectPreview"
        @zoom-in="zoomIn"
        @zoom-out="zoomOut"
        @reset-view="resetZoom"
        @viewport-active-change="isMindmapViewportActive = $event"
        @viewport-change="handleViewportChange"
        @node-drag-start="handleNodeDragStart"
        @node-drop="handleNodeDrop"
        @node-drag-end="draggingNode = null"
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
      <div v-if="contextMenuVisible" class="quick-node-menu" :style="contextMenuStyle" @click.stop>
        <svg class="quick-ring-track" viewBox="0 0 300 400" aria-hidden="true">
          <circle
            cx="150" cy="195" r="105"
            fill="none"
            stroke="rgba(71, 85, 105, 0.22)"
            stroke-width="20"
          />
        </svg>
        <!-- 环心：主操作「编辑」（红色，保留在圆环中央） -->
        <el-button class="quick-button primary" circle @click="runContextAction(openEditNode)">
          <span class="quick-text">编辑</span>
        </el-button>
        <!-- 环上 60° 等角均匀分布的次要操作 -->
        <el-button class="quick-button" circle :disabled="!canMoveSelectedNode('up')" @click="runContextAction(() => moveSelectedNode('up'))">
          <span class="quick-text">前移</span>
        </el-button>
        <el-button class="quick-button" circle @click="runContextAction(openCreateChild)">
          <span class="quick-text">下级</span>
        </el-button>
        <el-button class="quick-button" circle @click="runContextAction(handleDeleteNode)">
          <span class="quick-text">删除</span>
        </el-button>
        <el-button class="quick-button" circle @click="runContextAction(openSiblingNode)">
          <span class="quick-text">同级</span>
        </el-button>
        <el-button class="quick-button" circle :disabled="!canMoveSelectedNode('down')" @click="runContextAction(() => moveSelectedNode('down'))">
          <span class="quick-text">后移</span>
        </el-button>
        <el-button class="quick-button" circle :disabled="!selectedNodeParent" @click="runContextAction(() => selectRelativeNode('parent'))">
          <span class="quick-text">上级</span>
        </el-button>
        <div class="quick-extra-actions">
          <el-button round @click="runContextAction(() => openNoteDialog(selectedNode))">备注</el-button>
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

    <el-dialog v-model="caseReviewDialogVisible" title="发起用例集评审" width="720px">
      <div class="case-review-body">
        <el-form label-width="100px">
          <el-form-item label="评审人ID">
            <el-select
              v-model="caseReviewForm.reviewerIds"
              multiple
              filterable
              allow-create
              default-first-option
              placeholder="输入评审人ID后回车，例如 1、2、3"
              class="wide-select"
            />
          </el-form-item>
          <el-form-item label="截止时间">
            <el-date-picker v-model="caseReviewForm.dueAt" type="datetime" value-format="YYYY-MM-DD HH:mm:ss" placeholder="选择评审截止时间" />
          </el-form-item>
          <el-form-item label="评审说明">
            <el-input v-model="caseReviewForm.note" type="textarea" :rows="4" placeholder="例如：请重点检查前置条件、异常分支和预期结果是否完整。" />
          </el-form-item>
        </el-form>
        <div class="review-history" v-if="caseReviewRecords.length">
          <div class="review-history-title">最近评审记录</div>
          <div v-for="record in caseReviewRecords" :key="record.review_id" class="review-history-item">
            <div class="review-history-head">
              <el-tag :type="reviewStatusTagType(record.status)" size="small">{{ reviewStatusText(record.status) }}</el-tag>
              <div v-if="record.status !== 'completed'" class="review-actions">
                <el-button v-if="record.status === 'submitted'" size="small" type="primary" @click="startReview(record)">开始评审</el-button>
                <el-button size="small" type="success" @click="completeReview(record)">完成评审</el-button>
              </div>
            </div>
            <span>评审人：{{ (record.reviewer_ids || []).join('、') }}</span>
            <span>截止：{{ record.due_at || '未设置' }}</span>
            <small>{{ record.note || '无说明' }}</small>
            <small v-if="record.conclusion" class="review-conclusion">结论：{{ record.conclusion }}</small>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button @click="caseReviewDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitCaseReview">提交评审</el-button>
      </template>
    </el-dialog>

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
        <el-table-column label="创建时间" width="190">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="内容" min-width="220">
          <template #default="{ row }">
            标签 {{ Object.keys(row.data_json?.nodeTagsMap || {}).length }} 个节点，备注 {{ Object.keys(row.data_json?.nodeNotesMap || {}).length }} 个节点
          </template>
        </el-table-column>
        <el-table-column label="操作" width="190">
          <template #default="{ row }">
            <el-button size="small" type="primary" @click="restoreCanvasSnapshot(row)">恢复</el-button>
            <el-button size="small" type="danger" @click="deleteCanvasSnapshot(row.snapshot_id)">删除</el-button>
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
import { createReview, createSnapshot, deleteSnapshot, getCaseSetMetas, listReviews, listSnapshots, saveCaseSetMetas, updateReview } from '../api/canvas'
import CaseNodeForm from '../components/CaseNodeForm.vue'
import MindMapCanvas from '../components/MindMapCanvas.vue'
import VersionDrawer from '../components/VersionDrawer.vue'
import { NODE_TYPE_TEXT } from '../utils/constants'
import { formatDateTime } from '../utils/format'
import { confirmAction, showSuccess, showWarning } from '../utils/message'
import { getCurrentUserId } from '../utils/storage'

const route = useRoute()
const caseSetId = Number(route.params.id)
const customTagStorageKey = `rag_mindmap_custom_tags_${caseSetId}`
const collapsedNodeStorageKey = `rag_mindmap_collapsed_nodes_${caseSetId}`
const appearanceStorageKey = `rag_mindmap_appearance_${caseSetId}`
let remoteSaveTimer = null
const activeTab = ref('tools')
const labelTab = ref('system')
const customTagValue = ref('')
const customToolbarTags = ref([])
const metaLoaded = ref(false)
const treeData = ref([])
const selectedNode = ref(null)
const selectedNodeIds = ref([])
const editingNodeId = ref(null)
const nodeTagsMap = reactive({})
const nodeNotesMap = reactive({})
const nodeLinksMap = reactive({})
const nodeImagesMap = reactive({})
const collapsedNodeIds = ref([])
const canvasSnapshots = ref([])
const zoom = ref(1)
const isMindmapViewportActive = ref(false)
const mindMapCanvasRef = ref(null)
const contextMenuVisible = ref(false)
const contextMenuPosition = reactive({ x: 0, y: 0 })
const viewportState = reactive({
  scrollLeft: 0,
  scrollTop: 0,
  clientWidth: 1,
  clientHeight: 1,
  scrollWidth: 1,
  scrollHeight: 1,
  nodes: []
})
const detailDrawerVisible = ref(false)
const nodeDialogVisible = ref(false)
const caseReviewDialogVisible = ref(false)
const versionDrawerVisible = ref(false)
const shortcutDialogVisible = ref(false)
const snapshotDialogVisible = ref(false)
const searchDialogVisible = ref(false)
const noteDialogVisible = ref(false)
const linkDialogVisible = ref(false)
const imageDialogVisible = ref(false)
const noteEditingNode = ref(null)
const linkEditingNode = ref(null)
const imageEditingNode = ref(null)
const noteDraft = ref('')
const linkForm = reactive({ title: '', url: '' })
const imageForm = reactive({ title: '', url: '' })
const caseReviewForm = reactive({ reviewerIds: [], dueAt: '', note: '' })
const caseReviewRecords = ref([])
const searchKeyword = ref('')
const clipboardNode = ref(null)
const draggingNode = ref(null)
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

const visibleToolbarTags = computed(() => (labelTab.value === 'system' ? systemToolbarTags : businessToolbarTags.slice(0, 3)))
const allToolbarTags = computed(() => [...systemToolbarTags, ...businessToolbarTags, ...customToolbarTags.value])
const currentNodeNote = computed(() => String(nodeNotesMap[noteEditingNode.value?.node_id] || '').trim())
const currentNodeLink = computed(() => nodeLinksMap[linkEditingNode.value?.node_id] || null)
const currentNodeImage = computed(() => nodeImagesMap[imageEditingNode.value?.node_id] || null)
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
        selected: node.id === selectedNode.value?.node_id || selectedNodeIds.value.includes(node.id)
      }
    })
  }
}

function getMiniMapBounds() {
  const nodeMetaMap = new Map()
  collectMiniMapNodeMeta(filteredTreeData.value, nodeMetaMap)
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
    parent_id: snapshot.parent_id,
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
  if (action.type === 'title' || action.type === 'update') {
    await updateNodeBySnapshot(direction === 'undo' ? action.before : action.after, direction === 'undo' ? '撤销节点编辑' : '重做节点编辑')
    await loadTree()
    selectNodeOnly(findNodeById(treeData.value, action.nodeId))
    return
  }
  if (action.type === 'create') {
    if (direction === 'undo') {
      const node = findNodeById(treeData.value, action.nodeId)
      if (node) {
        await deleteCaseNode(action.nodeId)
        await loadTree()
      }
      selectedNode.value = null
      selectedNodeIds.value = []
      editingNodeId.value = null
      return
    }
    const oldNodeId = action.nodeId
    const createdNode = await createNodeFromHistoryPayload(action.payload || {
      title: action.title,
      node_type: action.nodeType,
      priority: 'P1'
    }, action.parentId)
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
  contextMenuPosition.x = Math.max(16, Math.min(window.innerWidth - 330, payload.x - 165))
  contextMenuPosition.y = Math.max(16, Math.min(window.innerHeight - 410, payload.y - 205))
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

function scheduleRemoteSave() {
  if (!metaLoaded.value) {
    return
  }
  if (remoteSaveTimer) {
    return
  }
  remoteSaveTimer = window.setTimeout(async () => {
    remoteSaveTimer = null
    await flushRemoteSave()
  }, 600)
}

async function flushRemoteSave() {
  const items = []
  Object.entries(nodeTagsMap).forEach(([nodeId, tags]) => {
    ;(tags || []).forEach(tag => {
      if (tag?.text) {
        items.push({ node_id: Number(nodeId), meta_type: 'tag', meta_key: String(tag.text), meta_value: { text: tag.text, color: tag.color || '' } })
      }
    })
  })
  Object.entries(nodeNotesMap).forEach(([nodeId, text]) => {
    if (String(text || '').trim()) {
      items.push({ node_id: Number(nodeId), meta_type: 'note', meta_value: { text } })
    }
  })
  Object.entries(nodeLinksMap).forEach(([nodeId, link]) => {
    if (link?.url) {
      items.push({ node_id: Number(nodeId), meta_type: 'link', meta_value: link })
    }
  })
  Object.entries(nodeImagesMap).forEach(([nodeId, image]) => {
    if (image?.url) {
      items.push({ node_id: Number(nodeId), meta_type: 'image', meta_value: image })
    }
  })
  try {
    await saveCaseSetMetas(caseSetId, items)
  } catch {
    // 全局拦截器已提示错误，这里静默避免重复弹窗。
  }
}

async function loadNodeMetasFromServer() {
  try {
    const result = await getCaseSetMetas(caseSetId)
    const items = result.items || []
    Object.keys(nodeTagsMap).forEach(nodeId => delete nodeTagsMap[nodeId])
    Object.keys(nodeNotesMap).forEach(nodeId => delete nodeNotesMap[nodeId])
    Object.keys(nodeLinksMap).forEach(nodeId => delete nodeLinksMap[nodeId])
    Object.keys(nodeImagesMap).forEach(nodeId => delete nodeImagesMap[nodeId])
    for (const item of items) {
      const nodeId = Number(item.node_id)
      const value = item.meta_value || {}
      if (item.meta_type === 'tag' && item.meta_key) {
        nodeTagsMap[nodeId] = [...(nodeTagsMap[nodeId] || []), { text: item.meta_key, color: value.color || '#dbeafe' }]
      } else if (item.meta_type === 'note') {
        if (value.text) {
          nodeNotesMap[nodeId] = value.text
        }
      } else if (item.meta_type === 'link') {
        nodeLinksMap[nodeId] = value
      } else if (item.meta_type === 'image') {
        nodeImagesMap[nodeId] = value
      }
    }
    metaLoaded.value = true
  } catch {
    // 全局拦截器已提示错误。
  }
}

function saveNodeTags() {
  scheduleRemoteSave()
}

function saveNodeNotes() {
  scheduleRemoteSave()
}

function saveNodeLinks() {
  scheduleRemoteSave()
}

function saveNodeImages() {
  scheduleRemoteSave()
}

function loadNodeTags() {
  // 节点元数据从服务端加载，见 loadNodeMetasFromServer。
}

function loadNodeNotes() {
  // 节点元数据从服务端加载，见 loadNodeMetasFromServer。
}

function loadNodeLinks() {
  // 节点元数据从服务端加载，见 loadNodeMetasFromServer。
}

function loadNodeImages() {
  // 节点元数据从服务端加载，见 loadNodeMetasFromServer。
}

function clonePlainObject(value) {
  return JSON.parse(JSON.stringify(value || {}))
}

async function loadCanvasSnapshots() {
  try {
    canvasSnapshots.value = await listSnapshots(caseSetId)
  } catch {
    canvasSnapshots.value = []
  }
}

function saveCanvasSnapshots() {
  // 快照已由后端持久化，见 createCanvasSnapshot / deleteCanvasSnapshot。
}

async function loadCaseReviewRecords() {
  try {
    caseReviewRecords.value = await listReviews(caseSetId)
  } catch {
    caseReviewRecords.value = []
  }
}

function saveCaseReviewRecords() {
  // 评审记录已由后端持久化，见 submitCaseReview。
}

function openCaseReviewDialog() {
  Object.assign(caseReviewForm, {
    reviewerIds: [String(getCurrentUserId())],
    dueAt: '',
    note: '请重点检查用例前置条件、执行步骤、预期结果和异常分支是否完整。'
  })
  caseReviewDialogVisible.value = true
}

async function submitCaseReview() {
  const reviewerIds = Array.from(new Set(caseReviewForm.reviewerIds.map(value => Number(String(value).trim())).filter(Number.isInteger).filter(value => value > 0)))
  if (!reviewerIds.length) {
    showWarning('请至少填写一个评审人ID')
    return
  }
  await createReview(caseSetId, {
    reviewer_ids: reviewerIds,
    due_at: caseReviewForm.dueAt || null,
    note: caseReviewForm.note.trim() || null
  })
  caseReviewRecords.value = await listReviews(caseSetId)
  caseReviewDialogVisible.value = false
  showSuccess(`已发起用例集评审，评审人 ${reviewerIds.join('、')}`)
}

async function startReview(record) {
  await updateReview(caseSetId, record.review_id, { status: 'reviewing' })
  showSuccess('已开始评审')
  caseReviewRecords.value = await listReviews(caseSetId)
}

async function completeReview(record) {
  const result = await ElMessageBox.prompt('请输入评审结论', '完成评审', {
    confirmButtonText: '确认完成',
    cancelButtonText: '取消',
    inputPlaceholder: '例如：用例覆盖完整，建议补充异常分支'
  }).catch(() => null)
  if (!result) {
    return
  }
  await updateReview(caseSetId, record.review_id, { status: 'completed', conclusion: String(result.value || '').trim() || null })
  showSuccess('评审已完成')
  caseReviewRecords.value = await listReviews(caseSetId)
}

function reviewStatusText(status) {
  const map = { submitted: '待评审', reviewing: '评审中', completed: '已完成' }
  return map[status] || status
}

function reviewStatusTagType(status) {
  if (status === 'completed') return 'success'
  if (status === 'reviewing') return 'warning'
  return 'info'
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
  const name = String(result.value || defaultName).trim() || defaultName
  const created = await createSnapshot(caseSetId, {
    name,
    data: {
      nodeTagsMap: clonePlainObject(nodeTagsMap),
      nodeNotesMap: clonePlainObject(nodeNotesMap),
      nodeLinksMap: clonePlainObject(nodeLinksMap),
      nodeImagesMap: clonePlainObject(nodeImagesMap),
      collapsedNodeIds: [...collapsedNodeIds.value],
      appearance: clonePlainObject(appearanceForm)
    }
  })
  canvasSnapshots.value = [created, ...canvasSnapshots.value].slice(0, 50)
  snapshotDialogVisible.value = true
  showSuccess('脑图版本快照已创建')
}

async function restoreCanvasSnapshot(snapshot) {
  await confirmAction(`确认恢复快照「${snapshot.name}」吗？当前页面标签、备注、链接、图片和外观会被覆盖。`, '恢复脑图快照')
  const data = snapshot.data_json || snapshot.data || {}
  restoreTagsMap(data.nodeTagsMap || {})
  restorePersistedMap(nodeNotesMap, data.nodeNotesMap || {})
  restorePersistedMap(nodeLinksMap, data.nodeLinksMap || {})
  restorePersistedMap(nodeImagesMap, data.nodeImagesMap || {})
  collapsedNodeIds.value = Array.isArray(data.collapsedNodeIds) ? data.collapsedNodeIds : []
  Object.assign(appearanceForm, data.appearance || {})
  handleSaveCanvas()
  showSuccess('脑图版本快照已恢复')
}

async function deleteCanvasSnapshot(snapshotId) {
  await confirmAction('确认删除这个脑图版本快照吗？')
  await deleteSnapshot(caseSetId, snapshotId)
  canvasSnapshots.value = canvasSnapshots.value.filter(snapshot => snapshot.snapshot_id !== snapshotId)
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

function loadAppearanceSettings() {
  try {
    const savedSettings = JSON.parse(window.localStorage.getItem(appearanceStorageKey) || '{}')
    Object.assign(appearanceForm, {
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

function handleNodeDragStart(node) {
  draggingNode.value = node
  selectNodeOnly(node)
}

async function handleNodeDrop(targetNode) {
  const sourceNode = draggingNode.value
  draggingNode.value = null
  if (!sourceNode || !targetNode) {
    return
  }
  if (sourceNode.node_id === targetNode.node_id) {
    showWarning('不能把节点拖到自身下面')
    return
  }
  if (isDescendantNode(sourceNode.node_id, targetNode.node_id)) {
    showWarning('不能把节点拖到自己的子节点下面')
    return
  }
  const currentParent = findParentNode(treeData.value, sourceNode.node_id)
  if ((currentParent?.node_id ?? null) === targetNode.node_id) {
    showWarning('目标节点已经是当前父节点')
    return
  }
  const freshSourceNode = findNodeById(treeData.value, sourceNode.node_id) || sourceNode
  const before = getNodeSnapshot(freshSourceNode)
  const after = {
    ...before,
    parent_id: targetNode.node_id,
    sort_order: targetNode.children?.length || 0
  }
  await updateNodeBySnapshot(after, `拖拽移动到「${targetNode.title}」下面`)
  pushHistory({
    type: 'update',
    nodeId: sourceNode.node_id,
    before,
    after
  })
  collapsedNodeIds.value = collapsedNodeIds.value.filter(nodeId => nodeId !== targetNode.node_id)
  saveCollapsedNodes()
  await loadTree()
  selectNodeOnly(findNodeById(treeData.value, sourceNode.node_id))
  showSuccess(`已移动到「${targetNode.title}」下面`)
}

function isDescendantNode(parentNodeId, possibleChildNodeId) {
  const parentNode = findNodeById(treeData.value, parentNodeId)
  if (!parentNode) {
    return false
  }
  return Boolean(findNodeById(parentNode.children || [], possibleChildNodeId))
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
  const parentId = selectedNode.value.node_id
  const payload = cloneNodePayload(clipboardNode.value)
  const created = await createNodeFromClipboard(payload, parentId)
  pushHistory({
    type: 'create',
    nodeId: created.node_id,
    parentId,
    payload
  })
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
    payload: {
      title: '新建节点',
      node_type: nodeType,
      precondition: null,
      test_steps: null,
      expected_result: null,
      priority: 'P1',
      children: []
    }
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
  saveCollapsedNodes()
  saveAppearanceSettings()
  flushRemoteSave()
  showSuccess('当前脑图标签、备注、链接、图片、折叠状态和外观已保存')
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
  const key = event.key.toLowerCase()
  const isCtrl = event.ctrlKey || event.metaKey
  if (isEditingTarget(event.target)) {
    const isInlineNodeEditor = Boolean(event.target?.closest?.('.mind-node'))
    if (isInlineNodeEditor && isCtrl && key === 'z') {
      event.preventDefault()
      undoLastAction()
      return
    }
    if (isInlineNodeEditor && isCtrl && key === 'y') {
      event.preventDefault()
      redoLastAction()
      return
    }
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
    editingNodeId.value = null
    return
  }
  if (shortcutDialogVisible.value || snapshotDialogVisible.value || nodeDialogVisible.value || noteDialogVisible.value || linkDialogVisible.value || imageDialogVisible.value || versionDrawerVisible.value || searchDialogVisible.value) {
    return
  }

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
  return createNodeFromHistoryPayload(node, parentId)
}

async function createNodeFromHistoryPayload(node, parentId) {
  const created = await createCaseNode({
    case_set_id: caseSetId,
    parent_id: parentId,
    node_type: node.node_type || 'case',
    title: `${node.title || '复制节点'}`,
    precondition: node.precondition || null,
    test_steps: node.test_steps || null,
    expected_result: node.expected_result || null,
    priority: node.priority || 'P1',
    sort_order: node.sort_order ?? 0,
    created_by: getCurrentUserId()
  })
  for (const child of node.children || []) {
    await createNodeFromHistoryPayload(child, created.node_id)
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
      const payload = {
        title: nodeForm.title,
        node_type: nodeForm.node_type,
        precondition: nodeForm.precondition || null,
        test_steps: nodeForm.test_steps || null,
        expected_result: nodeForm.expected_result || null,
        priority: nodeForm.priority,
        children: []
      }
      const createdNode = await createNodeFromHistoryPayload(payload, parentIdForCreate.value)
      pushHistory({
        type: 'create',
        nodeId: createdNode.node_id,
        parentId: parentIdForCreate.value,
        payload
      })
      showSuccess('节点创建成功')
    } else {
      const before = getNodeSnapshot(selectedNode.value)
      const after = {
        ...before,
        title: nodeForm.title,
        node_type: nodeForm.node_type,
        precondition: nodeForm.precondition || null,
        test_steps: nodeForm.test_steps || null,
        expected_result: nodeForm.expected_result || null,
        priority: nodeForm.priority
      }
      await updateNodeBySnapshot(after, nodeForm.change_note || '前端编辑节点')
      pushHistory({
        type: 'update',
        nodeId: selectedNode.value.node_id,
        before,
        after
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
  await deleteCaseNode(selectedNode.value.node_id)
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
  loadCollapsedNodes()
  loadAppearanceSettings()
  loadNodeMetasFromServer()
  loadCanvasSnapshots()
  loadCaseReviewRecords()
  loadTree()
  window.addEventListener('keydown', handleKeydown)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleKeydown)
  stopMiniMapPan()
  if (remoteSaveTimer) {
    window.clearTimeout(remoteSaveTimer)
    flushRemoteSave()
  }
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
  overflow: hidden;
  background: #ffffff;
  border: 1px solid #dbeafe;
  border-radius: 7px;
  box-shadow: 0 3px 14px rgba(15, 23, 42, 0.12);
}

.mini-map-svg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}

.mini-map-node-dot {
  fill: #60a5fa;
  stroke: #ffffff;
  stroke-width: 0.8;
}

.mini-map-node-dot.case {
  fill: #22c55e;
}

.mini-map-node-dot.selected {
  fill: #ef4444;
  stroke: #991b1b;
  stroke-width: 1;
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

.quick-node-menu {
  position: fixed;
  width: 300px;
  height: 400px;
  z-index: 3000;
  pointer-events: none;
}

.quick-ring-track {
  position: absolute;
  left: 0;
  top: 0;
  width: 300px;
  height: 400px;
  pointer-events: none;
  filter: drop-shadow(0 8px 20px rgba(15, 23, 42, 0.08));
}

.quick-button {
  position: absolute;
  width: 58px;
  height: 58px;
  margin-left: 0 !important;
  padding: 0 !important;
  border: 0;
  color: #111827;
  background: rgba(255, 255, 255, 0.98);
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.16);
  pointer-events: auto;
}

.quick-button:hover:not(.is-disabled) {
  color: #fff;
  background: #f05b67;
  transform: translateY(-2px);
  box-shadow: 0 14px 30px rgba(240, 91, 103, 0.28);
}

.quick-button.primary:hover {
  color: #fff;
  /* 保留原有编辑按钮悬停逻辑（与改前一致）：背景切为主色纯色、不抬起、阴影加深 */
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
  font-size: 15px;
  font-weight: 800;
}

/* 环心：主操作「编辑」（红色，保留在圆环中央） */
.quick-button.primary {
  left: 117px;
  top: 162px;
  width: 66px;
  height: 66px;
  color: #fff;
  background: radial-gradient(circle at 35% 30%, #f87171, #f05b67);
  box-shadow: 0 14px 32px rgba(240, 91, 103, 0.45), 0 4px 12px rgba(15, 23, 42, 0.2);
}

/* 环上 60° 等角均匀分布：环心 (150,195) 半径 105，从正上顺时针 */
.quick-button:nth-child(8) { left: 121px; top: 61px; }   /* 上级 0° */
.quick-button:nth-child(3) { left: 212px; top: 114px; }  /* 前移 60° */
.quick-button:nth-child(4) { left: 212px; top: 219px; }  /* 下级 120° */
.quick-button:nth-child(5) { left: 121px; top: 271px; }  /* 删除 180° */
.quick-button:nth-child(6) { left: 30px; top: 219px; }   /* 同级 240° */
.quick-button:nth-child(7) { left: 30px; top: 114px; }   /* 后移 300° */

.quick-extra-actions {
  position: absolute;
  left: 4px;
  top: 356px;
  display: flex;
  gap: 10px;
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
.meta-dialog-body,
.case-review-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.wide-select {
  width: 100%;
}

.review-history {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding-top: 12px;
  border-top: 1px solid #e5e7eb;
}

.review-history-title {
  color: #334155;
  font-weight: 700;
}

.review-history-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 10px;
  border: 1px solid #dbeafe;
  border-radius: 8px;
  background: #f8fafc;
}

.review-history-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.review-actions {
  display: flex;
  gap: 8px;
}

.review-history-item small {
  color: #64748b;
}

.review-conclusion {
  font-weight: 700;
  color: #166534 !important;
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
