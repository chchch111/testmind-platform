<template>
  <el-table :data="diffRows" border size="small">
    <el-table-column prop="label" label="字段" width="110" />
    <el-table-column label="当前内容">
      <template #default="{ row }">
        <div :class="{ changed: row.changed }">{{ row.current || '无' }}</div>
      </template>
    </el-table-column>
    <el-table-column label="历史版本内容">
      <template #default="{ row }">
        <div :class="{ changed: row.changed }">{{ row.history || '无' }}</div>
      </template>
    </el-table-column>
    <el-table-column label="是否变化" width="90">
      <template #default="{ row }">
        <el-tag :type="row.changed ? 'danger' : 'success'">{{ row.changed ? '有差异' : '一致' }}</el-tag>
      </template>
    </el-table-column>
  </el-table>
</template>

<script setup>
import { computed } from 'vue'
import { NODE_TYPE_TEXT } from '../utils/constants'

const props = defineProps({
  currentNode: {
    type: Object,
    default: null
  },
  historyVersion: {
    type: Object,
    default: null
  }
})

const fields = [
  { key: 'title', label: '标题' },
  { key: 'node_type', label: '节点类型', format: value => NODE_TYPE_TEXT[value] || value },
  { key: 'priority', label: '优先级' },
  { key: 'precondition', label: '前置条件' },
  { key: 'test_steps', label: '测试步骤' },
  { key: 'expected_result', label: '预期结果' }
]

const diffRows = computed(() => {
  if (!props.currentNode || !props.historyVersion) {
    return []
  }
  return fields.map(field => {
    const currentValue = field.format ? field.format(props.currentNode[field.key]) : props.currentNode[field.key]
    const historyValue = field.format ? field.format(props.historyVersion[field.key]) : props.historyVersion[field.key]
    return {
      label: field.label,
      current: currentValue,
      history: historyValue,
      changed: String(currentValue || '') !== String(historyValue || '')
    }
  })
})
</script>

<style scoped>
.changed {
  color: #dc2626;
  font-weight: 700;
  white-space: pre-wrap;
}
</style>
