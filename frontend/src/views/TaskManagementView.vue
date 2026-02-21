<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  LayoutDashboard, BarChart3, Plus,
  Clock, CheckCircle2, Send, ClipboardList,
} from 'lucide-vue-next'
import { useAuthStore } from '../stores/auth'
import { appConfirm } from '../components/AppConfirm.vue'
import {
  acceptTask, confirmTask, createTask, deleteTask, updateTask,
  fetchAcceptedTasks, fetchCategories, fetchPublishedTasks,
  fetchMessages, fetchReviews, sendMessage, createReview,
} from '../api/tasks'
import {
  fetchUserReviews, fetchMyWorkerProfile, updateWorkerProfile,
  updateProfile, uploadAvatar,
} from '../api/users'
import { createReport, fetchMyReports } from '../api/moderation'
import type { Task, Category, TaskMessage, TaskReview, UserReview, Report } from '../types/api'
import { isExpired, formatShort, formatFull, nowLocal, localToUTC, utcToLocal } from '../utils/time'
import { extractError } from '../utils/error'
import { getTaskIcon } from '../utils/taskIcons'
import HomeHeaderBar from '../components/home/HomeHeaderBar.vue'
import HomeSettingsDrawer from '../components/home/HomeSettingsDrawer.vue'
import HomeReportsDrawer from '../components/home/HomeReportsDrawer.vue'
import HomeTaskEditorModal from '../components/home/HomeTaskEditorModal.vue'
import HomeTaskDetailDrawer from '../components/home/HomeTaskDetailDrawer.vue'
import HomeToast from '../components/home/HomeToast.vue'
import HomeStatsSection from '../components/home/HomeStatsSection.vue'

const router = useRouter()
const auth = useAuthStore()
const appTitle = import.meta.env.VITE_APP_TITLE || '校园任务平台'

const activeView = ref<'dashboard' | 'stats'>('dashboard')
const activeRole = ref<'assignee' | 'publisher'>('assignee')
const activeStatus = ref<'pending' | 'progress' | 'completed'>('progress')
const loading = ref(false)
const myPublished = ref<Task[]>([])
const myAccepted = ref<Task[]>([])
const categories = ref<Category[]>([])
const showCreateModal = ref(false)
const showEditModal = ref(false)
const editingTask = ref<Task | null>(null)

const showSettingsPanel = ref(false)
const showReportsPanel = ref(false)
const settingsTab = ref<'profile' | 'worker'>('profile')
const avatarUploading = ref(false)
const myReports = ref<Report[]>([])
const profileForm = ref({ nickname: '', gender: '' as 'male' | 'female' | '' })
const workerForm = ref({
  enabled: false,
  skill_tag_ids: [] as number[],
  min_price: null as number | null,
  max_price: null as number | null,
  bio: '',
  phone: '',
  wechat: '',
})

const toast = ref<{ text: string; type: 'success' | 'error' | 'info' } | null>(null)
let toastTimer = 0

function showToast(text: string, type: 'success' | 'error' | 'info' = 'info') {
  toast.value = { text, type }
  clearTimeout(toastTimer)
  toastTimer = window.setTimeout(() => { toast.value = null }, 3500)
}

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
  icon: 'Hexagon',
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
  icon: 'Hexagon',
})

// ---- Task Detail State ----
const selectedTask = ref<Task | null>(null)
const taskMessages = ref<TaskMessage[]>([])
const taskReviews = ref<TaskReview[]>([])
const publisherHistoryReviews = ref<UserReview[]>([])
const chatContent = ref('')
const showReviewForm = ref(false)
const reviewForm = ref({ stars: 5, comment: '' })
const reportForm = ref({ reason: '', evidence: '' })

// ---- Computed: task data ----
type MyTask = Task & { myRole: 'publisher' | 'assignee' }

const byDate = (a: Task, b: Task) =>
  new Date(b.created_at).getTime() - new Date(a.created_at).getTime()

