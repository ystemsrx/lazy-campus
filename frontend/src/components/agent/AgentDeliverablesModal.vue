<script setup lang="ts">
import { computed } from "vue";

import type { AgentDeliverable } from "../../types/api";
import { formatFull } from "../../utils/time";
import { getFileIconComponent } from "../../composables/chat/attachmentUtils";
import { formatFileSize } from "./agentViewUtils";

const props = defineProps<{
  show: boolean;
  deliverables: AgentDeliverable[];
  selectedNames: Set<string>;
  deletingSelected: boolean;
  zippingAll: boolean;
}>();

const emit = defineEmits<{
  (e: "update:show", value: boolean): void;
  (e: "delete-selected"): void;
  (e: "download-zip"): void;
  (e: "toggle-select", name: string): void;
}>();

const deliverableCount = computed(() => props.deliverables.length);

function closeModal() {
  emit("update:show", false);
}

function isSelected(name: string): boolean {
  return props.selectedNames.has(name);
}

function getAgentFileIcon(name: string, mime = "") {
  return getFileIconComponent(mime, name);
}
</script>

<template>
  <Teleport to="body">
    <Transition name="modal-fade">
      <div v-if="show" class="modal-overlay" @click.self="closeModal">
        <div class="modal-panel">
          <div class="modal-header">
            <h3>交付文件</h3>
            <div class="modal-select-stats">
              <span class="modal-count modal-count--select">
                <span class="modal-count-num modal-count-num--left">{{
                  selectedNames.size
                }}</span>
                <span class="modal-count-slash">/</span>
                <span class="modal-count-num modal-count-num--right">{{
                  deliverableCount
                }}</span>
              </span>
            </div>
            <div class="modal-header-actions">
              <button
                v-if="deliverableCount > 0"
                class="modal-action-btn modal-action-btn--danger"
                :disabled="selectedNames.size === 0 || deletingSelected"
                @click="emit('delete-selected')"
              >
                <i
                  :class="
                    deletingSelected
                      ? 'fa-solid fa-spinner fa-spin'
                      : 'fa-solid fa-trash'
                  "
                ></i>
                删除
              </button>
              <button class="modal-close-btn" @click="closeModal">
                <i class="fa-solid fa-xmark"></i>
              </button>
            </div>
          </div>

          <div class="modal-body">
            <div v-if="!deliverableCount" class="modal-empty">
              <i class="fa-solid fa-folder-open modal-empty-icon"></i>
              <p>暂无交付文件</p>
            </div>

            <div v-else class="deliverable-list">
              <div
                v-for="item in deliverables"
                :key="item.name"
                class="deliverable-item"
                :class="{
                  'deliverable-item--selected': isSelected(item.name),
                }"
                @click="emit('toggle-select', item.name)"
              >
                <div class="deliverable-check">
                  <i
                    :class="
                      isSelected(item.name)
                        ? 'fa-solid fa-square-check'
                        : 'fa-regular fa-square'
                    "
                  ></i>
                </div>
                <div class="deliverable-icon">
                  <component
                    :is="getAgentFileIcon(item.name)"
                    :size="18"
                    class="agent-file-icon"
                  />
                </div>
                <div class="deliverable-info">
                  <span class="deliverable-name">{{ item.name }}</span>
                  <span class="deliverable-meta"
                    >{{ formatFileSize(item.size) }} ·
                    {{ formatFull(item.updated_at) }}</span
                  >
                </div>
              </div>
            </div>
          </div>

          <div v-if="deliverableCount > 0" class="modal-footer">
            <button
              class="modal-zip-btn"
              :disabled="zippingAll"
              @click="emit('download-zip')"
            >
              <i class="fa-solid fa-file-zipper"></i>
              {{
                zippingAll
                  ? "打包中..."
                  : selectedNames.size > 0
                    ? `打包下载（${selectedNames.size} 个）`
                    : "打包下载全部"
              }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.agent-file-icon {
  flex-shrink: 0;
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
  background: var(--c-surface, #fff);
  border-radius: var(--radius-lg, 16px);
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
  width: min(520px, 92vw);
  max-height: 80vh;
  display: flex;
  flex-direction: column;
}

.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.22s ease;
}

.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}

