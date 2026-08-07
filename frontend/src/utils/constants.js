export const CURRENT_USER_ID_KEY = 'rag_mindmap_current_user_id'

export const SOURCE_TYPE_TEXT = {
  manual: '手动创建',
  xmind_import: 'XMind导入',
  ai_generated: 'AI生成'
}

export const STATUS_TEXT = {
  active: '正常',
  disabled: '已禁用',
  archived: '已归档',
  draft: '草稿',
  assigned: '已分配',
  running: '执行中',
  finished: '已完成',
  cancelled: '已取消'
}

export const NODE_TYPE_TEXT = {
  folder: '目录',
  case: '测试用例'
}

export const EXECUTION_STATUS_TEXT = {
  not_run: '未执行',
  passed: '通过',
  failed: '失败',
  blocked: '阻塞',
  skipped: '不适用'
}

export const PRIORITY_OPTIONS = [
  { label: 'P0 高危', value: 'P0' },
  { label: 'P1 重要', value: 'P1' },
  { label: 'P2 一般', value: 'P2' },
  { label: 'P3 较低', value: 'P3' }
]

export const NODE_TYPE_OPTIONS = [
  { label: '目录', value: 'folder' },
  { label: '测试用例', value: 'case' }
]
