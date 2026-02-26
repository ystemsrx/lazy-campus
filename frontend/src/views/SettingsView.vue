<script setup lang="ts">
import AppSaveStatusBar from '../components/AppSaveStatusBar.vue'
import AppToast from '../components/AppToast.vue'
import HomeHeaderBar from '../components/home/HomeHeaderBar.vue'
import HomeTaskEditorModal from '../components/home/HomeTaskEditorModal.vue'
import SettingsBlacklistPanel from '../components/settings/SettingsBlacklistPanel.vue'
import SettingsNavTabs from '../components/settings/SettingsNavTabs.vue'
import SettingsProfilePanel from '../components/settings/SettingsProfilePanel.vue'
import SettingsWorkerPanel from '../components/settings/SettingsWorkerPanel.vue'
import { useQuickTaskPublish } from '../composables/useQuickTaskPublish'
import { useSettingsView } from '../composables/settings/useSettingsView'
import { nowLocal } from '../utils/time'

const {
  appTitle,
  toast,
  showToast,
  clearToast,
  me,
  isAuthenticated,
  displayName,
  loading,
  categories,
  activeTab,
  indicatorStyle,
  setTabRef,
  profileForm,
  workerForm,
  avatarUploading,
  paymentQrUploading,
  paymentQrDeleting,
  saveStatus,
  logout,
  openMyPanel,
  openSettings,
  goLogin,
  handleHeaderTabChange,
  toggleSkillTag,
  handleAvatarUpload,
  handlePaymentQrUpload,
  handlePaymentQrDelete,
} = useSettingsView()

const {
  showCreateModal,
  newTask,
  publishCategories,
  canCreateWithAgent,
  createWithAgentSubmitting,
  openPublishModal,
  submitPublishTask,
} = useQuickTaskPublish({ showToast })
</script>

<template>
  <AppToast :toast="toast" @dismiss="clearToast" />

  <div class="sv-page">
    <div class="sv-bg-gradient" />

    <HomeHeaderBar
      :active-tab="null"
      :app-title="appTitle"
      :is-authenticated="isAuthenticated"
      :display-name="displayName"
      :avatar-url="me?.avatar_url"
      :gender="me?.gender ?? null"
      @publish="openPublishModal"
      @open-my-panel="openMyPanel"
      @open-settings="openSettings"
      @open-reports="$router.push('/reports')"
      @open-chat="$router.push('/chat')"
      @open-agent-tasks="$router.push('/agent-tasks')"
      @login="goLogin"
      @logout="logout"
      @update:active-tab="handleHeaderTabChange"
    />

    <div class="sv-container">
      <header class="sv-header">
        <h1 class="sv-title">账号设置</h1>
        <p class="sv-subtitle">管理您的个人信息与接单首选项</p>
      </header>

      <div class="sv-layout">
        <template v-if="loading">
          <div class="sv-nav-skel">
            <div class="sv-skel sv-skel--nav-btn" />
            <div class="sv-skel sv-skel--nav-btn" />
          </div>

          <div class="sv-panel sv-panel-skel">
            <div class="sv-skel-section">
              <div class="sv-skel sv-skel--title" />
              <div class="sv-skel sv-skel--subtitle" />
            </div>
            <div class="sv-skel sv-skel--divider" />
            <div class="sv-skel-avatar-row">
              <div class="sv-skel sv-skel--avatar" />
              <div class="sv-skel-avatar-lines">
                <div class="sv-skel sv-skel--line-md" />
                <div class="sv-skel sv-skel--line-sm" />
              </div>
            </div>
            <div class="sv-skel-grid">
              <div v-for="i in 4" :key="i" class="sv-skel-field">
                <div class="sv-skel sv-skel--label" />
                <div class="sv-skel sv-skel--input" />
              </div>
            </div>
          </div>
        </template>

        <template v-else>
          <SettingsNavTabs
            v-model="activeTab"
            class="sv-anim-1"
            :indicator-style="indicatorStyle"
            :set-tab-ref="setTabRef"
          />

          <main class="sv-panel sv-anim-2">
            <form @submit.prevent>
              <div class="sv-tab-grid">
                <SettingsProfilePanel
                  :active="activeTab === 'profile'"
                  :me="me"
                  :profile-form="profileForm"
                  :avatar-uploading="avatarUploading"
                  :payment-qr-uploading="paymentQrUploading"
                  :payment-qr-deleting="paymentQrDeleting"
                  @avatar-upload="handleAvatarUpload"
                  @payment-qr-upload="handlePaymentQrUpload"
                  @payment-qr-delete="handlePaymentQrDelete"
                />

                <SettingsWorkerPanel
                  :active="activeTab === 'worker'"
                  :worker-form="workerForm"
                  :categories="categories"
                  @toggle-skill-tag="toggleSkillTag"
                  @enable-error="(msg) => showToast(msg, 'warning')"
                />

                <SettingsBlacklistPanel
                  :active="activeTab === 'blacklist'"
                  @toast="(msg, type) => showToast(msg, type)"
                />
              </div>

              <AppSaveStatusBar :status="saveStatus" />
            </form>
          </main>
        </template>
      </div>
    </div>

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
  </div>
</template>

<style scoped src="./settings-view.css"></style>
