<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import {
  banUser,
  fetchAdminDashboard,
  fetchAdminReports,
  fetchAdminUsers,
  fetchRegistrationSetting,
  fetchTaskSnapshot,
  reviewReport,
  updateRegistrationSetting
} from '../api/moderation'
import { createCategory, deleteCategory, fetchCategories, updateCategory } from '../api/tasks'
import { appConfirm } from '../components/AppConfirm.vue'
import AppDropdown from '../components/AppDropdown.vue'
import { extractError } from '../utils/error'
import { formatShort } from '../utils/time'
import { useAuthStore } from '../stores/auth'
import type { AdminUserItem, Category, Report } from '../types/api'

const auth = useAuthStore()
const router = useRouter()

const activeTab = ref<'dashboard' | 'reports' | 'users' | 'categories'>('dashboard')

/* -------- Toast -------- */
const toast = ref<{ text: string; type: 'success' | 'error' | 'info' } | null>(null)
let toastTimer = 0
function showToast(text: string, type: 'success' | 'error' | 'info' = 'info') {
  toast.value = { text, type }
  clearTimeout(toastTimer)
  toastTimer = window.setTimeout(() => { toast.value = null }, 3500)
}

/* -------- State -------- */
const loading = ref(true)
const dashboard = ref<Record<string, any>>({})
const reports = ref<Report[]>([])
const reportSubTab = ref<'report' | 'appeal'>('report')
const reportStatusFilter = ref<string>('pending')
const registrationEnabled = ref(true)
const savingRegistration = ref(false)

const STATUS_OPTIONS = [
  { value: 'pending', label: '待处理' },
  { value: 'approved', label: '已通过' },
  { value: 'rejected', label: '已驳回' },
]

/* -------- Users State -------- */
const userSearch = ref('')
const userPage = ref(1)
const userTotal = ref(0)
const userList = ref<AdminUserItem[]>([])
const userLoading = ref(false)
const PAGE_SIZE = 20

const showBanModal = ref(false)
const banTargetUser = ref<AdminUserItem | null>(null)
const banReasonInput = ref('')
const banSubmitting = ref(false)

const unbanOpenId = ref<number | null>(null)
const unbanSubmitting = ref(false)

const showReviewModal = ref(false)
const reviewTarget = ref<Report | null>(null)
const reviewBanReason = ref('')
const reviewSubmitting = ref(false)

/* -------- Categories State -------- */
const categoryList = ref<Category[]>([])
const categoryLoading = ref(false)
const showCategoryModal = ref(false)
const editingCategory = ref<Category | null>(null)
const categoryForm = ref({ name: '', description: '', sort_order: 0 })
const categorySubmitting = ref(false)

async function loadCategories() {
  categoryLoading.value = true
  try {
    categoryList.value = await fetchCategories()
  } catch (error: any) {
    showToast(extractError(error, '加载类别失败'), 'error')
  } finally {
    categoryLoading.value = false
  }
}

function openCategoryModal(cat: Category | null) {
  editingCategory.value = cat
  categoryForm.value = cat
    ? { name: cat.name, description: cat.description || '', sort_order: cat.sort_order }
    : { name: '', description: '', sort_order: categoryList.value.length + 1 }
  showCategoryModal.value = true
}

async function submitCategory() {
  if (!categoryForm.value.name.trim()) {
    showToast('请输入类别名称', 'error')
    return
  }
  categorySubmitting.value = true
  try {
    const payload = {
      name: categoryForm.value.name.trim(),
      description: categoryForm.value.description.trim() || undefined,
      sort_order: categoryForm.value.sort_order,
    }
    if (editingCategory.value) {
      await updateCategory(editingCategory.value.id, payload)
      showToast('类别已更新', 'success')
    } else {
      await createCategory(payload)
      showToast('类别已添加', 'success')
    }
    showCategoryModal.value = false
    await loadCategories()
  } catch (error: any) {
    showToast(extractError(error, '保存失败'), 'error')
  } finally {
    categorySubmitting.value = false
  }
}

async function handleDeleteCategory(cat: Category) {
  const warnings: string[] = []
  if (cat.task_count > 0) warnings.push(`${cat.task_count} 个任务`)
  if (cat.worker_count > 0) warnings.push(`${cat.worker_count} 位接单者`)
  const extra = warnings.length ? `\n当前有 ${warnings.join('、')} 使用此类别。` : ''
  const yes = await appConfirm({
    title: '确认删除',
    message: `确定删除类别「${cat.name}」？${extra}`,
    confirmText: '删除',
    type: 'danger',
  })
  if (!yes) return
  try {
    await deleteCategory(cat.id)
    showToast('类别已删除', 'success')
    await loadCategories()
  } catch (error: any) {
    showToast(extractError(error, '删除失败'), 'error')
  }
}

/* -------- Task Snapshot -------- */
const showSnapshot = ref(false)
const snapshotLoading = ref(false)
const snapshot = ref<any>(null)

async function openSnapshot(taskId: number) {
  showSnapshot.value = true
  snapshotLoading.value = true
  snapshot.value = null
  try {
    snapshot.value = await fetchTaskSnapshot(taskId)
  } catch (error: any) {
    showToast(extractError(error, '加载任务快照失败'), 'error')
    showSnapshot.value = false
  } finally {
    snapshotLoading.value = false
  }
}


const TASK_STATUS_MAP: Record<string, string> = {
  open: '待接取',
  in_progress: '进行中',
  completed: '已完成',
  canceled: '已取消',
  under_review: '审核中',
}

/* -------- Helpers -------- */
function reportStatusLabel(s: string) {
  return s === 'pending' ? '待审核' : s === 'approved' ? '已通过' : '已驳回'
}

function reportStatusClass(s: string) {
  return s === 'pending' ? 'badge-amber' : s === 'approved' ? 'badge-green' : 'badge-red'
}


function totalPages() {
  return Math.max(1, Math.ceil(userTotal.value / PAGE_SIZE))
}

/* -------- Data -------- */
async function loadData() {
  loading.value = true
  try {
    const [d, rs] = await Promise.all([fetchAdminDashboard(), fetchRegistrationSetting()])
    dashboard.value = d
    registrationEnabled.value = rs.registration_enabled
    await loadReports()
  } catch (error: any) {
    showToast(extractError(error, '加载失败'), 'error')
  } finally {
    loading.value = false
  }
}

