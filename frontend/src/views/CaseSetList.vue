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

    <el-table v-loading="loading" :data="caseSets" border>
      <el-table-column prop="case_set_id" label="ID" width="80" />
      <el-table-column prop="name" label="用例集名称" min-width="220" />
      <el-table-column label="来源" width="120">
        <template #default="{ row }">{{ SOURCE_TYPE_TEXT[row.source_type] || row.source_type }}</template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">{{ STATUS_TEXT[row.status] || row.status }}</template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="190" />
      <el-table-column label="操作" width="360" fixed="right">
        <template #default="{ row }">
          <el-button size="small" type="primary" @click="$router.push(`/case-sets/${row.case_set_id}`)">查看树</el-button>
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
      @current-change="loadCaseSets"
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
import { onMounted, reactive, ref } from 'vue'
import { createCaseSet, deleteCaseSet, listCaseSets } from '../api/case'
import { exportXmind, importXmind } from '../api/xmind'
import { SOURCE_TYPE_TEXT, STATUS_TEXT } from '../utils/constants'
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

async function loadCaseSets() {
  loading.value = true
  try {
    const result = await listCaseSets({ page: page.value, page_size: pageSize.value })
    caseSets.value = result.items || []
    total.value = result.total || 0
  } finally {
    loading.value = false
  }
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
  await deleteCaseSet(row.case_set_id, { operator_id: getCurrentUserId() })
  showSuccess('用例集删除成功')
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
    const result = await importXmind(file, getCurrentUserId())
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
    const blob = await exportXmind(row.case_set_id, getCurrentUserId(), getSavedNodeTagsMap(row.case_set_id))
    downloadBlob(blob, fileName)
    showSuccess(`XMind导出成功：${fileName}`)
  } finally {
    exportingId.value = null
  }
}

function getSavedNodeTagsMap(caseSetId) {
  try {
    const savedTagsMap = JSON.parse(window.localStorage.getItem(`rag_mindmap_node_tags_${caseSetId}`) || '{}')
    return Object.fromEntries(
      Object.entries(savedTagsMap || {})
        .map(([nodeId, tags]) => [nodeId, Array.isArray(tags) ? tags.filter(tag => tag?.text) : []])
        .filter(([, tags]) => tags.length)
    )
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
.pager {
  margin-top: 16px;
  justify-content: flex-end;
}

.hidden-file {
  display: none;
}
</style>
