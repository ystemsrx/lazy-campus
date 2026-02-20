<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { appConfirm } from '../components/AppConfirm.vue'
import AppDropdown from '../components/AppDropdown.vue'
import { extractError } from '../utils/error'
import { formatFull, formatShort, isExpired, localToUTC, nowLocal, utcToLocal } from '../utils/time'

import { createReport, fetchMyReports } from '../api/moderation'
import {
  acceptTask,
  confirmTask,
  createReview,
  createTask,
  deleteTask,
  fetchAcceptedTasks,
  fetchCategories,
  fetchMessages,
  fetchPublishedTasks,
  fetchReviews,
  fetchTasks,
  sendMessage,
  updateTask
} from '../api/tasks'
import { fetchMyWorkerProfile, fetchWorkers, updateWorkerProfile, updateProfile, uploadAvatar } from '../api/users'
import { useAuthStore } from '../stores/auth'
import type { Category, Report, Task, TaskMessage, TaskReview, WorkerProfile } from '../types/api'

const router = useRouter()
const auth = useAuthStore()
const appTitle = import.meta.env.VITE_APP_TITLE || '校园任务平台'

/* -------- Navigation -------- */
const activeTab = ref<'hall' | 'workers'>('hall')
const activeMyTab = ref<'tasks' | 'worker' | 'reports'>('tasks')

/* -------- Panels & Modals -------- */
const showUserMenu = ref(false)
const showPostModal = ref(false)
const showEditModal = ref(false)
const editingTask = ref<Task | null>(null)
const showSettingsPanel = ref(false)
const showMyPanel = ref(false)
const showReportsPanel = ref(false)
const settingsTab = ref<'profile' | 'worker'>('profile')
const userMenuRef = ref<HTMLElement | null>(null)

/* -------- Toast -------- */
const toast = ref<{ text: string; type: 'success' | 'error' | 'info' } | null>(null)
let toastTimer = 0

function showToast(text: string, type: 'success' | 'error' | 'info' = 'info') {
  toast.value = { text, type }
  clearTimeout(toastTimer)
  toastTimer = window.setTimeout(() => { toast.value = null }, 3500)
}

/* -------- Sort State -------- */
const taskSort = ref('ranking')
const workerSort = ref('ranking')

const taskSortOptions = [
  { value: 'ranking', label: '综合排序' },
  { value: 'newest', label: '最新发布' },
  { value: 'deadline_asc', label: '截止时间最近' },
  { value: 'publisher_rating', label: '发布人评分最高' },
  { value: 'publisher_completed', label: '发布人完成数最多' },
]

const workerSortOptions = [
  { value: 'ranking', label: '综合排序' },
  { value: 'worker_rating', label: '评分最高' },
  { value: 'worker_completed', label: '完成任务最多' },
]

/* -------- Core State -------- */
const loading = ref(false)
const categories = ref<Category[]>([])
const tasks = ref<Task[]>([])
const selectedTask = ref<Task | null>(null)
const myPublished = ref<Task[]>([])
const myAccepted = ref<Task[]>([])
const workers = ref<WorkerProfile[]>([])
const taskMessages = ref<TaskMessage[]>([])
const taskReviews = ref<TaskReview[]>([])
const myReports = ref<Report[]>([])

/* -------- Forms -------- */
const newTask = ref({
  title: '',
  description: '',
  deadline: '',
  location: '',
  price: 20,
  category_id: null as number | null,
  contact_visibility: 'after_accept' as 'after_accept' | 'internal_only',
  contact_info: '',
  required_gender: null as 'male' | 'female' | null,
})

const workerForm = ref({
  enabled: false,
  skills: '',
  min_price: null as number | null,
  max_price: null as number | null,
  bio: ''
})

const profileForm = ref({
  nickname: '',
  gender: '' as 'male' | 'female' | '',
})

const editTaskForm = ref({
  title: '',
  description: '',
  deadline: '',
  location: '',
  price: 20,
  category_id: null as number | null,
  contact_visibility: 'after_accept' as 'after_accept' | 'internal_only',
  contact_info: '',
  required_gender: null as 'male' | 'female' | null,
})

const chatContent = ref('')
const reviewForm = ref({
  stars: 5,
  comment: ''
})
const reportForm = ref({
  reason: '',
  evidence: ''
})

const avatarUploading = ref(false)

/* -------- Computed -------- */
const me = computed(() => auth.user)

const hasAvatar = computed(() => !!me.value?.avatar_url)

const isParticipant = computed(() => {
  if (!me.value || !selectedTask.value) return false
  return selectedTask.value.publisher_id === me.value.id || selectedTask.value.assignee_id === me.value.id
})

const isPublisher = computed(() => {
  if (!me.value || !selectedTask.value) return false
  return selectedTask.value.publisher_id === me.value.id
})

const canAccept = computed(() => {
  if (!selectedTask.value || !me.value) return false
  if (selectedTask.value.status !== 'open' || selectedTask.value.publisher_id === me.value.id) return false
  if (selectedTask.value.required_gender && selectedTask.value.required_gender !== me.value.gender) return false
  return true
})

const genderMismatch = computed(() => {
  if (!selectedTask.value || !me.value) return false
  if (selectedTask.value.status !== 'open' || selectedTask.value.publisher_id === me.value.id) return false
  return !!selectedTask.value.required_gender && selectedTask.value.required_gender !== me.value.gender
})

const canConfirm = computed(() => {
  if (!selectedTask.value || !me.value) return false
  return selectedTask.value.status === 'in_progress' && selectedTask.value.publisher_id === me.value.id
})

const myReviewTargetRole = computed<'worker' | 'publisher' | null>(() => {
  if (!me.value || !selectedTask.value) return null
  if (selectedTask.value.publisher_id === me.value.id) return 'worker'
  if (selectedTask.value.assignee_id === me.value.id) return 'publisher'
  return null
})

const hasAlreadyReviewed = computed(() => {
  if (!me.value) return false
  return taskReviews.value.some(r => r.reviewer_id === me.value!.id)
})

const bothSidesReviewed = computed(() => {
  if (!isParticipant.value) return true
  const roles = new Set(taskReviews.value.map(r => r.target_role))
  return roles.has('publisher') && roles.has('worker')
})

const waitingForOtherReview = computed(() =>
  hasAlreadyReviewed.value && !bothSidesReviewed.value
)

const canReview = computed(() =>
  selectedTask.value?.status === 'completed' &&
  isParticipant.value &&
  !hasAlreadyReviewed.value
)

const canDeleteTask = computed(() => {
  if (!isPublisher.value || !selectedTask.value) return false
  return selectedTask.value.status === 'open' || selectedTask.value.status === 'canceled'
})

const canEditTask = computed(() => {
  if (!isPublisher.value || !selectedTask.value) return false
  return selectedTask.value.status === 'open'
})

const deleteBlockedByAssignee = computed(() => {
  if (!isPublisher.value || !selectedTask.value) return false
  return selectedTask.value.status === 'in_progress'
})

/* -------- Helpers -------- */
const statusMap: Record<string, { label: string; cls: string }> = {
  open: { label: '待接取', cls: 'badge-blue' },
  in_progress: { label: '进行中', cls: 'badge-amber' },
  completed: { label: '已完成', cls: 'badge-green' },
  canceled: { label: '已取消', cls: 'badge-default' },
  under_review: { label: '审核中', cls: 'badge-red' }
}
function statusOf(s: string) { return statusMap[s] || { label: s, cls: 'badge-default' } }

const genderMap: Record<string, { label: string; icon: string; cls: string }> = {
  male: { label: '限男生', icon: 'fa-solid fa-mars', cls: 'badge-blue' },
  female: { label: '限女生', icon: 'fa-solid fa-venus', cls: 'badge-pink' },
}
function genderLabel(g: string | null) { return g ? genderMap[g] : null }


function reportStatusLabel(s: string) {
  return s === 'pending' ? '待审核' : s === 'approved' ? '已通过' : '已驳回'
}

function reportTypeLabel(s: string) {
  return s === 'report' ? '举报' : '申诉'
}


