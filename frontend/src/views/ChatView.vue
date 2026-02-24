<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { MessageSquare } from 'lucide-vue-next'

import AppToast from '../components/AppToast.vue'
import ChatAttachmentModal from '../components/chat/ChatAttachmentModal.vue'
import ChatPaymentQrLightbox from '../components/chat/ChatPaymentQrLightbox.vue'
import ChatConversationSidebar from '../components/chat/ChatConversationSidebar.vue'
import ChatHeaderPanel from '../components/chat/ChatHeaderPanel.vue'
import ChatInputArea from '../components/chat/ChatInputArea.vue'
import ChatMessageList from '../components/chat/ChatMessageList.vue'
import ChatTaskPreviewModal from '../components/chat/ChatTaskPreviewModal.vue'
import ChatUserDetailModal from '../components/chat/ChatUserDetailModal.vue'
import HomeHeaderBar from '../components/home/HomeHeaderBar.vue'
import HomeReportModal from '../components/home/HomeReportModal.vue'
import { getSnapshotStatusMap } from '../composables/chat/taskSnapshotStatus'
import { useChatAttachments } from '../composables/chat/useChatAttachments'
import { useChatSync } from '../composables/chat/useChatSync'
import { useConversationListInteraction } from '../composables/chat/useConversationListInteraction'
import { useChatViewActions, type ChatMessageListExpose } from '../composables/chat/useChatViewActions'
import { useChatViewUiState } from '../composables/chat/useChatViewUiState'
import { useAppToast } from '../composables/useAppToast'
import { useAuthStore } from '../stores/auth'
import { useNotificationStore } from '../stores/notifications'
import type { Conversation } from '../types/chat'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const notificationStore = useNotificationStore()

const appTitle = import.meta.env.VITE_APP_TITLE || '校园任务平台'
const myId = computed(() => auth.user?.id ?? 0)
const isAuthenticated = computed(() => auth.isAuthenticated)
const displayName = computed(() => auth.displayName)
const avatarUrl = computed(() => auth.user?.avatar_url ?? null)
const avatarGender = computed(() => auth.user?.gender ?? null)

const isMobile = ref(typeof window !== 'undefined' ? window.innerWidth < 768 : false)
const { toast, showToast, clearToast } = useAppToast()
const statusMap = getSnapshotStatusMap()

const messageListRef = ref<ChatMessageListExpose | null>(null)
const showPaymentQrLightbox = ref(false)

let loadAttachmentsHook: () => Promise<void> = async () => {}
let resetAttachmentsHook: () => void = () => {}
let autoUnhideUnreadHook: (conversations: Conversation[]) => void = () => {}
let prefetchTaskDetailHook: (taskId: number) => Promise<void> = async () => {}
let prefetchPeerProfileHook: (peerId: number) => Promise<void> = async () => {}
let clearConversationMetaStateHook: () => void = () => {}
let scrollToBottomHook: () => void = () => {}

const {
  conversations,
  activeConversation,
  messages,
  loading,
  hasMore,
  loadingMore,
  loadConversations,
  loadMoreMessages,
  selectConversation,
  goBack,
} = useChatSync({
  route,
  router,
  isMobile,
  onConversationsRefreshed: (freshConversations) => {
    autoUnhideUnreadHook(freshConversations)
  },
  onBeforeSelectConversation: () => {
    resetAttachmentsHook()
    clearConversationMetaStateHook()
  },
  onLoadAttachments: () => loadAttachmentsHook(),
  onPrefetchPeerProfile: (peerId) => prefetchPeerProfileHook(peerId),
  onPrefetchTaskDetail: (taskId) => prefetchTaskDetailHook(taskId),
  onAfterMessagesUpdated: async () => {
    await nextTick()
    scrollToBottomHook()
  },
  pollNotificationCount: () => {
    notificationStore.pollCount()
  },
})

const {
  isBannerCollapsed,
  inputText,
  sending,
  showUserDetailModal,
  peerWorkerProfile,
  peerWorkerReviews,
  showTaskPreview,
  taskPreview,
  showReportModal,
  isBlocked,
  blockReason,
  peerOnlineStatus,
  checkMobile,
  clearConversationMetaState,
} = useChatViewUiState(activeConversation, isMobile)

clearConversationMetaStateHook = clearConversationMetaState

const {
  searchQuery,
  filteredConversations,
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
} = useConversationListInteraction({
  userId: auth.user?.id ?? null,
  conversations,
  activeConversation,
})

autoUnhideUnreadHook = autoUnhideUnread

const {
  showAttachmentModal,
  attachments,
  attachmentCount,
  uploadingFile,
  loadAllAttachments,
  openAttachmentModal,
  resetAttachments,
  handleFileUpload,
  handleDeleteAttachment,
} = useChatAttachments({
  activeConversation,
  messages,
  showToast,
  onAfterMessageAppended: async () => {
    await nextTick()
    scrollToBottomHook()
  },
})

loadAttachmentsHook = loadAllAttachments
resetAttachmentsHook = resetAttachments

