<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { MessageSquare, Star, User as UserIcon, X } from 'lucide-vue-next'

import AppToast from '../components/AppToast.vue'
import ChatAttachmentModal from '../components/chat/ChatAttachmentModal.vue'
import ChatConversationSidebar from '../components/chat/ChatConversationSidebar.vue'
import ChatHeaderPanel from '../components/chat/ChatHeaderPanel.vue'
import ChatInputArea from '../components/chat/ChatInputArea.vue'
import ChatMessageList from '../components/chat/ChatMessageList.vue'
import HomeHeaderBar from '../components/home/HomeHeaderBar.vue'
import HomeReportModal from '../components/home/HomeReportModal.vue'
import HomeAvatar from '../components/home/ui/HomeAvatar.vue'
import HomeStars from '../components/home/ui/HomeStars.vue'
import { fetchTask } from '../api/tasks'
import { fetchUserReviews, fetchWorkerDetail } from '../api/users'
import { sendMessage } from '../api/chat'
import { blockUser, unblockUser } from '../api/moderation'
import { appConfirm } from '../components/AppConfirm.vue'
import { useChatAttachments } from '../composables/chat/useChatAttachments'
import { convKey } from '../composables/chat/conversationKey'
import { useConversationListInteraction } from '../composables/chat/useConversationListInteraction'
import { getSnapshotStatusMap } from '../composables/chat/taskSnapshotStatus'
import { useChatSync } from '../composables/chat/useChatSync'
import { useAppToast } from '../composables/useAppToast'
import { useAuthStore } from '../stores/auth'
import { useNotificationStore } from '../stores/notifications'
import type { Task, UserReview, WorkerProfile } from '../types/api'
import type { Conversation } from '../types/chat'
import { formatFull, formatLastSeen, isExpired } from '../utils/time'
import { getTaskIcon } from '../utils/taskIcons'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const notificationStore = useNotificationStore()

const myId = computed(() => auth.user?.id ?? 0)

const appTitle = import.meta.env.VITE_APP_TITLE || '校园任务平台'
const isAuthenticated = computed(() => auth.isAuthenticated)
const displayName = computed(() => auth.displayName)
const avatarUrl = computed(() => auth.user?.avatar_url ?? null)
const avatarGender = computed(() => auth.user?.gender ?? null)

const isMobile = ref(typeof window !== 'undefined' ? window.innerWidth < 768 : false)
const isBannerCollapsed = ref(false)

const inputText = ref('')
const sending = ref(false)

const showUserDetailModal = ref(false)
const peerWorkerProfile = ref<WorkerProfile | null>(null)
const peerWorkerReviews = ref<UserReview[]>([])

const showTaskPreview = ref(false)
const taskPreview = ref<Task | null>(null)

const showReportModal = ref(false)

const { toast, showToast, clearToast } = useAppToast()

const statusMap = getSnapshotStatusMap()

type ChatMessageListExpose = {
  scrollToBottom: () => void
  saveScrollPos: () => void
  restoreScrollPos: () => void
}

const messageListRef = ref<ChatMessageListExpose | null>(null)

function scrollToBottom() {
  messageListRef.value?.scrollToBottom()
}

async function prefetchTaskDetail(taskId: number) {
  try {
    taskPreview.value = await fetchTask(taskId)
  } catch {
    // ignore
  }
}

async function prefetchPeerProfile(peerId: number) {
  try {
    const [profile, reviews] = await Promise.all([
      fetchWorkerDetail(peerId),
      fetchUserReviews(peerId, 'worker'),
    ])

    peerWorkerProfile.value = profile
    peerWorkerReviews.value = reviews
  } catch {
    // ignore worker profile errors
  }
}

