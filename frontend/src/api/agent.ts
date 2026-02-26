import api from './client'
import type {
  AgentAdminConfig,
  AgentAdminSessionList,
  AgentAvailability,
  AgentDeliverable,
  AgentMessage,
  AgentMySessionList,
  AgentSendResult,
  AgentSessionDetail,
  AgentSessionStart,
} from '../types/api'

export async function fetchAgentAvailability() {
  const { data } = await api.get<AgentAvailability>('/agent/me/availability')
  return data
}

export async function fetchMyAgentSessions(params: { page?: number; page_size?: number } = {}) {
  const { data } = await api.get<AgentMySessionList>('/agent/me/sessions', { params })
  return data
}

export async function startTaskAgent(taskId: number) {
  const { data } = await api.post<AgentSessionStart>(`/agent/tasks/${taskId}/start`)
  return data
}

export async function fetchAgentSession(sessionId: string) {
  const { data } = await api.get<AgentSessionDetail>(`/agent/sessions/${sessionId}`)
  return data
}

export async function fetchAgentMessages(sessionId: string, afterId = 0) {
  const { data } = await api.get<AgentMessage[]>(`/agent/sessions/${sessionId}/messages`, {
    params: { after_id: afterId },
  })
  return data
}

export async function sendAgentMessage(sessionId: string, payload: { content: string; files: File[] }) {
  const form = new FormData()
  form.append('content', payload.content)
  payload.files.forEach((file) => form.append('files', file))
  const { data } = await api.post<AgentSendResult>(`/agent/sessions/${sessionId}/messages`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export async function fetchAgentDeliverables(sessionId: string) {
  const { data } = await api.get<AgentDeliverable[]>(`/agent/sessions/${sessionId}/deliverables`)
  return data
}

export async function downloadAgentDeliverable(sessionId: string, name: string) {
  const { data } = await api.get<Blob>(`/agent/sessions/${sessionId}/deliverables/file`, {
    params: { name },
    responseType: 'blob',
  })
  return data
}

export async function downloadDeliverableZip(sessionId: string, names: string[] = []) {
  const params = new URLSearchParams()
  for (const name of names) {
    params.append('names', name)
  }
  const { data } = await api.get<Blob>(`/agent/sessions/${sessionId}/deliverables/zip`, {
    params,
    responseType: 'blob',
  })
  return data
}

export async function cancelAgentSession(sessionId: string) {
  const { data } = await api.post<{ canceled: boolean }>(`/agent/sessions/${sessionId}/cancel`)
  return data
}

export async function deleteAgentDeliverables(sessionId: string, names: string[]) {
  const { data } = await api.delete<{ deleted: string[] }>(`/agent/sessions/${sessionId}/deliverables`, {
    data: { names },
  })
  return data
}

export async function fetchAdminAgentConfig() {
  const { data } = await api.get<AgentAdminConfig>('/agent/admin/config')
  return data
}

export async function updateAdminAgentConfig(payload: { agent_enabled: boolean }) {
  const { data } = await api.put<AgentAdminConfig>('/agent/admin/config', payload)
  return data
}

export async function batchGrantAgentUsage(payload: { user_ids: number[]; amount: number }) {
  const { data } = await api.post<{ updated_user_count: number }>('/agent/admin/grant', payload)
  return data
}

export async function fetchAdminAgentSessions(params: {
  q?: string
  user_id?: number
  page?: number
  page_size?: number
} = {}) {
  const { data } = await api.get<AgentAdminSessionList>('/agent/admin/sessions', { params })
  return data
}

export async function fetchAdminAgentMessages(sessionId: string, afterId = 0) {
  const { data } = await api.get<AgentMessage[]>(`/agent/admin/sessions/${sessionId}/messages`, {
    params: { after_id: afterId },
  })
  return data
}
