import { computed, ref, watch } from 'vue'

import { fetchAdminTasks, operateAdminTask } from '../../api/moderation'
import type { AdminTaskItem } from '../../types/api'
import { extractError } from '../../utils/error'
import type { AppToastNotifier } from '../useAppToast'

const PAGE_SIZE = 40

export function useAdminTasks(showToast: AppToastNotifier) {
  const loading = ref(false)
  const taskSearch = ref('')
  const statusFilter = ref<string>('all')
  const flagFilter = ref<string>('all')
  const page = ref(1)
  const total = ref(0)
  const tasks = ref<AdminTaskItem[]>([])
  const operatingIds = ref<Set<number>>(new Set())

  const totalPages = computed(() => Math.max(1, Math.ceil(total.value / PAGE_SIZE)))

  async function loadTasks() {
    loading.value = true
    try {
      const isOverdue = statusFilter.value === 'overdue'
      const isDeleted = statusFilter.value === 'deleted'
      const data = await fetchAdminTasks({
        q: taskSearch.value.trim() || undefined,
        status: !isOverdue && !isDeleted && statusFilter.value !== 'all' ? statusFilter.value : undefined,
        flag: flagFilter.value !== 'all' ? (flagFilter.value as 'pinned' | 'urgent' | 'flagged') : undefined,
        deleted: isDeleted ? true : undefined,
        overdue: isOverdue ? true : undefined,
        page: page.value,
        page_size: PAGE_SIZE,
      })
      tasks.value = data.items
      total.value = data.total
    } catch (error: unknown) {
      showToast(extractError(error, '加载任务列表失败'), 'error')
    } finally {
      loading.value = false
    }
  }

  let searchTimer = 0
  watch(taskSearch, () => {
    clearTimeout(searchTimer)
    searchTimer = window.setTimeout(() => {
      page.value = 1
      loadTasks()
    }, 300)
  })

  watch([statusFilter, flagFilter], () => {
    page.value = 1
    loadTasks()
  })

  watch(page, () => {
    loadTasks()
  })

  function isOperating(taskId: number): boolean {
    return operatingIds.value.has(taskId)
  }

  function setOperating(taskId: number, operating: boolean) {
    const set = new Set(operatingIds.value)
    if (operating) set.add(taskId)
    else set.delete(taskId)
    operatingIds.value = set
  }

  async function togglePinned(task: AdminTaskItem) {
    const next = !task.is_pinned
    const idx = tasks.value.findIndex(t => t.id === task.id)
    if (idx !== -1) tasks.value[idx] = { ...tasks.value[idx], is_pinned: next }
    setOperating(task.id, true)
    try {
      await operateAdminTask(task.id, { set_pinned: next })
      showToast(next ? '已置顶任务' : '已取消置顶', 'success')
    } catch (error: unknown) {
      if (idx !== -1) tasks.value[idx] = { ...tasks.value[idx], is_pinned: !next }
      showToast(extractError(error, '任务置顶操作失败'), 'error')
    } finally {
      setOperating(task.id, false)
    }
  }

  async function toggleUrgent(task: AdminTaskItem) {
    const next = !task.is_urgent
    const idx = tasks.value.findIndex(t => t.id === task.id)
    if (idx !== -1) tasks.value[idx] = { ...tasks.value[idx], is_urgent: next }
    setOperating(task.id, true)
    try {
      await operateAdminTask(task.id, { set_urgent: next })
      showToast(next ? '已加急任务' : '已取消加急', 'success')
    } catch (error: unknown) {
      if (idx !== -1) tasks.value[idx] = { ...tasks.value[idx], is_urgent: !next }
      showToast(extractError(error, '任务加急操作失败'), 'error')
    } finally {
      setOperating(task.id, false)
    }
  }

  async function setDemoteLevel(task: AdminTaskItem, level: number) {
    if (task.demote_level === level) return
    const prevLevel = task.demote_level
    const idx = tasks.value.findIndex(t => t.id === task.id)
    // Optimistic update
    if (idx !== -1) tasks.value[idx] = { ...tasks.value[idx], demote_level: level }
    setOperating(task.id, true)
    try {
      await operateAdminTask(task.id, { set_demote_level: level })
    } catch (error: unknown) {
      // Revert on failure
      if (idx !== -1) tasks.value[idx] = { ...tasks.value[idx], demote_level: prevLevel }
      showToast(extractError(error, '权重调整失败'), 'error')
    } finally {
      setOperating(task.id, false)
    }
  }

  async function deleteTask(task: AdminTaskItem) {
    setOperating(task.id, true)
    try {
      await operateAdminTask(task.id, { delete: true })
      showToast('任务已删除，相关用户已收到通知', 'success')
      await loadTasks()
    } catch (error: unknown) {
      showToast(extractError(error, '删除任务失败'), 'error')
    } finally {
      setOperating(task.id, false)
    }
  }

  function goPage(next: number) {
    if (next < 1 || next > totalPages.value) return
    page.value = next
  }

  return {
    loading,
    taskSearch,
    statusFilter,
    flagFilter,
    page,
    total,
    tasks,
    totalPages,
    loadTasks,
    goPage,
    togglePinned,
    toggleUrgent,
    setDemoteLevel,
    deleteTask,
    isOperating,
  }
}

export type AdminTasksModel = ReturnType<typeof useAdminTasks>
