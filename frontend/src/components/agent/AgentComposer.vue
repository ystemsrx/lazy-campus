<script setup lang="ts">
import { nextTick, ref, watch } from "vue";

import { getFileIconComponent } from "../../composables/chat/attachmentUtils";
import { formatFileSize } from "./agentViewUtils";

const props = defineProps<{
  modelValue: string;
  pendingFiles: File[];
  sendDisabled: boolean;
  useDisabledComposeStyle: boolean;
  composePlaceholder: string;
  isCancelable: boolean;
  canceling: boolean;
  canSendNow: boolean;
  sending: boolean;
  sessionStatus: string | null;
  taskStatus: string | null;
  queueAheadUsers: number;
  queueText: string;
  needsQueue: boolean;
  interactionLeft: number;
  interactionCount: number;
  maxInteractions: number;
  maxFileCount: number;
  maxFileSizeMb: number;
}>();

const emit = defineEmits<{
  (e: "update:modelValue", value: string): void;
  (e: "pick-files", files: File[]): void;
  (e: "remove-file", index: number): void;
  (e: "send"): void;
  (e: "cancel"): void;
}>();

const textareaRef = ref<HTMLTextAreaElement | null>(null);

function getAgentFileIcon(name: string, mime = "") {
  return getFileIconComponent(mime, name);
}

function autoResizeTextarea() {
  nextTick(() => {
    const el = textareaRef.value;
    if (!el) return;
    el.style.height = "0px";
    const height = Math.min(Math.max(el.scrollHeight, 38), 160);
    el.style.height = `${height}px`;
    el.style.overflowY = el.scrollHeight > 160 ? "auto" : "hidden";
  });
}

function handleInput(event: Event) {
  const target = event.target as HTMLTextAreaElement;
  emit("update:modelValue", target.value);
}

function handlePickFiles(event: Event) {
  const input = event.target as HTMLInputElement;
  const files = Array.from(input.files || []);
  if (files.length > 0) emit("pick-files", files);
  input.value = "";
}

watch(
  () => props.modelValue,
  () => {
    autoResizeTextarea();
  },
  { immediate: true },
);
</script>

<template>
  <div class="agent-input">
    <div class="agent-input-inner">
      <div v-if="pendingFiles.length" class="agent-pending">
        <div
          v-for="(file, index) in pendingFiles"
          :key="`${file.name}-${index}`"
          class="agent-pending__item"
        >
          <component
            :is="getAgentFileIcon(file.name, file.type)"
            :size="14"
            class="agent-file-icon"
          />
          <span>{{ file.name }}</span>
          <small>{{ formatFileSize(file.size) }}</small>
          <button type="button" @click="emit('remove-file', index)">
            <i class="fa-solid fa-xmark"></i>
          </button>
        </div>
      </div>

      <div
        class="agent-compose"
        :class="{ 'agent-compose--disabled': useDisabledComposeStyle }"
      >
        <label class="agent-upload-btn" :class="{ disabled: sendDisabled }">
          <i class="fa-solid fa-paperclip"></i>
          <input
            type="file"
            multiple
            :disabled="sendDisabled"
            @change="handlePickFiles"
          />
        </label>

        <textarea
          ref="textareaRef"
          :value="modelValue"
          class="agent-textarea"
          :disabled="sendDisabled"
          :placeholder="composePlaceholder"
          @input="handleInput"
        />

        <button
          v-if="isCancelable"
          class="agent-cancel-btn"
          :disabled="canceling"
          :title="
            canceling
              ? sessionStatus === 'queued'
                ? '终止排队中...'
                : '中断中...'
              : sessionStatus === 'queued'
                ? '终止排队'
                : '中断'
          "
          @click="emit('cancel')"
        >
          <i
            :class="
              canceling
                ? 'fa-solid fa-spinner fa-spin'
                : 'fa-solid fa-stop'
            "
          ></i>
        </button>
        <button
          v-else
          class="agent-send-btn"
          :class="{ active: canSendNow }"
          :disabled="!canSendNow"
          :title="sending ? '发送中...' : '发送'"
          @click="emit('send')"
        >
          <i
            :class="
              sending
                ? 'fa-solid fa-spinner fa-spin'
                : 'fa-solid fa-arrow-up'
            "
          ></i>
        </button>
      </div>

      <div class="agent-hint-row">
        <p class="agent-hint">
          <span v-if="taskStatus === 'completed'">任务已完成，会话已关闭。</span>
          <span v-else-if="sessionStatus === 'queued'">{{
            queueAheadUsers > 0 ? `排队中，${queueText}。` : "排队中，请稍候..."
          }}</span>
          <span v-else-if="sessionStatus === 'running'"
            >代理正在执行中，可等待输出。</span
          >
          <span v-else-if="needsQueue">{{
            queueAheadUsers > 0
              ? `当前需排队，${queueText}。`
              : "当前需排队，请稍后发送。"
          }}</span>
          <span v-else-if="interactionLeft <= 0">交互次数已用尽。</span>
          <span v-else
            >单次最多 {{ maxFileCount }} 个文件，单个不超过
            {{ maxFileSizeMb }} MB。</span
          >
        </p>
        <div class="agent-hint-badges">
          <span class="badge badge-blue"
            >已用 {{ interactionCount }}/{{ maxInteractions }}</span
          >
          <span
            class="badge"
            :class="interactionLeft > 0 ? 'badge-green' : 'badge-red'"
            >剩余 {{ interactionLeft }}</span
          >
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.agent-file-icon {
  flex-shrink: 0;
}

