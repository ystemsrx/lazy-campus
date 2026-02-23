import { computed, ref, watch } from 'vue'

import { fetchAdminTasks, operateAdminTask } from '../../api/moderation'
import type { AdminTaskItem } from '../../types/api'
import { extractError } from '../../utils/error'
import type { AppToastNotifier } from '../useAppToast'

const PAGE_SIZE = 20

export function useAdminTasks(showToast: AppToastNotifier) {
  const loading = ref(false)
  const taskSearch = ref('')
  const statusFilter = ref<string>('all')
  const flagFilter = ref<string>('all')
  const deletedFilter = ref<string>('all')
  const page = ref(1)
  const total = ref(0)
  const tasks = ref<AdminTaskItem[]>([])
  const operatingIds = ref<Set<number>>(new Set())

  const totalPages = computed(() => Math.max(1, Math.ceil(total.value / PAGE_SIZE)))

  async function loadTasks() {
    loading.value = true
    try {
      const data = await fetchAdminTasks({
        q: taskSearch.value.trim() || undefined,
        status: statusFilter.value !== 'all' ? statusFilter.value : undefined,
        flag: flagFilter.value !== 'all' ? (flagFilter.value as 'pinned' | 'urgent' | 'flagged') : undefined,
        deleted: deletedFilter.value === 'deleted' ? true : deletedFilter.value === 'normal' ? false : undefined,
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

  watch([statusFilter, flagFilter, deletedFilter], () => {
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
    setOperating(task.id, true)
    try {
      await operateAdminTask(task.id, { set_pinned: !task.is_pinned })
      showToast(task.is_pinned ? '已取消置顶' : '已置顶任务', 'success')
      await loadTasks()
    } catch (error: unknown) {
      showToast(extractError(error, '任务置顶操作失败'), 'error')
    } finally {
      setOperating(task.id, false)
    }
  }

  async function toggleUrgent(task: AdminTaskItem) {
    setOperating(task.id, true)
    try {
      await operateAdminTask(task.id, { set_urgent: !task.is_urgent })
      showToast(task.is_urgent ? '已取消加急' : '已加急任务', 'success')
      await loadTasks()
    } catch (error: unknown) {
      showToast(extractError(error, '任务加急操作失败'), 'error')
    } finally {
      setOperating(task.id, false)
    }
  }

  async function updateAdminNote(task: AdminTaskItem, note: string) {
    setOperating(task.id, true)
    try {
      await operateAdminTask(task.id, { admin_note: note })
      showToast('管理员备注已更新', 'success')
      await loadTasks()
    } catch (error: unknown) {
      showToast(extractError(error, '更新备注失败'), 'error')
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
    deletedFilter,
    page,
    total,
    tasks,
    totalPages,
    loadTasks,
    goPage,
    togglePinned,
    toggleUrgent,
    updateAdminNote,
    deleteTask,
    isOperating,
  }
}

export type AdminTasksModel = ReturnType<typeof useAdminTasks>
