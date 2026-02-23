<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import HomeHallSection from '../components/home/HomeHallSection.vue'
import HomeHeaderBar from '../components/home/HomeHeaderBar.vue'
import HomeLoadingState from '../components/home/HomeLoadingState.vue'
import HomeMyTasksDrawer from '../components/home/HomeMyTasksDrawer.vue'
import HomeReportModal from '../components/home/HomeReportModal.vue'
import HomeTaskDetailDrawer from '../components/home/HomeTaskDetailDrawer.vue'
import HomeTaskEditorModal from '../components/home/HomeTaskEditorModal.vue'
import AppToast from '../components/AppToast.vue'
import { appSlideCaptcha } from '../components/AppSlideCaptcha.vue'
import { useAppToast } from '../composables/useAppToast'
import HomeWorkerDetailDrawer from '../components/home/HomeWorkerDetailDrawer.vue'
import HomeWorkersSection from '../components/home/HomeWorkersSection.vue'
import {
  HOME_TASK_SORT_OPTIONS,
  HOME_WORKER_SORT_OPTIONS,
  genderLabel,
  statusOf,
} from '../composables/home/model'
import { useHomeMarketplace } from '../composables/home/useHomeMarketplace'
import { useHomeTabSync } from '../composables/home/useHomeTabSync'
import { useHomeTaskDrawer } from '../composables/home/useHomeTaskDrawer'
import { useHomeWorkerDrawer } from '../composables/home/useHomeWorkerDrawer'
import { useAuthStore } from '../stores/auth'
import { useNotificationStore } from '../stores/notifications'
import type { Task } from '../types/api'
import { extractError } from '../utils/error'
import { formatFull, formatShort, isExpired, nowLocal } from '../utils/time'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const notifStore = useNotificationStore()
const appTitle = import.meta.env.VITE_APP_TITLE || '校园任务平台'
const isAuthenticated = computed(() => auth.isAuthenticated)
const me = computed(() => auth.user)

const { activeTab } = useHomeTabSync(route, router)

const showMyPanel = ref(false)

const { toast, showToast, clearToast } = useAppToast()

const {
  taskSort,
  workerSort,
  searchQuery,
  workerSearchQuery,
  selectedCategory,
  selectedWorkerCategory,
  loading,
  categories,
  allTasks,
  myPublished,
  myAccepted,
  totalWorkerCount,
  totalTaskCount,
  tasks,
  workers,
  categoryName,
  loadCategories,
  loadTasks,
  loadWorkers,
  loadMyTasks,
  bootstrap,
} = useHomeMarketplace({
  isAuthenticated: () => auth.isAuthenticated,
  onBootstrapError: (error) => {
    showToast(extractError(error, '加载失败'), 'error')
  },
})

const {
  showPostModal,
  showEditModal,
  selectedTask,
  taskMessages,
  taskReviews,
  publisherHistoryReviews,
  showReviewForm,
  newTask,
  editTaskForm,
  chatContent,
  reviewForm,
  showReportModal,
  isParticipant,
  isPublisher,
  canAccept,
  genderMismatch,
  canConfirm,
  canAbandon,
  canCancelTask,
  canRepublish,
  myReviewTargetRole,
  hasAlreadyReviewed,
  bothSidesReviewed,
  waitingForOtherReview,
  canReview,
  canDeleteTask,
  canEditTask,
  deleteBlockedByAssignee,
  canReport,
  reportTargetId,
  openDrawer: openTaskDrawer,
  closeDrawer: closeTaskDrawer,
  submitCreateTask,
  handleAcceptTask: _handleAcceptTask,
  handleConfirmTask,
  handleAbandonTask,
  handleCancelTask,
  handleRepublishTask,
  submitMessage,
  submitReview,
  handleDeleteTask,
  openEditModal,
  submitEditTask,
  openReportModal,
  handleBlockTaskUser,
} = useHomeTaskDrawer({
  me,
  isAuthenticated,
  showToast,
  pollNotificationCount: () => {
    notifStore.pollCount()
  },
  dismissTaskChatNotification: (taskId: number) => notifStore.dismissChat(taskId),
  loadTasks,
  loadMyTasks,
  loadCategories,
  loadWorkers,
  requestCaptcha: appSlideCaptcha,
})

