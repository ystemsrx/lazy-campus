<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import AdminCategoriesSection from '../components/admin/AdminCategoriesSection.vue'
import AdminDashboardSection from '../components/admin/AdminDashboardSection.vue'
import AdminHeader from '../components/admin/AdminHeader.vue'
import type { AdminTabKey } from '../components/admin/AdminHeader.vue'
import AdminLoadingState from '../components/admin/AdminLoadingState.vue'
import AdminReportsSection from '../components/admin/AdminReportsSection.vue'
import AppToast from '../components/AppToast.vue'
import AdminUsersSection from '../components/admin/AdminUsersSection.vue'
import { useAdminCategories } from '../composables/admin/useAdminCategories'
import { useAdminDashboard } from '../composables/admin/useAdminDashboard'
import { useAdminReports } from '../composables/admin/useAdminReports'
import { useAppToast } from '../composables/useAppToast'
import { useAdminUsers } from '../composables/admin/useAdminUsers'
import { useAuthStore } from '../stores/auth'
import { extractError } from '../utils/error'

const auth = useAuthStore()
const router = useRouter()

const activeTab = ref<AdminTabKey>('dashboard')
const loading = ref(true)

const toastModel = useAppToast()
const dashboardModel = useAdminDashboard(toastModel.showToast)
const reportsModel = useAdminReports(toastModel.showToast)
const usersModel = useAdminUsers(toastModel.showToast)
const categoriesModel = useAdminCategories(toastModel.showToast)

async function loadData() {
  loading.value = true
  try {
    await dashboardModel.loadDashboard()
    await reportsModel.loadReports()
  } catch (error: unknown) {
    toastModel.showToast(extractError(error, '加载失败'), 'error')
  } finally {
    loading.value = false
  }
}

function onTabChange(key: AdminTabKey) {
  activeTab.value = key

  if (key === 'reports') {
    reportsModel.loadReports()
    return
  }

  if (key === 'users' && usersModel.userList.value.length === 0) {
    usersModel.loadUsers()
    return
  }

  if (key === 'categories') {
    categoriesModel.loadCategories()
  }
}

function logout() {
  auth.logout()
  router.push('/login')
}

onMounted(() => {
  loadData()
})
</script>

<template>
  <AppToast :toast="toastModel.toast" @dismiss="toastModel.clearToast" />

  <AdminHeader :active-tab="activeTab" @tab-change="onTabChange" @logout="logout" />

  <AdminLoadingState v-if="loading" />

  <main v-else class="av-main">
    <AdminDashboardSection v-if="activeTab === 'dashboard'" :model="dashboardModel" />
    <AdminReportsSection v-if="activeTab === 'reports'" :model="reportsModel" />
    <AdminUsersSection v-if="activeTab === 'users'" :model="usersModel" />
    <AdminCategoriesSection v-if="activeTab === 'categories'" :model="categoriesModel" />
  </main>
</template>

<style scoped>
.av-main {
  padding: 24px;
  max-width: 1100px;
  margin: 0 auto;
}

@media (max-width: 768px) {
  .av-main {
    padding: 16px;
  }
}
</style>
