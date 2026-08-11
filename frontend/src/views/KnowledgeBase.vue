<template>
  <div class="knowledge-page">
    <div class="kb-layout">
      <!-- 左侧：知识库列表 -->
      <div class="kb-sidebar">
        <div class="kb-sidebar-header">
          <h1 class="page-title">知识库</h1>
          <el-button type="primary" size="small" @click="openCreateDialog">新建</el-button>
        </div>
        <div class="kb-list" v-loading="loading">
          <div
            v-for="kb in knowledgeBases"
            :key="kb.knowledge_base_id"
            class="kb-card"
            :class="{ active: selectedKnowledgeBase?.knowledge_base_id === kb.knowledge_base_id }"
            @click="handleSelectKnowledgeBase(kb)"
          >
            <div class="kb-card-head">
              <strong class="kb-name">{{ kb.name }}</strong>
              <el-tag :type="indexStatusTagType(kb.index_status)" size="small">
                {{ INDEX_STATUS_TEXT[kb.index_status] || kb.index_status }}
              </el-tag>
            </div>
            <div class="kb-desc" v-if="kb.description">{{ kb.description }}</div>
            <div class="kb-meta">
              <span>来源 {{ kb.source_count || 0 }}</span>
              <span>切片 {{ kb.chunk_count || 0 }}</span>
              <span v-if="kb.product_type">{{ kb.product_type }}</span>
            </div>
            <div class="kb-card-actions" @click.stop>
              <el-button size="small" text type="primary" @click="openEditDialog(kb)">编辑</el-button>
              <el-button size="small" text type="danger" @click="handleDeleteKnowledgeBase(kb)">删除</el-button>
            </div>
          </div>
          <el-empty v-if="!loading && !knowledgeBases.length" description="暂无知识库，点击「新建」创建" :image-size="60" />
        </div>
      </div>

      <!-- 右侧：详情 -->
      <div class="kb-detail" v-if="selectedKnowledgeBase">
        <div class="kb-detail-header">
          <div>
            <h2 class="detail-title">{{ selectedKnowledgeBase.name }}</h2>
            <p class="section-desc" v-if="selectedKnowledgeBase.description">{{ selectedKnowledgeBase.description }}</p>
          </div>
          <div class="detail-stats">
            <el-statistic title="知识来源" :value="selectedKnowledgeBase.source_count || 0" />
            <el-statistic title="切片数量" :value="selectedKnowledgeBase.chunk_count || 0" />
          </div>
        </div>

        <el-tabs v-model="activeTab" class="kb-tabs">
          <!-- Tab1 知识来源 -->
          <el-tab-pane label="知识来源" name="sources">
            <div class="source-section">
              <el-tabs v-model="sourceTab" class="source-add-tabs">
                <el-tab-pane label="手动粘贴" name="manual">
                  <el-form label-width="90px" class="source-form">
                    <el-form-item label="资料名称">
                      <el-input v-model="sourceForm.source_name" placeholder="例如：摄像头夜视测试规范" />
                    </el-form-item>
                    <el-form-item label="资料正文">
                      <el-input v-model="sourceForm.content_text" type="textarea" :rows="6" placeholder="粘贴硬件测试规范、历史测试文档或XMind用例文本" />
                    </el-form-item>
                    <el-button type="primary" :loading="addingSource" @click="handleAddSource">保存资料</el-button>
                  </el-form>
                </el-tab-pane>

                <el-tab-pane label="上传文件" name="upload">
                  <div class="source-form">
                    <el-upload
                      drag
                      :auto-upload="false"
                      :limit="1"
                      accept=".txt,.md,.xmind"
                      :on-change="handleFileChange"
                      :on-remove="handleFileRemove"
                      :file-list="uploadFileList"
                    >
                      <el-icon class="upload-icon"><UploadFilled /></el-icon>
                      <div class="el-upload__text">拖拽文件到此处，或 <em>点击选择</em></div>
                      <template #tip>
                        <div class="el-upload__tip">支持 .txt / .md 文本文件，以及新版 .xmind 用例文件，最大 20MB</div>
                      </template>
                    </el-upload>
                    <el-button class="upload-submit" type="primary" :loading="uploadingSource" :disabled="!selectedFile" @click="handleUploadSource">
                      上传并解析
                    </el-button>
                  </div>
                </el-tab-pane>

                <el-tab-pane label="从用例集导入" name="caseSet">
                  <el-form label-width="90px" class="source-form">
                    <el-form-item label="用例集">
                      <el-select v-model="importCaseSetId" filterable placeholder="请选择用例集" class="wide-select">
                        <el-option v-for="caseSet in caseSets" :key="caseSet.case_set_id" :label="`#${caseSet.case_set_id} ${caseSet.name}`" :value="caseSet.case_set_id" />
                      </el-select>
                    </el-form-item>
                    <p class="section-desc">把已有用例集的树形节点文本导入为知识来源，便于复用历史用例。</p>
                    <el-button type="primary" :loading="importingSource" :disabled="!importCaseSetId" @click="handleImportCaseSet">导入为知识来源</el-button>
                  </el-form>
                </el-tab-pane>
              </el-tabs>

              <div class="source-list">
                <div class="source-list-head">
                  <span class="source-list-title">知识来源列表</span>
                  <el-button size="small" :loading="sourcesLoading" @click="loadSources">刷新</el-button>
                </div>
                <el-table v-loading="sourcesLoading" :data="knowledgeSources" border>
                  <el-table-column prop="source_id" label="ID" width="70" />
                  <el-table-column prop="source_name" label="来源名称" min-width="180" show-overflow-tooltip />
                  <el-table-column label="类型" width="130">
                    <template #default="{ row }">
                      <el-tag size="small" :type="sourceTypeTagType(row.source_type)">{{ sourceTypeText(row.source_type) }}</el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column label="创建时间" width="170">
                    <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
                  </el-table-column>
                  <el-table-column label="操作" width="140" fixed="right">
                    <template #default="{ row }">
                      <el-button size="small" text type="primary" @click="openSourceDetail(row)">查看</el-button>
                      <el-button size="small" type="danger" text @click="handleDeleteSource(row)">删除</el-button>
                    </template>
                  </el-table-column>
                </el-table>
                <el-empty v-if="!sourcesLoading && !knowledgeSources.length" description="暂无知识来源" :image-size="60" />
              </div>
            </div>
          </el-tab-pane>

          <!-- Tab2 构建索引 -->
          <el-tab-pane label="构建索引" name="build">
            <div class="build-section">
              <el-alert
                v-if="building"
                :title="buildStageText"
                type="info"
                show-icon
                :closable="false"
              >
                <template #default>
                  <div class="stage-hint">{{ buildStageDetail }}</div>
                </template>
              </el-alert>
              <div v-if="building" class="build-progress-box">
                <el-progress
                  :percentage="buildProgress"
                  :stroke-width="14"
                  :color="buildProgressColor"
                  text-inside
                  :status="buildProgress === 100 ? 'success' : undefined"
                />
              </div>
              <el-button class="build-button" type="success" :loading="building" :disabled="building" @click="handleBuildIndex">
                {{ hasActiveIndex ? '重新构建索引' : '构建索引' }}
              </el-button>
              <el-descriptions v-if="buildResult" class="result-box" border :column="1">
                <el-descriptions-item label="FAISS索引ID">{{ buildResult.faiss_index_id }}</el-descriptions-item>
                <el-descriptions-item label="切片数量">{{ buildResult.chunk_count }}</el-descriptions-item>
                <el-descriptions-item label="向量数量">{{ buildResult.vector_count }}</el-descriptions-item>
                <el-descriptions-item label="向量维度">{{ buildResult.vector_dimension }}</el-descriptions-item>
                <el-descriptions-item label="索引文件">{{ buildResult.index_file_path }}</el-descriptions-item>
              </el-descriptions>
            </div>
          </el-tab-pane>

          <!-- Tab3 RAG检索 -->
          <el-tab-pane label="RAG检索" name="search">
            <div class="search-section">
              <el-form label-width="90px">
                <el-form-item label="检索问题">
                  <el-input v-model="searchForm.query_text" type="textarea" :rows="3" placeholder="例如：如何测试摄像头夜视红外灯是否正常开启？" />
                </el-form-item>
                <el-form-item label="返回数量">
                  <el-input-number v-model="searchForm.top_k" :min="1" :max="20" />
                </el-form-item>
              </el-form>
              <el-button type="primary" :loading="searching" @click="handleSearch">开始检索</el-button>

              <div v-if="searchResult.length" class="search-summary-grid">
                <div class="search-summary-card">
                  <span>命中片段</span>
                  <strong>{{ searchResult.length }}</strong>
                </div>
                <div class="search-summary-card">
                  <span>最高相似度</span>
                  <strong>{{ topSearchScore }}</strong>
                </div>
                <div class="search-summary-card">
                  <span>平均相似度</span>
                  <strong>{{ averageSearchScore }}</strong>
                </div>
              </div>

              <div v-if="searchResult.length" class="search-result-list result-box">
                <div v-for="(item, index) in searchResult" :key="item.chunk_id" class="search-result-card">
                  <div class="result-card-head">
                    <el-tag size="small" type="info">#{{ index + 1 }}</el-tag>
                    <span class="result-source">{{ item.source_name || `来源#${item.source_id}` }}</span>
                    <div class="result-score">
                      <span>相似度</span>
                      <el-progress
                        :percentage="scoreToPercent(item.score)"
                        :stroke-width="8"
                        :color="scoreColor(item.score)"
                        style="width: 120px"
                      />
                    </div>
                    <el-button size="small" text type="primary" @click="openChunkDetail(item)">详情</el-button>
                    <el-button size="small" text @click="copyChunkText(item)">复制</el-button>
                  </div>
                  <div class="result-text" :title="item.chunk_text">{{ item.chunk_text }}</div>
                </div>
              </div>
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>

      <!-- 未选中知识库 -->
      <div class="kb-detail kb-detail-empty" v-else>
        <el-empty description="从左侧选择一个知识库开始管理" :image-size="100" />
      </div>
    </div>

    <!-- 创建/编辑知识库对话框 -->
    <el-dialog v-model="createDialogVisible" :title="editingKnowledgeBase ? '编辑知识库' : '创建知识库'" width="560px">
      <el-form label-width="90px">
        <el-form-item label="名称">
          <el-input v-model="createForm.name" placeholder="例如：摄像头硬件测试知识库" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="createForm.description" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="产品类型">
          <el-input v-model="createForm.product_type" placeholder="例如：camera" />
        </el-form-item>
        <el-form-item label="硬件模块">
          <el-input v-model="createForm.hardware_module" placeholder="例如：night_vision" />
        </el-form-item>
        <el-form-item label="状态" v-if="editingKnowledgeBase">
          <el-radio-group v-model="createForm.status">
            <el-radio value="active">启用</el-radio>
            <el-radio value="disabled">停用</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="handleSaveKnowledgeBase">保存</el-button>
      </template>
    </el-dialog>

    <!-- 命中知识片段详情 -->
    <el-dialog v-model="chunkDialogVisible" title="命中知识片段详情" width="720px">
      <div v-if="activeChunk" class="chunk-detail-body">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="chunk_id">{{ activeChunk.chunk_id }}</el-descriptions-item>
          <el-descriptions-item label="source_id">{{ activeChunk.source_id }}</el-descriptions-item>
          <el-descriptions-item label="相似度">{{ Number(activeChunk.score).toFixed(6) }}</el-descriptions-item>
          <el-descriptions-item label="来源">{{ activeChunk.source_name || `来源#${activeChunk.source_id}` }}</el-descriptions-item>
        </el-descriptions>
        <div class="chunk-section">
          <div class="chunk-title">命中文本</div>
          <div class="chunk-text">{{ activeChunk.chunk_text }}</div>
        </div>
        <div class="chunk-section">
          <div class="chunk-title">元数据</div>
          <pre class="metadata-preview">{{ formatMetadata(activeChunk.metadata) }}</pre>
        </div>
      </div>
      <template #footer>
        <el-button @click="chunkDialogVisible = false">关闭</el-button>
        <el-button type="primary" @click="copyChunkText(activeChunk)">复制片段</el-button>
      </template>
    </el-dialog>

    <!-- 知识来源详情 -->
    <el-dialog v-model="sourceDetailVisible" title="知识来源内容" width="720px">
      <template v-if="activeSource">
        <el-descriptions :column="2" border class="chunk-detail-body">
          <el-descriptions-item label="来源名称">{{ activeSource.source_name }}</el-descriptions-item>
          <el-descriptions-item label="类型">{{ sourceTypeText(activeSource.source_type) }}</el-descriptions-item>
          <el-descriptions-item label="来源ID">{{ activeSource.source_id }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ formatDateTime(activeSource.created_at) }}</el-descriptions-item>
        </el-descriptions>
        <div class="chunk-section">
          <div class="chunk-title">资料正文</div>
          <div class="chunk-text source-text">{{ activeSource.content_text || '该来源暂无正文内容' }}</div>
        </div>
        <div class="chunk-section" v-if="activeSource.file_name">
          <div class="chunk-title">文件名</div>
          <div class="source-file-name">{{ activeSource.file_name }}</div>
        </div>
      </template>
      <template #footer>
        <el-button @click="sourceDetailVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { UploadFilled } from '@element-plus/icons-vue'
