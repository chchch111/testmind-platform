import { ElMessage, ElMessageBox } from 'element-plus'

export function showSuccess(message) {
  ElMessage.success(message)
}

export function showWarning(message) {
  ElMessage.warning(message)
}

export function showError(message) {
  ElMessage.error(message)
}

export function confirmAction(message, title = '操作确认') {
  return ElMessageBox.confirm(message, title, {
    confirmButtonText: '确认',
    cancelButtonText: '取消',
    type: 'warning'
  })
}

export function showErrorDetail(message, title = '错误详情') {
  return ElMessageBox.alert(message, title, {
    confirmButtonText: '我知道了',
    type: 'error'
  })
}
