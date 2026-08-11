<template>
  <div v-if="visible" class="status-mask" @mousedown.self="$emit('close')" @contextmenu.prevent.self="$emit('close')">
    <div class="status-dial" :style="menuStyle" @click.stop>
      <!-- 闭合灰色环形轨道 -->
      <svg class="track-arc" viewBox="0 0 290 360" aria-hidden="true">
        <circle
          cx="145" cy="165" r="78"
          fill="none"
          stroke="rgba(71, 85, 105, 0.22)"
          stroke-width="20"
        />
      </svg>

      <!-- 顶部左胶囊：移除 (Del) -->
      <button class="tag-capsule tag-remove" @click="emitAction('remove')">
        <span class="tag-main">移除</span>
        <span class="tag-note">(Del)</span>
      </button>

      <!-- 顶部右胶囊：缺陷 (缺陷) -->
      <button class="tag-capsule tag-bug" @click="emitAction('bug')">
        <span class="tag-main">缺陷</span>
        <span class="tag-note">(缺陷)</span>
      </button>

      <!-- 环形正上方：红色主状态「通过」（覆盖在环上） -->
      <button class="ring-node ring-passed" @click="emitAction('passed')">
        <span class="ring-main">通过</span>
        <span class="ring-sub">通过</span>
      </button>

      <!-- 环形左侧：白色「阻塞」 -->
      <button class="ring-node ring-blocked" @click="emitAction('blocked')">
        <span class="ring-main">阻塞</span>
        <span class="ring-sub">阻塞</span>
      </button>

      <!-- 环形右侧：白色「失败」 -->
      <button class="ring-node ring-failed" @click="emitAction('failed')">
        <span class="ring-main">失败</span>
        <span class="ring-sub">失败</span>
      </button>

      <!-- 环形正下方：白色「不适用」 -->
      <button class="ring-node ring-skipped" @click="emitAction('skipped')">
        <span class="ring-main">不适用</span>
        <span class="ring-sub">不适用</span>
      </button>

      <!-- 底部居中胶囊：备注 (备注) -->
      <button class="tag-capsule tag-note" @click="emitAction('note')">
        <span class="tag-icon">✎</span>
        <span class="tag-main">备注</span>
        <span class="tag-note">(备注)</span>
      </button>
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
    default: 0
  },
  y: {
    type: Number,
    default: 0
  }
})

const emit = defineEmits(['close', 'action'])

const MENU_WIDTH = 290
const MENU_HEIGHT = 360

// 钳制在视口内，避免菜单跑到屏幕外点不到。
const menuStyle = computed(() => {
  const left = Math.max(8, Math.min(props.x - MENU_WIDTH / 2, window.innerWidth - MENU_WIDTH - 8))
  const top = Math.max(8, Math.min(props.y - MENU_HEIGHT / 2, window.innerHeight - MENU_HEIGHT - 8))
  return {
    left: `${left}px`,
    top: `${top}px`
  }
})

function emitAction(action) {
  emit('action', action)
}
</script>

<style scoped>
.status-mask {
  position: fixed;
  inset: 0;
  z-index: 3000;
  background: transparent;
}

.status-dial {
  position: fixed;
  width: 290px;
  height: 360px;
  pointer-events: none;
}

.track-arc {
  position: absolute;
  left: 0;
  top: 0;
  width: 290px;
  height: 360px;
  pointer-events: none;
  filter: drop-shadow(0 8px 20px rgba(15, 23, 42, 0.08));
}

/* ---------- 环形状态节点（覆盖在轨道上） ---------- */
.ring-node {
  position: absolute;
  width: 54px;
  height: 54px;
  border: 0;
  border-radius: 50%;
  background: #ffffff;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.16);
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 3px;
  pointer-events: auto;
  transition: transform 0.16s ease, box-shadow 0.16s ease;
}

.ring-node:hover:not(.ring-passed) {
  transform: translateY(-2px);
  box-shadow: 0 14px 30px rgba(15, 23, 42, 0.22);
}

.ring-main {
  color: #111827;
  font-size: 13px;
  font-weight: 800;
  line-height: 1;
}

.ring-sub {
  color: #9ca3af;
  font-size: 9px;
  font-weight: 600;
  line-height: 1;
  letter-spacing: 1px;
}

/* 环心：红色主状态「通过」（保留在圆环中央，参考用例编辑菜单主操作） */
.ring-passed {
  left: 110px;
  top: 130px;
  width: 70px;
  height: 70px;
  background: radial-gradient(circle at 35% 30%, #f87171, #f05b67);
  box-shadow: 0 14px 32px rgba(240, 91, 103, 0.45), 0 4px 12px rgba(15, 23, 42, 0.2);
}

/* 主状态悬停逻辑（与用例编辑一致）：不抬起、阴影不变 */
.ring-passed:hover {
  transform: none;
  box-shadow: 0 14px 32px rgba(240, 91, 103, 0.45), 0 4px 12px rgba(15, 23, 42, 0.2);
}

.ring-passed .ring-main {
  color: #ffffff;
  font-size: 16px;
}

.ring-passed .ring-sub {
  color: rgba(255, 255, 255, 0.88);
}

/* 环上 120° 等角均匀分布：环心 (145,165) 半径 78，从正上顺时针 */
.ring-blocked {
  left: 118px;
  top: 60px;
}

.ring-failed {
  left: 186px;
  top: 177px;
}

.ring-skipped {
  left: 50px;
  top: 177px;
}

/* ---------- 外围胶囊标签 ---------- */
.tag-capsule {
  position: absolute;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  height: 38px;
  padding: 0 18px;
  border: 0;
  border-radius: 999px;
  background: #ffffff;
  box-shadow: 0 8px 20px rgba(15, 23, 42, 0.14);
  cursor: pointer;
  pointer-events: auto;
  transition: transform 0.16s ease, box-shadow 0.16s ease;
}

.tag-capsule:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 26px rgba(15, 23, 42, 0.2);
}

.tag-main {
  color: #1f2937;
  font-size: 13px;
  font-weight: 800;
  line-height: 1;
}

.tag-note {
  color: #9ca3af;
  font-size: 11px;
  font-weight: 600;
  line-height: 1;
}

.tag-icon {
  color: #64748b;
  font-size: 13px;
  line-height: 1;
}

.tag-remove { left: 12px; top: 10px; }
.tag-bug { left: 188px; top: 10px; }
.tag-note { left: 92px; top: 306px; }
</style>
