<script setup lang="ts">
import type { AppToastMessage } from '../composables/useAppToast'

defineProps<{
  toast: AppToastMessage | null
  inline?: boolean
}>()

defineEmits<{
  dismiss: []
}>()
</script>

<template>
  <Transition v-if="!inline" name="app-toast">
    <div
      v-if="toast"
      class="app-toast app-toast--fixed"
      :class="'app-toast--' + toast.type"
      @click="$emit('dismiss')"
    >
      {{ toast.text }}
    </div>
  </Transition>
  <Transition v-else name="app-toast-inline">
    <span
      v-if="toast"
      class="app-toast app-toast--inline"
      :class="'app-toast--' + toast.type"
      @click="$emit('dismiss')"
    >
      {{ toast.text }}
    </span>
  </Transition>
</template>

<style scoped>
/* ── Fixed mode ── */
.app-toast--fixed {
  position: fixed;
  top: 20px;
  right: 24px;
  z-index: 600;
  padding: 12px 22px;
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-weight: 500;
  box-shadow: var(--shadow-lg);
  cursor: pointer;
  max-width: 420px;
}

/* ── Inline mode ── */
.app-toast--inline {
  margin-left: auto;
  font-size: 13px;
  font-weight: 500;
  padding: 5px 14px;
  border-radius: 20px;
  white-space: nowrap;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  cursor: pointer;
}

/* ── Fixed type colors ── */
.app-toast--fixed.app-toast--info {
  background: var(--c-primary);
  color: var(--c-text-inverse);
}
.app-toast--fixed.app-toast--success {
  background: var(--c-success);
  color: var(--c-text-inverse);
}
.app-toast--fixed.app-toast--warning {
  background: #f59e0b;
  color: var(--c-text-inverse);
}
.app-toast--fixed.app-toast--error {
  background: var(--c-danger);
  color: var(--c-text-inverse);
}

/* ── Inline type colors ── */
.app-toast--inline.app-toast--info {
  background: rgba(59, 130, 246, 0.12);
  color: #2563eb;
}
.app-toast--inline.app-toast--success {
  background: rgba(16, 185, 129, 0.12);
  color: #059669;
}
.app-toast--inline.app-toast--warning {
  background: rgba(245, 158, 11, 0.12);
  color: #d97706;
}
.app-toast--inline.app-toast--error {
  background: rgba(239, 68, 68, 0.12);
  color: #dc2626;
}

/* ── Fixed transitions ── */
.app-toast-enter-active {
  transition: all var(--dur-normal) var(--ease);
}
.app-toast-leave-active {
  transition: all var(--dur-fast) var(--ease);
}
.app-toast-enter-from {
  opacity: 0;
  transform: translateX(40px);
}
.app-toast-leave-to {
  opacity: 0;
  transform: translateY(-12px);
}

/* ── Inline transitions ── */
.app-toast-inline-enter-active,
.app-toast-inline-leave-active {
  transition: all 0.3s ease;
}
.app-toast-inline-enter-from,
.app-toast-inline-leave-to {
  opacity: 0;
  transform: translateX(-8px);
}
</style>
