import { computed, ref, watch } from 'vue'

import { fetchAdminActionLogs } from '../../api/moderation'
import type { AdminActionLogItem } from '../../types/api'
import { extractError } from '../../utils/error'
import type { AppToastNotifier } from '../useAppToast'

const PAGE_SIZE = 30

export function useAdminActionLogs(showToast: AppToastNotifier) {
  const loading = ref(false)
  const query = ref('')
  const actionFilter = ref<string>('all')
  const page = ref(1)
  const total = ref(0)
  const logs = ref<AdminActionLogItem[]>([])

  const totalPages = computed(() => Math.max(1, Math.ceil(total.value / PAGE_SIZE)))

  const actionOptions = computed(() => {
    const set = new Set(logs.value.map(l => l.action))
    return ['all', ...Array.from(set).sort()]
  })

  async function loadLogs() {
    loading.value = true
    try {
      const data = await fetchAdminActionLogs({
        q: query.value.trim() || undefined,
        action: actionFilter.value !== 'all' ? actionFilter.value : undefined,
        page: page.value,
        page_size: PAGE_SIZE,
      })
      logs.value = data.items
      total.value = data.total
    } catch (error: unknown) {
      showToast(extractError(error, '加载操作日志失败'), 'error')
    } finally {
      loading.value = false
    }
  }

  let timer = 0
  watch(query, () => {
    clearTimeout(timer)
    timer = window.setTimeout(() => {
      page.value = 1
      loadLogs()
    }, 250)
  })

  watch(actionFilter, () => {
    page.value = 1
    loadLogs()
  })

  watch(page, () => {
    loadLogs()
  })

  function goPage(next: number) {
    if (next < 1 || next > totalPages.value) return
    page.value = next
  }

  return {
    loading,
    query,
    actionFilter,
    page,
    total,
    totalPages,
    logs,
    actionOptions,
    loadLogs,
    goPage,
  }
}

export type AdminActionLogsModel = ReturnType<typeof useAdminActionLogs>
