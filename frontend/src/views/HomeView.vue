<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { appConfirm } from '../components/AppConfirm.vue'
import { extractError } from '../utils/error'
import { formatFull, formatShort, isExpired, localToUTC, nowLocal, utcToLocal } from '../utils/time'

import { createReport } from '../api/moderation'
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
  updateTask,
} from '../api/tasks'
import {
  fetchWorkerDetail,
  revealWorkerContact,
  fetchUserReviews,
  fetchWorkers,
} from '../api/users'
import HomeHallSection from '../components/home/HomeHallSection.vue'
import HomeHeaderBar from '../components/home/HomeHeaderBar.vue'
import HomeLoadingState from '../components/home/HomeLoadingState.vue'
import HomeMyTasksDrawer from '../components/home/HomeMyTasksDrawer.vue'
import HomeTaskDetailDrawer from '../components/home/HomeTaskDetailDrawer.vue'
import HomeTaskEditorModal from '../components/home/HomeTaskEditorModal.vue'
import AppToast from '../components/AppToast.vue'
import { useAppToast } from '../composables/useAppToast'
import HomeWorkerDetailDrawer from '../components/home/HomeWorkerDetailDrawer.vue'
import HomeWorkersSection from '../components/home/HomeWorkersSection.vue'
import { useAuthStore } from '../stores/auth'
import type { Category, Task, TaskMessage, TaskReview, UserReview, WorkerContactReveal, WorkerProfile } from '../types/api'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const appTitle = import.meta.env.VITE_APP_TITLE || '校园任务平台'

const activeTab = ref<'hall' | 'workers'>(
  route.query.tab === 'workers' ? 'workers' : 'hall'
)

const showPostModal = ref(false)
const showEditModal = ref(false)
const editingTask = ref<Task | null>(null)
const showMyPanel = ref(false)

const { toast, showToast, clearToast } = useAppToast()

const taskSort = ref('ranking')
const workerSort = ref('ranking')

const taskSortOptions = [
  { value: 'ranking', label: '综合排序' },
  { value: 'newest', label: '最新发布' },
  { value: 'deadline_asc', label: '截止时间最近' },
  { value: 'publisher_rating', label: '发布人评分最高' },
  { value: 'publisher_completed', label: '发布人完成数最多' },
  { value: 'price_desc', label: '价格最高' },
]

const workerSortOptions = [
  { value: 'ranking', label: '综合排序' },
  { value: 'worker_rating', label: '评分最高' },
  { value: 'worker_completed', label: '完成任务最多' },
]

const searchQuery = ref('')
const workerSearchQuery = ref('')
const selectedCategory = ref<number | null>(null)
const selectedWorkerCategory = ref<number | null>(null)
const totalWorkerCount = ref(0)

const loading = ref(false)
const categories = ref<Category[]>([])
const allTasks = ref<Task[]>([])
const selectedTask = ref<Task | null>(null)
const myPublished = ref<Task[]>([])
const myAccepted = ref<Task[]>([])
const allWorkers = ref<WorkerProfile[]>([])
const selectedWorker = ref<WorkerProfile | null>(null)
const workerHistoryReviews = ref<UserReview[]>([])
const workerContactReveal = ref<WorkerContactReveal | null>(null)
const workerContactLoading = ref(false)
const taskMessages = ref<TaskMessage[]>([])
const taskReviews = ref<TaskReview[]>([])
const publisherHistoryReviews = ref<UserReview[]>([])
const showReviewForm = ref(false)
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

const chatContent = ref('')
const reviewForm = ref({
  stars: 5,
  comment: '',
})
const reportForm = ref({
  reason: '',
  evidence: '',
})

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

const myReviewTargetRole = computed<'worker' | 'publisher' | null>(() => {
  if (!me.value || !selectedTask.value) return null
  if (selectedTask.value.publisher_id === me.value.id) return 'worker'
  if (selectedTask.value.assignee_id === me.value.id) return 'publisher'
  return null
})

const hasAlreadyReviewed = computed(() => {
  if (!me.value) return false
  return taskReviews.value.some((r) => r.reviewer_id === me.value!.id)
})

const bothSidesReviewed = computed(() => {
  if (!isParticipant.value) return true
  const roles = new Set(taskReviews.value.map((r) => r.target_role))
  return roles.has('publisher') && roles.has('worker')
})

const waitingForOtherReview = computed(() => hasAlreadyReviewed.value && !bothSidesReviewed.value)