const assigneeTotal = computed(() => myAccepted.value.length)
const publisherTotal = computed(() => myPublished.value.length)

const assigneeProgress = computed(() =>
  myAccepted.value.filter(t => t.status === 'open' || t.status === 'in_progress').length)
const publisherPending = computed(() =>
  myPublished.value.filter(t => t.status === 'open').length)
const publisherProgress = computed(() =>
  myPublished.value.filter(t => t.status === 'in_progress').length)

// 切换到"我接取的"时，若当前是"待接取"则重置为"进行中"
watch(activeRole, (role) => {
  if (role === 'assignee' && activeStatus.value === 'pending') {
    activeStatus.value = 'progress'
  }
})

const currentTasks = computed<MyTask[]>(() => {
  const base = activeRole.value === 'assignee'
    ? myAccepted.value.map(t => ({ ...t, myRole: 'assignee' as const }))
    : myPublished.value.map(t => ({ ...t, myRole: 'publisher' as const }))
  return base
    .filter(t => {
      if (activeStatus.value === 'pending') return t.status === 'open'
      if (activeStatus.value === 'progress') {
        return activeRole.value === 'assignee'
          ? (t.status === 'open' || t.status === 'in_progress')
          : t.status === 'in_progress'
      }
      return ['completed', 'canceled', 'under_review'].includes(t.status)
    })
    .sort(byDate)
})

const emptyText = computed(() => {
  if (activeRole.value === 'assignee') {
    return activeStatus.value === 'progress' ? '还没有进行中的委托，去任务大厅接取任务吧' : '还没有完成过的委托'
  }
  if (activeStatus.value === 'pending') return '暂无等待接单的任务'
  if (activeStatus.value === 'progress') return '暂无正在进行中的任务'
  return '没有已结束的发布任务'
})

// ---- Status / Gender helpers ----
const statusMap: Record<string, { label: string; cls: string }> = {
  open: { label: '待接取', cls: 'badge-blue' },
  in_progress: { label: '进行中', cls: 'badge-amber' },
  completed: { label: '已完成', cls: 'badge-green' },
  canceled: { label: '已取消', cls: 'badge-default' },
  under_review: { label: '审核中', cls: 'badge-red' },
}

function statusOf(s: string) {
  return statusMap[s] || { label: s, cls: 'badge-default' }
}

const genderMap: Record<string, { label: string; icon: string; cls: string }> = {
  male: { label: '限男生', icon: 'fa-solid fa-mars', cls: 'badge-blue' },
  female: { label: '限女生', icon: 'fa-solid fa-venus', cls: 'badge-pink' },
}

function genderLabel(g: string | null) {
  return g ? genderMap[g] : null
}

// ---- Computed: task detail permissions ----
const me = computed(() => auth.user)

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

const canEditTask = computed(() => {
  if (!isPublisher.value || !selectedTask.value) return false
  return selectedTask.value.status === 'open'
})

const canDeleteTask = computed(() => {
  if (!isPublisher.value || !selectedTask.value) return false
  return selectedTask.value.status === 'open' || selectedTask.value.status === 'canceled'
})

