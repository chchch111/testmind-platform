<template>
  <el-drawer v-model="visible" title="历史版本与差异对比" size="70%" @open="loadVersions">
    <div v-if="currentNode">
      <p class="version-tip">当前节点：{{ currentNode.title }}。选择历史版本后，可查看差异并回退。</p>
      <el-table v-loading="loading" :data="versions" border highlight-current-row @current-change="selectedVersion = $event">
        <el-table-column prop="version_no" label="版本号" width="90" />
        <el-table-column prop="operation_type" label="操作类型" width="110" />
        <el-table-column prop="change_note" label="变更说明" min-width="180" />
        <el-table-column label="创建时间" width="180">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button size="small" type="primary" @click="selectedVersion = row">对比</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div v-if="selectedVersion" class="diff-box">
        <h3>当前节点 vs 历史版本 v{{ selectedVersion.version_no }}</h3>
        <VersionDiff :current-node="currentNode" :history-version="selectedVersion" />
        <div class="drawer-actions">
          <el-button type="warning" :loading="rollingBack" @click="handleRollback">回退到该版本</el-button>
        </div>
      </div>
    </div>
    <el-empty v-else description="请先选择一个节点" />
  </el-drawer>
</template>

<script setup>
import { computed, ref } from 'vue'
import { listNodeVersions, rollbackNode } from '../api/case'
import { formatDateTime } from '../utils/format'
import { confirmAction, showSuccess } from '../utils/message'
import VersionDiff from './VersionDiff.vue'

const props = defineProps({
  modelValue: {
    type: Boolean,
    required: true
  },
  currentNode: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['update:modelValue', 'rollback-success'])

const visible = computed({
  get: () => props.modelValue,
  set: value => emit('update:modelValue', value)
})

const loading = ref(false)
const rollingBack = ref(false)
const versions = ref([])
const selectedVersion = ref(null)

async function loadVersions() {
  if (!props.currentNode) {
    return
  }
  loading.value = true
  selectedVersion.value = null
  try {
    versions.value = await listNodeVersions(props.currentNode.node_id)
  } finally {
    loading.value = false
  }
}

async function handleRollback() {
  if (!selectedVersion.value || !props.currentNode) {
    return
  }
  await confirmAction(`确认将当前节点回退到版本 v${selectedVersion.value.version_no} 吗？回退也会生成新的历史版本。`, '版本回退确认')
  rollingBack.value = true
  try {
    await rollbackNode(props.currentNode.node_id, selectedVersion.value.version_id, {
      change_note: `前端回退到版本 v${selectedVersion.value.version_no}`
    })
    showSuccess('版本回退成功')
    visible.value = false
    emit('rollback-success')
  } finally {
    rollingBack.value = false
  }
}
</script>

<style scoped>
.version-tip {
  margin-top: 0;
  color: #64748b;
}

.diff-box {
  margin-top: 18px;
}

.drawer-actions {
  margin-top: 14px;
  text-align: right;
}
</style>
