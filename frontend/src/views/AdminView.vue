<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AppToast from '../components/AppToast.vue'
import AdminActionLogsSection from '../components/admin/AdminActionLogsSection.vue'
import AdminCategoriesSection from '../components/admin/AdminCategoriesSection.vue'
import AdminChatsSection from '../components/admin/AdminChatsSection.vue'
import AdminDashboardSection from '../components/admin/AdminDashboardSection.vue'
import AdminLoadingState from '../components/admin/AdminLoadingState.vue'
import AdminNotificationsSection from '../components/admin/AdminNotificationsSection.vue'
import AdminReportsSection from '../components/admin/AdminReportsSection.vue'
import AdminSidebar from '../components/admin/AdminSidebar.vue'
import type { AdminTabKey } from '../components/admin/AdminSidebar.vue'
import AdminTasksSection from '../components/admin/AdminTasksSection.vue'
import AdminUsersSection from '../components/admin/AdminUsersSection.vue'
import { useAdminActionLogs } from '../composables/admin/useAdminActionLogs'
import { useAdminCategories } from '../composables/admin/useAdminCategories'
import { useAdminChats } from '../composables/admin/useAdminChats'
import { useAdminDashboard } from '../composables/admin/useAdminDashboard'
import { useAdminNotifications } from '../composables/admin/useAdminNotifications'
import { useAdminReports } from '../composables/admin/useAdminReports'
import { useAdminTasks } from '../composables/admin/useAdminTasks'
import { useAdminUsers } from '../composables/admin/useAdminUsers'
import { useAppToast } from '../composables/useAppToast'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const validTabs = new Set<AdminTabKey>([
  'dashboard', 'reports', 'users', 'tasks', 'chats', 'notifications', 'categories', 'logs',
])

function resolveTabFromQuery(): AdminTabKey {
  const q = route.query.tab
  if (typeof q === 'string' && validTabs.has(q as AdminTabKey)) return q as AdminTabKey
  return 'dashboard'
}

const activeTab = ref<AdminTabKey>(resolveTabFromQuery())
const initialLoading = ref(true)
const sidebarMobileOpen = ref(false)

const toastModel = reactive(useAppToast())
const dashboardModel = useAdminDashboard(toastModel.showToast)
const reportsModel = useAdminReports(toastModel.showToast)
const usersModel = useAdminUsers(toastModel.showToast)
const tasksModel = useAdminTasks(toastModel.showToast)
const chatsModel = useAdminChats(toastModel.showToast)
const notificationsModel = useAdminNotifications(toastModel.showToast)
const categoriesModel = useAdminCategories(toastModel.showToast)
const actionLogsModel = useAdminActionLogs(toastModel.showToast)

const loaded = reactive<Record<AdminTabKey, boolean>>({
  dashboard: false,
  reports: false,
  users: false,
  tasks: false,
  chats: false,
  notifications: false,
  categories: false,
  logs: false,
})

const tabTitleMap: Record<AdminTabKey, string> = {
  dashboard: '运营看板',
  reports: '举报审核',
  users: '用户管理',
  tasks: '任务处置',
  chats: '聊天审计',
  notifications: '通知推送',
  categories: '类别管理',
  logs: '操作日志',
}

const tabIconMap: Record<AdminTabKey, string> = {
  dashboard: 'fa-solid fa-chart-line',
  reports: 'fa-solid fa-flag',
  users: 'fa-solid fa-users-gear',
  tasks: 'fa-solid fa-list-check',
  chats: 'fa-solid fa-comments',
  notifications: 'fa-solid fa-bullhorn',
  categories: 'fa-solid fa-tags',
  logs: 'fa-solid fa-clock-rotate-left',
}

const pageTitle = computed(() => tabTitleMap[activeTab.value])

const currentTime = ref(new Date())
let clockTimer: ReturnType<typeof setInterval>

const greeting = computed(() => {
  return currentTime.value.toLocaleDateString('zh-CN', {
    month: 'long',
    day: 'numeric',
    weekday: 'long',
  })
})

async function loadTabData(tab: AdminTabKey, force = false) {
  if (!force && loaded[tab]) return

  if (tab === 'dashboard') {
    await dashboardModel.loadDashboard()
    loaded.dashboard = true
    return
  }
  if (tab === 'reports') {
    await reportsModel.loadReports()
    loaded.reports = true
    return
  }
  if (tab === 'users') {
    await usersModel.loadUsers()
    loaded.users = true
    return
  }
  if (tab === 'tasks') {
    await tasksModel.loadTasks()
    loaded.tasks = true
    return
  }
  if (tab === 'chats') {
    await chatsModel.loadConversations()
    loaded.chats = true
    return
  }
  if (tab === 'categories') {
    await categoriesModel.loadCategories()
    loaded.categories = true
    return
  }
  if (tab === 'logs') {
    await actionLogsModel.loadLogs()
    loaded.logs = true
  }
}

async function bootstrap() {
  initialLoading.value = true
  try {
    const initial = activeTab.value
    const always = new Set<AdminTabKey>(['dashboard', 'reports'])
    always.add(initial)
    await Promise.all([...always].map(t => loadTabData(t, true)))
  } catch {
    // Errors are already surfaced by each composable via toast.
  } finally {
    initialLoading.value = false
  }
}

