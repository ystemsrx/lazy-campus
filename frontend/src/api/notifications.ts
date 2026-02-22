import api from './client'
import type { AppNotification } from '../types/api'

export async function fetchNotifications() {
  const { data } = await api.get<AppNotification[]>('/notifications')
  return data
}

export async function fetchUnreadCount() {
  const { data } = await api.get<{ count: number }>('/notifications/count')
  return data
}

export async function markNotificationRead(id: number) {
  await api.post(`/notifications/${id}/read`)
}

export async function markAllNotificationsRead() {
  await api.post('/notifications/read-all')
}

export async function dismissChatNotification(taskId: number) {
  await api.post(`/notifications/dismiss-chat/${taskId}`)
}

export async function deleteNotification(id: number) {
  await api.delete(`/notifications/${id}`)
}
