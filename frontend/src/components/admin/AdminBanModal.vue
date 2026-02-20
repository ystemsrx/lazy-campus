<script setup lang="ts">
import type { AdminUserItem } from '../../types/api'

defineProps<{
  show: boolean
  user: AdminUserItem | null
  reason: string
  submitting: boolean
}>()

const emit = defineEmits<{
  close: []
  confirm: []
  'update:reason': [value: string]
}>()

function updateReason(event: Event) {
  const target = event.target as HTMLInputElement
  emit('update:reason', target.value)
}
</script>

<template>
  <Transition name="fade">
    <div v-if="show" class="av-modal-overlay" @click.self="$emit('close')">
      <div class="av-modal">
        <div class="av-modal__header">
          <h3>封禁用户</h3>
          <button class="btn btn-ghost btn-sm" @click="$emit('close')">
            <i class="fa-solid fa-xmark"></i>
          </button>
        </div>
        <div class="av-modal__body">
          <p class="av-modal-text">
            确认封禁用户 <strong>{{ user?.display_name }}</strong>（{{ user?.account }}）？
          </p>
          <div class="form-group">
            <label class="form-label">封禁原因（选填）</label>
            <input
              :value="reason"
              class="form-input"
              placeholder="输入封禁原因…"
              @input="updateReason"
              @keyup.enter="$emit('confirm')"
            />
          </div>
        </div>
        <div class="av-modal__footer">
          <button class="btn btn-outline btn-sm" @click="$emit('close')">取消</button>
          <button class="btn btn-danger btn-sm" :disabled="submitting" @click="$emit('confirm')">
            {{ submitting ? '处理中…' : '确认封禁' }}
          </button>
        </div>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.av-modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 100;
  background: rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.av-modal {
  background: var(--c-surface);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xl);
  width: min(440px, 100%);
  overflow: hidden;
}

.av-modal__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid var(--c-border-light);
}

.av-modal__header h3 {
  margin: 0;
}

.av-modal__body {
  padding: 20px;
}

.av-modal-text {
  margin-bottom: 12px;
  color: var(--c-text-secondary);
  font-size: var(--text-sm);
}

.av-modal__footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 12px 20px;
  border-top: 1px solid var(--c-border-light);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity var(--dur-fast) var(--ease);
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
