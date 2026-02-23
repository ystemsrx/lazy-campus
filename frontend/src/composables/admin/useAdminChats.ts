import { computed, ref, watch } from 'vue'

import {
  fetchAdminChatConversations,
  fetchAdminChatMessages,
  fetchAdminTaskChatConversations,
  fetchAdminTaskChatMessages,
} from '../../api/moderation'
import type {
  AdminChatConversationItem,
  AdminChatMessage,
  AdminTaskChatConversationItem,
  AdminTaskChatMessage,
} from '../../types/api'
import { extractError } from '../../utils/error'
import type { AppToastNotifier } from '../useAppToast'

const PAGE_SIZE = 20

export interface AdminUnifiedMessage {
  id: string
  sender_id: number
  sender_display_name: string
  content: string
  created_at: string
  sub_label: string
}

export function useAdminChats(showToast: AppToastNotifier) {
  const mode = ref<'direct' | 'task'>('direct')
  const search = ref('')
  const loading = ref(false)
  const messagesLoading = ref(false)

  const page = ref(1)
  const total = ref(0)

  const directConversations = ref<AdminChatConversationItem[]>([])
  const taskConversations = ref<AdminTaskChatConversationItem[]>([])
  const selectedDirect = ref<AdminChatConversationItem | null>(null)
  const selectedTask = ref<AdminTaskChatConversationItem | null>(null)
  const messages = ref<AdminUnifiedMessage[]>([])

  const totalPages = computed(() => Math.max(1, Math.ceil(total.value / PAGE_SIZE)))
  const conversationList = computed(() =>
    mode.value === 'direct' ? directConversations.value : taskConversations.value,
  )

  async function loadConversations() {
    loading.value = true
    try {
      if (mode.value === 'direct') {
        const data = await fetchAdminChatConversations({
          q: search.value.trim() || undefined,
          page: page.value,
          page_size: PAGE_SIZE,
        })
        directConversations.value = data.items
        total.value = data.total
      } else {
        const data = await fetchAdminTaskChatConversations({
          q: search.value.trim() || undefined,
          page: page.value,
          page_size: PAGE_SIZE,
        })
        taskConversations.value = data.items
        total.value = data.total
      }
    } catch (error: unknown) {
      showToast(extractError(error, '加载聊天会话失败'), 'error')
    } finally {
      loading.value = false
    }
  }

  async function loadDirectMessages(item: AdminChatConversationItem) {
    messagesLoading.value = true
    selectedDirect.value = item
    selectedTask.value = null
    try {
      const data = await fetchAdminChatMessages({
        user_a_id: item.user_a_id,
        user_b_id: item.user_b_id,
        task_id: item.task_id,
        limit: 300,
      })
      messages.value = data.map((m: AdminChatMessage) => ({
        id: `d-${m.id}`,
        sender_id: m.sender_id,
        sender_display_name: m.sender_display_name,
        content: m.content,
        created_at: m.created_at,
        sub_label: `→ ${m.receiver_display_name}`,
      }))
    } catch (error: unknown) {
      showToast(extractError(error, '加载聊天消息失败'), 'error')
    } finally {
      messagesLoading.value = false
    }
  }

  async function loadTaskMessages(item: AdminTaskChatConversationItem) {
    messagesLoading.value = true
    selectedTask.value = item
    selectedDirect.value = null
    try {
      const params: {
        task_id: number
        session_assignee_id?: number | null
        null_session?: boolean
        limit?: number
      } = { task_id: item.task_id, limit: 300 }
      if (item.session_assignee_id === null) params.null_session = true
      else params.session_assignee_id = item.session_assignee_id

      const data = await fetchAdminTaskChatMessages(params)
      messages.value = data.map((m: AdminTaskChatMessage) => ({
        id: `t-${m.id}`,
        sender_id: m.sender_id,
        sender_display_name: m.sender_display_name,
        content: m.content,
        created_at: m.created_at,
        sub_label: item.task_title,
      }))
    } catch (error: unknown) {
      showToast(extractError(error, '加载任务聊天失败'), 'error')
    } finally {
      messagesLoading.value = false
    }
  }

  function clearSelection() {
    selectedDirect.value = null
    selectedTask.value = null
    messages.value = []
  }

  function switchMode(next: 'direct' | 'task') {
    if (mode.value === next) return
    mode.value = next
    page.value = 1
    clearSelection()
    loadConversations()
  }

  let searchTimer = 0
  watch(search, () => {
    clearTimeout(searchTimer)
    searchTimer = window.setTimeout(() => {
      page.value = 1
      clearSelection()
      loadConversations()
    }, 250)
  })

  watch(page, () => {
    clearSelection()
    loadConversations()
  })

  function goPage(next: number) {
    if (next < 1 || next > totalPages.value) return
    page.value = next
  }

  return {
    mode,
    search,
    loading,
    messagesLoading,
    page,
    total,
    totalPages,
    conversationList,
    directConversations,
    taskConversations,
    selectedDirect,
    selectedTask,
    messages,
    loadConversations,
    loadDirectMessages,
    loadTaskMessages,
    switchMode,
    clearSelection,
    goPage,
  }
}

export type AdminChatsModel = ReturnType<typeof useAdminChats>
