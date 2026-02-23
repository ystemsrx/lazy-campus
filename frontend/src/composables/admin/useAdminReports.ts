import { ref, watch } from 'vue'

import {
  fetchAdminReports,
  fetchReportChatHistory,
  fetchTaskSnapshot,
  reviewReport,
} from '../../api/moderation'
import { appConfirm } from '../../components/AppConfirm.vue'
import type { Report } from '../../types/api'
import { extractError } from '../../utils/error'
import type { AppToastNotifier } from '../useAppToast'

export interface ReportStatusOption {
  value: string
  label: string
}

export interface TaskSnapshotMessage {
  sender_display_name: string
  created_at: string
  content: string
}

export interface TaskSnapshotReview {
  target_role: 'publisher' | 'worker'
  stars: number
  reviewer_display_name: string
  created_at: string
  comment: string | null
}

export interface DirectChatMessage {
  sender_display_name: string
  content: string
  created_at: string
}

export interface DirectChatHistory {
  reporter_display_name: string
  reported_user_display_name: string
  messages: DirectChatMessage[]
}

export interface TaskSnapshot {
  title: string
  status: string
  price: number
  location: string | null
  description: string
  publisher_display_name: string
  assignee_display_name: string | null
  deadline: string | null
  messages: TaskSnapshotMessage[]
  reviews: TaskSnapshotReview[]
}

const STATUS_OPTIONS: ReportStatusOption[] = [
  { value: 'pending', label: '待处理' },
  { value: 'approved', label: '已通过' },
  { value: 'rejected', label: '已驳回' },
]

const BAN_DAYS = [1, 3, 7]

const TASK_STATUS_MAP: Record<string, string> = {
  open: '待接取',
  in_progress: '进行中',
  completed: '已完成',
  canceled: '已取消',
  under_review: '审核中',
}

function reportStatusLabel(status: string) {
  return status === 'pending' ? '待审核' : status === 'approved' ? '已通过' : '已驳回'
}

function reportStatusClass(status: string) {
  return status === 'pending'
    ? 'badge-amber'
    : status === 'approved'
      ? 'badge-green'
      : 'badge-red'
}

export function useAdminReports(showToast: AppToastNotifier) {
  const reports = ref<Report[]>([])
  const reportSubTab = ref<'report' | 'appeal'>('report')
  const reportStatusFilter = ref<string>('pending')

  const showReviewModal = ref(false)
  const reviewTarget = ref<Report | null>(null)
  const reviewBanReason = ref('')
  const reviewSubmitting = ref(false)

  const showSnapshot = ref(false)
  const snapshotLoading = ref(false)
  const snapshot = ref<TaskSnapshot | null>(null)

  const showChatHistory = ref(false)
  const chatHistoryLoading = ref(false)
  const chatHistory = ref<DirectChatHistory | null>(null)

  async function loadReports() {
    try {
      reports.value = await fetchAdminReports({
        type: reportSubTab.value,
        status: reportStatusFilter.value || undefined,
      })
    } catch (error: unknown) {
      showToast(extractError(error, '加载举报列表失败'), 'error')
    }
  }

  watch([reportSubTab, reportStatusFilter], () => {
    loadReports()
  })

  async function doReview(
    report: Report,
    status: 'approved' | 'rejected',
    adminNotes?: string,
  ) {
    const isReport = report.type === 'report'
    try {
      await reviewReport(report.id, { status, admin_notes: adminNotes })
      if (isReport) {
        showToast(status === 'approved' ? '已通过，被举报用户已自动封禁' : '已驳回', 'success')
      } else {
        showToast(status === 'approved' ? '申诉通过，用户已解封' : '申诉已驳回', 'success')
      }
      await loadReports()
    } catch (error: unknown) {
      showToast(extractError(error, '审核失败'), 'error')
    }
  }

  async function handleReview(report: Report, status: 'approved' | 'rejected') {
    const isReport = report.type === 'report'

    if (isReport && status === 'approved') {
      reviewTarget.value = report
      reviewBanReason.value = ''
      showReviewModal.value = true
      return
    }

    if (!isReport && status === 'approved') {
      const name =
        report.reporter_nickname ||
        report.reporter_name ||
        report.reporter_account ||
        '该用户'
      const yes = await appConfirm({
        title: '确认通过申诉',
        message: `通过后「${name}」将被解除封禁，确定通过？`,
        confirmText: '确认通过',
        type: 'info',
      })
      if (!yes) {
        return
      }
    }

    await doReview(report, status)
  }

  async function confirmReportReview() {
    if (!reviewTarget.value) {
      return
    }
    reviewSubmitting.value = true
    try {
      await doReview(
        reviewTarget.value,
        'approved',
        reviewBanReason.value || undefined,
      )
      showReviewModal.value = false
    } finally {
      reviewSubmitting.value = false
    }
  }

  function closeReviewModal() {
    showReviewModal.value = false
  }

  async function openSnapshot(taskId: number) {
    showSnapshot.value = true
    snapshotLoading.value = true
    snapshot.value = null
    try {
      snapshot.value = await fetchTaskSnapshot(taskId)
    } catch (error: unknown) {
      showToast(extractError(error, '加载任务快照失败'), 'error')
      showSnapshot.value = false
    } finally {
      snapshotLoading.value = false
    }
  }

  function closeSnapshot() {
    showSnapshot.value = false
  }

  async function openChatHistory(reportId: number) {
    showChatHistory.value = true
    chatHistoryLoading.value = true
    chatHistory.value = null
    try {
      chatHistory.value = await fetchReportChatHistory(reportId)
    } catch (error: unknown) {
      showToast(extractError(error, '加载聊天记录失败'), 'error')
      showChatHistory.value = false
    } finally {
      chatHistoryLoading.value = false
    }
  }

  function closeChatHistory() {
    showChatHistory.value = false
  }

  return {
    reports,
    reportSubTab,
    reportStatusFilter,
    STATUS_OPTIONS,
    BAN_DAYS,
    TASK_STATUS_MAP,
    reportStatusLabel,
    reportStatusClass,
    loadReports,
    handleReview,
    showReviewModal,
    reviewTarget,
    reviewBanReason,
    reviewSubmitting,
    confirmReportReview,
    closeReviewModal,
    showSnapshot,
    snapshotLoading,
    snapshot,
    openSnapshot,
    closeSnapshot,
    showChatHistory,
    chatHistoryLoading,
    chatHistory,
    openChatHistory,
    closeChatHistory,
  }
}

export type AdminReportsModel = ReturnType<typeof useAdminReports>