const deleteBlockedByAssignee = computed(() => {
  if (!isPublisher.value || !selectedTask.value) return false
  return selectedTask.value.status === 'in_progress'
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

const waitingForOtherReview = computed(() => hasAlreadyReviewed.value && !bothSidesReviewed.value)

const canReview = computed(() => selectedTask.value?.status === 'completed' && isParticipant.value && !hasAlreadyReviewed.value)

const canReport = computed(() => {
  if (!me.value || !selectedTask.value) return false
  return isParticipant.value && !!selectedTask.value.assignee_id
})

const reportTargetId = computed(() => {
  if (!me.value || !selectedTask.value) return null
  return me.value.id === selectedTask.value.publisher_id ? selectedTask.value.assignee_id : selectedTask.value.publisher_id
})

// ---- Data loading ----
async function loadMyTasks() {
  const [pub, acc] = await Promise.all([fetchPublishedTasks(), fetchAcceptedTasks()])
  myPublished.value = pub
  myAccepted.value = acc
}

async function loadCategories() {
  categories.value = await fetchCategories()
}

async function loadMyWorkerProfile() {
  try {
    const p = await fetchMyWorkerProfile()
    workerForm.value = {
      enabled: p.enabled,
      skill_tag_ids: p.skill_tags.map((t: { id: number }) => t.id),
      min_price: p.min_price,
      max_price: p.max_price,
      bio: p.bio || '',
      phone: p.phone || '',
      wechat: p.wechat || '',
    }
  } catch { /* 非接单者时忽略 */ }
}

async function loadMyReports() {
  try {
    myReports.value = await fetchMyReports()
  } catch { /* 忽略 */ }
}

function initProfileForm() {
  if (me.value) {
    profileForm.value.nickname = me.value.nickname || ''
    profileForm.value.gender = me.value.gender || ''
  }
}

function openSettings() {
  initProfileForm()
  settingsTab.value = 'profile'
  showSettingsPanel.value = true
}

function openReports() {
  loadMyReports()
  showReportsPanel.value = true
}

function logout() {
  auth.logout()
  router.push('/login')
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

async function submitWorkerProfile() {
  try {
    await updateWorkerProfile({
      enabled: workerForm.value.enabled,
      skill_tag_ids: workerForm.value.skill_tag_ids,
      min_price: workerForm.value.min_price,
      max_price: workerForm.value.max_price,
      bio: workerForm.value.bio || null,
      phone: workerForm.value.phone || null,
      wechat: workerForm.value.wechat || null,
    })
    showToast('接单资料已更新', 'success')
  } catch (error: any) {
    showToast(extractError(error, '保存失败'), 'error')
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

async function bootstrap() {
  loading.value = true
  try {
    await Promise.all([loadMyTasks(), loadCategories(), loadMyWorkerProfile(), loadMyReports()])
  } catch (error: any) {
    showToast(extractError(error, '加载失败'), 'error')
  } finally {
    loading.value = false
  }
}

// ---- Task detail actions ----
function openDrawer(task: Task) {
  selectedTask.value = task
  showReviewForm.value = false
  refreshTaskMeta()
  refreshPublisherReviews()
}

function closeDrawer() {
  selectedTask.value = null
}

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
}

async function refreshPublisherReviews() {
  if (!selectedTask.value) return
  try {
    publisherHistoryReviews.value = await fetchUserReviews(selectedTask.value.publisher_id, 'publisher')
  } catch {
    publisherHistoryReviews.value = []
  }
}

async function handleAcceptTask() {
  if (!selectedTask.value) return
  try {
    selectedTask.value = await acceptTask(selectedTask.value.id)
    showToast('已接取该委托', 'success')
    await Promise.all([loadMyTasks(), refreshTaskMeta()])
  } catch (error: any) {
    showToast(extractError(error, '接取失败'), 'error')
  }
}

async function handleConfirmTask() {
  if (!selectedTask.value) return
  try {
    selectedTask.value = await confirmTask(selectedTask.value.id)
    showToast('已确认完成', 'success')
    await Promise.all([loadMyTasks(), refreshTaskMeta()])
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
      comment: reviewForm.value.comment || undefined,
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
    await loadMyTasks()
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
    icon: t.icon || 'Hexagon',
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
      icon: editTaskForm.value.icon,
    })
    showEditModal.value = false
    editingTask.value = null
    showToast('委托信息已更新', 'success')
    await loadMyTasks()
    openDrawer(updated)
  } catch (error: any) {
    showToast(extractError(error, '修改失败'), 'error')
  }
}

async function submitReport() {
  if (!selectedTask.value || !reportTargetId.value) return
  try {
    await createReport({
      task_id: selectedTask.value.id,
      reported_user_id: reportTargetId.value,
      reason: reportForm.value.reason,
      evidence: reportForm.value.evidence,
    })
    reportForm.value.reason = ''
    reportForm.value.evidence = ''
    showToast('举报已提交，等待管理员审核', 'success')
  } catch (error: any) {
    showToast(extractError(error, '提交失败'), 'error')
  }
}

// ---- Create task ----
function openCreateTask() {
  if (!auth.isAuthenticated) {
    router.push('/login')
    return
  }
  showCreateModal.value = true
}

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
      icon: newTask.value.icon,
    })
    showToast('委托发布成功', 'success')
    newTask.value = {
      title: '', description: '', deadline: '', location: '',
      price: 20, category_id: null,
      contact_visibility: 'after_accept', contact_info: '',
      required_gender: null, icon: 'Hexagon',
    }
    showCreateModal.value = false
    await loadMyTasks()
  } catch (error: any) {
    showToast(extractError(error, '发布失败'), 'error')
  }
}

