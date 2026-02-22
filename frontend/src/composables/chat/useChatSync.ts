import { onMounted, onUnmounted, ref, type Ref } from 'vue'
import type { RouteLocationNormalizedLoaded, Router } from 'vue-router'

import { fetchConversations, fetchMessages, markRead } from '../../api/chat'
import { fetchTask } from '../../api/tasks'
import { fetchUserPublic } from '../../api/users'
import type { ChatMessage, Conversation } from '../../types/chat'

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
      messages.value = await fetchMessages(activeConversation.value.peer_id, activeConversation.value.task_id)
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

  async function selectConversation(conversation: Conversation) {
    activeConversation.value = conversation
    messages.value = []
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
            last_message: null,
            last_message_time: null,
            unread_count: 0,
            blocked_by_me: false,
            blocked_by_them: false,
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
      const previousMessages = messages.value
      const latestMessages = await fetchMessages(activeConversation.value.peer_id, activeConversation.value.task_id)

      const hasChanged =
        latestMessages.length !== previousMessages.length ||
        (latestMessages.length > 0 && latestMessages[latestMessages.length - 1].id !== previousMessages[previousMessages.length - 1]?.id)

      if (!hasChanged) return

      messages.value = latestMessages
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
    loadConversations,
    loadMessages,
    selectConversation,
    goBack,
  }
}
