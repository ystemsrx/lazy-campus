<script setup lang="ts">
import { Ban, CheckCircle2, ClipboardList, Clock } from 'lucide-vue-next'

defineProps<{
  activeRole: 'assignee' | 'publisher'
  modelValue: 'pending' | 'progress' | 'completed' | 'canceled'
  publisherPending: number
  canceledCount: number
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: 'pending' | 'progress' | 'completed' | 'canceled'): void
}>()
</script>

<template>
  <div class="tm-tabs tm-anim-2">
    <button
      v-if="activeRole === 'publisher'"
      class="tm-tab--pending-wrap"
      :class="{ 'tm-tab--active': modelValue === 'pending' }"
      @click="emit('update:modelValue', 'pending')"
    >
      <div class="tm-tab__icon"><ClipboardList :size="16" /></div>
      待接取
      <span v-if="publisherPending" class="tm-tab-badge">{{ publisherPending > 99 ? '99+' : publisherPending }}</span>
    </button>

    <button :class="{ 'tm-tab--active': modelValue === 'progress' }" @click="emit('update:modelValue', 'progress')">
      <div class="tm-tab__icon"><Clock :size="16" /></div>
      进行中
    </button>

    <button :class="{ 'tm-tab--active': modelValue === 'completed' }" @click="emit('update:modelValue', 'completed')">
      <div class="tm-tab__icon"><CheckCircle2 :size="16" /></div>
      已完成
    </button>

    <button
      v-if="activeRole === 'publisher'"
      class="tm-tab--canceled-wrap"
      :class="{ 'tm-tab--active': modelValue === 'canceled' }"
      @click="emit('update:modelValue', 'canceled')"
    >
      <div class="tm-tab__icon"><Ban :size="16" /></div>
      已取消
      <span v-if="canceledCount" class="tm-tab-badge tm-tab-badge--muted">{{ canceledCount > 99 ? '99+' : canceledCount }}</span>
    </button>
  </div>
</template>

<style scoped>
@keyframes tm-rise {
  from {
    opacity: 0;
    transform: translateY(20px);
  }

  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.tm-anim-2 {
  animation: tm-rise 0.5s ease-out 0.12s both;
}

.tm-tabs {
  display: flex;
  gap: 10px;
  margin-bottom: 28px;
  max-width: 560px;
}

.tm-tabs button {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 11px 18px;
  border-radius: 12px;
  border: none;
  font-weight: 700;
  font-size: 13px;
  font-family: var(--font-sans);
  cursor: pointer;
  transition: all 0.25s var(--ease);
  background: #ffffff;
  color: var(--c-text-muted);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  position: relative;
  overflow: visible;
}

.tm-tab-badge {
  position: absolute;
  top: -8px;
  right: -8px;
  min-width: 20px;
  height: 20px;
  padding: 0 5px;
  border-radius: 10px;
  background: #ef4444;
  color: #ffffff;
  font-size: 11px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
  border: 2px solid #f8fafc;
  pointer-events: none;
  z-index: 1;
}

.tm-tab-badge--muted {
  background: #94a3b8;
}

.tm-tabs button:hover {
  background: var(--c-border-light);
  color: var(--c-text);
}

.tm-tab__icon {
  padding: 4px;
  border-radius: 7px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--c-accent-light);
  color: var(--c-accent);
}

.tm-tab--active {
  background: var(--c-accent) !important;
  color: #ffffff !important;
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.14) !important;
}

.tm-tab--active .tm-tab__icon {
  background: rgba(255, 255, 255, 0.2) !important;
  color: #ffffff !important;
}

@media (max-width: 900px) {
  .tm-tabs {
    gap: 8px;
  }

  .tm-tabs button {
    padding: 10px 12px;
    font-size: 13px;
    gap: 6px;
    border-radius: 12px;
  }

  .tm-tab__icon {
    padding: 4px;
    border-radius: 6px;
  }
}
</style>
