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
            <button class="btn btn-ghost btn-sm" @click="close"><i class="fa-solid fa-xmark"></i></button>
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

.hv-modal__body {
  padding: 20px 24px 24px;
  overflow-y: auto;
}

.modal-enter-active {
  transition: all var(--dur-normal) var(--ease);
}

.modal-leave-active {
  transition: all var(--dur-fast) var(--ease);
}

.modal-enter-from {
  opacity: 0;
}

.modal-leave-to {
  opacity: 0;
}

.modal-enter-from .hv-modal {
  transform: scale(0.95) translateY(10px);
}

.modal-leave-to .hv-modal {
  transform: scale(0.97) translateY(5px);
}
</style>