import {
  addManualSource,
  buildIndex,
  createKnowledgeBase,
  deleteKnowledgeBase,
  deleteKnowledgeSource,
  getBuildProgress,
  importCaseSetAsSource,
  listKnowledgeBases,
  listKnowledgeSources,
  searchKnowledgeBase,
  updateKnowledgeBase,
  uploadKnowledgeSourceFile
} from '../api/rag'
import { listCaseSets } from '../api/case'
import { INDEX_STATUS_TEXT, SOURCE_TYPE_TEXT } from '../utils/constants'
import { formatDateTime } from '../utils/format'
import { confirmAction, showSuccess, showWarning } from '../utils/message'
import { getCurrentUserId } from '../utils/storage'

const loading = ref(false)
const creating = ref(false)
const addingSource = ref(false)
const uploadingSource = ref(false)
const importingSource = ref(false)
const building = ref(false)
const searching = ref(false)
const createDialogVisible = ref(false)
const editingKnowledgeBase = ref(null)
const chunkDialogVisible = ref(false)
const sourceDetailVisible = ref(false)
const knowledgeBases = ref([])
const selectedKnowledgeBase = ref(null)
const activeChunk = ref(null)
const activeSource = ref(null)
const buildResult = ref(null)
const buildStageText = ref('准备构建索引...')
const buildStageDetail = ref('')
const buildProgress = ref(0)
const searchResult = ref([])
const knowledgeSources = ref([])
const sourcesLoading = ref(false)
const activeTab = ref('sources')
const sourceTab = ref('manual')
const uploadFileList = ref([])
const selectedFile = ref(null)
const importCaseSetId = ref(null)
const caseSets = ref([])
let buildPollTimer = null