function openTaskDetail(task: MyTask) {
  openDrawer(task)
}

onMounted(() => bootstrap())
onUnmounted(() => clearTimeout(toastTimer))
</script>

<template>
  <div class="tm-page">
    <HomeToast :toast="toast" @dismiss="toast = null" />

    <!-- Top Header Bar (same as home) -->
    <HomeHeaderBar
      :active-tab="null"
      :app-title="appTitle"
      :is-authenticated="auth.isAuthenticated"
      :display-name="auth.displayName"
      :avatar-url="me?.avatar_url"
      :gender="me?.gender ?? null"
      @publish="openCreateTask"
      @open-my-panel="() => {}"
      @open-settings="openSettings"
      @open-reports="openReports"
      @login="router.push('/login')"
      @logout="logout"
      @update:active-tab="(t) => router.push({ path: '/', query: t === 'workers' ? { tab: 'workers' } : {} })"
    />

    <!-- Body: sidebar + main -->
    <div class="tm-body">
      <!-- Desktop Sidebar -->
      <aside class="tm-sidebar">
        <button
          class="tm-sidebar__btn"
          :class="{ 'tm-sidebar__btn--active': activeView === 'dashboard' }"
          @click="activeView = 'dashboard'"
        >
          <LayoutDashboard :size="22" />
          <span>任务</span>
        </button>
        <button class="tm-sidebar__add-btn" @click="openCreateTask">
          <Plus :size="22" />
          <span>发布</span>
        </button>
        <button
          class="tm-sidebar__btn"
          :class="{ 'tm-sidebar__btn--active': activeView === 'stats' }"
          @click="activeView = 'stats'"
        >
          <BarChart3 :size="22" />
          <span>统计</span>
        </button>
      </aside>

      <!-- Main Content -->
      <main class="tm-main">
        <!-- Page title (below the header bar) -->
        <div class="tm-page-title">
          <h1>任务<span>管理</span></h1>
          <p>管理你发布和接取的所有任务</p>
        </div>

        <div class="tm-content">
        <!-- Dashboard -->
        <template v-if="activeView === 'dashboard'">
          <div v-if="loading" class="tm-loading"><div class="spinner"></div></div>
          <template v-else>
            <!-- Role Switcher -->
            <div class="tm-role-switcher">
              <button
                class="tm-role-btn"
                :class="{ 'tm-role-btn--active': activeRole === 'assignee' }"
                @click="activeRole = 'assignee'"
              >
                <div class="tm-role-btn__icon">
                  <ClipboardList :size="20" />
                </div>
                <div class="tm-role-btn__body">
                  <span class="tm-role-btn__label">我接取的</span>
                  <span class="tm-role-btn__count">{{ assigneeTotal }} 个委托 · {{ assigneeProgress }} 进行中</span>
                </div>
              </button>
              <button
                class="tm-role-btn"
                :class="{ 'tm-role-btn--active': activeRole === 'publisher' }"
                @click="activeRole = 'publisher'"
              >
                <div class="tm-role-btn__icon">
                  <Send :size="20" />
                </div>
                <div class="tm-role-btn__body">
                  <span class="tm-role-btn__label">我发布的</span>
                  <span class="tm-role-btn__count">{{ publisherTotal }} 个任务 · {{ publisherPending }} 待接取</span>
                </div>
              </button>
            </div>

            <!-- Status Tabs -->
            <div class="tm-tabs">
              <button
                v-if="activeRole === 'publisher'"
                :class="{ 'tm-tab--active': activeStatus === 'pending' }"
                @click="activeStatus = 'pending'"
              >
                <div class="tm-tab__icon"><ClipboardList :size="16" /></div>
                待接取
                <span v-if="publisherPending" class="tm-tab__badge">{{ publisherPending }}</span>
              </button>
              <button :class="{ 'tm-tab--active': activeStatus === 'progress' }" @click="activeStatus = 'progress'">
                <div class="tm-tab__icon"><Clock :size="16" /></div>
                进行中
              </button>
              <button :class="{ 'tm-tab--active': activeStatus === 'completed' }" @click="activeStatus = 'completed'">
                <div class="tm-tab__icon"><CheckCircle2 :size="16" /></div>
                已完成
              </button>
            </div>

            <div v-if="currentTasks.length" class="tm-task-grid">
              <div
                v-for="task in currentTasks"
                :key="`${task.myRole}-${task.id}`"
                class="tm-task-card"
                @click="openTaskDetail(task)"
              >
                <div class="tm-task-card__header">
                  <div class="tm-task-card__icon" :style="{ backgroundColor: getTaskIcon(task.icon).bg }">
                    <component :is="getTaskIcon(task.icon).component" :size="22" :style="{ color: getTaskIcon(task.icon).color }" />
                  </div>
                  <div class="tm-task-card__info">
                    <h3>{{ task.title }}</h3>
                    <span class="tm-task-card__role">
                      {{ task.myRole === 'publisher' && task.assignee_display_name
                        ? '接单人: ' + task.assignee_display_name
                        : task.myRole === 'assignee'
                          ? '发布人: ' + task.publisher_display_name
                          : '暂无接单人' }}
                    </span>
                  </div>
                  <span class="badge" :class="statusOf(task.status).cls">{{ statusOf(task.status).label }}</span>
                </div>

                <p class="tm-task-card__desc">{{ task.description }}</p>

                <div class="tm-task-card__footer">
                  <div class="tm-task-card__metas">
                    <div v-if="task.deadline" class="tm-task-card__meta">
                      <Clock :size="14" />
                      <span :class="{ 'tm-danger': isExpired(task.deadline) }">
                        {{ isExpired(task.deadline) ? '已过期' : formatShort(task.deadline) }}
                      </span>
                    </div>
                    <div v-if="task.location" class="tm-task-card__meta">
                      <span>{{ task.location }}</span>
                    </div>
                  </div>
                  <span class="tm-task-card__price">¥{{ task.price }}</span>
                </div>
              </div>
            </div>

            <div v-else class="tm-empty">
              <ClipboardList :size="48" />
              <h3>暂无任务</h3>
              <p>{{ emptyText }}</p>
            </div>
          </template>
        </template>

        <!-- Stats -->
        <template v-else-if="activeView === 'stats'">
          <HomeStatsSection
            :my-accepted="myAccepted"
            :my-published="myPublished"
            :categories="categories"
          />
        </template>
        </div>
      </main>
    </div>

    <!-- Mobile Bottom Bar -->
    <nav class="tm-bottombar">
      <button
        class="tm-bottombar__item"
        :class="{ 'tm-bottombar__item--active': activeView === 'dashboard' }"
        @click="activeView = 'dashboard'"
      >
        <LayoutDashboard :size="22" />
        <span>任务</span>
      </button>
      <button class="tm-bottombar__item tm-bottombar__item--add" @click="openCreateTask">
        <div class="tm-bottombar__add-circle">
          <Plus :size="22" />
        </div>
        <span>发布</span>
      </button>
      <button
        class="tm-bottombar__item"
        :class="{ 'tm-bottombar__item--active': activeView === 'stats' }"
        @click="activeView = 'stats'"
      >
        <BarChart3 :size="22" />
        <span>统计</span>
      </button>
    </nav>

    <!-- Settings Drawer -->
    <HomeSettingsDrawer
      v-model="showSettingsPanel"
      v-model:settings-tab="settingsTab"
      :me="me"
      :avatar-uploading="avatarUploading"
      :profile-form="profileForm"
      :worker-form="workerForm"
      :categories="categories"
      @submit-profile="submitProfileUpdate"
      @submit-worker="submitWorkerProfile"
      @avatar-upload="handleAvatarUpload"
    />

    <!-- Reports Drawer -->
    <HomeReportsDrawer v-model="showReportsPanel" :my-reports="myReports" />

    <!-- Create Task Modal -->
    <HomeTaskEditorModal
      v-model="showCreateModal"
      mode="create"
      :form="newTask"
      :categories="categories"
      :now-local="nowLocal"
      @submit="submitCreateTask"
    />

    <!-- Edit Task Modal -->
    <HomeTaskEditorModal
      v-model="showEditModal"
      mode="edit"
      :form="editTaskForm"
      :categories="categories"
      :now-local="nowLocal"
      @submit="submitEditTask"
    />

    <!-- Task Detail Drawer -->
    <HomeTaskDetailDrawer
      :task="selectedTask"
      :is-authenticated="auth.isAuthenticated"
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
      @login="router.push('/login')"
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
}