.agent-input {
  background: #fff;
  border-top: 1px solid var(--c-border, #e2e8f0);
  padding: 12px 24px;
  flex-shrink: 0;
}

.agent-input-inner {
  width: min(60%, 980px);
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 0;
}

.agent-pending {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 8px;
}

.agent-pending__item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 4px 8px;
  font-size: 12px;
  color: #334155;
  background: #f8fafc;
}

.agent-pending__item small {
  color: #64748b;
}

.agent-pending__item button {
  border: none;
  background: transparent;
  color: #64748b;
  padding: 0;
  cursor: pointer;
}

.agent-compose {
  display: flex;
  align-items: flex-end;
  background: var(--c-bg, #f1f5f9);
  border: 1.5px solid var(--c-border, #e2e8f0);
  border-radius: 24px;
  padding: 4px;
  transition:
    border-color 0.15s ease,
    background 0.15s ease;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
}

.agent-compose:focus-within {
  background: #fff;
  border-color: var(--c-accent, #2563eb);
}

.agent-compose--disabled {
  background: #fff5f5;
  border-color: #fca5a5;
}

.agent-compose--disabled:focus-within {
  background: #fff5f5;
  border-color: #fca5a5;
}

.agent-compose--disabled .agent-textarea {
  color: #ef4444;
}

.agent-compose--disabled .agent-textarea::placeholder {
  color: #ef4444;
  opacity: 0.8;
}

.agent-compose--disabled .agent-upload-btn,
.agent-compose--disabled .agent-send-btn {
  opacity: 0.4;
}

.agent-upload-btn {
  width: 38px;
  height: 38px;
  flex-shrink: 0;
  border-radius: 50%;
  border: none;
  background: transparent;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--c-text-secondary, #64748b);
  cursor: pointer;
  transition:
    background 0.15s ease,
    color 0.15s ease;
  font-size: 15px;
}

.agent-upload-btn:hover {
  background: var(--c-border, #e2e8f0);
}

.agent-upload-btn.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.agent-upload-btn input {
  display: none;
}

.agent-textarea {
  flex: 1;
  border: none;
  background: transparent;
  border-radius: 0;
  height: 38px;
  max-height: 160px;
  resize: none;
  overflow-y: hidden;
  font-size: 14px;
  padding: 9px 8px;
  font-family: inherit;
  outline: none;
  color: var(--c-text, #1e293b);
  line-height: 20px;
}

.agent-textarea::placeholder {
  color: var(--c-text-muted, #94a3b8);
}

.agent-send-btn {
  width: 38px;
  height: 38px;
  flex-shrink: 0;
  border-radius: 50%;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  background: var(--c-border, #e2e8f0);
  color: var(--c-text-muted, #94a3b8);
  cursor: not-allowed;
  transition:
    background 0.15s ease,
    color 0.15s ease,
    transform 0.1s ease;
  min-width: unset;
}

.agent-send-btn.active {
  background: var(--c-accent, #2563eb);
  color: #fff;
  cursor: pointer;
}

.agent-send-btn.active:hover {
  background: #1d4ed8;
  transform: scale(1.05);
}

.agent-send-btn.active:active {
  transform: scale(0.95);
}

.agent-cancel-btn {
  width: 38px;
  height: 38px;
  flex-shrink: 0;
  border-radius: 50%;
  border: none;
  background: #fee2e2;
  color: #dc2626;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 15px;
  cursor: pointer;
  transition: background 0.15s ease;
  min-width: unset;
}

.agent-cancel-btn:hover:not(:disabled) {
  background: #fecaca;
}

.agent-cancel-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.agent-hint-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-top: 6px;
}

.agent-hint {
  margin: 0;
  font-size: 11px;
  color: #64748b;
}

.agent-hint-badges {
  display: flex;
  gap: 6px;
  flex-shrink: 0;
}

.badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  font-weight: 500;
  padding: 2px 8px;
  border-radius: 999px;
}

.badge-blue {
  background: #dbeafe;
  color: #1d4ed8;
}

.badge-green {
  background: #dcfce7;
  color: #16a34a;
}

.badge-red {
  background: #fee2e2;
  color: #dc2626;
}

@media (max-width: 768px) {
  .agent-input {
    padding: 12px 16px;
  }

  .agent-input-inner {
    width: 100%;
  }
}
</style>