const {
  selectedWorker,
  workerHistoryReviews,
  workerContactReveal,
  workerContactLoading,
  openWorkerDrawer,
  closeWorkerDrawer,
  handleWorkerContactAction,
  handleBlockWorkerUser,
} = useHomeWorkerDrawer({
  isAuthenticated,
  router,
  showToast,
  loadTasks,
  loadWorkers,
  requestCaptcha: appSlideCaptcha,
})

async function handleAcceptTask() {
  await _handleAcceptTask()
  if (selectedTask.value?.status === 'in_progress') {
    closeTaskDrawer()
    router.push('/tasks')
  }
}

function findTaskById(taskId: number): Task | undefined {
  return [...allTasks.value, ...myPublished.value, ...myAccepted.value].find(
    (task) => task.id === taskId,
  )
}

function consumeTaskQuery() {
  const taskQuery = route.query.task
  if (!taskQuery) return
  const taskId = Number(taskQuery)
  const task = findTaskById(taskId)
  if (task) {
    openTaskDrawer(task)
  }
  const nextQuery = { ...route.query }
  delete nextQuery.task
  router.replace({ query: nextQuery })
}

function logout() {
  closeWorkerDrawer()
  auth.logout()
  router.push('/login')
}

function openMyPanel() {
  router.push('/tasks')
}

function openSettings() {
  router.push('/settings')
}

function openReports() {
  router.push('/reports')
}

function openChat() {
  router.push('/chat')
}

watch(() => route.query.task, (newVal) => {
  if (!newVal || loading.value) return
  consumeTaskQuery()
})

onMounted(() => {
  bootstrap().then(() => {
    consumeTaskQuery()
  })
})
</script>

