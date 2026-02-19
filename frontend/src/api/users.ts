import api from './client'
import type { WorkerProfile } from '../types/api'

export async function fetchWorkers(params: Record<string, string | number | undefined>) {
  const { data } = await api.get<WorkerProfile[]>('/users/workers', { params })
  return data
}

export async function updateWorkerProfile(payload: {
  enabled: boolean
  skills: string | null
  min_price: number | null
  max_price: number | null
  bio: string | null
}) {
  const { data } = await api.put<WorkerProfile>('/users/me/worker-profile', payload)
  return data
}

export async function fetchMyWorkerProfile() {
  const { data } = await api.get<WorkerProfile>('/users/me/worker-profile')
  return data
}
