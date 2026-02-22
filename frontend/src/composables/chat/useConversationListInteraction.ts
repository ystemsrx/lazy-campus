import { computed, onMounted, onUnmounted, ref, type Ref } from 'vue'

import type { Conversation } from '../../types/chat'
import { convKey } from './conversationKey'

export interface ConversationContextMenu {
  x: number
  y: number
  key: string
}

interface UseConversationListInteractionOptions {
  userId: number | null | undefined
  conversations: Ref<Conversation[]>
  activeConversation: Ref<Conversation | null>
}

function createStorageKey(userId: number | null | undefined) {
  return `chat-hidden-convs-${userId ?? 'guest'}`
}

function loadHiddenKeys(storageKey: string): Set<string> {
  try {
    const raw = localStorage.getItem(storageKey)
    return raw ? new Set(JSON.parse(raw) as string[]) : new Set()
  } catch {
    return new Set()
  }
}

function saveHiddenKeys(storageKey: string, keys: Set<string>) {
  try {
    localStorage.setItem(storageKey, JSON.stringify([...keys]))
  } catch {
    // ignore write failures from storage sandbox/privacy mode
  }
}

export function useConversationListInteraction(options: UseConversationListInteractionOptions) {
  const storageKey = createStorageKey(options.userId)

  const searchQuery = ref('')
  const hiddenConversationKeys = ref<Set<string>>(loadHiddenKeys(storageKey))

  const swipedKey = ref<string | null>(null)
  const swipeStartX = ref(0)
  const contextMenu = ref<ConversationContextMenu | null>(null)

  const filteredConversations = computed(() => {
    const safeConversations = options.conversations.value.filter(
      (conv): conv is Conversation => Boolean(conv && typeof conv.peer_id === 'number'),
    )
    const visible = safeConversations.filter((conv) => !hiddenConversationKeys.value.has(convKey(conv)))
    if (!searchQuery.value.trim()) return visible

    const q = searchQuery.value.toLowerCase()
    return visible.filter(
      (conv) =>
        conv.peer_name.toLowerCase().includes(q) ||
        (conv.task_title && conv.task_title.toLowerCase().includes(q)),
    )
  })

  function closeSwipe() {
    swipedKey.value = null
  }

  function closeContextMenu() {
    contextMenu.value = null
  }

  function onSwipeStart(event: TouchEvent, key: string) {
    swipeStartX.value = event.touches[0].clientX
    if (swipedKey.value !== key) {
      swipedKey.value = null
    }
  }

  function onSwipeMove(event: TouchEvent, key: string) {
    const deltaX = swipeStartX.value - event.touches[0].clientX
    if (deltaX > 40) {
      swipedKey.value = key
    } else if (deltaX < -10) {
      swipedKey.value = null
    }
  }

  function onSwipeEnd() {
    // keep current swipe state
  }

  function onContextMenu(event: MouseEvent, key: string) {
    event.preventDefault()
    event.stopPropagation()
    contextMenu.value = { x: event.clientX, y: event.clientY, key }
  }

  function hideConversation(key: string) {
    const next = new Set([...hiddenConversationKeys.value, key])
    hiddenConversationKeys.value = next
    saveHiddenKeys(storageKey, next)

    swipedKey.value = null
    contextMenu.value = null

    if (options.activeConversation.value && convKey(options.activeConversation.value) === key) {
      options.activeConversation.value = null
    }
  }

  function unhideConversation(key: string) {
    if (!hiddenConversationKeys.value.has(key)) return

    const next = new Set(hiddenConversationKeys.value)
    next.delete(key)
    hiddenConversationKeys.value = next
    saveHiddenKeys(storageKey, next)
  }

  function autoUnhideUnread(conversations: Conversation[]) {
    for (const conversation of conversations) {
      const key = convKey(conversation)
      if (hiddenConversationKeys.value.has(key) && conversation.unread_count > 0) {
        unhideConversation(key)
      }
    }
  }

  onMounted(() => {
    document.addEventListener('click', closeContextMenu)
  })

  onUnmounted(() => {
    document.removeEventListener('click', closeContextMenu)
  })

  return {
    searchQuery,
    filteredConversations,
    hiddenConversationKeys,
    swipedKey,
    contextMenu,
    closeSwipe,
    closeContextMenu,
    onSwipeStart,
    onSwipeMove,
    onSwipeEnd,
    onContextMenu,
    hideConversation,
    unhideConversation,
    autoUnhideUnread,
  }
}