const canReview = computed(() => selectedTask.value?.status === 'completed' && isParticipant.value && !hasAlreadyReviewed.value)

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

function categoryName(id: number | null) {
  if (!id) return null
  return categories.value.find((c) => c.id === id)?.name ?? null
}

const totalTaskCount = computed(() => categories.value.reduce((sum, c) => sum + c.task_count, 0))

const tasks = computed(() => {
  let result = [...allTasks.value]

  if (searchQuery.value.trim()) {
    const kw = searchQuery.value.trim().toLowerCase()
    result = result.filter(t =>
      t.title.toLowerCase().includes(kw) ||
      t.description.toLowerCase().includes(kw) ||
      (t.location && t.location.toLowerCase().includes(kw))
    )
  }

  if (selectedCategory.value !== null) {
    result = result.filter(t => t.category_id === selectedCategory.value)
  }

  if (taskSort.value === 'newest') {
    result.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
  } else if (taskSort.value === 'deadline_asc') {
    result.sort((a, b) => {
      if (!a.deadline && !b.deadline) return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      if (!a.deadline) return 1
      if (!b.deadline) return -1
      return new Date(a.deadline).getTime() - new Date(b.deadline).getTime()
    })
  } else if (taskSort.value === 'publisher_rating') {
    result.sort((a, b) =>
      b.publisher_rating_avg - a.publisher_rating_avg ||
      b.publisher_rating_count - a.publisher_rating_count ||
      new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    )
  } else if (taskSort.value === 'publisher_completed') {
    result.sort((a, b) =>
      (b.publisher_completed_count ?? 0) - (a.publisher_completed_count ?? 0) ||
      new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    )
  } else if (taskSort.value === 'price_desc') {
    result.sort((a, b) =>
      b.price - a.price ||
      new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    )
  }

  return result
})

const workers = computed(() => {
  let result = [...allWorkers.value]

  if (workerSearchQuery.value.trim()) {
    const kw = workerSearchQuery.value.trim().toLowerCase()
    result = result.filter(w =>
      w.display_name.toLowerCase().includes(kw) ||
      (w.bio && w.bio.toLowerCase().includes(kw)) ||
      w.skill_tags.some(t => t.name.toLowerCase().includes(kw))
    )
  }

  if (selectedWorkerCategory.value !== null) {
    const catId = selectedWorkerCategory.value
    result = result.filter(w => w.skill_tags.some(t => t.id === catId))
  }

  if (workerSort.value === 'worker_rating') {
    result.sort((a, b) =>
      b.overall_rating_avg - a.overall_rating_avg ||
      b.overall_rating_count - a.overall_rating_count ||
      b.worker_completed_count - a.worker_completed_count
    )
  } else if (workerSort.value === 'worker_completed') {
    result.sort((a, b) =>
      b.worker_completed_count - a.worker_completed_count ||
      b.overall_rating_avg - a.overall_rating_avg ||
      b.overall_rating_count - a.overall_rating_count
    )
  }

  return result
})

async function bootstrap() {
  loading.value = true
  try {
    const publicLoads = [loadCategories(), loadTasks(), loadWorkers()]
    if (auth.isAuthenticated) {
      publicLoads.push(loadMyTasks())
    }
    await Promise.all(publicLoads)
  } catch (error: any) {
    showToast(extractError(error, '加载失败'), 'error')
  } finally {
    loading.value = false
  }
  const taskId = router.currentRoute.value.query.task
  if (taskId) {
    const id = Number(taskId)
    const task = [...allTasks.value, ...myPublished.value, ...myAccepted.value].find(t => t.id === id)
    if (task) openDrawer(task)
    router.replace({ query: {} })
  }
}

async function loadCategories() {
  categories.value = await fetchCategories()
}

async function loadTasks() {
  allTasks.value = await fetchTasks({ status: 'open' })
}

async function loadWorkers() {
  allWorkers.value = await fetchWorkers({})
  totalWorkerCount.value = allWorkers.value.length
}

async function loadMyTasks() {
  const [published, accepted] = await Promise.all([fetchPublishedTasks(), fetchAcceptedTasks()])
  myPublished.value = published
  myAccepted.value = accepted
}

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
      title: '',
      description: '',
      deadline: '',
      location: '',
      price: 20,
      category_id: null,
      contact_visibility: 'after_accept',
      contact_info: '',
      required_gender: null,
      icon: 'Hexagon',
    }
    showPostModal.value = false
    await Promise.all([loadTasks(), loadMyTasks(), loadCategories()])
  } catch (error: any) {
    showToast(extractError(error, '发布失败'), 'error')
  }
}

