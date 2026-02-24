import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import {
  deleteNotification,
  dismissChatNotification,
  fetchNotifications,
  fetchUnreadCount,
  markAllNotificationsRead,
  markNotificationRead,
} from '../api/notifications'
import type { AppNotification } from '../types/api'

function isPinned(n: AppNotification): boolean {
  return n.dismiss_type !== 'read' && n.dismiss_type !== 'source'
}

function countBadge(list: AppNotification[]): number {
  return list.filter(n => !n.is_read || isPinned(n)).length
}

export const useNotificationStore = defineStore('notifications', () => {
  const notifications = ref<AppNotification[]>([])
  const unreadCount = ref(0)
  let pollTimer: ReturnType<typeof setInterval> | null = null
  let pollSuppressedUntil = 0
  const pendingReads = new Set<number>()
  let pendingAllRead = false

  async function load() {
    try {
      const items = await fetchNotifications()
      for (const item of items) {
        if (pendingAllRead || pendingReads.has(item.id)) {
          item.is_read = true
        }
      }
      notifications.value = items
      unreadCount.value = countBadge(items)
    } catch { /* silent */ }
  }

  async function pollCount() {
    if (Date.now() < pollSuppressedUntil) return
    try {
      const data = await fetchUnreadCount()
      unreadCount.value = data.count
    } catch { /* silent */ }
  }

  function startPolling() {
    if (pollTimer) return
    pollCount()
    pollTimer = setInterval(pollCount, 10000)
  }

  function stopPolling() {
    if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
  }

  function reset() {
    stopPolling()
    notifications.value = []
    unreadCount.value = 0
  }

  async function markRead(id: number) {
    const n = notifications.value.find(x => x.id === id)
    if (!n || n.is_read) return

    n.is_read = true
    if (n.dismiss_type === 'read') {
      notifications.value = notifications.value.filter(x => x.id !== id)
    }
    unreadCount.value = countBadge(notifications.value)
    pollSuppressedUntil = Date.now() + 5000
    pendingReads.add(id)

    try {
      await markNotificationRead(id)
    } catch {
      n.is_read = false
      if (n.dismiss_type === 'read' && !notifications.value.find(x => x.id === id)) {
        notifications.value.push(n)
        notifications.value.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
      }
      unreadCount.value = countBadge(notifications.value)
    } finally {
      pendingReads.delete(id)
    }
  }

  async function markAllRead() {
    const snapshot = notifications.value.map(n => ({ id: n.id, wasRead: n.is_read }))
    notifications.value = notifications.value.filter(n => n.dismiss_type !== 'read')
    notifications.value.forEach(n => { n.is_read = true })
    unreadCount.value = countBadge(notifications.value)
    pollSuppressedUntil = Date.now() + 5000
    pendingAllRead = true

    try {
      await markAllNotificationsRead()
    } catch {
      for (const s of snapshot) {
        const n = notifications.value.find(x => x.id === s.id)
        if (n) n.is_read = s.wasRead
      }
      unreadCount.value = countBadge(notifications.value)
    } finally {
      pendingAllRead = false
    }
  }

  async function dismissChat(taskId: number) {
    try {
      await dismissChatNotification(taskId)
      notifications.value = notifications.value.filter(
        n => !(n.type === 'chat_message' && n.related_task_id === taskId),
      )
      unreadCount.value = countBadge(notifications.value)
    } catch { /* silent */ }
  }

  async function remove(id: number) {
    try {
      await deleteNotification(id)
      notifications.value = notifications.value.filter(n => n.id !== id)
      unreadCount.value = countBadge(notifications.value)
    } catch { /* silent */ }
  }

  const trueUnreadCount = computed(() => notifications.value.filter(n => !n.is_read).length)

  return {
    notifications,
    unreadCount,
    trueUnreadCount,
    load,
    pollCount,
    startPolling,
    stopPolling,
    reset,
    markRead,
    markAllRead,
    dismissChat,
    remove,
  }
})
