<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import {
  banUser,
  fetchAdminDashboard,
  fetchAdminReports,
  fetchAdminUsers,
  fetchRegistrationSetting,
  reviewReport,
  updateRegistrationSetting
} from '../api/moderation'
import { useAuthStore } from '../stores/auth'
import type { AdminUserItem, Report } from '../types/api'

const auth = useAuthStore()
const router = useRouter()

const activeTab = ref<'dashboard' | 'reports' | 'users'>('dashboard')

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
const registrationEnabled = ref(true)
const savingRegistration = ref(false)

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
    const [d, r, rs] = await Promise.all([fetchAdminDashboard(), fetchAdminReports(), fetchRegistrationSetting()])
    dashboard.value = d
    reports.value = r
    registrationEnabled.value = rs.registration_enabled
  } catch (error: any) {
    showToast(error?.response?.data?.detail || '加载失败', 'error')
  } finally {
    loading.value = false
  }
}

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
    showToast(error?.response?.data?.detail || '加载用户列表失败', 'error')
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

async function handleReview(report: Report, status: 'approved' | 'rejected') {
  try {
    await reviewReport(report.id, { status, admin_notes: status === 'approved' ? '审核通过' : '审核驳回' })
    showToast(status === 'approved' ? '已通过' : '已驳回', 'success')
    await loadData()
  } catch (error: any) {
    showToast(error?.response?.data?.detail || '审核失败', 'error')
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
    showToast(error?.response?.data?.detail || '封禁失败', 'error')
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
    showToast(error?.response?.data?.detail || '解封失败', 'error')
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
    showToast(error?.response?.data?.detail || '更新注册开关失败', 'error')
  } finally {
    savingRegistration.value = false
  }
}

function onTabChange(key: 'dashboard' | 'reports' | 'users') {
  activeTab.value = key
  if (key === 'users' && userList.value.length === 0) {
    loadUsers()
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
        { key: 'reports', label: '举报审核', icon: 'fa-solid fa-flag' },
        { key: 'users', label: '用户管理', icon: 'fa-solid fa-users-gear' }
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

    <!-- ===== 举报审核 ===== -->
    <section v-if="activeTab === 'reports'" class="av-section">
      <h2 style="margin-bottom: 20px;">举报 / 申诉审核</h2>

      <div v-if="reports.length" class="av-report-list">
        <div v-for="report in reports" :key="report.id" class="card av-report-card">
          <div class="av-report-card__header">
            <div style="display: flex; align-items: center; gap: 8px;">
              <span class="badge badge-default">{{ report.type === 'report' ? '举报' : '申诉' }}</span>
              <span style="font-weight: 600;">#{{ report.id }}</span>
            </div>
            <span class="badge" :class="reportStatusClass(report.status)">{{ reportStatusLabel(report.status) }}</span>
          </div>

          <div class="av-report-card__body">
            <div class="av-report-card__row">
              <span class="av-report-card__label">任务 ID</span>
              <span>{{ report.task_id || '-' }}</span>
            </div>
            <div class="av-report-card__row">
              <span class="av-report-card__label">被举报用户</span>
              <span>{{ report.reported_user_id || '-' }}</span>
            </div>
            <div class="av-report-card__row" style="flex-direction: column; align-items: flex-start; gap: 2px;">
              <span class="av-report-card__label">原因</span>
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
      <div v-else class="av-empty"><i class="fa-regular fa-folder-open" style="font-size: 36px; display: block; margin-bottom: 12px; color: var(--c-border);"></i>暂无举报/申诉数据</div>
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
</style>
