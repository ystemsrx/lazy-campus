<script setup lang="ts">
defineProps<{
  toast: { text: string; type: 'success' | 'error' | 'info' } | null
}>()

const emit = defineEmits<{
  (e: 'dismiss'): void
}>()
</script>

<template>
  <Transition name="toast">
    <div v-if="toast" class="hv-toast" :class="'hv-toast--' + toast.type" @click="emit('dismiss')">
      {{ toast.text }}
    </div>
  </Transition>
</template>

<style scoped>
.hv-toast {
  position: fixed;
  top: 20px;
  right: 24px;
  z-index: 200;
  padding: 12px 22px;
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-weight: 500;
  box-shadow: var(--shadow-lg);
  cursor: pointer;
  max-width: 420px;
}

.hv-toast--info {
  background: var(--c-primary);
  color: var(--c-text-inverse);
}

.hv-toast--success {
  background: var(--c-success);
  color: var(--c-text-inverse);
}

.hv-toast--error {
  background: var(--c-danger);
  color: var(--c-text-inverse);
}

.toast-enter-active {
  transition: all var(--dur-normal) var(--ease);
}

.toast-leave-active {
  transition: all var(--dur-fast) var(--ease);
}

.toast-enter-from {
  opacity: 0;
  transform: translateX(40px);
}

.toast-leave-to {
  opacity: 0;
  transform: translateY(-12px);
}
</style>