async function loadReports() {
  try {
    reports.value = await fetchAdminReports({
      type: reportSubTab.value,
      status: reportStatusFilter.value || undefined,
    })
  } catch (error: any) {
    showToast(extractError(error, '加载举报列表失败'), 'error')
  }
}

watch([reportSubTab, reportStatusFilter], () => {
  loadReports()
})

async function loadUsers() {
  userLoading.value = true
  try {
    const res = await fetchAdminUsers({
      q: userSearch.value || undefined,
      page: userPage.value,
      page_size: PAGE_SIZE,
    })
    userList.value = res.items
    userTotal.value = res.total
  } catch (error: any) {
    showToast(extractError(error, '加载用户列表失败'), 'error')
  } finally {
    userLoading.value = false
  }
}

let searchDebounce = 0
watch(userSearch, () => {
  clearTimeout(searchDebounce)
  searchDebounce = window.setTimeout(() => {
    userPage.value = 1
    loadUsers()
  }, 300)
})

watch(userPage, () => {
  loadUsers()
})

function goPage(p: number) {
  if (p < 1 || p > totalPages()) return
  userPage.value = p
}

const BAN_DAYS = [1, 3, 7]

async function handleReview(report: Report, status: 'approved' | 'rejected') {
  const isReport = report.type === 'report'

  if (isReport && status === 'approved') {
    reviewTarget.value = report
    reviewBanReason.value = ''
    showReviewModal.value = true
    return
  }

  if (!isReport && status === 'approved') {
    const name = report.reporter_nickname || report.reporter_name || report.reporter_account || '该用户'
    const yes = await appConfirm({
      title: '确认通过申诉',
      message: `通过后「${name}」将被解除封禁，确定通过？`,
      confirmText: '确认通过',
      type: 'info',
    })
    if (!yes) return
  }

  await doReview(report, status)
}

async function doReview(report: Report, status: 'approved' | 'rejected', adminNotes?: string) {
  const isReport = report.type === 'report'
  try {
    await reviewReport(report.id, { status, admin_notes: adminNotes })
    if (isReport) {
      showToast(status === 'approved' ? '已通过，被举报用户已自动封禁' : '已驳回', 'success')
    } else {
      showToast(status === 'approved' ? '申诉通过，用户已解封' : '申诉已驳回', 'success')
    }
    await loadReports()
  } catch (error: any) {
    showToast(extractError(error, '审核失败'), 'error')
  }
}

async function confirmReportReview() {
  if (!reviewTarget.value) return
  reviewSubmitting.value = true
  try {
    await doReview(reviewTarget.value, 'approved', reviewBanReason.value || undefined)
    showReviewModal.value = false
  } finally {
    reviewSubmitting.value = false
  }
}

function openBanModal(user: AdminUserItem) {
  banTargetUser.value = user
  banReasonInput.value = ''
  showBanModal.value = true
}

async function confirmBan() {
  if (!banTargetUser.value) return
  banSubmitting.value = true
  try {
    await banUser(banTargetUser.value.id, { banned: true, reason: banReasonInput.value || undefined })
    banTargetUser.value.is_banned = true
    banTargetUser.value.ban_reason = banReasonInput.value || null
    banTargetUser.value.ban_count++
    showToast('用户已封禁', 'success')
    showBanModal.value = false
  } catch (error: any) {
    showToast(extractError(error, '封禁失败'), 'error')
  } finally {
    banSubmitting.value = false
  }
}

function toggleUnbanMenu(userId: number) {
  unbanOpenId.value = unbanOpenId.value === userId ? null : userId
}

async function confirmUnban(user: AdminUserItem, innocent: boolean) {
  unbanSubmitting.value = true
  try {
    await banUser(user.id, { banned: false, innocent })
    user.is_banned = false
    user.ban_reason = null
    if (innocent && user.ban_count > 0) {
      user.ban_count--
    }
    showToast(innocent ? '已无责解封' : '已有责解封', 'success')
  } catch (error: any) {
    showToast(extractError(error, '解封失败'), 'error')
  } finally {
    unbanOpenId.value = null
    unbanSubmitting.value = false
  }
}

async function handleToggleRegistration() {
  savingRegistration.value = true
  try {
    const nextValue = !registrationEnabled.value
    const data = await updateRegistrationSetting({ registration_enabled: nextValue })
    registrationEnabled.value = data.registration_enabled
    dashboard.value.registration_enabled = data.registration_enabled
    showToast(data.registration_enabled ? '已开启用户注册' : '已关闭用户注册', 'success')
  } catch (error: any) {
    showToast(extractError(error, '更新注册开关失败'), 'error')
  } finally {
    savingRegistration.value = false
  }
}

function onTabChange(key: 'dashboard' | 'reports' | 'users' | 'categories') {
  activeTab.value = key
  if (key === 'reports') {
    loadReports()
  } else if (key === 'users' && userList.value.length === 0) {
    loadUsers()
  } else if (key === 'categories') {
    loadCategories()
  }
}

function logout() {
  auth.logout()
  router.push('/login')
}

function onClickOutsideUnban(e: MouseEvent) {
  if (unbanOpenId.value === null) return
  const target = e.target as HTMLElement
  if (!target.closest('.av-unban-wrap')) {
    unbanOpenId.value = null
  }
}

onMounted(() => {
  loadData()
  document.addEventListener('mousedown', onClickOutsideUnban)
})
onUnmounted(() => {
  document.removeEventListener('mousedown', onClickOutsideUnban)
})
</script>

