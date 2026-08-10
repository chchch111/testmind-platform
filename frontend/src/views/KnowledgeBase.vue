<template>
  <div class="knowledge-page">
    <div class="page-card">
      <div class="page-header-row">
        <div>
          <h1 class="page-title">知识库管理</h1>
          <p class="page-desc">管理RAG知识库，支持录入硬件测试规范、构建FAISS索引、执行相似知识检索。</p>
        </div>
        <el-button type="primary" @click="openCreateDialog">创建知识库</el-button>
      </div>

      <el-table v-loading="loading" :data="knowledgeBases" border highlight-current-row @current-change="handleSelectKnowledgeBase">
        <el-table-column prop="knowledge_base_id" label="ID" width="80" />
        <el-table-column prop="name" label="知识库名称" min-width="200" />
        <el-table-column prop="product_type" label="产品类型" width="130" />
        <el-table-column prop="hardware_module" label="硬件模块" width="140" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">{{ STATUS_TEXT[row.status] || row.status }}</template>
        </el-table-column>
        <el-table-column label="创建时间" width="190">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" @click="selectAndScroll(row)">管理</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-row :gutter="18" v-if="selectedKnowledgeBase">
      <el-col :span="12">
        <div class="page-card">
          <h2>添加知识资料</h2>
          <p class="section-desc">当前知识库：{{ selectedKnowledgeBase.name }}</p>
          <el-tabs v-model="sourceTab">
            <el-tab-pane label="手动粘贴" name="manual">
              <el-form label-width="90px">
                <el-form-item label="资料名称">
                  <el-input v-model="sourceForm.source_name" placeholder="例如：摄像头夜视测试规范" />
                </el-form-item>
                <el-form-item label="资料正文">
                  <el-input v-model="sourceForm.content_text" type="textarea" :rows="6" placeholder="粘贴硬件测试规范、历史测试文档或XMind用例文本" />
                </el-form-item>
              </el-form>
              <el-button type="primary" :loading="addingSource" @click="handleAddSource">保存资料</el-button>
            </el-tab-pane>

            <el-tab-pane label="上传文件" name="upload">
              <el-form label-width="90px">
                <el-form-item label="文件">
                  <input ref="fileInputRef" type="file" accept=".txt,.md,.xmind" @change="handleFileChange" />
                </el-form-item>
              </el-form>
              <p class="section-desc">支持 .txt / .md 文本文件，以及新版 .xmind 用例文件。系统会抽取纯文本作为知识来源，之后需点击“构建索引”。</p>
              <el-button type="primary" :loading="uploadingSource" :disabled="!selectedFile" @click="handleUploadSource">上传并解析</el-button>
            </el-tab-pane>

            <el-tab-pane label="从用例集导入" name="caseSet">
              <el-form label-width="90px">
                <el-form-item label="用例集">
                  <el-select v-model="importCaseSetId" filterable placeholder="请选择用例集" class="wide-select">
                    <el-option v-for="caseSet in caseSets" :key="caseSet.case_set_id" :label="`#${caseSet.case_set_id} ${caseSet.name}`" :value="caseSet.case_set_id" />
                  </el-select>
                </el-form-item>
              </el-form>
              <p class="section-desc">把已有用例集的树形节点文本导入为知识来源，便于复用历史用例。</p>
              <el-button type="primary" :loading="importingSource" :disabled="!importCaseSetId" @click="handleImportCaseSet">导入为知识来源</el-button>
            </el-tab-pane>
          </el-tabs>
        </div>
      </el-col>

      <el-col :span="12">
        <div class="page-card">
          <h2>构建FAISS索引</h2>
          <p class="section-desc">系统将使用 LangChain 切片、bge-small-zh 向量化，并把 FAISS 文件保存到服务端磁盘。</p>
          <el-alert v-if="building" :title="buildStageText" type="info" show-icon :closable="false">
            <template #default>
              <div class="stage-hint">阶段文案为流程示意，实际构建以服务端返回为准，知识库较大时耗时较长。</div>
            </template>
          </el-alert>
          <el-button class="build-button" type="success" :loading="building" @click="handleBuildIndex">构建索引</el-button>
          <el-descriptions v-if="buildResult" class="result-box" border :column="1">
            <el-descriptions-item label="FAISS索引ID">{{ buildResult.faiss_index_id }}</el-descriptions-item>
            <el-descriptions-item label="切片数量">{{ buildResult.chunk_count }}</el-descriptions-item>
            <el-descriptions-item label="向量数量">{{ buildResult.vector_count }}</el-descriptions-item>
            <el-descriptions-item label="向量维度">{{ buildResult.vector_dimension }}</el-descriptions-item>
            <el-descriptions-item label="索引文件">{{ buildResult.index_file_path }}</el-descriptions-item>
          </el-descriptions>
        </div>
      </el-col>
    </el-row>

    <div class="page-card" v-if="selectedKnowledgeBase">
      <h2>RAG检索测试</h2>
      <p class="section-desc">输入新的测试需求，系统会从FAISS索引中检索相似历史知识片段。</p>
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

      <el-table v-if="searchResult.length" class="result-box" :data="searchResult" border>
        <el-table-column prop="chunk_id" label="chunk_id" width="100" />
        <el-table-column prop="source_id" label="source_id" width="100" />
        <el-table-column label="score" width="120">
          <template #default="{ row }">{{ Number(row.score).toFixed(4) }}</template>
        </el-table-column>
        <el-table-column prop="chunk_text" label="命中文本" min-width="360" show-overflow-tooltip />
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="openChunkDetail(row)">详情</el-button>
            <el-button size="small" type="primary" @click="copyChunkText(row)">复制</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <div class="page-card" v-if="selectedKnowledgeBase">
      <div class="source-header">
        <div>
          <h2>知识来源列表</h2>
          <p class="section-desc">当前知识库的全部知识来源，删除后需重新构建索引才会生效。</p>
        </div>
        <el-button :loading="sourcesLoading" @click="loadSources">刷新</el-button>
      </div>
      <el-table v-loading="sourcesLoading" :data="knowledgeSources" border>
        <el-table-column prop="source_id" label="ID" width="80" />
        <el-table-column prop="source_name" label="来源名称" min-width="220" show-overflow-tooltip />
        <el-table-column label="类型" width="150">
          <template #default="{ row }">{{ SOURCE_TYPE_TEXT[row.source_type] || row.source_type }}</template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">{{ STATUS_TEXT[row.status] || row.status }}</template>
        </el-table-column>
        <el-table-column label="创建时间" width="190">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="danger" @click="handleDeleteSource(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="chunkDialogVisible" title="命中知识片段详情" width="720px">
      <div v-if="activeChunk" class="chunk-detail-body">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="chunk_id">{{ activeChunk.chunk_id }}</el-descriptions-item>
          <el-descriptions-item label="source_id">{{ activeChunk.source_id }}</el-descriptions-item>
          <el-descriptions-item label="相似度">{{ Number(activeChunk.score).toFixed(6) }}</el-descriptions-item>
          <el-descriptions-item label="知识库">{{ selectedKnowledgeBase?.name }}</el-descriptions-item>
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

    <el-dialog v-model="createDialogVisible" title="创建知识库" width="560px">
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
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="handleCreateKnowledgeBase">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { addManualSource, buildIndex, createKnowledgeBase, deleteKnowledgeSource, importCaseSetAsSource, listKnowledgeBases, listKnowledgeSources, searchKnowledgeBase, uploadKnowledgeSourceFile } from '../api/rag'
import { listCaseSets } from '../api/case'
import { SOURCE_TYPE_TEXT, STATUS_TEXT } from '../utils/constants'
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
const chunkDialogVisible = ref(false)
const knowledgeBases = ref([])
const selectedKnowledgeBase = ref(null)
const activeChunk = ref(null)
const buildResult = ref(null)
const buildStageText = ref('准备构建索引...')
const searchResult = ref([])
const knowledgeSources = ref([])
const sourcesLoading = ref(false)
const sourceTab = ref('manual')
const fileInputRef = ref(null)
const selectedFile = ref(null)
const importCaseSetId = ref(null)
const caseSets = ref([])
let buildStageTimer = null

