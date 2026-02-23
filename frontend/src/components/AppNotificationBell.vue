<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import {
  AlertTriangle,
  Ban,
  Bell,
  Check,
  CheckCircle,
  LogOut,
  MessageCircle,
  ShieldCheck,
  UserCheck,
  X,
} from 'lucide-vue-next'

import { useAuthStore } from '../stores/auth'
import { useNotificationStore } from '../stores/notifications'
import { formatRelativeTime } from '../utils/time'
import type { AppNotification, NotificationType } from '../types/api'

const router = useRouter()
const authStore = useAuthStore()
const notifStore = useNotificationStore()

const isOpen = ref(false)
const isExpanded = ref(false)
const wrapRef = ref<HTMLElement | null>(null)

const notifications = computed(() => notifStore.notifications)
const unreadCount = computed(() => notifStore.unreadCount)

const hasReadableUnread = computed(() =>
  notifications.value.some(n => !n.is_read && n.dismiss_type === 'read'),
)

const displayedNotifications = computed(() => {
  if (isExpanded.value) return notifications.value
  return notifications.value.slice(0, 5)
})

function toggleOpen() {
  isOpen.value = !isOpen.value
  if (isOpen.value) {
    notifStore.load()
  }
}

function onClickOutside(e: MouseEvent) {
  if (wrapRef.value && !wrapRef.value.contains(e.target as Node)) {
    isOpen.value = false
  }
}

watch(isOpen, (val) => {
  if (!val) {
    setTimeout(() => { isExpanded.value = false }, 300)
  }
})

async function markAllRead() {
  await notifStore.markAllRead()
}

function handleClick(n: AppNotification) {
  isOpen.value = false

  if (n.dismiss_type === 'read' && !n.is_read && n.id > 0) {
    notifStore.markRead(n.id).catch(() => {})
  }

  if (n.type === 'chat_message') {
    const query: Record<string, string> = {}
    if (n.related_user_id) query.peer = String(n.related_user_id)
    if (n.related_task_id) query.task = String(n.related_task_id)
    router.push({ path: '/chat', query })
  } else if (n.type === 'report_reviewed') {
    router.push('/reports')
  } else if (n.type === 'punishment') {
    router.push('/reports?tab=received')
  } else if (n.related_task_id) {
    router.push({ path: '/', query: { task: String(n.related_task_id) } })
  }
}

function dismissNotification(e: Event, n: AppNotification) {
  e.stopPropagation()
  if (n.id > 0) {
    notifStore.remove(n.id)
  }
}

const iconMap: Record<NotificationType, any> = {
  task_expired: AlertTriangle,
  chat_message: MessageCircle,
  task_accepted: UserCheck,
  report_reviewed: ShieldCheck,
  task_completed: CheckCircle,
  task_abandoned: LogOut,
  punishment: Ban,
}

function getIcon(type: string) {
  return iconMap[type as NotificationType] || Bell
}

onMounted(() => {
  document.addEventListener('mousedown', onClickOutside)
  if (authStore.isAuthenticated) {
    notifStore.startPolling()
  }
})

onUnmounted(() => {
  document.removeEventListener('mousedown', onClickOutside)
  notifStore.stopPolling()
})
</script>