<template>
  <!-- Toast -->
  <Transition name="toast">
    <div v-if="toast" class="av-toast" :class="'av-toast--' + toast.type" @click="toast = null">
      {{ toast.text }}
    </div>
  </Transition>

  <!-- Header -->
  <header class="av-header">
    <div class="av-header__brand">
      <div class="av-logo">A</div>
      <span class="av-header__title">管理员控制台</span>
    </div>

    <nav class="av-tabs">
      <button v-for="t in ([
        { key: 'dashboard', label: '数据看板', icon: 'fa-solid fa-chart-line' },
        { key: 'reports', label: '举报 / 申诉', icon: 'fa-solid fa-flag' },
        { key: 'users', label: '用户管理', icon: 'fa-solid fa-users-gear' },
        { key: 'categories', label: '类别管理', icon: 'fa-solid fa-tags' }
      ] as const)" :key="t.key" class="av-tab" :class="{ 'av-tab--active': activeTab === t.key }" @click="onTabChange(t.key)">
        <i :class="t.icon"></i> {{ t.label }}
      </button>
    </nav>

    <div class="av-header__right">
      <button class="btn btn-ghost btn-sm" @click="logout"><i class="fa-solid fa-right-from-bracket"></i> 退出</button>
    </div>
  </header>

  <!-- Loading -->
  <div v-if="loading" class="av-loading">
    <div class="spinner"></div>
    <span>加载中…</span>
  </div>

  <!-- Main Content -->
  <main v-else class="av-main">

    <!-- ===== 数据看板 ===== -->
    <section v-if="activeTab === 'dashboard'" class="av-section">
      <h2 style="margin-bottom: 20px;">数据看板</h2>

      <div class="av-stats-grid">
        <div class="av-stat-card">
          <span class="av-stat__value">{{ dashboard.total_users ?? '-' }}</span>
          <span class="av-stat__label">总用户</span>
        </div>
        <div class="av-stat-card">
          <span class="av-stat__value">{{ dashboard.active_workers ?? '-' }}</span>
          <span class="av-stat__label">活跃接单者</span>
        </div>
        <div class="av-stat-card">
          <span class="av-stat__value">{{ dashboard.total_tasks ?? '-' }}</span>
          <span class="av-stat__label">总任务</span>
        </div>
        <div class="av-stat-card">
          <span class="av-stat__value">{{ dashboard.completed_tasks ?? '-' }}</span>
          <span class="av-stat__label">已完成</span>
        </div>
        <div class="av-stat-card av-stat-card--accent">
          <span class="av-stat__value">{{ dashboard.pending_reports ?? '-' }}</span>
          <span class="av-stat__label">待处理举报</span>
        </div>
        <div class="av-stat-card">
          <span class="av-stat__value">{{ dashboard.completion_rate ?? '-' }}</span>
          <span class="av-stat__label">完成率</span>
        </div>
      </div>

      <div class="card av-reg-card">
        <div class="av-reg-row">
          <div>
            <h4 style="margin: 0 0 4px;">用户注册</h4>
            <p style="color: var(--c-text-muted); font-size: var(--text-sm); margin: 0;">
              当前状态：<span class="badge" :class="registrationEnabled ? 'badge-green' : 'badge-red'">{{ registrationEnabled ? '已开启' : '已关闭' }}</span>
            </p>
          </div>
          <button class="btn" :class="registrationEnabled ? 'btn-outline' : 'btn-primary'" :disabled="savingRegistration" @click="handleToggleRegistration">
            {{ savingRegistration ? '保存中...' : (registrationEnabled ? '关闭注册' : '开启注册') }}
          </button>
        </div>
      </div>
    </section>

    <!-- ===== 举报/申诉审核 ===== -->
    <section v-if="activeTab === 'reports'" class="av-section">
      <div class="av-report-toolbar">
        <div class="av-report-subtabs">
          <button class="av-report-subtab" :class="{ 'av-report-subtab--active': reportSubTab === 'report' }" @click="reportSubTab = 'report'">
            <i class="fa-solid fa-flag"></i> 举报
          </button>
          <button class="av-report-subtab" :class="{ 'av-report-subtab--active': reportSubTab === 'appeal' }" @click="reportSubTab = 'appeal'">
            <i class="fa-solid fa-hand"></i> 申诉
          </button>
        </div>
        <AppDropdown
          v-model="reportStatusFilter"
          :options="STATUS_OPTIONS"
          width="auto"
          min-width="110px"
        />
      </div>

      <div v-if="reports.length" class="av-report-list">
        <div v-for="report in reports" :key="report.id" class="card av-report-card">
          <div class="av-report-card__header">
            <a v-if="report.task_id" class="av-task-link" @click.prevent="openSnapshot(report.task_id)">
              <i class="fa-solid fa-arrow-up-right-from-square" style="font-size: 11px;"></i> 任务 #{{ report.task_id }}
            </a>
            <span v-else style="font-weight: 600; color: var(--c-text-muted);">账号申诉</span>
            <span class="badge" :class="reportStatusClass(report.status)">{{ reportStatusLabel(report.status) }}</span>
          </div>

          <div class="av-report-card__body">
            <table class="av-report-table">
              <thead>
                <tr>
                  <th>类型</th>
                  <th>账号</th>
                  <th>姓名</th>
                  <th>昵称</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="reportSubTab === 'report'">
                  <td>举报用户</td>
                  <td>{{ report.reporter_account || '-' }}</td>
                  <td>{{ report.reporter_name || '-' }}</td>
                  <td>{{ report.reporter_nickname || '-' }}</td>
                </tr>
                <tr>
                  <td>{{ reportSubTab === 'report' ? '被举报用户' : '申诉用户' }}</td>
                  <td>{{ (reportSubTab === 'report' ? report.reported_user_account : report.reporter_account) || '-' }}</td>
                  <td>{{ (reportSubTab === 'report' ? report.reported_user_name : report.reporter_name) || '-' }}</td>
                  <td>{{ (reportSubTab === 'report' ? report.reported_user_nickname : report.reporter_nickname) || '-' }}</td>
                </tr>
              </tbody>
            </table>

            <div class="av-report-card__row" style="flex-direction: column; align-items: flex-start; gap: 2px;">
              <span class="av-report-card__label">{{ reportSubTab === 'report' ? '举报原因' : '申诉理由' }}</span>
              <span style="color: var(--c-text-secondary);">{{ report.reason }}</span>
            </div>
            <div v-if="report.evidence" class="av-report-card__row" style="flex-direction: column; align-items: flex-start; gap: 2px;">
              <span class="av-report-card__label">证据</span>
              <span style="color: var(--c-text-secondary);">{{ report.evidence }}</span>
            </div>
          </div>

          <div v-if="report.status === 'pending'" class="av-report-card__actions">
            <button class="btn btn-success btn-sm" @click="handleReview(report, 'approved')"><i class="fa-solid fa-check"></i> 通过</button>
            <button class="btn btn-outline btn-sm" @click="handleReview(report, 'rejected')"><i class="fa-solid fa-xmark"></i> 驳回</button>
          </div>
        </div>
      </div>
      <div v-else class="av-empty"><i class="fa-regular fa-folder-open" style="font-size: 36px; display: block; margin-bottom: 12px; color: var(--c-border);"></i>{{ reportSubTab === 'report' ? '暂无举报数据' : '暂无申诉数据' }}</div>
    </section>

    <!-- ===== 类别管理 ===== -->
    <section v-if="activeTab === 'categories'" class="av-section">
      <div class="av-users-header">
        <h2>类别管理</h2>
        <span class="av-users-total">共 {{ categoryList.length }} 个</span>
        <button class="btn btn-primary btn-sm" style="margin-left: auto;" @click="openCategoryModal(null)">
          <i class="fa-solid fa-plus"></i> 添加类别
        </button>
      </div>
      <p class="av-category-hint">类别同时用于任务分类和接单者擅长领域</p>

      <div v-if="categoryLoading" class="av-users-loading"><div class="spinner"></div></div>

      <div v-else-if="categoryList.length === 0" class="av-empty">
        <i class="fa-solid fa-tags" style="font-size: 36px; display: block; margin-bottom: 12px; color: var(--c-border);"></i>
        暂无类别，点击上方按钮添加
      </div>

      <div v-else class="av-category-grid">
        <div v-for="cat in categoryList" :key="cat.id" class="card av-category-card">
          <div class="av-category-card__main">
            <h4 class="av-category-card__name">{{ cat.name }}</h4>
            <p v-if="cat.description" class="av-category-card__desc">{{ cat.description }}</p>
            <div class="av-category-card__stats">
              <span class="badge badge-blue">{{ cat.task_count }} 个任务</span>
              <span class="badge badge-green">{{ cat.worker_count }} 位接单者</span>
              <span class="av-category-card__order">排序: {{ cat.sort_order }}</span>
            </div>
          </div>
          <div class="av-category-card__actions">
            <button class="av-action-btn" title="编辑" @click="openCategoryModal(cat)">
              <i class="fa-solid fa-pen"></i>
            </button>
            <button class="av-action-btn av-action-btn--ban" title="删除" @click="handleDeleteCategory(cat)">
              <i class="fa-solid fa-trash"></i>
            </button>
          </div>
        </div>
      </div>
    </section>

    <!-- ===== 用户管理 ===== -->
    <section v-if="activeTab === 'users'" class="av-section">
      <div class="av-users-header">
        <h2>用户管理</h2>
        <span class="av-users-total">共 {{ userTotal }} 人</span>
      </div>

      <div class="av-users-search">
        <i class="fa-solid fa-magnifying-glass av-search-icon"></i>
        <input
          v-model="userSearch"
          class="form-input av-search-input"
          placeholder="搜索账号、姓名或昵称…"
        />
      </div>

      <div v-if="userLoading" class="av-users-loading">
        <div class="spinner"></div>
      </div>

      <div v-else-if="userList.length === 0" class="av-empty">
        <i class="fa-regular fa-user" style="font-size: 36px; display: block; margin-bottom: 12px; color: var(--c-border);"></i>
        {{ userSearch ? '未找到匹配用户' : '暂无用户' }}
      </div>

      <template v-else>
        <div class="av-user-table">
          <div class="av-user-row av-user-row--header">
            <span class="av-user-col av-user-col--account">账号</span>
            <span class="av-user-col av-user-col--name">姓名</span>
            <span class="av-user-col av-user-col--nickname">昵称</span>
            <span class="av-user-col av-user-col--role">角色</span>
            <span class="av-user-col av-user-col--status">状态</span>
            <span class="av-user-col av-user-col--bancount">封禁</span>
            <span class="av-user-col av-user-col--action">操作</span>
          </div>
          <div v-for="u in userList" :key="u.id" class="av-user-row" :class="{ 'av-user-row--banned': u.is_banned }">
            <span class="av-user-col av-user-col--account" :title="u.account">{{ u.account }}</span>
            <span class="av-user-col av-user-col--name" :title="u.name">{{ u.name }}</span>
            <span class="av-user-col av-user-col--nickname" :title="u.nickname || '-'">{{ u.nickname || '-' }}</span>
            <span class="av-user-col av-user-col--role">
              <span class="badge" :class="u.role === 'admin' ? 'badge-blue' : 'badge-default'">{{ u.role === 'admin' ? '管理员' : '用户' }}</span>
            </span>
            <span class="av-user-col av-user-col--status">
              <span v-if="u.is_banned" class="badge badge-red" :title="u.ban_reason || ''">已封禁</span>
              <span v-else class="badge badge-green">正常</span>
              <span v-if="u.is_banned && u.ban_until" class="av-ban-until">至 {{ formatShort(u.ban_until!) }}</span>
            </span>
            <span class="av-user-col av-user-col--bancount" :class="{ 'av-bancount--warn': u.ban_count > 0 }">
              {{ u.ban_count }}
            </span>
            <span class="av-user-col av-user-col--action">
              <button
                v-if="!u.is_banned"
                class="av-action-btn av-action-btn--ban"
                title="封禁该用户"
                @click="openBanModal(u)"
              >
                <i class="fa-solid fa-ban"></i>
              </button>
              <div v-else class="av-unban-wrap">
                <button
                  class="av-action-btn av-action-btn--unban"
                  title="解封该用户"
                  @click="toggleUnbanMenu(u.id)"
                >
                  <i class="fa-solid fa-lock-open"></i>
                </button>
                <Transition name="av-dropdown">
                  <div v-if="unbanOpenId === u.id" class="av-unban-menu">
                    <button class="av-unban-menu__item" :disabled="unbanSubmitting" @click="confirmUnban(u, false)">
                      <i class="fa-solid fa-gavel" style="color: var(--c-warning);"></i>
                      有责解封
                    </button>
                    <button class="av-unban-menu__item" :disabled="unbanSubmitting" @click="confirmUnban(u, true)">
                      <i class="fa-solid fa-shield-halved" style="color: var(--c-success);"></i>
                      无责解封
                    </button>
                  </div>
                </Transition>
              </div>
            </span>
          </div>
        </div>

        <div v-if="totalPages() > 1" class="av-pagination">
          <button class="btn btn-ghost btn-sm" :disabled="userPage <= 1" @click="goPage(userPage - 1)">
            <i class="fa-solid fa-chevron-left"></i>
          </button>
          <template v-for="p in totalPages()" :key="p">
            <button
              v-if="p === 1 || p === totalPages() || (p >= userPage - 2 && p <= userPage + 2)"
              class="av-page-btn"
              :class="{ 'av-page-btn--active': p === userPage }"
              @click="goPage(p)"
            >{{ p }}</button>
            <span
              v-else-if="p === userPage - 3 || p === userPage + 3"
              class="av-page-ellipsis"
            >…</span>
          </template>
          <button class="btn btn-ghost btn-sm" :disabled="userPage >= totalPages()" @click="goPage(userPage + 1)">
            <i class="fa-solid fa-chevron-right"></i>
          </button>
        </div>
      </template>
    </section>
  </main>

  <!-- Ban Modal -->
  <Transition name="fade">
    <div v-if="showBanModal" class="av-modal-overlay" @click.self="showBanModal = false">
      <div class="av-modal">
        <div class="av-modal__header">
          <h3>封禁用户</h3>
          <button class="btn btn-ghost btn-sm" @click="showBanModal = false">
            <i class="fa-solid fa-xmark"></i>
          </button>
        </div>
        <div class="av-modal__body">
          <p style="margin-bottom: 12px; color: var(--c-text-secondary); font-size: var(--text-sm);">
            确认封禁用户 <strong>{{ banTargetUser?.display_name }}</strong>（{{ banTargetUser?.account }}）？
          </p>
          <div class="form-group">
            <label class="form-label">封禁原因（选填）</label>
            <input
              v-model="banReasonInput"
              class="form-input"
              placeholder="输入封禁原因…"
              @keyup.enter="confirmBan"
            />
          </div>
        </div>
        <div class="av-modal__footer">
          <button class="btn btn-outline btn-sm" @click="showBanModal = false">取消</button>
          <button class="btn btn-danger btn-sm" :disabled="banSubmitting" @click="confirmBan">
            {{ banSubmitting ? '处理中…' : '确认封禁' }}
          </button>
        </div>
      </div>
    </div>
  </Transition>

  <!-- Review Report Modal -->
  <Transition name="fade">
    <div v-if="showReviewModal" class="av-modal-overlay" @click.self="showReviewModal = false">
      <div class="av-modal">
        <div class="av-modal__header">
          <h3>通过举报</h3>
          <button class="btn btn-ghost btn-sm" @click="showReviewModal = false">
            <i class="fa-solid fa-xmark"></i>
          </button>
        </div>
        <div class="av-modal__body">
          <p style="margin-bottom: 12px; color: var(--c-text-secondary); font-size: var(--text-sm);">
            通过后「<strong>{{ reviewTarget?.reported_user_nickname || reviewTarget?.reported_user_name || reviewTarget?.reported_user_account || '该用户' }}</strong>」将被封禁
            {{ BAN_DAYS[Math.min(reviewTarget?.reported_user_ban_count ?? 0, BAN_DAYS.length - 1)] }} 天（第
            {{ (reviewTarget?.reported_user_ban_count ?? 0) + 1 }} 次封禁）。
          </p>
          <div class="form-group">
            <label class="form-label">封禁理由（选填，留空则显示"违反社区规则。"）</label>
            <input
              v-model="reviewBanReason"
              class="form-input"
              placeholder="输入封禁理由…"
              @keyup.enter="confirmReportReview"
            />
          </div>
        </div>
        <div class="av-modal__footer">
          <button class="btn btn-outline btn-sm" @click="showReviewModal = false">取消</button>
          <button class="btn btn-warning btn-sm" :disabled="reviewSubmitting" @click="confirmReportReview">
            {{ reviewSubmitting ? '处理中…' : '确认通过' }}
          </button>
        </div>
      </div>
    </div>
  </Transition>

  <!-- Category Modal -->
  <Transition name="fade">
    <div v-if="showCategoryModal" class="av-modal-overlay" @click.self="showCategoryModal = false">
      <div class="av-modal">
        <div class="av-modal__header">
          <h3>{{ editingCategory ? '编辑类别' : '添加类别' }}</h3>
          <button class="btn btn-ghost btn-sm" @click="showCategoryModal = false">
            <i class="fa-solid fa-xmark"></i>
          </button>
        </div>
        <div class="av-modal__body">
          <div class="form-group">
            <label class="form-label">名称</label>
            <input v-model="categoryForm.name" class="form-input" placeholder="输入类别名称" @keyup.enter="submitCategory" />
          </div>
          <div class="form-group">
            <label class="form-label">描述（选填）</label>
            <input v-model="categoryForm.description" class="form-input" placeholder="输入类别描述" />
          </div>
          <div class="form-group">
            <label class="form-label">排序（越小越靠前）</label>
            <input v-model.number="categoryForm.sort_order" class="form-input" type="number" />
          </div>
        </div>
        <div class="av-modal__footer">
          <button class="btn btn-outline btn-sm" @click="showCategoryModal = false">取消</button>
          <button class="btn btn-primary btn-sm" :disabled="categorySubmitting" @click="submitCategory">
            {{ categorySubmitting ? '保存中…' : '保存' }}
          </button>
        </div>
      </div>
    </div>
  </Transition>

  <!-- ===== Task Snapshot Drawer ===== -->
  <Teleport to="body">
    <Transition name="av-drawer">
      <div v-if="showSnapshot" class="av-snapshot-overlay" @mousedown.self="showSnapshot = false">
        <div class="av-snapshot-drawer">
          <div class="av-snapshot-drawer__header">
            <h3>任务快照</h3>
            <button class="btn btn-ghost btn-sm" @click="showSnapshot = false"><i class="fa-solid fa-xmark"></i></button>
          </div>

          <div v-if="snapshotLoading" class="av-snapshot-drawer__body" style="display: flex; align-items: center; justify-content: center; min-height: 200px;">
            <div class="spinner"></div>
          </div>

          <div v-else-if="snapshot" class="av-snapshot-drawer__body">
            <!-- Task Info -->
            <div class="av-snap-section">
              <h4 class="av-snap-title">{{ snapshot.title }}</h4>
              <div class="av-snap-meta">
                <span class="badge" :class="{
                  'badge-green': snapshot.status === 'completed',
                  'badge-amber': snapshot.status === 'in_progress' || snapshot.status === 'under_review',
                  'badge-red': snapshot.status === 'canceled',
                  'badge-default': snapshot.status === 'open',
                }">{{ TASK_STATUS_MAP[snapshot.status] || snapshot.status }}</span>
                <span>¥{{ snapshot.price }}</span>
                <span v-if="snapshot.location"><i class="fa-solid fa-location-dot"></i> {{ snapshot.location }}</span>
              </div>
              <p class="av-snap-desc">{{ snapshot.description }}</p>
              <div class="av-snap-users">
                <div class="av-snap-user-row">
                  <span class="av-snap-user-label">发布者</span>
                  <span>{{ snapshot.publisher_display_name }}</span>
                </div>
                <div class="av-snap-user-row">
                  <span class="av-snap-user-label">接单者</span>
                  <span>{{ snapshot.assignee_display_name || '—' }}</span>
                </div>
                <div v-if="snapshot.deadline" class="av-snap-user-row">
                  <span class="av-snap-user-label">截止时间</span>
                  <span>{{ formatShort(snapshot.deadline) }}</span>
                </div>
              </div>
            </div>

            <!-- Messages -->
            <div class="av-snap-section">
              <h4 class="av-snap-subtitle"><i class="fa-regular fa-comment-dots"></i> 聊天记录 ({{ snapshot.messages.length }})</h4>
              <div v-if="snapshot.messages.length" class="av-snap-chat">
                <div v-for="(msg, idx) in snapshot.messages" :key="idx" class="av-snap-msg">
                  <div class="av-snap-msg__head">
                    <span class="av-snap-msg__sender">{{ msg.sender_display_name }}</span>
                    <span class="av-snap-msg__time">{{ formatShort(msg.created_at) }}</span>
                  </div>
                  <div class="av-snap-msg__text">{{ msg.content }}</div>
                </div>
              </div>
              <p v-else class="av-snap-empty">暂无聊天记录</p>
            </div>

            <!-- Reviews -->
            <div class="av-snap-section">
              <h4 class="av-snap-subtitle"><i class="fa-regular fa-star-half-stroke"></i> 互评 ({{ snapshot.reviews.length }})</h4>
              <div v-if="snapshot.reviews.length" class="av-snap-reviews">
                <div v-for="(rev, idx) in snapshot.reviews" :key="idx" class="av-snap-review">
                  <div class="av-snap-review__head">
                    <span class="badge badge-default">{{ rev.target_role === 'worker' ? '评价接单者' : '评价发布者' }}</span>
                    <span class="av-snap-review__stars">
                      <i v-for="s in 5" :key="s" :class="s <= rev.stars ? 'fa-solid fa-star' : 'fa-regular fa-star'" style="color: #f59e0b; font-size: 12px;"></i>
                    </span>
                  </div>
                  <p class="av-snap-review__by">{{ rev.reviewer_display_name }} · {{ formatShort(rev.created_at) }}</p>
                  <p v-if="rev.comment" class="av-snap-review__comment">{{ rev.comment }}</p>
                </div>
              </div>
              <p v-else class="av-snap-empty">暂无评价</p>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>

