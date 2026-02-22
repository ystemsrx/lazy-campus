<script setup lang="ts">
import HomeHeaderBar from '../components/home/HomeHeaderBar.vue'
import HomeStatsSection from '../components/home/HomeStatsSection.vue'
import HomeTaskDetailDrawer from '../components/home/HomeTaskDetailDrawer.vue'
import HomeTaskEditorModal from '../components/home/HomeTaskEditorModal.vue'
import AppToast from '../components/AppToast.vue'
import TaskManagementBottomBar from '../components/task-management/TaskManagementBottomBar.vue'
import TaskManagementDashboardSection from '../components/task-management/TaskManagementDashboardSection.vue'
import TaskManagementNavSidebar from '../components/task-management/TaskManagementNavSidebar.vue'
import TaskManagementPageTitle from '../components/task-management/TaskManagementPageTitle.vue'
import { useTaskManagement } from '../composables/task-management/useTaskManagement'

const {
  appTitle,
  activeView,
  activeRole,
  activeStatus,
  loading,
  myPublished,
  myAccepted,
  categories,
  showCreateModal,
  showEditModal,
  toast,
  clearToast,
  newTask,
  editTaskForm,
  selectedTask,
  taskMessages,
  taskReviews,
  publisherHistoryReviews,
  chatContent,
  showReviewForm,
  reviewForm,
  reportForm,
  assigneeTotal,
  publisherTotal,
  assigneeProgress,
  publisherPending,
  currentTasks,
  displayedTasks,
  hasMore,
  loadingMore,
  emptyText,
  taskGroups,
  me,
  isAuthenticated,
  displayName,
  isParticipant,
  isPublisher,
  canAccept,
  genderMismatch,
  canConfirm,
  canEditTask,
  canDeleteTask,
  deleteBlockedByAssignee,
  myReviewTargetRole,
  hasAlreadyReviewed,
  bothSidesReviewed,
  waitingForOtherReview,
  canReview,
  canReport,
  statusOf,
  genderLabel,
  openSettings,
  openReports,
  logout,
  goLogin,
  handleHeaderTabChange,
  handleAcceptTask,
  handleConfirmTask,
  submitMessage,
  submitReview,
  handleDeleteTask,
  openEditModal,
  submitEditTask,
  submitReport,
  openCreateTask,
  submitCreateTask,
  closeDrawer,
  openTaskDetail,
  setSentinelRef,
  formatShort,
  formatFull,
  isExpired,
  nowLocal,
} = useTaskManagement()
</script>

<template>
  <div class="tm-page">
    <AppToast :toast="toast" @dismiss="clearToast" />

    <HomeHeaderBar
      :active-tab="null"
      :app-title="appTitle"
      :is-authenticated="isAuthenticated"
      :display-name="displayName"
      :avatar-url="me?.avatar_url"
      :gender="me?.gender ?? null"
      @publish="openCreateTask"
      @open-my-panel="() => {}"
      @open-settings="openSettings"
      @open-reports="openReports"
      @login="goLogin"
      @logout="logout"
      @update:active-tab="handleHeaderTabChange"
    />

    <div class="tm-body">
      <TaskManagementNavSidebar
        :active-view="activeView"
        @update:active-view="activeView = $event"
        @create="openCreateTask"
      />

      <main class="tm-main">
        <TaskManagementPageTitle />

        <div class="tm-content">
          <TaskManagementDashboardSection
            v-if="activeView === 'dashboard'"
            :loading="loading"
            :active-role="activeRole"
            :active-status="activeStatus"
            :assignee-total="assigneeTotal"
            :assignee-progress="assigneeProgress"
            :publisher-total="publisherTotal"
            :publisher-pending="publisherPending"
            :current-tasks="currentTasks"
            :displayed-tasks="displayedTasks"
            :task-groups="taskGroups"
            :has-more="hasMore"
            :loading-more="loadingMore"
            :empty-text="emptyText"
            :status-of="statusOf"
            :is-expired="isExpired"
            :format-short="formatShort"
            :set-sentinel-ref="setSentinelRef"
            @update:active-role="activeRole = $event"
            @update:active-status="activeStatus = $event"
            @open-task="openTaskDetail"
          />

          <HomeStatsSection
            v-else
            :my-accepted="myAccepted"
            :my-published="myPublished"
            :categories="categories"
          />
        </div>
      </main>
    </div>

    <TaskManagementBottomBar
      :active-view="activeView"
      @update:active-view="activeView = $event"
      @create="openCreateTask"
    />

    <HomeTaskEditorModal
      v-model="showCreateModal"
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

    <HomeTaskDetailDrawer
      :task="selectedTask"
      :is-authenticated="isAuthenticated"
      :me-id="me?.id ?? null"
      :is-participant="isParticipant"
      :is-publisher="isPublisher"
      :can-accept="canAccept"
      :gender-mismatch="genderMismatch"
      :can-confirm="canConfirm"
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
      :report-form="reportForm"
      :status-of="statusOf"
      :gender-label="genderLabel"
      :is-expired="isExpired"
      :format-full="formatFull"
      @close="closeDrawer"
      @login="goLogin"
      @accept-task="handleAcceptTask"
      @confirm-task="handleConfirmTask"
      @edit-task="openEditModal"
      @delete-task="handleDeleteTask"
      @update:chat-content="chatContent = $event"
      @submit-message="submitMessage"
      @update:show-review-form="showReviewForm = $event"
      @submit-review="submitReview"
      @submit-report="submitReport"
    />
  </div>
</template>

<style scoped>
.tm-page {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  min-height: 100dvh;
  background: #f8fafc;
  font-family: var(--font-sans);
  width: 100%;
  overflow-x: hidden;
}

.tm-body {
  display: flex;
  flex: 1;
  min-width: 0;
}

.tm-main {
  flex: 1;
  min-width: 0;
  margin-left: 80px;
  display: flex;
  flex-direction: column;
  min-height: calc(100vh - 60px);
  min-height: calc(100dvh - 60px);
}

.tm-content {
  flex: 1;
  padding: 24px 32px 32px;
  min-width: 0;
  overflow-x: hidden;
}

.tm-content::-webkit-scrollbar {
  width: 6px;
}

.tm-content::-webkit-scrollbar-track {
  background: transparent;
}

.tm-content::-webkit-scrollbar-thumb {
  background-color: #cbd5e1;
  border-radius: 20px;
}

.tm-content:hover::-webkit-scrollbar-thumb {
  background-color: #94a3b8;
}

@media (max-width: 900px) {
  .tm-main {
    margin-left: 0;
    padding-bottom: 80px;
    min-height: calc(100vh - 60px);
    min-height: calc(100dvh - 60px);
  }

  .tm-content {
    padding: 16px;
  }
}
</style>
