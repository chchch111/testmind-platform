<template>
  <el-tree
    :data="treeData"
    node-key="node_id"
    default-expand-all
    highlight-current
    :props="treeProps"
    @node-click="node => $emit('select', node)"
  >
    <template #default="{ data }">
      <span class="tree-node">
        <el-tag size="small" :type="data.node_type === 'case' ? 'success' : 'info'">
          {{ NODE_TYPE_TEXT[data.node_type] || data.node_type }}
        </el-tag>
        <span class="node-title">{{ data.title }}</span>
        <el-tag size="small" type="warning">{{ data.priority }}</el-tag>
      </span>
    </template>
  </el-tree>
</template>

<script setup>
import { NODE_TYPE_TEXT } from '../utils/constants'

defineProps({
  treeData: {
    type: Array,
    default: () => []
  }
})

defineEmits(['select'])

const treeProps = {
  children: 'children',
  label: 'title'
}
</script>

<style scoped>
.tree-node {
  display: flex;
  align-items: center;
  gap: 8px;
}

.node-title {
  font-weight: 600;
}
</style>