function starsArray(n: number) {
  return Array.from({ length: 5 }, (_, i) => i < n)
}

/* -------- Data Loading -------- */
async function bootstrap() {
  loading.value = true
  try {
    const publicLoads = [loadCategories(), loadTasks(), loadWorkers()]
    if (auth.isAuthenticated) {
      publicLoads.push(loadMyTasks(), loadMyReports(), loadMyWorkerProfile())
    }
    await Promise.all(publicLoads)
    if (auth.isAuthenticated) initProfileForm()
  } catch (error: any) {
    showToast(extractError(error, '加载失败'), 'error')
  } finally {
    loading.value = false
  }
}

function requireAuth(action?: () => void) {
  if (!auth.isAuthenticated) {
    router.push('/login')
    return false
  }
  action?.()
  return true
}

async function loadCategories() { categories.value = await fetchCategories() }
async function loadTasks() { tasks.value = await fetchTasks({ status: 'open', sort: taskSort.value }) }
async function loadWorkers() { workers.value = await fetchWorkers({ sort: workerSort.value }) }

watch(taskSort, () => loadTasks())
watch(workerSort, () => loadWorkers())

async function loadMyTasks() {
  const [published, accepted] = await Promise.all([fetchPublishedTasks(), fetchAcceptedTasks()])
  myPublished.value = published
  myAccepted.value = accepted
}

async function loadMyWorkerProfile() {
  const p = await fetchMyWorkerProfile()
  workerForm.value = { enabled: p.enabled, skills: p.skills || '', min_price: p.min_price, max_price: p.max_price, bio: p.bio || '' }
}

async function loadMyReports() { myReports.value = await fetchMyReports() }

function initProfileForm() {
  if (me.value) {
    profileForm.value.nickname = me.value.nickname || ''
    profileForm.value.gender = me.value.gender || ''
  }
}

/* -------- Task Detail Drawer -------- */
const messagesEnd = ref<HTMLDivElement | null>(null)

function openDrawer(task: Task) {
  selectedTask.value = task
  refreshTaskMeta()
}
function closeDrawer() { selectedTask.value = null }

async function refreshTaskMeta() {
  if (!selectedTask.value) return
  const taskId = selectedTask.value.id
  try {
    const [msgs, revs] = await Promise.all([fetchMessages(taskId), fetchReviews(taskId)])
    taskMessages.value = msgs
    taskReviews.value = revs
  } catch {
    taskMessages.value = []
    taskReviews.value = await fetchReviews(taskId).catch(() => [])
  }
  await nextTick()
  messagesEnd.value?.scrollIntoView({ behavior: 'smooth' })
}

/* -------- Actions -------- */
async function submitCreateTask() {
  try {
    await createTask({
      title: newTask.value.title,
      description: newTask.value.description,
      deadline: newTask.value.deadline ? localToUTC(newTask.value.deadline) : null,
      location: newTask.value.location || null,
      price: Number(newTask.value.price),
      category_id: newTask.value.category_id,
      contact_visibility: newTask.value.contact_visibility,
      contact_info: newTask.value.contact_visibility === 'after_accept' ? newTask.value.contact_info || null : null,
      required_gender: newTask.value.required_gender,
    })
    showToast('委托发布成功', 'success')
    newTask.value = { title: '', description: '', deadline: '', location: '', price: 20, category_id: null, contact_visibility: 'after_accept', contact_info: '', required_gender: null }
    showPostModal.value = false
    await Promise.all([loadTasks(), loadMyTasks()])
  } catch (error: any) {
    showToast(extractError(error, '发布失败'), 'error')
  }
}

async function submitWorkerProfile() {
  try {
    await updateWorkerProfile({
      enabled: workerForm.value.enabled,
      skills: workerForm.value.skills || null,
      min_price: workerForm.value.min_price,
      max_price: workerForm.value.max_price,
      bio: workerForm.value.bio || null
    })
    showToast('接单资料已更新', 'success')
    await loadWorkers()
  } catch (error: any) {
    showToast(extractError(error, '保存失败'), 'error')
  }
}

async function submitProfileUpdate() {
  if (!profileForm.value.nickname || !profileForm.value.gender) {
    showToast('请填写昵称和性别', 'error')
    return
  }
  try {
    const updated = await updateProfile({
      nickname: profileForm.value.nickname,
      gender: profileForm.value.gender as 'male' | 'female',
    })
    auth.user = updated
    auth.displayName = updated.nickname || updated.name
    localStorage.setItem('display_name', auth.displayName)
    showToast('个人资料已更新', 'success')
  } catch (error: any) {
    showToast(extractError(error, '更新失败'), 'error')
  }
}

async function handleAvatarUpload(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  avatarUploading.value = true
  try {
    const updated = await uploadAvatar(file)
    auth.user = updated
    showToast('头像已更新', 'success')
  } catch (error: any) {
    showToast(extractError(error, '头像上传失败'), 'error')
  } finally {
    avatarUploading.value = false
    input.value = ''
  }
}

async function handleAcceptTask() {
  if (!selectedTask.value) return
  try {
    selectedTask.value = await acceptTask(selectedTask.value.id)
    showToast('已接取该委托', 'success')
    await Promise.all([loadTasks(), loadMyTasks(), refreshTaskMeta()])
  } catch (error: any) {
    showToast(extractError(error, '接取失败'), 'error')
  }
}

async function handleConfirmTask() {
  if (!selectedTask.value) return
  try {
    selectedTask.value = await confirmTask(selectedTask.value.id)
    showToast('已确认完成', 'success')
    await Promise.all([loadTasks(), loadMyTasks(), refreshTaskMeta()])
  } catch (error: any) {
    showToast(extractError(error, '确认失败'), 'error')
  }
}

async function submitMessage() {
  if (!selectedTask.value || !chatContent.value.trim()) return
  try {
    await sendMessage(selectedTask.value.id, chatContent.value.trim())
    chatContent.value = ''
    await refreshTaskMeta()
  } catch (error: any) {
    showToast(extractError(error, '发送失败'), 'error')
  }
}

async function submitReview() {
  if (!selectedTask.value || !myReviewTargetRole.value) return
  try {
    await createReview(selectedTask.value.id, {
      target_role: myReviewTargetRole.value,
      stars: reviewForm.value.stars,
      comment: reviewForm.value.comment || undefined
    })
    reviewForm.value.comment = ''
    reviewForm.value.stars = 5
    await refreshTaskMeta()
    showToast('评价已提交', 'success')
  } catch (error: any) {
    showToast(extractError(error, '评价失败'), 'error')
  }
}

async function handleDeleteTask() {
  if (!selectedTask.value) return
  const yes = await appConfirm({
    title: '确认删除',
    message: '确认删除该任务？此操作不可撤销。',
    confirmText: '删除',
    type: 'danger',
  })
  if (!yes) return
  try {
    await deleteTask(selectedTask.value.id)
    closeDrawer()
    showToast('任务已删除', 'success')
    await Promise.all([loadTasks(), loadMyTasks()])
  } catch (error: any) {
    showToast(extractError(error, '删除失败'), 'error')
  }
}

function openEditModal() {
  if (!selectedTask.value) return
  const t = selectedTask.value
  editingTask.value = t
  editTaskForm.value = {
    title: t.title,
    description: t.description,
    deadline: t.deadline ? utcToLocal(t.deadline) : '',
    location: t.location || '',
    price: t.price,
    category_id: t.category_id,
    contact_visibility: t.contact_visibility,
    contact_info: t.contact_info || '',
    required_gender: t.required_gender,
  }
  closeDrawer()
  showEditModal.value = true
}

async function submitEditTask() {
  if (!editingTask.value) return
  try {
    const updated = await updateTask(editingTask.value.id, {
      title: editTaskForm.value.title,
      description: editTaskForm.value.description,
      deadline: editTaskForm.value.deadline ? localToUTC(editTaskForm.value.deadline) : null,
      location: editTaskForm.value.location || null,
      price: Number(editTaskForm.value.price),
      category_id: editTaskForm.value.category_id,
      contact_visibility: editTaskForm.value.contact_visibility,
      contact_info: editTaskForm.value.contact_visibility === 'after_accept' ? editTaskForm.value.contact_info || null : null,
      required_gender: editTaskForm.value.required_gender,
    })
    showEditModal.value = false
    editingTask.value = null
    showToast('委托信息已更新', 'success')
    await Promise.all([loadTasks(), loadMyTasks()])
    openDrawer(updated)
  } catch (error: any) {
    showToast(extractError(error, '修改失败'), 'error')
  }
}

