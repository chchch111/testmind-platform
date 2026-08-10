<template>
  <div class="page-card">
    <h1 class="page-title">用例集管理</h1>
    <p class="page-desc">管理思维导图式测试用例集，支持新建、删除、查看树、XMind导入和自定义文件名导出。</p>

    <div class="toolbar">
      <el-button type="primary" @click="openCreateDialog">新建用例集</el-button>
      <el-button type="success" :loading="importing" @click="openImportFile">导入XMind</el-button>
      <el-button @click="loadCaseSets">刷新列表</el-button>
      <input ref="fileInputRef" class="hidden-file" type="file" accept=".xmind" @change="handleImportFileChange" />
    </div>

    <div class="filter-bar">
      <el-input v-model="filters.keyword" clearable placeholder="按名称/描述搜索" class="keyword-input" />
      <el-select v-model="filters.sourceType" clearable placeholder="全部来源" class="filter-select">
        <el-option v-for="option in sourceTypeOptions" :key="option.value" :label="option.label" :value="option.value" />
      </el-select>
      <el-select v-model="filters.status" clearable placeholder="全部状态" class="filter-select">
        <el-option v-for="option in statusOptions" :key="option.value" :label="option.label" :value="option.value" />
      </el-select>
      <el-button @click="resetFilters">重置筛选</el-button>
      <span class="filter-count">共 {{ total }} 条</span>
    </div>

    <el-table v-loading="loading" :data="caseSets" border>
      <el-table-column prop="case_set_id" label="ID" width="80" />
      <el-table-column prop="name" label="用例集名称" min-width="220" />
      <el-table-column label="来源" width="120">
        <template #default="{ row }">{{ SOURCE_TYPE_TEXT[row.source_type] || row.source_type }}</template>
      </el-table-column>
      <el-table-column label="AI生成需求" min-width="200" show-overflow-tooltip>
        <template #default="{ row }">
          <span v-if="row.requirement_text" class="req-text">{{ row.requirement_text }}</span>
          <span v-else class="req-empty">-</span>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">{{ STATUS_TEXT[row.status] || row.status }}</template>
      </el-table-column>
      <el-table-column label="创建时间" width="190">
        <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="430" fixed="right">
        <template #default="{ row }">
          <el-button size="small" type="primary" @click="$router.push(`/case-sets/${row.case_set_id}`)">查看树</el-button>
          <el-button v-if="row.status === 'draft'" size="small" type="success" @click="handlePublish(row)">发布</el-button>
          <el-button size="small" type="success" :loading="exportingId === row.case_set_id" @click="handleExport(row)">导出XMind</el-button>
          <el-button size="small" type="danger" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      class="pager"
      background
      layout="prev, pager, next, total"
      :total="total"
      :page-size="pageSize"
      v-model:current-page="page"
    />

    <el-dialog v-model="createDialogVisible" title="新建用例集" width="520px">
      <el-form label-width="90px">
        <el-form-item label="名称">
          <el-input v-model="createForm.name" placeholder="例如：摄像头夜视功能测试用例集" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="createForm.description" type="textarea" :rows="4" placeholder="请输入用例集说明" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="handleCreate">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ElMessageBox } from 'element-plus'
import { onMounted, reactive, ref, watch } from 'vue'
import { createCaseSet, deleteCaseSet, listCaseSets, publishCaseSet } from '../api/case'
import { getCaseSetMetas } from '../api/canvas'
import { exportXmind, importXmind } from '../api/xmind'
import { SOURCE_TYPE_TEXT, STATUS_TEXT } from '../utils/constants'
import { formatDateTime } from '../utils/format'
import { confirmAction, showErrorDetail, showSuccess } from '../utils/message'
import { getCurrentUserId } from '../utils/storage'

const loading = ref(false)
const creating = ref(false)
const importing = ref(false)
const exportingId = ref(null)
const caseSets = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const createDialogVisible = ref(false)
const fileInputRef = ref(null)
const createForm = reactive({ name: '', description: '' })
const filters = reactive({ keyword: '', sourceType: '', status: '' })

const sourceTypeOptions = Object.entries(SOURCE_TYPE_TEXT).map(([value, label]) => ({ value, label }))
const statusOptions = ['active', 'disabled', 'archived'].map(value => ({ value, label: STATUS_TEXT[value] || value }))

watch([filters, page], () => {
  loadCaseSets()
})

