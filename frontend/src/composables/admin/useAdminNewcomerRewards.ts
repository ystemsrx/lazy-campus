import { computed, ref, watch } from 'vue'

import { appConfirm } from '../../components/AppConfirm.vue'
import { fetchAdminUsers } from '../../api/moderation'
import {
  createNewcomerRewardRule,
  deleteNewcomerRewardRule,
  fetchNewcomerRewardLogs,
  fetchNewcomerRewardRules,
  grantNewcomerRewardToUsers,
  toggleNewcomerRewardRule,
  updateNewcomerRewardRule,
} from '../../api/newcomerRewards'
import type { AdminUserItem, NewcomerRewardLogItem, NewcomerRewardRuleItem } from '../../types/api'
import { extractError } from '../../utils/error'
import type { AppToastNotifier } from '../useAppToast'

const LOG_PAGE_SIZE = 20

interface ManualGrantUser {
  id: number
  name: string
  nickname: string | null
  display_name: string
}

export function useAdminNewcomerRewards(showToast: AppToastNotifier) {
  const activeSubTab = ref<'config' | 'history'>('config')

  const rulesLoading = ref(false)
  const rules = ref<NewcomerRewardRuleItem[]>([])
  const rulesTotal = ref(0)

  const logsLoading = ref(false)
  const logs = ref<NewcomerRewardLogItem[]>([])
  const logsTotal = ref(0)
  const logsPage = ref(1)
  const logsTotalPages = computed(() => Math.max(1, Math.ceil(logsTotal.value / LOG_PAGE_SIZE)))
  const logsSearch = ref('')
  const logsTypeFilter = ref('')
  const logsStatusFilter = ref('')

  const manualGrantForm = ref<{
    reward_type: string
    reward_detail: string | number | null
  }>({
    reward_type: 'agent_usage',
    reward_detail: '',
  })
  const manualGrantUserSearchQuery = ref('')
  const manualGrantUserSearchResults = ref<AdminUserItem[]>([])
  const manualGrantSelectedUsers = ref<ManualGrantUser[]>([])
  const manualGrantSearching = ref(false)
  const manualGrantSubmitting = ref(false)

  const isModalOpen = ref(false)
  const editingRule = ref<NewcomerRewardRuleItem | null>(null)
  const formSaving = ref(false)
  const formData = ref<{
    reward_type: string
    reward_detail: string | number | null
    start_time: string
    end_time: string
  }>({
    reward_type: 'agent_usage',
    reward_detail: '',
    start_time: '',
    end_time: '',
  })

  async function loadRules() {
    rulesLoading.value = true
    try {
      const data = await fetchNewcomerRewardRules({ page: 1, page_size: 100 })
      rules.value = data.items
      rulesTotal.value = data.total
    } catch (error: unknown) {
      showToast(extractError(error, '加载奖励规则失败'), 'error')
    } finally {
      rulesLoading.value = false
    }
  }

  async function loadLogs() {
    logsLoading.value = true
    try {
      const data = await fetchNewcomerRewardLogs({
        page: logsPage.value,
        page_size: LOG_PAGE_SIZE,
        reward_type: logsTypeFilter.value || undefined,
        status: logsStatusFilter.value || undefined,
        q: logsSearch.value.trim() || undefined,
      })
      logs.value = data.items
      logsTotal.value = data.total
    } catch (error: unknown) {
      showToast(extractError(error, '加载发放记录失败'), 'error')
    } finally {
      logsLoading.value = false
    }
  }

  async function searchManualGrantUsers(q: string) {
    manualGrantSearching.value = true
    try {
      const res = await fetchAdminUsers({ q, page_size: 8 })
      manualGrantUserSearchResults.value = res.items.filter(
        (u) => !manualGrantSelectedUsers.value.some((s) => s.id === u.id),
      )
    } catch {
      manualGrantUserSearchResults.value = []
    } finally {
      manualGrantSearching.value = false
    }
  }

  function addManualGrantUser(user: AdminUserItem) {
    if (manualGrantSelectedUsers.value.some((u) => u.id === user.id)) return
    manualGrantSelectedUsers.value.push({
      id: user.id,
      name: user.name,
      nickname: user.nickname,
      display_name: user.display_name,
    })
    manualGrantUserSearchResults.value = manualGrantUserSearchResults.value.filter((u) => u.id !== user.id)
    manualGrantUserSearchQuery.value = ''
  }

  function removeManualGrantUser(userId: number) {
    manualGrantSelectedUsers.value = manualGrantSelectedUsers.value.filter((u) => u.id !== userId)
  }

  function formatManualGrantUserLabel(user: ManualGrantUser) {
    if (user.nickname && user.nickname !== user.name) return `${user.nickname}（${user.name}）`
    return user.name
  }

  async function submitManualGrant() {
    const rewardType = (manualGrantForm.value.reward_type || '').trim()
    const rewardDetail = String(manualGrantForm.value.reward_detail ?? '').trim()
    if (!rewardType) {
      showToast('请先选择奖励类型', 'warning')
      return false
    }
    if (!rewardDetail) {
      showToast('请填写奖励详情', 'warning')
      return false
    }
    if (rewardType === 'agent_usage') {
      const num = Number(rewardDetail)
      if (!Number.isFinite(num) || num <= 0 || !Number.isInteger(num)) {
        showToast('代理使用次数必须为正整数', 'warning')
        return false
      }
    }

    const userIds = manualGrantSelectedUsers.value.map((u) => u.id)
    if (!userIds.length) {
      showToast('请至少选择一个用户', 'warning')
      return false
    }
    if (userIds.length > 200) {
      showToast('单次最多发放给 200 位用户', 'warning')
      return false
    }

    manualGrantSubmitting.value = true
    try {
      const result = await grantNewcomerRewardToUsers({
        reward_type: rewardType,
        reward_detail: rewardDetail,
        user_ids: userIds,
      })

      const messageParts = [`成功 ${result.success_count} 人`]
      if (result.failed_count > 0) messageParts.push(`失败 ${result.failed_count} 人`)
      if (result.missing_user_ids.length > 0) messageParts.push(`未找到 ${result.missing_user_ids.length} 人`)
      const hasWarning = result.failed_count > 0 || result.missing_user_ids.length > 0
      showToast(`发放完成：${messageParts.join('，')}`, hasWarning ? 'warning' : 'success')

      manualGrantSelectedUsers.value = []
      manualGrantUserSearchQuery.value = ''
      manualGrantUserSearchResults.value = []
      manualGrantForm.value = {
        reward_type: 'agent_usage',
        reward_detail: '',
      }
      logsPage.value = 1
      await loadLogs()
      return true
    } catch (error: unknown) {
      showToast(extractError(error, '奖励发放失败'), 'error')
      return false
    } finally {
      manualGrantSubmitting.value = false
    }
  }

  function openAddModal() {
    editingRule.value = null
    formData.value = {
      reward_type: 'agent_usage',
      reward_detail: '',
      start_time: '',
      end_time: '',
    }
    isModalOpen.value = true
  }

  function openEditModal(rule: NewcomerRewardRuleItem) {
    editingRule.value = rule
    formData.value = {
      reward_type: rule.reward_type,
      reward_detail: rule.reward_detail,
      start_time: rule.start_time ? rule.start_time.slice(0, 10) : '',
      end_time: rule.end_time ? rule.end_time.slice(0, 10) : '',
    }
    isModalOpen.value = true
  }

  function closeModal() {
    isModalOpen.value = false
  }

  function normalizeRewardDetail(detail: string | number | null) {
    if (detail === null || detail === undefined) return ''
    return String(detail).trim()
  }

  async function saveRule() {
    const detail = normalizeRewardDetail(formData.value.reward_detail)
    if (!detail) {
      showToast('请填写奖励详情', 'warning')
      return
    }

    if (formData.value.reward_type === 'agent_usage') {
      const num = Number(detail)
      if (!Number.isFinite(num) || num <= 0 || !Number.isInteger(num)) {
        showToast('代理使用次数必须为正整数', 'warning')
        return
      }
    }

    formSaving.value = true
    try {
      if (editingRule.value) {
        await updateNewcomerRewardRule(editingRule.value.id, {
          reward_type: formData.value.reward_type,
          reward_detail: detail,
          start_time: formData.value.start_time || null,
          end_time: formData.value.end_time || null,
        })
        showToast('规则修改成功', 'success')
      } else {
        await createNewcomerRewardRule({
          reward_type: formData.value.reward_type,
          reward_detail: detail,
          start_time: formData.value.start_time || null,
          end_time: formData.value.end_time || null,
        })
        showToast('新规则创建成功', 'success')
      }
      isModalOpen.value = false
      await loadRules()
    } catch (error: unknown) {
      showToast(extractError(error, '保存规则失败'), 'error')
    } finally {
      formSaving.value = false
    }
  }

  async function handleToggleRule(rule: NewcomerRewardRuleItem) {
    try {
      const updated = await toggleNewcomerRewardRule(rule.id)
      const idx = rules.value.findIndex((r) => r.id === rule.id)
      if (idx !== -1) rules.value[idx] = updated
      showToast('规则状态已更新', 'success')
    } catch (error: unknown) {
      showToast(extractError(error, '切换状态失败'), 'error')
    }
  }

  async function handleDeleteRule(rule: NewcomerRewardRuleItem) {
    const yes = await appConfirm({
      title: '确认删除',
      message: `确定要删除此奖励规则吗？删除后将不可恢复。`,
      type: 'danger',
      confirmText: '删除',
    })
    if (!yes) return

    try {
      await deleteNewcomerRewardRule(rule.id)
      showToast('规则已删除', 'success')
      await loadRules()
    } catch (error: unknown) {
      showToast(extractError(error, '删除规则失败'), 'error')
    }
  }

  async function bootstrap() {
    await Promise.all([loadRules(), loadLogs()])
  }

  let logSearchTimer = 0
  let manualGrantUserSearchTimer = 0
  watch(logsSearch, () => {
    clearTimeout(logSearchTimer)
    logSearchTimer = window.setTimeout(() => {
      logsPage.value = 1
      loadLogs().catch(() => {})
    }, 300)
  })
  watch(manualGrantUserSearchQuery, (query) => {
    clearTimeout(manualGrantUserSearchTimer)
    const q = query.trim()
    if (!q) {
      manualGrantUserSearchResults.value = []
      return
    }
    manualGrantUserSearchTimer = window.setTimeout(() => {
      searchManualGrantUsers(q).catch(() => {})
    }, 300)
  })
  watch([logsPage, logsTypeFilter, logsStatusFilter], () => {
    loadLogs().catch(() => {})
  })

  return {
    activeSubTab,
    rulesLoading,
    rules,
    rulesTotal,

    logsLoading,
    logs,
    logsTotal,
    logsPage,
    logsTotalPages,
    logsSearch,
    logsTypeFilter,
    logsStatusFilter,
    manualGrantForm,
    manualGrantUserSearchQuery,
    manualGrantUserSearchResults,
    manualGrantSelectedUsers,
    manualGrantSearching,
    manualGrantSubmitting,

    isModalOpen,
    editingRule,
    formSaving,
    formData,

    loadRules,
    loadLogs,
    openAddModal,
    openEditModal,
    closeModal,
    saveRule,
    handleToggleRule,
    handleDeleteRule,
    addManualGrantUser,
    removeManualGrantUser,
    formatManualGrantUserLabel,
    submitManualGrant,
    bootstrap,
  }
}

export type AdminNewcomerRewardsModel = ReturnType<typeof useAdminNewcomerRewards>