const canReport = computed(() => {
  if (!me.value || !selectedTask.value) return false
  return isParticipant.value && !!selectedTask.value.assignee_id
})

const reportTargetId = computed(() => {
  if (!me.value || !selectedTask.value) return null
  return me.value.id === selectedTask.value.publisher_id
    ? selectedTask.value.assignee_id
    : selectedTask.value.publisher_id
})

async function submitReport() {
  if (!selectedTask.value || !reportTargetId.value) return
  try {
    await createReport({
      task_id: selectedTask.value.id,
      reported_user_id: reportTargetId.value,
      reason: reportForm.value.reason,
      evidence: reportForm.value.evidence
    })
    reportForm.value.reason = ''
    reportForm.value.evidence = ''
    await loadMyReports()
    showToast('举报已提交，等待管理员审核', 'success')
  } catch (error: any) {
    showToast(extractError(error, '提交失败'), 'error')
  }
}

function logout() {
  auth.logout()
  router.push('/login')
}

/* -------- User Menu helpers -------- */
function openMyPanel() {
  showUserMenu.value = false
  showMyPanel.value = true
}
function openSettings() {
  showUserMenu.value = false
  initProfileForm()
  showSettingsPanel.value = true
}
function openReports() {
  showUserMenu.value = false
  showReportsPanel.value = true
}

function onClickOutsideMenu(e: MouseEvent) {
  if (userMenuRef.value && !userMenuRef.value.contains(e.target as Node)) {
    showUserMenu.value = false
  }
}

onMounted(() => {
  bootstrap()
  document.addEventListener('mousedown', onClickOutsideMenu)
})
onUnmounted(() => {
  document.removeEventListener('mousedown', onClickOutsideMenu)
})
</script>