let loadAttachmentsHook: () => Promise<void> = async () => {}
let resetAttachmentsHook: () => void = () => {}
let autoUnhideUnreadHook: (conversations: Conversation[]) => void = () => {}

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
    taskPreview.value = null
    peerWorkerProfile.value = null
    peerWorkerReviews.value = []
  },
  onLoadAttachments: () => loadAttachmentsHook(),
  onPrefetchPeerProfile: prefetchPeerProfile,
  onPrefetchTaskDetail: prefetchTaskDetail,
  onAfterMessagesUpdated: async () => {
    await nextTick()
    scrollToBottom()
  },
  pollNotificationCount: () => {
    notificationStore.pollCount()
  },
})

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
    scrollToBottom()
  },
})

loadAttachmentsHook = loadAllAttachments
resetAttachmentsHook = resetAttachments

const isBlocked = computed(() => {
  if (!activeConversation.value) return false
  return activeConversation.value.blocked_by_me || activeConversation.value.blocked_by_them
})

const blockReason = computed(() => {
  if (!activeConversation.value) return ''
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
  isMobile.value = window.innerWidth < 768
}

async function handleSelectConversation(conversation: Conversation) {
  unhideConversation(convKey(conversation))
  await selectConversation(conversation)
}

async function handleLoadMore() {
  messageListRef.value?.saveScrollPos()
  await loadMoreMessages()
  await nextTick()
  messageListRef.value?.restoreScrollPos()
}

function handleSearchQueryUpdate(value: string) {
  searchQuery.value = value
}

async function handleSend() {
  if (!inputText.value.trim() || !activeConversation.value || isBlocked.value || sending.value) return

  sending.value = true

  try {
    const message = await sendMessage(
      activeConversation.value.peer_id,
      inputText.value.trim(),
      activeConversation.value.task_id,
    )

    messages.value.push(message)
    inputText.value = ''

    await nextTick()
    scrollToBottom()
    loadConversations()
  } catch {
    // ignore
  }

  sending.value = false
}

function openTaskDetail() {
  if (!activeConversation.value?.task_id) return
  showTaskPreview.value = true
}

function openUserDetail() {
  if (!activeConversation.value) return
  showUserDetailModal.value = true
}

function openReportModal() {
  if (!activeConversation.value) return
  showReportModal.value = true
}

async function handleBlockToggle() {
  if (!activeConversation.value) return

  const conversation = activeConversation.value

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
      showToast(`已解除对「${conversation.peer_name}」的拉黑`, 'success')
      await loadConversations()
    } catch (error: any) {
      showToast(error?.response?.data?.detail || '操作失败', 'error')
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
    showToast(`已拉黑「${conversation.peer_name}」`, 'success')
    await loadConversations()
  } catch (error: any) {
    showToast(error?.response?.data?.detail || '操作失败', 'error')
  }
}

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
      @open-my-panel="router.push('/?panel=my')"
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

      <Teleport to="body">
        <Transition name="modal-fade">
          <div v-if="showTaskPreview" class="modal-overlay" @click.self="showTaskPreview = false">
            <div class="modal-panel task-preview-panel">
              <div class="modal-header">
                <div class="task-preview-icon" :style="{ background: getTaskIcon(taskPreview?.icon ?? null).bg }">
                  <component
                    :is="getTaskIcon(taskPreview?.icon ?? null).component"
                    :size="16"
                    :style="{ color: getTaskIcon(taskPreview?.icon ?? null).color }"
                  />
                </div>
                <h3>{{ taskPreview?.title || '加载中…' }}</h3>
                <button class="icon-btn" @click="showTaskPreview = false">
                  <X :size="20" />
                </button>
              </div>

              <div v-if="!taskPreview" class="modal-body task-preview-loading">
                <div class="spinner"></div>
              </div>

              <div v-else class="modal-body task-preview-body">
                <div class="task-preview-meta">
                  <span class="task-preview-price">¥{{ taskPreview.price }}</span>
                  <span class="task-preview-status" :class="statusMap[taskPreview.status]?.cls">
                    {{ statusMap[taskPreview.status]?.label ?? taskPreview.status }}
                  </span>
                </div>

                <div v-if="taskPreview.description" class="task-preview-desc">
                  {{ taskPreview.description }}
                </div>

                <div class="task-preview-fields">
                  <div v-if="taskPreview.deadline" class="task-preview-field">
                    <span class="field-label">截止时间</span>
                    <span class="field-value" :class="{ 'field-expired': isExpired(taskPreview.deadline) }">
                      {{ formatFull(taskPreview.deadline) }}{{ isExpired(taskPreview.deadline) ? '（已过期）' : '' }}
                    </span>
                  </div>

                  <div v-if="taskPreview.location" class="task-preview-field">
                    <span class="field-label">地点</span>
                    <span class="field-value">{{ taskPreview.location }}</span>
                  </div>

                  <div class="task-preview-field">
                    <span class="field-label">发布者</span>
                    <span class="field-value">{{ taskPreview.publisher_display_name }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </Transition>
      </Teleport>

      <Teleport to="body">
        <Transition name="modal-fade">
          <div v-if="showUserDetailModal" class="modal-overlay" @click.self="showUserDetailModal = false">
            <div class="modal-panel user-detail-panel">
              <div class="modal-header">
                <UserIcon :size="18" class="header-icon-accent" />
                <h3>用户资料</h3>
                <button class="icon-btn" @click="showUserDetailModal = false">
                  <X :size="20" />
                </button>
              </div>

              <div class="modal-body user-detail-body">
                <div class="user-detail-section user-detail-top-section">
                  <div class="user-detail-card">
                    <HomeAvatar
                      :avatar-url="activeConversation?.peer_avatar ?? null"
                      :gender="activeConversation?.peer_gender ?? null"
                      size="xl"
                      :alt="activeConversation?.peer_name ?? ''"
                      class="user-detail-avatar"
                    />

                    <div class="user-detail-info">
                      <h4 class="user-detail-name">{{ activeConversation?.peer_name }}</h4>

                      <div class="user-detail-tags">
                        <span class="user-tag gender-tag">
                          {{
                            activeConversation?.peer_gender === 'male'
                              ? '男'
                              : activeConversation?.peer_gender === 'female'
                                ? '女'
                                : '未知性别'
                          }}
                        </span>

                        <span class="user-tag online-tag" :class="{ 'online-active': peerOnlineStatus.online }">
                          {{ peerOnlineStatus.text }}
                        </span>
                      </div>

                      <template v-if="peerWorkerProfile">
                        <div class="user-worker-rating">
                          <HomeStars :value="Math.round(peerWorkerProfile.overall_rating_avg)" size="sm" />
                          <span class="rating-text">
                            {{
                              peerWorkerProfile.overall_rating_count > 0
                                ? `${peerWorkerProfile.overall_rating_avg.toFixed(1)} 分 · ${peerWorkerProfile.overall_rating_count} 评价`
                                : '暂无评分'
                            }}
                          </span>
                        </div>
                      </template>
                    </div>
                  </div>

                  <template v-if="peerWorkerProfile">
                    <div v-if="peerWorkerProfile.skill_tags.length" class="worker-skills">
                      <span v-for="tag in peerWorkerProfile.skill_tags" :key="tag.id" class="skill-chip">
                        {{ tag.name }}
                      </span>
                    </div>

                    <div class="hv-detail-grid">
                      <div class="hv-detail-item">
                        <span class="hv-detail-label">完成任务</span>
                        <span>{{ peerWorkerProfile.worker_completed_count }} 单</span>
                      </div>

                      <div class="hv-detail-item">
                        <span class="hv-detail-label">被拉黑</span>
                        <span>{{ peerWorkerProfile.blocked_by_count }} 次</span>
                      </div>

                      <div
                        v-if="peerWorkerProfile.min_price != null || peerWorkerProfile.max_price != null"
                        class="hv-detail-item"
                      >
                        <span class="hv-detail-label">报价区间</span>
                        <span>¥{{ peerWorkerProfile.min_price ?? '—' }} ~ ¥{{ peerWorkerProfile.max_price ?? '—' }}</span>
                      </div>
                    </div>

                    <p v-if="peerWorkerProfile.bio" class="worker-bio">
                      {{ peerWorkerProfile.bio }}
                    </p>
                  </template>

                  <p v-else class="user-detail-no-worker">该用户暂未开通接单服务</p>
                </div>

                <template v-if="peerWorkerProfile">
                  <div class="user-detail-section">
                    <h4 class="user-detail-section-title">
                      <Star :size="14" />
                      历史评价
                    </h4>

                    <div v-if="peerWorkerReviews.length" class="user-reviews">
                      <div v-for="review in peerWorkerReviews" :key="review.id" class="user-review-item">
                        <div class="user-review-header">
                          <HomeStars :value="review.stars" size="sm" />
                          <span class="user-review-meta">
                            来自 {{ review.reviewer_display_name }} · {{ formatFull(review.created_at) }}
                          </span>
                        </div>
                        <p v-if="review.comment" class="user-review-comment">{{ review.comment }}</p>
                      </div>
                    </div>

                    <p v-else class="user-detail-hint">暂无历史评价</p>
                  </div>
                </template>
              </div>
            </div>
          </div>
        </Transition>
      </Teleport>

      <HomeReportModal
        v-model="showReportModal"
        :task-id="activeConversation?.task_id ?? null"
        :reported-user-id="activeConversation?.peer_id ?? null"
        :reported-user-name="activeConversation?.peer_name"
        @success="showToast('举报已提交，请等待管理员审核', 'success')"
        @error="(msg) => showToast(msg, 'error')"
      />

      <AppToast :toast="toast" @dismiss="clearToast" />
    </div>
  </div>
</template>

<style scoped>
.chat-outer {
  display: flex;
  flex-direction: column;
  height: 100dvh;
  width: 100%;
  overflow: hidden;
}

.chat-page {
  display: flex;
  flex: 1;
  min-height: 0;
  width: 100%;
  background: var(--c-bg);
  color: var(--c-text);
  overflow: hidden;
}

@keyframes chat-rise {
  from {
    opacity: 0;
    transform: translateY(16px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.chat-main {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
  background: #f8fafc;
  position: relative;
  animation: chat-rise 0.48s cubic-bezier(0.22, 1, 0.36, 1) 0.08s both;
}

.chat-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--c-text-muted);
  gap: 16px;
}

.empty-icon {
  opacity: 0.15;
}

.icon-btn {
  padding: 8px;
  border-radius: 50%;
  background: transparent;
  border: none;
  color: var(--c-text-muted);
  cursor: pointer;
  transition: all var(--dur-fast) var(--ease);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}

.icon-btn:hover {
  background: var(--c-bg);
  color: var(--c-text);
}

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  backdrop-filter: blur(4px);
}

.modal-panel {
  background: var(--c-surface);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xl);
  width: min(480px, 92vw);
  max-height: 80vh;
  display: flex;
  flex-direction: column;
}

