<template>
  <div class="ai-generate-page">
    <div class="page-card hero-card">
      <div>
        <div class="breadcrumb">AI用例生成 / RAG检索 / 自动入库</div>
        <h1 class="page-title">AI生成测试用例</h1>
        <p class="page-desc">选择知识库并输入硬件测试需求，系统会先检索FAISS知识片段，再调用DeepSeek生成树形思维导图用例。</p>
      </div>
      <div class="hero-actions">
        <el-button @click="loadInitialData">刷新数据</el-button>
        <el-button type="primary" :disabled="!lastCaseSetId" @click="openGeneratedCaseSet">查看生成的脑图</el-button>
      </div>
    </div>

    <el-row :gutter="18">
      <el-col :span="8">
        <div class="page-card form-card">
          <h2>生成参数</h2>
          <p class="section-desc">选择知识库并描述测试需求，系统先检索知识片段，再调用 DeepSeek 生成用例。</p>

          <el-form label-position="top">
            <el-form-item label="知识库">
              <el-select v-model="form.knowledge_base_id" class="full-width" placeholder="请选择知识库" filterable>
                <el-option
                  v-for="item in knowledgeBases"
                  :key="item.knowledge_base_id"
                  :label="`${item.name}（${item.hardware_module || '通用模块'}）`"
                  :value="item.knowledge_base_id"
                />
              </el-select>
            </el-form-item>

            <div v-if="selectedKnowledgeBase" class="kb-summary">
              <div class="kb-title">当前知识库</div>
              <div class="kb-name-line">{{ selectedKnowledgeBase.name }}</div>
              <div class="kb-meta">产品：{{ selectedKnowledgeBase.product_type || '未填写' }} / 模块：{{ selectedKnowledgeBase.hardware_module || '未填写' }}</div>
              <div class="kb-stats">
                <span class="kb-stat-item">来源 {{ selectedKnowledgeBase.source_count || 0 }}</span>
                <span class="kb-stat-item">切片 {{ selectedKnowledgeBase.chunk_count || 0 }}</span>
                <el-tag size="small" :type="indexStatusTagType(selectedKnowledgeBase.index_status)">
                  {{ INDEX_STATUS_TEXT[selectedKnowledgeBase.index_status] || selectedKnowledgeBase.index_status }}
                </el-tag>
              </div>
              <div v-if="selectedKnowledgeBase.index_status !== 'active'" class="kb-warn">
                {{ indexStatusHint(selectedKnowledgeBase.index_status) }}
              </div>
            </div>

            <el-form-item label="测试需求">
              <el-input
                v-model="form.requirement_text"
                type="textarea"
                :rows="8"
                maxlength="1200"
                show-word-limit
                placeholder="例如：基于摄像头WEB管理后台，生成4K/1080P视频参数、存储空间、系统信息相关的功能测试用例。"
              />
            </el-form-item>

            <el-row :gutter="12">
              <el-col :span="12">
                <el-form-item label="检索片段数 top_k">
                  <el-input-number v-model="form.top_k" class="full-width" :min="1" :max="10" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="保存方式">
                  <el-switch v-model="form.save_to_case_set" active-text="自动入库" inactive-text="仅预览" />
                </el-form-item>
              </el-col>
            </el-row>
          </el-form>

          <el-button class="generate-button" type="primary" size="large" :loading="generating" @click="handleGenerate">
            {{ generating ? '正在生成...' : '开始AI生成' }}
          </el-button>
          <el-button class="presearch-button" size="large" :loading="preSearching" @click="handlePreSearch">
            预检索知识片段
          </el-button>
        </div>
      </el-col>

      <el-col :span="16">
        <div class="page-card preview-card">
          <div class="section-header">
            <div>
              <h2>生成结果</h2>
              <p class="section-desc">生成的 JSON 会按目录/用例树展示，自动入库后可跳转到思维导图编辑器。</p>
            </div>
            <div class="preview-actions">
              <el-button :disabled="!result" @click="copyGeneratedText">复制原始JSON</el-button>
              <el-button type="primary" :disabled="!lastCaseSetId" @click="openGeneratedCaseSet">打开脑图</el-button>
            </div>
          </div>

          <div class="status-bar" :class="`status-${stageStatusType}`">
            <span class="status-dot" />
            <span class="status-text">{{ statusBarText }}</span>
            <span v-if="generating" class="status-detail">{{ currentStageText }}</span>
          </div>
          <el-progress
            v-if="generating"
            class="generate-progress"
            :percentage="generateProgress"
            :stroke-width="12"
            :color="generateProgressColor"
            text-inside
          />
          <div v-if="generating && generateStageDetail" class="generate-stage-detail">
            {{ generateStageDetail }}
          </div>

          <div v-if="preSearchResult.length" class="retrieval-panel">
            <div class="retrieval-head">
              <div>
                <h3>预检索知识片段</h3>
                <p class="section-desc">已命中 {{ preSearchResult.length }} 条，勾选后生成会只使用这些片段。</p>
              </div>
              <div class="retrieval-actions">
                <el-button size="small" @click="selectAllChunks">全选</el-button>
                <el-button size="small" @click="selectedChunkIds = []">清空</el-button>
              </div>
            </div>
            <el-checkbox-group v-model="selectedChunkIds" class="chunk-check-list">
              <div v-for="(item, index) in preSearchResult" :key="item.chunk_id" class="chunk-check-card">
                <el-checkbox :label="item.chunk_id">
                  <span class="chunk-check-title">#{{ index + 1 }} {{ item.source_name || `来源#${item.source_id}` }}</span>
                  <span class="chunk-score">相似度 {{ formatScore(item.score) }}</span>
                </el-checkbox>
                <div class="chunk-preview-text">{{ item.chunk_text }}</div>
              </div>
            </el-checkbox-group>
          </div>

          <AiResultPreview :result="result" />
        </div>
      </el-col>
    </el-row>

    <div class="page-card record-card">
      <div class="section-header">
        <div>
          <h2>最近生成记录</h2>
          <p class="section-desc">展示最近50条AI生成记录，便于回看需求、模型、生成状态和入库用例集。</p>
        </div>
        <el-button @click="loadRecords">刷新记录</el-button>
      </div>

      <el-table v-loading="recordLoading" :data="records" border>
        <el-table-column prop="generation_id" label="ID" width="80" />
        <el-table-column prop="requirement_text" label="需求摘要" min-width="300" show-overflow-tooltip />
        <el-table-column label="模型" width="170">
          <template #default="{ row }">{{ row.model_provider }} / {{ row.model_name }}</template>
        </el-table-column>
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="row.generation_status === 'success' ? 'success' : 'danger'">{{ row.generation_status === 'success' ? '成功' : '失败' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="用例集" width="140">
          <template #default="{ row }">
            <el-button v-if="row.case_set_id" link type="primary" @click="$router.push(`/case-sets/${row.case_set_id}`)">#{{ row.case_set_id }}</el-button>
            <span v-else>未入库</span>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="190">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="170" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="previewRecord(row)">预览</el-button>
            <el-button size="small" type="primary" @click="openRecordDetail(row)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="recordDetailVisible" title="AI生成记录详情" width="820px">
      <div v-if="activeRecord" class="record-detail-body">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="生成ID">{{ activeRecord.generation_id }}</el-descriptions-item>
          <el-descriptions-item label="检索ID">{{ activeRecord.retrieval_id || '-' }}</el-descriptions-item>
          <el-descriptions-item label="用户ID">{{ activeRecord.user_id }}</el-descriptions-item>
          <el-descriptions-item label="生成状态">
            <el-tag :type="activeRecord.generation_status === 'success' ? 'success' : 'danger'">{{ activeRecord.generation_status }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="模型">{{ activeRecord.model_provider }} / {{ activeRecord.model_name }}</el-descriptions-item>
          <el-descriptions-item label="用例集">{{ activeRecord.case_set_id ? `#${activeRecord.case_set_id}` : '未入库' }}</el-descriptions-item>
          <el-descriptions-item label="创建时间" :span="2">{{ formatDateTime(activeRecord.created_at) }}</el-descriptions-item>
        </el-descriptions>
        <div class="detail-section">
          <div class="detail-title">原始需求</div>
          <div class="detail-text">{{ activeRecord.requirement_text }}</div>
        </div>
        <div class="detail-section">
          <div class="detail-title">使用知识片段ID</div>
          <el-tag v-for="chunkId in activeRecord.used_chunk_ids || []" :key="chunkId" type="info">{{ chunkId }}</el-tag>
          <span v-if="!activeRecord.used_chunk_ids?.length" class="empty-text">无</span>
        </div>
        <div v-if="activeRecord.error_message" class="detail-section">
          <div class="detail-title danger-text">错误信息</div>
          <div class="detail-text danger-text">{{ activeRecord.error_message }}</div>
        </div>
        <div class="detail-section">
          <div class="detail-title">生成JSON</div>
          <pre class="json-preview">{{ formatRecordJson(activeRecord.generated_json) }}</pre>
        </div>
      </div>
      <template #footer>
        <el-button @click="recordDetailVisible = false">关闭</el-button>
        <el-button :disabled="!activeRecord?.case_set_id" type="primary" @click="router.push(`/case-sets/${activeRecord.case_set_id}`)">打开脑图</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import AiResultPreview from '../components/AiResultPreview.vue'
import { getGenerateProgress, listGenerationRecords, startGenerateCaseSet } from '../api/ai'
import { listKnowledgeBases, searchKnowledgeBase } from '../api/rag'
import { INDEX_STATUS_TEXT } from '../utils/constants'
import { formatDateTime } from '../utils/format'
import { showSuccess, showWarning } from '../utils/message'
import { getCurrentUserId } from '../utils/storage'

const router = useRouter()
const knowledgeBases = ref([])
const records = ref([])
const result = ref(null)
const generating = ref(false)
const preSearching = ref(false)
const recordLoading = ref(false)
const recordDetailVisible = ref(false)
const activeRecord = ref(null)
const currentStageText = ref('等待输入需求并开始生成')
const generateStageDetail = ref('')
const generateProgress = ref(0)
const preSearchResult = ref([])
const selectedChunkIds = ref([])
let generatePollTimer = null
let generatePollCancelled = false

const form = reactive({
  knowledge_base_id: null,
  requirement_text: '基于摄像头WEB管理后台，生成视频编码参数、4K/1080P清晰度、存储空间、系统信息相关的功能测试用例。',
  top_k: 5,
  save_to_case_set: true
})

const selectedKnowledgeBase = computed(() => knowledgeBases.value.find(item => item.knowledge_base_id === form.knowledge_base_id) || null)
const lastCaseSetId = computed(() => result.value?.case_set_id || null)
const stageStatusType = computed(() => {
  if (generating.value) return 'running'
  return result.value ? 'success' : 'idle'
})
const statusBarText = computed(() => {
  if (generating.value) return '正在生成测试用例'
  if (result.value) {
    return result.value.case_set_id ? '生成完成，已保存为草稿用例集，可跳转脑图查看' : '生成完成，结果已在下方展示'
  }
  return '等待开始生成'
})
const generateProgressColor = computed(() => {
  if (generateProgress.value >= 90) return '#16a34a'
  if (generateProgress.value >= 58) return '#f59e0b'
  return '#2563eb'
})

function indexStatusTagType(status) {
  const map = { none: 'info', rebuilding: 'warning', stale: 'warning', active: 'success', deleted: 'danger' }
  return map[status] || 'info'
}

function indexStatusHint(status) {
  if (status === 'stale') {
    return '该知识库的知识来源已变更，当前索引已过期，请先到知识库管理页重新构建索引。'
  }
  if (status === 'rebuilding') {
    return '该知识库正在构建索引，请等待构建完成后再生成。'
  }
  return '该知识库尚未构建可用索引，请先到知识库管理页构建。'
}

async function loadInitialData() {
  await Promise.all([loadKnowledgeBases(), loadRecords()])
}

async function loadKnowledgeBases() {
  knowledgeBases.value = await listKnowledgeBases()
  if (!form.knowledge_base_id && knowledgeBases.value.length) {
    form.knowledge_base_id = knowledgeBases.value[0].knowledge_base_id
  }
}

async function loadRecords() {
  recordLoading.value = true
  try {
    records.value = await listGenerationRecords()
  } finally {
    recordLoading.value = false
  }
}

async function handleGenerate() {
  if (!form.knowledge_base_id) {
    showWarning('请先选择知识库')
    return
  }
  if (!form.requirement_text.trim()) {
    showWarning('请输入测试需求')
    return
  }
  if (preSearchResult.value.length && !selectedChunkIds.value.length) {
    showWarning('请至少选择一个预检索知识片段，或刷新页面后直接生成')
    return
  }

  generating.value = true
  result.value = null
  generateProgress.value = 0
  currentStageText.value = '任务启动中...'
  generateStageDetail.value = ''
  generatePollCancelled = false
  try {
    const task = await startGenerateCaseSet({
      knowledge_base_id: form.knowledge_base_id,
      requirement_text: form.requirement_text,
      top_k: form.top_k,
      selected_chunk_ids: selectedChunkIds.value.length ? selectedChunkIds.value : null,
      created_by: getCurrentUserId(),
      save_to_case_set: form.save_to_case_set
    })
    await pollGenerateProgress(task.task_id)
  } finally {
    stopGeneratePolling()
    generating.value = false
  }
}

async function pollGenerateProgress(taskId) {
  while (!generatePollCancelled) {
    try {
      const state = await getGenerateProgress(taskId)
      generateProgress.value = state.progress || 0
      currentStageText.value = state.stage || ''
      generateStageDetail.value = state.detail || ''
      if (state.status === 'success') {
        result.value = state.result
        currentStageText.value = '生成完成，结果已返回前端'
        showSuccess(state.result?.case_set_id ? `AI生成成功，已保存为草稿用例集 #${state.result.case_set_id}，可在用例集管理中审阅并发布` : 'AI生成成功，结果已返回预览')
        await loadRecords()
        return
      }
      if (state.status === 'error') {
        showWarning(state.detail || 'AI生成失败')
        return
      }
      await waitForNextGeneratePoll(800)
    } catch {
      await waitForNextGeneratePoll(1200)
    }
  }
}

function waitForNextGeneratePoll(ms) {
  return new Promise(resolve => {
    generatePollTimer = window.setTimeout(() => {
      generatePollTimer = null
      resolve()
    }, ms)
  })
}

async function handlePreSearch() {
  if (!form.knowledge_base_id) {
    showWarning('请先选择知识库')
    return
  }
  if (!form.requirement_text.trim()) {
    showWarning('请输入测试需求')
    return
  }
  preSearching.value = true
  try {
    const data = await searchKnowledgeBase(form.knowledge_base_id, {
      query_text: form.requirement_text,
      top_k: form.top_k
    })
    preSearchResult.value = data.items || []
    selectedChunkIds.value = preSearchResult.value.map(item => item.chunk_id)
    showSuccess(`预检索完成，命中 ${preSearchResult.value.length} 条知识片段`)
  } finally {
    preSearching.value = false
  }
}

function selectAllChunks() {
  selectedChunkIds.value = preSearchResult.value.map(item => item.chunk_id)
}

function clearPreSearch() {
  preSearchResult.value = []
  selectedChunkIds.value = []
}

function stopGeneratePolling() {
  generatePollCancelled = true
  if (generatePollTimer) {
    window.clearTimeout(generatePollTimer)
    generatePollTimer = null
  }
}

function openGeneratedCaseSet() {
  if (lastCaseSetId.value) {
    router.push(`/case-sets/${lastCaseSetId.value}`)
  }
}

async function copyGeneratedText() {
  if (!result.value) {
    return
  }
  const text = result.value.generated_text || JSON.stringify(result.value.generated_json, null, 2)
  await navigator.clipboard.writeText(text)
  showSuccess('已复制AI生成JSON')
}

function openRecordDetail(row) {
  activeRecord.value = row
  recordDetailVisible.value = true
}

function formatRecordJson(value) {
  if (!value) {
    return '无可预览JSON'
  }
  return JSON.stringify(value, null, 2)
}

function formatScore(value) {
  return Number(value || 0).toFixed(4)
}

function previewRecord(row) {
  result.value = {
    generation_id: row.generation_id,
    retrieval_id: row.retrieval_id,
    case_set_id: row.case_set_id,
    generated_json: row.generated_json || { case_set_name: '无可预览内容', nodes: [] },
    generated_text: row.generated_json ? JSON.stringify(row.generated_json, null, 2) : ''
  }
  currentStageText.value = row.generation_status === 'success' ? '生成完成，结果已返回前端' : '生成失败，请查看记录详情'
  window.scrollTo({ top: 260, behavior: 'smooth' })
}

onMounted(loadInitialData)
onBeforeUnmount(stopGeneratePolling)

watch(
  () => [form.knowledge_base_id, form.requirement_text, form.top_k],
  clearPreSearch
)
</script>

<style scoped>
.ai-generate-page {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.hero-card,
.section-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
}

.breadcrumb {
  margin-bottom: 10px;
  color: #64748b;
  font-size: 13px;
}

.hero-actions,
.preview-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.form-card,
.stage-card,
.preview-card {
  height: 100%;
}

.form-card h2,
.stage-card h2,
.preview-card h2,
.record-card h2 {
  margin: 0 0 8px;
  font-size: 18px;
}

.section-desc {
  margin: 0 0 16px;
  color: #64748b;
  line-height: 1.7;
}

.full-width {
  width: 100%;
}

.kb-summary {
  margin-top: 4px;
  padding: 14px;
  border-radius: 10px;
  background: linear-gradient(135deg, #eff6ff, #f8fafc);
  border: 1px solid #dbeafe;
  color: #1e293b;
}

.kb-title {
  margin-bottom: 6px;
  color: #2563eb;
  font-weight: 700;
}

.kb-name-line {
  font-weight: 600;
}

.kb-meta {
  margin-top: 6px;
  color: #64748b;
  font-size: 13px;
}

.kb-stats {
  margin-top: 10px;
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.kb-stat-item {
  color: #475569;
  font-size: 13px;
}

.kb-warn {
  margin-top: 10px;
  padding: 8px 12px;
  border-radius: 8px;
  background: #fffbeb;
  border: 1px solid #fde68a;
  color: #92400e;
  font-size: 12px;
  line-height: 1.6;
}

.generate-button {
  width: 100%;
  margin-top: 18px;
}

.presearch-button {
  width: 100%;
  margin-top: 10px;
}

.status-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  margin-bottom: 16px;
  border-radius: 10px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
}

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #94a3b8;
}

.status-running .status-dot {
  background: #f59e0b;
  animation: status-pulse 1s ease-in-out infinite;
}

.status-success .status-dot {
  background: #16a34a;
}

.status-text {
  color: #1e293b;
  font-weight: 700;
}

.status-detail {
  color: #64748b;
  font-size: 13px;
}

.generate-progress {
  margin: -4px 0 12px;
}

.generate-stage-detail {
  margin: -4px 0 16px;
  color: #64748b;
  font-size: 13px;
}

.retrieval-panel {
  margin-bottom: 16px;
  padding: 14px;
  border: 1px solid #dbeafe;
  border-radius: 10px;
  background: #f8fafc;
}

.retrieval-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.retrieval-head h3 {
  margin: 0 0 6px;
  font-size: 16px;
}

.retrieval-actions {
  display: flex;
  gap: 8px;
}

.chunk-check-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: 300px;
  overflow: auto;
}

.chunk-check-card {
  padding: 10px 12px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
}

.chunk-check-card :deep(.el-checkbox) {
  width: 100%;
  height: auto;
  align-items: flex-start;
  white-space: normal;
}

.chunk-check-card :deep(.el-checkbox__label) {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  width: 100%;
  min-width: 0;
}

.chunk-check-title {
  min-width: 0;
  color: #334155;
  font-weight: 700;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chunk-score {
  flex-shrink: 0;
  color: #2563eb;
  font-size: 12px;
}

.chunk-preview-text {
  margin-top: 6px;
  padding-left: 24px;
  color: #64748b;
  font-size: 13px;
  line-height: 1.7;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  white-space: pre-wrap;
}

@keyframes status-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.35; }
}

.preview-card {
  min-height: 500px;
}

.record-detail-body {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.detail-section {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.detail-title {
  width: 100%;
  color: #334155;
  font-weight: 700;
}

.detail-text {
  width: 100%;
  padding: 10px 12px;
  border-radius: 8px;
  background: #f8fafc;
  color: #475569;
  line-height: 1.7;
}

.json-preview {
  width: 100%;
  max-height: 280px;
  overflow: auto;
  margin: 0;
  padding: 12px;
  border-radius: 8px;
  background: #0f172a;
  color: #e2e8f0;
  font-size: 12px;
  line-height: 1.6;
}

.empty-text {
  color: #94a3b8;
}

.danger-text {
  color: #dc2626;
}
</style>