<template>
  <!-- Toast -->
  <Transition name="toast">
    <div v-if="toast" class="hv-toast" :class="'hv-toast--' + toast.type" @click="toast = null">
      {{ toast.text }}
    </div>
  </Transition>

  <!-- Header -->
  <header class="hv-header">
    <div class="hv-header__brand">
      <div class="hv-logo">T</div>
      <span class="hv-header__title">{{ appTitle }}</span>
    </div>

    <nav class="hv-tabs">
      <button
        class="hv-tab" :class="{ 'hv-tab--active': activeTab === 'hall' }"
        @click="activeTab = 'hall'"
      >
        <i class="fa-solid fa-clipboard-list"></i> 任务大厅
      </button>
      <button
        class="hv-tab" :class="{ 'hv-tab--active': activeTab === 'workers' }"
        @click="activeTab = 'workers'"
      >
        <i class="fa-solid fa-user-group"></i> 接单广场
      </button>
    </nav>

    <div class="hv-header__right">
      <template v-if="auth.isAuthenticated">
        <button class="btn btn-primary btn-sm hv-publish-btn" @click="showPostModal = true">
          <i class="fa-solid fa-plus"></i> 发布
        </button>

        <div ref="userMenuRef" class="hv-user-menu-wrap">
          <button class="hv-user-trigger" @click="showUserMenu = !showUserMenu">
            <div v-if="hasAvatar" class="hv-avatar hv-avatar--img">
              <img :src="me!.avatar_url!" alt="avatar" />
            </div>
            <div v-else class="hv-avatar" :class="me?.gender === 'female' ? 'hv-avatar--female' : 'hv-avatar--male'">
              <i class="fa-solid fa-user"></i>
            </div>
            <span class="hv-header__name">{{ auth.displayName }}</span>
            <i class="fa-solid fa-chevron-down hv-user-trigger__arrow" :class="{ 'hv-user-trigger__arrow--open': showUserMenu }"></i>
          </button>

          <Transition name="app-dropdown">
            <div v-if="showUserMenu" class="hv-user-dropdown">
              <button class="hv-user-dropdown__item" @click="openMyPanel">
                <i class="fa-solid fa-list-check"></i> 任务
              </button>
              <button class="hv-user-dropdown__item" @click="openSettings">
                <i class="fa-solid fa-gear"></i> 设置
              </button>
              <button class="hv-user-dropdown__item" @click="openReports">
                <i class="fa-solid fa-flag"></i> 我的举报
              </button>
              <div class="hv-user-dropdown__divider"></div>
              <button class="hv-user-dropdown__item hv-user-dropdown__item--danger" @click="logout">
                <i class="fa-solid fa-right-from-bracket"></i> 退出登录
              </button>
            </div>
          </Transition>
        </div>
      </template>
      <template v-else>
        <button class="btn btn-primary btn-sm" @click="router.push('/login')">
          <i class="fa-solid fa-right-to-bracket"></i> 登录
        </button>
      </template>
    </div>
  </header>

  <!-- Loading -->
  <div v-if="loading" class="hv-loading">
    <div class="spinner"></div>
    <span>加载中…</span>
  </div>

  <!-- Main Content -->
  <main v-else class="hv-main">

    <!-- ============ 任务大厅 ============ -->
    <section v-if="activeTab === 'hall'" class="hv-section">
      <div class="hv-section__header">
        <h2>任务大厅</h2>
        <span class="hv-section__count">{{ tasks.length }} 个可接任务</span>
        <AppDropdown
          v-model="taskSort"
          :options="taskSortOptions"
          width="auto"
          min-width="160px"
          class="hv-sort-dropdown"
        />
      </div>

      <div v-if="tasks.length" class="hv-task-grid">
        <div v-for="task in tasks" :key="task.id" class="card card-hover hv-task-card" @click="openDrawer(task)">
          <div class="hv-task-card__top">
            <div class="hv-task-card__badges">
              <span class="badge" :class="statusOf(task.status).cls">{{ statusOf(task.status).label }}</span>
              <span v-if="task.required_gender && genderLabel(task.required_gender)" class="badge" :class="genderLabel(task.required_gender)!.cls">
                <i :class="genderLabel(task.required_gender)!.icon" style="margin-right: 3px;"></i>{{ genderLabel(task.required_gender)!.label }}
              </span>
            </div>
            <span class="hv-task-card__price">¥{{ task.price }}</span>
          </div>
          <h4 class="hv-task-card__title">{{ task.title }}</h4>
          <p class="hv-task-card__desc">{{ task.description }}</p>
          <div class="hv-task-card__meta">
            <span v-if="task.location">{{ task.location }}</span>
            <span v-if="task.deadline" :class="{ 'hv-meta--expired': isExpired(task.deadline) }">
              截止 {{ formatShort(task.deadline!) }}
              <span v-if="isExpired(task.deadline)" class="badge badge-red hv-expired-badge">已过期</span>
            </span>
            <span>发布者：{{ task.publisher_display_name }}</span>
          </div>
        </div>
      </div>
      <div v-else class="hv-empty">
        <i class="fa-solid fa-inbox hv-empty__icon"></i>
        <p>暂无可接任务</p>
      </div>
    </section>

    <!-- ============ 接单广场 ============ -->
    <section v-if="activeTab === 'workers'" class="hv-section">
      <div class="hv-section__header">
        <h2>接单广场</h2>
        <span class="hv-section__count">{{ workers.length }} 位接单者</span>
        <AppDropdown
          v-model="workerSort"
          :options="workerSortOptions"
          width="auto"
          min-width="140px"
          class="hv-sort-dropdown"
        />
      </div>

      <div v-if="workers.length" class="hv-worker-grid">
        <div v-for="w in workers" :key="w.user_id" class="card hv-worker-card">
          <div class="hv-worker-card__header">
            <div v-if="w.avatar_url" class="hv-avatar hv-avatar--lg hv-avatar--img">
              <img :src="w.avatar_url" alt="" />
            </div>
            <div v-else class="hv-avatar hv-avatar--lg" :class="w.gender === 'female' ? 'hv-avatar--female' : 'hv-avatar--male'">
              <i class="fa-solid fa-user"></i>
            </div>
            <div class="hv-worker-card__info">
              <h4>{{ w.display_name }}</h4>
              <div class="hv-worker-card__rating">
                <span class="hv-stars">
                  <i v-for="(filled, idx) in starsArray(Math.round(w.worker_rating_avg))" :key="idx" :class="filled ? 'fa-solid fa-star' : 'fa-regular fa-star'"></i>
                </span>
                <span class="hv-worker-card__count">{{ w.worker_rating_avg.toFixed(1) }} 分 · {{ w.worker_rating_count }} 评价</span>
              </div>
            </div>
          </div>
          <div class="hv-worker-card__body">
            <div class="hv-worker-card__row">
              <span class="hv-worker-card__label">擅长</span>
              <span>{{ w.skills || '未设置' }}</span>
            </div>
            <div class="hv-worker-card__row">
              <span class="hv-worker-card__label">价格</span>
              <span>{{ w.min_price ?? '-' }} ~ {{ w.max_price ?? '-' }} 元</span>
            </div>
            <div v-if="w.blocked_by_count > 0" class="hv-worker-card__row">
              <span class="hv-worker-card__label">被拉黑</span>
              <span class="badge badge-red">{{ w.blocked_by_count }} 次</span>
            </div>
            <p v-if="w.bio" class="hv-worker-card__bio">{{ w.bio }}</p>
          </div>
        </div>
      </div>
      <div v-else class="hv-empty">
        <i class="fa-solid fa-users hv-empty__icon"></i>
        <p>暂无接单者</p>
      </div>
    </section>
  </main>

  <!-- ============ 发布委托弹窗 ============ -->
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="showPostModal" class="hv-modal-overlay" @click.self="showPostModal = false">
        <div class="hv-modal hv-modal--md">
          <div class="hv-modal__header">
            <h3>发布新委托</h3>
            <button class="btn btn-ghost btn-sm" @click="showPostModal = false"><i class="fa-solid fa-xmark"></i></button>
          </div>
          <div class="hv-modal__body">
            <p class="hv-hint" style="margin-bottom: 12px;">填写委托信息后发布，其他用户即可在任务大厅看到并接取。</p>
            <form class="hv-form" @submit.prevent="submitCreateTask">
              <div class="form-group">
                <label class="form-label">标题</label>
                <input v-model="newTask.title" class="form-input" placeholder="简要描述你需要完成的事项" required />
              </div>

              <div class="form-group">
                <label class="form-label">详细描述</label>
                <textarea v-model="newTask.description" class="form-textarea" placeholder="详细说明需求、要求和注意事项" style="min-height: 80px;"></textarea>
              </div>

              <div class="form-row">
                <div class="form-group">
                  <label class="form-label">地点</label>
                  <input v-model="newTask.location" class="form-input" placeholder="任务执行地点（选填）" />
                </div>
                <div class="form-group">
                  <label class="form-label">价格 (¥)</label>
                  <input v-model.number="newTask.price" class="form-input" type="number" min="1" placeholder="报酬金额" />
                </div>
              </div>

              <div class="form-row">
                <div class="form-group">
                  <label class="form-label">截止时间</label>
                  <input v-model="newTask.deadline" class="form-input" type="datetime-local" :min="nowLocal()" />
                </div>
                <div class="form-group">
                  <label class="form-label">所属类目</label>
                  <AppDropdown
                    v-model="newTask.category_id"
                    :options="[{ value: null, label: '选择类目' }, ...categories.map(c => ({ value: c.id, label: c.name }))]"
                    placeholder="选择类目"
                  />
                </div>
              </div>

              <div class="form-row">
                <div class="form-group">
                  <label class="form-label">联系方式可见性</label>
                  <AppDropdown
                    v-model="newTask.contact_visibility"
                    :options="[
                      { value: 'after_accept', label: '接取后可见联系方式' },
                      { value: 'internal_only', label: '仅站内沟通' },
                    ]"
                  />
                </div>
                <div class="form-group">
                  <label class="form-label">联系方式</label>
                  <input
                    v-model="newTask.contact_info"
                    class="form-input"
                    :disabled="newTask.contact_visibility === 'internal_only'"
                    placeholder="微信/手机号等（选填）"
                  />
                </div>
              </div>

              <div class="form-group">
                <label class="form-label">接单者性别要求</label>
                <AppDropdown
                  v-model="newTask.required_gender"
                  :options="[
                    { value: null, label: '不限性别' },
                    { value: 'male', label: '仅限男生' },
                    { value: 'female', label: '仅限女生' },
                  ]"
                  placeholder="不限性别"
                />
              </div>

              <button class="btn btn-primary btn-block" type="submit" style="margin-top: 4px;">发布委托</button>
            </form>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>

  <!-- ============ 编辑任务模态框 ============ -->
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="showEditModal" class="hv-modal-overlay" @click.self="showEditModal = false">
        <div class="hv-modal hv-modal--md">
          <div class="hv-modal__header">
            <h3>编辑委托</h3>
            <button class="btn btn-ghost btn-sm" @click="showEditModal = false"><i class="fa-solid fa-xmark"></i></button>
          </div>
          <div class="hv-modal__body">
            <p class="hv-hint" style="margin-bottom: 12px;">任务被接取前可随时修改所有信息。</p>
            <form class="hv-form" @submit.prevent="submitEditTask">
              <div class="form-group">
                <label class="form-label">标题</label>
                <input v-model="editTaskForm.title" class="form-input" placeholder="简要描述你需要完成的事项" required />
              </div>

              <div class="form-group">
                <label class="form-label">详细描述</label>
                <textarea v-model="editTaskForm.description" class="form-textarea" placeholder="详细说明需求、要求和注意事项" style="min-height: 80px;"></textarea>
              </div>

              <div class="form-row">
                <div class="form-group">
                  <label class="form-label">地点</label>
                  <input v-model="editTaskForm.location" class="form-input" placeholder="任务执行地点（选填）" />
                </div>
                <div class="form-group">
                  <label class="form-label">价格 (¥)</label>
                  <input v-model.number="editTaskForm.price" class="form-input" type="number" min="1" placeholder="报酬金额" />
                </div>
              </div>

              <div class="form-row">
                <div class="form-group">
                  <label class="form-label">截止时间</label>
                  <input v-model="editTaskForm.deadline" class="form-input" type="datetime-local" :min="nowLocal()" />
                </div>
                <div class="form-group">
                  <label class="form-label">所属类目</label>
                  <AppDropdown
                    v-model="editTaskForm.category_id"
                    :options="[{ value: null, label: '选择类目' }, ...categories.map(c => ({ value: c.id, label: c.name }))]"
                    placeholder="选择类目"
                  />
                </div>
              </div>

              <div class="form-row">
                <div class="form-group">
                  <label class="form-label">联系方式可见性</label>
                  <AppDropdown
                    v-model="editTaskForm.contact_visibility"
                    :options="[
                      { value: 'after_accept', label: '接取后可见联系方式' },
                      { value: 'internal_only', label: '仅站内沟通' },
                    ]"
                  />
                </div>
                <div class="form-group">
                  <label class="form-label">联系方式</label>
                  <input
                    v-model="editTaskForm.contact_info"
                    class="form-input"
                    :disabled="editTaskForm.contact_visibility === 'internal_only'"
                    placeholder="微信/手机号等（选填）"
                  />
                </div>
              </div>

              <div class="form-group">
                <label class="form-label">接单者性别要求</label>
                <AppDropdown
                  v-model="editTaskForm.required_gender"
                  :options="[
                    { value: null, label: '不限性别' },
                    { value: 'male', label: '仅限男生' },
                    { value: 'female', label: '仅限女生' },
                  ]"
                  placeholder="不限性别"
                />
              </div>

              <button class="btn btn-primary btn-block" type="submit" style="margin-top: 4px;">保存修改</button>
            </form>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>

  <!-- ============ 我的任务面板 ============ -->
  <Teleport to="body">
    <Transition name="drawer">
      <div v-if="showMyPanel" class="hv-drawer-overlay" @click.self="showMyPanel = false">
        <div class="hv-drawer">
          <div class="hv-drawer__header">
            <h3>我的任务</h3>
            <button class="btn btn-ghost btn-sm" @click="showMyPanel = false"><i class="fa-solid fa-xmark"></i></button>
          </div>
          <div class="hv-drawer__body" style="padding: 20px 24px;">
            <div class="hv-my-tasks-vertical">
              <div class="hv-my-col">
                <h4>我发布的 <span class="badge badge-default">{{ myPublished.length }}</span></h4>
                <div v-if="myPublished.length" class="hv-record-list">
                  <div v-for="t in myPublished" :key="t.id" class="hv-record card card-hover" @click="showMyPanel = false; openDrawer(t)">
                    <div class="hv-record__top">
                      <span class="hv-record__title">{{ t.title }}</span>
                      <div style="display: flex; gap: 5px; align-items: center; flex-shrink: 0;">
                        <span v-if="t.status === 'open' && isExpired(t.deadline)" class="badge badge-red">已过期</span>
                        <span class="badge" :class="statusOf(t.status).cls">{{ statusOf(t.status).label }}</span>
                      </div>
                    </div>
                    <div class="hv-record__meta">¥{{ t.price }}<template v-if="t.assignee_display_name"> · 接单者：{{ t.assignee_display_name }}</template></div>
                  </div>
                </div>
                <p v-else class="hv-empty-text">暂无发布的任务</p>
              </div>

              <div class="hv-my-col">
                <h4>我接取的 <span class="badge badge-default">{{ myAccepted.length }}</span></h4>
                <div v-if="myAccepted.length" class="hv-record-list">
                  <div v-for="t in myAccepted" :key="t.id" class="hv-record card card-hover" @click="showMyPanel = false; openDrawer(t)">
                    <div class="hv-record__top">
                      <span class="hv-record__title">{{ t.title }}</span>
                      <span class="badge" :class="statusOf(t.status).cls">{{ statusOf(t.status).label }}</span>
                    </div>
                    <div class="hv-record__meta">¥{{ t.price }} · 发布者：{{ t.publisher_display_name }}</div>
                  </div>
                </div>
                <p v-else class="hv-empty-text">暂无接取的任务</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>

  <!-- ============ 设置面板 ============ -->
  <Teleport to="body">
    <Transition name="drawer">
      <div v-if="showSettingsPanel" class="hv-drawer-overlay" @click.self="showSettingsPanel = false">
        <div class="hv-drawer">
          <div class="hv-drawer__header">
            <h3>设置</h3>
            <button class="btn btn-ghost btn-sm" @click="showSettingsPanel = false"><i class="fa-solid fa-xmark"></i></button>
          </div>
          <div class="hv-drawer__body">
            <div class="hv-settings-tabs">
              <button class="hv-pill" :class="{ 'hv-pill--active': settingsTab === 'profile' }" @click="settingsTab = 'profile'">
                <i class="fa-solid fa-user"></i> 个人资料
              </button>
              <button class="hv-pill" :class="{ 'hv-pill--active': settingsTab === 'worker' }" @click="settingsTab = 'worker'">
                <i class="fa-solid fa-id-card"></i> 接单设置
              </button>
            </div>

            <!-- 个人资料 -->
            <div v-if="settingsTab === 'profile'" class="hv-drawer__section">
              <div class="hv-avatar-section">
                <div v-if="hasAvatar" class="hv-avatar hv-avatar--xl hv-avatar--img">
                  <img :src="me!.avatar_url!" alt="avatar" />
                </div>
                <div v-else class="hv-avatar hv-avatar--xl" :class="me?.gender === 'female' ? 'hv-avatar--female' : 'hv-avatar--male'">
                  <i class="fa-solid fa-user"></i>
                </div>
                <div class="hv-avatar-actions">
                  <label class="btn btn-outline btn-sm hv-avatar-upload-btn">
                    <i class="fa-solid fa-camera"></i>
                    {{ avatarUploading ? '上传中...' : '更换头像' }}
                    <input type="file" accept="image/*" hidden @change="handleAvatarUpload" :disabled="avatarUploading" />
                  </label>
                  <span class="hv-hint">支持 JPG/PNG，最大 10MB</span>
                </div>
              </div>

              <form class="hv-form" @submit.prevent="submitProfileUpdate">
                <div class="form-group">
                  <label class="form-label">姓名</label>
                  <input class="form-input" :value="me?.name" disabled />
                  <span class="form-hint">姓名不可修改</span>
                </div>

                <div class="form-group">
                  <label class="form-label">昵称</label>
                  <input v-model="profileForm.nickname" class="form-input" placeholder="输入昵称" required />
                </div>

                <div class="form-group">
                  <label class="form-label">性别</label>
                  <AppDropdown
                    v-model="profileForm.gender"
                    :options="[
                      { value: 'male', label: '男' },
                      { value: 'female', label: '女' },
                    ]"
                    placeholder="选择性别"
                  />
                </div>

                <button class="btn btn-primary btn-block" type="submit">保存资料</button>
              </form>
            </div>

            <!-- 接单设置 -->
            <div v-if="settingsTab === 'worker'" class="hv-drawer__section">
              <p class="hv-hint" style="margin-bottom: 12px;">开启后你将出现在接单广场，其他用户可以查看你的资料。</p>
              <form class="hv-form" @submit.prevent="submitWorkerProfile">
                <label class="hv-switch-row">
                  <input v-model="workerForm.enabled" type="checkbox" class="hv-switch" />
                  <span>开启接单（对外展示）</span>
                </label>

                <div class="form-group">
                  <label class="form-label">擅长类型</label>
                  <input v-model="workerForm.skills" class="form-input" placeholder="如：高数、前端开发、跑腿取件" />
                </div>

                <div class="form-row">
                  <div class="form-group">
                    <label class="form-label">最低价 (¥)</label>
                    <input v-model.number="workerForm.min_price" class="form-input" type="number" placeholder="最低接单价格" />
                  </div>
                  <div class="form-group">
                    <label class="form-label">最高价 (¥)</label>
                    <input v-model.number="workerForm.max_price" class="form-input" type="number" placeholder="最高接单价格" />
                  </div>
                </div>

                <div class="form-group">
                  <label class="form-label">个人简介</label>
                  <textarea v-model="workerForm.bio" class="form-textarea" placeholder="介绍一下自己的能力和服务"></textarea>
                </div>

                <button class="btn btn-primary btn-block" type="submit">保存接单资料</button>
              </form>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>

  <!-- ============ 举报记录面板 ============ -->
  <Teleport to="body">
    <Transition name="drawer">
      <div v-if="showReportsPanel" class="hv-drawer-overlay" @click.self="showReportsPanel = false">
        <div class="hv-drawer">
          <div class="hv-drawer__header">
            <h3>我的举报</h3>
            <button class="btn btn-ghost btn-sm" @click="showReportsPanel = false"><i class="fa-solid fa-xmark"></i></button>
          </div>
          <div class="hv-drawer__body" style="padding: 20px 24px;">
            <div v-if="myReports.length" class="hv-record-list">
              <div v-for="r in myReports" :key="r.id" class="card hv-report-item">
                <div class="hv-record__top">
                  <span class="badge badge-default">{{ reportTypeLabel(r.type) }}</span>
                  <span class="badge" :class="r.status === 'pending' ? 'badge-amber' : r.status === 'approved' ? 'badge-green' : 'badge-red'">{{ reportStatusLabel(r.status) }}</span>
                </div>
                <p style="margin: 6px 0 0; color: var(--c-text-secondary); font-size: var(--text-sm);">{{ r.reason }}</p>
              </div>
            </div>
            <p v-else class="hv-empty-text">暂无举报记录</p>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>

  <!-- ============ Task Detail Drawer ============ -->
  <Teleport to="body">
    <Transition name="drawer">
      <div v-if="selectedTask" class="hv-drawer-overlay" @click.self="closeDrawer">
        <div class="hv-drawer">
          <div class="hv-drawer__header">
            <h3>任务详情</h3>
            <button class="btn btn-ghost btn-sm" @click="closeDrawer" aria-label="关闭"><i class="fa-solid fa-xmark"></i></button>
          </div>

          <div class="hv-drawer__body">
            <!-- Basic Info -->
            <div class="hv-drawer__section">
              <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px; flex-wrap: wrap;">
                <span class="badge" :class="statusOf(selectedTask.status).cls">{{ statusOf(selectedTask.status).label }}</span>
                <span v-if="selectedTask.required_gender && genderLabel(selectedTask.required_gender)" class="badge" :class="genderLabel(selectedTask.required_gender)!.cls">
                  <i :class="genderLabel(selectedTask.required_gender)!.icon" style="margin-right: 3px;"></i>{{ genderLabel(selectedTask.required_gender)!.label }}
                </span>
                <span style="font-size: var(--text-2xl); font-weight: 700; color: var(--c-accent);">¥{{ selectedTask.price }}</span>
              </div>
              <h3 style="margin-bottom: 8px;">{{ selectedTask.title }}</h3>
              <p style="color: var(--c-text-secondary); line-height: 1.7; margin-bottom: 12px;">{{ selectedTask.description }}</p>

              <div class="hv-detail-grid">
                <div class="hv-detail-item">
                  <span class="hv-detail-label">发布者</span>
                  <span>{{ selectedTask.publisher_display_name }}</span>
                </div>
                <div class="hv-detail-item">
                  <span class="hv-detail-label">地点</span>
                  <span>{{ selectedTask.location || '未填写' }}</span>
                </div>
                <div class="hv-detail-item">
                  <span class="hv-detail-label">截止</span>
                  <span v-if="selectedTask.deadline" :class="{ 'hv-meta--expired': isExpired(selectedTask.deadline) }">
                    {{ formatFull(selectedTask.deadline!) }}
                    <span v-if="isExpired(selectedTask.deadline)" class="badge badge-red" style="margin-left: 4px;">已过期</span>
                  </span>
                  <span v-else>未设置</span>
                </div>
                <div class="hv-detail-item">
                  <span class="hv-detail-label">联系方式</span>
                  <span>{{ selectedTask.contact_info || '仅站内沟通' }}</span>
                </div>
              </div>

              <div v-if="!auth.isAuthenticated && selectedTask.status === 'open'" class="hv-drawer__actions">
                <button class="btn btn-primary" @click="router.push('/login')"><i class="fa-solid fa-right-to-bracket"></i> 登录后接取任务</button>
              </div>
              <div v-else-if="canAccept || canConfirm || isPublisher || genderMismatch" class="hv-drawer__actions">
                <button v-if="canAccept" class="btn btn-primary" @click="handleAcceptTask"><i class="fa-solid fa-hand-pointer"></i> 接取此任务</button>
                <button v-if="canConfirm" class="btn btn-success" @click="handleConfirmTask"><i class="fa-solid fa-circle-check"></i> 确认完成</button>
                <button v-if="canEditTask" class="btn btn-outline btn-sm" @click="openEditModal"><i class="fa-solid fa-pen-to-square"></i> 编辑</button>
                <button v-if="canDeleteTask" class="btn btn-danger btn-sm" @click="handleDeleteTask"><i class="fa-solid fa-trash"></i> 删除任务</button>
                <span v-if="deleteBlockedByAssignee" class="hv-delete-hint"><i class="fa-solid fa-lock"></i> 任务已被接取，接单者取消后方可删除</span>
                <span v-if="genderMismatch" class="hv-delete-hint"><i class="fa-solid fa-ban"></i> 该任务限{{ selectedTask!.required_gender === 'male' ? '男生' : '女生' }}接取，您不满足要求</span>
              </div>
            </div>

            <!-- Messages -->
            <div class="hv-drawer__section">
              <h4 class="hv-drawer__subtitle"><i class="fa-regular fa-comment-dots"></i> 站内消息</h4>
              <div v-if="isParticipant" class="hv-chat">
                <div class="hv-chat__messages">
                  <div v-for="m in taskMessages" :key="m.id" class="hv-chat__msg" :class="{ 'hv-chat__msg--mine': me && m.sender_id === me.id }">
                    <span class="hv-chat__sender">{{ m.sender_display_name }}</span>
                    <span class="hv-chat__text">{{ m.content }}</span>
                  </div>
                  <p v-if="taskMessages.length === 0" style="color: var(--c-text-muted); font-size: var(--text-sm); text-align: center; padding: 16px 0;">暂无消息</p>
                  <div ref="messagesEnd"></div>
                </div>
                <form class="hv-chat__input" @submit.prevent="submitMessage">
                  <input v-model="chatContent" class="form-input" placeholder="输入消息..." />
                  <button class="btn btn-primary btn-sm" type="submit">发送</button>
                </form>
              </div>
              <p v-else style="color: var(--c-text-muted); font-size: var(--text-sm);">仅任务参与者可查看和发送消息。</p>
            </div>

            <!-- Reviews -->
            <div class="hv-drawer__section">
              <h4 class="hv-drawer__subtitle"><i class="fa-regular fa-star-half-stroke"></i> 双向互评</h4>
              <div class="hv-reviews">
                <div v-for="r in taskReviews" :key="r.id" class="hv-review">
                  <div class="hv-review__header">
                    <span class="badge badge-default">{{ r.target_role === 'worker' ? '评价接单者' : '评价发布者' }}</span>
                    <span class="hv-stars hv-stars--sm">
                      <i v-for="(filled, idx) in starsArray(r.stars)" :key="idx" :class="filled ? 'fa-solid fa-star' : 'fa-regular fa-star'"></i>
                    </span>
                    <span v-if="me && r.reviewer_id === me.id" class="hv-review__mine">我的评价</span>
                  </div>
                  <p v-if="r.comment" class="hv-review__comment">{{ r.comment }}</p>
                </div>
                <p v-if="taskReviews.length === 0" style="color: var(--c-text-muted); font-size: var(--text-sm);">暂无评价</p>
              </div>

              <div v-if="waitingForOtherReview" class="hv-reviewed-hint hv-reviewed-hint--waiting">
                <i class="fa-solid fa-hourglass-half"></i> 您已评价，等待对方评价后双方评价互相可见
              </div>
              <div v-else-if="selectedTask?.status === 'completed' && isParticipant && hasAlreadyReviewed && bothSidesReviewed" class="hv-reviewed-hint">
                <i class="fa-solid fa-circle-check"></i> 互评已完成
              </div>

              <div v-if="canReview" class="hv-review-form">
                <div style="display: flex; gap: 10px; align-items: center; flex-wrap: wrap;">
                  <span class="badge badge-default">{{ myReviewTargetRole === 'worker' ? '评价接单者' : '评价发布者' }}</span>
                  <div class="hv-star-input">
                    <button v-for="n in 5" :key="n" type="button" class="hv-star-btn" :class="{ active: n <= reviewForm.stars }" @click="reviewForm.stars = n">
                      <i :class="n <= reviewForm.stars ? 'fa-solid fa-star' : 'fa-regular fa-star'"></i>
                    </button>
                  </div>
                </div>
                <div style="display: flex; gap: 8px; margin-top: 8px;">
                  <input v-model="reviewForm.comment" class="form-input" placeholder="评价内容（选填）" />
                  <button class="btn btn-primary btn-sm" @click="submitReview">提交</button>
                </div>
              </div>
            </div>

            <!-- Report -->
            <div v-if="canReport" class="hv-drawer__section">
              <h4 class="hv-drawer__subtitle"><i class="fa-solid fa-flag"></i> 举报对方</h4>
              <input v-model="reportForm.reason" class="form-input" placeholder="问题描述（必填）" style="margin-bottom: 8px;" />
              <textarea v-model="reportForm.evidence" class="form-textarea" style="min-height: 64px;" placeholder="证据说明（链接、截图描述等）"></textarea>
              <button class="btn btn-outline btn-sm" style="margin-top: 6px;" @click="submitReport">提交举报</button>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
