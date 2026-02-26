import { computed, ref, watch } from 'vue'

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

  const grantAmount = ref(1)
  const grantSubmitting = ref(false)

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
      userList.value = data.items
      userTotal.value = data.total
    } catch (error: unknown) {
      showToast(extractError(error, '加载用户失败'), 'error')
    } finally {
      usersLoading.value = false
    }
  }

  async function grantUsageToSelected() {
    const userIds = [...new Set(selectedUserIds.value)]
    if (!userIds.length) {
      showToast('请先选择至少一个用户', 'warning')
      return
    }
    if (grantAmount.value <= 0) {
      showToast('发放次数必须大于 0', 'warning')
      return
    }

    grantSubmitting.value = true
    try {
      const data = await batchGrantAgentUsage({
        user_ids: userIds,
        amount: grantAmount.value,
      })
      showToast(`已为 ${data.updated_user_count} 位用户发放次数`, 'success')
      await loadUsers()
    } catch (error: unknown) {
      showToast(extractError(error, '批量发放失败'), 'error')
    } finally {
      grantSubmitting.value = false
    }
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
    selectedUserIds,
    grantAmount,
    grantSubmitting,
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
    toggleUserSelection,
    toggleSelectAllCurrentPage,
    loadConfig,
    toggleAgentEnabled,
    loadUsers,
    grantUsageToSelected,
    loadSessions,
    selectSession,
    loadSessionMessages,
    bootstrap,
  }
}

export type AdminAgentsModel = ReturnType<typeof useAdminAgents>