const createForm = reactive({
  name: '',
  description: '',
  product_type: '',
  hardware_module: '',
  status: 'active'
})

const sourceForm = reactive({
  source_name: '',
  content_text: ''
})

const searchForm = reactive({
  query_text: '',
  top_k: 5
})

const hasActiveIndex = computed(() => selectedKnowledgeBase.value?.index_status === 'active')

const buildProgressColor = computed(() => {
  if (buildProgress.value >= 100) return '#16a34a'
  if (buildProgress.value >= 60) return '#f59e0b'
  return '#2563eb'
})

const topSearchScore = computed(() => formatScore(Math.max(...searchResult.value.map(item => Number(item.score || 0)))))
const averageSearchScore = computed(() => {
  if (!searchResult.value.length) {
    return '0.0000'
  }
  const total = searchResult.value.reduce((sum, item) => sum + Number(item.score || 0), 0)
  return formatScore(total / searchResult.value.length)
})

async function loadKnowledgeBases() {
  loading.value = true
  try {
    knowledgeBases.value = await listKnowledgeBases()
    if (!selectedKnowledgeBase.value && knowledgeBases.value.length) {
      selectedKnowledgeBase.value = knowledgeBases.value[0]
      await loadSources()
    } else if (selectedKnowledgeBase.value) {
      const updated = knowledgeBases.value.find(item => item.knowledge_base_id === selectedKnowledgeBase.value.knowledge_base_id)
      if (updated) {
        selectedKnowledgeBase.value = updated
      }
    }
  } finally {
    loading.value = false
  }
}

