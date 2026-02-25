import { onActivated, onDeactivated, onMounted, onUnmounted, ref, watch, type Ref } from 'vue'
import type { RouteLocationNormalizedLoaded, Router } from 'vue-router'

import { fetchConversations, fetchMessages, markRead } from '../../api/chat'
import { fetchTask } from '../../api/tasks'
import { fetchUserPublic } from '../../api/users'
import type { ChatMessage, Conversation } from '../../types/chat'

const PAGE_SIZE = 30

interface UseChatSyncOptions {
  route: RouteLocationNormalizedLoaded
  router: Router
  isMobile: Ref<boolean>
  onConversationsRefreshed?: (conversations: Conversation[]) => void
  onBeforeSelectConversation?: (conversation: Conversation) => void
  onLoadAttachments?: () => Promise<void>
  onPrefetchPeerProfile?: (peerId: number) => Promise<void>
  onPrefetchTaskDetail?: (taskId: number) => Promise<void>
  onAfterMessagesUpdated?: () => Promise<void> | void
  onAfterLoadConversations?: () => Promise<void> | void
  pollNotificationCount?: () => void
}

export function useChatSync(options: UseChatSyncOptions) {
  const conversations = ref<Conversation[]>([])
  const activeConversation = ref<Conversation | null>(null)
  const messages = ref<ChatMessage[]>([])
  const loading = ref(false)
  const hasMore = ref(false)
  const loadingMore = ref(false)

  let pollTimer: ReturnType<typeof setInterval> | null = null
  let mountedReady = false

  function normalizeTaskId(taskId: number | null | undefined): number | null {
    if (typeof taskId !== 'number' || !Number.isFinite(taskId) || taskId <= 0) return null
    return taskId
  }

  function parseQueryId(raw: unknown): number | null {
    const value = Array.isArray(raw) ? raw[0] : raw
    if (value === undefined || value === null || value === '') return null
    const parsed = Number(value)
    if (!Number.isFinite(parsed) || parsed <= 0) return null
    return parsed
  }

  function conversationKey(peerId: number, taskId: number | null): string {
    return `${peerId}-${taskId === null ? 'null' : taskId}`
  }

  function normalizeConversation(conversation: Conversation): Conversation {
    return {
      ...conversation,
      task_id: normalizeTaskId(conversation.task_id),
      peer_last_active: conversation.peer_last_active ?? null,
    }
  }

  function isSameConversation(conversation: Conversation | null | undefined, peerId: number, taskId: number | null): boolean {
    if (!conversation) return false
    return (
      conversation.peer_id === peerId &&
      normalizeTaskId(conversation.task_id) === taskId
    )
  }

  function dedupeConversations(list: Conversation[]): Conversation[] {
    const order: string[] = []
    const byKey = new Map<string, Conversation>()

    const pickBetter = (a: Conversation, b: Conversation): Conversation => {
      const aScore = (a.last_message_time ? 8 : 0) + (a.last_message ? 4 : 0) + (a.peer_last_active ? 2 : 0) + (a.task_title ? 1 : 0)
      const bScore = (b.last_message_time ? 8 : 0) + (b.last_message ? 4 : 0) + (b.peer_last_active ? 2 : 0) + (b.task_title ? 1 : 0)
      if (bScore > aScore) return b
      if (bScore < aScore) return a

      const aTime = a.last_message_time ?? ''
      const bTime = b.last_message_time ?? ''
      return bTime > aTime ? b : a
    }

    for (const item of list) {
      const normalized = normalizeConversation(item)
      const key = conversationKey(normalized.peer_id, normalized.task_id)
      if (!byKey.has(key)) {
        byKey.set(key, normalized)
        order.push(key)
        continue
      }

      byKey.set(key, pickBetter(byKey.get(key)!, normalized))
    }

    return order
      .map((key) => byKey.get(key))
      .filter((conversation): conversation is Conversation => Boolean(conversation))
  }

  function findConversation(peerId: number, taskId: number | null): Conversation | undefined {
    return conversations.value.find((conversation) => isSameConversation(conversation, peerId, taskId))
  }

  async function loadConversations() {
    try {
      const fetchedList = await fetchConversations()
      const freshList = dedupeConversations(fetchedList)

      const activePeer = activeConversation.value?.peer_id
      const activeTask = normalizeTaskId(activeConversation.value?.task_id)

      if (activePeer !== undefined) {
        const existsInFresh = freshList.some(
          (conversation) => isSameConversation(conversation, activePeer, activeTask),
        )

        if (!existsInFresh && activeConversation.value) {
          freshList.unshift(normalizeConversation(activeConversation.value))
        }
      }

      const nextList = dedupeConversations(freshList)
      conversations.value = nextList
      options.onConversationsRefreshed?.(nextList)

      if (activeConversation.value) {
        const updated = nextList.find(
          (conversation) => isSameConversation(
            conversation,
            activeConversation.value!.peer_id,
            normalizeTaskId(activeConversation.value!.task_id),
          ),
        )
        if (updated) {
          activeConversation.value = updated
        }
      }
    } catch {
      // ignore
    }
  }

  async function loadMessages() {
    if (!activeConversation.value) return

    loading.value = true
    try {
      const loaded = await fetchMessages(activeConversation.value.peer_id, activeConversation.value.task_id, undefined, PAGE_SIZE)
      messages.value = loaded
      hasMore.value = loaded.length >= PAGE_SIZE
      await markRead(activeConversation.value.peer_id, activeConversation.value.task_id)
      options.pollNotificationCount?.()
      if (activeConversation.value) {
        activeConversation.value.unread_count = 0
      }
    } catch {
      // ignore
    }

    loading.value = false
    await options.onAfterMessagesUpdated?.()
  }

  async function loadMoreMessages() {
    if (!activeConversation.value || loadingMore.value || !hasMore.value) return

    loadingMore.value = true
    try {
      const oldestId = messages.value[0]?.id
      const older = await fetchMessages(
        activeConversation.value.peer_id,
        activeConversation.value.task_id,
        oldestId,
        PAGE_SIZE,
      )
      if (older.length === 0) {
        hasMore.value = false
      } else {
        messages.value = [...older, ...messages.value]
        hasMore.value = older.length >= PAGE_SIZE
      }
    } catch {
      // ignore
    }
    loadingMore.value = false
  }

  async function selectConversation(conversation: Conversation) {
    const normalizedConversation = normalizeConversation(conversation)
    activeConversation.value = normalizedConversation
    messages.value = []
    hasMore.value = false
    options.onBeforeSelectConversation?.(normalizedConversation)

    const query: Record<string, string> = { peer: String(normalizedConversation.peer_id) }
    if (normalizedConversation.task_id !== null) {
      query.task = String(normalizedConversation.task_id)
    }

    const tasks: Promise<unknown>[] = [
      loadMessages(),
      options.onLoadAttachments?.() ?? Promise.resolve(),
      options.onPrefetchPeerProfile?.(normalizedConversation.peer_id) ?? Promise.resolve(),
    ]

    if (normalizedConversation.task_id !== null) {
      tasks.push(options.onPrefetchTaskDetail?.(normalizedConversation.task_id) ?? Promise.resolve())
    }
    options.router.replace({ path: '/chat', query })

    await Promise.all(tasks)
  }

  function goBack() {
    activeConversation.value = null
  }

  async function hydrateRouteSelection() {
    const peerId = parseQueryId(options.route.query.peer) ?? 0
    const taskId = parseQueryId(options.route.query.task)

    if (peerId) {
      let found = findConversation(peerId, taskId)

      if (!found) {
        try {
          const userInfo = await fetchUserPublic(peerId)

          let taskTitle: string | null = null
          let taskPrice: number | null = null
          let taskStatus: string | null = null
          let taskIcon: string | null = null

          if (taskId !== null) {
            try {
              const taskInfo = await fetchTask(taskId)
              taskTitle = taskInfo.title
              taskPrice = taskInfo.price
              taskStatus = taskInfo.status
              taskIcon = taskInfo.icon ?? null
            } catch {
              // task not found
            }
          }

          found = findConversation(peerId, taskId)
          if (!found) {
            const placeholder: Conversation = normalizeConversation({
              peer_id: peerId,
              peer_name: userInfo.display_name,
              peer_avatar: userInfo.avatar_url,
              peer_gender: userInfo.gender ?? null,
              peer_last_active: userInfo.last_active ?? null,
              task_id: taskId,
              task_title: taskTitle,
              task_price: taskPrice,
              task_status: taskStatus,
              task_icon: taskIcon,
              task_is_deleted: false,
              last_message: null,
              last_message_time: null,
              unread_count: 0,
              blocked_by_me: false,
              blocked_by_them: false,
              peer_ban_contact: false,
              peer_payment_qr_url: null,
              task_publisher_id: null,
            })

            conversations.value = dedupeConversations([placeholder, ...conversations.value])
            found = findConversation(peerId, taskId) ?? placeholder
          }
        } catch {
          // user not found
        }
      }

      if (found) {
        await selectConversation(found)
      }
      return
    }

    if (!options.isMobile.value && conversations.value.length > 0) {
      await selectConversation(conversations.value[0])
    }
  }

  async function pollConversationChanges() {
    await loadConversations()

    if (!activeConversation.value) return

    try {
      const latestBatch = await fetchMessages(activeConversation.value.peer_id, activeConversation.value.task_id, undefined, PAGE_SIZE)
      if (latestBatch.length === 0) return

      const newestInBatch = latestBatch.at(-1)!.id
      const newestLocal = messages.value.at(-1)?.id ?? 0

      // 将批次数据建立 id→message 索引，用于同步 is_read 状态
      const batchById = new Map(latestBatch.map(m => [m.id, m]))

      // 无论是否有新消息，都将已读状态同步到现有消息列表（双勾显示依赖此逻辑）
      let readStatusChanged = false
      messages.value = messages.value.map(m => {
        const fresh = batchById.get(m.id)
        if (fresh && !m.is_read && fresh.is_read) {
          readStatusChanged = true
          return { ...m, is_read: true }
        }
        return m
      })

      if (newestInBatch <= newestLocal) {
        if (readStatusChanged) await options.onAfterMessagesUpdated?.()
        return
      }

      // Only append genuinely new messages (don't replace existing paginated history)
      const newOnes = latestBatch.filter(m => m.id > newestLocal)
      if (newOnes.length === 0) return

      messages.value = [...messages.value, ...newOnes]
      await Promise.all([
        markRead(activeConversation.value.peer_id, activeConversation.value.task_id),
        options.onLoadAttachments?.() ?? Promise.resolve(),
      ])

      options.pollNotificationCount?.()
      if (activeConversation.value) {
        activeConversation.value.unread_count = 0
      }
      await options.onAfterMessagesUpdated?.()
    } catch {
      // ignore polling exceptions
    }
  }

  function startPolling() {
    if (pollTimer) return
    pollTimer = setInterval(async () => {
      await pollConversationChanges()
    }, 5000)
  }

  function stopPolling() {
    if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
  }

  onMounted(async () => {
    try {
      await loadConversations()
      await options.onAfterLoadConversations?.()
      await hydrateRouteSelection()
    } finally {
      mountedReady = true
      startPolling()
    }
  })

  onActivated(async () => {
    if (!mountedReady) {
      startPolling()
      return
    }

    const routePeer = parseQueryId(options.route.query.peer) ?? 0
    const routeTask = parseQueryId(options.route.query.task)

    const needsRehydrate = routePeer > 0 && (
      !isSameConversation(activeConversation.value, routePeer, routeTask)
    )

    if (needsRehydrate) {
      await loadConversations()
      await hydrateRouteSelection()
    }

    startPolling()
  })

  watch(
    () => [options.route.query.peer, options.route.query.task] as const,
    async () => {
      const routePeer = parseQueryId(options.route.query.peer) ?? 0
      const routeTask = parseQueryId(options.route.query.task)

      if (routePeer === 0) return

      if (isSameConversation(activeConversation.value, routePeer, routeTask)) {
        return
      }

      await loadConversations()
      await hydrateRouteSelection()
    },
  )

  onDeactivated(() => {
    stopPolling()
  })

  onUnmounted(() => {
    stopPolling()
  })

  return {
    conversations,
    activeConversation,
    messages,
    loading,
    hasMore,
    loadingMore,
    loadConversations,
    loadMessages,
    loadMoreMessages,
    selectConversation,
    goBack,
  }
}
