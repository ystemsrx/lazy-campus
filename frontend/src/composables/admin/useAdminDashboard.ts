import { ref } from 'vue'

import {
  fetchAdminDashboard,
  fetchRegistrationSetting,
  updateRegistrationSetting,
} from '../../api/moderation'
import { extractError } from '../../utils/error'
import type { AdminToastType } from './useAdminToast'

export type AdminNotifier = (text: string, type?: AdminToastType) => void

export interface AdminDashboardStats {
  total_users?: number
  active_workers?: number
  total_tasks?: number
  completed_tasks?: number
  pending_reports?: number
  completion_rate?: string
  registration_enabled?: boolean
  [key: string]: unknown
}

export function useAdminDashboard(showToast: AdminNotifier) {
  const dashboard = ref<AdminDashboardStats>({})
  const registrationEnabled = ref(true)
  const savingRegistration = ref(false)

  async function loadDashboard() {
    const [dashboardData, registration] = await Promise.all([
      fetchAdminDashboard(),
      fetchRegistrationSetting(),
    ])
    dashboard.value = dashboardData
    registrationEnabled.value = registration.registration_enabled
  }

  async function handleToggleRegistration() {
    savingRegistration.value = true
    try {
      const nextValue = !registrationEnabled.value
      const data = await updateRegistrationSetting({
        registration_enabled: nextValue,
      })
      registrationEnabled.value = data.registration_enabled
      dashboard.value.registration_enabled = data.registration_enabled
      showToast(
        data.registration_enabled ? '已开启用户注册' : '已关闭用户注册',
        'success',
      )
    } catch (error: unknown) {
      showToast(extractError(error, '更新注册开关失败'), 'error')
    } finally {
      savingRegistration.value = false
    }
  }

  return {
    dashboard,
    registrationEnabled,
    savingRegistration,
    loadDashboard,
    handleToggleRegistration,
  }
}

export type AdminDashboardModel = ReturnType<typeof useAdminDashboard>