function openCreateDialog() {
  editingKnowledgeBase.value = null
  Object.assign(createForm, {
    name: '',
    description: '',
    product_type: '',
    hardware_module: '',
    status: 'active'
  })
  createDialogVisible.value = true
}

function openEditDialog(kb) {
  editingKnowledgeBase.value = kb
  Object.assign(createForm, {
    name: kb.name,
    description: kb.description || '',
    product_type: kb.product_type || '',
    hardware_module: kb.hardware_module || '',
    status: kb.status || 'active'
  })
  createDialogVisible.value = true
}

async function handleSaveKnowledgeBase() {
  if (!createForm.name.trim()) {
    showWarning('请填写知识库名称')
    return
  }
  creating.value = true
  try {
    const payload = {
      name: createForm.name.trim(),
      description: createForm.description.trim(),
      product_type: createForm.product_type.trim(),
      hardware_module: createForm.hardware_module.trim()
    }
    if (editingKnowledgeBase.value) {
      payload.status = createForm.status
      await updateKnowledgeBase(editingKnowledgeBase.value.knowledge_base_id, payload)
      showSuccess('知识库已更新')
    } else {
      const result = await createKnowledgeBase({
        ...payload,
        created_by: getCurrentUserId()
      })
      showSuccess('知识库创建成功')
      selectedKnowledgeBase.value = result
    }
    createDialogVisible.value = false
    await loadKnowledgeBases()
    await loadSources()
  } finally {
    creating.value = false
  }
}