async function onTabChange(key: AdminTabKey) {
  activeTab.value = key
  router.replace({ query: { tab: key } })
  try {
    await loadTabData(key)
  } catch {
    // Errors are already surfaced by each composable via toast.
  }
}

function logout() {
  auth.logout()
  router.push('/login')
}

onMounted(() => {
  bootstrap()
  clockTimer = setInterval(() => { currentTime.value = new Date() }, 60000)
})

onUnmounted(() => {
  clearInterval(clockTimer)
})
</script>

<template>
  <AppToast :toast="toastModel.toast" @dismiss="toastModel.clearToast" />

  <div class="av-layout">
    <AdminSidebar
      :active-tab="activeTab"
      :mobile-open="sidebarMobileOpen"
      @tab-change="onTabChange"
      @logout="logout"
      @close-mobile="sidebarMobileOpen = false"
    />

    <main class="av-body">
      <div class="av-orb av-orb--top" />
      <div class="av-orb av-orb--bottom" />

      <header class="av-topbar">
        <div class="av-topbar__left">
          <button class="av-menu-btn" @click="sidebarMobileOpen = true">
            <i class="fa-solid fa-bars"></i>
          </button>
          <div class="av-breadcrumb">
            <span class="av-breadcrumb__root">概览</span>
            <span class="av-breadcrumb__sep">/</span>
            <span class="av-breadcrumb__current">
              <i :class="tabIconMap[activeTab]"></i>
              {{ pageTitle }}
            </span>
          </div>
        </div>
      </header>

      <div class="av-content">
        <div class="av-content__inner">
          <div class="av-page-head">
            <div>
              <h1 class="av-page-title">{{ pageTitle }}</h1>
              <p class="av-page-subtitle">今天是 {{ greeting }}，祝您工作顺利。</p>
            </div>
          </div>

          <AdminLoadingState v-if="initialLoading" />

          <div v-else class="av-main">
            <AdminDashboardSection v-if="activeTab === 'dashboard'" :model="dashboardModel" />
            <AdminReportsSection v-if="activeTab === 'reports'" :model="reportsModel" />
            <AdminUsersSection v-if="activeTab === 'users'" :model="usersModel" />
            <AdminTasksSection v-if="activeTab === 'tasks'" :model="tasksModel" />
            <AdminChatsSection v-if="activeTab === 'chats'" :model="chatsModel" />
            <AdminNotificationsSection v-if="activeTab === 'notifications'" :model="notificationsModel" />
            <AdminCategoriesSection v-if="activeTab === 'categories'" :model="categoriesModel" />
            <AdminActionLogsSection v-if="activeTab === 'logs'" :model="actionLogsModel" />
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<style scoped>
.av-layout {
  height: 100vh;
  display: flex;
  background: #f8fafc;
  font-family: var(--font-sans);
  color: var(--c-text);
  overflow: hidden;
}

.av-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  position: relative;
  overflow: hidden;
  height: 100vh;
}

.av-orb {
  position: absolute;
  border-radius: 50%;
  pointer-events: none;
  filter: blur(80px);
}

.av-orb--top {
  top: -200px;
  right: -100px;
  width: 500px;
  height: 500px;
  background: rgba(59, 130, 246, 0.05);
}

.av-orb--bottom {
  bottom: -160px;
  left: -120px;
  width: 400px;
  height: 400px;
  background: rgba(139, 92, 246, 0.04);
}

.av-topbar {
  position: sticky;
  top: 0;
  z-index: 45;
  height: 72px;
  background: rgba(255, 255, 255, 0.6);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border-bottom: 1px solid rgba(226, 232, 240, 0.5);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px 0 28px;
}

.av-topbar__left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.av-menu-btn {
  display: none;
  width: 36px;
  height: 36px;
  border: none;
  background: transparent;
  color: #64748b;
  font-size: 18px;
  border-radius: var(--radius-md);
  transition: color 200ms var(--ease), background 200ms var(--ease);
}

.av-menu-btn:hover {
  color: var(--c-accent);
  background: rgba(59, 130, 246, 0.06);
}

.av-breadcrumb {
  display: flex;
  align-items: center;
  font-size: 13px;
  font-weight: 500;
  gap: 8px;
}

.av-breadcrumb__root {
  color: #94a3b8;
}

.av-breadcrumb__sep {
  color: #cbd5e1;
}

.av-breadcrumb__current {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--c-accent);
  background: rgba(59, 130, 246, 0.06);
  padding: 4px 10px;
  border-radius: var(--radius-sm);
}

.av-breadcrumb__current i {
  font-size: 12px;
}

.av-content {
  flex: 1;
  overflow-y: auto;
  padding: 24px 28px 32px;
  position: relative;
  z-index: 10;
}

.av-content__inner {
  max-width: 1440px;
  margin: 0 auto;
}

.av-page-head {
  margin-bottom: 28px;
}

.av-page-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--c-text);
  margin: 0;
  letter-spacing: -0.02em;
}

.av-page-subtitle {
  margin: 4px 0 0;
  font-size: 13px;
  color: #94a3b8;
}

.av-main {
  width: 100%;
}

@media (max-width: 1024px) {
  .av-menu-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
  }

  .av-breadcrumb {
    display: none;
  }

  .av-topbar {
    padding: 0 16px;
    height: 60px;
  }

  .av-content {
    padding: 16px 14px 20px;
  }

  .av-page-head {
    margin-bottom: 20px;
  }

  .av-page-title {
    font-size: 20px;
  }
}
</style>
