<template>
  <div class="forbidden-page">
    <div class="page-card forbidden-card">
      <div class="status-code">403</div>
      <h1>无权限访问</h1>
      <p>当前账号没有权限进入该模块，请联系管理员调整角色后再访问。</p>
      <el-button type="primary" @click="$router.replace('/dashboard')">返回首页</el-button>
    </div>
  </div>
</template>

<style scoped>
.forbidden-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: calc(100vh - 140px);
}

.forbidden-card {
  width: 520px;
  text-align: center;
}

.status-code {
  color: #2563eb;
  font-size: 72px;
  font-weight: 800;
  line-height: 1;
}

.forbidden-card h1 {
  margin: 16px 0 8px;
  color: #0f172a;
}

.forbidden-card p {
  margin: 0 0 22px;
  color: #64748b;
  line-height: 1.8;
}
</style>
