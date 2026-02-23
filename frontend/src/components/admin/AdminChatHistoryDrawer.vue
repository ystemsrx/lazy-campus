<script setup lang="ts">
import type { DirectChatHistory } from '../../composables/admin/useAdminReports'
import { formatShort } from '../../utils/time'

defineProps<{
  show: boolean
  loading: boolean
  chatHistory: DirectChatHistory | null
}>()

defineEmits<{
  close: []
}>()
</script>

<template>
  <Teleport to="body">
    <Transition name="av-drawer">
      <div v-if="show" class="av-snapshot-overlay" @mousedown.self="$emit('close')">
        <div class="av-snapshot-drawer">
          <div class="av-snapshot-drawer__header">
            <h3>聊天记录</h3>
            <button class="btn btn-ghost btn-sm" @click="$emit('close')">
              <i class="fa-solid fa-xmark"></i>
            </button>
          </div>

          <div v-if="loading" class="av-snapshot-drawer__loading">
            <div class="spinner"></div>
          </div>

          <div v-else-if="chatHistory" class="av-snapshot-drawer__body">
            <div class="av-chat-parties">
              <div class="av-chat-party">
                <i class="fa-solid fa-user av-chat-party__icon av-chat-party__icon--reporter"></i>
                <span>{{ chatHistory.reporter_display_name }}</span>
                <span class="av-chat-party__label">举报者</span>
              </div>
              <i class="fa-solid fa-arrows-left-right av-chat-arrow"></i>
              <div class="av-chat-party av-chat-party--right">
                <i class="fa-solid fa-user av-chat-party__icon av-chat-party__icon--reported"></i>
                <span>{{ chatHistory.reported_user_display_name }}</span>
                <span class="av-chat-party__label">被举报者</span>
              </div>
            </div>

            <div class="av-snap-section">
              <h4 class="av-snap-subtitle">
                <i class="fa-regular fa-comment-dots"></i>
                聊天记录 ({{ chatHistory.messages.length }})
              </h4>
              <div v-if="chatHistory.messages.length" class="av-snap-chat">
                <div
                  v-for="(msg, idx) in chatHistory.messages"
                  :key="idx"
                  class="av-snap-msg"
                  :class="{
                    'av-snap-msg--reporter': msg.sender_display_name === chatHistory.reporter_display_name,
                    'av-snap-msg--reported': msg.sender_display_name !== chatHistory.reporter_display_name,
                  }"
                >
                  <div class="av-snap-msg__head">
                    <span
                      class="av-snap-msg__sender"
                      :class="{
                        'av-snap-msg__sender--reporter': msg.sender_display_name === chatHistory.reporter_display_name,
                        'av-snap-msg__sender--reported': msg.sender_display_name !== chatHistory.reporter_display_name,
                      }"
                    >{{ msg.sender_display_name }}</span>
                    <span class="av-snap-msg__time">{{ formatShort(msg.created_at) }}</span>
                  </div>
                  <div class="av-snap-msg__text">{{ msg.content }}</div>
                </div>
              </div>
              <p v-else class="av-snap-empty">
                <i class="fa-regular fa-comment-slash"></i>
                双方之间暂无聊天记录
              </p>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.av-snapshot-overlay {
  position: fixed;
  inset: 0;
  z-index: 2000;
  display: flex;
  justify-content: flex-end;
  background: rgba(0, 0, 0, 0.3);
  backdrop-filter: blur(2px);
}

.av-snapshot-drawer {
  width: 520px;
  max-width: 100vw;
  height: 100vh;
  background: #fff;
  box-shadow: -8px 0 30px rgba(0, 0, 0, 0.12);
  display: flex;
  flex-direction: column;
  animation: av-slide-in 0.25s var(--ease, cubic-bezier(0.16, 1, 0.3, 1));
}

@keyframes av-slide-in {
  from {
    transform: translateX(100%);
  }
}

.av-snapshot-drawer__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 24px;
  border-bottom: 1px solid var(--c-border);
  flex-shrink: 0;
}

.av-snapshot-drawer__header h3 {
  margin: 0;
  font-size: 16px;
}

.av-snapshot-drawer__loading {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 200px;
  padding: 20px 24px;
}

.av-snapshot-drawer__body {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
}

.av-chat-parties {
  display: flex;
  align-items: center;
  gap: 12px;
  background: var(--c-bg-secondary, #f8fafc);
  border-radius: var(--radius-md);
  padding: 14px 16px;
  margin-bottom: 20px;
}

.av-chat-party {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-width: 0;
}

.av-chat-party--right {
  flex-direction: row-reverse;
}

.av-chat-party__icon {
  font-size: 14px;
  flex-shrink: 0;
}

.av-chat-party__icon--reporter {
  color: var(--c-accent, #6366f1);
}

.av-chat-party__icon--reported {
  color: #ef4444;
}

.av-chat-party__label {
  font-size: 11px;
  color: var(--c-text-muted);
  background: var(--c-border-light, #e2e8f0);
  padding: 1px 6px;
  border-radius: 999px;
  flex-shrink: 0;
}

.av-chat-arrow {
  color: var(--c-text-muted);
  font-size: 12px;
  flex-shrink: 0;
}

.av-snap-section {
  margin-bottom: 24px;
}

.av-snap-subtitle {
  font-size: 14px;
  font-weight: 600;
  margin: 0 0 10px;
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--c-text);
}

.av-snap-chat {
  max-height: calc(100vh - 280px);
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px;
  background: var(--c-bg-secondary, #f8fafc);
  border-radius: var(--radius-md);
}

.av-snap-msg__head {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 2px;
}

.av-snap-msg__sender {
  font-size: 12px;
  font-weight: 600;
}

.av-snap-msg__sender--reporter {
  color: var(--c-accent, #6366f1);
}

.av-snap-msg__sender--reported {
  color: #ef4444;
}

.av-snap-msg__time {
  font-size: 11px;
  color: var(--c-text-muted);
}

.av-snap-msg__text {
  font-size: var(--text-sm);
  color: var(--c-text-secondary);
  line-height: 1.5;
  word-break: break-word;
  padding: 6px 10px;
  background: #fff;
  border-radius: var(--radius-sm);
  display: inline-block;
  max-width: 100%;
}

.av-snap-empty {
  color: var(--c-text-muted);
  font-size: var(--text-sm);
  text-align: center;
  padding: 24px 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.av-snap-empty i {
  font-size: 24px;
  color: var(--c-border);
}

.av-drawer-enter-active {
  transition: opacity 0.25s var(--ease);
}

.av-drawer-leave-active {
  transition: opacity 0.2s var(--ease);
}

.av-drawer-enter-from,
.av-drawer-leave-to {
  opacity: 0;
}
</style>