async function loadCaseSets() {
  loading.value = true
  try {
    const result = await listCaseSets({
      page: page.value,
      page_size: pageSize.value,
      keyword: filters.keyword.trim() || undefined,
      source_type: filters.sourceType || undefined,
      status: filters.status || undefined
    })
    caseSets.value = result.items || []
    total.value = result.total || 0
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  filters.keyword = ''
  filters.sourceType = ''
  filters.status = ''
  page.value = 1
}

function openCreateDialog() {
  createForm.name = ''
  createForm.description = ''
  createDialogVisible.value = true
}

async function handleCreate() {
  if (!createForm.name.trim()) {
    return
  }
  creating.value = true
  try {
    await createCaseSet({
      name: createForm.name,
      description: createForm.description,
      created_by: getCurrentUserId()
    })
    showSuccess('用例集创建成功')
    createDialogVisible.value = false
    await loadCaseSets()
  } finally {
    creating.value = false
  }
}

async function handleDelete(row) {
  await confirmAction(`确认删除用例集「${row.name}」吗？该操作会逻辑删除其下节点。`)
  await deleteCaseSet(row.case_set_id)
  showSuccess('用例集删除成功')
  await loadCaseSets()
}

async function handlePublish(row) {
  await confirmAction(`确认发布用例集「${row.name}」吗？发布后其他用户可以查看和使用它。`, '发布用例集')
  await publishCaseSet(row.case_set_id)
  showSuccess('用例集已发布')
  await loadCaseSets()
}

function openImportFile() {
  fileInputRef.value?.click()
}

async function handleImportFileChange(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) {
    return
  }
  if (!file.name.toLowerCase().endsWith('.xmind')) {
    await showErrorDetail('请选择 .xmind 格式文件。', 'XMind导入失败')
    return
  }

  importing.value = true
  try {
    const result = await importXmind(file)
    await ElMessageBox.alert(
      `导入成功！\n用例集ID：${result.case_set_id}\n导入批次ID：${result.import_batch_id}\n节点数量：${result.node_count}`,
      'XMind导入成功',
      { confirmButtonText: '我知道了', type: 'success' }
    )
    await loadCaseSets()
  } catch (error) {
    await showErrorDetail(error.message || 'XMind导入失败，请检查文件格式。', 'XMind导入失败详情')
  } finally {
    importing.value = false
  }
}

async function handleExport(row) {
  const defaultName = ensureXmindFileName(row.name)
  const { value } = await ElMessageBox.prompt('请输入导出的XMind文件名', '导出XMind', {
    confirmButtonText: '导出',
    cancelButtonText: '取消',
    inputValue: defaultName,
    inputPlaceholder: defaultName
  })

  const fileName = ensureXmindFileName(value || defaultName)
  exportingId.value = row.case_set_id
  try {
    const nodeTagsMap = await getSavedNodeTagsMap(row.case_set_id)
    const blob = await exportXmind(row.case_set_id, nodeTagsMap)
    downloadBlob(blob, fileName)
    showSuccess(`XMind导出成功：${fileName}`)
  } finally {
    exportingId.value = null
  }
}

async function getSavedNodeTagsMap(caseSetId) {
  try {
    const result = await getCaseSetMetas(caseSetId)
    const tagsMap = {}
    for (const item of result.items || []) {
      if (item.meta_type === 'tag' && item.meta_key) {
        tagsMap[item.node_id] = [...(tagsMap[item.node_id] || []), item.meta_key]
      }
    }
    return tagsMap
  } catch {
    return {}
  }
}

function ensureXmindFileName(name) {
  const safeName = String(name || '用例集').replace(/[\\/:*?"<>|]/g, '_').trim() || '用例集'
  return safeName.toLowerCase().endsWith('.xmind') ? safeName : `${safeName}.xmind`
}

function downloadBlob(blob, fileName) {
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = fileName
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
}

onMounted(loadCaseSets)
</script>

<style scoped>
.filter-bar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  margin: 14px 0;
}

.keyword-input {
  width: 260px;
}

.filter-select {
  width: 150px;
}

.filter-count {
  color: #64748b;
  font-size: 13px;
}

.req-text {
  color: #475569;
}

.req-empty {
  color: #94a3b8;
}

.pager {
  margin-top: 16px;
  justify-content: flex-end;
}

.hidden-file {
  display: none;
}
</style>
