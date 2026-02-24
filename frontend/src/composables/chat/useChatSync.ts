import { onMounted, onUnmounted, ref, type Ref } from 'vue'
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

  async function loadConversations() {
    try {
      const freshList = await fetchConversations()

      const activePeer = activeConversation.value?.peer_id
      const activeTask = activeConversation.value?.task_id

      if (activePeer !== undefined) {
        const existsInFresh = freshList.some(
          (conversation) => conversation.peer_id === activePeer && conversation.task_id === activeTask,
        )

        if (!existsInFresh && activeConversation.value) {
          freshList.unshift(activeConversation.value)
        }
      }

      conversations.value = freshList
      options.onConversationsRefreshed?.(freshList)

      if (activeConversation.value) {
        const updated = freshList.find(
          (conversation) =>
            conversation.peer_id === activeConversation.value!.peer_id &&
            conversation.task_id === activeConversation.value!.task_id,
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
    activeConversation.value = conversation
    messages.value = []
    hasMore.value = false
    options.onBeforeSelectConversation?.(conversation)

    const query: Record<string, string> = { peer: String(conversation.peer_id) }
    if (conversation.task_id) {
      query.task = String(conversation.task_id)
    }
    options.router.replace({ path: '/chat', query })

    const tasks: Promise<unknown>[] = [
      loadMessages(),
      options.onLoadAttachments?.() ?? Promise.resolve(),
      options.onPrefetchPeerProfile?.(conversation.peer_id) ?? Promise.resolve(),
    ]

    if (conversation.task_id) {
      tasks.push(options.onPrefetchTaskDetail?.(conversation.task_id) ?? Promise.resolve())
    }

    await Promise.all(tasks)
  }

  function goBack() {
    activeConversation.value = null
  }

  async function hydrateRouteSelection() {
    const peerId = Number(options.route.query.peer)
    const taskId = options.route.query.task ? Number(options.route.query.task) : null

    if (peerId) {
      let found = conversations.value.find(
        (conversation) => conversation.peer_id === peerId && conversation.task_id === taskId,
      )

      if (!found) {
        try {
          const userInfo = await fetchUserPublic(peerId)

          let taskTitle: string | null = null
          let taskPrice: number | null = null
          let taskStatus: string | null = null
          let taskIcon: string | null = null

          if (taskId) {
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

          const placeholder: Conversation = {
            peer_id: peerId,
            peer_name: userInfo.display_name,
            peer_avatar: userInfo.avatar_url,
            peer_gender: userInfo.gender ?? null,
            peer_last_active: null,
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
          }

          conversations.value.unshift(placeholder)
          found = placeholder
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

  onMounted(async () => {
    await loadConversations()
    await options.onAfterLoadConversations?.()
    await hydrateRouteSelection()

    pollTimer = setInterval(async () => {
      await pollConversationChanges()
    }, 5000)
  })

  onUnmounted(() => {
    if (pollTimer) {
      clearInterval(pollTimer)
    }
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
