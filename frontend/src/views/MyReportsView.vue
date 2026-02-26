<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'

import AppToast from '../components/AppToast.vue'
import HomeHeaderBar from '../components/home/HomeHeaderBar.vue'
import HomeTaskEditorModal from '../components/home/HomeTaskEditorModal.vue'
import LoginAppealModal from '../components/login/LoginAppealModal.vue'
import ReceivedReportsSection from '../components/reports/sections/ReceivedReportsSection.vue'
import SubmittedReportsSection from '../components/reports/sections/SubmittedReportsSection.vue'
import { useMyReportsData } from '../composables/reports/useMyReportsData'
import { useAppToast } from '../composables/useAppToast'
import { useQuickTaskPublish } from '../composables/useQuickTaskPublish'
import { useAuthStore } from '../stores/auth'
import { nowLocal } from '../utils/time'

const router = useRouter()
const auth = useAuthStore()
const appTitle = import.meta.env.VITE_APP_TITLE || '校园任务平台'
const me = computed(() => auth.user)

const { toast, showToast, clearToast } = useAppToast()
const {
  showCreateModal,
  newTask,
  publishCategories,
  canCreateWithAgent,
  createWithAgentSubmitting,
  openPublishModal,
  submitPublishTask,
} = useQuickTaskPublish({ showToast })

const {
  sections,
  tabs,
  lightboxSrc,
  activeSection,
  sectionIndex,
  loading,
  receivedReports,
  activeTab,
  tabIndex,
  filteredReports,
  selectedReportId,
  selectedReceivedId,
  selectedReport,
  selectedReceived,
  showAppealModal,
  hasPendingAppeal,
  hasAnyBan,
  activePenaltyId,
  loadReports,
  setActiveSection,
  setActiveTab,
  selectReport,
  deselectReport,
  selectReceived,
  deselectReceived,
  openAppealModal,
  onAppealSubmitted,
  openLightbox,
  closeLightbox,
} = useMyReportsData({
  me,
  showToast,
})

function handleHeaderTabChange(tab: 'hall' | 'workers' | null) {
  router.push({ path: '/', query: tab === 'workers' ? { tab: 'workers' } : {} })
}

function logout() {
  auth.logout()
  router.push('/login')
}
</script>

<template>
  <AppToast :toast="toast" @dismiss="clearToast" />

  <div class="mr-page">
    <div class="mr-bg-gradient" />

    <HomeHeaderBar
      :active-tab="null"
      :app-title="appTitle"
      :is-authenticated="auth.isAuthenticated"
      :display-name="auth.displayName"
      :avatar-url="me?.avatar_url"
      :gender="me?.gender ?? null"
      @publish="openPublishModal"
      @open-my-panel="router.push('/tasks')"
      @open-settings="router.push('/settings')"
      @open-reports="loadReports"
      @open-chat="router.push('/chat')"
      @open-agent-tasks="router.push('/agent-tasks')"
      @login="router.push('/login')"
      @logout="logout"
      @update:active-tab="handleHeaderTabChange"
    />

    <div class="mr-container">
      <header class="mr-page-header">
        <h1 class="mr-page-title">我的举报与申诉</h1>
        <p class="mr-page-subtitle">查看您提交的举报与收到的处罚</p>
      </header>

      <div class="mr-section-toggle">
        <div
          class="mr-section-slider"
          :style="{ transform: `translateX(${sectionIndex * 100}%)` }"
        />
        <button
          v-for="sec in sections"
          :key="sec.id"
          class="mr-section-btn"
          :class="{ 'mr-section-btn--active': activeSection === sec.id }"
          @click="setActiveSection(sec.id)"
        >
          <i :class="sec.icon" />
          {{ sec.label }}
          <span v-if="sec.id === 'received' && hasAnyBan" class="mr-section-count">1</span>
        </button>
      </div>

      <div v-if="loading" class="mr-layout">
        <div class="mr-skel-list">
          <div class="mr-skel mr-skel--tabs" />
          <div class="mr-skel mr-skel--card" />
          <div class="mr-skel mr-skel--card" />
          <div class="mr-skel mr-skel--card" />
        </div>
        <div class="mr-skel-detail">
          <div class="mr-skel mr-skel--banner" />
          <div class="mr-skel mr-skel--block" />
        </div>
      </div>

      <SubmittedReportsSection
        v-else-if="activeSection === 'submitted'"
        :tabs="tabs"
        :active-tab="activeTab"
        :tab-index="tabIndex"
        :reports="filteredReports"
        :selected-report-id="selectedReportId"
        :selected-report="selectedReport"
        @update:active-tab="setActiveTab"
        @select-report="selectReport"
        @deselect-report="deselectReport"
        @preview-image="openLightbox"
      />

      <ReceivedReportsSection
        v-else
        :reports="receivedReports"
        :selected-received-id="selectedReceivedId"
        :selected-received="selectedReceived"
        :active-penalty-id="activePenaltyId"
        :has-pending-appeal="hasPendingAppeal"
        :has-any-ban="hasAnyBan"
        @select-received="selectReceived"
        @deselect-received="deselectReceived"
        @preview-image="openLightbox"
        @open-appeal="openAppealModal"
      />
    </div>
  </div>

  <LoginAppealModal
    v-model="showAppealModal"
    authenticated
    :initial-ban-until="me?.ban_until ?? null"
    @submitted="onAppealSubmitted"
  />

  <HomeTaskEditorModal
    v-model="showCreateModal"
    mode="create"
    :form="newTask"
    :categories="publishCategories"
    :now-local="nowLocal"
    :show-agent-action="canCreateWithAgent"
    :agent-submitting="createWithAgentSubmitting"
    @submit="submitPublishTask"
    @submit-agent="submitPublishTask('agent')"
  />

  <Teleport to="body">
    <Transition name="mr-lb">
      <div v-if="lightboxSrc" class="mr-lightbox" @click="closeLightbox">
        <img :src="lightboxSrc" class="mr-lightbox__img" alt="证据截图预览" />
      </div>
    </Transition>
  </Teleport>
</template>

<style src="./my-reports-view.css"></style>