</template>

<style scoped>
.av-header {
  position: sticky;
  top: 0;
  z-index: 40;
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 0 24px;
  height: 60px;
  background: rgba(255, 255, 255, 0.82);
  backdrop-filter: blur(14px);
  border-bottom: 1px solid var(--c-border);
}

.av-header__brand {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.av-logo {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-sm);
  background: var(--c-primary);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 16px;
}

.av-header__title {
  font-weight: 700;
  font-size: var(--text-lg);
  color: var(--c-text);
}

.av-header__right {
  margin-left: auto;
  flex-shrink: 0;
}

.av-tabs { display: flex; gap: 4px; }

.av-tab {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border: none;
  background: transparent;
  color: var(--c-text-muted);
  font-size: var(--text-sm);
  font-weight: 500;
  border-radius: var(--radius-sm);
  transition: color var(--dur-fast) var(--ease), background var(--dur-fast) var(--ease);
}

.av-tab:hover { color: var(--c-text); background: var(--c-border-light); }
.av-tab--active { color: var(--c-accent); background: var(--c-accent-light); }

.av-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  height: calc(100vh - 60px);
  color: var(--c-text-muted);
  font-size: var(--text-sm);
}

.av-main {
  padding: 24px;
  max-width: 1100px;
  margin: 0 auto;
}