/* ---- Body (sidebar + main) ---- */
.tm-body {
  display: flex;
  flex: 1;
}

/* ---- Sidebar ---- */
.tm-sidebar {
  width: 80px;
  background: #ffffff;
  border-right: 1px solid var(--c-border-light);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 20px;
  position: fixed;
  top: 60px;
  left: 0;
  bottom: 0;
  z-index: 10;
  box-shadow: 4px 0 24px rgba(0, 0, 0, 0.02);
}

.tm-sidebar__btn {
  width: 64px;
  padding: 10px 6px;
  border-radius: 14px;
  border: none;
  background: transparent;
  color: var(--c-text-muted);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 5px;
  cursor: pointer;
  transition: all 0.2s var(--ease);
  font-size: 11px;
  font-weight: 500;
  font-family: var(--font-sans);
  line-height: 1;
}

.tm-sidebar__btn:hover {
  background: var(--c-border-light);
  color: var(--c-text);
}

.tm-sidebar__btn--active {
  background: var(--c-accent-light);
  color: var(--c-accent);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
}

.tm-sidebar__add-btn {
  width: 64px;
  padding: 10px 6px;
  border-radius: 14px;
  background: #0f172a;
  color: #ffffff;
  border: none;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 5px;
  cursor: pointer;
  box-shadow: 0 4px 16px rgba(15, 23, 42, 0.28);
  transition: all 0.2s var(--ease);
  font-size: 11px;
  font-weight: 600;
  font-family: var(--font-sans);
  line-height: 1;
}

