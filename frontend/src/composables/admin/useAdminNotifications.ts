import { ref, watch } from 'vue'

import {
  deleteAdminSentNotification,
  fetchAdminSentNotifications,
  fetchAdminUsers,
  pushAdminNotification,
} from '../../api/moderation'
import type { AdminSentNotification, AdminUserItem } from '../../types/api'
import { extractError } from '../../utils/error'
import type { AppToastNotifier } from '../useAppToast'

export interface SelectedUser {
  id: number
  name: string
  nickname: string | null
  display_name: string
}

export function useAdminNotifications(showToast: AppToastNotifier) {
  const pushKind = ref<'notification' | 'announcement'>('notification')
  const title = ref('')
  const description = ref('')
  const targetMode = ref<'all' | 'banned' | 'active' | 'custom'>('all')
  const dismissType = ref<'read' | 'action' | 'persistent'>('read')
  const notificationType = ref('admin_notice')
  const lastNotificationType = ref('admin_notice')
  const sending = ref(false)

  const userSearchQuery = ref('')
  const userSearchResults = ref<AdminUserItem[]>([])
  const selectedUsers = ref<SelectedUser[]>([])
  const searching = ref(false)
  let searchTimer: ReturnType<typeof setTimeout> | null = null

  const sentNotifications = ref<AdminSentNotification[]>([])
  const loadingSent = ref(false)
  const deletingTitle = ref<string | null>(null)

  watch(userSearchQuery, (q) => {
    if (searchTimer) clearTimeout(searchTimer)
    const trimmed = q.trim()
    if (!trimmed) {
      userSearchResults.value = []
      return
    }
    searchTimer = setTimeout(() => searchUsers(trimmed), 300)
  })

  watch(notificationType, (type) => {
    if (type !== 'admin_announcement') {
      lastNotificationType.value = type
    }
  })

  async function searchUsers(q: string) {
    searching.value = true
    try {
      const res = await fetchAdminUsers({ q, page_size: 8 })
      userSearchResults.value = res.items.filter(
        u => !selectedUsers.value.some(s => s.id === u.id),
      )
    } catch {
      userSearchResults.value = []
    } finally {
      searching.value = false
    }
  }

  function addUser(user: AdminUserItem) {
    if (selectedUsers.value.some(s => s.id === user.id)) return
    selectedUsers.value.push({
      id: user.id,
      name: user.name,
      nickname: user.nickname,
      display_name: user.display_name,
    })
    userSearchResults.value = userSearchResults.value.filter(u => u.id !== user.id)
    userSearchQuery.value = ''
  }

  function removeUser(userId: number) {
    selectedUsers.value = selectedUsers.value.filter(u => u.id !== userId)
  }

  function formatUserLabel(u: SelectedUser): string {
    if (u.nickname && u.nickname !== u.name) return `${u.nickname}（${u.name}）`
    return u.name
  }

  function setPushKind(kind: 'notification' | 'announcement') {
    pushKind.value = kind
    if (kind === 'announcement') {
      if (notificationType.value !== 'admin_announcement') {
        lastNotificationType.value = notificationType.value
      }
      notificationType.value = 'admin_announcement'
      return
    }
    if (notificationType.value === 'admin_announcement') {
      notificationType.value = lastNotificationType.value || 'admin_notice'
    }
  }

  async function send() {
    const heading = title.value.trim()
    if (!heading) {
      showToast('请填写通知标题', 'error')
      return
    }
    const body = description.value.trim()
    if (pushKind.value === 'announcement' && !body) {
      showToast('请填写公告正文', 'error')
      return
    }

    const userIds = targetMode.value === 'custom'
      ? selectedUsers.value.map(u => u.id)
      : []
    if (targetMode.value === 'custom' && userIds.length === 0) {
      showToast('请选择至少一个目标用户', 'error')
      return
    }

    sending.value = true
    try {
      const result = await pushAdminNotification({
        title: heading,
        description: body,
        user_ids: userIds,
        include_all: targetMode.value === 'all',
        include_banned: targetMode.value === 'banned',
        include_recent_active: targetMode.value === 'active',
        dismiss_type: dismissType.value,
        type: pushKind.value === 'announcement' ? 'admin_announcement' : notificationType.value,
      })
      showToast(`推送成功，已发送给 ${result.sent_count} 位用户`, 'success')
      title.value = ''
      description.value = ''
      await loadSentNotifications()
    } catch (error: unknown) {
      showToast(extractError(error, '推送通知失败'), 'error')
    } finally {
      sending.value = false
    }
  }

  async function loadSentNotifications() {
    loadingSent.value = true
    try {
      sentNotifications.value = await fetchAdminSentNotifications()
    } catch {
      // silently fail
    } finally {
      loadingSent.value = false
    }
  }

  async function deleteSentNotification(item: AdminSentNotification) {
    deletingTitle.value = item.title
    try {
      await deleteAdminSentNotification(item.title, item.type)
      sentNotifications.value = sentNotifications.value.filter(
        n => !(n.title === item.title && n.type === item.type),
      )
      showToast('已删除该批次通知', 'success')
    } catch (error: unknown) {
      showToast(extractError(error, '删除失败'), 'error')
    } finally {
      deletingTitle.value = null
    }
  }

  return {
    pushKind,
    title,
    description,
    targetMode,
    dismissType,
    notificationType,
    sending,
    userSearchQuery,
    userSearchResults,
    selectedUsers,
    searching,
    sentNotifications,
    loadingSent,
    deletingTitle,
    addUser,
    removeUser,
    formatUserLabel,
    setPushKind,
    send,
    loadSentNotifications,
    deleteSentNotification,
  }
}

export type AdminNotificationsModel = ReturnType<typeof useAdminNotifications>