/* Stats Grid */
.av-stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(170px, 1fr));
  gap: 12px;
  margin-bottom: 20px;
}

.av-stat-card {
  background: var(--c-surface);
  border: 1px solid var(--c-border);
  border-radius: var(--radius-lg);
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.av-stat-card--accent {
  background: var(--c-danger-light);
  border-color: var(--c-danger-soft);
}

.av-stat__value {
  font-size: var(--text-2xl);
  font-weight: 700;
  color: var(--c-text);
}

.av-stat-card--accent .av-stat__value {
  color: var(--c-danger);
}

.av-stat__label {
  font-size: var(--text-sm);
  color: var(--c-text-muted);
}

.av-reg-card { max-width: 500px; }

.av-reg-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}

/* Report Toolbar */
.av-report-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
  gap: 16px;
}

.av-report-subtabs {
  display: flex;
  gap: 4px;
  background: var(--c-bg-secondary, #f1f5f9);
  border-radius: var(--radius-md);
  padding: 3px;
}

.av-report-subtab {
  padding: 7px 18px;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--c-text-muted);
  font-size: var(--text-sm);
  font-weight: 500;
  cursor: pointer;
  transition: all var(--dur-fast) var(--ease);
  font-family: var(--font-sans);
  display: flex;
  align-items: center;
  gap: 6px;
}
.av-report-subtab:hover {
  color: var(--c-text);
}
.av-report-subtab--active {
  background: #fff;
  color: var(--c-accent);
  box-shadow: var(--shadow-sm);
}

