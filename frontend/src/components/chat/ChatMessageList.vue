<script setup lang="ts">
import { ref } from 'vue'
import { Check, CheckCheck, MessageSquare } from 'lucide-vue-next'

import HomeAvatar from '../home/ui/HomeAvatar.vue'
import ChatRichTextRenderer from './ChatRichTextRenderer.vue'
import type { ChatAttachment, ChatMessage, Conversation } from '../../types/chat'
import { formatChatTime } from '../../utils/time'
import {
  getAttachmentFileName,
  getFileIconComponent,
  getMessageAttachments,
  isAttachmentOnly,
  isImageMime,
} from '../../composables/chat/attachmentUtils'

defineProps<{
  messages: ChatMessage[]
  loading: boolean
  myId: number
  conversation: Conversation
  attachments: ChatAttachment[]
}>()

const emit = defineEmits<{
  (e: 'missingAttachment'): void
}>()

const containerRef = ref<HTMLDivElement | null>(null)

function scrollToBottom() {
  if (!containerRef.value) return
  containerRef.value.scrollTop = containerRef.value.scrollHeight
}

defineExpose({
  scrollToBottom,
})
</script>

<template>
  <div ref="containerRef" class="chat-messages">
    <div v-if="loading" class="messages-loading">
      <div class="spinner"></div>
    </div>

    <div v-else-if="messages.length === 0" class="messages-empty">
      <MessageSquare :size="48" class="empty-icon" />
      <p>暂无聊天记录，开始打个招呼吧</p>
    </div>

    <template v-else>
      <div
        v-for="msg in messages"
        :key="msg.id"
        class="message-row"
        :class="{
          'msg-own': msg.sender_id === myId,
          'msg-other': msg.sender_id !== myId,
        }"
      >
        <template v-if="msg.sender_id !== myId">
          <div class="msg-other-wrap">
            <div class="msg-meta-other">
              <HomeAvatar
                :avatar-url="conversation.peer_avatar"
                :gender="conversation.peer_gender"
                size="sm"
                :alt="conversation.peer_name"
                class="msg-avatar-wrap"
              />
              <span class="msg-sender">{{ conversation.peer_name }}</span>
              <span class="msg-time">{{ formatChatTime(msg.created_at) }}</span>
            </div>
            <div v-if="!isAttachmentOnly(msg)" class="msg-content-other bubble-other">
              <ChatRichTextRenderer :content="msg.content" />
            </div>

            <div v-if="getMessageAttachments(attachments, msg.id).length" class="msg-attachments">
              <div v-for="att in getMessageAttachments(attachments, msg.id)" :key="att.id" class="att-preview-item">
                <a :href="att.file_url" target="_blank" class="att-preview-link">
                  <img v-if="isImageMime(att.mime_type)" :src="att.file_url" class="att-thumb" />
                  <div v-else class="att-icon-thumb">
                    <component :is="getFileIconComponent(att.mime_type, att.file_name)" :size="24" />
                    <span class="att-ext">{{ att.file_name.split('.').pop()?.toUpperCase() }}</span>
                  </div>
                </a>
              </div>
            </div>

            <div v-else-if="isAttachmentOnly(msg)" class="msg-attachments">
              <div class="att-preview-item" @click="emit('missingAttachment')">
                <div class="att-preview-link att-deleted-link">
                  <div class="att-icon-thumb att-deleted-style">
                    <component :is="getFileIconComponent('', getAttachmentFileName(msg))" :size="24" />
                    <span class="att-ext">
                      {{ getAttachmentFileName(msg).split('.').pop()?.toUpperCase() || '文件' }}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </template>

        <template v-else>
          <div class="msg-own-wrap">
            <div class="msg-meta-own">
              <span class="msg-time">{{ formatChatTime(msg.created_at) }}</span>
              <CheckCheck v-if="msg.is_read" :size="14" class="status-read" />
              <Check v-else :size="14" class="status-sent" />
              <span class="msg-sender-me">我</span>
            </div>

            <div v-if="!isAttachmentOnly(msg)" class="msg-bubble-own bubble-own">
              <ChatRichTextRenderer :content="msg.content" />
            </div>

            <div v-if="getMessageAttachments(attachments, msg.id).length" class="msg-attachments own-attachments">
              <div v-for="att in getMessageAttachments(attachments, msg.id)" :key="att.id" class="att-preview-item">
                <a :href="att.file_url" target="_blank" class="att-preview-link">
                  <img v-if="isImageMime(att.mime_type)" :src="att.file_url" class="att-thumb" />
                  <div v-else class="att-icon-thumb">
                    <component :is="getFileIconComponent(att.mime_type, att.file_name)" :size="24" />
                    <span class="att-ext">{{ att.file_name.split('.').pop()?.toUpperCase() }}</span>
                  </div>
                </a>
              </div>
            </div>

            <div v-else-if="isAttachmentOnly(msg)" class="msg-attachments own-attachments">
              <div class="att-preview-item" @click="emit('missingAttachment')">
                <div class="att-preview-link att-deleted-link">
                  <div class="att-icon-thumb att-deleted-style">
                    <component :is="getFileIconComponent('', getAttachmentFileName(msg))" :size="24" />
                    <span class="att-ext">
                      {{ getAttachmentFileName(msg).split('.').pop()?.toUpperCase() || '文件' }}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </template>
      </div>
    </template>
  </div>
