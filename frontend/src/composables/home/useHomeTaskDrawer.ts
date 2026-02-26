import { computed, ref, watch, type ComputedRef } from 'vue'
import { appConfirm } from '../../components/AppConfirm.vue'
import { fetchAgentAvailability, startTaskAgent } from '../../api/agent'
import { blockUser } from '../../api/moderation'
import {
  abandonTask,
  acceptTask,
  cancelTask,
  confirmTask,
  createReview,
  createTask,
  deleteTask,
  fetchMessages,
  fetchReviews,
  sendMessage,
  updateTask,
} from '../../api/tasks'
import { fetchUserReviews } from '../../api/users'
import type { AgentAvailability, Category, Task, TaskMessage, TaskReview, UserMe, UserReview } from '../../types/api'
import type { AppToastNotifier } from '../useAppToast'
import { CaptchaCancelledError, type CaptchaScene, withCaptchaRetry } from '../../utils/captcha'
import { extractError } from '../../utils/error'
import { localToUTC, utcToLocal } from '../../utils/time'
import { createReviewForm, createTaskEditorForm } from './model'

interface UseHomeTaskDrawerOptions {
  me: ComputedRef<UserMe | null>
  isAuthenticated: ComputedRef<boolean>
  categories: ComputedRef<Category[]>
  showToast: AppToastNotifier
  pollNotificationCount: () => void
  dismissTaskChatNotification: (taskId: number) => Promise<unknown>
  loadTasks: () => Promise<void>
  loadMyTasks: () => Promise<void>
  loadCategories: () => Promise<void>
  loadWorkers: () => Promise<void>
  goToAgentSession: (sessionId: string) => void
  requestCaptcha: (scene: CaptchaScene) => Promise<string | null>
}

