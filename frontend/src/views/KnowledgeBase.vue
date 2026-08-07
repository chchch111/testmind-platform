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
        <el-table-column prop="created_at" label="创建时间" width="190" />
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
          <el-form label-width="90px">
            <el-form-item label="资料名称">
              <el-input v-model="sourceForm.source_name" placeholder="例如：摄像头夜视测试规范" />
            </el-form-item>
            <el-form-item label="资料正文">
              <el-input v-model="sourceForm.content_text" type="textarea" :rows="8" placeholder="粘贴硬件测试规范、历史测试文档或XMind用例文本" />
            </el-form-item>
          </el-form>
          <el-button type="primary" :loading="addingSource" @click="handleAddSource">保存资料</el-button>
        </div>
      </el-col>

      <el-col :span="12">
        <div class="page-card">
          <h2>构建FAISS索引</h2>
          <p class="section-desc">系统将使用 LangChain 切片、bge-small-zh 向量化，并把 FAISS 文件保存到服务端磁盘。</p>
          <el-alert v-if="building" :title="buildStageText" type="info" show-icon :closable="false" />
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

      <el-table v-if="searchResult.length" class="result-box" :data="searchResult" border>
        <el-table-column prop="chunk_id" label="chunk_id" width="100" />
        <el-table-column prop="source_id" label="source_id" width="100" />
        <el-table-column label="score" width="120">
          <template #default="{ row }">{{ Number(row.score).toFixed(4) }}</template>
        </el-table-column>
        <el-table-column prop="chunk_text" label="命中文本" min-width="360" />
      </el-table>
    </div>

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
import { nextTick, onMounted, reactive, ref } from 'vue'
import { addManualSource, buildIndex, createKnowledgeBase, listKnowledgeBases, searchKnowledgeBase } from '../api/rag'
import { STATUS_TEXT } from '../utils/constants'
import { showSuccess, showWarning } from '../utils/message'
import { getCurrentUserId } from '../utils/storage'

const loading = ref(false)
const creating = ref(false)
const addingSource = ref(false)
const building = ref(false)
const searching = ref(false)
const createDialogVisible = ref(false)
const knowledgeBases = ref([])
const selectedKnowledgeBase = ref(null)
const buildResult = ref(null)
const buildStageText = ref('准备构建索引...')
const searchResult = ref([])
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
  }
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
    sourceForm.source_name = ''
    sourceForm.content_text = ''
  } finally {
    addingSource.value = false
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
    buildResult.value = await buildIndex(selectedKnowledgeBase.value.knowledge_base_id, getCurrentUserId())
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

function startBuildStageText() {
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

onMounted(loadKnowledgeBases)
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

.result-box {
  margin-top: 16px;
}
</style>
