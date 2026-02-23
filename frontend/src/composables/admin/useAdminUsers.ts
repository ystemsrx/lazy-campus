import { computed, onUnmounted, reactive, ref, watch } from 'vue'

import {
  addAdminUserBlacklist,
  banUser,
  fetchAdminTasks,
  fetchAdminUserBlacklist,
  fetchAdminUserProfile,
  fetchAdminUsers,
  removeAdminUserBlacklist,
  updateAdminUserProfile,
} from '../../api/moderation'
import type { AdminBlacklistItem, AdminTaskItem, AdminUserItem, AdminUserProfile } from '../../types/api'
import { extractError } from '../../utils/error'
import { localToUTC, utcToLocal } from '../../utils/time'
import type { AppToastNotifier } from '../useAppToast'

export type ProfileSaveStatus = 'idle' | 'saving' | 'saved'

const PAGE_SIZE = 20

interface AdminUserEditForm {
  name: string
  nickname: string
  email: string
  gender: 'male' | 'female' | ''
  role: 'user' | 'admin'
  is_active: boolean
  is_banned: boolean
  ban_publish: boolean
  ban_accept: boolean
  ban_contact: boolean
  ban_reason: string
  ban_count: number
  blocked_by_count: number
  ban_until_local: string
  worker_enabled: boolean
  worker_bio: string
  worker_min_price: string
  worker_max_price: string
  worker_phone: string
  worker_wechat: string
  worker_show_contact: boolean
  worker_skill_tag_ids_text: string
}

function toForm(profile: AdminUserProfile): AdminUserEditForm {
  return {
    name: profile.name || '',
    nickname: profile.nickname || '',
    email: profile.email || '',
    gender: profile.gender || '',
    role: profile.role,
    is_active: profile.is_active,
    is_banned: profile.is_banned,
    ban_publish: profile.ban_publish,
    ban_accept: profile.ban_accept,
    ban_contact: profile.ban_contact,
    ban_reason: profile.ban_reason || '',
    ban_count: profile.ban_count || 0,
    blocked_by_count: profile.blocked_by_count || 0,
    ban_until_local: profile.ban_until ? utcToLocal(profile.ban_until) : '',
    worker_enabled: profile.worker_enabled,
    worker_bio: profile.worker_bio || '',
    worker_min_price: profile.worker_min_price != null ? String(profile.worker_min_price) : '',
    worker_max_price: profile.worker_max_price != null ? String(profile.worker_max_price) : '',
    worker_phone: profile.worker_phone || '',
    worker_wechat: profile.worker_wechat || '',
    worker_show_contact: profile.worker_show_contact,
    worker_skill_tag_ids_text: profile.worker_skill_ids.join(','),
  }
}

function parseSkillIds(text: string): number[] {
  return text
    .split(/[,，\s]+/)
    .map(s => Number(s.trim()))
    .filter(n => Number.isFinite(n) && n > 0)
}

