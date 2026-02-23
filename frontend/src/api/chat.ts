import api from './client'
import type { ChatMessage, ChatAttachment, Conversation, AttachmentCount } from '../types/chat'

export async function fetchConversations() {
  const { data } = await api.get<Conversation[]>('/chat/conversations')
  return data
}

export async function fetchMessages(peerId: number, taskId?: number | null, before?: number, limit = 50) {
  const params: Record<string, string | number> = { peer_id: peerId, limit }
  if (taskId != null) params.task_id = taskId
  if (before != null) params.before = before
  const { data } = await api.get<ChatMessage[]>('/chat/messages', { params })
  return data
}

export async function fetchMessageSnapshot(peerId: number, taskId?: number | null) {
  const params: Record<string, string | number> = { peer_id: peerId }
  if (taskId != null) params.task_id = taskId
  const { data } = await api.get<ChatMessage[]>('/chat/messages/snapshot', { params })
  return data
}

export async function sendMessage(
  peerId: number,
  content: string,
  taskId?: number | null,
  captchaToken?: string,
) {
  const params: Record<string, string | number> = { peer_id: peerId }
  if (taskId != null) params.task_id = taskId
  const { data } = await api.post<ChatMessage>(
    '/chat/messages',
    { content, captcha_token: captchaToken ?? null },
    { params },
  )
  return data
}

export async function markRead(peerId: number, taskId?: number | null) {
  const params: Record<string, string | number> = { peer_id: peerId }
  if (taskId != null) params.task_id = taskId
  await api.post('/chat/messages/read', null, { params })
}

export async function fetchAttachments(peerId: number, taskId?: number | null) {
  const params: Record<string, string | number> = { peer_id: peerId }
  if (taskId != null) params.task_id = taskId
  const { data } = await api.get<ChatAttachment[]>('/chat/attachments', { params })
  return data
}

export async function fetchAttachmentCount(peerId: number, taskId?: number | null) {
  const params: Record<string, string | number> = { peer_id: peerId }
  if (taskId != null) params.task_id = taskId
  const { data } = await api.get<AttachmentCount>('/chat/attachments/count', { params })
  return data
}

export async function uploadAttachment(peerId: number, file: File, taskId?: number | null, messageId?: number | null) {
  const formData = new FormData()
  formData.append('file', file)
  const params: Record<string, string | number> = { peer_id: peerId }
  if (taskId != null) params.task_id = taskId
  if (messageId != null) params.message_id = messageId
  const { data } = await api.post<ChatAttachment>('/chat/attachments', formData, {
    params,
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export async function deleteAttachment(attachmentId: number) {
  await api.delete(`/chat/attachments/${attachmentId}`)
}
