<script setup lang="ts">
import { Download, Paperclip, Trash2, X } from 'lucide-vue-next'

import type { AttachmentCount, ChatAttachment } from '../../types/chat'
import { formatFileSize, getFileIconComponent, isImageMime } from '../../composables/chat/attachmentUtils'

defineProps<{
  modelValue: boolean
  attachments: ChatAttachment[]
  attachmentCount: AttachmentCount
  myId: number
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'delete', attachment: ChatAttachment): void
}>()
</script>

<template>
  <Teleport to="body">
    <Transition name="modal-fade">
      <div v-if="modelValue" class="modal-overlay" @click.self="emit('update:modelValue', false)">
        <div class="modal-panel">
          <div class="modal-header">
            <h3>附件管理</h3>
            <span class="modal-count">{{ attachmentCount.count }} / {{ attachmentCount.limit }}</span>
            <button class="icon-btn" @click="emit('update:modelValue', false)">
              <X :size="20" />
            </button>
          </div>

          <div class="modal-body">
            <div v-if="attachments.length === 0" class="modal-empty">
              <Paperclip :size="32" class="empty-icon" />
              <p>暂无附件</p>
            </div>

            <div v-else class="att-list">
              <div v-for="att in attachments" :key="att.id" class="att-item">
                <div class="att-item-preview">
                  <img v-if="isImageMime(att.mime_type)" :src="att.file_url" class="att-list-thumb" />
                  <div v-else class="att-list-icon">
                    <component :is="getFileIconComponent(att.mime_type, att.file_name)" :size="28" />
                  </div>
                </div>

                <div class="att-item-info">
                  <span class="att-item-name">{{ att.file_name }}</span>
                  <span class="att-item-size">{{ formatFileSize(att.file_size) }}</span>
                </div>

                <div class="att-item-actions">
                  <a :href="att.file_url" target="_blank" class="icon-btn">
                    <Download :size="16" />
                  </a>
                  <button v-if="att.uploader_id === myId" class="icon-btn danger" @click="emit('delete', att)">
                    <Trash2 :size="16" />
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
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

.modal-count {
  font-size: var(--text-sm);
  color: var(--c-text-muted);
  font-weight: 500;
}

.modal-body {
  padding: 16px 20px;
  overflow-y: auto;
  flex: 1;
}

.modal-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 32px;
  color: var(--c-text-muted);
  gap: 8px;
}

.empty-icon {
  opacity: 0.15;
}

.att-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.att-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--c-border);
  transition: border-color var(--dur-fast) var(--ease);
}

.att-item:hover {
  border-color: var(--c-accent);
}

.att-item-preview {
  width: 48px;
  height: 48px;
  flex-shrink: 0;
  border-radius: 8px;
  overflow: hidden;
}

.att-list-thumb {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.att-list-icon {
  width: 100%;
  height: 100%;
  background: var(--c-bg);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--c-text-muted);
}

.att-item-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.att-item-name {
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--c-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.att-item-size {
  font-size: var(--text-xs);
  color: var(--c-text-muted);
}

.att-item-actions {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}

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

.icon-btn.danger:hover {
  background: var(--c-danger-light);
  color: var(--c-danger);
}
</style>
