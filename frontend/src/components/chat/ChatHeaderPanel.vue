<script setup lang="ts">
import { ChevronUp, Compass, Flag, Paperclip, ShieldOff, ArrowLeft } from 'lucide-vue-next'

import HomeAvatar from '../home/ui/HomeAvatar.vue'
import type { Conversation } from '../../types/chat'
import { getTaskIcon } from '../../utils/taskIcons'
import {
  snapshotStatusClass,
  snapshotStatusLabel,
} from '../../composables/chat/taskSnapshotStatus'

defineProps<{
  conversation: Conversation
  isMobile: boolean
  isBlocked: boolean
  isBannerCollapsed: boolean
  attachmentCount: number
  peerOnlineStatus: { online: boolean; text: string }
}>()

const emit = defineEmits<{
  (e: 'back'): void
  (e: 'openReport'): void
  (e: 'toggleBlock'): void
  (e: 'openAttachments'): void
  (e: 'toggleBanner'): void
  (e: 'openTaskDetail'): void
  (e: 'openUserDetail'): void
}>()
</script>

<template>
  <div class="chat-header">
    <div class="header-top">
      <div class="header-left">
        <button v-if="isMobile" class="icon-btn back-btn" @click="emit('back')">
          <ArrowLeft :size="22" />
        </button>
        <div class="header-avatar-container">
          <HomeAvatar
            :avatar-url="conversation.peer_avatar"
            :gender="conversation.peer_gender"
            size="lg"
            :alt="conversation.peer_name"
            class="header-avatar-wrap"
          />
          <span v-if="peerOnlineStatus.online" class="header-online-dot"></span>
        </div>
        <div>
          <h2 class="header-name" :class="{ 'name-blocked': isBlocked }">{{ conversation.peer_name }}</h2>
          <p class="header-last-seen" :class="{ 'last-seen-online': peerOnlineStatus.online }">
            {{ peerOnlineStatus.text }}
          </p>
        </div>
      </div>

      <div class="header-actions">
        <button class="icon-btn" title="举报此用户" @click="emit('openReport')">
          <Flag :size="18" />
        </button>
        <button
          class="icon-btn"
          :class="{ 'btn-blocked': conversation.blocked_by_me }"
          :title="conversation.blocked_by_me ? '解除拉黑' : '拉黑此用户'"
          @click="emit('toggleBlock')"
        >
          <ShieldOff :size="18" />
        </button>
        <button class="icon-btn" @click="emit('openAttachments')">
          <Paperclip :size="18" />
          <span v-if="attachmentCount > 0" class="att-count-badge">{{ attachmentCount }}</span>
        </button>
      </div>
    </div>

    <div class="banner-area" :class="{ 'banner-collapsed': isBannerCollapsed }">
      <div class="banner-content">
        <div
          v-if="conversation.task_id"
          class="task-snapshot"
          :class="{
            'task-snapshot--clickable': !conversation.task_is_deleted,
            'task-snapshot--deleted': conversation.task_is_deleted,
          }"
          @click="!conversation.task_is_deleted && emit('openTaskDetail')"
        >
          <div class="snapshot-icon-wrap" :style="{ background: getTaskIcon(conversation.task_icon).bg }">
            <component
              :is="getTaskIcon(conversation.task_icon).component"
              :size="16"
              :style="{ color: getTaskIcon(conversation.task_icon).color }"
            />
          </div>
          <span v-if="conversation.task_is_deleted" class="snapshot-badge snapshot-badge--deleted">已删除</span>
          <span v-else class="snapshot-badge">快照</span>
          <span class="snapshot-title">{{ conversation.task_title || '未知任务' }}</span>
          <div class="snapshot-right">
            <span class="snapshot-price">¥{{ conversation.task_price ?? '—' }}</span>
            <span v-if="conversation.task_is_deleted" class="snapshot-status status-deleted">已删除</span>
            <span v-else class="snapshot-status" :class="snapshotStatusClass(conversation.task_status)">
              {{ snapshotStatusLabel(conversation.task_status) }}
            </span>
          </div>
        </div>

        <div v-else class="marketplace-badge marketplace-badge--clickable" @click="emit('openUserDetail')">
          <Compass :size="16" />
          <span>来自接单广场 · 查看对方资料</span>
        </div>
      </div>

      <button class="collapse-toggle" @click="emit('toggleBanner')">
        <ChevronUp :size="12" class="collapse-chevron" :class="{ rotated: isBannerCollapsed }" />
      </button>
    </div>
  </div>
</template>

<style scoped>
.chat-header {
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--c-border);
  position: sticky;
  top: 0;
  z-index: 10;
  flex-shrink: 0;
}