.modal-fade-enter-active .modal-panel,
.modal-fade-leave-active .modal-panel {
  transition:
    transform 0.22s ease,
    opacity 0.22s ease;
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
  border-bottom: 1px solid var(--c-border, #e2e8f0);
  display: flex;
  align-items: center;
  gap: 12px;
}

.modal-header h3 {
  font-size: var(--text-lg, 18px);
  font-weight: 700;
  flex: 1;
  margin: 0;
}

.modal-count {
  font-size: var(--text-sm, 13px);
  color: var(--c-text-muted, #94a3b8);
  font-weight: 500;
}

.modal-select-stats {
  display: inline-flex;
  align-items: center;
  justify-content: flex-end;
  min-width: 86px;
  flex-shrink: 0;
}

.modal-count--select {
  display: inline-flex;
  align-items: center;
  justify-content: flex-end;
  min-width: 7ch;
  gap: 1px;
  font-variant-numeric: tabular-nums;
}

.modal-count-num {
  display: inline-block;
}

.modal-count-num--left {
  min-width: 3ch;
  text-align: right;
}

.modal-count-num--right {
  min-width: 3ch;
  text-align: left;
}

.modal-count-slash {
  display: inline-block;
  line-height: 1;
}

.modal-header-actions {
  display: flex;
  align-items: center;
  gap: 4px;
}

.modal-close-btn {
  width: 30px;
  height: 30px;
  padding: 0;
  border-radius: 50%;
  aspect-ratio: 1 / 1;
  flex-shrink: 0;
  border: none;
  background: transparent;
  color: var(--c-text-muted, #94a3b8);
  cursor: pointer;
  transition: all 0.15s ease;
}

.modal-close-btn:hover {
  background: var(--c-bg, #f1f5f9);
  color: var(--c-text, #1e293b);
}

.modal-action-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border-radius: 8px;
  border: 1px solid #cbd5e1;
  background: #f8fafc;
  color: #334155;
  font-size: 12px;
  cursor: pointer;
  white-space: nowrap;
  transition:
    background 0.15s,
    border-color 0.15s;
}

.modal-action-btn:hover {
  background: #f1f5f9;
  border-color: #94a3b8;
}

.modal-action-btn--danger {
  background: #fee2e2;
  border-color: #fca5a5;
  color: #dc2626;
}

.modal-action-btn--danger:hover {
  background: #fecaca;
  border-color: #f87171;
  color: #b91c1c;
}

.modal-action-btn--danger:disabled {
  opacity: 0.45;
  cursor: not-allowed;
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
  color: var(--c-text-muted, #94a3b8);
  gap: 8px;
}

.modal-empty-icon {
  font-size: 32px;
  opacity: 0.15;
}

.modal-empty p {
  margin: 0;
  font-size: 13px;
}

.deliverable-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.deliverable-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid var(--c-border, #e2e8f0);
  cursor: pointer;
  transition:
    border-color 0.15s ease,
    background 0.15s ease;
  user-select: none;
}

@media (hover: hover) {
  .deliverable-item:hover {
    border-color: var(--c-accent, #2563eb);
    background: #fafbff;
  }
}

@media (hover: none) {
  .deliverable-item:active {
    border-color: var(--c-accent, #2563eb);
    background: #fafbff;
  }
}

.deliverable-item--selected {
  background: #eff6ff;
  border-color: #93c5fd;
}

.deliverable-check {
  color: #2563eb;
  font-size: 16px;
  flex-shrink: 0;
}

.deliverable-icon {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  background: var(--c-bg, #f1f5f9);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--c-text-muted, #94a3b8);
  font-size: 16px;
  flex-shrink: 0;
}

.deliverable-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.deliverable-name {
  font-size: var(--text-sm, 13px);
  font-weight: 500;
  color: var(--c-text, #1e293b);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.deliverable-meta {
  font-size: var(--text-xs, 11px);
  color: var(--c-text-muted, #94a3b8);
}

.modal-footer {
  padding: 12px 20px;
  border-top: 1px solid var(--c-border, #e2e8f0);
}

.modal-zip-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  width: 100%;
  padding: 8px 12px;
  border-radius: 10px;
  border: 1px solid #cbd5e1;
  background: #f8fafc;
  color: #334155;
  font-size: 13px;
  cursor: pointer;
  transition:
    background 0.15s,
    border-color 0.15s;
}

.modal-zip-btn:hover:not(:disabled) {
  background: #f1f5f9;
  border-color: #94a3b8;
}

.modal-zip-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
