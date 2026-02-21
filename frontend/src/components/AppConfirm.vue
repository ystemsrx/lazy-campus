<script lang="ts">
import { reactive } from 'vue'

export interface ConfirmOptions {
  title?: string
  message: string
  confirmText?: string
  cancelText?: string
  type?: 'info' | 'warning' | 'danger'
}

interface ConfirmState {
  visible: boolean
  title: string
  message: string
  confirmText: string
  cancelText: string
  type: 'info' | 'warning' | 'danger'
  resolve: ((value: boolean) => void) | null
}

export const confirmState = reactive<ConfirmState>({
  visible: false,
  title: '确认',
  message: '',
  confirmText: '确定',
  cancelText: '取消',
  type: 'info',
  resolve: null,
})

export function appConfirm(options: ConfirmOptions): Promise<boolean> {
  return new Promise((resolve) => {
    confirmState.title = options.title ?? '确认'
    confirmState.message = options.message
    confirmState.confirmText = options.confirmText ?? '确定'
    confirmState.cancelText = options.cancelText ?? '取消'
    confirmState.type = options.type ?? 'info'
    confirmState.resolve = resolve
    confirmState.visible = true
  })
}
</script>

<script setup lang="ts">
function handleConfirm() {
  confirmState.resolve?.(true)
  confirmState.visible = false
  confirmState.resolve = null
}

function handleCancel() {
  confirmState.resolve?.(false)
  confirmState.visible = false
  confirmState.resolve = null
}

function handleOverlay(e: MouseEvent) {
  if (e.target === e.currentTarget) handleCancel()
}
</script>

<template>
  <Teleport to="body">
    <Transition name="ac">
      <div v-if="confirmState.visible" class="ac-overlay" @mousedown="handleOverlay">
        <div class="ac-dialog" :class="`ac-dialog--${confirmState.type}`">
          <div class="ac-dialog__header">
            <i
              class="ac-dialog__icon"
              :class="{
                'fa-solid fa-circle-info': confirmState.type === 'info',
                'fa-solid fa-triangle-exclamation': confirmState.type === 'warning',
                'fa-solid fa-circle-exclamation': confirmState.type === 'danger',
              }"
            ></i>
            <span class="ac-dialog__title">{{ confirmState.title }}</span>
          </div>
          <div class="ac-dialog__body">{{ confirmState.message }}</div>
          <div class="ac-dialog__footer">
            <button class="btn btn-outline btn-sm" @click="handleCancel">{{ confirmState.cancelText }}</button>
            <button
              class="btn btn-sm"
              :class="{
                'btn-primary': confirmState.type === 'info',
                'btn-warning': confirmState.type === 'warning',
                'btn-danger': confirmState.type === 'danger',
              }"
              @click="handleConfirm"
            >{{ confirmState.confirmText }}</button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.ac-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.35);
  backdrop-filter: blur(2px);
}

.ac-dialog {
  background: #fff;
  border-radius: var(--radius-xl, 16px);
  box-shadow: var(--shadow-xl, 0 20px 60px rgba(0, 0, 0, 0.18));
  width: 380px;
  max-width: calc(100vw - 32px);
  padding: 24px;
  animation: ac-pop 0.22s var(--ease, cubic-bezier(0.16, 1, 0.3, 1));
}

@keyframes ac-pop {
  from {
    opacity: 0;
    transform: scale(0.92) translateY(8px);
  }
}

.ac-dialog__header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.ac-dialog__icon {
  font-size: 20px;
}
.ac-dialog--info .ac-dialog__icon { color: var(--c-accent, #6366f1); }
.ac-dialog--warning .ac-dialog__icon { color: var(--c-warning, #f59e0b); }
.ac-dialog--danger .ac-dialog__icon { color: var(--c-danger, #ef4444); }

.ac-dialog__title {
  font-size: 16px;
  font-weight: 600;
  color: var(--c-text, #1e293b);
}

.ac-dialog__body {
  font-size: var(--text-sm, 14px);
  color: var(--c-text-secondary, #64748b);
  line-height: 1.6;
  margin-bottom: 20px;
}

.ac-dialog__footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.btn-warning {
  background: var(--c-warning, #f59e0b);
  color: #fff;
  border: none;
}
@media (hover: hover) {
  .btn-warning:hover {
    background: #d97706;
  }
}

/* Transition */
.ac-enter-active {
  transition: opacity 0.2s var(--ease, ease);
}
.ac-leave-active {
  transition: opacity 0.16s var(--ease, ease);
}
.ac-enter-from,
.ac-leave-to {
  opacity: 0;
}
</style>
