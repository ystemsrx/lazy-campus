import { ref } from 'vue'

import {
  fetchAdminDashboard,
  fetchRegistrationSetting,
  updateRegistrationSetting,
} from '../../api/moderation'
import type { AdminDashboardData } from '../../types/api'
import { extractError } from '../../utils/error'
import type { AppToastNotifier } from '../useAppToast'

export function useAdminDashboard(showToast: AppToastNotifier) {
  const dashboard = ref<AdminDashboardData>({
    total_users: 0,
    active_users_24h: 0,
    new_users_7d: 0,
    active_workers: 0,
    total_tasks: 0,
    open_tasks: 0,
    in_progress_tasks: 0,
    under_review_tasks: 0,
    completed_tasks: 0,
    canceled_tasks: 0,
    overdue_open_tasks: 0,
    pinned_tasks: 0,
    urgent_tasks: 0,
    avg_task_price: 0,
    pending_reports: 0,
    approved_reports_7d: 0,
    rejected_reports_7d: 0,
    chat_messages_24h: 0,
    completion_rate: 0,
    registration_enabled: true,
    trends: [],
    top_risk_users: [],
  })
  const trendDays = ref(7)
  const registrationEnabled = ref(true)
  const savingRegistration = ref(false)

  async function loadDashboard(days = trendDays.value) {
    trendDays.value = days
    try {
      const [dashboardData, registration] = await Promise.all([fetchAdminDashboard({ days }), fetchRegistrationSetting()])
      dashboard.value = dashboardData
      registrationEnabled.value = registration.registration_enabled
    } catch (error: unknown) {
      showToast(extractError(error, '加载运营看板失败'), 'error')
      throw error
    }
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
    trendDays,
    registrationEnabled,
    savingRegistration,
    loadDashboard,
    handleToggleRegistration,
  }
}

export type AdminDashboardModel = ReturnType<typeof useAdminDashboard>