.tm-sidebar__add-btn:hover {
  background: #1e293b;
  transform: translateY(-1px);
  box-shadow: 0 6px 20px rgba(15, 23, 42, 0.35);
}

/* ---- Main ---- */
.tm-main {
  flex: 1;
  margin-left: 80px;
  display: flex;
  flex-direction: column;
  min-height: calc(100vh - 60px);
  min-height: calc(100dvh - 60px);
}

/* ---- Page Title (below top bar) ---- */
.tm-page-title {
  padding: 28px 32px 0;
  flex-shrink: 0;
}

.tm-page-title h1 {
  margin: 0;
  font-size: 26px;
  font-weight: 800;
  color: var(--c-text);
  display: flex;
  align-items: center;
  gap: 4px;
  line-height: 1.2;
}

.tm-page-title h1 span {
  color: var(--c-accent);
}

.tm-page-title p {
  margin: 6px 0 0;
  font-size: 13px;
  color: var(--c-text-muted);
  font-weight: 500;
}

/* ---- Content ---- */
.tm-content {
  flex: 1;
  padding: 24px 32px 32px;
}

.tm-content::-webkit-scrollbar { width: 6px; }
.tm-content::-webkit-scrollbar-track { background: transparent; }
.tm-content::-webkit-scrollbar-thumb { background-color: #cbd5e1; border-radius: 20px; }
.tm-content:hover::-webkit-scrollbar-thumb { background-color: #94a3b8; }

/* ---- Loading ---- */
.tm-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 300px;
}

/* ---- Role Switcher ---- */
.tm-role-switcher {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
  margin-bottom: 24px;
}

.tm-role-btn {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 18px 20px;
  border-radius: 20px;
  border: 2px solid transparent;
  background: #ffffff;
  cursor: pointer;
  transition: all 0.25s var(--ease);
  text-align: left;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.04);
  font-family: var(--font-sans);
}