.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.22s var(--ease);
}

.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}

.modal-fade-enter-active .modal-panel,
.modal-fade-leave-active .modal-panel {
  transition:
    transform 0.22s var(--ease),
    opacity 0.22s var(--ease);
}

.modal-fade-enter-from .modal-panel {
  transform: scale(0.95) translateY(10px);
  opacity: 0;
}

.modal-fade-leave-to .modal-panel {
  transform: scale(0.96) translateY(6px);
  opacity: 0;
}

.modal-header {
  padding: 16px 20px;
  border-bottom: 1px solid var(--c-border);
  display: flex;
  align-items: center;
  gap: 12px;
}

.modal-header h3 {
  font-size: var(--text-lg);
  font-weight: 700;
  flex: 1;
}

.modal-body {
  padding: 16px 20px;
  overflow-y: auto;
  flex: 1;
}

.status-open {
  color: var(--c-accent);
}

.status-active {
  color: var(--c-warning);
}

.status-done {
  color: var(--c-success);
}

.status-canceled {
  color: var(--c-text-muted);
}

.task-preview-panel {
  width: min(440px, 92vw);
}

.task-preview-icon {
  padding: 6px;
  border-radius: 8px;
  flex-shrink: 0;
  display: flex;
}

.task-preview-loading {
  display: flex;
  justify-content: center;
  padding: 32px;
}

