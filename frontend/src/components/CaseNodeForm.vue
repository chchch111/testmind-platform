<template>
  <el-form label-width="90px">
    <el-form-item label="标题">
      <el-input v-model="localForm.title" placeholder="请输入节点标题" />
    </el-form-item>
    <el-form-item label="类型">
      <el-select v-model="localForm.node_type" style="width: 100%">
        <el-option v-for="item in NODE_TYPE_OPTIONS" :key="item.value" :label="item.label" :value="item.value" />
      </el-select>
    </el-form-item>
    <el-form-item label="优先级">
      <el-select v-model="localForm.priority" style="width: 100%">
        <el-option v-for="item in PRIORITY_OPTIONS" :key="item.value" :label="item.label" :value="item.value" />
      </el-select>
    </el-form-item>
    <el-form-item label="前置条件">
      <el-input v-model="localForm.precondition" type="textarea" :rows="2" />
    </el-form-item>
    <el-form-item label="测试步骤">
      <el-input v-model="localForm.test_steps" type="textarea" :rows="4" />
    </el-form-item>
    <el-form-item label="预期结果">
      <el-input v-model="localForm.expected_result" type="textarea" :rows="3" />
    </el-form-item>
    <el-form-item v-if="showChangeNote" label="变更说明">
      <el-input v-model="localForm.change_note" type="textarea" :rows="2" placeholder="例如：补充测试步骤，便于历史追溯" />
    </el-form-item>
  </el-form>
</template>

<script setup>
import { reactive, watch } from 'vue'
import { NODE_TYPE_OPTIONS, PRIORITY_OPTIONS } from '../utils/constants'

const props = defineProps({
  modelValue: {
    type: Object,
    required: true
  },
  showChangeNote: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue'])

const localForm = reactive({
  title: '',
  node_type: 'folder',
  priority: 'P1',
  precondition: '',
  test_steps: '',
  expected_result: '',
  change_note: ''
})

watch(
  () => props.modelValue,
  value => {
    Object.assign(localForm, {
      title: value.title || '',
      node_type: value.node_type || 'folder',
      priority: value.priority || 'P1',
      precondition: value.precondition || '',
      test_steps: value.test_steps || '',
      expected_result: value.expected_result || '',
      change_note: value.change_note || ''
    })
  },
  { immediate: true, deep: true }
)

watch(
  localForm,
  value => {
    emit('update:modelValue', { ...value })
  },
  { deep: true }
)
</script>
