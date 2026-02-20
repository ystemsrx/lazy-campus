<script setup lang="ts">
const props = withDefaults(defineProps<{
  modelValue: boolean
  title: string
  width?: string
  bodyClass?: string
  overlayClass?: string
  drawerClass?: string
  closeOnOverlay?: boolean
}>(), {
  width: 'min(540px, 92vw)',
  bodyClass: '',
  overlayClass: '',
  drawerClass: '',
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
    <Transition name="drawer">
      <div v-if="modelValue" class="hv-drawer-overlay" :class="overlayClass" @click.self="onOverlayClick">
        <div class="hv-drawer" :class="drawerClass" :style="{ width }">
          <slot name="prepend"></slot>

          <slot name="header" :close="close">
            <div class="hv-drawer__header">
              <h3>{{ title }}</h3>
              <button class="btn btn-ghost btn-sm" @click="close"><i class="fa-solid fa-xmark"></i></button>
            </div>
          </slot>

          <div class="hv-drawer__body" :class="bodyClass">
            <slot></slot>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.hv-drawer-overlay {
  position: fixed;
  inset: 0;
  z-index: 100;
  background: rgba(15, 23, 42, 0.35);
  display: flex;
  justify-content: flex-end;
}

.hv-drawer {
  height: 100vh;
  background: var(--c-surface);
  display: flex;
  flex-direction: column;
  box-shadow: -4px 0 24px rgba(0, 0, 0, 0.12);
}

.hv-drawer__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  border-bottom: 1px solid var(--c-border);
  flex-shrink: 0;
}

.hv-drawer__header h3 {
  margin: 0;
}

.hv-drawer__body {
  flex: 1;
  overflow-y: auto;
  padding: 0;
}

.drawer-enter-active {
  transition: all var(--dur-slow) var(--ease);
}

.drawer-leave-active {
  transition: all var(--dur-normal) var(--ease);
}

.drawer-enter-active .hv-drawer {
  transition: transform var(--dur-slow) var(--ease);
}

.drawer-leave-active .hv-drawer {
  transition: transform var(--dur-normal) var(--ease);
}

.drawer-enter-from,
.drawer-leave-to {
  opacity: 0;
}

.drawer-enter-from .hv-drawer,
.drawer-leave-to .hv-drawer {
  transform: translateX(100%);
}
</style>
