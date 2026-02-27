import { computed, onUnmounted, ref, watch } from 'vue'

import { appConfirm } from '../../components/AppConfirm.vue'
import { batchGrantAgentUsage, fetchAdminAgentConfig, fetchAdminAgentMessages, fetchAdminAgentSessions, updateAdminAgentConfig } from '../../api/agent'
import { fetchAdminUsers } from '../../api/moderation'
import type { AgentAdminSessionItem, AgentMessage, AdminUserItem } from '../../types/api'
import { extractError } from '../../utils/error'
import type { AppToastNotifier } from '../useAppToast'

const USER_PAGE_SIZE = 20
const SESSION_PAGE_SIZE = 20

export function useAdminAgents(showToast: AppToastNotifier) {
  const configLoading = ref(false)
  const configSaving = ref(false)
  const agentEnabled = ref(false)

  const usersLoading = ref(false)
  const userSearch = ref('')
  const userPage = ref(1)
  const userTotal = ref(0)
  const userList = ref<AdminUserItem[]>([])
  const selectedUserIds = ref<number[]>([])
  const userQuotaDraftMap = ref<Record<number, number>>({})
  const rowSavingIds = ref<Set<number>>(new Set())
  const rowQueuedSaveIds = ref<Set<number>>(new Set())
  const quotaSaveTimerMap = ref<Record<number, number>>({})
  const quotaSaveStatus = ref<'idle' | 'saving' | 'saved'>('idle')
  let quotaSavedResetTimer: ReturnType<typeof setTimeout> | null = null

  const usageAmount = ref(1)
  const usageSubmitting = ref(false)

  const sessionsLoading = ref(false)
  const sessionsSearch = ref('')
  const sessionsPage = ref(1)
  const sessionsTotal = ref(0)
  const sessionList = ref<AgentAdminSessionItem[]>([])

  const selectedSessionId = ref<string | null>(null)
  const messagesLoading = ref(false)
  const sessionMessages = ref<AgentMessage[]>([])

  const userTotalPages = computed(() => Math.max(1, Math.ceil(userTotal.value / USER_PAGE_SIZE)))
  const sessionTotalPages = computed(() => Math.max(1, Math.ceil(sessionsTotal.value / SESSION_PAGE_SIZE)))
  const selectedSet = computed(() => new Set(selectedUserIds.value))
  const hasSelectedUsers = computed(() => selectedUserIds.value.length > 0)
  const allCurrentPageSelected = computed(() => {
    if (!userList.value.length) return false
    return userList.value.every((user) => selectedSet.value.has(user.id))
  })

  const activeSession = computed(() => {
    if (!selectedSessionId.value) return null
    return sessionList.value.find((item) => item.session_id === selectedSessionId.value) || null
  })

  function isUserSelected(userId: number) {
    return selectedSet.value.has(userId)
  }

  function toggleUserSelection(userId: number) {
    const set = new Set(selectedUserIds.value)
    if (set.has(userId)) set.delete(userId)
    else set.add(userId)
    selectedUserIds.value = [...set]
  }

  function toggleSelectAllCurrentPage() {
    const currentIds = userList.value.map((u) => u.id)
    const set = new Set(selectedUserIds.value)
    const allChecked = currentIds.every((id) => set.has(id))
    if (allChecked) {
      currentIds.forEach((id) => set.delete(id))
    } else {
      currentIds.forEach((id) => set.add(id))
    }
    selectedUserIds.value = [...set]
  }

  function normalizeQuota(value: unknown) {
    const num = Number(value)
    if (!Number.isFinite(num)) return 0
    return Math.max(0, Math.floor(num))
  }

  function isUserQuotaSaving(userId: number) {
    return rowSavingIds.value.has(userId)
  }

  function isUserQuotaDirty(user: AdminUserItem) {
    return normalizeQuota(userQuotaDraftMap.value[user.id]) !== intUserQuota(user)
  }

  function intUserQuota(user: AdminUserItem) {
    return normalizeQuota(user.agent_usage_remaining)
  }

  function setUserQuotaSaving(userId: number, saving: boolean) {
    const next = new Set(rowSavingIds.value)
    if (saving) next.add(userId)
    else next.delete(userId)
    rowSavingIds.value = next
  }

  function queueUserQuotaSave(userId: number, queued: boolean) {
    const next = new Set(rowQueuedSaveIds.value)
    if (queued) next.add(userId)
    else next.delete(userId)
    rowQueuedSaveIds.value = next
  }

  function clearQuotaSaveTimer(userId: number) {
    const timer = quotaSaveTimerMap.value[userId]
    if (timer) {
      clearTimeout(timer)
      const next = { ...quotaSaveTimerMap.value }
      delete next[userId]
      quotaSaveTimerMap.value = next
    }
  }

  function clearAllQuotaSaveTimers() {
    Object.values(quotaSaveTimerMap.value).forEach((timer) => clearTimeout(timer))
    quotaSaveTimerMap.value = {}
  }

  function hasPendingQuotaWork() {
    return (
      rowSavingIds.value.size > 0
      || rowQueuedSaveIds.value.size > 0
      || Object.keys(quotaSaveTimerMap.value).length > 0
    )
  }

  function clearQuotaSavedResetTimer() {
    if (!quotaSavedResetTimer) return
    clearTimeout(quotaSavedResetTimer)
    quotaSavedResetTimer = null
  }

  function markQuotaSaving() {
    clearQuotaSavedResetTimer()
    quotaSaveStatus.value = 'saving'
  }

  function markQuotaSaved() {
    quotaSaveStatus.value = 'saved'
    clearQuotaSavedResetTimer()
    quotaSavedResetTimer = setTimeout(() => {
      quotaSaveStatus.value = 'idle'
      quotaSavedResetTimer = null
    }, 2000)
  }

  async function loadConfig() {
    configLoading.value = true
    try {
      const data = await fetchAdminAgentConfig()
      agentEnabled.value = data.agent_enabled
    } catch (error: unknown) {
      showToast(extractError(error, '加载代理开关失败'), 'error')
    } finally {
      configLoading.value = false
    }
  }

  async function toggleAgentEnabled() {
    configSaving.value = true
    try {
      const data = await updateAdminAgentConfig({ agent_enabled: !agentEnabled.value })
      agentEnabled.value = data.agent_enabled
      showToast(data.agent_enabled ? 'AI 代理已开启' : 'AI 代理已关闭', 'success')
    } catch (error: unknown) {
      showToast(extractError(error, '更新代理开关失败'), 'error')
    } finally {
      configSaving.value = false
    }
  }

  async function loadUsers() {
    usersLoading.value = true
    try {
      const data = await fetchAdminUsers({
        q: userSearch.value.trim() || undefined,
        page: userPage.value,
        page_size: USER_PAGE_SIZE,
      })
      clearAllQuotaSaveTimers()
      rowQueuedSaveIds.value = new Set()
      quotaSaveStatus.value = 'idle'
      userList.value = data.items
      userTotal.value = data.total
      userQuotaDraftMap.value = Object.fromEntries(
        data.items.map((user) => [user.id, intUserQuota(user)]),
      )
    } catch (error: unknown) {
      showToast(extractError(error, '加载用户失败'), 'error')
    } finally {
      usersLoading.value = false
    }
  }

  async function manageUsage(
    mode: 'grant' | 'set',
    scope: 'selected' | 'all',
  ) {
    const includeAll = scope === 'all'
    const userIds = includeAll ? [] : [...new Set(selectedUserIds.value)]
    if (!includeAll && !userIds.length) {
      showToast('请先选择至少一个用户', 'warning')
      return
    }

    const amount = normalizeQuota(usageAmount.value)
    if (mode === 'grant' && amount <= 0) {
      showToast('发放次数必须大于 0', 'warning')
      return
    }

    if (mode === 'set') {
      const targetText = includeAll ? '所有用户' : `已选的 ${userIds.length} 位用户`
      const yes = await appConfirm({
        title: '确认调整次数',
        message: `将 ${targetText} 的 AI 次数直接调整为 ${amount}，是否继续？`,
        type: 'warning',
        confirmText: '确认调整',
      })
      if (!yes) return
    } else if (includeAll) {
      const yes = await appConfirm({
        title: '确认全员发放',
        message: `将为所有用户增加 ${amount} 次 AI 使用次数，是否继续？`,
        type: 'warning',
        confirmText: '确认发放',
      })
      if (!yes) return
    }

    usageSubmitting.value = true
    try {
      const data = await batchGrantAgentUsage({
        user_ids: userIds,
        amount,
        mode,
        include_all: includeAll,
      })

      if (mode === 'set') {
        showToast(`已将 ${data.updated_user_count} 位用户的次数调整为 ${amount}`, 'success')
      } else {
        showToast(`已为 ${data.updated_user_count} 位用户发放次数`, 'success')
      }

      await loadUsers()
    } catch (error: unknown) {
      showToast(extractError(error, mode === 'set' ? '批量调整失败' : '批量发放失败'), 'error')
    } finally {
      usageSubmitting.value = false
    }
  }

  async function grantUsageToSelected() {
    await manageUsage('grant', 'selected')
  }

  async function adjustUsageForSelected() {
    await manageUsage('set', 'selected')
  }

  async function grantUsageToAll() {
    await manageUsage('grant', 'all')
  }

  async function adjustUsageForAll() {
    await manageUsage('set', 'all')
  }

  async function saveUserQuota(user: AdminUserItem) {
    const userId = user.id
    if (isUserQuotaSaving(userId)) {
      queueUserQuotaSave(userId, true)
      return
    }

    const amount = normalizeQuota(userQuotaDraftMap.value[userId])
    const previousAmount = intUserQuota(user)
    if (amount === previousAmount) {
      if (!hasPendingQuotaWork()) {
        quotaSaveStatus.value = 'idle'
      }
      return
    }

    setUserQuotaSaving(userId, true)
    user.agent_usage_remaining = amount
    let saveSucceeded = false
    try {
      await batchGrantAgentUsage({
        user_ids: [userId],
        amount,
        mode: 'set',
      })
      saveSucceeded = true
    } catch (error: unknown) {
      user.agent_usage_remaining = previousAmount
      userQuotaDraftMap.value = {
        ...userQuotaDraftMap.value,
        [userId]: previousAmount,
      }
      clearQuotaSavedResetTimer()
      quotaSaveStatus.value = 'idle'
      showToast(extractError(error, '自动保存次数失败'), 'error')
    } finally {
      setUserQuotaSaving(userId, false)
      if (rowQueuedSaveIds.value.has(userId)) {
        queueUserQuotaSave(userId, false)
        markQuotaSaving()
        void saveUserQuota(user)
      } else if (hasPendingQuotaWork()) {
        markQuotaSaving()
      } else if (saveSucceeded) {
        markQuotaSaved()
      }
    }
  }

  function scheduleUserQuotaSave(user: AdminUserItem, immediate = false) {
    clearQuotaSaveTimer(user.id)
    markQuotaSaving()
    if (immediate) {
      void saveUserQuota(user)
      return
    }
    const timer = window.setTimeout(() => {
      clearQuotaSaveTimer(user.id)
      void saveUserQuota(user)
    }, 500)
    quotaSaveTimerMap.value = {
      ...quotaSaveTimerMap.value,
      [user.id]: timer,
    }
  }

  function handleUserQuotaInput(user: AdminUserItem) {
    scheduleUserQuotaSave(user, false)
  }

  function handleUserQuotaBlur(user: AdminUserItem) {
    scheduleUserQuotaSave(user, true)
  }

  async function loadSessions() {
    sessionsLoading.value = true
    try {
      const data = await fetchAdminAgentSessions({
        q: sessionsSearch.value.trim() || undefined,
        page: sessionsPage.value,
        page_size: SESSION_PAGE_SIZE,
      })
      sessionList.value = data.items
      sessionsTotal.value = data.total
      if (selectedSessionId.value && !sessionList.value.some((item) => item.session_id === selectedSessionId.value)) {
        selectedSessionId.value = null
        sessionMessages.value = []
      }
    } catch (error: unknown) {
      showToast(extractError(error, '加载代理会话失败'), 'error')
    } finally {
      sessionsLoading.value = false
    }
  }

  async function loadSessionMessages() {
    if (!selectedSessionId.value) {
      sessionMessages.value = []
      return
    }
    messagesLoading.value = true
    try {
      sessionMessages.value = await fetchAdminAgentMessages(selectedSessionId.value, 0)
    } catch (error: unknown) {
      showToast(extractError(error, '加载会话消息失败'), 'error')
    } finally {
      messagesLoading.value = false
    }
  }

  async function selectSession(item: AgentAdminSessionItem) {
    selectedSessionId.value = item.session_id
    await loadSessionMessages()
  }

  async function bootstrap() {
    await Promise.all([loadConfig(), loadUsers(), loadSessions()])
  }

  let userSearchTimer = 0
  watch(userSearch, () => {
    clearTimeout(userSearchTimer)
    userSearchTimer = window.setTimeout(() => {
      userPage.value = 1
      loadUsers().catch(() => {})
    }, 300)
  })
  watch(userPage, () => { loadUsers().catch(() => {}) })

  let sessionSearchTimer = 0
  watch(sessionsSearch, () => {
    clearTimeout(sessionSearchTimer)
    sessionSearchTimer = window.setTimeout(() => {
      sessionsPage.value = 1
      loadSessions().catch(() => {})
    }, 300)
  })
  watch(sessionsPage, () => { loadSessions().catch(() => {}) })

  onUnmounted(() => {
    clearAllQuotaSaveTimers()
    clearQuotaSavedResetTimer()
  })

  return {
    configLoading,
    configSaving,
    agentEnabled,
    usersLoading,
    userSearch,
    userPage,
    userTotal,
    userList,
    userTotalPages,
    allCurrentPageSelected,
    hasSelectedUsers,
    selectedUserIds,
    usageAmount,
    usageSubmitting,
    quotaSaveStatus,
    userQuotaDraftMap,
    sessionsLoading,
    sessionsSearch,
    sessionsPage,
    sessionsTotal,
    sessionTotalPages,
    sessionList,
    selectedSessionId,
    activeSession,
    messagesLoading,
    sessionMessages,
    isUserSelected,
    isUserQuotaSaving,
    isUserQuotaDirty,
    toggleUserSelection,
    toggleSelectAllCurrentPage,
    loadConfig,
    toggleAgentEnabled,
    loadUsers,
    grantUsageToSelected,
    adjustUsageForSelected,
    grantUsageToAll,
    adjustUsageForAll,
    handleUserQuotaInput,
    handleUserQuotaBlur,
    loadSessions,
    selectSession,
    loadSessionMessages,
    bootstrap,
  }
}

export type AdminAgentsModel = ReturnType<typeof useAdminAgents>
