export interface ConversationKeyLike {
  peer_id: number
  task_id: number | null
}

export function convKey(conv: ConversationKeyLike | null | undefined) {
  if (!conv) return 'unknown-null'
  const peerId = typeof conv.peer_id === 'number' ? conv.peer_id : 'unknown'
  const taskId = conv.task_id ?? 'null'
  return `${peerId}-${taskId}`
}
