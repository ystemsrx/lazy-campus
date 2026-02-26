<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  show: boolean
  isEditing: boolean
  name: string
  description: string
  aiAgentEnabled: boolean
  submitting: boolean
}>()

const emit = defineEmits<{
  close: []
  confirm: []
  'update:name': [value: string]
  'update:description': [value: string]
  'update:ai-agent-enabled': [value: boolean]
}>()

const descLength = computed(() => props.description.length)

function updateName(event: Event) {
  const target = event.target as HTMLInputElement
  emit('update:name', target.value)
}

function updateDescription(event: Event) {
  const target = event.target as HTMLTextAreaElement
  emit('update:description', target.value)
}

function toggleAiAgent(event: Event) {
  const target = event.target as HTMLInputElement
  emit('update:ai-agent-enabled', target.checked)
}
</script>

<template>
  <Teleport to="body">
    <Transition name="modal">
    <div v-if="show" class="av-modal-overlay" @click.self="$emit('close')">
      <div class="av-modal">
        <div class="av-modal__header">
          <h3>{{ isEditing ? '编辑类别' : '添加类别' }}</h3>
          <button class="av-modal__close" @click="$emit('close')">
            <i class="fa-solid fa-xmark"></i>
          </button>
        </div>
        <form class="av-modal__body" @submit.prevent="$emit('confirm')">
          <div class="av-modal__field">
            <label class="av-modal__label">
              类别名称
              <span class="av-modal__required">*</span>
            </label>
            <input
              :value="name"
              class="av-modal__input"
              placeholder="例如：跑腿代购"
              @input="updateName"
            />
          </div>
          <div class="av-modal__field">
            <label class="av-modal__label av-modal__label--flex">
              <span>类别描述（选填）</span>
              <span class="av-modal__counter">{{ descLength }}/100</span>
            </label>
            <textarea
              :value="description"
              class="av-modal__input av-modal__textarea"
              rows="3"
              maxlength="100"
              placeholder="简短描述该类别包含哪些任务，帮助用户准确选择..."
              @input="updateDescription"
            />
            <p class="av-modal__field-hint">此描述将在用户发布任务选择类别时作为提示信息显示。</p>
          </div>
          <div class="av-modal__field">
            <label class="av-modal__switch">
              <input :checked="aiAgentEnabled" type="checkbox" @change="toggleAiAgent" />
              <span>允许该类别使用 AI 代理</span>
            </label>
            <p class="av-modal__field-hint">开启后，用户在该类别下可选择“AI 代理”模式。</p>
          </div>
        </form>
        <div class="av-modal__footer">
          <button class="btn btn-outline btn-sm" @click="$emit('close')">取消</button>
          <button class="btn btn-primary btn-sm" :disabled="submitting" @click="$emit('confirm')">
            {{ submitting ? '保存中…' : isEditing ? '保存修改' : '确认创建' }}
          </button>
        </div>
      </div>
    </div>
  </Transition>
  </Teleport>
</template>

<style>
.av-modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 100;
  background: rgba(15, 23, 42, 0.35);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.av-modal {
  background: var(--c-surface, #fff);
  border-radius: 16px;
  box-shadow: 0 25px 60px rgba(0, 0, 0, 0.12);
  width: min(440px, 100%);
  overflow: hidden;
}

.av-modal__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid rgba(241, 245, 249, 0.8);
}

.av-modal__header h3 {
  margin: 0;
  font-size: 17px;
  font-weight: 700;
}

.av-modal__close {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: #94a3b8;
  font-size: 16px;
  cursor: pointer;
  transition: color 200ms ease, background 200ms ease;
}

.av-modal__close:hover {
  color: #64748b;
  background: rgba(100, 116, 139, 0.08);
}

.av-modal__body {
  padding: 24px;
}

.av-modal__field {
  margin-bottom: 20px;
}

.av-modal__field:last-child {
  margin-bottom: 0;
}

.av-modal__label {
  display: block;
  font-size: 14px;
  font-weight: 500;
  color: #475569;
  margin-bottom: 6px;
}

.av-modal__label--flex {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.av-modal__required {
  color: #ef4444;
  margin-left: 2px;
}

.av-modal__counter {
  font-size: 12px;
  color: #94a3b8;
  font-weight: 400;
}

.av-modal__input {
  display: block;
  width: 100%;
  padding: 10px 14px;
  border: 1px solid rgba(226, 232, 240, 0.8);
  border-radius: 12px;
  font-size: 14px;
  color: var(--c-text);
  background: #fff;
  outline: none;
  transition: border-color 200ms ease, box-shadow 200ms ease;
}

.av-modal__input::placeholder {
  color: #94a3b8;
}

.av-modal__input:focus {
  border-color: var(--c-accent, #3b82f6);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.12);
}

.av-modal__textarea {
  resize: none;
  line-height: 1.5;
}

.av-modal__field-hint {
  margin: 8px 0 0;
  font-size: 12px;
  color: #94a3b8;
}

.av-modal__switch {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: #334155;
}

.av-modal__switch input {
  width: 16px;
  height: 16px;
}

.av-modal__footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 16px 24px;
  border-top: 1px solid rgba(241, 245, 249, 0.8);
}

/* ======== 过渡动画 ======== */

.modal-enter-active {
  transition: opacity 300ms ease-out;
}

.modal-enter-active .av-modal {
  animation: modal-slide-in 300ms cubic-bezier(0.2, 0.8, 0.2, 1) both;
}

.modal-leave-active {
  transition: opacity 200ms ease-in;
}

.modal-leave-active .av-modal {
  animation: modal-slide-out 200ms ease-in both;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

@keyframes modal-slide-in {
  from {
    opacity: 0;
    transform: translateY(24px) scale(0.95);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

@keyframes modal-slide-out {
  from {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
  to {
    opacity: 0;
    transform: translateY(16px) scale(0.95);
  }
}
</style>
