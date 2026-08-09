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
      <el-col :span="9">
        <div class="page-card form-card">
          <h2>生成参数</h2>
          <p class="section-desc">建议先在知识库管理页补充资料并构建索引，否则后端会提示“RAG没有检索到可用上下文”。</p>

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

          <div v-if="selectedKnowledgeBase" class="kb-summary">
            <div class="kb-title">当前知识库</div>
            <div>{{ selectedKnowledgeBase.name }}</div>
            <div class="kb-meta">产品：{{ selectedKnowledgeBase.product_type || '未填写' }} / 模块：{{ selectedKnowledgeBase.hardware_module || '未填写' }}</div>
          </div>

          <el-button class="generate-button" type="primary" size="large" :loading="generating" @click="handleGenerate">
            {{ generating ? '正在生成...' : '开始AI生成' }}
          </el-button>
        </div>
      </el-col>

      <el-col :span="15">
        <div class="page-card stage-card">
          <div class="section-header">
            <div>
              <h2>生成阶段</h2>
              <p class="section-desc">用于答辩演示：清楚展示从RAG检索到用例入库的处理链路。</p>
            </div>
            <el-tag :type="generating ? 'warning' : result ? 'success' : 'info'" size="large">{{ stageStatusText }}</el-tag>
          </div>

          <el-steps :active="activeStage" finish-status="success" process-status="process" align-center>
            <el-step v-for="stage in stages" :key="stage.title" :title="stage.title" :description="stage.desc" />
          </el-steps>

          <el-alert v-if="generating" class="stage-alert" :title="currentStageText" type="info" show-icon :closable="false">
            <template #default>
              <div class="stage-hint">上方步骤为处理链路示意，实际进度以后端返回结果为准。</div>
            </template>
          </el-alert>
          <el-alert v-else-if="result" class="stage-alert" title="生成完成：可以在下方预览结果，也可以跳转到用例集详情页查看脑图。" type="success" show-icon :closable="false" />
          <el-alert v-else class="stage-alert" title="等待输入需求并开始生成。" type="info" show-icon :closable="false" />
        </div>

        <div class="page-card preview-card">
          <div class="section-header">
            <div>
              <h2>结果预览</h2>
              <p class="section-desc">生成的JSON会按目录/用例树展示，自动入库后可直接跳转到思维导图编辑器。</p>
            </div>
            <div class="preview-actions">
              <el-button :disabled="!result" @click="copyGeneratedText">复制原始JSON</el-button>
              <el-button type="primary" :disabled="!lastCaseSetId" @click="openGeneratedCaseSet">打开脑图</el-button>
            </div>
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
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import AiResultPreview from '../components/AiResultPreview.vue'
import { generateCaseSet, listGenerationRecords } from '../api/ai'
import { listKnowledgeBases } from '../api/rag'
import { formatDateTime } from '../utils/format'
import { showSuccess, showWarning } from '../utils/message'
import { getCurrentUserId } from '../utils/storage'

const router = useRouter()
const knowledgeBases = ref([])
const records = ref([])
const result = ref(null)
const generating = ref(false)
const recordLoading = ref(false)
const recordDetailVisible = ref(false)
const activeRecord = ref(null)
const activeStage = ref(0)
const currentStageText = ref('等待开始生成')
let stageTimer = null

const stages = [
  { title: '选择知识库', desc: '确定检索范围' },
  { title: 'RAG检索', desc: '召回相似知识' },
  { title: 'AI生成', desc: '输出树形JSON' },
  { title: '结果入库', desc: '保存为用例集' },
  { title: '脑图预览', desc: '跳转编辑器' }
]

const form = reactive({
  knowledge_base_id: null,
  requirement_text: '基于摄像头WEB管理后台，生成视频编码参数、4K/1080P清晰度、存储空间、系统信息相关的功能测试用例。',
  top_k: 5,
  save_to_case_set: true
})

const selectedKnowledgeBase = computed(() => knowledgeBases.value.find(item => item.knowledge_base_id === form.knowledge_base_id) || null)
const lastCaseSetId = computed(() => result.value?.case_set_id || null)
const stageStatusText = computed(() => {
  if (generating.value) {
    return '生成中'
  }
  return result.value ? '已完成' : '待开始'
})

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

  generating.value = true
  result.value = null
  startStageProgress()
  try {
    const data = await generateCaseSet({
      knowledge_base_id: form.knowledge_base_id,
      requirement_text: form.requirement_text,
      top_k: form.top_k,
      created_by: getCurrentUserId(),
      save_to_case_set: form.save_to_case_set
    })
    result.value = data
    activeStage.value = stages.length
    currentStageText.value = '生成完成，结果已返回前端'
    showSuccess(data.case_set_id ? `AI生成成功，已保存为用例集 #${data.case_set_id}` : 'AI生成成功，结果已返回预览')
    await loadRecords()
  } finally {
    stopStageProgress()
    generating.value = false
  }
}

function startStageProgress() {
  // 说明：后端当前是单次同步请求，无法返回真实阶段进度。
  // 这里仅展示处理链路示意，完成后跳到完成态。
  const texts = [
    '正在调用后端生成服务（RAG检索 → AI生成 → 结果入库）...',
    '后端处理中，请耐心等待...'
  ]
  activeStage.value = 1
  currentStageText.value = texts[0]
  let index = 0
  stageTimer = window.setInterval(() => {
    index = Math.min(index + 1, texts.length - 1)
    currentStageText.value = texts[index]
  }, 3000)
}

function stopStageProgress() {
  if (stageTimer) {
    window.clearInterval(stageTimer)
    stageTimer = null
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

function previewRecord(row) {
  result.value = {
    generation_id: row.generation_id,
    retrieval_id: row.retrieval_id,
    case_set_id: row.case_set_id,
    generated_json: row.generated_json || { case_set_name: '无可预览内容', nodes: [] },
    generated_text: row.generated_json ? JSON.stringify(row.generated_json, null, 2) : ''
  }
  activeStage.value = row.generation_status === 'success' ? stages.length : 0
  window.scrollTo({ top: 260, behavior: 'smooth' })
}

onMounted(loadInitialData)
onBeforeUnmount(stopStageProgress)
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

.kb-meta {
  margin-top: 6px;
  color: #64748b;
  font-size: 13px;
}

.generate-button {
  width: 100%;
  margin-top: 18px;
}

.stage-card {
  margin-bottom: 18px;
}

.stage-alert {
  margin-top: 22px;
}

.stage-hint {
  margin-top: 6px;
  color: #94a3b8;
  font-size: 12px;
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