/* Report List */
.av-report-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-width: 700px;
}

.av-report-card__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.av-report-card__body {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.av-report-card__row {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: var(--text-sm);
}

.av-report-card__label {
  color: var(--c-text-muted);
  min-width: 80px;
  flex-shrink: 0;
}

.av-report-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--text-sm);
  margin-bottom: 4px;
}
.av-report-table th,
.av-report-table td {
  padding: 6px 10px;
  text-align: left;
  border-bottom: 1px solid var(--c-border);
}
.av-report-table th {
  color: var(--c-text-muted);
  font-weight: 500;
  background: var(--c-bg-secondary);
}
.av-report-table td:first-child {
  color: var(--c-text-muted);
  white-space: nowrap;
}

.av-report-card__actions {
  display: flex;
  gap: 8px;
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid var(--c-border-light);
}

.av-empty {
  text-align: center;
  color: var(--c-text-muted);
  padding: 48px 20px;
}

/* Users */
.av-users-header {
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 16px;
}

.av-users-total {
  font-size: var(--text-sm);
  color: var(--c-text-muted);
  font-weight: 500;
}

.av-users-search {
  position: relative;
  max-width: 400px;
  margin-bottom: 16px;
}

.av-search-icon {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--c-text-muted);
  font-size: var(--text-sm);
  pointer-events: none;
}