.tm-role-btn:hover {
  border-color: var(--c-border);
  box-shadow: 0 4px 18px rgba(0, 0, 0, 0.08);
}

.tm-role-btn--active {
  border-color: var(--c-accent);
  background: var(--c-accent-light);
  box-shadow: 0 4px 18px rgba(0, 0, 0, 0.08);
}

.tm-role-btn__icon {
  width: 46px;
  height: 46px;
  border-radius: 14px;
  background: var(--c-border-light);
  color: var(--c-text-muted);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all 0.25s var(--ease);
}

.tm-role-btn--active .tm-role-btn__icon {
  background: var(--c-accent);
  color: #ffffff;
}

.tm-role-btn__body {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.tm-role-btn__label {
  font-size: 15px;
  font-weight: 700;
  color: var(--c-text);
  display: block;
}

.tm-role-btn--active .tm-role-btn__label {
  color: var(--c-accent);
}

.tm-role-btn__count {
  font-size: 12px;
  color: var(--c-text-muted);
  font-weight: 500;
  display: block;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ---- Status Tabs ---- */
.tm-tabs {
  display: flex;
  gap: 10px;
  margin-bottom: 28px;
  max-width: 560px;
}

.tm-tabs button {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 11px 18px;
  border-radius: 12px;
  border: none;
  font-weight: 700;
  font-size: 13px;
  font-family: var(--font-sans);
  cursor: pointer;
  transition: all 0.25s var(--ease);
  background: #ffffff;
  color: var(--c-text-muted);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.tm-tabs button:hover {
  background: var(--c-border-light);
  color: var(--c-text);
}

.tm-tab__icon {
  padding: 4px;
  border-radius: 7px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--c-accent-light);
  color: var(--c-accent);
}

.tm-tab--active {
  background: var(--c-accent) !important;
  color: #ffffff !important;
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.14) !important;
}

.tm-tab--active .tm-tab__icon {
  background: rgba(255, 255, 255, 0.2) !important;
  color: #ffffff !important;
}

.tm-tab__badge {
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  border-radius: 9px;
  background: var(--c-accent);
  color: #ffffff;
  font-size: 11px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
}

.tm-tab--active .tm-tab__badge {
  background: rgba(255, 255, 255, 0.3);
}

/* ---- Task Grid ---- */
.tm-task-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
  padding-bottom: 16px;
}

/* ---- Task Card ---- */
.tm-task-card {
  background: #ffffff;
  padding: 24px;
  border-radius: 24px;
  border: 1px solid rgba(0, 0, 0, 0.03);
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.04);
  display: flex;
  flex-direction: column;
  cursor: pointer;
  transition: all 0.3s var(--ease);
}

.tm-task-card:hover {
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
}

.tm-task-card__header {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  margin-bottom: 14px;
}