<template>
  <div ref="wrapRef" class="notif-bell-wrap">
    <button
      class="notif-bell-btn"
      :class="{ 'notif-bell-btn--active': isOpen }"
      @click="toggleOpen"
    >
      <Bell :size="20" :stroke-width="2" />
      <span v-if="unreadCount > 0" class="notif-badge">
        {{ unreadCount > 99 ? '99+' : unreadCount }}
      </span>
    </button>

    <Transition name="notif-anim">
      <div v-if="isOpen" class="notif-dropdown">
        <div class="notif-dropdown__header">
          <div class="notif-dropdown__title-row">
            <h3 class="notif-dropdown__title">通知中心</h3>
            <span v-if="unreadCount > 0" class="notif-unread-tag">{{ unreadCount }} 未读</span>
          </div>
          <button v-if="hasReadableUnread" class="notif-mark-all-btn" @click="markAllRead">
            <Check :size="14" />
            全部已读
          </button>
        </div>

        <div class="notif-dropdown__body">
          <div v-if="notifications.length === 0" class="notif-empty">
            <div class="notif-empty__icon">
              <Bell :size="24" />
            </div>
            <p class="notif-empty__title">暂无新通知</p>
            <p class="notif-empty__sub">当前没有需要处理的事项</p>
          </div>

          <template v-else>
            <div
              v-for="n in displayedNotifications"
              :key="n.id"
              class="notif-item"
              :class="{ 'notif-item--unread': !n.is_read }"
              @click="handleClick(n)"
            >
              <div class="notif-item__icon" :class="`notif-icon--${n.type}`">
                <component :is="getIcon(n.type)" :size="20" :stroke-width="1.5" />
              </div>
              <div class="notif-item__body">
                <div class="notif-item__top">
                  <span
                    class="notif-item__title"
                    :class="{ 'notif-item__title--bold': !n.is_read }"
                  >{{ n.title }}</span>
                  <span class="notif-item__time">{{ formatRelativeTime(n.created_at) }}</span>
                </div>
                <p
                  class="notif-item__desc"
                  :class="{ 'notif-item__desc--unread': !n.is_read }"
                >{{ n.description }}</p>
              </div>
              <span v-if="n.dismiss_type === 'persistent'" class="notif-item__persistent-tag">
                <i class="fa-solid fa-thumbtack"></i>
              </span>
              <button
                v-else-if="n.dismiss_type === 'read' && n.id > 0"
                class="notif-item__close"
                @click="dismissNotification($event, n)"
              >
                <X :size="16" />
              </button>
            </div>

            <div v-if="notifications.length > 5" class="notif-dropdown__footer">
              <button class="notif-expand-btn" @click="isExpanded = !isExpanded">
                {{ isExpanded ? '收起通知' : `查看全部 ${notifications.length} 条通知` }}
              </button>
            </div>
          </template>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.notif-bell-wrap {
  position: relative;
}