async function openWorkerDrawer(worker: WorkerProfile) {
  workerContactReveal.value = null
  workerContactLoading.value = false
  try {
    const [detail, reviews] = await Promise.all([fetchWorkerDetail(worker.user_id), fetchUserReviews(worker.user_id, 'worker')])
    selectedWorker.value = detail
    workerHistoryReviews.value = reviews
  } catch (error: any) {
    showToast(extractError(error, '加载接单者详情失败'), 'error')
  }
}

function closeWorkerDrawer() {
  selectedWorker.value = null
  workerHistoryReviews.value = []
  workerContactReveal.value = null
  workerContactLoading.value = false
}

async function handleWorkerContactAction(action: 'view_contact' | 'internal_contact') {
  if (!selectedWorker.value) return

  if (action === 'internal_contact') {
    if (!auth.isAuthenticated) {
      showToast('请先登录后再使用站内联系', 'info')
      router.push('/login')
      return
    }
    closeWorkerDrawer()
    activeTab.value = 'hall'
    newTask.value.contact_visibility = 'internal_only'
    showPostModal.value = true
    showToast('已打开发布任务，任务被接取后即可站内沟通', 'info')
    return
  }

  if (!auth.isAuthenticated) {
    showToast('请先登录后再查看联系方式', 'info')
    router.push('/login')
    return
  }

  workerContactLoading.value = true
  try {
    const reveal = await revealWorkerContact(selectedWorker.value.user_id)
    workerContactReveal.value = reveal
    if (!reveal.phone && !reveal.wechat) {
      showToast('该接单者暂未填写手机号或微信号', 'info')
    } else {
      showToast('联系方式已展示', 'success')
    }
  } catch (error: any) {
    showToast(extractError(error, '查看联系方式失败'), 'error')
  } finally {
    workerContactLoading.value = false
  }
}

async function handleAcceptTask() {
  if (!selectedTask.value) return
  try {
    selectedTask.value = await acceptTask(selectedTask.value.id)
    showToast('已接取该委托', 'success')
    await Promise.all([loadTasks(), loadMyTasks(), loadCategories(), refreshTaskMeta()])
  } catch (error: any) {
    showToast(extractError(error, '接取失败'), 'error')
  }
}

async function handleConfirmTask() {
  if (!selectedTask.value) return
  try {
    selectedTask.value = await confirmTask(selectedTask.value.id)
    showToast('已确认完成', 'success')
    await Promise.all([loadTasks(), loadMyTasks(), loadCategories(), refreshTaskMeta()])
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
    await Promise.all([loadTasks(), loadMyTasks(), loadCategories()])
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
    await Promise.all([loadTasks(), loadMyTasks(), loadCategories()])
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
  return me.value.id === selectedTask.value.publisher_id ? selectedTask.value.assignee_id : selectedTask.value.publisher_id
})

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

onMounted(() => {
  bootstrap()
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
      :task-sort-options="taskSortOptions"
      :categories="categories"
      :total-task-count="totalTaskCount"
      :tasks="tasks"
      :status-of="statusOf"
      :gender-label="genderLabel"
      :category-name="categoryName"
      :is-expired="isExpired"
      :format-short="formatShort"
      @open-task="openDrawer"
    />

    <HomeWorkersSection
      v-if="activeTab === 'workers'"
      v-model:worker-sort="workerSort"
      v-model:selected-category="selectedWorkerCategory"
      v-model:search-query="workerSearchQuery"
      :workers="workers"
      :worker-sort-options="workerSortOptions"
      :categories="categories"
      :total-worker-count="totalWorkerCount"
      @open-worker="openWorkerDrawer"
    />
  </main>

  <button
    v-if="auth.isAuthenticated && activeTab === 'hall' && !showPostModal && !selectedTask"
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

  <HomeMyTasksDrawer
    v-model="showMyPanel"
    :my-published="myPublished"
    :my-accepted="myAccepted"
    :status-of="statusOf"
    :is-expired="isExpired"
    @open-task="openDrawer"
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

  <HomeWorkerDetailDrawer
    :worker="selectedWorker"
    :reviews="workerHistoryReviews"
    :contact-reveal="workerContactReveal"
    :is-authenticated="auth.isAuthenticated"
    :reveal-loading="workerContactLoading"
    :format-full="formatFull"
    @close="closeWorkerDrawer"
    @login="router.push('/login')"
    @contact-action="handleWorkerContactAction"
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