.av-search-input {
  padding-left: 36px !important;
}

.av-users-loading {
  display: flex;
  justify-content: center;
  padding: 40px 0;
}

.av-user-table {
  border: 1px solid var(--c-border);
  border-radius: var(--radius-lg);
  background: var(--c-surface);
}

.av-user-row {
  display: grid;
  grid-template-columns: 1.2fr 1fr 1fr 80px 80px 52px 64px;
  align-items: center;
  padding: 0 16px;
  min-height: 46px;
  font-size: var(--text-sm);
  border-bottom: 1px solid var(--c-border-light);
  transition: background var(--dur-fast) var(--ease);
}

.av-user-row:last-child { border-bottom: none; }

.av-user-row:not(.av-user-row--header):hover {
  background: var(--c-border-light);
}

.av-user-row--header {
  background: var(--c-bg);
  font-weight: 600;
  color: var(--c-text-muted);
  font-size: var(--text-xs);
  text-transform: uppercase;
  letter-spacing: 0.03em;
  min-height: 40px;
  border-bottom: 1px solid var(--c-border);
  border-radius: var(--radius-lg) var(--radius-lg) 0 0;
}

.av-user-row:last-child {
  border-radius: 0 0 var(--radius-lg) var(--radius-lg);
}

.av-user-row--banned {
  background: var(--c-danger-light);
}
.av-user-row--banned:hover {
  background: var(--c-danger-soft) !important;
}

.av-user-col {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  padding: 4px 0;
}

.av-user-col--action {
  display: flex;
  justify-content: center;
  overflow: visible;
}

.av-action-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  font-size: 14px;
  transition: all var(--dur-fast) var(--ease);
}

.av-action-btn--ban {
  color: var(--c-text-muted);
}
.av-action-btn--ban:hover {
  color: var(--c-danger);
  background: var(--c-danger-light);
}

.av-action-btn--unban {
  color: var(--c-success);
}
.av-action-btn--unban:hover {
  color: #047857;
  background: var(--c-success-light);
}

/* Pagination */
.av-pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  margin-top: 16px;
}

.av-page-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 32px;
  height: 32px;
  padding: 0 8px;
  border: 1px solid var(--c-border);
  border-radius: var(--radius-sm);
  background: var(--c-surface);
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--c-text-secondary);
  transition: all var(--dur-fast) var(--ease);
}

.av-page-btn:hover {
  border-color: var(--c-accent);
  color: var(--c-accent);
}

.av-page-btn--active {
  background: var(--c-accent);
  border-color: var(--c-accent);
  color: var(--c-text-inverse);
}
.av-page-btn--active:hover {
  background: var(--c-accent-hover);
  color: var(--c-text-inverse);
}

.av-page-ellipsis {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  color: var(--c-text-muted);
  font-size: var(--text-sm);
}

/* Ban count */
.av-user-col--bancount {
  text-align: center;
  font-weight: 600;
  color: var(--c-text-muted);
}

.av-bancount--warn {
  color: var(--c-danger) !important;
}

.av-ban-until {
  display: block;
  font-size: 11px;
  color: var(--c-danger);
  margin-top: 2px;
  white-space: nowrap;
}

/* Unban inline dropdown */
.av-unban-wrap {
  position: relative;
  display: inline-flex;
  justify-content: center;
}

.av-user-col--action {
  position: relative;
}

.av-unban-menu {
  position: absolute;
  right: 50%;
  transform: translateX(50%);
  top: calc(100% + 4px);
  z-index: 50;
  min-width: 130px;
  background: var(--c-surface);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-xl);
  padding: 4px;
  transform-origin: top center;
}

.av-unban-menu__item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 8px 12px;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--c-text);
  font-size: var(--text-sm);
  font-family: var(--font-sans);
  white-space: nowrap;
  text-align: left;
  transition: background var(--dur-fast) var(--ease);
}

.av-unban-menu__item:hover:not(:disabled) {
  background: var(--c-accent-light);
  color: var(--c-accent);
}

.av-unban-menu__item:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.av-unban-menu__item i {
  font-size: 13px;
  width: 16px;
  text-align: center;
  flex-shrink: 0;
}

.av-dropdown-enter-active {
  transition: opacity var(--dur-normal) var(--ease), transform var(--dur-normal) var(--ease);
}
.av-dropdown-leave-active {
  transition: opacity 150ms var(--ease), transform 150ms var(--ease);
}
.av-dropdown-enter-from {
  opacity: 0;
  transform: translateX(50%) scaleY(0.88) translateY(-4px);
}
.av-dropdown-leave-to {
  opacity: 0;
  transform: translateX(50%) scaleY(0.94) translateY(-2px);
}

/* Modal */
.av-modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 100;
  background: rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.av-modal {
  background: var(--c-surface);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xl);
  width: min(440px, 100%);
  overflow: hidden;
}

.av-modal__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid var(--c-border-light);
}

.av-modal__header h3 { margin: 0; }

.av-modal__body {
  padding: 20px;
}

.av-modal__footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 12px 20px;
  border-top: 1px solid var(--c-border-light);
}