async function handleDeleteKnowledgeBase(kb) {
  await confirmAction(`确认删除知识库「${kb.name}」吗？其下的知识来源、切片和FAISS索引将一并清除，不可恢复。`, '删除知识库')
  await deleteKnowledgeBase(kb.knowledge_base_id)
  showSuccess('知识库已删除')
  if (selectedKnowledgeBase.value?.knowledge_base_id === kb.knowledge_base_id) {
    selectedKnowledgeBase.value = null
    searchResult.value = []
    buildResult.value = null
    knowledgeSources.value = []
  }
  await loadKnowledgeBases()
}

function handleSelectKnowledgeBase(kb) {
  selectedKnowledgeBase.value = kb
  buildResult.value = null
  searchResult.value = []
  activeTab.value = 'sources'
  loadSources()
}

async function loadSources() {
  if (!selectedKnowledgeBase.value) {
    return
  }
  sourcesLoading.value = true
  try {
    knowledgeSources.value = await listKnowledgeSources(selectedKnowledgeBase.value.knowledge_base_id)
  } catch {
    knowledgeSources.value = []
  } finally {
    sourcesLoading.value = false
  }
}

async function handleDeleteSource(row) {
  await confirmAction(`确认删除知识来源「${row.source_name}」吗？删除后需要重新构建索引。`, '删除知识来源')
  await deleteKnowledgeSource(row.source_id)
  showSuccess('知识来源已删除')
  await loadSources()
  await loadKnowledgeBases()
}

async function handleAddSource() {
  if (!selectedKnowledgeBase.value) {
    return
  }
  if (!sourceForm.source_name.trim() || !sourceForm.content_text.trim()) {
    showWarning('请填写资料名称和资料正文')
    return
  }
  addingSource.value = true
  try {
    await addManualSource(selectedKnowledgeBase.value.knowledge_base_id, {
      source_name: sourceForm.source_name,
      source_type: 'manual_text',
      content_text: sourceForm.content_text,
      created_by: getCurrentUserId()
    })
    showSuccess('知识资料保存成功，请继续构建索引')
    await loadSources()
    await loadKnowledgeBases()
    sourceForm.source_name = ''
    sourceForm.content_text = ''
  } finally {
    addingSource.value = false
  }
}

function handleFileChange(file) {
  selectedFile.value = file?.raw || null
}

function handleFileRemove() {
  selectedFile.value = null
  uploadFileList.value = []
}

async function handleUploadSource() {
  if (!selectedKnowledgeBase.value || !selectedFile.value) {
    return
  }
  uploadingSource.value = true
  try {
    const result = await uploadKnowledgeSourceFile(selectedKnowledgeBase.value.knowledge_base_id, selectedFile.value)
    showSuccess(`文件解析成功：${result.source_name}，请继续构建索引`)
    await loadSources()
    await loadKnowledgeBases()
    selectedFile.value = null
    uploadFileList.value = []
  } finally {
    uploadingSource.value = false
  }
}

