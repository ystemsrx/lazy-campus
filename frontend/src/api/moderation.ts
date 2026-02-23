import api from './client'
import type {
  AdminActionLogListResponse,
  AdminBlacklistItem,
  AdminChatConversationListResponse,
  AdminChatMessage,
  AdminDashboardData,
  AdminPushNotificationResult,
  AdminTaskChatConversationListResponse,
  AdminTaskChatMessage,
  AdminTaskListResponse,
  AdminUserListResponse,
  AdminUserProfile,
  BanContext,
  BlacklistItem,
  Report,
} from '../types/api'

export async function uploadReportImage(blob: Blob): Promise<string> {
  const form = new FormData()
  form.append('file', blob, 'screenshot.webp')
  const { data } = await api.post<{ url: string }>('/uploads/images', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data.url
}

export async function createReport(payload: {
  task_id?: number | null
  reported_user_id: number
  reason: string
  evidence: string
  images?: string[]
}) {
  const { data } = await api.post<Report>('/moderation/reports', payload)
  return data
}

export async function uploadAppealImage(blob: Blob): Promise<string> {
  const form = new FormData()
  form.append('file', blob, 'screenshot.webp')
  const { data } = await api.post<{ url: string }>('/uploads/appeal-images', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data.url
}

export async function createAppeal(payload: {
  account: string
  password: string
  reason: string
  evidence: string
  images?: string[]
}) {
  const { data } = await api.post<Report>('/moderation/appeals', payload)
  return data
}

export async function fetchBanContext(payload: { account: string; password: string }) {
  const { data } = await api.post<BanContext>('/moderation/ban-context', payload)
  return data
}

export async function fetchMyBanContext() {
  const { data } = await api.get<BanContext>('/moderation/me/ban-context')
  return data
}

export async function blockUser(payload: { blocked_user_id: number; reason?: string }) {
  const { data } = await api.post('/moderation/blacklist', payload)
  return data
}

export async function unblockUser(blockedUserId: number) {
  const { data } = await api.delete(`/moderation/blacklist/${blockedUserId}`)
  return data
}

export async function fetchBlacklist() {
  const { data } = await api.get<BlacklistItem[]>('/moderation/blacklist')
  return data
}

export async function checkBlocked(targetUserId: number) {
  const { data } = await api.get<{ is_blocked: boolean }>(`/moderation/blacklist/check/${targetUserId}`)
  return data.is_blocked
}

export async function fetchMyReports() {
  const { data } = await api.get<Report[]>('/moderation/me/reports')
  return data
}

export async function fetchReceivedReports() {
  const { data } = await api.get<Report[]>('/moderation/me/received-reports')
  return data
}

export async function createAuthenticatedAppeal(payload: {
  reason: string
  evidence: string
  images?: string[]
}) {
  const { data } = await api.post<Report>('/moderation/me/appeal', payload)
  return data
}

export async function fetchAdminDashboard(params: { days?: number } = {}) {
  const { data } = await api.get<AdminDashboardData>('/moderation/admin/dashboard', { params })
  return data
}

export async function fetchAdminReports(params: { type?: string; status?: string } = {}) {
  const { data } = await api.get<Report[]>('/moderation/admin/reports', { params })
  return data
}

export async function reviewReport(reportId: number, payload: {
  status: 'pending' | 'approved' | 'rejected'
  admin_notes?: string
  ban_types?: string[]
  ban_days?: number | null
}) {
  const { data } = await api.post<Report>(`/moderation/admin/reports/${reportId}/review`, payload)
  return data
}

export async function fetchTaskSnapshot(taskId: number) {
  const { data } = await api.get(`/moderation/admin/tasks/${taskId}/snapshot`)
  return data
}

export async function fetchReportChatHistory(reportId: number) {
  const { data } = await api.get(`/moderation/admin/reports/${reportId}/chat-history`)
  return data
}

export async function banUser(userId: number, payload: {
  banned: boolean
  reason?: string
  innocent?: boolean
  ban_types?: string[]
  ban_days?: number | null
}) {
  const { data } = await api.post(`/moderation/admin/users/${userId}/ban`, payload)
  return data
}

export async function fetchAdminUsers(params: { q?: string; page?: number; page_size?: number } = {}) {
  const { data } = await api.get<AdminUserListResponse>('/moderation/admin/users', { params })
  return data
}

export async function fetchAdminUserProfile(userId: number) {
  const { data } = await api.get<AdminUserProfile>(`/moderation/admin/users/${userId}/profile`)
  return data
}

export async function updateAdminUserProfile(userId: number, payload: {
  name?: string | null
  nickname?: string | null
  email?: string | null
  gender?: 'male' | 'female' | null
  role?: 'user' | 'admin'
  is_active?: boolean
  is_banned?: boolean
  ban_publish?: boolean
  ban_accept?: boolean
  ban_contact?: boolean
  ban_reason?: string | null
  ban_until?: string | null
  ban_count?: number
  blocked_by_count?: number
  worker_enabled?: boolean
  worker_bio?: string | null
  worker_min_price?: number | null
  worker_max_price?: number | null
  worker_phone?: string | null
  worker_wechat?: string | null
  worker_show_contact?: boolean
  worker_skill_tag_ids?: number[]
}) {
  const { data } = await api.put<AdminUserProfile>(`/moderation/admin/users/${userId}/profile`, payload)
  return data
}

export async function fetchAdminUserBlacklist(userId: number) {
  const { data } = await api.get<AdminBlacklistItem[]>(`/moderation/admin/users/${userId}/blacklist`)
  return data
}

export async function addAdminUserBlacklist(userId: number, payload: { blocked_user_id: number; reason?: string }) {
  const { data } = await api.post<AdminBlacklistItem[]>(`/moderation/admin/users/${userId}/blacklist`, payload)
  return data
}

export async function removeAdminUserBlacklist(userId: number, blockedUserId: number) {
  const { data } = await api.delete<AdminBlacklistItem[]>(`/moderation/admin/users/${userId}/blacklist/${blockedUserId}`)
  return data
}

export async function fetchAdminTasks(params: {
  q?: string
  status?: string
  publisher_id?: number
  assignee_id?: number
  flag?: 'pinned' | 'urgent' | 'flagged'
  deleted?: boolean
  page?: number
  page_size?: number
} = {}) {
  const { data } = await api.get<AdminTaskListResponse>('/moderation/admin/tasks', { params })
  return data
}

export async function operateAdminTask(taskId: number, payload: {
  delete?: boolean
  set_pinned?: boolean
  set_urgent?: boolean
  admin_note?: string | null
}) {
  const { data } = await api.post<{ message: string; deleted: boolean; item?: unknown }>(`/moderation/admin/tasks/${taskId}/operate`, payload)
  return data
}

export async function fetchAdminChatConversations(params: {
  q?: string
  task_id?: number
  user_id?: number
  page?: number
  page_size?: number
} = {}) {
  const { data } = await api.get<AdminChatConversationListResponse>('/moderation/admin/chats', { params })
  return data
}

export async function fetchAdminChatMessages(params: {
  user_a_id: number
  user_b_id: number
  task_id?: number | null
  before_id?: number
  limit?: number
}) {
  const { data } = await api.get<AdminChatMessage[]>('/moderation/admin/chats/messages', { params })
  return data
}

export async function fetchAdminTaskChatConversations(params: {
  q?: string
  task_id?: number
  page?: number
  page_size?: number
} = {}) {
  const { data } = await api.get<AdminTaskChatConversationListResponse>('/moderation/admin/task-chats', { params })
  return data
}

export async function fetchAdminTaskChatMessages(params: {
  task_id: number
  session_assignee_id?: number | null
  null_session?: boolean
  before_id?: number
  limit?: number
}) {
  const { data } = await api.get<AdminTaskChatMessage[]>('/moderation/admin/task-chats/messages', { params })
  return data
}

export async function pushAdminNotification(payload: {
  title: string
  description?: string
  user_ids?: number[]
  include_all?: boolean
  include_banned?: boolean
  include_recent_active?: boolean
  dismiss_type?: 'read' | 'action' | 'source' | 'persistent'
  type?: string
  related_task_id?: number | null
  related_report_id?: number | null
  related_user_id?: number | null
}) {
  const { data } = await api.post<AdminPushNotificationResult>('/moderation/admin/notifications/push', payload)
  return data
}

export async function fetchAdminActionLogs(params: {
  q?: string
  action?: string
  page?: number
  page_size?: number
} = {}) {
  const { data } = await api.get<AdminActionLogListResponse>('/moderation/admin/action-logs', { params })
  return data
}

export async function fetchRegistrationSetting() {
  const { data } = await api.get<{ registration_enabled: boolean }>('/moderation/admin/registration-setting')
  return data
}

export async function updateRegistrationSetting(payload: { registration_enabled: boolean }) {
  const { data } = await api.put<{ registration_enabled: boolean }>('/moderation/admin/registration-setting', payload)
  return data
}
