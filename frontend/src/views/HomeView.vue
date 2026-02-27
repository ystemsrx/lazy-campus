<script setup lang="ts">
import { computed, onActivated, onDeactivated, onMounted, ref, watch } from 'vue'
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
  canCreateWithAgent,
  canUseAgentOnSelectedTask,
  createWithAgentSubmitting,
  startingAgent,
  deleteBlockedByAssignee,
  canReport,
  reportTargetId,
  openDrawer: openTaskDrawer,
  closeDrawer: closeTaskDrawer,
  refreshAgentAvailability,
  uploadTaskImage,
  submitCreateTask,
  handleAcceptTask: _handleAcceptTask,
  handleConfirmTask,
  handleAbandonTask,
  handleCancelTask,
  handleRepublishTask,
  handleStartAgentFromSelectedTask,
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
  categories: computed(() => categories.value),
  showToast,
  pollNotificationCount: () => {
    notifStore.pollCount()
  },
  dismissTaskChatNotification: (taskId: number) => notifStore.dismissChat(taskId),
  loadTasks,
  loadMyTasks,
  loadCategories,
  loadWorkers,
  goToAgentSession: (sessionId) => {
    router.push(`/agent/${sessionId}`)
  },
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

function getRouteTaskQuery() {
  const rawTask = route.query.task
  if (Array.isArray(rawTask)) return rawTask[0]
  return rawTask
}

function getRoutePublishQuery() {
  const rawPublish = route.query.publish
  if (Array.isArray(rawPublish)) return rawPublish[0]
  return rawPublish
}

function consumeRouteQueries() {
  if (route.path !== '/') return

  const nextQuery = { ...route.query }
  let shouldReplace = false

  const taskQuery = getRouteTaskQuery()
  if (taskQuery) {
    const taskId = Number(taskQuery)
    if (Number.isFinite(taskId) && taskId > 0) {
      const task = findTaskById(taskId)
      if (task) openTaskDrawer(task)
    }
    delete nextQuery.task
    shouldReplace = true
  }

  const publishQuery = getRoutePublishQuery()
  if (publishQuery) {
    showPostModal.value = true
    delete nextQuery.publish
    shouldReplace = true
  }

  if (shouldReplace) {
    router.replace({ path: route.path, query: nextQuery })
  }
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

function openAgentTasks() {
  router.push('/agent-tasks')
}

watch(() => [route.path, route.query.task, route.query.publish, loading.value] as const, ([path, taskQuery, publishQuery, isLoading]) => {
  if (path !== '/' || isLoading || (!taskQuery && !publishQuery)) return
  consumeRouteQueries()
})

let bootstrapped = false

onMounted(() => {
  bootstrap().then(() => {
    bootstrapped = true
    consumeRouteQueries()
  })
})

onActivated(() => {
  if (bootstrapped) {
    Promise.all([loadTasks(), loadWorkers(), loadCategories()]).catch(() => {})
    refreshAgentAvailability().catch(() => {})
    if (auth.isAuthenticated) loadMyTasks().catch(() => {})
  }
})

onDeactivated(() => {
  closeTaskDrawer()
  closeWorkerDrawer()
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
    @open-agent-tasks="openAgentTasks"
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
    :show-agent-action="canCreateWithAgent"
    :agent-submitting="createWithAgentSubmitting"
    :upload-task-image="uploadTaskImage"
    @submit="submitCreateTask"
    @submit-agent="submitCreateTask('agent')"
  />

  <HomeTaskEditorModal
    v-model="showEditModal"
    mode="edit"
    :form="editTaskForm"
    :categories="categories"
    :now-local="nowLocal"
    :show-agent-action="false"
    :upload-task-image="uploadTaskImage"
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
    :can-use-agent="canUseAgentOnSelectedTask"
    :agent-starting="startingAgent"
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
    @start-agent="handleStartAgentFromSelectedTask"
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