.task-preview-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.task-preview-meta {
  display: flex;
  align-items: center;
  gap: 10px;
}

.task-preview-price {
  font-size: var(--text-xl, 1.25rem);
  font-weight: 700;
  color: var(--c-accent);
}

.task-preview-status {
  font-size: var(--text-sm);
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 99px;
  background: var(--c-bg);
}

.task-preview-desc {
  font-size: var(--text-sm);
  color: var(--c-text-secondary);
  line-height: 1.6;
  white-space: pre-wrap;
}

.task-preview-fields {
  display: flex;
  flex-direction: column;
  gap: 6px;
  border-top: 1px solid var(--c-border);
  padding-top: 10px;
}

.task-preview-field {
  display: flex;
  gap: 8px;
  font-size: var(--text-sm);
}

.field-label {
  color: var(--c-text-muted);
  flex-shrink: 0;
  width: 56px;
}

.field-value {
  color: var(--c-text);
  font-weight: 500;
}

.field-expired {
  color: var(--c-danger);
}

.user-detail-panel {
  width: min(440px, 92vw);
}

.header-icon-accent {
  color: var(--c-accent);
  flex-shrink: 0;
}

.user-detail-body {
  display: flex;
  flex-direction: column;
  padding: 0;
  gap: 0;
}

.user-detail-section {
  padding: 16px 20px;
  border-bottom: 1px solid var(--c-border-light);
}

