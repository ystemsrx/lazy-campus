import { ref } from 'vue'

import { pushAdminNotification } from '../../api/moderation'
import { extractError } from '../../utils/error'
import type { AppToastNotifier } from '../useAppToast'

export function useAdminNotifications(showToast: AppToastNotifier) {
  const title = ref('')
  const description = ref('')
  const targetMode = ref<'all' | 'banned' | 'active' | 'custom'>('all')
  const customUserIds = ref('')
  const dismissType = ref<'read' | 'action' | 'source' | 'persistent'>('read')
  const sending = ref(false)
  const lastSentCount = ref(0)

  function parseCustomUserIds(): number[] {
    return customUserIds.value
      .split(/[,，\s]+/)
      .map(s => Number(s.trim()))
      .filter(n => Number.isFinite(n) && n > 0)
  }

  async function send() {
    const heading = title.value.trim()
    if (!heading) {
      showToast('请填写通知标题', 'error')
      return
    }

    const userIds = targetMode.value === 'custom' ? parseCustomUserIds() : []
    if (targetMode.value === 'custom' && userIds.length === 0) {
      showToast('请填写至少一个用户 ID', 'error')
      return
    }

    sending.value = true
    try {
      const result = await pushAdminNotification({
        title: heading,
        description: description.value.trim(),
        user_ids: userIds,
        include_all: targetMode.value === 'all',
        include_banned: targetMode.value === 'banned',
        include_recent_active: targetMode.value === 'active',
        dismiss_type: dismissType.value,
        type: 'admin_notice',
      })
      lastSentCount.value = result.sent_count
      showToast(`推送成功，已发送给 ${result.sent_count} 位用户`, 'success')
    } catch (error: unknown) {
      showToast(extractError(error, '推送通知失败'), 'error')
    } finally {
      sending.value = false
    }
  }

  return {
    title,
    description,
    targetMode,
    customUserIds,
    dismissType,
    sending,
    lastSentCount,
    send,
  }
}

export type AdminNotificationsModel = ReturnType<typeof useAdminNotifications>
