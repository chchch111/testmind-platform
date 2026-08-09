<template>
  <div class="permission-page">
    <div class="page-card">
      <div class="page-header-row">
        <div>
          <h1 class="page-title">权限管理</h1>
          <p class="page-desc">管理员可在此查看系统用户，并调整用户角色和启用状态。</p>
        </div>
        <div class="header-actions">
          <el-button type="primary" @click="openCreateDialog">新增用户</el-button>
          <el-button type="primary" :loading="loading" @click="loadUsers">刷新</el-button>
        </div>
      </div>
    </div>

    <div class="summary-grid">
      <div class="summary-card page-card">
        <span>用户总数</span>
        <strong>{{ total }}</strong>
      </div>
      <div class="summary-card page-card">
        <span>本页管理员</span>
        <strong>{{ countByRole('admin') }}</strong>
      </div>
      <div class="summary-card page-card">
        <span>本页启用</span>
        <strong>{{ countByActive(1) }}</strong>
      </div>
      <div class="summary-card page-card">
        <span>本页禁用</span>
        <strong>{{ countByActive(0) }}</strong>
      </div>
    </div>

    <div class="page-card">
      <div class="filter-bar">
        <el-input v-model="filters.keyword" clearable placeholder="用户名/姓名/邮箱/手机号" class="keyword-input" @keyup.enter="searchUsers" />
        <el-select v-model="filters.role_code" clearable placeholder="全部角色" class="filter-select">
          <el-option v-for="role in roles" :key="role.value" :label="role.label" :value="role.value" />
        </el-select>
        <el-select v-model="filters.is_active" clearable placeholder="全部状态" class="filter-select">
          <el-option label="启用" :value="1" />
          <el-option label="禁用" :value="0" />
        </el-select>
        <el-button type="primary" @click="searchUsers">查询</el-button>
        <el-button @click="resetFilters">重置</el-button>
        <span class="filter-count">筛选结果 {{ total }} 条</span>
      </div>

      <el-table v-loading="loading" :data="users" border empty-text="暂无用户数据">
        <el-table-column prop="user_id" label="ID" width="80" />
        <el-table-column label="用户名" min-width="160">
          <template #default="{ row }">
            <span>{{ row.username }}</span>
            <el-tag v-if="row.user_id === currentUser?.user_id" class="current-user-tag" size="small">当前账号</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="real_name" label="真实姓名" min-width="130" />
        <el-table-column label="角色" width="130">
          <template #default="{ row }">
            <el-tag :type="roleTagType(row.role_code)">{{ roleLabel(row.role_code) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="email" label="邮箱" min-width="180" show-overflow-tooltip />
        <el-table-column prop="phone" label="手机号" min-width="140" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_active === 1 ? 'success' : 'danger'">{{ row.is_active === 1 ? '启用' : '禁用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="190">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" @click="openEditDialog(row)">编辑权限</el-button>
            <el-button size="small" type="warning" @click="openResetPasswordDialog(row)">重置密码</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        class="pager"
        background
        layout="prev, pager, next, total"
        v-model:current-page="page"
        :total="total"
        :page-size="pageSize"
        @current-change="loadUsers"
      />
    </div>

    <el-dialog v-model="editDialogVisible" title="编辑用户权限" width="520px">
      <el-alert
        v-if="isEditingCurrentUser"
        class="self-edit-alert"
        title="当前正在编辑自己的账号，不能移除管理员角色或禁用自己。"
        type="warning"
        :closable="false"
        show-icon
      />
      <el-form v-if="editingUser" label-width="90px">
        <el-form-item label="用户名">
          <el-input :model-value="editingUser.username" disabled />
        </el-form-item>
        <el-form-item label="真实姓名">
          <el-input :model-value="editingUser.real_name || '-'" disabled />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="editForm.role_code" class="wide-select" :disabled="isEditingCurrentUser">
            <el-option v-for="role in roles" :key="role.value" :label="role.label" :value="role.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="启用状态">
          <el-switch v-model="editForm.is_active" :active-value="1" :inactive-value="0" active-text="启用" inactive-text="禁用" :disabled="isEditingCurrentUser" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSavePermission">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="createDialogVisible" title="新增用户" width="560px">
      <el-form label-width="90px">
        <el-form-item label="用户名">
          <el-input v-model="createForm.username" placeholder="字母/数字/下划线，2-50位" />
        </el-form-item>
        <el-form-item label="初始密码">
          <el-input v-model="createForm.password" type="password" show-password placeholder="至少6位" />
        </el-form-item>
        <el-form-item label="真实姓名">
          <el-input v-model="createForm.real_name" placeholder="可选" />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="createForm.role_code" class="wide-select">
            <el-option v-for="role in roles" :key="role.value" :label="role.label" :value="role.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="createForm.email" placeholder="可选" />
        </el-form-item>
        <el-form-item label="手机号">
          <el-input v-model="createForm.phone" placeholder="可选" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="handleCreateUser">创建用户</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="resetDialogVisible" title="重置密码" width="460px">
      <el-form label-width="90px">
        <el-form-item label="用户名">
          <el-input :model-value="editingUser?.username || ''" disabled />
        </el-form-item>
        <el-form-item label="新密码">
          <el-input v-model="resetPassword" type="password" show-password placeholder="至少6位" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="resetDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="resetting" @click="handleResetPassword">确认重置</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { createUser, getPermissionUserDetail, listPermissionUsers, listRoles, resetUserPassword, updateUserPermission } from '../api/permission'
import { ROLE_TEXT } from '../utils/constants'
import { formatDateTime } from '../utils/format'
import { confirmAction, showSuccess, showWarning } from '../utils/message'
import { getCurrentUser } from '../utils/storage'

const loading = ref(false)
const saving = ref(false)
const creating = ref(false)
const resetting = ref(false)
const editDialogVisible = ref(false)
const createDialogVisible = ref(false)
const resetDialogVisible = ref(false)
const users = ref([])
const roles = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const editingUser = ref(null)
const resetPassword = ref('')
const currentUser = computed(() => getCurrentUser())
const isEditingCurrentUser = computed(() => editingUser.value?.user_id === currentUser.value?.user_id)
const filters = reactive({ keyword: '', role_code: '', is_active: null })
const editForm = reactive({ role_code: '', is_active: 1 })
const createForm = reactive({
  username: '',
  password: '',
  real_name: '',
  role_code: 'tester',
  email: '',
  phone: ''
})

async function loadRoles() {
  const data = await listRoles()
  roles.value = data.length ? data : Object.entries(ROLE_TEXT).map(([value, label]) => ({ value, label }))
}

async function loadUsers() {
  loading.value = true
  try {
    const result = await listPermissionUsers({
      keyword: filters.keyword.trim() || undefined,
      role_code: filters.role_code || undefined,
      is_active: filters.is_active === null || filters.is_active === '' ? undefined : filters.is_active,
      page: page.value,
      page_size: pageSize.value
    })
    users.value = result.items || []
    total.value = result.total || 0
  } finally {
    loading.value = false
  }
}

function searchUsers() {
  page.value = 1
  loadUsers()
}

function resetFilters() {
  filters.keyword = ''
  filters.role_code = ''
  filters.is_active = null
  searchUsers()
}

async function openEditDialog(row) {
  const detail = await getPermissionUserDetail(row.user_id)
  editingUser.value = detail
  editForm.role_code = detail.role_code
  editForm.is_active = detail.is_active
  editDialogVisible.value = true
}

async function handleSavePermission() {
  if (!editingUser.value) {
    return
  }
  if (editingUser.value.user_id === currentUser.value?.user_id) {
    if (editForm.role_code !== 'admin') {
      showWarning('不能移除当前登录用户的管理员角色')
      return
    }
    if (editForm.is_active !== 1) {
      showWarning('不能禁用当前登录用户')
      return
    }
  }
  saving.value = true
  try {
    await updateUserPermission(editingUser.value.user_id, {
      role_code: editForm.role_code,
      is_active: editForm.is_active
    })
    showSuccess('用户权限已更新')
    editDialogVisible.value = false
    await loadUsers()
  } finally {
    saving.value = false
  }
}

function openCreateDialog() {
  Object.assign(createForm, {
    username: '',
    password: '',
    real_name: '',
    role_code: 'tester',
    email: '',
    phone: ''
  })
  createDialogVisible.value = true
}

async function handleCreateUser() {
  const username = createForm.username.trim()
  if (!/^[a-zA-Z0-9_]{2,50}$/.test(username)) {
    showWarning('用户名只能包含字母、数字、下划线，长度2-50位')
    return
  }
  if (createForm.password.length < 6) {
    showWarning('密码至少6位')
    return
  }
  creating.value = true
  try {
    await createUser({
      username,
      password: createForm.password,
      real_name: createForm.real_name.trim() || null,
      role_code: createForm.role_code,
      email: createForm.email.trim() || null,
      phone: createForm.phone.trim() || null
    })
    showSuccess('用户创建成功')
    createDialogVisible.value = false
    await loadUsers()
  } finally {
    creating.value = false
  }
}

function openResetPasswordDialog(row) {
  editingUser.value = row
  resetPassword.value = ''
  resetDialogVisible.value = true
}

async function handleResetPassword() {
  if (!editingUser.value) {
    return
  }
  if (resetPassword.value.length < 6) {
    showWarning('新密码至少6位')
    return
  }
  await confirmAction(`确认将用户「${editingUser.value.username}」的密码重置为输入的新密码吗？`, '重置密码确认')
  resetting.value = true
  try {
    await resetUserPassword(editingUser.value.user_id, resetPassword.value)
    showSuccess('密码已重置')
    resetDialogVisible.value = false
  } finally {
    resetting.value = false
  }
}

function roleLabel(roleCode) {
  return roles.value.find(role => role.value === roleCode)?.label || ROLE_TEXT[roleCode] || roleCode
}

function roleTagType(roleCode) {
  if (roleCode === 'admin') return 'danger'
  if (roleCode === 'manager') return 'warning'
  if (roleCode === 'executor') return 'success'
  return 'info'
}

function countByRole(roleCode) {
  return users.value.filter(user => user.role_code === roleCode).length
}

function countByActive(active) {
  return users.value.filter(user => user.is_active === active).length
}

onMounted(async () => {
  await loadRoles()
  await loadUsers()
})
</script>

<style scoped>
.permission-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.page-header-row {
  display: flex;
  justify-content: space-between;
  gap: 16px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.summary-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.summary-card span {
  color: #64748b;
  font-size: 13px;
}

.summary-card strong {
  color: #1f2937;
  font-size: 28px;
}

.filter-bar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 14px;
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

.current-user-tag {
  margin-left: 8px;
}

.self-edit-alert {
  margin-bottom: 16px;
}

.pager {
  margin-top: 16px;
  justify-content: flex-end;
}

.wide-select {
  width: 100%;
}
</style>
