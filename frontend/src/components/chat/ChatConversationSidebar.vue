<script setup lang="ts">
import { computed } from 'vue'
import { MessageSquare, Search, ShieldAlert, Trash2 } from 'lucide-vue-next'

import HomeAvatar from '../home/ui/HomeAvatar.vue'
import type { Conversation } from '../../types/chat'
import { formatChatTime, formatLastSeen } from '../../utils/time'
import { convKey } from '../../composables/chat/conversationKey'
import type { ConversationContextMenu } from '../../composables/chat/useConversationListInteraction'

const props = defineProps<{
  conversations: Conversation[]
  activeConversation: Conversation | null
  isMobile: boolean
  isHidden: boolean
  swipedKey: string | null
  ctxMenu: ConversationContextMenu | null
  searchQuery: string
}>()

const emit = defineEmits<{
  (e: 'update:searchQuery', value: string): void
  (e: 'select', value: Conversation): void
  (e: 'hide', key: string): void
  (e: 'swipeStart', payload: { event: TouchEvent; key: string }): void
  (e: 'swipeMove', payload: { event: TouchEvent; key: string }): void
  (e: 'swipeEnd'): void
  (e: 'openContextMenu', payload: { event: MouseEvent; key: string }): void
  (e: 'closeSwipe'): void
  (e: 'closeContextMenu'): void
}>()

const searchModel = computed({
  get: () => props.searchQuery,
  set: (value: string) => emit('update:searchQuery', value),
})

const safeConversations = computed(() =>
  props.conversations.filter(
    (conversation): conversation is Conversation =>
      Boolean(conversation && typeof conversation.peer_id === 'number'),
  ),
)

function handleListClick() {
  emit('closeSwipe')
  emit('closeContextMenu')
}

function handleConversationClick(conversation: Conversation) {
  emit('closeSwipe')
  emit('closeContextMenu')
  emit('select', conversation)
}
</script>

<template>
  <aside class="chat-sidebar" :class="{ 'sidebar-hidden': isHidden }">
    <div class="sidebar-header">
      <h1 class="sidebar-title">消息中心</h1>
      <div class="sidebar-search-inline">
        <Search class="search-icon-inline" :size="14" />
        <input v-model="searchModel" type="text" placeholder="搜索..." class="search-input-inline" />
      </div>
    </div>

    <div class="contact-list" @click="handleListClick">
      <div
        v-for="conversation in safeConversations"
        :key="convKey(conversation)"
        class="contact-item-wrap"
        :class="{ swiped: isMobile && swipedKey === convKey(conversation) }"
        @touchstart.passive="isMobile && emit('swipeStart', { event: $event, key: convKey(conversation) })"
        @touchmove.passive="isMobile && emit('swipeMove', { event: $event, key: convKey(conversation) })"
        @touchend.passive="isMobile && emit('swipeEnd')"
        @contextmenu.prevent="!isMobile && emit('openContextMenu', { event: $event, key: convKey(conversation) })"
      >
        <div
          class="contact-item"
          :class="{
            active:
              activeConversation?.peer_id === conversation.peer_id &&
              activeConversation?.task_id === conversation.task_id,
            blocked: conversation.blocked_by_me || conversation.blocked_by_them,
          }"
          @click.stop="handleConversationClick(conversation)"
        >
          <div class="contact-avatar-wrap">
            <HomeAvatar
              :avatar-url="conversation.peer_avatar"
              :gender="conversation.peer_gender"
              size="lg"
              :alt="conversation.peer_name"
            />
            <div v-if="conversation.blocked_by_me || conversation.blocked_by_them" class="avatar-badge blocked-badge">
              <ShieldAlert :size="10" />
            </div>
            <div v-else-if="formatLastSeen(conversation.peer_last_active).online" class="avatar-badge online-badge"></div>
          </div>
          <div class="contact-info">
            <div class="contact-top-row">
              <span
                class="contact-name"
                :class="{ 'name-blocked': conversation.blocked_by_me || conversation.blocked_by_them }"
              >
                {{ conversation.peer_name }}
              </span>
              <span class="contact-time">
                {{ conversation.last_message_time ? formatChatTime(conversation.last_message_time) : '' }}
              </span>
            </div>
            <div class="contact-bottom-row">
              <span class="contact-preview">{{ conversation.last_message || '暂无消息' }}</span>
              <span v-if="conversation.unread_count > 0" class="unread-badge">
                {{ conversation.unread_count > 99 ? '99+' : conversation.unread_count }}
              </span>
            </div>
          </div>
        </div>

        <button v-if="isMobile" class="swipe-delete-btn" @click.stop="emit('hide', convKey(conversation))">
          <Trash2 :size="18" />
        </button>
      </div>

      <div v-if="safeConversations.length === 0" class="no-contacts">
        <MessageSquare :size="32" />
        <p>暂无聊天记录</p>
      </div>
    </div>
  </aside>

  <Teleport to="body">
    <div
      v-if="ctxMenu"
      class="ctx-menu"
      :style="{ top: `${ctxMenu.y}px`, left: `${ctxMenu.x}px` }"
      @click.stop
      @contextmenu.prevent.stop
    >
      <button class="ctx-menu-item ctx-menu-item--danger" @click="emit('hide', ctxMenu.key)">
        <Trash2 :size="14" />
        从列表移除
      </button>
    </div>
  </Teleport>
</template>