async function loadCaseSets() {
  try {
    const result = await listCaseSets({ page: 1, page_size: 100, status: 'active' })
    caseSets.value = result.items || []
  } catch {
    caseSets.value = []
  }
}

async function handleImportCaseSet() {
  if (!selectedKnowledgeBase.value || !importCaseSetId.value) {
    return
  }
  importingSource.value = true
  try {
    const result = await importCaseSetAsSource(selectedKnowledgeBase.value.knowledge_base_id, importCaseSetId.value)
    showSuccess(`用例集已导入为知识来源：${result.source_name}，请继续构建索引`)
    await loadSources()
    await loadKnowledgeBases()
    importCaseSetId.value = null
  } finally {
    importingSource.value = false
  }
}

async function handleBuildIndex() {
  if (!selectedKnowledgeBase.value) {
    return
  }
  building.value = true
  buildResult.value = null
  buildProgress.value = 0
  buildStageText.value = '任务已启动'
  buildStageDetail.value = ''
  try {
    const task = await buildIndex(selectedKnowledgeBase.value.knowledge_base_id)
    await pollBuildProgress(task.task_id)
  } finally {
    stopBuildPolling()
    building.value = false
  }
}

async function pollBuildProgress(taskId) {
  if (!selectedKnowledgeBase.value) {
    return
  }
  try {
    const state = await getBuildProgress(selectedKnowledgeBase.value.knowledge_base_id, taskId)
    buildProgress.value = state.progress || 0
    buildStageText.value = state.stage || ''
    buildStageDetail.value = state.detail || ''
    if (state.status === 'success') {
      buildResult.value = state.result
      showSuccess('FAISS索引构建成功')
      await loadKnowledgeBases()
      return
    }
    if (state.status === 'error') {
      showWarning(state.detail || '构建失败')
      return
    }
    buildPollTimer = window.setTimeout(() => pollBuildProgress(taskId), 600)
  } catch {
    buildPollTimer = window.setTimeout(() => pollBuildProgress(taskId), 600)
  }
}

function stopBuildPolling() {
  if (buildPollTimer) {
    window.clearTimeout(buildPollTimer)
    buildPollTimer = null
  }
}

async function handleSearch() {
  if (!selectedKnowledgeBase.value) {
    return
  }
  if (!searchForm.query_text.trim()) {
    showWarning('请输入检索问题')
    return
  }
  searching.value = true
  try {
    const result = await searchKnowledgeBase(selectedKnowledgeBase.value.knowledge_base_id, {
      query_text: searchForm.query_text,
      top_k: searchForm.top_k
    })
    searchResult.value = result.items || []
    showSuccess(`检索完成，命中 ${searchResult.value.length} 条知识片段`)
  } finally {
    searching.value = false
  }
}

function openChunkDetail(row) {
  activeChunk.value = row
  chunkDialogVisible.value = true
}

function openSourceDetail(row) {
  activeSource.value = row
  sourceDetailVisible.value = true
}

async function copyChunkText(row) {
  if (!row?.chunk_text) {
    showWarning('暂无可复制的片段内容')
    return
  }
  await navigator.clipboard.writeText(row.chunk_text)
  showSuccess('命中知识片段已复制')
}

function formatMetadata(metadata) {
  return metadata ? JSON.stringify(metadata, null, 2) : '无元数据'
}

function formatScore(value) {
  return Number(value || 0).toFixed(4)
}

function scoreToPercent(score) {
  return Math.max(0, Math.min(100, Math.round(Number(score || 0) * 100)))
}

function scoreColor(score) {
  const value = Number(score || 0)
  if (value >= 0.7) return '#f05b67'
  if (value >= 0.5) return '#f59e0b'
  return '#94a3b8'
}

function indexStatusTagType(status) {
  const map = { none: 'info', rebuilding: 'warning', active: 'success', deleted: 'danger' }
  return map[status] || 'info'
}

function sourceTypeTagType(sourceType) {
  const map = { manual_text: 'info', history_doc: 'warning', xmind_case: 'success' }
  return map[sourceType] || 'info'
}

function sourceTypeText(sourceType) {
  return SOURCE_TYPE_TEXT[sourceType] || sourceType
}

onMounted(() => {
  loadKnowledgeBases()
  loadCaseSets()
})
onBeforeUnmount(stopBuildPolling)
</script>

