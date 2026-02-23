import {
  computed,
  onMounted,
  onUnmounted,
  ref,
  watch,
  type ComponentPublicInstance,
} from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useAuthStore } from '../../stores/auth'
import { appConfirm } from '../../components/AppConfirm.vue'
import {
  abandonTask,
  acceptTask,
  confirmTask,
  createTask,
  deleteTask,
  updateTask,
  fetchAcceptedTasks,
  fetchCategories,
  fetchPublishedTasks,
  fetchMessages,
  fetchReviews,
  sendMessage,
  createReview,
} from '../../api/tasks'
import { fetchUserReviews } from '../../api/users'
import type {
  Category,
  Task,
  TaskMessage,
  TaskReview,
  UserReview,
} from '../../types/api'
import {
  formatFull,
  formatShort,
  isExpired,
  localToUTC,
  nowLocal,
  parseUTC,
  utcToLocal,
} from '../../utils/time'
import { extractError } from '../../utils/error'
import { useAppToast } from '../useAppToast'

export type TaskManagementView = 'dashboard' | 'stats'
export type TaskManagementRole = 'assignee' | 'publisher'
export type TaskManagementStatus = 'pending' | 'progress' | 'completed'

export type TaskEditorForm = {
  title: string
  description: string
  deadline: string
  location: string
  price: number
  category_id: number | null
  contact_visibility: 'after_accept' | 'internal_only'
  contact_info: string
  required_gender: 'male' | 'female' | null
  icon: string
}

export type MyTask = Task & { myRole: 'publisher' | 'assignee' }
export type TaskTimelineItem = MyTask & { _animIdx: number }

export interface TaskTimelineGroup {
  dateKey: string
  dateNum: string
  month: string
  showMonth: boolean
  weekday: string
  isToday: boolean
  tasks: TaskTimelineItem[]
}