export function useHomeTaskDrawer(options: UseHomeTaskDrawerOptions) {
  const showPostModal = ref(false)
  const showEditModal = ref(false)
  const editingTask = ref<Task | null>(null)

  const selectedTask = ref<Task | null>(null)
  const taskMessages = ref<TaskMessage[]>([])
  const taskReviews = ref<TaskReview[]>([])
  const publisherHistoryReviews = ref<UserReview[]>([])
  const showReviewForm = ref(false)
  const newTask = ref(createTaskEditorForm())
  const editTaskForm = ref(createTaskEditorForm())
  const chatContent = ref('')
  const reviewForm = ref(createReviewForm())
  const showReportModal = ref(false)
  const agentAvailability = ref<AgentAvailability | null>(null)
  const createWithAgentSubmitting = ref(false)
  const startingAgent = ref(false)

  const isParticipant = computed(() => {
    if (!options.me.value || !selectedTask.value) return false
    return (
      selectedTask.value.publisher_id === options.me.value.id ||
      selectedTask.value.assignee_id === options.me.value.id
    )
  })

  const isPublisher = computed(() => {
    if (!options.me.value || !selectedTask.value) return false
    return selectedTask.value.publisher_id === options.me.value.id
  })

  const canAccept = computed(() => {
    if (!selectedTask.value || !options.me.value) return false
    if (
      selectedTask.value.status !== 'open' ||
      selectedTask.value.publisher_id === options.me.value.id
    ) {
      return false
    }
    if (
      selectedTask.value.required_gender &&
      selectedTask.value.required_gender !== options.me.value.gender
    ) {
      return false
    }
    return true
  })

  const genderMismatch = computed(() => {
    if (!selectedTask.value || !options.me.value) return false
    if (
      selectedTask.value.status !== 'open' ||
      selectedTask.value.publisher_id === options.me.value.id
    ) {
      return false
    }
    return (
      !!selectedTask.value.required_gender &&
      selectedTask.value.required_gender !== options.me.value.gender
    )
  })

  const canConfirm = computed(() => {
    if (!selectedTask.value || !options.me.value) return false
    return (
      selectedTask.value.status === 'in_progress' &&
      selectedTask.value.publisher_id === options.me.value.id
    )
  })

  const canAbandon = computed(() => {
    if (!selectedTask.value || !options.me.value) return false
    return (
      selectedTask.value.status === 'in_progress' &&
      selectedTask.value.assignee_id === options.me.value.id
    )
  })

  const canCancelTask = computed(() => {
    if (!selectedTask.value || !options.me.value) return false
    return (
      (selectedTask.value.status === 'in_progress' ||
        selectedTask.value.status === 'under_review') &&
      selectedTask.value.publisher_id === options.me.value.id
    )
  })

  const myReviewTargetRole = computed<'worker' | 'publisher' | null>(() => {
    if (!options.me.value || !selectedTask.value) return null
    if (selectedTask.value.publisher_id === options.me.value.id) return 'worker'
    if (selectedTask.value.assignee_id === options.me.value.id) return 'publisher'
    return null
  })

  const hasAlreadyReviewed = computed(() => {
    if (!options.me.value) return false
    return taskReviews.value.some((review) => review.reviewer_id === options.me.value!.id)
  })

  const bothSidesReviewed = computed(() => {
    if (!isParticipant.value) return true
    const roles = new Set(taskReviews.value.map((review) => review.target_role))
    return roles.has('publisher') && roles.has('worker')
  })

  const waitingForOtherReview = computed(
    () => hasAlreadyReviewed.value && !bothSidesReviewed.value,
  )

  const canReview = computed(
    () =>
      selectedTask.value?.status === 'completed' &&
      isParticipant.value &&
      !hasAlreadyReviewed.value,
  )

  const canDeleteTask = computed(() => {
    if (!isPublisher.value || !selectedTask.value) return false
    return selectedTask.value.status === 'open' || selectedTask.value.status === 'canceled'
  })

  const canRepublish = computed(() => {
    if (!isPublisher.value || !selectedTask.value) return false
    return selectedTask.value.status === 'canceled'
  })

  const canEditTask = computed(() => {
    if (!isPublisher.value || !selectedTask.value) return false
    return selectedTask.value.status === 'open'
  })

  const deleteBlockedByAssignee = computed(() => {
    if (!isPublisher.value || !selectedTask.value) return false
    return selectedTask.value.status === 'in_progress'
  })

  const canReport = computed(() => {
    if (!options.me.value || !selectedTask.value) return false
    return isParticipant.value && !!selectedTask.value.assignee_id
  })

  const reportTargetId = computed(() => {
    if (!options.me.value || !selectedTask.value) return null
    return options.me.value.id === selectedTask.value.publisher_id
      ? selectedTask.value.assignee_id
      : selectedTask.value.publisher_id
  })

  const selectedCategorySupportsAgent = computed(() => {
    if (!newTask.value.category_id) return false
    return options.categories.value.some(
      (category) => category.id === newTask.value.category_id && category.ai_agent_enabled,
    )
  })

  const canCreateWithAgent = computed(() => {
    if (!options.isAuthenticated.value) return false
    if (!agentAvailability.value?.agent_enabled) return false
    if ((agentAvailability.value.remaining_count ?? 0) <= 0) return false
    return selectedCategorySupportsAgent.value
  })

  const selectedTaskCategorySupportsAgent = computed(() => {
    if (!selectedTask.value?.category_id) return false
    return options.categories.value.some(
      (category) => category.id === selectedTask.value!.category_id && category.ai_agent_enabled,
    )
  })

  const canUseAgentOnSelectedTask = computed(() => {
    if (!isPublisher.value || !selectedTask.value) return false
    if (!selectedTaskCategorySupportsAgent.value) return false
    if (!agentAvailability.value?.agent_enabled) return false
    const likelyExistingSession = selectedTask.value.status === 'in_progress' && !selectedTask.value.assignee_id
    if (likelyExistingSession) return true
    return selectedTask.value.status === 'open' && (agentAvailability.value.remaining_count ?? 0) > 0
  })

  async function refreshTaskBoardData() {
    await Promise.all([options.loadTasks(), options.loadMyTasks(), options.loadCategories()])
  }

  async function refreshAgentAvailability() {
    if (!options.isAuthenticated.value) {
      agentAvailability.value = null
      return
    }
    try {
      agentAvailability.value = await fetchAgentAvailability()
    } catch {
      agentAvailability.value = null
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
      if (options.isAuthenticated.value) {
        options.dismissTaskChatNotification(taskId).catch(() => {})
      }
    } catch {
      taskMessages.value = []
      taskReviews.value = await fetchReviews(taskId).catch(() => [])
    }
  }

  async function refreshPublisherReviews() {
    if (!selectedTask.value) return
    try {
      publisherHistoryReviews.value = await fetchUserReviews(
        selectedTask.value.publisher_id,
        'publisher',
      )
    } catch {
      publisherHistoryReviews.value = []
    }
  }

  async function submitCreateTask(mode: 'normal' | 'agent' = 'normal') {
    if (!newTask.value.category_id) {
      options.showToast('请选择所属类目', 'error')
      return
    }
    if (mode === 'agent' && !canCreateWithAgent.value) {
      options.showToast('当前任务不满足 AI 代理开启条件', 'error')
      return
    }
    if (mode === 'agent') {
      createWithAgentSubmitting.value = true
    }
    try {
      const createdTask = await withCaptchaRetry(
        (captchaToken) =>
          createTask({
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
            captcha_token: captchaToken ?? null,
          }),
        options.requestCaptcha,
      )
      if (republishSourceId.value) {
        await deleteTask(republishSourceId.value).catch(() => {})
        republishSourceId.value = null
      }
      options.showToast(mode === 'agent' ? '委托已发布，正在启动 AI 代理' : '委托发布成功', 'success')

      let startedSessionId: string | null = null
      if (mode === 'agent') {
        try {
          const started = await startTaskAgent(createdTask.id)
          startedSessionId = started.session_id
          await refreshAgentAvailability()
        } catch (error) {
          options.showToast(extractError(error, '委托已发布，但启动 AI 代理失败'), 'error')
        }
      }

      newTask.value = createTaskEditorForm()
      showPostModal.value = false
      await refreshTaskBoardData()
      options.pollNotificationCount()
      if (startedSessionId) {
        options.goToAgentSession(startedSessionId)
      }
    } catch (error) {
      if (error instanceof CaptchaCancelledError) return
      options.showToast(extractError(error, '发布失败'), 'error')
    } finally {
      createWithAgentSubmitting.value = false
    }
  }

  async function handleAcceptTask() {
    if (!selectedTask.value) return
    const taskId = selectedTask.value.id
    try {
      selectedTask.value = await withCaptchaRetry(
        (captchaToken) => acceptTask(taskId, captchaToken),
        options.requestCaptcha,
      )
      options.showToast('已接取该委托', 'success')
      await Promise.all([refreshTaskBoardData(), refreshTaskMeta()])
      options.pollNotificationCount()
    } catch (error) {
      if (error instanceof CaptchaCancelledError) return
      options.showToast(extractError(error, '接取失败'), 'error')
    }
  }

  async function handleConfirmTask() {
    if (!selectedTask.value) return
    try {
      selectedTask.value = await confirmTask(selectedTask.value.id)
      options.showToast('已确认完成', 'success')
      await Promise.all([refreshTaskBoardData(), refreshTaskMeta()])
      options.pollNotificationCount()
    } catch (error) {
      options.showToast(extractError(error, '确认失败'), 'error')
    }
  }

  async function handleAbandonTask() {
    if (!selectedTask.value) return
    const yes = await appConfirm({
      title: '确认放弃接取',
      message:
        '放弃后任务将重新开放，24小时内累计放弃5次将无法继续接取任务。是否确认放弃？',
      confirmText: '放弃接取',
      type: 'danger',
    })
    if (!yes) return
    try {
      selectedTask.value = await abandonTask(selectedTask.value.id)
      options.showToast('已放弃接取该委托', 'success')
      await Promise.all([refreshTaskBoardData(), refreshTaskMeta()])
      options.pollNotificationCount()
    } catch (error) {
      options.showToast(extractError(error, '放弃失败'), 'error')
    }
  }

  async function handleCancelTask() {
    if (!selectedTask.value) return
    const yes = await appConfirm({
      title: '确认取消任务',
      message:
        '取消后任务将结束并通知接单者。24小时内累计取消5次将暂时无法发布新任务。是否确认取消？',
      confirmText: '取消任务',
      type: 'danger',
    })
    if (!yes) return
    try {
      selectedTask.value = await cancelTask(selectedTask.value.id)
      options.showToast('任务已取消', 'success')
      await Promise.all([refreshTaskBoardData(), refreshTaskMeta()])
      options.pollNotificationCount()
    } catch (error) {
      options.showToast(extractError(error, '取消失败'), 'error')
    }
  }

  const republishSourceId = ref<number | null>(null)

  watch(
    () => options.isAuthenticated.value,
    () => {
      refreshAgentAvailability().catch(() => {})
    },
    { immediate: true },
  )

  watch(showPostModal, (open) => {
    if (!open) {
      republishSourceId.value = null
      return
    }
    refreshAgentAvailability().catch(() => {})
  })

  function handleRepublishTask() {
    if (!selectedTask.value) return
    const task = selectedTask.value
    republishSourceId.value = task.id
    newTask.value = {
      title: task.title,
      description: task.description,
      deadline: '',
      location: task.location || '',
      price: task.price,
      category_id: task.category_id,
      contact_visibility: task.contact_visibility,
      contact_info: task.contact_info || '',
      required_gender: task.required_gender,
      icon: task.icon || 'Hexagon',
    }
    closeDrawer()
    showPostModal.value = true
  }

  async function handleStartAgentFromSelectedTask() {
    if (!selectedTask.value) return
    startingAgent.value = true
    try {
      const started = await startTaskAgent(selectedTask.value.id)
      await refreshAgentAvailability()
      await refreshTaskBoardData()
      closeDrawer()
      options.goToAgentSession(started.session_id)
    } catch (error) {
      options.showToast(extractError(error, '启动 AI 代理失败'), 'error')
    } finally {
      startingAgent.value = false
    }
  }

  async function submitMessage() {
    if (!selectedTask.value || !chatContent.value.trim()) return
    try {
      await sendMessage(selectedTask.value.id, chatContent.value.trim())
      chatContent.value = ''
      await refreshTaskMeta()
    } catch (error) {
      options.showToast(extractError(error, '发送失败'), 'error')
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
      options.showToast('评价已提交', 'success')
    } catch (error) {
      options.showToast(extractError(error, '评价失败'), 'error')
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
      options.showToast('任务已删除', 'success')
      await refreshTaskBoardData()
      options.pollNotificationCount()
    } catch (error) {
      options.showToast(extractError(error, '删除失败'), 'error')
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
    if (!editTaskForm.value.category_id) {
      options.showToast('请选择所属类目', 'error')
      return
    }
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
      options.showToast('委托信息已更新', 'success')
      await refreshTaskBoardData()
      options.pollNotificationCount()
      openDrawer(updated)
    } catch (error) {
      options.showToast(extractError(error, '修改失败'), 'error')
    }
  }

  function openReportModal() {
    showReportModal.value = true
  }

  async function handleBlockTaskUser(userId: number) {
    const yes = await appConfirm({
      title: '确认拉黑',
      message: '拉黑后双方将无法看到对方的任务和接单信息。确认拉黑？',
      confirmText: '拉黑',
      type: 'danger',
    })
    if (!yes) return
    try {
      await blockUser({ blocked_user_id: userId })
      closeDrawer()
      options.showToast('已拉黑该用户', 'success')
      await Promise.all([options.loadTasks(), options.loadWorkers()])
    } catch (error) {
      options.showToast(extractError(error, '拉黑失败'), 'error')
    }
  }

  return {
    showPostModal,
    showEditModal,
    editingTask,
    selectedTask,
    taskMessages,
    taskReviews,
    publisherHistoryReviews,
    showReviewForm,
    newTask,
    editTaskForm,
    chatContent,
    reviewForm,
    showReportModal,
    agentAvailability,
    createWithAgentSubmitting,
    startingAgent,
    isParticipant,
    isPublisher,
    canAccept,
    genderMismatch,
    canConfirm,
    canAbandon,
    canCancelTask,
    myReviewTargetRole,
    hasAlreadyReviewed,
    bothSidesReviewed,
    waitingForOtherReview,
    canReview,
    canDeleteTask,
    canRepublish,
    canEditTask,
    canCreateWithAgent,
    canUseAgentOnSelectedTask,
    deleteBlockedByAssignee,
    canReport,
    reportTargetId,
    openDrawer,
    closeDrawer,
    refreshAgentAvailability,
    refreshTaskMeta,
    refreshPublisherReviews,
    submitCreateTask,
    handleAcceptTask,
    handleConfirmTask,
    handleAbandonTask,
    handleCancelTask,
    handleRepublishTask,
    handleStartAgentFromSelectedTask,
    submitMessage,
    submitReview,
    handleDeleteTask,
    openEditModal,
    submitEditTask,
    openReportModal,
    handleBlockTaskUser,
  }
}
