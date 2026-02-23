<script setup lang="ts">
const props = withDefaults(defineProps<{
  modelValue: boolean
  title: string
  width?: string
  bodyClass?: string
  closeOnOverlay?: boolean
}>(), {
  width: 'min(640px, 92vw)',
  bodyClass: '',
  closeOnOverlay: true,
})

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'close'): void
}>()

function close() {
  emit('update:modelValue', false)
  emit('close')
}

function onOverlayClick() {
  if (!props.closeOnOverlay) return
  close()
}
</script>

<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="modelValue" class="hv-modal-overlay" @click.self="onOverlayClick">
        <div class="hv-modal" :style="{ width }">
          <div class="hv-modal__header">
            <slot name="header">
              <h3>{{ title }}</h3>
            </slot>
            <button class="hv-modal__close-btn" @click="close"><i class="fa-solid fa-xmark"></i></button>
          </div>
          <div class="hv-modal__body" :class="bodyClass">
            <slot></slot>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.hv-modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 100;
  background: rgba(15, 23, 42, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
}

.hv-modal {
  background: var(--c-surface);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-xl);
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.hv-modal__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  border-bottom: 1px solid var(--c-border);
  flex-shrink: 0;
}

.hv-modal__header h3 {
  margin: 0;
}

.hv-modal__close-btn {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: none;
  background: var(--c-bg-subtle, #f1f5f9);
  color: var(--c-text-muted);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  flex-shrink: 0;
  transition: background 0.15s, color 0.15s;
}

@media (hover: hover) {
  .hv-modal__close-btn:hover {
    background: var(--c-border);
    color: var(--c-text);
  }
}

.hv-modal__body {
  padding: 20px 24px 24px;
  overflow-y: auto;
}

/* ── Backdrop ── */
.modal-enter-active {
  transition: opacity 300ms cubic-bezier(0.16, 1, 0.3, 1);
}

.modal-leave-active {
  transition: opacity 220ms cubic-bezier(0.4, 0, 1, 1);
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

/* ── Card: independent spring enter ── */
.modal-enter-active .hv-modal {
  transition:
    opacity 260ms cubic-bezier(0.16, 1, 0.3, 1),
    transform 400ms cubic-bezier(0.16, 1, 0.3, 1);
  will-change: transform, opacity;
}

.modal-enter-from .hv-modal {
  opacity: 0;
  transform: scale(0.88) translateY(32px);
}

/* ── Card: snappy ease-in exit ── */
.modal-leave-active .hv-modal {
  transition:
    opacity 200ms cubic-bezier(0.4, 0, 1, 1),
    transform 200ms cubic-bezier(0.4, 0, 1, 1);
  will-change: transform, opacity;
}

.modal-leave-to .hv-modal {
  opacity: 0;
  transform: scale(0.94) translateY(12px);
}
</style>