/* ===== Header ===== */
.hv-header {
  position: sticky;
  top: 0;
  z-index: 40;
  display: flex;
  align-items: center;
  padding: 0 24px;
  height: 60px;
  background: rgba(255, 255, 255, 0.82);
  backdrop-filter: blur(14px);
  border-bottom: 1px solid var(--c-border);
}

.hv-header__brand {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.hv-logo {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-sm);
  background: var(--c-accent);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 16px;
}

.hv-header__title {
  font-weight: 700;
  font-size: var(--text-lg);
  color: var(--c-text);
}

.hv-header__right {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}

.hv-header__name {
  font-size: var(--text-sm);
  color: var(--c-text-secondary);
}

.hv-publish-btn {
  border-radius: var(--radius-full);
  padding: 6px 18px;
}

/* ===== Avatar ===== */
.hv-avatar {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-full);
  background: linear-gradient(135deg, var(--c-accent-soft), var(--c-accent));
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 13px;
  flex-shrink: 0;
  overflow: hidden;
}

.hv-avatar--lg {
  width: 44px;
  height: 44px;
  font-size: 17px;
}

.hv-avatar--xl {
  width: 72px;
  height: 72px;
  font-size: 28px;
}

.hv-avatar--male {
  background: linear-gradient(135deg, #93c5fd, #3b82f6);
}

.hv-avatar--female {
  background: linear-gradient(135deg, #f9a8d4, #ec4899);
}

.hv-avatar--img {
  background: none;
}

.hv-avatar--img img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

/* ===== User Menu ===== */
.hv-user-menu-wrap {
  position: relative;
}

.hv-user-trigger {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 8px 4px 4px;
  background: transparent;
  border: none;
  border-radius: var(--radius-full);
  transition: background var(--dur-fast) var(--ease);
}

.hv-user-trigger:hover {
  background: var(--c-border-light);
}

.hv-user-trigger__arrow {
  font-size: 10px;
  color: var(--c-text-muted);
  transition: transform var(--dur-normal) var(--ease);
}

.hv-user-trigger__arrow--open {
  transform: rotate(180deg);
}

.hv-user-dropdown {
  position: absolute;
  top: calc(100% + 6px);
  right: 0;
  min-width: 180px;
  background: #ffffff;
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xl);
  z-index: 1000;
  padding: 5px;
  transform-origin: top right;
}

.hv-user-dropdown__item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 9px 14px;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--c-text);
  font-size: var(--text-base);
  font-family: var(--font-sans);
  cursor: pointer;
  text-align: left;
  transition: background var(--dur-fast) var(--ease), color var(--dur-fast) var(--ease);
}