<style scoped>
.knowledge-page {
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.kb-layout {
  display: flex;
  gap: 18px;
  align-items: flex-start;
}

/* 左侧列表 */
.kb-sidebar {
  width: 340px;
  flex-shrink: 0;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  background: #fff;
  padding: 14px;
}

.kb-sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.kb-sidebar-header .page-title {
  margin: 0;
  font-size: 18px;
}

.kb-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: calc(100vh - 200px);
  overflow: auto;
}

.kb-card {
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 12px;
  cursor: pointer;
  transition: 0.18s ease;
}

.kb-card:hover {
  border-color: #2563eb;
  box-shadow: 0 6px 16px rgba(37, 99, 235, 0.1);
}

.kb-card.active {
  border-color: #2563eb;
  background: #eff6ff;
}

.kb-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.kb-name {
  color: #111827;
  font-size: 14px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.kb-desc {
  margin-top: 6px;
  color: #6b7280;
  font-size: 12px;
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.kb-meta {
  margin-top: 8px;
  display: flex;
  gap: 10px;
  color: #64748b;
  font-size: 12px;
}

.kb-card-actions {
  margin-top: 8px;
  display: flex;
  justify-content: flex-end;
  gap: 4px;
  border-top: 1px solid #f1f5f9;
  padding-top: 6px;
}

/* 右侧详情 */
.kb-detail {
  flex: 1;
  min-width: 0;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  background: #fff;
  padding: 18px;
}

.kb-detail-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 400px;
}

.kb-detail-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 6px;
}

.detail-title {
  margin: 0 0 6px;
  font-size: 20px;
}

.detail-stats {
  display: flex;
  gap: 28px;
}

.section-desc {
  color: #64748b;
  line-height: 1.7;
}

.kb-tabs {
  margin-top: 10px;
}

.source-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.source-add-tabs {
  border: 1px solid #f1f5f9;
  border-radius: 10px;
  padding: 10px 14px;
}

.source-form {
  max-width: 560px;
}

.upload-submit {
  margin-top: 14px;
}

.upload-icon {
  font-size: 40px;
  color: #94a3b8;
}

.source-list-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.source-list-title {
  font-weight: 700;
  color: #334155;
}

.build-button {
  margin-top: 14px;
}

.build-progress-box {
  margin-top: 16px;
  max-width: 560px;
}

.stage-hint {
  margin-top: 6px;
  color: #94a3b8;
  font-size: 12px;
}

.result-box {
  margin-top: 16px;
}

.search-summary-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-top: 16px;
}

.search-summary-card {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 14px;
  border: 1px solid #dbeafe;
  border-radius: 10px;
  background: #f8fafc;
}

.search-summary-card span {
  color: #64748b;
  font-size: 13px;
}

.search-summary-card strong {
  color: #2563eb;
  font-size: 24px;
}

.search-result-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.search-result-card {
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 12px 14px;
  transition: 0.18s ease;
}

.search-result-card:hover {
  border-color: #2563eb;
  box-shadow: 0 8px 20px rgba(37, 99, 235, 0.1);
}

.result-card-head {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.result-source {
  flex: 1;
  min-width: 0;
  color: #334155;
  font-weight: 700;
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.result-score {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #64748b;
  font-size: 12px;
}

.result-text {
  color: #475569;
  font-size: 13px;
  line-height: 1.7;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
  white-space: pre-wrap;
}

.chunk-detail-body {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.chunk-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.chunk-title {
  color: #334155;
  font-weight: 700;
}

.chunk-text {
  max-height: 220px;
  overflow: auto;
  padding: 12px;
  border-radius: 8px;
  background: #f8fafc;
  color: #475569;
  line-height: 1.8;
  white-space: pre-wrap;
}

.source-text {
  min-height: 120px;
}

.source-file-name {
  padding: 10px 12px;
  border-radius: 8px;
  background: #f8fafc;
  color: #475569;
  font-family: Consolas, 'Courier New', monospace;
}

.metadata-preview {
  max-height: 180px;
  overflow: auto;
  margin: 0;
  padding: 12px;
  border-radius: 8px;
  background: #0f172a;
  color: #e2e8f0;
  font-size: 12px;
}

@media (max-width: 1100px) {
  .kb-layout {
    flex-direction: column;
  }
  .kb-sidebar {
    width: 100%;
  }
}
</style>