<style scoped>
@keyframes chat-rise {
  from {
    opacity: 0;
    transform: translateY(16px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.chat-sidebar {
  display: flex;
  flex-direction: column;
  width: 320px;
  background: var(--c-surface);
  border-right: 1px solid var(--c-border);
  flex-shrink: 0;
  z-index: 20;
  animation: chat-rise 0.48s cubic-bezier(0.22, 1, 0.36, 1) 0ms both;
}

.sidebar-header {
  padding: 10px 16px;
  border-bottom: 1px solid var(--c-border-light);
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.sidebar-title {
  font-size: var(--text-lg);
  font-weight: 700;
  white-space: nowrap;
  flex-shrink: 0;
  background: linear-gradient(135deg, var(--c-accent), #7c3aed);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.sidebar-search-inline {
  flex: 1;
  min-width: 0;
  position: relative;
  display: flex;
  align-items: center;
}

.search-icon-inline {
  position: absolute;
  left: 10px;
  color: var(--c-text-muted);
  pointer-events: none;
}

.search-input-inline {
  width: 100%;
  padding: 6px 12px 6px 30px;
  background: var(--c-bg);
  border: 1.5px solid var(--c-border);
  border-radius: 999px;
  font-size: var(--text-sm);
  color: var(--c-text);
  outline: none;
  transition:
    border-color var(--dur-fast) var(--ease),
    box-shadow var(--dur-fast) var(--ease),
    background var(--dur-fast) var(--ease);
}

.search-input-inline::placeholder {
  color: var(--c-text-muted);
}

.search-input-inline:focus {
  border-color: var(--c-accent);
  box-shadow: 0 0 0 3px var(--c-accent-soft);
  background: var(--c-surface);
}

.contact-list {
  flex: 1;
  overflow-y: auto;
}

.contact-item-wrap {
  position: relative;
  overflow: hidden;
  margin: 4px 8px;
  border-radius: 12px;
}

.contact-item-wrap .contact-item {
  margin: 0;
  border-radius: 12px;
}

@media (hover: none) and (pointer: coarse) {
  .contact-item-wrap .contact-item {
    transform: translateX(0);
    transition: transform 0.28s cubic-bezier(0.4, 0, 0.2, 1);
  }

  .contact-item-wrap.swiped .contact-item {
    transform: translateX(-72px);
  }

  .swipe-delete-btn {
    position: absolute;
    top: 0;
    right: 0;
    height: 100%;
    width: 72px;
    background: var(--c-danger);
    color: white;
    border: none;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    border-radius: 0 12px 12px 0;
    transform: translateX(100%);
    transition: transform 0.28s cubic-bezier(0.4, 0, 0.2, 1);
  }

  .contact-item-wrap.swiped .swipe-delete-btn {
    transform: translateX(0);
  }

  .swipe-delete-btn:hover {
    background: var(--c-danger-hover, #dc2626);
  }
}

.ctx-menu {
  position: fixed;
  z-index: 9000;
  background: var(--c-surface);
  border: 1px solid var(--c-border);
  border-radius: 10px;
  box-shadow: var(--shadow-lg);
  padding: 4px;
  min-width: 140px;
  animation: ctx-in 0.12s ease;
}

@keyframes ctx-in {
  from {
    opacity: 0;
    transform: scale(0.94);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

.ctx-menu-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 7px 12px;
  border: none;
  background: transparent;
  border-radius: 7px;
  font-size: var(--text-sm);
  cursor: pointer;
  color: var(--c-text);
  transition: background var(--dur-fast) var(--ease);
}

.ctx-menu-item:hover {
  background: var(--c-bg);
}

.ctx-menu-item--danger {
  color: var(--c-danger);
}

.ctx-menu-item--danger:hover {
  background: var(--c-danger-light);
}

.contact-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 12px;
  cursor: pointer;
  transition:
    background var(--dur-fast) var(--ease),
    border-color var(--dur-fast) var(--ease);
  border: 1px solid transparent;
}

.contact-item:hover {
  background: var(--c-bg);
}

.contact-item.active {
  background: var(--c-accent-light);
  border-color: var(--c-accent-soft);
  box-shadow: var(--shadow-xs);
}

.contact-avatar-wrap {
  position: relative;
  flex-shrink: 0;
}

.contact-avatar-wrap :deep(img) {
  border: 1px solid var(--c-border);
  box-shadow: var(--shadow-xs);
}

.avatar-badge {
  position: absolute;
  bottom: -2px;
  right: -2px;
  border: 2px solid var(--c-surface);
  border-radius: 50%;
}

.online-badge {
  width: 12px;
  height: 12px;
  background: var(--c-success);
}

.blocked-badge {
  background: var(--c-danger);
  color: white;
  padding: 1px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.contact-info {
  flex: 1;
  min-width: 0;
}

.contact-top-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.contact-name {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--c-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.contact-item.active .contact-name {
  color: #1e3a5f;
}

.name-blocked {
  color: var(--c-danger) !important;
}

.contact-time {
  font-size: var(--text-xs);
  color: var(--c-text-muted);
  flex-shrink: 0;
  margin-left: 8px;
}

.contact-bottom-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.contact-preview {
  font-size: var(--text-xs);
  color: var(--c-text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}

.unread-badge {
  background: var(--c-accent);
  color: white;
  font-size: 10px;
  font-weight: 700;
  min-width: 18px;
  height: 18px;
  border-radius: 9px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 5px;
  flex-shrink: 0;
}

.no-contacts {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 16px;
  color: var(--c-text-muted);
  gap: 8px;
}

@media (max-width: 768px) {
  .chat-sidebar {
    width: 100%;
  }

  .sidebar-hidden {
    display: none;
  }
}
</style>