function toNullableNumber(text: string): number | null {
  const trimmed = text.trim()
  if (!trimmed) return null
  const n = Number(trimmed)
  if (!Number.isFinite(n)) return null
  return n
}

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

  const profileOpen = ref(false)
  const profileLoading = ref(false)
  const profileSaving = ref(false)
  const selectedProfile = ref<AdminUserProfile | null>(null)
  const blacklistItems = ref<AdminBlacklistItem[]>([])
  const blacklistLoading = ref(false)
  const blacklistSubmitting = ref(false)
  const blacklistAddUserId = ref('')
  const blacklistSearchQuery = ref('')
  const blacklistSearchResults = ref<AdminUserItem[]>([])
  const blacklistSearchLoading = ref(false)
  const blacklistSearchOpen = ref(false)

  const profileDataLoaded = ref(false)
  const profileSaveStatus = ref<ProfileSaveStatus>('idle')
  let profileAutosaveTimer: ReturnType<typeof setTimeout> | null = null
  let savedResetTimer: ReturnType<typeof setTimeout> | null = null

  const profileTasks = ref<AdminTaskItem[]>([])
  const profileTasksLoading = ref(false)
  const profileTaskTab = ref<'published' | 'accepted'>('published')

  const profileForm = reactive<AdminUserEditForm>({
    name: '',
    nickname: '',
    email: '',
    gender: '',
    role: 'user',
    is_active: true,
    is_banned: false,
    ban_publish: false,
    ban_accept: false,
    ban_contact: false,
    ban_reason: '',
    ban_count: 0,
    blocked_by_count: 0,
    ban_until_local: '',
    worker_enabled: false,
    worker_bio: '',
    worker_min_price: '',
    worker_max_price: '',
    worker_phone: '',
    worker_wechat: '',
    worker_show_contact: true,
    worker_skill_tag_ids_text: '',
  })

  const totalPages = computed(() => Math.max(1, Math.ceil(userTotal.value / PAGE_SIZE)))

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

  async function loadUsers() {
    userLoading.value = true
    try {
      const res = await fetchAdminUsers({
        q: userSearch.value.trim() || undefined,
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
    if (page < 1 || page > totalPages.value) return
    userPage.value = page
  }

  function openBanModal(user: AdminUserItem) {
    banTargetUser.value = user
    showBanModal.value = true
  }

  function closeBanModal() {
    showBanModal.value = false
  }

  async function confirmBan(payload: { ban_types: string[]; ban_days: number | null; admin_notes: string }) {
    if (!banTargetUser.value) return
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
      showToast('用户限制已更新', 'success')
      showBanModal.value = false
      await loadUsers()
      if (selectedProfile.value && selectedProfile.value.id === banTargetUser.value.id) {
        await loadUserProfile(banTargetUser.value.id)
      }
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
      if (selectedProfile.value && selectedProfile.value.id === user.id) {
        await loadUserProfile(user.id)
      }
    } catch (error: unknown) {
      showToast(extractError(error, '解封失败'), 'error')
    } finally {
      unbanOpenId.value = null
      unbanSubmitting.value = false
    }
  }

  function onClickOutsideUnban(event: MouseEvent) {
    if (unbanOpenId.value === null) return
    const target = event.target as HTMLElement
    if (!target.closest('.av-unban-wrap')) {
      unbanOpenId.value = null
    }
  }

  async function loadUserProfile(userId: number) {
    profileDataLoaded.value = false
    profileLoading.value = true
    try {
      const [profile, bl] = await Promise.all([
        fetchAdminUserProfile(userId),
        fetchAdminUserBlacklist(userId),
      ])
      selectedProfile.value = profile
      Object.assign(profileForm, toForm(profile))
      blacklistItems.value = bl
      profileTaskTab.value = 'published'
      await loadProfileTasks()
    } catch (error: unknown) {
      showToast(extractError(error, '加载用户画像失败'), 'error')
    } finally {
      profileLoading.value = false
      profileDataLoaded.value = true
    }
  }

  async function openUserProfile(user: AdminUserItem) {
    profileOpen.value = true
    await loadUserProfile(user.id)
  }

  function closeUserProfile() {
    profileOpen.value = false
  }

  async function saveUserProfile() {
    if (profileAutosaveTimer) clearTimeout(profileAutosaveTimer)
    await doAutosave()
  }

  let blSearchDebounce = 0
  watch(blacklistSearchQuery, (q) => {
    clearTimeout(blSearchDebounce)
    if (!q.trim()) {
      blacklistSearchResults.value = []
      blacklistSearchOpen.value = false
      return
    }
    blSearchDebounce = window.setTimeout(async () => {
      blacklistSearchLoading.value = true
      try {
        const res = await fetchAdminUsers({ q: q.trim(), page: 1, page_size: 8 })
        blacklistSearchResults.value = res.items.filter(
          u => selectedProfile.value && u.id !== selectedProfile.value.id,
        )
        blacklistSearchOpen.value = true
      } catch {
        blacklistSearchResults.value = []
      } finally {
        blacklistSearchLoading.value = false
      }
    }, 300)
  })

  async function selectBlacklistUser(user: AdminUserItem) {
    blacklistSearchOpen.value = false
    blacklistSearchQuery.value = ''
    blacklistSearchResults.value = []
    if (!selectedProfile.value) return

    const optimistic: AdminBlacklistItem = {
      blocked_user_id: user.id,
      blocked_display_name: user.display_name,
      blocked_name: user.name !== user.display_name ? user.name : undefined,
      blocked_account: user.account,
      blocked_avatar_url: user.avatar_url,
      reason: null,
      created_at: new Date().toISOString(),
    }
    blacklistItems.value = [...blacklistItems.value, optimistic]

    try {
      blacklistItems.value = await addAdminUserBlacklist(selectedProfile.value.id, {
        blocked_user_id: user.id,
      })
    } catch (error: unknown) {
      blacklistItems.value = blacklistItems.value.filter(i => i.blocked_user_id !== user.id)
      showToast(extractError(error, '添加黑名单失败'), 'error')
    }
  }

  function closeBlacklistSearch() {
    blacklistSearchOpen.value = false
  }

  async function refreshBlacklist() {
    if (!selectedProfile.value) return
    blacklistLoading.value = true
    try {
      blacklistItems.value = await fetchAdminUserBlacklist(selectedProfile.value.id)
    } catch (error: unknown) {
      showToast(extractError(error, '加载黑名单失败'), 'error')
    } finally {
      blacklistLoading.value = false
    }
  }

  async function addBlacklistItem() {
    if (!selectedProfile.value) return
    const blockedId = Number(blacklistAddUserId.value.trim())
    if (!Number.isFinite(blockedId) || blockedId <= 0) {
      showToast('请输入正确的用户 ID', 'error')
      return
    }
    const prev = [...blacklistItems.value]
    const optimistic: AdminBlacklistItem = {
      blocked_user_id: blockedId,
      blocked_display_name: `用户 ${blockedId}`,
      blocked_account: '',
      blocked_avatar_url: null,
      reason: null,
      created_at: new Date().toISOString(),
    }
    blacklistItems.value = [...blacklistItems.value, optimistic]
    blacklistAddUserId.value = ''

    try {
      blacklistItems.value = await addAdminUserBlacklist(selectedProfile.value.id, {
        blocked_user_id: blockedId,
      })
    } catch (error: unknown) {
      blacklistItems.value = prev
      showToast(extractError(error, '添加黑名单失败'), 'error')
    }
  }

  async function removeBlacklistItem(blockedUserId: number) {
    if (!selectedProfile.value) return
    const prev = [...blacklistItems.value]
    blacklistItems.value = blacklistItems.value.filter(i => i.blocked_user_id !== blockedUserId)

    try {
      blacklistItems.value = await removeAdminUserBlacklist(selectedProfile.value.id, blockedUserId)
    } catch (error: unknown) {
      blacklistItems.value = prev
      showToast(extractError(error, '移除黑名单失败'), 'error')
    }
  }

  async function loadProfileTasks() {
    if (!selectedProfile.value) return
    profileTasksLoading.value = true
    try {
      const key = profileTaskTab.value === 'published' ? 'publisher_id' : 'assignee_id'
      const res = await fetchAdminTasks({ [key]: selectedProfile.value.id, page_size: 50 })
      profileTasks.value = res.items
    } catch (error: unknown) {
      showToast(extractError(error, '加载用户任务失败'), 'error')
    } finally {
      profileTasksLoading.value = false
    }
  }

  watch(profileTaskTab, () => {
    loadProfileTasks()
  })

  // 自动保存
  function markSaved() {
    profileSaveStatus.value = 'saved'
    if (savedResetTimer) clearTimeout(savedResetTimer)
    savedResetTimer = setTimeout(() => {
      profileSaveStatus.value = 'idle'
    }, 2000)
  }

  async function doAutosave() {
    if (!selectedProfile.value) return
    profileSaving.value = true
    try {
      const payload = {
        name: profileForm.name.trim() || undefined,
        nickname: profileForm.nickname.trim() || null,
        email: profileForm.email.trim() || null,
        gender: profileForm.gender || null,
        role: profileForm.role,
        is_active: profileForm.is_active,
        is_banned: profileForm.is_banned,
        ban_publish: profileForm.ban_publish,
        ban_accept: profileForm.ban_accept,
        ban_contact: profileForm.ban_contact,
        ban_reason: profileForm.ban_reason.trim() || null,
        ban_count: Number(profileForm.ban_count) || 0,
        blocked_by_count: Number(profileForm.blocked_by_count) || 0,
        ban_until: profileForm.ban_until_local ? localToUTC(profileForm.ban_until_local) : null,
        worker_enabled: profileForm.worker_enabled,
        worker_bio: profileForm.worker_bio.trim() || null,
        worker_min_price: toNullableNumber(profileForm.worker_min_price),
        worker_max_price: toNullableNumber(profileForm.worker_max_price),
        worker_phone: profileForm.worker_phone.trim() || null,
        worker_wechat: profileForm.worker_wechat.trim() || null,
        worker_show_contact: profileForm.worker_show_contact,
        worker_skill_tag_ids: parseSkillIds(profileForm.worker_skill_tag_ids_text),
      }
      const updated = await updateAdminUserProfile(selectedProfile.value.id, payload)
      selectedProfile.value = updated
      markSaved()
      await loadUsers()
    } catch (error: unknown) {
      profileSaveStatus.value = 'idle'
      showToast(extractError(error, '自动保存失败'), 'error')
    } finally {
      profileSaving.value = false
    }
  }

  watch(
    () => ({ ...profileForm }),
    () => {
      if (!profileDataLoaded.value) return
      profileSaveStatus.value = 'saving'
      if (profileAutosaveTimer) clearTimeout(profileAutosaveTimer)
      profileAutosaveTimer = setTimeout(doAutosave, 600)
    },
    { deep: true },
  )

  onUnmounted(() => {
    clearTimeout(searchDebounce)
    clearTimeout(blSearchDebounce)
    if (profileAutosaveTimer) clearTimeout(profileAutosaveTimer)
    if (savedResetTimer) clearTimeout(savedResetTimer)
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
    profileOpen,
    profileLoading,
    profileSaving,
    selectedProfile,
    profileForm,
    openUserProfile,
    closeUserProfile,
    saveUserProfile,
    profileSaveStatus,
    profileTasks,
    profileTasksLoading,
    profileTaskTab,
    loadProfileTasks,
    blacklistItems,
    blacklistLoading,
    blacklistSubmitting,
    blacklistAddUserId,
    blacklistSearchQuery,
    blacklistSearchResults,
    blacklistSearchLoading,
    blacklistSearchOpen,
    selectBlacklistUser,
    closeBlacklistSearch,
    refreshBlacklist,
    addBlacklistItem,
    removeBlacklistItem,
  }
}

export type AdminUsersModel = ReturnType<typeof useAdminUsers>