</template>

<style scoped>
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

.messages-loading {
  display: flex;
  justify-content: center;
  padding: 48px;
}

.messages-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--c-text-muted);
  gap: 16px;
}

.empty-icon {
  opacity: 0.15;
}

.message-row {
  margin-bottom: 24px;
  animation: msg-in 0.3s var(--ease);
}

@keyframes msg-in {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.msg-other-wrap {
  display: flex;
  flex-direction: column;
}

.msg-meta-other {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.msg-avatar-wrap :deep(img) {
  border: 1px solid var(--c-border);
}

.msg-sender {
  font-size: var(--text-xs);
  font-weight: 600;
  color: var(--c-text-secondary);
}

.msg-time {
  font-size: 10px;
  color: var(--c-text-muted);
}

.msg-content-other {
  width: 100%;
  color: var(--c-text);
  line-height: 1.6;
}

.msg-own {
  display: flex;
  justify-content: flex-end;
}

.msg-own-wrap {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  max-width: 80%;
}

.msg-meta-own {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
}

.status-read {
  color: var(--c-accent);
}

.status-sent {
  color: var(--c-text-muted);
}

.msg-sender-me {
  font-size: var(--text-xs);
  font-weight: 600;
  color: var(--c-text-secondary);
  margin-left: 2px;
}

.msg-bubble-own {
  background: var(--c-accent);
  color: white;
  border-radius: 16px 4px 16px 16px;
  padding: 10px 16px;
  box-shadow: var(--shadow-sm);
  line-height: 1.6;
  border: 1px solid #2563eb80;
}

:deep(.rich-text) p {
  margin-top: 0.25em;
  margin-bottom: 0.25em;
}

:deep(.rich-text) p:first-child {
  margin-top: 0;
}

:deep(.rich-text) p:last-child {
  margin-bottom: 0;
}

:deep(.rich-text) ul,
:deep(.rich-text) ol {
  padding-left: 1.5em;
  margin: 0.25em 0;
}

:deep(.rich-text) ul {
  list-style-type: disc;
}

:deep(.rich-text) ol {
  list-style-type: decimal;
}

:deep(.rich-text) ul ul {
  list-style-type: circle;
}

:deep(.rich-text) ul ul ul {
  list-style-type: square;
}

:deep(.rich-text) li {
  margin: 0.1em 0;
}

:deep(.rich-text) li > ul,
:deep(.rich-text) li > ol {
  margin: 0;
}

:deep(.rich-text) blockquote {
  border-left: 3px solid var(--c-accent);
  margin: 0.4em 0;
  padding: 0.3em 0.8em;
  background: rgba(0, 0, 0, 0.03);
  border-radius: 0 6px 6px 0;
  color: var(--c-text-secondary);
}

:deep(.rich-text) blockquote p {
  margin: 0.15em 0;
}

:deep(.rich-text) pre,
:deep(.rich-text) pre.hljs-pre {
  position: relative;
  background: #f3f4f6;
  color: #1f2937;
  padding: 12px 14px;
  padding-top: 34px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 0.4em 0;
  font-size: 0.85em;
  line-height: 1.5;
  border: 1px solid #e5e7eb;
}

:deep(.rich-text) pre code,
:deep(.rich-text) pre.hljs-pre code {
  font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
  background: transparent;
  padding: 0;
  border-radius: 0;
  font-size: inherit;
  color: inherit;
}

:deep(.rich-text) code {
  font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
  background: rgba(0, 0, 0, 0.06);
  padding: 1px 5px;
  border-radius: 4px;
  font-size: 0.85em;
}

:deep(.code-lang) {
  position: absolute;
  top: 8px;
  left: 12px;
  font-size: 11px;
  font-weight: 600;
  color: #9ca3af;
  font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
  user-select: none;
  letter-spacing: 0.03em;
}

:deep(.bubble-own .code-lang) {
  color: rgba(255, 255, 255, 0.45);
}

:deep(.code-copy-btn) {
  position: absolute;
  top: 7px;
  right: 8px;
  padding: 4px 6px;
  border: none;
  border-radius: 5px;
  background: transparent;
  color: #6b7280;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition:
    background 0.15s,
    color 0.15s;
  line-height: 0;
}

:deep(.code-copy-btn:hover) {
  background: #e5e7eb;
  color: #111827;
}

:deep(.code-copy-btn .icon-check) {
  display: none;
}

:deep(.code-copy-btn.copied .icon-copy) {
  display: none;
}

:deep(.code-copy-btn.copied .icon-check) {
  display: flex;
  color: #16a34a;
}

:deep(.rich-text) table {
  width: 100%;
  border-collapse: collapse;
  margin: 0.4em 0;
  font-size: 0.9em;
}

:deep(.rich-text) th,
:deep(.rich-text) td {
  padding: 6px 10px;
  text-align: left;
}

:deep(.rich-text) th {
  font-weight: 600;
  border-bottom: 2px solid var(--c-text-muted);
}

:deep(.rich-text) td {
  border-bottom: 1px solid var(--c-border);
}

:deep(.rich-text) tr:last-child td {
  border-bottom: none;
}

:deep(.rich-text) hr {
  border: none;
  border-top: 1px solid var(--c-border);
  margin: 0.5em 0;
}

:deep(.rich-text) img {
  width: 25vw;
  min-width: 150px;
  max-width: 100%;
  height: auto;
  border-radius: 8px;
  display: block;
  margin: 0 auto;
  box-shadow: var(--shadow-xs);
}

:deep(.bubble-other .rich-text > *:not(p:has(img))) {
  margin-left: 2rem;
  max-width: calc(85% - 2rem);
}

:deep(.bubble-other .rich-text p:has(img)) {
  display: flex;
  justify-content: center;
  width: 100%;
  margin: 1rem 0;
}

:deep(.bubble-own .rich-text) {
  color: white !important;
}

:deep(.bubble-own .rich-text) a {
  color: #bfdbfe;
  text-decoration: underline;
}

:deep(.bubble-own .rich-text) pre {
  background: rgba(0, 0, 0, 0.25);
  color: #e2e8f0;
  border-color: rgba(255, 255, 255, 0.15);
}

:deep(.bubble-own .rich-text) pre code {
  background: transparent;
  color: inherit;
}

:deep(.bubble-own .rich-text) code {
  background: rgba(255, 255, 255, 0.2);
  color: white;
}

:deep(.bubble-own .code-copy-btn) {
  color: rgba(255, 255, 255, 0.6);
}

:deep(.bubble-own .code-copy-btn:hover) {
  background: rgba(255, 255, 255, 0.15);
  color: white;
}

:deep(.bubble-own .rich-text) blockquote {
  border-left-color: rgba(255, 255, 255, 0.5);
  background: rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.85);
}

:deep(.bubble-own .rich-text) th {
  border-bottom-color: rgba(255, 255, 255, 0.4);
}

:deep(.bubble-own .rich-text) td {
  border-bottom-color: rgba(255, 255, 255, 0.15);
}

:deep(.bubble-own .katex) {
  color: white;
}

:deep(.bubble-own .rich-text p:has(img)) {
  display: flex;
  justify-content: center;
  margin: 0.5rem 0;
}

:deep(.bubble-other .rich-text) {
  color: var(--c-text);
  width: 100%;
}

:deep(.bubble-other .rich-text) a {
  color: var(--c-accent);
  text-decoration: underline;
}

:deep(.latex-error) {
  color: var(--c-danger);
  font-size: var(--text-xs);
  background: var(--c-danger-light);
  padding: 1px 4px;
  border-radius: 4px;
}

.msg-attachments {
  display: flex;
  gap: 8px;
  margin-top: 6px;
  padding-left: 2rem;
  flex-wrap: wrap;
}

.own-attachments {
  padding-left: 0;
  justify-content: flex-end;
}

.att-preview-item {
  width: 72px;
  height: 72px;
  flex-shrink: 0;
}

.att-preview-link {
  display: block;
  width: 100%;
  height: 100%;
  border-radius: 10px;
  overflow: hidden;
  border: 1.5px solid var(--c-text-muted);
  transition:
    box-shadow var(--dur-fast) var(--ease),
    transform var(--dur-fast) var(--ease);
}

.att-preview-link:hover {
  box-shadow: var(--shadow-md);
  transform: scale(1.04);
}

.att-thumb {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.att-icon-thumb {
  width: 100%;
  height: 100%;
  background: var(--c-bg);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  color: var(--c-text-muted);
}

.att-ext {
  font-size: 9px;
  font-weight: 700;
  color: var(--c-text-muted);
  line-height: 1;
  max-width: 56px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.att-deleted-link {
  cursor: pointer;
  opacity: 0.5;
}

.att-deleted-style {
  position: relative;
}

.att-deleted-link:hover {
  opacity: 0.75;
}

@media (max-width: 768px) {
  .chat-messages {
    padding: 16px;
  }

  .msg-own-wrap {
    max-width: 90%;
  }
}
</style>