.tm-task-card__icon {
  width: 48px;
  height: 48px;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.tm-task-card__info {
  flex: 1;
  min-width: 0;
}

.tm-task-card__info h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  color: var(--c-text);
  line-height: 1.3;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.tm-task-card__role {
  font-size: 12px;
  color: var(--c-text-muted);
  margin-top: 2px;
  display: block;
}

.tm-task-card__desc {
  color: var(--c-text-secondary);
  font-size: 14px;
  line-height: 1.6;
  margin: 0 0 16px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  flex: 1;
}

.tm-task-card__footer {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  margin-top: auto;
}

.tm-task-card__metas {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.tm-task-card__meta {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--c-text-muted);
  font-weight: 500;
}

.tm-task-card__price {
  font-size: 20px;
  font-weight: 700;
  color: var(--c-accent);
}

.tm-danger {
  color: var(--c-danger) !important;
  font-weight: 600;
}

/* ---- Empty ---- */
.tm-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 64px 20px;
  color: var(--c-text-muted);
  text-align: center;
}

.tm-empty h3 {
  margin: 16px 0 4px;
  font-size: 18px;
  color: var(--c-text-secondary);
}

.tm-empty p {
  margin: 0;
  font-size: 14px;
}


/* ---- Bottom Bar ---- */
.tm-bottombar {
  display: none;
}

/* ---- Mobile ---- */
@media (max-width: 900px) {
  .tm-sidebar {
    display: none;
  }

  .tm-main {
    margin-left: 0;
    padding-bottom: 80px;
    min-height: calc(100vh - 60px);
    min-height: calc(100dvh - 60px);
  }

  .tm-page-title {
    padding: 20px 16px 0;
  }

  .tm-page-title h1 {
    font-size: 22px;
  }

  .tm-content {
    padding: 16px 16px 16px;
  }

  .tm-tabs {
    gap: 8px;
  }

  .tm-tabs button {
    padding: 10px 12px;
    font-size: 13px;
    gap: 6px;
    border-radius: 12px;
  }

  .tm-tab__icon {
    padding: 4px;
    border-radius: 6px;
  }

  .tm-task-grid {
    grid-template-columns: 1fr;
    gap: 12px;
  }

  .tm-task-card {
    padding: 16px;
    border-radius: 16px;
  }

  .tm-task-card__icon {
    width: 40px;
    height: 40px;
    border-radius: 12px;
  }

  .tm-task-card__header {
    gap: 10px;
    margin-bottom: 10px;
  }

  .tm-task-card__info h3 {
    font-size: 14px;
  }

  .tm-task-card__desc {
    font-size: 13px;
    margin-bottom: 12px;
  }

  .tm-task-card__price {
    font-size: 18px;
  }

  .tm-bottombar {
    display: flex;
    justify-content: space-around;
    align-items: flex-end;
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    background: #ffffff;
    border-top: 1px solid var(--c-border-light);
    padding: 6px 0;
    padding-bottom: calc(6px + env(safe-area-inset-bottom, 0px));
    z-index: 50;
  }

  .tm-bottombar__item {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 3px;
    padding: 6px 20px;
    border: none;
    background: transparent;
    color: var(--c-text-muted);
    font-size: 11px;
    font-weight: 500;
    font-family: var(--font-sans);
    cursor: pointer;
    transition: color 0.2s var(--ease);
    flex: 1;
  }

  .tm-bottombar__item--active {
    color: var(--c-accent);
  }

  .tm-bottombar__item--add {
    color: var(--c-text);
  }

  .tm-bottombar__add-circle {
    width: 44px;
    height: 44px;
    border-radius: 50%;
    background: #0f172a;
    color: #ffffff;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 4px 15px rgba(15, 23, 42, 0.35);
    margin-top: -20px;
    transition: background 0.2s var(--ease);
  }

  .tm-bottombar__item--add:hover .tm-bottombar__add-circle {
    background: #1e293b;
  }

  .tm-role-switcher {
    gap: 10px;
  }

  .tm-role-btn {
    padding: 14px 14px;
    gap: 10px;
    border-radius: 16px;
  }

  .tm-role-btn__icon {
    width: 38px;
    height: 38px;
    border-radius: 11px;
  }

  .tm-role-btn__label {
    font-size: 14px;
  }

  .tm-role-btn__count {
    font-size: 11px;
  }
}
</style>
