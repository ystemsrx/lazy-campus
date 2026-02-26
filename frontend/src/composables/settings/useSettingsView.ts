import { computed, nextTick, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { fetchCategories } from '../../api/tasks'
import {
  deletePaymentQr,
  fetchMyWorkerProfile,
  updateProfile,
  updateWorkerProfile,
  uploadAvatar,
  uploadPaymentQr,
} from '../../api/users'
import { useAuthStore } from '../../stores/auth'
import type { Category } from '../../types/api'
import { extractError } from '../../utils/error'
import { useAppToast } from '../useAppToast'
import { useSettingsAutosave } from './useSettingsAutosave'
import { useSettingsTabs } from './useSettingsTabs'
import {
  createProfileForm,
  createWorkerForm,
  type SettingsTab,
  type ProfileForm,
  type WorkerForm,
} from './types'

export function useSettingsView() {
  const router = useRouter()
  const auth = useAuthStore()
  const { toast, showToast, clearToast } = useAppToast()

  const appTitle = import.meta.env.VITE_APP_TITLE || '校园任务平台'

  const me = computed(() => auth.user)
  const isAuthenticated = computed(() => auth.isAuthenticated)
  const displayName = computed(() => auth.displayName)

  const loading = ref(true)
  const categories = ref<Category[]>([])
  const activeTab = ref<SettingsTab>('profile')
  const avatarUploading = ref(false)
  const paymentQrUploading = ref(false)
  const paymentQrDeleting = ref(false)
  const isDataLoaded = ref(false)

  const profileForm = ref<ProfileForm>(createProfileForm())
  const workerForm = ref<WorkerForm>(createWorkerForm())

  async function saveProfile() {
    const updated = await updateProfile({
      email: profileForm.value.email,
      gender: profileForm.value.gender as 'male' | 'female',
      nickname: profileForm.value.nickname || undefined,
    })

    auth.user = updated
    auth.displayName = updated.nickname || updated.name
    localStorage.setItem('display_name', auth.displayName)
  }

  async function saveWorker() {
    await updateWorkerProfile({
      enabled: workerForm.value.enabled,
      skill_tag_ids: workerForm.value.skill_tag_ids,
      min_price: null,
      max_price: null,
      bio: workerForm.value.bio || null,
      phone: workerForm.value.phone || null,
      wechat: workerForm.value.wechat || null,
      show_contact: workerForm.value.show_contact,
    })
  }

  const { saveStatus } = useSettingsAutosave({
    profileForm,
    workerForm,
    isDataLoaded,
    saveProfile,
    saveWorker,
    onError: (error) => {
      showToast(extractError(error, '保存失败'), 'error')
    },
  })

  const { indicatorStyle, updateIndicator, setTabRef } = useSettingsTabs(activeTab)

  function logout() {
    auth.logout()
    router.push('/login')
  }

  function openHome() {
    router.push({ path: '/', query: { publish: '1' } })
  }

  function openMyPanel() {
    router.push('/tasks')
  }

  function openSettings() {
    router.push('/settings')
  }

  function goLogin() {
    router.push('/login')
  }

  function handleHeaderTabChange(tab: 'hall' | 'workers' | null) {
    router.push({
      path: '/',
      query: tab === 'workers' ? { tab: 'workers' } : {},
    })
  }

  function toggleSkillTag(id: number) {
    const ids = workerForm.value.skill_tag_ids
    const idx = ids.indexOf(id)
    if (idx >= 0) {
      ids.splice(idx, 1)
      return
    }

    if (ids.length < 5) {
      ids.push(id)
    }
  }

  async function handleAvatarUpload(event: Event) {
    const input = event.target as HTMLInputElement
    const file = input.files?.[0]
    if (!file) return

    avatarUploading.value = true
    try {
      const updated = await uploadAvatar(file)
      auth.user = updated
      showToast('头像已更新', 'success')
    } catch (error) {
      showToast(extractError(error, '头像上传失败'), 'error')
    } finally {
      avatarUploading.value = false
      input.value = ''
    }
  }

  async function handlePaymentQrUpload(event: Event) {
    const input = event.target as HTMLInputElement
    const file = input.files?.[0]
    if (!file) return

    paymentQrUploading.value = true
    try {
      const updated = await uploadPaymentQr(file)
      auth.user = updated
      showToast('收款码已上传', 'success')
    } catch (error) {
      showToast(extractError(error, '收款码上传失败'), 'error')
    } finally {
      paymentQrUploading.value = false
      input.value = ''
    }
  }

  async function handlePaymentQrDelete() {
    paymentQrDeleting.value = true
    try {
      const updated = await deletePaymentQr()
      auth.user = updated
      showToast('收款码已删除', 'success')
    } catch (error) {
      showToast(extractError(error, '收款码删除失败'), 'error')
    } finally {
      paymentQrDeleting.value = false
    }
  }

  onMounted(async () => {
    try {
      const [cats, workerProfile] = await Promise.all([fetchCategories(), fetchMyWorkerProfile()])
      categories.value = cats
      workerForm.value = {
        enabled: workerProfile.enabled,
        skill_tag_ids: workerProfile.skill_tags.map((tag) => tag.id),
        bio: workerProfile.bio || '',
        phone: workerProfile.phone || '',
        wechat: workerProfile.wechat || '',
        show_contact: workerProfile.show_contact ?? true,
      }
    } catch (error) {
      showToast(extractError(error, '加载失败'), 'error')
    }

    if (me.value) {
      profileForm.value.email = me.value.email || ''
      profileForm.value.nickname = me.value.nickname || ''
      profileForm.value.gender = (me.value.gender as 'male' | 'female') || ''
    }

    loading.value = false

    await nextTick()
    updateIndicator()
    isDataLoaded.value = true
  })

  return {
    appTitle,
    toast,
    showToast,
    clearToast,
    me,
    isAuthenticated,
    displayName,
    loading,
    categories,
    activeTab,
    indicatorStyle,
    setTabRef,
    profileForm,
    workerForm,
    avatarUploading,
    paymentQrUploading,
    paymentQrDeleting,
    saveStatus,
    logout,
    openHome,
    openMyPanel,
    openSettings,
    goLogin,
    handleHeaderTabChange,
    toggleSkillTag,
    handleAvatarUpload,
    handlePaymentQrUpload,
    handlePaymentQrDelete,
  }
}