function createEditorForm(): TaskEditorForm {
  return {
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
}

function effectiveDate(task: Task): number {
  return parseUTC(task.deadline || task.created_at).getTime()
}

const byDateDesc = (a: Task, b: Task) => effectiveDate(b) - effectiveDate(a)
const weekdayNames = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六']

function toDateKey(ts: number): string {
  const d = new Date(ts)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function toHTMLElement(el: Element | ComponentPublicInstance | null): HTMLElement | null {
  if (!el) return null
  if (el instanceof HTMLElement) return el
  const maybeEl = el.$el
  return maybeEl instanceof HTMLElement ? maybeEl : null
}

export function useTaskManagement() {
  const router = useRouter()
  const route = useRoute()
  const auth = useAuthStore()
  const appTitle = import.meta.env.VITE_APP_TITLE || '校园任务平台'

  const activeView = ref<TaskManagementView>('dashboard')
  const activeRole = ref<TaskManagementRole>('assignee')
  const activeStatus = ref<TaskManagementStatus>('progress')

  const loading = ref(false)
  const myPublished = ref<Task[]>([])
  const myAccepted = ref<Task[]>([])
  const categories = ref<Category[]>([])

  const showCreateModal = ref(false)
  const showEditModal = ref(false)
  const editingTask = ref<Task | null>(null)

  const { toast, showToast, clearToast } = useAppToast()

  const newTask = ref<TaskEditorForm>(createEditorForm())
  const editTaskForm = ref<TaskEditorForm>(createEditorForm())

  const selectedTask = ref<Task | null>(null)
  const taskMessages = ref<TaskMessage[]>([])
  const taskReviews = ref<TaskReview[]>([])
  const publisherHistoryReviews = ref<UserReview[]>([])

  const chatContent = ref('')
  const showReviewForm = ref(false)
  const reviewForm = ref({ stars: 5, comment: '' })
  const showReportModal = ref(false)

  const assigneeTotal = computed(() => myAccepted.value.length)
  const publisherTotal = computed(() => myPublished.value.length)

  const assigneeProgress = computed(() =>
    myAccepted.value.filter((t) => t.status === 'open' || t.status === 'in_progress' || t.status === 'under_review').length,
  )
  const publisherPending = computed(() =>
    myPublished.value.filter((t) => t.status === 'open').length,
  )

  watch(activeRole, (role) => {
    if (role === 'assignee' && activeStatus.value === 'pending') {
      activeStatus.value = 'progress'
    }
  })

  const currentTasks = computed<MyTask[]>(() => {
    const base =
      activeRole.value === 'assignee'
        ? myAccepted.value.map((task) => ({ ...task, myRole: 'assignee' as const }))
        : myPublished.value.map((task) => ({ ...task, myRole: 'publisher' as const }))

    return base
      .filter((task) => {
        if (activeStatus.value === 'pending') return task.status === 'open'
        if (activeStatus.value === 'progress') {
          return activeRole.value === 'assignee'
            ? task.status === 'open' || task.status === 'in_progress' || task.status === 'under_review'
            : task.status === 'in_progress' || task.status === 'under_review'
        }
        return task.status === 'completed' || task.status === 'canceled'
      })
      .sort(byDateDesc)
  })

  const emptyText = computed(() => {
    if (activeRole.value === 'assignee') {
      return activeStatus.value === 'progress'
        ? '还没有进行中的委托，去任务大厅接取任务吧'
        : '还没有完成过的委托'
    }
    if (activeStatus.value === 'pending') return '暂无等待接单的任务'
    if (activeStatus.value === 'progress') return '暂无正在进行中的任务'
    return '没有已结束的发布任务'
  })

  const PAGE_SIZE = 8
  const displayCount = ref(PAGE_SIZE)
  const loadingMore = ref(false)
  const sentinelRef = ref<HTMLElement | null>(null)
  let scrollObserver: IntersectionObserver | null = null

  const displayedTasks = computed(() => currentTasks.value.slice(0, displayCount.value))
  const hasMore = computed(() => displayCount.value < currentTasks.value.length)

  const taskGroups = computed<TaskTimelineGroup[]>(() => {
    const map = new Map<string, MyTask[]>()
    for (const task of displayedTasks.value) {
      const key = toDateKey(effectiveDate(task))
      if (!map.has(key)) map.set(key, [])
      map.get(key)!.push(task)
    }

    const now = new Date()
    const todayKey = toDateKey(now.getTime())
    const groups = Array.from(map.entries()).sort(([a], [b]) => (a > b ? -1 : a < b ? 1 : 0))

    let animIndex = 0
    return groups.map(([key, tasks], idx) => {
      const date = new Date(`${key}T00:00:00`)
      const month = date.getMonth() + 1
      const prevMonth = idx > 0 ? new Date(`${groups[idx - 1][0]}T00:00:00`).getMonth() + 1 : -1
      return {
        dateKey: key,
        dateNum: String(date.getDate()).padStart(2, '0'),
        month: `${month}月`,
        showMonth: idx === 0 || month !== prevMonth,
        weekday: weekdayNames[date.getDay()],
        isToday: key === todayKey,
        tasks: tasks.map((task) => ({ ...task, _animIdx: animIndex++ })),
      }
    })
  })

  function loadMore() {
    if (loadingMore.value || !hasMore.value) return
    loadingMore.value = true
    setTimeout(() => {
      displayCount.value += PAGE_SIZE
      loadingMore.value = false
    }, 300)
  }

  watch([activeRole, activeStatus], () => {
    displayCount.value = PAGE_SIZE
  })

  const statusMap: Record<string, { label: string; cls: string }> = {
    open: { label: '待接取', cls: 'badge-blue' },
    in_progress: { label: '进行中', cls: 'badge-amber' },
    completed: { label: '已完成', cls: 'badge-green' },
    canceled: { label: '已取消', cls: 'badge-default' },
    under_review: { label: '进行中', cls: 'badge-amber' },
  }

  function statusOf(status: string) {
    return statusMap[status] || { label: status, cls: 'badge-default' }
  }

  const genderMap: Record<string, { label: string; icon: string; cls: string }> = {
    male: { label: '限男生', icon: 'fa-solid fa-mars', cls: 'badge-blue' },
    female: { label: '限女生', icon: 'fa-solid fa-venus', cls: 'badge-pink' },
  }

  function genderLabel(gender: string | null) {
    return gender ? genderMap[gender] : null
  }

  const me = computed(() => auth.user)
  const isAuthenticated = computed(() => auth.isAuthenticated)
  const displayName = computed(() => auth.displayName)

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
    return (selectedTask.value.status === 'in_progress' || selectedTask.value.status === 'under_review') && selectedTask.value.publisher_id === me.value.id
  })

  const canAbandon = computed(() => {
    if (!selectedTask.value || !me.value) return false
    return (selectedTask.value.status === 'in_progress' || selectedTask.value.status === 'under_review') && selectedTask.value.assignee_id === me.value.id
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
    return taskReviews.value.some((review) => review.reviewer_id === me.value!.id)
  })

  const bothSidesReviewed = computed(() => {
    if (!isParticipant.value) return true
    const roles = new Set(taskReviews.value.map((review) => review.target_role))
    return roles.has('publisher') && roles.has('worker')
  })

  const waitingForOtherReview = computed(() => hasAlreadyReviewed.value && !bothSidesReviewed.value)
  const canReview = computed(
    () => selectedTask.value?.status === 'completed' && isParticipant.value && !hasAlreadyReviewed.value,
  )

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

  async function loadMyTasks() {
    const [published, accepted] = await Promise.all([fetchPublishedTasks(), fetchAcceptedTasks()])
    myPublished.value = published
    myAccepted.value = accepted
  }

  async function loadCategories() {
    categories.value = await fetchCategories()
  }

  function goLogin() {
    router.push('/login')
  }

  function openSettings() {
    router.push('/settings')
  }

  function handleHeaderTabChange(tab: 'hall' | 'workers' | null) {
    router.push({ path: '/', query: tab === 'workers' ? { tab: 'workers' } : {} })
  }

  function openReports() {
    router.push('/reports')
  }

  function logout() {
    auth.logout()
    router.push('/login')
  }

  async function bootstrap() {
    loading.value = true
    try {
      await Promise.all([loadMyTasks(), loadCategories()])
    } catch (error: unknown) {
      showToast(extractError(error, '加载失败'), 'error')
    } finally {
      loading.value = false
    }
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
      const [messages, reviews] = await Promise.all([fetchMessages(taskId), fetchReviews(taskId)])
      taskMessages.value = messages
      taskReviews.value = reviews
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
    } catch (error: unknown) {
      showToast(extractError(error, '接取失败'), 'error')
    }
  }

  async function handleConfirmTask() {
    if (!selectedTask.value) return
    try {
      selectedTask.value = await confirmTask(selectedTask.value.id)
      showToast('已确认完成', 'success')
      await Promise.all([loadMyTasks(), refreshTaskMeta()])
    } catch (error: unknown) {
      showToast(extractError(error, '确认失败'), 'error')
    }
  }

  async function handleAbandonTask() {
    if (!selectedTask.value) return
    const confirmed = await appConfirm({
      title: '确认放弃接取',
      message: '放弃后任务将重新开放，24小时内累计放弃3次将无法继续接取任务。是否确认放弃？',
      confirmText: '放弃接取',
      type: 'danger',
    })
    if (!confirmed) return
    try {
      selectedTask.value = await abandonTask(selectedTask.value.id)
      showToast('已放弃接取该委托', 'success')
      await Promise.all([loadMyTasks(), refreshTaskMeta()])
    } catch (error: unknown) {
      showToast(extractError(error, '放弃失败'), 'error')
    }
  }

  async function submitMessage() {
    if (!selectedTask.value || !chatContent.value.trim()) return
    try {
      await sendMessage(selectedTask.value.id, chatContent.value.trim())
      chatContent.value = ''
      await refreshTaskMeta()
    } catch (error: unknown) {
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
    } catch (error: unknown) {
      showToast(extractError(error, '评价失败'), 'error')
    }
  }

  async function handleDeleteTask() {
    if (!selectedTask.value) return
    const confirmed = await appConfirm({
      title: '确认删除',
      message: '确认删除该任务？此操作不可撤销。',
      confirmText: '删除',
      type: 'danger',
    })
    if (!confirmed) return

    try {
      await deleteTask(selectedTask.value.id)
      closeDrawer()
      showToast('任务已删除', 'success')
      await loadMyTasks()
    } catch (error: unknown) {
      showToast(extractError(error, '删除失败'), 'error')
    }
  }

  function openEditModal() {
    if (!selectedTask.value) return
    const task = selectedTask.value
    editingTask.value = task

    editTaskForm.value = {
      title: task.title,
      description: task.description,
      deadline: task.deadline ? utcToLocal(task.deadline) : '',
      location: task.location || '',
      price: task.price,
      category_id: task.category_id,
      contact_visibility: task.contact_visibility,
      contact_info: task.contact_info || '',
      required_gender: task.required_gender,
      icon: task.icon || 'Hexagon',
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
        contact_info:
          editTaskForm.value.contact_visibility === 'after_accept'
            ? editTaskForm.value.contact_info || null
            : null,
        required_gender: editTaskForm.value.required_gender,
        icon: editTaskForm.value.icon,
      })
      showEditModal.value = false
      editingTask.value = null
      showToast('委托信息已更新', 'success')
      await loadMyTasks()
      openDrawer(updated)
    } catch (error: unknown) {
      showToast(extractError(error, '修改失败'), 'error')
    }
  }

  function openReportModal() {
    showReportModal.value = true
  }

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
        contact_info:
          newTask.value.contact_visibility === 'after_accept'
            ? newTask.value.contact_info || null
            : null,
        required_gender: newTask.value.required_gender,
        icon: newTask.value.icon,
      })
      showToast('委托发布成功', 'success')
      newTask.value = createEditorForm()
      showCreateModal.value = false
      await loadMyTasks()
    } catch (error: unknown) {
      showToast(extractError(error, '发布失败'), 'error')
    }
  }

  function openTaskDetail(task: MyTask) {
    openDrawer(task)
  }

  function findTaskById(taskId: number): MyTask | undefined {
    const all: MyTask[] = [
      ...myPublished.value.map((t) => ({ ...t, myRole: 'publisher' as const })),
      ...myAccepted.value.map((t) => ({ ...t, myRole: 'assignee' as const })),
    ]
    return all.find((t) => t.id === taskId)
  }

  function consumeTaskQuery() {
    const taskQuery = route.query.task
    if (!taskQuery) return
    const taskId = Number(taskQuery)
    const task = findTaskById(taskId)
    if (task) openDrawer(task)
    const nextQuery = { ...route.query }
    delete nextQuery.task
    router.replace({ query: nextQuery })
  }

  function setSentinelRef(el: Element | ComponentPublicInstance | null) {
    sentinelRef.value = toHTMLElement(el)
  }

  watch(() => route.query.task, (newVal) => {
    if (!newVal || loading.value) return
    consumeTaskQuery()
  })

  onMounted(() => {
    bootstrap().then(() => {
      consumeTaskQuery()
    })
    scrollObserver = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting && hasMore.value) loadMore()
      },
      { rootMargin: '200px' },
    )
  })

  watch(sentinelRef, (el, oldEl) => {
    if (oldEl) scrollObserver?.unobserve(oldEl)
    if (el) scrollObserver?.observe(el)
  })

  onUnmounted(() => {
    scrollObserver?.disconnect()
  })

  return {
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
    showReportModal,
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
    canAbandon,
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
    handleAbandonTask,
    submitMessage,
    submitReview,
    handleDeleteTask,
    openEditModal,
    submitEditTask,
    openReportModal,
    reportTargetId,
    showToast,
    openCreateTask,
    submitCreateTask,
    closeDrawer,
    openTaskDetail,
    setSentinelRef,
    formatShort,
    formatFull,
    isExpired,
    nowLocal,
  }
}

export type TaskManagementModel = ReturnType<typeof useTaskManagement>
