import api from './client'
import type { AdminUserListResponse, BanContext, BlacklistItem, Report } from '../types/api'

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

export async function fetchAdminDashboard() {
  const { data } = await api.get('/moderation/admin/dashboard')
  return data
}

export async function fetchAdminReports(params: { type?: string; status?: string } = {}) {
  const { data } = await api.get<Report[]>('/moderation/admin/reports', { params })
  return data
}

export async function reviewReport(reportId: number, payload: { status: 'pending' | 'approved' | 'rejected'; admin_notes?: string }) {
  const { data } = await api.post<Report>(`/moderation/admin/reports/${reportId}/review`, payload)
  return data
}

export async function fetchTaskSnapshot(taskId: number) {
  const { data } = await api.get(`/moderation/admin/tasks/${taskId}/snapshot`)
  return data
}

export async function banUser(userId: number, payload: { banned: boolean; reason?: string; innocent?: boolean }) {
  const { data } = await api.post(`/moderation/admin/users/${userId}/ban`, payload)
  return data
}

export async function fetchAdminUsers(params: { q?: string; page?: number; page_size?: number } = {}) {
  const { data } = await api.get<AdminUserListResponse>('/moderation/admin/users', { params })
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