/* Toast */
.av-toast {
  position: fixed;
  top: 20px;
  right: 24px;
  z-index: 200;
  padding: 12px 22px;
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-weight: 500;
  box-shadow: var(--shadow-lg);
  cursor: pointer;
  max-width: 420px;
}
.av-toast--info { background: var(--c-primary); color: var(--c-text-inverse); }
.av-toast--success { background: var(--c-success); color: var(--c-text-inverse); }
.av-toast--error { background: var(--c-danger); color: var(--c-text-inverse); }

.toast-enter-active { transition: all var(--dur-normal) var(--ease); }
.toast-leave-active { transition: all var(--dur-fast) var(--ease); }
.toast-enter-from { opacity: 0; transform: translateX(40px); }
.toast-leave-to { opacity: 0; transform: translateY(-12px); }

/* Category management */
.av-category-hint {
  color: var(--c-text-muted);
  font-size: var(--text-sm);
  margin: -8px 0 16px;
}

.av-category-grid {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-width: 700px;
}

.av-category-card {
  display: flex;
  align-items: center;
  gap: 16px;
}

.av-category-card__main {
  flex: 1;
  min-width: 0;
}

.av-category-card__name {
  margin: 0 0 2px;
  font-size: var(--text-base);
}

.av-category-card__desc {
  margin: 0 0 6px;
  font-size: var(--text-sm);
  color: var(--c-text-muted);
}

.av-category-card__stats {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.av-category-card__order {
  font-size: var(--text-xs);
  color: var(--c-text-muted);
}

.av-category-card__actions {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}

@media (max-width: 768px) {
  .av-header { padding: 0 14px; gap: 10px; }
  .av-header__title { display: none; }
  .av-tabs { overflow-x: auto; }
  .av-main { padding: 16px; }
  .av-stats-grid { grid-template-columns: repeat(2, 1fr); }
  .av-reg-row { flex-direction: column; align-items: flex-start; }
  .av-users-search { max-width: 100%; }
  .av-user-row {
    grid-template-columns: 1fr 60px 44px 48px;
  }
  .av-user-col--name,
  .av-user-col--nickname,
  .av-user-col--role {
    display: none;
  }
  .av-user-row--header .av-user-col--name,
  .av-user-row--header .av-user-col--nickname,
  .av-user-row--header .av-user-col--role {
    display: none;
  }
}

/* ===== Task Link ===== */
.av-task-link {
  font-weight: 600;
  color: var(--c-accent);
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 5px;
  transition: color var(--dur-fast) var(--ease);
}
.av-task-link:hover {
  color: #4338ca;
  text-decoration: underline;
}

/* ===== Snapshot Drawer ===== */
.av-snapshot-overlay {
  position: fixed;
  inset: 0;
  z-index: 2000;
  display: flex;
  justify-content: flex-end;
  background: rgba(0, 0, 0, 0.3);
  backdrop-filter: blur(2px);
}

.av-snapshot-drawer {
  width: 520px;
  max-width: 100vw;
  height: 100vh;
  background: #fff;
  box-shadow: -8px 0 30px rgba(0, 0, 0, 0.12);
  display: flex;
  flex-direction: column;
  animation: av-slide-in 0.25s var(--ease, cubic-bezier(0.16, 1, 0.3, 1));
}

@keyframes av-slide-in {
  from { transform: translateX(100%); }
}

.av-snapshot-drawer__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 24px;
  border-bottom: 1px solid var(--c-border);
  flex-shrink: 0;
}
.av-snapshot-drawer__header h3 {
  margin: 0;
  font-size: 16px;
}

.av-snapshot-drawer__body {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
}

.av-snap-section {
  margin-bottom: 24px;
}
.av-snap-section:last-child {
  margin-bottom: 0;
}

.av-snap-title {
  font-size: 16px;
  font-weight: 600;
  margin: 0 0 8px;
}

.av-snap-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: var(--text-sm);
  color: var(--c-text-secondary);
  margin-bottom: 10px;
}

.av-snap-desc {
  font-size: var(--text-sm);
  color: var(--c-text-secondary);
  line-height: 1.6;
  margin: 0 0 12px;
  white-space: pre-wrap;
}

.av-snap-users {
  background: var(--c-bg-secondary, #f8fafc);
  border-radius: var(--radius-md);
  padding: 10px 14px;
}
.av-snap-user-row {
  display: flex;
  gap: 12px;
  font-size: var(--text-sm);
  padding: 3px 0;
}
.av-snap-user-label {
  color: var(--c-text-muted);
  min-width: 56px;
  flex-shrink: 0;
}

.av-snap-subtitle {
  font-size: 14px;
  font-weight: 600;
  margin: 0 0 10px;
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--c-text);
}

/* Chat */
.av-snap-chat {
  max-height: 360px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px;
  background: var(--c-bg-secondary, #f8fafc);
  border-radius: var(--radius-md);
}

.av-snap-msg__head {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 2px;
}
.av-snap-msg__sender {
  font-size: 12px;
  font-weight: 600;
  color: var(--c-text);
}
.av-snap-msg__time {
  font-size: 11px;
  color: var(--c-text-muted);
}
.av-snap-msg__text {
  font-size: var(--text-sm);
  color: var(--c-text-secondary);
  line-height: 1.5;
  word-break: break-word;
  padding: 6px 10px;
  background: #fff;
  border-radius: var(--radius-sm);
  display: inline-block;
}

/* Reviews */
.av-snap-reviews {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.av-snap-review {
  background: var(--c-bg-secondary, #f8fafc);
  border-radius: var(--radius-md);
  padding: 10px 14px;
}
.av-snap-review__head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}
.av-snap-review__stars {
  display: flex;
  gap: 1px;
}
.av-snap-review__by {
  font-size: 12px;
  color: var(--c-text-muted);
  margin: 0 0 4px;
}
.av-snap-review__comment {
  font-size: var(--text-sm);
  color: var(--c-text-secondary);
  margin: 0;
  line-height: 1.5;
}

.av-snap-empty {
  color: var(--c-text-muted);
  font-size: var(--text-sm);
  text-align: center;
  padding: 16px 0;
}

/* Drawer transition */
.av-drawer-enter-active {
  transition: opacity 0.25s var(--ease);
}
.av-drawer-leave-active {
  transition: opacity 0.2s var(--ease);
}
.av-drawer-enter-from,
.av-drawer-leave-to {
  opacity: 0;
}
</style>
