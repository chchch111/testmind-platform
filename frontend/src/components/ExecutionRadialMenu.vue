<template>
  <div v-if="visible" class="radial-mask" @click.self="$emit('close')">
    <div class="radial-menu" :style="menuStyle">
      <button class="action action-top-left" @click="emitAction('remove')">移除<span>Del</span></button>
      <button class="action action-top-right" @click="emitAction('bug')">缺陷<span>缺陷</span></button>
      <button class="action action-left" @click="emitAction('blocked')">阻塞<span>阻塞</span></button>
      <button class="action action-right" @click="emitAction('failed')">失败<span>失败</span></button>
      <button class="action action-bottom" @click="emitAction('note')">备注<span>备注</span></button>
      <button class="action action-center" @click="emitAction('passed')">通过<span>通过</span></button>
      <button class="action action-skip" @click="emitAction('skipped')">不适用<span>不适用</span></button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  x: {
    type: Number,
    default: 500
  },
  y: {
    type: Number,
    default: 300
  }
})

const emit = defineEmits(['close', 'action'])

const menuStyle = computed(() => ({
  left: `${props.x}px`,
  top: `${props.y}px`
}))

function emitAction(action) {
  emit('action', action)
}
</script>

<style scoped>
.radial-mask {
  position: fixed;
  inset: 0;
  z-index: 3000;
  background: rgba(15, 23, 42, 0.08);
}

.radial-menu {
  position: fixed;
  width: 320px;
  height: 260px;
  transform: translate(-50%, -50%);
  border: 6px solid rgba(239, 68, 68, 0.85);
  background: rgba(255, 255, 255, 0.12);
  box-shadow: 0 18px 60px rgba(15, 23, 42, 0.25);
}

.radial-menu::before {
  content: '';
  position: absolute;
  left: 50%;
  top: 50%;
  width: 170px;
  height: 170px;
  border-radius: 50%;
  transform: translate(-50%, -50%);
  background: conic-gradient(
    rgba(148, 163, 184, 0.78),
    rgba(71, 85, 105, 0.5),
    rgba(148, 163, 184, 0.78),
    rgba(71, 85, 105, 0.5),
    rgba(148, 163, 184, 0.78)
  );
}

.action {
  position: absolute;
  z-index: 2;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-width: 86px;
  min-height: 52px;
  border: 0;
  border-radius: 16px;
  background: #ffffff;
  color: #334155;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.16);
  cursor: pointer;
  font-size: 18px;
  transition: 0.16s ease;
}

.action:hover {
  transform: scale(1.06);
}

.action span {
  margin-top: 3px;
  color: #64748b;
  font-size: 12px;
}

.action-center {
  left: 50%;
  top: 50%;
  width: 84px;
  height: 84px;
  min-width: 84px;
  min-height: 84px;
  transform: translate(-50%, -50%);
  border-radius: 50%;
  color: #ffffff;
  background: #ef4444;
  font-size: 24px;
}

.action-center span {
  color: #fff;
}

.action-center:hover {
  transform: translate(-50%, -50%) scale(1.06);
}

.action-top-left {
  left: 38px;
  top: 20px;
}

.action-top-right {
  right: 38px;
  top: 20px;
}

.action-left {
  left: 34px;
  top: 112px;
}

.action-right {
  right: 34px;
  top: 112px;
}

.action-bottom {
  left: 50%;
  bottom: 14px;
  transform: translateX(-50%);
}

.action-bottom:hover {
  transform: translateX(-50%) scale(1.06);
}

.action-skip {
  left: 50%;
  top: 150px;
  min-width: 78px;
  min-height: 56px;
  border-radius: 50%;
  transform: translateX(-50%);
}

.action-skip:hover {
  transform: translateX(-50%) scale(1.06);
}
</style>
