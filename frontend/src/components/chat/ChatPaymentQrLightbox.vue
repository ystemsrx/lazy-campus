<script setup lang="ts">
defineProps<{
  modelValue: boolean
  qrUrl: string | null
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
}>()
</script>

<template>
  <Teleport to="body">
    <Transition name="qr-fade">
      <div
        v-if="modelValue && qrUrl"
        class="qr-lightbox-overlay"
        @click="emit('update:modelValue', false)"
      >
        <img :src="qrUrl" class="qr-lightbox-img" alt="收款码" />
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.qr-lightbox-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(6px);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.qr-lightbox-img {
  max-width: min(90vw, 420px);
  max-height: 85vh;
  border-radius: var(--radius-lg);
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.4);
  pointer-events: none;
}

.qr-fade-enter-active,
.qr-fade-leave-active {
  transition: opacity 0.22s ease;
}

.qr-fade-enter-from,
.qr-fade-leave-to {
  opacity: 0;
}
</style>