const {
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
} = useChatViewActions({
  activeConversation,
  messages,
  inputText,
  sending,
  isBlocked,
  searchQuery,
  messageListRef,
  showTaskPreview,
  showUserDetailModal,
  showReportModal,
  taskPreview,
  peerWorkerProfile,
  peerWorkerReviews,
  selectConversation,
  loadConversations,
  loadMoreMessages,
  unhideConversation,
  showToast,
})

prefetchTaskDetailHook = prefetchTaskDetail
prefetchPeerProfileHook = prefetchPeerProfile
scrollToBottomHook = scrollToBottom

onMounted(() => {
  checkMobile()
  window.addEventListener('resize', checkMobile)
})

onUnmounted(() => {
  window.removeEventListener('resize', checkMobile)
})
</script>

<template>
  <div class="chat-outer">
    <HomeHeaderBar
      :active-tab="null"
      :app-title="appTitle"
      :is-authenticated="isAuthenticated"
      :display-name="displayName"
      :avatar-url="avatarUrl"
      :gender="avatarGender"
      @publish="router.push('/')"
      @open-my-panel="router.push('/tasks')"
      @open-settings="router.push('/settings')"
      @open-reports="router.push('/reports')"
      @open-chat="router.push('/chat')"
      @login="router.push('/login')"
      @logout="auth.logout(); router.push('/login')"
      @update:active-tab="(tab) => router.push(tab === 'workers' ? '/?tab=workers' : '/')"
    />

    <div class="chat-page" @click="closeContextMenu()" @contextmenu.self="closeContextMenu()">
      <ChatConversationSidebar
        :conversations="filteredConversations"
        :active-conversation="activeConversation"
        :is-mobile="isMobile"
        :is-hidden="Boolean(activeConversation && isMobile)"
        :swiped-key="swipedKey"
        :ctx-menu="contextMenu"
        :search-query="searchQuery"
        @update:search-query="handleSearchQueryUpdate"
        @select="handleSelectConversation"
        @hide="hideConversation"
        @swipe-start="onSwipeStart($event.event, $event.key)"
        @swipe-move="onSwipeMove($event.event, $event.key)"
        @swipe-end="onSwipeEnd"
        @open-context-menu="onContextMenu($event.event, $event.key)"
        @close-swipe="closeSwipe"
        @close-context-menu="closeContextMenu"
      />

      <main class="chat-main" :class="{ 'main-hidden': !activeConversation && isMobile }">
        <div v-if="!activeConversation" class="chat-empty">
          <MessageSquare :size="64" class="empty-icon" />
          <p>从左侧选择一个联系人开始聊天</p>
        </div>

        <template v-else>
          <ChatHeaderPanel
            :conversation="activeConversation"
            :is-mobile="isMobile"
            :is-blocked="isBlocked"
            :is-banner-collapsed="isBannerCollapsed"
            :attachment-count="attachmentCount.count"
            :peer-online-status="peerOnlineStatus"
            @back="goBack"
            @open-report="openReportModal"
            @toggle-block="handleBlockToggle"
            @open-attachments="openAttachmentModal"
            @toggle-banner="isBannerCollapsed = !isBannerCollapsed"
            @open-task-detail="openTaskDetail"
            @open-user-detail="openUserDetail"
            @open-payment-qr="showPaymentQrLightbox = true"
          />

          <ChatMessageList
            ref="messageListRef"
            :messages="messages"
            :loading="loading"
            :my-id="myId"
            :conversation="activeConversation"
            :attachments="attachments"
            :has-more="hasMore"
            :loading-more="loadingMore"
            @missing-attachment="showToast('文件不存在', 'warning')"
            @load-more="handleLoadMore"
          />

          <ChatInputArea
            v-model="inputText"
            :is-blocked="isBlocked"
            :block-reason="blockReason"
            :is-mobile="isMobile"
            :sending="sending"
            :uploading-file="uploadingFile"
            @send="handleSend"
            @upload="handleFileUpload"
          />
        </template>
      </main>

      <ChatAttachmentModal
        v-model="showAttachmentModal"
        :attachments="attachments"
        :attachment-count="attachmentCount"
        :my-id="myId"
        @delete="handleDeleteAttachment"
      />

      <ChatTaskPreviewModal
        v-model="showTaskPreview"
        :task-preview="taskPreview"
        :status-map="statusMap"
      />

      <ChatUserDetailModal
        v-model="showUserDetailModal"
        :conversation="activeConversation"
        :peer-online-status="peerOnlineStatus"
        :peer-worker-profile="peerWorkerProfile"
        :peer-worker-reviews="peerWorkerReviews"
      />

      <HomeReportModal
        v-model="showReportModal"
        :task-id="activeConversation?.task_id ?? null"
        :reported-user-id="activeConversation?.peer_id ?? null"
        :reported-user-name="activeConversation?.peer_name"
        @success="showToast('举报已提交，请等待管理员审核', 'success')"
        @error="(msg) => showToast(msg, 'error')"
      />

      <ChatPaymentQrLightbox
        v-model="showPaymentQrLightbox"
        :qr-url="activeConversation?.peer_payment_qr_url ?? null"
      />

      <AppToast :toast="toast" @dismiss="clearToast" />
    </div>
  </div>
</template>

<style scoped src="./chat-view.css"></style>