<template>
  <AppToast :toast="toast" @dismiss="clearToast" />

  <HomeHeaderBar
    v-model:active-tab="activeTab"
    :app-title="appTitle"
    :is-authenticated="auth.isAuthenticated"
    :display-name="auth.displayName"
    :avatar-url="me?.avatar_url"
    :gender="me?.gender ?? null"
    @publish="showPostModal = true"
    @open-my-panel="openMyPanel"
    @open-settings="openSettings"
    @open-reports="openReports"
    @open-chat="openChat"
    @login="router.push('/login')"
    @logout="logout"
  />

  <HomeLoadingState v-if="loading" />

  <main v-else class="hv-main">
    <HomeHallSection
      v-if="activeTab === 'hall'"
      v-model:search-query="searchQuery"
      v-model:task-sort="taskSort"
      v-model:selected-category="selectedCategory"
      :task-sort-options="HOME_TASK_SORT_OPTIONS"
      :categories="categories"
      :total-task-count="totalTaskCount"
      :tasks="tasks"
      :status-of="statusOf"
      :gender-label="genderLabel"
      :category-name="categoryName"
      :is-expired="isExpired"
      :format-short="formatShort"
      @open-task="openTaskDrawer"
    />

    <HomeWorkersSection
      v-if="activeTab === 'workers'"
      v-model:worker-sort="workerSort"
      v-model:selected-category="selectedWorkerCategory"
      v-model:search-query="workerSearchQuery"
      :workers="workers"
      :worker-sort-options="HOME_WORKER_SORT_OPTIONS"
      :categories="categories"
      :total-worker-count="totalWorkerCount"
      @open-worker="openWorkerDrawer"
    />
  </main>

  <button
    v-if="auth.isAuthenticated && activeTab === 'hall' && !showPostModal && !showEditModal && !selectedTask"
    class="hv-fab-publish"
    aria-label="发布任务"
    @click="showPostModal = true"
  >
    <i class="fa-solid fa-plus"></i>
  </button>

  <HomeTaskEditorModal
    v-model="showPostModal"
    mode="create"
    :form="newTask"
    :categories="categories"
    :now-local="nowLocal"
    @submit="submitCreateTask"
  />

  <HomeTaskEditorModal
    v-model="showEditModal"
    mode="edit"
    :form="editTaskForm"
    :categories="categories"
    :now-local="nowLocal"
    @submit="submitEditTask"
  />

  <HomeMyTasksDrawer
    v-model="showMyPanel"
    :my-published="myPublished"
    :my-accepted="myAccepted"
    :status-of="statusOf"
    :is-expired="isExpired"
    @open-task="openTaskDrawer"
  />

  <HomeTaskDetailDrawer
    :task="selectedTask"
    :is-authenticated="auth.isAuthenticated"
    :me-id="me?.id ?? null"
    :is-participant="isParticipant"
    :is-publisher="isPublisher"
    :can-accept="canAccept"
    :gender-mismatch="genderMismatch"
    :can-confirm="canConfirm"
    :can-abandon="canAbandon"
    :can-cancel-task="canCancelTask"
    :can-republish="canRepublish"
    :can-edit-task="canEditTask"
    :can-delete-task="canDeleteTask"
    :delete-blocked-by-assignee="deleteBlockedByAssignee"
    :task-messages="taskMessages"
    :task-reviews="taskReviews"
    :publisher-history-reviews="publisherHistoryReviews"
    :chat-content="chatContent"
    :show-review-form="showReviewForm"
    :review-form="reviewForm"
    :my-review-target-role="myReviewTargetRole"
    :has-already-reviewed="hasAlreadyReviewed"
    :both-sides-reviewed="bothSidesReviewed"
    :waiting-for-other-review="waitingForOtherReview"
    :can-review="canReview"
    :can-report="canReport"
    :status-of="statusOf"
    :gender-label="genderLabel"
    :is-expired="isExpired"
    :format-full="formatFull"
    @close="closeTaskDrawer"
    @login="router.push('/login')"
    @accept-task="handleAcceptTask"
    @confirm-task="handleConfirmTask"
    @abandon-task="handleAbandonTask"
    @cancel-task="handleCancelTask"
    @republish-task="handleRepublishTask"
    @edit-task="openEditModal"
    @delete-task="handleDeleteTask"
    @update:chat-content="chatContent = $event"
    @submit-message="submitMessage"
    @update:show-review-form="showReviewForm = $event"
    @submit-review="submitReview"
    @open-report="openReportModal"
    @block-user="handleBlockTaskUser"
  />

  <HomeReportModal
    v-model="showReportModal"
    :task-id="selectedTask?.id ?? null"
    :reported-user-id="reportTargetId"
    :reported-user-name="selectedTask ? (me?.id === selectedTask.publisher_id ? selectedTask.assignee_display_name : selectedTask.publisher_display_name) ?? undefined : undefined"
    @success="showToast('举报已提交，等待管理员审核', 'success')"
    @error="showToast($event, 'error')"
  />

  <HomeWorkerDetailDrawer
    :worker="selectedWorker"
    :reviews="workerHistoryReviews"
    :contact-reveal="workerContactReveal"
    :is-authenticated="auth.isAuthenticated"
    :me-id="me?.id ?? null"
    :reveal-loading="workerContactLoading"
    :format-full="formatFull"
    @close="closeWorkerDrawer"
    @login="router.push('/login')"
    @contact-action="handleWorkerContactAction"
    @block-user="handleBlockWorkerUser"
  />
</template>

<style scoped>
.hv-main {
  padding: 24px;
  max-width: 1200px;
  margin: 0 auto;
}

.hv-fab-publish {
  display: none;
}

@media (max-width: 900px) {
  .hv-main {
    padding: 16px;
  }

  .hv-fab-publish {
    display: flex;
    position: fixed;
    bottom: 24px;
    left: 50%;
    transform: translateX(-50%);
    width: 56px;
    height: 56px;
    border-radius: 50%;
    background: #000;
    color: #fff;
    border: none;
    align-items: center;
    justify-content: center;
    font-size: 22px;
    z-index: 200;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.35);
    cursor: pointer;
    transition: transform 0.15s var(--ease), box-shadow 0.15s var(--ease);
  }

  .hv-fab-publish:active {
    transform: translateX(-50%) scale(0.93);
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.3);
  }
}
</style>
