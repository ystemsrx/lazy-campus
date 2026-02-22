import { defineStore } from 'pinia'
import { ref } from 'vue'

import {
  deleteNotification,
  dismissChatNotification,
  fetchNotifications,
  fetchUnreadCount,
  markAllNotificationsRead,
  markNotificationRead,
} from '../api/notifications'
import type { AppNotification } from '../types/api'

export const useNotificationStore = defineStore('notifications', () => {
  const notifications = ref<AppNotification[]>([])
  const unreadCount = ref(0)
  let pollTimer: ReturnType<typeof setInterval> | null = null

  async function load() {
    try {
      notifications.value = await fetchNotifications()
      unreadCount.value = notifications.value.filter(n => !n.is_read).length
    } catch { /* silent */ }
  }

  async function pollCount() {
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
    try {
      await markNotificationRead(id)
      notifications.value = notifications.value.filter(n => n.id !== id)
      unreadCount.value = notifications.value.filter(n => !n.is_read).length
    } catch { /* silent */ }
  }

  async function markAllRead() {
    try {
      await markAllNotificationsRead()
      notifications.value = notifications.value.filter(n => n.dismiss_type !== 'read')
      unreadCount.value = notifications.value.filter(n => !n.is_read).length
    } catch { /* silent */ }
  }

  async function dismissChat(taskId: number) {
    try {
      await dismissChatNotification(taskId)
      notifications.value = notifications.value.filter(
        n => !(n.type === 'chat_message' && n.related_task_id === taskId),
      )
      unreadCount.value = notifications.value.filter(n => !n.is_read).length
    } catch { /* silent */ }
  }

  async function remove(id: number) {
    try {
      await deleteNotification(id)
      notifications.value = notifications.value.filter(n => n.id !== id)
      unreadCount.value = notifications.value.filter(n => !n.is_read).length
    } catch { /* silent */ }
  }

  return {
    notifications,
    unreadCount,
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
