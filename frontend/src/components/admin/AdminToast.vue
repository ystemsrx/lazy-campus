<script setup lang="ts">
import type { AdminToast } from '../../composables/admin/useAdminToast'

defineProps<{
  toast: AdminToast | null
}>()

defineEmits<{
  close: []
}>()
</script>

<template>
  <Transition name="toast">
    <div
      v-if="toast"
      class="av-toast"
      :class="'av-toast--' + toast.type"
      @click="$emit('close')"
    >
      {{ toast.text }}
    </div>
  </Transition>
</template>

<style scoped>
.av-toast {
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

.av-toast--info {
  background: var(--c-primary);
  color: var(--c-text-inverse);
}

.av-toast--success {
  background: var(--c-success);
  color: var(--c-text-inverse);
}

.av-toast--error {
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
