import { computed, ref, watch } from 'vue'

import {
  fetchAdminChatAttachments,
  fetchAdminChatConversations,
  fetchAdminChatMessages,
  fetchAdminTaskChatConversations,
  fetchAdminTaskChatMessages,
  fetchTaskSnapshot,
  updateAdminUserProfile,
} from '../../api/moderation'
import type {
  AdminChatAttachment,
  AdminChatConversationItem,
  AdminChatMessage,
  AdminTaskChatConversationItem,
  AdminTaskChatMessage,
} from '../../types/api'
import { extractError } from '../../utils/error'
import type { AppToastNotifier } from '../useAppToast'
import type { TaskSnapshot } from './useAdminReports'

const PAGE_SIZE = 20

export interface AdminUnifiedMessage {
  id: string
  rawId: number
  sender_id: number
  sender_display_name: string
  sender_avatar_url: string | null
  sender_gender: 'male' | 'female' | null
  content: string
  created_at: string
  sub_label: string
  blocked?: boolean
}

export interface AdminChatParticipant {
  id: number
  display_name: string
  avatar_url: string | null
  gender: 'male' | 'female' | null
  role: string
}

export interface AdminChatTaskInfo {
  id: number
  title: string
  price: number | null
  status: string | null
}

export type ChatFilterMode = 'all' | 'task' | 'direct'

export function useAdminChats(showToast: AppToastNotifier) {
  const mode = ref<ChatFilterMode>('all')
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
  const attachments = ref<AdminChatAttachment[]>([])

  const participantA = ref<AdminChatParticipant | null>(null)
  const participantB = ref<AdminChatParticipant | null>(null)
  const taskInfo = ref<AdminChatTaskInfo | null>(null)

  const showSnapshot = ref(false)
  const snapshotLoading = ref(false)
  const snapshot = ref<TaskSnapshot | null>(null)

  const totalPages = computed(() => Math.max(1, Math.ceil(total.value / PAGE_SIZE)))

  async function loadConversations() {
    loading.value = true
    try {
      if (mode.value === 'task') {
        const [dData, tData] = await Promise.all([
          fetchAdminChatConversations({
            q: search.value.trim() || undefined,
            task_id: -1,
            page: page.value,
            page_size: PAGE_SIZE,
          }),
          fetchAdminTaskChatConversations({
            q: search.value.trim() || undefined,
            page: page.value,
            page_size: PAGE_SIZE,
          }),
        ])
        directConversations.value = dData.items
        taskConversations.value = tData.items
        total.value = dData.total + tData.total
      } else if (mode.value === 'direct') {
        const data = await fetchAdminChatConversations({
          q: search.value.trim() || undefined,
          task_id: 0,
          page: page.value,
          page_size: PAGE_SIZE,
        })
        directConversations.value = data.items
        taskConversations.value = []
        total.value = data.total
      } else {
        const [dData, tData] = await Promise.all([
          fetchAdminChatConversations({
            q: search.value.trim() || undefined,
            page: page.value,
            page_size: PAGE_SIZE,
          }),
          fetchAdminTaskChatConversations({
            q: search.value.trim() || undefined,
            page: page.value,
            page_size: PAGE_SIZE,
          }),
        ])
        directConversations.value = dData.items
        taskConversations.value = tData.items
        total.value = dData.total + tData.total
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

    participantA.value = {
      id: item.user_a_id,
      display_name: item.user_a_display_name,
      avatar_url: item.user_a_avatar_url,
      gender: item.user_a_gender,
      role: '用户',
    }
    participantB.value = {
      id: item.user_b_id,
      display_name: item.user_b_display_name,
      avatar_url: item.user_b_avatar_url,
      gender: item.user_b_gender,
      role: '用户',
    }
    taskInfo.value = item.task_id ? {
      id: item.task_id,
      title: item.task_title || `任务 #${item.task_id}`,
      price: item.task_price,
      status: item.task_status,
    } : null

    try {
      const [data, atts] = await Promise.all([
        fetchAdminChatMessages({
          user_a_id: item.user_a_id,
          user_b_id: item.user_b_id,
          task_id: item.task_id,
          limit: 300,
        }),
        fetchAdminChatAttachments({
          user_a_id: item.user_a_id,
          user_b_id: item.user_b_id,
          task_id: item.task_id,
        }),
      ])
      messages.value = data.map((m: AdminChatMessage) => ({
        id: `d-${m.id}`,
        rawId: m.id,
        sender_id: m.sender_id,
        sender_display_name: m.sender_display_name,
        sender_avatar_url: m.sender_avatar_url,
        sender_gender: m.sender_gender,
        content: m.content,
        created_at: m.created_at,
        sub_label: `→ ${m.receiver_display_name}`,
        blocked: m.blocked,
      }))
      attachments.value = atts
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

    participantA.value = {
      id: item.publisher_id,
      display_name: item.publisher_display_name,
      avatar_url: item.publisher_avatar_url,
      gender: item.publisher_gender,
      role: '发布者',
    }
    participantB.value = item.session_assignee_id ? {
      id: item.session_assignee_id,
      display_name: item.session_assignee_display_name || '接单者',
      avatar_url: item.session_assignee_avatar_url,
      gender: item.session_assignee_gender,
      role: '接单者',
    } : null
    taskInfo.value = {
      id: item.task_id,
      title: item.task_title,
      price: item.task_price,
      status: item.task_status,
    }

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
        rawId: m.id,
        sender_id: m.sender_id,
        sender_display_name: m.sender_display_name,
        sender_avatar_url: m.sender_avatar_url,
        sender_gender: m.sender_gender,
        content: m.content,
        created_at: m.created_at,
        sub_label: item.task_title,
      }))
      attachments.value = []
    } catch (error: unknown) {
      showToast(extractError(error, '加载任务聊天失败'), 'error')
    } finally {
      messagesLoading.value = false
    }
  }

  async function toggleBanContact(userId: number, banned: boolean) {
    try {
      await updateAdminUserProfile(userId, { ban_contact: banned })
      showToast(banned ? '已禁止该用户联系他人' : '已解除联系限制', 'success')
    } catch (error: unknown) {
      showToast(extractError(error, '操作失败'), 'error')
    }
  }

  async function openSnapshot(taskId: number) {
    showSnapshot.value = true
    snapshotLoading.value = true
    snapshot.value = null
    try {
      snapshot.value = await fetchTaskSnapshot(taskId)
    } catch (error: unknown) {
      showToast(extractError(error, '加载任务快照失败'), 'error')
      showSnapshot.value = false
    } finally {
      snapshotLoading.value = false
    }
  }

  function closeSnapshot() {
    showSnapshot.value = false
  }

  function clearSelection() {
    selectedDirect.value = null
    selectedTask.value = null
    messages.value = []
    attachments.value = []
    participantA.value = null
    participantB.value = null
    taskInfo.value = null
  }

  function switchMode(next: ChatFilterMode) {
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
    directConversations,
    taskConversations,
    selectedDirect,
    selectedTask,
    messages,
    attachments,
    participantA,
    participantB,
    taskInfo,
    showSnapshot,
    snapshotLoading,
    snapshot,
    loadConversations,
    loadDirectMessages,
    loadTaskMessages,
    toggleBanContact,
    openSnapshot,
    closeSnapshot,
    switchMode,
    clearSelection,
    goPage,
  }
}

export type AdminChatsModel = ReturnType<typeof useAdminChats>
