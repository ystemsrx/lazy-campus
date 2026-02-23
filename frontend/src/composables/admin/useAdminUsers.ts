import { computed, onUnmounted, ref, watch } from 'vue'

import { banUser, fetchAdminUsers } from '../../api/moderation'
import type { AdminUserItem } from '../../types/api'
import { extractError } from '../../utils/error'
import type { AppToastNotifier } from '../useAppToast'

const PAGE_SIZE = 20

export function useAdminUsers(showToast: AppToastNotifier) {
  const userSearch = ref('')
  const userPage = ref(1)
  const userTotal = ref(0)
  const userList = ref<AdminUserItem[]>([])
  const userLoading = ref(false)

  const showBanModal = ref(false)
  const banTargetUser = ref<AdminUserItem | null>(null)
  const banSubmitting = ref(false)

  const unbanOpenId = ref<number | null>(null)
  const unbanSubmitting = ref(false)

  const totalPages = computed(() => Math.max(1, Math.ceil(userTotal.value / PAGE_SIZE)))

  async function loadUsers() {
    userLoading.value = true
    try {
      const res = await fetchAdminUsers({
        q: userSearch.value || undefined,
        page: userPage.value,
        page_size: PAGE_SIZE,
      })
      userList.value = res.items
      userTotal.value = res.total
    } catch (error: unknown) {
      showToast(extractError(error, '加载用户列表失败'), 'error')
    } finally {
      userLoading.value = false
    }
  }

  let searchDebounce = 0
  watch(userSearch, () => {
    clearTimeout(searchDebounce)
    searchDebounce = window.setTimeout(() => {
      userPage.value = 1
      loadUsers()
    }, 300)
  })

  watch(userPage, () => {
    loadUsers()
  })

  function goPage(page: number) {
    if (page < 1 || page > totalPages.value) {
      return
    }
    userPage.value = page
  }

  const banPreselectedTypes = computed<string[]>(() => {
    const u = banTargetUser.value
    if (!u) return ['login']
    const types: string[] = []
    if (u.is_banned) types.push('login')
    if (u.ban_publish) types.push('publish')
    if (u.ban_accept) types.push('accept')
    if (u.ban_contact) types.push('contact')
    return types.length ? types : ['login']
  })

  function openBanModal(user: AdminUserItem) {
    banTargetUser.value = user
    showBanModal.value = true
  }

  function closeBanModal() {
    showBanModal.value = false
  }

  async function confirmBan(payload: { ban_types: string[]; ban_days: number | null; admin_notes: string }) {
    if (!banTargetUser.value) {
      return
    }
    banSubmitting.value = true
    try {
      const result = await banUser(banTargetUser.value.id, {
        banned: true,
        reason: payload.admin_notes || undefined,
        ban_types: payload.ban_types,
        ban_days: payload.ban_days,
      })
      banTargetUser.value.is_banned = payload.ban_types.includes('login')
      banTargetUser.value.ban_publish = payload.ban_types.includes('publish')
      banTargetUser.value.ban_accept = payload.ban_types.includes('accept')
      banTargetUser.value.ban_contact = payload.ban_types.includes('contact')
      banTargetUser.value.ban_reason = payload.admin_notes || null
      banTargetUser.value.ban_until = result.ban_until ?? null
      banTargetUser.value.ban_count = result.ban_count ?? banTargetUser.value.ban_count
      showToast('用户已封禁', 'success')
      showBanModal.value = false
    } catch (error: unknown) {
      showToast(extractError(error, '封禁失败'), 'error')
    } finally {
      banSubmitting.value = false
    }
  }

  function toggleUnbanMenu(userId: number) {
    unbanOpenId.value = unbanOpenId.value === userId ? null : userId
  }

  async function confirmUnban(user: AdminUserItem, innocent: boolean) {
    unbanSubmitting.value = true
    try {
      await banUser(user.id, { banned: false, innocent })
      user.is_banned = false
      user.ban_reason = null
      user.ban_publish = false
      user.ban_accept = false
      user.ban_contact = false
      user.ban_until = null
      if (innocent && user.ban_count > 0) {
        user.ban_count -= 1
      }
      showToast(innocent ? '已无责解封' : '已有责解封', 'success')
    } catch (error: unknown) {
      showToast(extractError(error, '解封失败'), 'error')
    } finally {
      unbanOpenId.value = null
      unbanSubmitting.value = false
    }
  }

  function onClickOutsideUnban(event: MouseEvent) {
    if (unbanOpenId.value === null) {
      return
    }
    const target = event.target as HTMLElement
    if (!target.closest('.av-unban-wrap')) {
      unbanOpenId.value = null
    }
  }

  onUnmounted(() => {
    clearTimeout(searchDebounce)
  })

  return {
    userSearch,
    userPage,
    userTotal,
    userList,
    userLoading,
    totalPages,
    loadUsers,
    goPage,
    showBanModal,
    banTargetUser,
    banPreselectedTypes,
    banSubmitting,
    openBanModal,
    closeBanModal,
    confirmBan,
    unbanOpenId,
    unbanSubmitting,
    toggleUnbanMenu,
    confirmUnban,
    onClickOutsideUnban,
  }
}

export type AdminUsersModel = ReturnType<typeof useAdminUsers>
