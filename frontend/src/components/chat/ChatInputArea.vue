<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import { ArrowUp, Plus, ShieldAlert } from 'lucide-vue-next'

const props = defineProps<{
  modelValue: string
  isBlocked: boolean
  blockReason: string
  isMobile: boolean
  sending: boolean
  uploadingFile: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
  (e: 'send'): void
  (e: 'upload', event: Event): void
}>()

const textareaRef = ref<HTMLTextAreaElement | null>(null)

function autoResize() {
  nextTick(() => {
    const el = textareaRef.value
    if (!el) return

    el.style.height = '0px'
    const height = Math.min(Math.max(el.scrollHeight, 38), 120)
    el.style.height = `${height}px`
    el.style.overflowY = el.scrollHeight > 120 ? 'auto' : 'hidden'
  })
}

watch(
  () => props.modelValue,
  () => {
    autoResize()
  },
  { immediate: true },
)

function onKeyDown(event: KeyboardEvent) {
  if (props.isMobile) return

  if (event.key === 'Enter' && !event.shiftKey && !event.ctrlKey && !event.metaKey) {
    event.preventDefault()
    emit('send')
  }
}

function onInput(event: Event) {
  const target = event.target as HTMLTextAreaElement | null
  emit('update:modelValue', target?.value ?? '')
}
</script>

<template>
  <div class="chat-input-area">
    <div v-if="isBlocked" class="blocked-notice">
      <ShieldAlert :size="18" />
      <span>{{ blockReason }}，无法发送消息</span>
    </div>

    <div v-else class="input-wrap">
      <div class="capsule-input">
        <label class="file-upload-btn" :class="{ disabled: uploadingFile }">
          <Plus :size="20" />
          <input type="file" class="file-input-hidden" multiple :disabled="uploadingFile" @change="emit('upload', $event)" />
        </label>

        <textarea
          ref="textareaRef"
          :value="modelValue"
          placeholder="发送消息..."
          class="msg-textarea"
          @input="onInput"
          @keydown="onKeyDown"
        ></textarea>

        <button
          class="send-btn"
          :class="{ active: modelValue.trim() }"
          :disabled="!modelValue.trim() || sending"
          @click="emit('send')"
        >
          <ArrowUp :size="20" />
        </button>
      </div>

      <div class="input-hint">
        {{ isMobile ? '点击发送按钮发送' : 'Enter 发送 · Shift+Enter 换行' }}
      </div>
    </div>
  </div>
</template>

<style scoped>
.chat-input-area {
  background: transparent;
  padding: 0 12px 6px;
  flex-shrink: 0;
  z-index: 10;
}

.blocked-notice {
  background: var(--c-danger-light);
  border: 1px solid var(--c-danger-soft);
  border-radius: var(--radius-full);
  padding: 8px 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: var(--c-danger);
  margin: 4px 0;
}

.blocked-notice span {
  font-size: var(--text-sm);
  font-weight: 500;
}

.input-wrap {
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-width: 800px;
  margin: 0 auto;
}

.capsule-input {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  background: var(--c-bg);
  border: 1.5px solid var(--c-border);
  border-radius: 24px;
  padding: 4px;
  transition: all var(--dur-fast) var(--ease);
  box-shadow: var(--shadow-xs);
}

.capsule-input:focus-within {
  background: var(--c-surface);
  border-color: var(--c-accent);
}

.file-upload-btn {
  width: 38px;
  height: 38px;
  flex-shrink: 0;
  border-radius: 50%;
  background: transparent;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--c-text-secondary);
  cursor: pointer;
  transition:
    background var(--dur-fast) var(--ease),
    color var(--dur-fast) var(--ease);
}

.file-upload-btn:hover {
  background: var(--c-border);
  color: var(--c-text-secondary);
}

.file-upload-btn.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.file-input-hidden {
  display: none;
}

.msg-textarea {
  flex: 1;
  background: transparent;
  border: none;
  outline: none;
  resize: none;
  padding: 9px 8px;
  font-size: 15px;
  color: var(--c-text);
  line-height: 20px;
  height: 38px;
  overflow-y: hidden;
  font-family: inherit;
}

.msg-textarea::placeholder {
  color: var(--c-text-muted);
}

.send-btn {
  width: 38px;
  height: 38px;
  flex-shrink: 0;
  border-radius: 50%;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--dur-fast) var(--ease);
  background: var(--c-border);
  color: var(--c-text-muted);
  cursor: not-allowed;
}

.send-btn.active {
  background: var(--c-accent);
  color: white;
  cursor: pointer;
  box-shadow: var(--shadow-sm);
}

.send-btn.active:hover {
  background: var(--c-accent-hover);
  transform: scale(1.05);
}

.send-btn.active:active {
  transform: scale(0.95);
}

.input-hint {
  font-size: 10px;
  color: var(--c-text-muted);
  text-align: center;
  padding-top: 2px;
}

@media (max-width: 768px) {
  .msg-textarea {
    font-size: 16px !important;
  }
}
</style>
