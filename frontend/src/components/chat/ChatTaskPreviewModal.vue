<script setup lang="ts">
import { computed } from 'vue'
import { X } from 'lucide-vue-next'

import type { Task } from '../../types/api'
import { formatFull, isExpired } from '../../utils/time'
import { getTaskIcon } from '../../utils/taskIcons'

const props = defineProps<{
  modelValue: boolean
  taskPreview: Task | null
  statusMap: Record<string, { label: string; cls: string }>
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
}>()

const taskIcon = computed(() => getTaskIcon(props.taskPreview?.icon ?? null))

function closeModal() {
  emit('update:modelValue', false)
}
</script>

<template>
  <Teleport to="body">
    <Transition name="modal-fade">
      <div v-if="modelValue" class="modal-overlay" @click.self="closeModal">
        <div class="modal-panel task-preview-panel">
          <div class="modal-header">
            <div class="task-preview-icon" :style="{ background: taskIcon.bg }">
              <component
                :is="taskIcon.component"
                :size="16"
                :style="{ color: taskIcon.color }"
              />
            </div>
            <h3>{{ taskPreview?.title || '加载中…' }}</h3>
            <button class="icon-btn" @click="closeModal">
              <X :size="20" />
            </button>
          </div>

          <div v-if="!taskPreview" class="modal-body task-preview-loading">
            <div class="spinner"></div>
          </div>

          <div v-else class="modal-body task-preview-body">
            <div class="task-preview-meta">
              <span class="task-preview-price">¥{{ taskPreview.price }}</span>
              <span class="task-preview-status" :class="statusMap[taskPreview.status]?.cls">
                {{ statusMap[taskPreview.status]?.label ?? taskPreview.status }}
              </span>
            </div>

            <div v-if="taskPreview.description" class="task-preview-desc">
              {{ taskPreview.description }}
            </div>

            <div class="task-preview-fields">
              <div v-if="taskPreview.deadline" class="task-preview-field">
                <span class="field-label">截止时间</span>
                <span class="field-value" :class="{ 'field-expired': isExpired(taskPreview.deadline) }">
                  {{ formatFull(taskPreview.deadline) }}{{ isExpired(taskPreview.deadline) ? '（已过期）' : '' }}
                </span>
              </div>

              <div v-if="taskPreview.location" class="task-preview-field">
                <span class="field-label">地点</span>
                <span class="field-value">{{ taskPreview.location }}</span>
              </div>

              <div class="task-preview-field">
                <span class="field-label">发布者</span>
                <span class="field-value">{{ taskPreview.publisher_display_name }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.icon-btn {
  padding: 8px;
  border-radius: 50%;
  background: transparent;
  border: none;
  color: var(--c-text-muted);
  cursor: pointer;
  transition: all var(--dur-fast) var(--ease);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}

.icon-btn:hover {
  background: var(--c-bg);
  color: var(--c-text);
}

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  backdrop-filter: blur(4px);
}

.modal-panel {
  background: var(--c-surface);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xl);
  width: min(480px, 92vw);
  max-height: 80vh;
  display: flex;
  flex-direction: column;
}

.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.22s var(--ease);
}

.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}

.modal-fade-enter-active .modal-panel,
.modal-fade-leave-active .modal-panel {
  transition:
    transform 0.22s var(--ease),
    opacity 0.22s var(--ease);
}

.modal-fade-enter-from .modal-panel {
  transform: scale(0.95) translateY(10px);
  opacity: 0;
}

.modal-fade-leave-to .modal-panel {
  transform: scale(0.96) translateY(6px);
  opacity: 0;
}

.modal-header {
  padding: 16px 20px;
  border-bottom: 1px solid var(--c-border);
  display: flex;
  align-items: center;
  gap: 12px;
}

.modal-header h3 {
  font-size: var(--text-lg);
  font-weight: 700;
  flex: 1;
}

.modal-body {
  padding: 16px 20px;
  overflow-y: auto;
  flex: 1;
}

.status-open {
  color: var(--c-accent);
}

.status-active {
  color: var(--c-warning);
}

.status-done {
  color: var(--c-success);
}

.status-canceled {
  color: var(--c-text-muted);
}

.task-preview-panel {
  width: min(440px, 92vw);
}

.task-preview-icon {
  padding: 6px;
  border-radius: 8px;
  flex-shrink: 0;
  display: flex;
}

.task-preview-loading {
  display: flex;
  justify-content: center;
  padding: 32px;
}

.task-preview-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.task-preview-meta {
  display: flex;
  align-items: center;
  gap: 10px;
}

.task-preview-price {
  font-size: var(--text-xl, 1.25rem);
  font-weight: 700;
  color: var(--c-accent);
}

.task-preview-status {
  font-size: var(--text-sm);
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 99px;
  background: var(--c-bg);
}

.task-preview-desc {
  font-size: var(--text-sm);
  color: var(--c-text-secondary);
  line-height: 1.6;
  white-space: pre-wrap;
}

.task-preview-fields {
  display: flex;
  flex-direction: column;
  gap: 6px;
  border-top: 1px solid var(--c-border);
  padding-top: 10px;
}

.task-preview-field {
  display: flex;
  gap: 8px;
  font-size: var(--text-sm);
}

.field-label {
  color: var(--c-text-muted);
  flex-shrink: 0;
  width: 56px;
}

.field-value {
  color: var(--c-text);
  font-weight: 500;
}

.field-expired {
  color: var(--c-danger);
}
</style>