.hv-user-dropdown__item i {
  width: 16px;
  text-align: center;
  color: var(--c-text-muted);
}

.hv-user-dropdown__item:hover {
  background: var(--c-accent-light);
  color: var(--c-accent);
}

.hv-user-dropdown__item:hover i {
  color: var(--c-accent);
}

.hv-user-dropdown__item--danger:hover {
  background: var(--c-danger-light);
  color: var(--c-danger);
}

.hv-user-dropdown__item--danger:hover i {
  color: var(--c-danger);
}

.hv-user-dropdown__divider {
  height: 1px;
  background: var(--c-border-light);
  margin: 4px 8px;
}

/* ===== Tabs ===== */
.hv-tabs {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  gap: 4px;
}

.hv-tab {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 20px;
  border: none;
  background: transparent;
  color: var(--c-text-muted);
  font-size: var(--text-sm);
  font-weight: 500;
  border-radius: var(--radius-sm);
  transition: color var(--dur-fast) var(--ease), background var(--dur-fast) var(--ease);
}

.hv-tab:hover {
  color: var(--c-text);
  background: var(--c-border-light);
}

.hv-tab--active {
  color: var(--c-accent);
  background: var(--c-accent-light);
}

/* ===== Pills (sub-tabs) ===== */
.hv-settings-tabs {
  display: flex;
  gap: 6px;
  padding: 16px 24px;
  border-bottom: 1px solid var(--c-border-light);
}