.notif-bell-btn {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: 1px solid transparent;
  background: transparent;
  color: var(--c-text-secondary, #525252);
  cursor: pointer;
  transition: background 0.2s, border-color 0.2s;
}

@media (hover: hover) {
  .notif-bell-btn:hover {
    background: var(--c-border-light, #f5f5f5);
    border-color: var(--c-border, #e5e5e5);
  }
}

.notif-bell-btn--active {
  background: var(--c-border-light, #f0f0f0);
}

.notif-badge {
  position: absolute;
  top: -2px;
  right: -2px;
  background: #f43f5e;
  color: #fff;
  font-size: 10px;
  font-weight: 700;
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  border-radius: 9px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px solid #fff;
  line-height: 1;
  pointer-events: none;
}

.notif-dropdown {
  position: absolute;
  right: 0;
  top: calc(100% + 8px);
  width: 380px;
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 12px 40px -12px rgba(0, 0, 0, 0.15);
  border: 1px solid rgba(0, 0, 0, 0.06);
  overflow: hidden;
  z-index: 1000;
  transform-origin: top right;
}

.notif-dropdown__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
}

.notif-dropdown__title-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.notif-dropdown__title {
  font-size: 15px;
  font-weight: 600;
  color: #171717;
  margin: 0;
}

.notif-unread-tag {
  font-size: 11px;
  font-weight: 500;
  padding: 2px 8px;
  border-radius: 99px;
  background: #fff1f2;
  color: #e11d48;
}

.notif-mark-all-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  font-weight: 500;
  color: #737373;
  background: none;
  border: none;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 6px;
  transition: color 0.15s, background 0.15s;
}

@media (hover: hover) {
  .notif-mark-all-btn:hover {
    color: #171717;
    background: #f5f5f5;
  }
}

.notif-dropdown__body {
  max-height: 60vh;
  overflow-y: auto;
  overscroll-behavior: contain;
}

.notif-dropdown__body::-webkit-scrollbar {
  width: 4px;
}

.notif-dropdown__body::-webkit-scrollbar-track {
  background: transparent;
}

.notif-dropdown__body::-webkit-scrollbar-thumb {
  background-color: #e5e5e5;
  border-radius: 10px;
}

.notif-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 24px;
  text-align: center;
}

.notif-empty__icon {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: #f5f5f5;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 12px;
  color: #d4d4d4;
}

.notif-empty__title {
  font-size: 14px;
  font-weight: 500;
  color: #171717;
  margin: 0 0 4px;
}

.notif-empty__sub {
  font-size: 12px;
  color: #a3a3a3;
  margin: 0;
}

.notif-item {
  position: relative;
  display: flex;
  align-items: flex-start;
  padding: 14px 16px;
  cursor: pointer;
  transition: background 0.15s;
  border-left: 2px solid transparent;
}

@media (hover: hover) {
  .notif-item:hover {
    background: #fafafa;
  }
}

.notif-item--unread {
  border-left-color: #3b82f6;
  background: rgba(59, 130, 246, 0.03);
}

.notif-item__icon {
  flex-shrink: 0;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 2px;
}

.notif-icon--task_expired {
  background: #fff7ed;
  color: #f59e0b;
}

.notif-icon--chat_message {
  background: #eff6ff;
  color: #3b82f6;
}

.notif-icon--task_accepted {
  background: #f0fdf4;
  color: #22c55e;
}

.notif-icon--report_reviewed {
  background: #faf5ff;
  color: #a855f7;
}

.notif-icon--task_completed {
  background: #ecfdf5;
  color: #10b981;
}

.notif-icon--task_abandoned {
  background: #fff7ed;
  color: #f97316;
}

.notif-icon--punishment {
  background: #fef2f2;
  color: #ef4444;
}

.notif-item__persistent-tag {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  color: #ef4444;
  font-size: 11px;
  opacity: 0.6;
}

.notif-item__body {
  flex: 1;
  min-width: 0;
  margin-left: 12px;
  padding-right: 24px;
}

.notif-item__top {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 2px;
}

.notif-item__title {
  font-size: 13px;
  color: #525252;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  padding-right: 8px;
}

.notif-item__title--bold {
  font-weight: 600;
  color: #171717;
}

.notif-item__time {
  font-size: 11px;
  color: #a3a3a3;
  white-space: nowrap;
  flex-shrink: 0;
}

.notif-item__desc {
  font-size: 12px;
  color: #a3a3a3;
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  line-height: 1.5;
}

.notif-item__desc--unread {
  color: #737373;
}

.notif-item__close {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 4px;
  background: none;
  border: none;
  color: #d4d4d4;
  border-radius: 6px;
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.15s, color 0.15s, background 0.15s;
}

.notif-item:hover .notif-item__close {
  opacity: 1;
}

@media (hover: hover) {
  .notif-item__close:hover {
    color: #525252;
    background: rgba(0, 0, 0, 0.05);
  }
}

.notif-dropdown__footer {
  padding: 10px 16px;
  border-top: 1px solid rgba(0, 0, 0, 0.06);
  text-align: center;
}

.notif-expand-btn {
  font-size: 12px;
  font-weight: 500;
  color: #3b82f6;
  background: none;
  border: none;
  cursor: pointer;
  padding: 6px 12px;
  border-radius: 6px;
  width: 100%;
  transition: background 0.15s, color 0.15s;
}

@media (hover: hover) {
  .notif-expand-btn:hover {
    background: rgba(59, 130, 246, 0.05);
    color: #2563eb;
  }
}

.notif-anim-enter-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.notif-anim-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}

.notif-anim-enter-from {
  opacity: 0;
  transform: scale(0.95) translateY(-4px);
}

.notif-anim-leave-to {
  opacity: 0;
  transform: scale(0.97) translateY(-2px);
}

@media (max-width: 900px) {
  .notif-dropdown {
    right: auto;
    left: 0;
    width: calc(100vw - 28px);
    max-width: 380px;
    transform-origin: top left;
  }

  .notif-anim-enter-from {
    opacity: 0;
    transform: scale(0.95) translateX(-4px);
  }

  .notif-anim-leave-to {
    opacity: 0;
    transform: scale(0.97) translateX(-2px);
  }
}
</style>