.user-detail-top-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.user-detail-card {
  display: flex;
  align-items: flex-start;
  gap: 14px;
}

.user-detail-avatar :deep(img) {
  border: 2px solid var(--c-border);
  box-shadow: var(--shadow-sm);
}

.user-detail-info {
  display: flex;
  flex-direction: column;
  gap: 5px;
  flex: 1;
  min-width: 0;
}

.user-detail-name {
  font-size: var(--text-lg);
  font-weight: 700;
  color: var(--c-text);
  margin: 0;
}

.user-detail-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.user-tag {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 99px;
  background: var(--c-bg);
  color: var(--c-text-secondary);
  border: 1px solid var(--c-border);
}

.gender-tag {
  background: #ede9fe;
  color: #7c3aed;
  border-color: #ddd6fe;
}

.online-active {
  background: #dcfce7;
  color: #16a34a;
  border-color: #bbf7d0;
}

.user-worker-rating {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 2px;
}

.rating-text {
  font-size: var(--text-xs);
  color: var(--c-text-muted);
}

.hv-detail-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.hv-detail-item {
  display: flex;
  flex-direction: column;
  gap: 3px;
  font-size: var(--text-sm);
}

.hv-detail-label {
  color: var(--c-text-muted);
  font-size: var(--text-xs);
}

.worker-bio {
  font-size: var(--text-sm);
  color: var(--c-text-secondary);
  line-height: 1.65;
  white-space: pre-wrap;
  margin: 0;
}

.worker-skills {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.skill-chip {
  display: inline-block;
  font-size: var(--text-sm);
  font-weight: 500;
  padding: 4px 12px;
  border-radius: var(--radius-full);
  background: var(--c-accent-light);
  color: var(--c-accent);
}

.user-detail-no-worker {
  color: var(--c-text-muted);
  font-size: var(--text-sm);
  margin: 0;
}

.user-detail-section-title {
  margin: 0 0 10px;
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--c-text-secondary);
  display: flex;
  align-items: center;
  gap: 6px;
}

.user-reviews {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.user-review-item {
  padding: 10px 12px;
  background: var(--c-bg);
  border-radius: var(--radius-md);
}

.user-review-header {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 4px;
}

.user-review-meta {
  color: var(--c-text-muted);
  font-size: var(--text-xs);
}

.user-review-comment {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--c-text-secondary);
  line-height: 1.5;
}

.user-detail-hint {
  color: var(--c-text-muted);
  font-size: var(--text-sm);
  margin: 0;
}

@media (max-width: 768px) {
  .main-hidden {
    display: none;
  }

  .chat-main {
    width: 100%;
  }
}
</style>