.hv-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 18px;
  border: 1.5px solid var(--c-border);
  border-radius: var(--radius-full);
  background: transparent;
  color: var(--c-text-secondary);
  font-size: var(--text-sm);
  font-weight: 500;
  transition: all var(--dur-fast) var(--ease);
}

.hv-pill:hover {
  border-color: var(--c-text-muted);
}

.hv-pill--active {
  background: var(--c-primary);
  color: var(--c-text-inverse);
  border-color: transparent;
}

/* ===== Main ===== */
.hv-main {
  padding: 24px;
  max-width: 1200px;
  margin: 0 auto;
}

.hv-section__header {
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 20px;
}

.hv-section__count {
  font-size: var(--text-sm);
  color: var(--c-text-muted);
}

.hv-sort-dropdown {
  margin-left: auto;
}

/* ===== Loading ===== */
.hv-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  height: calc(100vh - 60px);
  color: var(--c-text-muted);
  font-size: var(--text-sm);
}

/* ===== Task Card Grid ===== */
.hv-task-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 14px;
}

.hv-task-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.hv-task-card__top {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.hv-task-card__badges {
  display: flex;
  gap: 6px;
  align-items: center;
  flex-wrap: wrap;
}

.hv-task-card__price {
  font-size: var(--text-xl);
  font-weight: 700;
  color: var(--c-accent);
}

.hv-task-card__title {
  font-size: var(--text-lg);
  margin: 0;
  line-height: 1.4;
}

.hv-task-card__desc {
  color: var(--c-text-secondary);
  font-size: var(--text-sm);
  line-height: 1.55;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  margin: 0;
}

.hv-task-card__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 14px;
  font-size: var(--text-xs);
  color: var(--c-text-muted);
  margin-top: auto;
  padding-top: 6px;
  border-top: 1px solid var(--c-border-light);
}

/* ===== Worker Grid ===== */
.hv-worker-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 14px;
}

.hv-worker-card__header {
  display: flex;
  gap: 14px;
  align-items: center;
  margin-bottom: 14px;
}

.hv-worker-card__info h4 {
  margin: 0 0 2px;
}

.hv-worker-card__rating {
  display: flex;
  align-items: center;
  gap: 6px;
}

.hv-worker-card__count {
  font-size: var(--text-xs);
  color: var(--c-text-muted);
}

