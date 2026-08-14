<template>
  <div class="ai-result-preview">
    <template v-if="result">
      <div class="preview-header">
        <div>
          <div class="preview-title">{{ caseSetName }}</div>
          <div class="preview-subtitle">已生成 {{ stats.folderCount }} 个目录、{{ stats.caseCount }} 条测试用例</div>
        </div>
        <el-tag v-if="caseSetId" type="success" size="large">已保存到用例集 #{{ caseSetId }}</el-tag>
        <el-tag v-else type="warning" size="large">仅预览，未入库</el-tag>
      </div>

      <el-alert
        v-if="qualityWarnings.length"
        class="quality-alert"
        type="warning"
        show-icon
        :closable="false"
        title="生成结果需要人工复核"
      >
        <template #default>
          <div v-for="warning in qualityWarnings" :key="warning">{{ warning }}</div>
        </template>
      </el-alert>

      <div class="stat-row">
        <div class="stat-card">
          <span>总节点</span>
          <strong>{{ stats.total }}</strong>
        </div>
        <div class="stat-card p0">
          <span>P0</span>
          <strong>{{ stats.priority.P0 }}</strong>
        </div>
        <div class="stat-card p1">
          <span>P1</span>
          <strong>{{ stats.priority.P1 }}</strong>
        </div>
        <div class="stat-card p2">
          <span>P2/P3</span>
          <strong>{{ stats.priority.P2 + stats.priority.P3 }}</strong>
        </div>
      </div>

      <div v-if="qualitySummary || retrievalSummary" class="diagnostic-row">
        <div v-if="qualitySummary" class="diagnostic-card">
          <span>结构深度</span>
          <strong>{{ qualitySummary.max_depth || stats.maxDepth }}</strong>
        </div>
        <div v-if="qualitySummary" class="diagnostic-card">
          <span>重复标题</span>
          <strong>{{ qualitySummary.duplicate_title_count || 0 }}</strong>
        </div>
        <div v-if="qualitySummary" class="diagnostic-card">
          <span>空目录</span>
          <strong>{{ qualitySummary.leaf_folder_count || 0 }}</strong>
        </div>
        <div v-if="retrievalSummary" class="diagnostic-card">
          <span>检索来源</span>
          <strong>{{ retrievalSummary.source_count || 0 }}</strong>
        </div>
        <div v-if="retrievalSummary" class="diagnostic-card">
          <span>平均相似度</span>
          <strong>{{ formatScore(retrievalSummary.avg_score) }}</strong>
        </div>
      </div>

      <el-tree class="preview-tree" :data="treeNodes" default-expand-all node-key="preview_id">
        <template #default="{ data }">
          <div class="tree-node-row">
            <div class="node-main">
              <el-tag :type="data.node_type === 'folder' ? 'info' : 'primary'" size="small">
                {{ data.node_type === 'folder' ? '目录' : '用例' }}
              </el-tag>
              <span class="node-title">{{ data.title }}</span>
              <span class="priority-pill" :class="data.priority?.toLowerCase()">{{ data.priority || 'P1' }}</span>
            </div>
            <div v-if="data.node_type === 'case'" class="node-detail">
              <span v-if="data.precondition">前置：{{ data.precondition }}</span>
              <span v-if="data.test_steps">步骤：{{ data.test_steps }}</span>
              <span v-if="data.expected_result">预期：{{ data.expected_result }}</span>
            </div>
          </div>
        </template>
      </el-tree>
    </template>

    <el-empty v-else description="生成完成后将在这里预览树形用例结果" />
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  result: {
    type: Object,
    default: null
  }
})

const generatedJson = computed(() => props.result?.generated_json || null)
const caseSetName = computed(() => generatedJson.value?.case_set_name || 'AI生成用例集')
const caseSetId = computed(() => props.result?.case_set_id || null)
const qualityWarnings = computed(() => generatedJson.value?.quality_warnings || [])
const qualitySummary = computed(() => generatedJson.value?.quality_summary || null)
const retrievalSummary = computed(() => props.result?.retrieval_summary || null)

