import { computed, ref, type Ref } from 'vue'

import type { Task, UserReview, WorkerProfile } from '../../types/api'
import type { Conversation } from '../../types/chat'
import { formatLastSeen } from '../../utils/time'

export function useChatViewUiState(
  activeConversation: Ref<Conversation | null>,
  externalIsMobile?: Ref<boolean>,
) {
  const isMobile = externalIsMobile ?? ref(typeof window !== 'undefined' ? window.innerWidth < 768 : false)
  const isBannerCollapsed = ref(false)

  const inputText = ref('')
  const sending = ref(false)

  const showUserDetailModal = ref(false)
  const peerWorkerProfile = ref<WorkerProfile | null>(null)
  const peerWorkerReviews = ref<UserReview[]>([])

  const showTaskPreview = ref(false)
  const taskPreview = ref<Task | null>(null)

  const showReportModal = ref(false)

  const isTaskEnded = computed(() => {
    if (!activeConversation.value) return false
    return activeConversation.value.task_is_deleted || activeConversation.value.task_status === 'canceled'
  })

  const isBlocked = computed(() => {
    if (!activeConversation.value) return false
    if (isTaskEnded.value) return true
    return activeConversation.value.blocked_by_me || activeConversation.value.blocked_by_them
  })

  const blockReason = computed(() => {
    if (!activeConversation.value) return ''
    if (activeConversation.value.task_is_deleted) return '该任务已被删除'
    if (activeConversation.value.task_status === 'canceled') return '该任务已被取消'
    if (activeConversation.value.blocked_by_me && activeConversation.value.blocked_by_them) return '双方已相互拉黑'
    if (activeConversation.value.blocked_by_me) return '您已拉黑此用户'
    if (activeConversation.value.blocked_by_them) return '对方已将您拉黑'
    return ''
  })

  const peerOnlineStatus = computed(() => {
    if (!activeConversation.value) {
      return { online: false, text: '' }
    }
    return formatLastSeen(activeConversation.value.peer_last_active)
  })

  function checkMobile() {
    if (typeof window === 'undefined') return
    isMobile.value = window.innerWidth < 768
  }

  function clearConversationMetaState() {
    taskPreview.value = null
    peerWorkerProfile.value = null
    peerWorkerReviews.value = []
  }

  return {
    isMobile,
    isBannerCollapsed,
    inputText,
    sending,
    showUserDetailModal,
    peerWorkerProfile,
    peerWorkerReviews,
    showTaskPreview,
    taskPreview,
    showReportModal,
    isTaskEnded,
    isBlocked,
    blockReason,
    peerOnlineStatus,
    checkMobile,
    clearConversationMetaState,
  }
}