.header-top {
  padding: 12px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.back-btn {
  margin-left: -8px;
}

.header-avatar-container {
  position: relative;
  flex-shrink: 0;
}

.header-avatar-wrap :deep(img) {
  border: 1px solid var(--c-border);
}

.header-online-dot {
  position: absolute;
  bottom: 1px;
  right: 1px;
  width: 12px;
  height: 12px;
  background: #22c55e;
  border-radius: 50%;
  border: 2px solid white;
}

.header-name {
  font-size: var(--text-base);
  font-weight: 700;
  color: var(--c-text);
  line-height: 1.2;
}

.name-blocked {
  color: var(--c-danger) !important;
}

.header-last-seen {
  font-size: 11px;
  color: var(--c-text-muted);
  margin: 0;
  line-height: 1.3;
}

.last-seen-online {
  color: #22c55e;
  font-weight: 500;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 2px;
  flex-shrink: 0;
}

.btn-blocked {
  color: var(--c-danger) !important;
}

.att-count-badge {
  position: absolute;
  top: -4px;
  right: -4px;
  background: var(--c-accent);
  color: white;
  font-size: 9px;
  font-weight: 700;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.banner-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 0 24px;
}

.banner-content {
  width: 100%;
  overflow: hidden;
  max-height: 80px;
  transition:
    max-height 0.28s cubic-bezier(0.4, 0, 0.2, 1),
    opacity 0.22s ease,
    margin-bottom 0.28s ease;
  opacity: 1;
  margin-bottom: 2px;
}

.banner-area.banner-collapsed .banner-content {
  max-height: 0;
  opacity: 0;
  margin-bottom: 0;
}

.collapse-toggle {
  display: flex;
  width: 100%;
  height: 18px;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  background: transparent;
  border: none;
  color: var(--c-text-muted);
  opacity: 0.35;
  transition:
    opacity 0.2s ease,
    height 0.28s cubic-bezier(0.4, 0, 0.2, 1),
    background 0.15s ease;
  border-top: 1px solid var(--c-border-light);
  flex-shrink: 0;
}

.banner-area.banner-collapsed .collapse-toggle {
  height: 10px;
  border-top-color: transparent;
  opacity: 0.25;
}

.collapse-toggle:hover {
  opacity: 0.8;
  background: var(--c-bg);
}

.banner-area.banner-collapsed .collapse-toggle:hover {
  opacity: 0.6;
}

.task-snapshot {
  background: var(--c-surface);
  border: 1px solid var(--c-border);
  border-radius: 12px;
  box-shadow: var(--shadow-xs);
  margin-bottom: 4px;
  padding: 10px;
  display: flex;
  align-items: center;
  gap: 10px;
}

.task-snapshot--clickable {
  cursor: pointer;
  transition:
    border-color var(--dur-fast) var(--ease),
    box-shadow var(--dur-fast) var(--ease);
}

.task-snapshot--clickable:hover {
  border-color: var(--c-accent);
  box-shadow: var(--shadow-sm);
}

.snapshot-icon-wrap {
  padding: 6px;
  border-radius: 8px;
  flex-shrink: 0;
  display: flex;
}

.task-snapshot--deleted {
  opacity: 0.7;
  border-color: var(--c-border);
  cursor: default;
}

.snapshot-badge {
  font-size: 10px;
  font-weight: 600;
  color: var(--c-accent);
  background: var(--c-accent-light);
  padding: 2px 6px;
  border-radius: 4px;
  border: 1px solid var(--c-accent-soft);
  flex-shrink: 0;
}

.snapshot-badge--deleted {
  color: #ef4444;
  background: #fef2f2;
  border-color: #fecaca;
}

.snapshot-title {
  font-size: var(--text-sm);
  font-weight: 700;
  color: var(--c-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  min-width: 0;
}

.snapshot-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  flex-shrink: 0;
  padding-left: 12px;
  border-left: 1px solid var(--c-border-light);
}

.snapshot-price {
  font-size: var(--text-base);
  font-weight: 800;
  color: var(--c-text);
  line-height: 1;
  margin-bottom: 4px;
}

.snapshot-status {
  font-size: 10px;
  font-weight: 600;
  line-height: 1;
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

.status-deleted {
  color: #ef4444;
}

.marketplace-badge {
  background: #eff6ff80;
  border: 1px solid #bfdbfe;
  border-radius: 12px;
  margin-bottom: 4px;
  padding: 8px 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: var(--c-accent);
}

.marketplace-badge span {
  font-size: var(--text-sm);
  font-weight: 500;
}

.marketplace-badge--clickable {
  cursor: pointer;
  transition:
    border-color var(--dur-fast) var(--ease),
    box-shadow var(--dur-fast) var(--ease),
    background var(--dur-fast) var(--ease);
}

.marketplace-badge--clickable:hover {
  border-color: #93c5fd;
  box-shadow: var(--shadow-sm);
  background: #eff6ffcc;
}

.collapse-chevron {
  transition: transform 0.28s cubic-bezier(0.4, 0, 0.2, 1);
}

.collapse-chevron.rotated {
  transform: rotate(180deg);
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

@media (max-width: 768px) {
  .header-top {
    padding: 12px 16px;
  }

  .banner-area {
    padding: 0 16px;
  }
}
</style>
