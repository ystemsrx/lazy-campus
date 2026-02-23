import { nextTick, type ComputedRef, type Ref } from 'vue'

import type { Task, UserReview, WorkerProfile } from '../../types/api'
import type { ChatMessage, Conversation } from '../../types/chat'
import { sendMessage } from '../../api/chat'
import { blockUser, unblockUser } from '../../api/moderation'
import { fetchTask } from '../../api/tasks'
import { fetchUserReviews, fetchWorkerDetail } from '../../api/users'
import { appConfirm } from '../../components/AppConfirm.vue'
import { appSlideCaptcha } from '../../components/AppSlideCaptcha.vue'
import type { AppToastNotifier } from '../useAppToast'
import { convKey } from './conversationKey'
import { CaptchaCancelledError, withCaptchaRetry } from '../../utils/captcha'
import { extractError } from '../../utils/error'

export type ChatMessageListExpose = {
  scrollToBottom: () => void
  saveScrollPos: () => void
  restoreScrollPos: () => void
}

interface UseChatViewActionsOptions {
  activeConversation: Ref<Conversation | null>
  messages: Ref<ChatMessage[]>
  inputText: Ref<string>
  sending: Ref<boolean>
  isBlocked: ComputedRef<boolean>
  searchQuery: Ref<string>
  messageListRef: Ref<ChatMessageListExpose | null>
  showTaskPreview: Ref<boolean>
  showUserDetailModal: Ref<boolean>
  showReportModal: Ref<boolean>
  taskPreview: Ref<Task | null>
  peerWorkerProfile: Ref<WorkerProfile | null>
  peerWorkerReviews: Ref<UserReview[]>
  selectConversation: (conversation: Conversation) => Promise<void>
  loadConversations: () => Promise<void> | void
  loadMoreMessages: () => Promise<void>
  unhideConversation: (key: string) => void
  showToast: AppToastNotifier
}

export function useChatViewActions(options: UseChatViewActionsOptions) {
  function scrollToBottom() {
    options.messageListRef.value?.scrollToBottom()
  }

  async function prefetchTaskDetail(taskId: number) {
    try {
      options.taskPreview.value = await fetchTask(taskId)
    } catch {
      // ignore task detail errors
    }
  }

  async function prefetchPeerProfile(peerId: number) {
    try {
      const [profile, reviews] = await Promise.all([
        fetchWorkerDetail(peerId),
        fetchUserReviews(peerId, 'worker'),
      ])

      options.peerWorkerProfile.value = profile
      options.peerWorkerReviews.value = reviews
    } catch {
      // ignore worker profile errors
    }
  }

  async function handleSelectConversation(conversation: Conversation) {
    options.unhideConversation(convKey(conversation))
    await options.selectConversation(conversation)
  }

  async function handleLoadMore() {
    options.messageListRef.value?.saveScrollPos()
    await options.loadMoreMessages()
    await nextTick()
    options.messageListRef.value?.restoreScrollPos()
  }

  function handleSearchQueryUpdate(value: string) {
    options.searchQuery.value = value
  }

  async function handleSend() {
    if (!options.inputText.value.trim() || !options.activeConversation.value || options.isBlocked.value || options.sending.value) {
      return
    }

    const content = options.inputText.value.trim()
    const peerId = options.activeConversation.value.peer_id
    const taskId = options.activeConversation.value.task_id

    options.sending.value = true

    try {
      const message = await withCaptchaRetry(
        (captchaToken) =>
          sendMessage(
            peerId,
            content,
            taskId,
            captchaToken,
          ),
        appSlideCaptcha,
      )

      options.messages.value.push(message)
      options.inputText.value = ''

      await nextTick()
      scrollToBottom()
      void options.loadConversations()
    } catch (error) {
      if (error instanceof CaptchaCancelledError) return
      options.showToast(extractError(error, '发送失败'), 'error')
    } finally {
      options.sending.value = false
    }
  }

  function openTaskDetail() {
    if (!options.activeConversation.value?.task_id) return
    options.showTaskPreview.value = true
    void prefetchTaskDetail(options.activeConversation.value.task_id)
  }

  function openUserDetail() {
    if (!options.activeConversation.value) return
    options.showUserDetailModal.value = true
  }

  function openReportModal() {
    if (!options.activeConversation.value) return
    options.showReportModal.value = true
  }

  async function handleBlockToggle() {
    if (!options.activeConversation.value) return

    const conversation = options.activeConversation.value

    if (conversation.blocked_by_me) {
      const confirmed = await appConfirm({
        title: '解除拉黑',
        message: `确定解除对「${conversation.peer_name}」的拉黑吗？`,
        confirmText: '解除拉黑',
        type: 'warning',
      })
      if (!confirmed) return

      try {
        await unblockUser(conversation.peer_id)
        options.showToast(`已解除对「${conversation.peer_name}」的拉黑`, 'success')
        await options.loadConversations()
      } catch (error: any) {
        options.showToast(error?.response?.data?.detail || '操作失败', 'error')
      }
      return
    }

    const confirmed = await appConfirm({
      title: '拉黑用户',
      message: `确定拉黑「${conversation.peer_name}」吗？拉黑后双方将无法发送消息。`,
      confirmText: '拉黑',
      type: 'danger',
    })
    if (!confirmed) return

    try {
      await blockUser({ blocked_user_id: conversation.peer_id })
      options.showToast(`已拉黑「${conversation.peer_name}」`, 'success')
      await options.loadConversations()
    } catch (error: any) {
      options.showToast(error?.response?.data?.detail || '操作失败', 'error')
    }
  }

  return {
    scrollToBottom,
    prefetchTaskDetail,
    prefetchPeerProfile,
    handleSelectConversation,
    handleLoadMore,
    handleSearchQueryUpdate,
    handleSend,
    openTaskDetail,
    openUserDetail,
    openReportModal,
    handleBlockToggle,
  }
}
