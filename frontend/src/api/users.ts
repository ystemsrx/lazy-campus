import api from './client'
import type { UserMe, UserReview, WorkerContactReveal, WorkerProfile } from '../types/api'

export async function fetchWorkers(params: Record<string, string | number | undefined>) {
  const { data } = await api.get<WorkerProfile[]>('/users/workers', { params })
  return data
}

export async function updateWorkerProfile(payload: {
  enabled: boolean
  skill_tag_ids: number[]
  min_price: number | null
  max_price: number | null
  bio: string | null
  phone: string | null
  wechat: string | null
}) {
  const { data } = await api.put<WorkerProfile>('/users/me/worker-profile', payload)
  return data
}

export async function fetchMyWorkerProfile() {
  const { data } = await api.get<WorkerProfile>('/users/me/worker-profile')
  return data
}

export async function fetchWorkerDetail(userId: number) {
  const { data } = await api.get<WorkerProfile>(`/users/workers/${userId}`)
  return data
}

export async function revealWorkerContact(userId: number) {
  const { data } = await api.post<WorkerContactReveal>(`/users/workers/${userId}/contact-view`)
  return data
}

export async function updateProfile(payload: { email: string; gender: 'male' | 'female'; nickname?: string }) {
  const { data } = await api.put<UserMe>('/users/me/profile', payload)
  return data
}

export async function fetchUserReviews(userId: number, role: 'publisher' | 'worker' = 'publisher') {
  const { data } = await api.get<UserReview[]>(`/users/${userId}/reviews`, { params: { role } })
  return data
}

export async function uploadAvatar(file: File) {
  const form = new FormData()
  form.append('file', file)
  const { data } = await api.post<UserMe>('/users/me/avatar', form, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
  return data
}