const treeNodes = computed(() => normalizeNodes(generatedJson.value?.nodes || []))

const stats = computed(() => {
  const value = {
    total: 0,
    folderCount: 0,
    caseCount: 0,
    maxDepth: 0,
    priority: { P0: 0, P1: 0, P2: 0, P3: 0 }
  }
  walkNodes(treeNodes.value, (node, depth) => {
    value.total += 1
    value.maxDepth = Math.max(value.maxDepth, depth)
    if (node.node_type === 'folder') {
      value.folderCount += 1
    } else {
      value.caseCount += 1
    }
    const priority = value.priority[node.priority] === undefined ? 'P1' : node.priority
    value.priority[priority] += 1
  })
  return value
})

function normalizeNodes(nodes, path = 'node') {
  return nodes.map((node, index) => ({
    ...node,
    preview_id: `${path}-${index}`,
    node_type: node.node_type || ((node.children || []).length ? 'folder' : 'case'),
    priority: node.priority || 'P1',
    children: normalizeNodes(node.children || [], `${path}-${index}`)
  }))
}

function walkNodes(nodes, callback, depth = 1) {
  nodes.forEach(node => {
    callback(node, depth)
    walkNodes(node.children || [], callback, depth + 1)
  })
}

function formatScore(value) {
  if (value === null || value === undefined) return '-'
  return Number(value || 0).toFixed(4)
}
</script>

<style scoped>
.ai-result-preview {
  min-height: 360px;
}

.preview-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.quality-alert {
  margin-bottom: 16px;
}

.preview-title {
  font-size: 18px;
  font-weight: 700;
  color: #0f172a;
}

.preview-subtitle {
  margin-top: 6px;
  color: #64748b;
  font-size: 13px;
}

.stat-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
  margin-bottom: 16px;
}

.diagnostic-row {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 16px;
}

.stat-card {
  padding: 12px;
  border-radius: 10px;
  background: #f8fafc;
  border: 1px solid #e5e7eb;
}

.stat-card span {
  display: block;
  color: #64748b;
  font-size: 13px;
}

.stat-card strong {
  display: block;
  margin-top: 6px;
  font-size: 22px;
  color: #111827;
}

.diagnostic-card {
  padding: 10px 12px;
  border-radius: 8px;
  background: #fff;
  border: 1px solid #e5e7eb;
}

.diagnostic-card span {
  display: block;
  color: #64748b;
  font-size: 12px;
}

.diagnostic-card strong {
  display: block;
  margin-top: 4px;
  color: #0f172a;
  font-size: 18px;
}

.stat-card.p0 {
  background: #fef2f2;
}

.stat-card.p1 {
  background: #eff6ff;
}

.stat-card.p2 {
  background: #f0fdf4;
}

.preview-tree {
  padding: 10px;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  max-height: 520px;
  overflow: auto;
}

.tree-node-row {
  display: flex;
  flex-direction: column;
  gap: 6px;
  width: 100%;
  padding: 5px 0;
}

.node-main {
  display: flex;
  align-items: center;
  gap: 8px;
}

.node-title {
  color: #1f2937;
  font-weight: 600;
}

.node-detail {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding-left: 56px;
  color: #475569;
  font-size: 12px;
  line-height: 1.6;
}

.node-detail span {
  max-width: 320px;
  padding: 3px 8px;
  background: #f8fafc;
  border-radius: 6px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.priority-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 30px;
  height: 20px;
  border-radius: 999px;
  color: #fff;
  font-size: 12px;
  font-weight: 700;
}

.priority-pill.p0 { background: #ef4444; }
.priority-pill.p1 { background: #0ea5e9; }
.priority-pill.p2 { background: #22c55e; }
.priority-pill.p3 { background: #f97316; }
</style>
