import { computed, onActivated, onMounted, ref, watch, type Ref } from 'vue'
import { useRoute } from 'vue-router'

import { fetchMyReports, fetchReceivedReports } from '../../api/moderation'
import type { Report, UserMe } from '../../types/api'
import { extractError } from '../../utils/error'
import type { AppToastNotifier } from '../useAppToast'

export type ReportsSectionType = 'submitted' | 'received'
export type ReportsTabType = 'all' | 'processing' | 'completed'

export const REPORT_SECTION_OPTIONS = [
  { id: 'submitted' as const, label: '我提交的', icon: 'fa-solid fa-paper-plane' },
  { id: 'received' as const, label: '我收到的', icon: 'fa-solid fa-gavel' },
]

export const REPORT_TAB_OPTIONS = [
  { id: 'all' as const, label: '全部' },
  { id: 'processing' as const, label: '处理中' },
  { id: 'completed' as const, label: '已完结' },
]

interface UseMyReportsDataOptions {
  me: Readonly<Ref<UserMe | null | undefined>>
  showToast: AppToastNotifier
}

export function useMyReportsData(options: UseMyReportsDataOptions) {
  const route = useRoute()

  const lightboxSrc = ref<string | null>(null)
  const activeSection = ref<ReportsSectionType>(route.query.tab === 'received' ? 'received' : 'submitted')

  const loading = ref(false)
  const myReports = ref<Report[]>([])
  const receivedReports = ref<Report[]>([])

  const activeTab = ref<ReportsTabType>('all')
  const selectedReportId = ref<number | null>(null)
  const selectedReceivedId = ref<number | null>(null)
  const showAppealModal = ref(false)

  const sectionIndex = computed(() =>
    REPORT_SECTION_OPTIONS.findIndex((section) => section.id === activeSection.value),
  )
  const tabIndex = computed(() =>
    REPORT_TAB_OPTIONS.findIndex((tab) => tab.id === activeTab.value),
  )

  const filteredReports = computed(() =>
    myReports.value.filter((report) => {
      if (activeTab.value === 'processing') return report.status === 'pending'
      if (activeTab.value === 'completed') return report.status === 'approved' || report.status === 'rejected'
      return true
    }),
  )

  const selectedReport = computed(() =>
    myReports.value.find((report) => report.id === selectedReportId.value) ?? null,
  )

  const selectedReceived = computed(() =>
    receivedReports.value.find((report) => report.id === selectedReceivedId.value) ?? null,
  )

  const hasPendingAppeal = computed(() =>
    myReports.value.some((report) => report.type === 'appeal' && report.status === 'pending'),
  )

  const hasAnyBan = computed(() => {
    const user = options.me.value
    if (!user) return false
    return user.is_banned || user.ban_publish || user.ban_accept || user.ban_contact
  })

  const activePenaltyId = computed(() => {
    if (!hasAnyBan.value || receivedReports.value.length === 0) return null
    return receivedReports.value[0].id
  })

  async function loadReports() {
    loading.value = true
    try {
      const [submitted, received] = await Promise.all([
        fetchMyReports(),
        fetchReceivedReports(),
      ])
      myReports.value = submitted
      receivedReports.value = received
    } catch (error: unknown) {
      options.showToast(extractError(error, '加载举报记录失败'), 'error')
    } finally {
      loading.value = false
    }
  }

  function setActiveSection(section: ReportsSectionType) {
    activeSection.value = section
  }

  function setActiveTab(tab: ReportsTabType) {
    activeTab.value = tab
  }

  function selectReport(id: number) {
    selectedReportId.value = id
  }

  function deselectReport() {
    selectedReportId.value = null
  }

  function selectReceived(id: number) {
    selectedReceivedId.value = id
  }

  function deselectReceived() {
    selectedReceivedId.value = null
  }

  function openAppealModal() {
    showAppealModal.value = true
  }

  function onAppealSubmitted() {
    showAppealModal.value = false
    void loadReports()
  }

  function openLightbox(src: string) {
    lightboxSrc.value = src
  }

  function closeLightbox() {
    lightboxSrc.value = null
  }

  watch(activeSection, () => {
    selectedReportId.value = null
    selectedReceivedId.value = null
  })

  let bootstrapped = false

  onMounted(() => {
    loadReports().then(() => { bootstrapped = true })
  })

  onActivated(() => {
    if (bootstrapped) loadReports().catch(() => {})
  })

  return {
    sections: REPORT_SECTION_OPTIONS,
    tabs: REPORT_TAB_OPTIONS,
    lightboxSrc,
    activeSection,
    sectionIndex,
    loading,
    myReports,
    receivedReports,
    activeTab,
    tabIndex,
    filteredReports,
    selectedReportId,
    selectedReceivedId,
    selectedReport,
    selectedReceived,
    showAppealModal,
    hasPendingAppeal,
    hasAnyBan,
    activePenaltyId,
    loadReports,
    setActiveSection,
    setActiveTab,
    selectReport,
    deselectReport,
    selectReceived,
    deselectReceived,
    openAppealModal,
    onAppealSubmitted,
    openLightbox,
    closeLightbox,
  }
}