const buildStages = [
  '正在读取知识来源...',
  '正在切片文档...',
  '正在使用 bge-small-zh 生成向量...',
  '正在写入 FAISS 索引文件...',
  '正在保存 MySQL 元数据...'
]

const createForm = reactive({
  name: '',
  description: '',
  product_type: '',
  hardware_module: ''
})

const sourceForm = reactive({
  source_name: '',
  content_text: ''
})

const searchForm = reactive({
  query_text: '',
  top_k: 5
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
    }
  } finally {
    loading.value = false
  }
}

function openCreateDialog() {
  Object.assign(createForm, {
    name: '',
    description: '',
    product_type: '',
    hardware_module: ''
  })
  createDialogVisible.value = true
}

async function handleCreateKnowledgeBase() {
  if (!createForm.name.trim()) {
    showWarning('请填写知识库名称')
    return
  }
  creating.value = true
  try {
    const result = await createKnowledgeBase({
      ...createForm,
      created_by: getCurrentUserId()
    })
    showSuccess('知识库创建成功')
    createDialogVisible.value = false
    await loadKnowledgeBases()
    selectedKnowledgeBase.value = result
  } finally {
    creating.value = false
  }
}

function handleSelectKnowledgeBase(row) {
  if (row) {
    selectedKnowledgeBase.value = row
    buildResult.value = null
    searchResult.value = []
    loadSources()
  }
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
}

async function selectAndScroll(row) {
  handleSelectKnowledgeBase(row)
  await nextTick()
  window.scrollTo({ top: 360, behavior: 'smooth' })
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
    sourceForm.source_name = ''
    sourceForm.content_text = ''
  } finally {
    addingSource.value = false
  }
}

function handleFileChange(event) {
  const file = event.target.files?.[0]
  selectedFile.value = file || null
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
    selectedFile.value = null
    if (fileInputRef.value) {
      fileInputRef.value.value = ''
    }
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
  startBuildStageText()
  try {
    buildResult.value = await buildIndex(selectedKnowledgeBase.value.knowledge_base_id)
    showSuccess('FAISS索引构建成功')
  } finally {
    stopBuildStageText()
    building.value = false
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

function startBuildStageText() {
  stopBuildStageText()
  let index = 0
  buildStageText.value = buildStages[index]
  buildStageTimer = window.setInterval(() => {
    index = (index + 1) % buildStages.length
    buildStageText.value = buildStages[index]
  }, 1800)
}

function stopBuildStageText() {
  if (buildStageTimer) {
    window.clearInterval(buildStageTimer)
    buildStageTimer = null
  }
}

onMounted(() => {
  loadKnowledgeBases()
  loadCaseSets()
})
onBeforeUnmount(stopBuildStageText)
</script>

<style scoped>
.knowledge-page {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.page-header-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.section-desc {
  color: #64748b;
  line-height: 1.7;
}

.build-button {
  margin-top: 14px;
}

.source-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 12px;
}

.source-header h2 {
  margin: 0 0 6px;
}

.wide-select {
  width: 100%;
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
</style>