.hv-worker-card__body {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.hv-worker-card__row {
  display: flex;
  justify-content: space-between;
  font-size: var(--text-sm);
  color: var(--c-text-secondary);
}

.hv-worker-card__label {
  color: var(--c-text-muted);
  flex-shrink: 0;
}

.hv-worker-card__bio {
  margin: 6px 0 0;
  padding-top: 8px;
  border-top: 1px solid var(--c-border-light);
  font-size: var(--text-sm);
  color: var(--c-text-secondary);
  line-height: 1.55;
}

/* ===== Stars ===== */
.hv-stars {
  color: #f59e0b;
  font-size: var(--text-sm);
  letter-spacing: 1px;
}

.hv-stars--sm {
  font-size: var(--text-xs);
}

.hv-star-input {
  display: flex;
  gap: 2px;
}

.hv-star-btn {
  border: none;
  background: transparent;
  font-size: 22px;
  color: var(--c-border);
  padding: 0 2px;
  transition: color var(--dur-fast) var(--ease), transform var(--dur-fast) var(--ease);
}

.hv-star-btn.active {
  color: #f59e0b;
}

.hv-star-btn:hover {
  transform: scale(1.2);
}

/* ===== My Tasks (vertical layout in drawer) ===== */
.hv-my-tasks-vertical {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.hv-my-col h4 {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.hv-record-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.hv-record {
  padding: 14px 16px !important;
}

.hv-record__top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

.hv-record__title {
  font-weight: 600;
  font-size: var(--text-base);
}

.hv-record__meta {
  font-size: var(--text-sm);
  color: var(--c-text-muted);
  margin-top: 4px;
}

.hv-report-item {
  padding: 14px 16px !important;
}

/* ===== Empty States ===== */
.hv-empty {
  text-align: center;
  padding: 60px 20px;
  color: var(--c-text-muted);
}

.hv-empty__icon {
  display: block;
  font-size: 44px;
  margin-bottom: 14px;
  color: var(--c-border);
}

.hv-empty-text {
  color: var(--c-text-muted);
  font-size: var(--text-sm);
  padding: 20px 0;
}

/* ===== Form Card ===== */
.hv-form {
  display: flex;
  flex-direction: column;
  gap: 14px;
  margin-top: 16px;
}

.hv-hint {
  color: var(--c-text-muted);
  font-size: var(--text-sm);
  margin: 0;
}

.hv-switch-row {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  font-size: var(--text-base);
}

.hv-switch {
  appearance: none;
  width: 40px;
  height: 22px;
  border-radius: 11px;
  background: var(--c-border);
  position: relative;
  cursor: pointer;
  transition: background var(--dur-fast) var(--ease);
  flex-shrink: 0;
}

.hv-switch::after {
  content: '';
  position: absolute;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #fff;
  top: 2px;
  left: 2px;
  transition: transform var(--dur-fast) var(--ease);
  box-shadow: 0 1px 3px rgba(0,0,0,0.15);
}

.hv-switch:checked {
  background: var(--c-accent);
}

.hv-switch:checked::after {
  transform: translateX(18px);
}

/* ===== Avatar Section ===== */
.hv-avatar-section {
  display: flex;
  align-items: center;
  gap: 20px;
  padding-bottom: 20px;
  border-bottom: 1px solid var(--c-border-light);
}

.hv-avatar-actions {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.hv-avatar-upload-btn {
  cursor: pointer;
}

/* ===== Toast ===== */
.hv-toast {
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

.hv-toast--info { background: var(--c-primary); color: var(--c-text-inverse); }
.hv-toast--success { background: var(--c-success); color: var(--c-text-inverse); }
.hv-toast--error { background: var(--c-danger); color: var(--c-text-inverse); }

.toast-enter-active { transition: all var(--dur-normal) var(--ease); }
.toast-leave-active { transition: all var(--dur-fast) var(--ease); }
.toast-enter-from { opacity: 0; transform: translateX(40px); }
.toast-leave-to { opacity: 0; transform: translateY(-12px); }

/* ===== Modal ===== */
.hv-modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 100;
  background: rgba(15, 23, 42, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
}

.hv-modal {
  background: var(--c-surface);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-xl);
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.hv-modal--md {
  width: min(640px, 92vw);
}

.hv-modal__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  border-bottom: 1px solid var(--c-border);
  flex-shrink: 0;
}

.hv-modal__header h3 { margin: 0; }

.hv-modal__body {
  padding: 20px 24px 24px;
  overflow-y: auto;
}

/* ===== Drawer ===== */
.hv-drawer-overlay {
  position: fixed;
  inset: 0;
  z-index: 100;
  background: rgba(15, 23, 42, 0.35);
  display: flex;
  justify-content: flex-end;
}

.hv-drawer {
  width: min(540px, 92vw);
  height: 100vh;
  background: var(--c-surface);
  display: flex;
  flex-direction: column;
  box-shadow: -4px 0 24px rgba(0, 0, 0, 0.12);
}

.hv-drawer__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  border-bottom: 1px solid var(--c-border);
  flex-shrink: 0;
}

.hv-drawer__header h3 { margin: 0; }

.hv-drawer__body {
  flex: 1;
  overflow-y: auto;
  padding: 0;
}

.hv-drawer__section {
  padding: 20px 24px;
  border-bottom: 1px solid var(--c-border-light);
}

.hv-drawer__section:last-child { border-bottom: none; }

.hv-drawer__subtitle {
  margin: 0 0 12px;
  font-size: var(--text-base);
  color: var(--c-text-secondary);
  display: flex;
  align-items: center;
  gap: 7px;
}

.hv-drawer__actions {
  display: flex;
  gap: 10px;
  margin-top: 16px;
}

.hv-detail-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.hv-detail-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: var(--text-sm);
}

.hv-detail-label {
  color: var(--c-text-muted);
  font-size: var(--text-xs);
}

/* ===== Chat ===== */
.hv-chat__messages {
  max-height: 220px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 10px;
  padding: 4px 0;
}

.hv-chat__msg {
  display: flex;
  flex-direction: column;
  gap: 2px;
  max-width: 85%;
}

.hv-chat__msg--mine {
  align-self: flex-end;
  align-items: flex-end;
}

.hv-chat__sender {
  font-size: var(--text-xs);
  color: var(--c-text-muted);
}

.hv-chat__text {
  display: inline-block;
  padding: 8px 12px;
  border-radius: var(--radius-md);
  background: var(--c-border-light);
  font-size: var(--text-sm);
  line-height: 1.5;
  word-break: break-word;
}

.hv-chat__msg--mine .hv-chat__text {
  background: var(--c-accent);
  color: #fff;
}

.hv-chat__input {
  display: flex;
  gap: 8px;
}

/* ===== Reviews ===== */
.hv-reviews {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 14px;
}

.hv-review {
  padding: 10px 14px;
  background: var(--c-border-light);
  border-radius: var(--radius-md);
}

.hv-review__header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.hv-review__comment {
  margin: 6px 0 0;
  font-size: var(--text-sm);
  color: var(--c-text-secondary);
}

.hv-review-form {
  padding: 12px 14px;
  background: var(--c-border-light);
  border-radius: var(--radius-md);
}

.hv-review__mine {
  font-size: var(--text-xs);
  color: var(--c-accent);
  margin-left: auto;
}

.hv-reviewed-hint {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: var(--text-sm);
  color: var(--c-success);
  padding: 8px 0;
}

.hv-reviewed-hint--waiting {
  color: var(--c-text-muted);
}

.hv-delete-hint {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: var(--text-xs);
  color: var(--c-text-muted);
}

/* ===== Expired ===== */
.hv-meta--expired {
  color: var(--c-danger) !important;
}

.hv-expired-badge {
  font-size: 10px;
  padding: 1px 5px;
  vertical-align: middle;
  margin-left: 3px;
}

/* ===== Gender Badge ===== */
.badge-pink {
  background: #fce7f3;
  color: #be185d;
}

/* ===== Transitions ===== */
.drawer-enter-active { transition: all var(--dur-slow) var(--ease); }
.drawer-leave-active { transition: all var(--dur-normal) var(--ease); }
.drawer-enter-from,
.drawer-leave-to { opacity: 0; }
.drawer-enter-from .hv-drawer { transform: translateX(100%); }
.drawer-leave-to .hv-drawer { transform: translateX(100%); }

.modal-enter-active { transition: all var(--dur-normal) var(--ease); }
.modal-leave-active { transition: all var(--dur-fast) var(--ease); }
.modal-enter-from { opacity: 0; }
.modal-leave-to { opacity: 0; }
.modal-enter-from .hv-modal { transform: scale(0.95) translateY(10px); }
.modal-leave-to .hv-modal { transform: scale(0.97) translateY(5px); }

.app-dropdown-enter-active {
  transition: opacity var(--dur-normal) var(--ease), transform var(--dur-normal) var(--ease);
}
.app-dropdown-leave-active {
  transition: opacity 180ms var(--ease), transform 180ms var(--ease);
}
.app-dropdown-enter-from {
  opacity: 0;
  transform: scaleY(0.88) translateY(-6px);
}
.app-dropdown-leave-to {
  opacity: 0;
  transform: scaleY(0.94) translateY(-3px);
}

/* ===== Responsive ===== */
@media (max-width: 900px) {
  .hv-header {
    padding: 0 14px;
  }
  .hv-header__title { display: none; }
  .hv-header__name { display: none; }
  .hv-tabs {
    position: static;
    transform: none;
  }
  .hv-main { padding: 16px; }
  .hv-task-grid { grid-template-columns: 1fr; }
  .hv-worker-grid { grid-template-columns: 1fr; }
  .hv-detail-grid { grid-template-columns: 1fr; }
}
</style>
