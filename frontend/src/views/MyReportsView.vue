<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { fetchMyReports, fetchReceivedReports } from '../api/moderation'
import AppToast from '../components/AppToast.vue'
import HomeAvatar from '../components/home/ui/HomeAvatar.vue'
import HomeHeaderBar from '../components/home/HomeHeaderBar.vue'
import LoginAppealModal from '../components/login/LoginAppealModal.vue'
import { useAppToast } from '../composables/useAppToast'
import { useAuthStore } from '../stores/auth'
import type { Report } from '../types/api'
import { extractError } from '../utils/error'
import { formatFull } from '../utils/time'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const appTitle = import.meta.env.VITE_APP_TITLE || '校园任务平台'
const me = computed(() => auth.user)

const { toast, showToast, clearToast } = useAppToast()
const lightboxSrc = ref<string | null>(null)

type SectionType = 'submitted' | 'received'
const SECTIONS = [
  { id: 'submitted' as const, label: '我提交的', icon: 'fa-solid fa-paper-plane' },
  { id: 'received' as const, label: '我收到的', icon: 'fa-solid fa-gavel' },
]
const activeSection = ref<SectionType>(route.query.tab === 'received' ? 'received' : 'submitted')
const sectionIndex = computed(() => SECTIONS.findIndex(s => s.id === activeSection.value))

const loading = ref(false)
const myReports = ref<Report[]>([])
const receivedReports = ref<Report[]>([])
const activeTab = ref<'all' | 'processing' | 'completed'>('all')
const selectedReportId = ref<number | null>(null)
const selectedReceivedId = ref<number | null>(null)

const TABS = [
  { id: 'all' as const,        label: '全部' },
  { id: 'processing' as const, label: '处理中' },
  { id: 'completed' as const,  label: '已完结' },
]

const tabIndex = computed(() => TABS.findIndex(t => t.id === activeTab.value))

const filteredReports = computed(() => {
  return myReports.value.filter((r) => {
    if (activeTab.value === 'processing') return r.status === 'pending'
    if (activeTab.value === 'completed') return r.status === 'approved' || r.status === 'rejected'
    return true
  })
})

const selectedReport = computed(() =>
  myReports.value.find((r) => r.id === selectedReportId.value) ?? null,
)

const selectedReceived = computed(() =>
  receivedReports.value.find((r) => r.id === selectedReceivedId.value) ?? null,
)

function reportDisplayName(r: Report) {
  if (r.type === 'appeal') {
    return r.reporter_nickname || r.reporter_name || r.reporter_account || '未知'
  }
  return r.reported_user_nickname || r.reported_user_name || r.reported_user_account || '未知用户'
}

function typeLabel(type: string) {
  return type === 'report' ? '举报' : '申诉'
}

function statusLabel(status: string) {
  if (status === 'pending') return '待审核'
  if (status === 'approved') return '已通过'
  return '已驳回'
}

function statusIcon(status: string) {
  if (status === 'pending') return 'fa-solid fa-clock'
  if (status === 'approved') return 'fa-solid fa-shield-halved'
  return 'fa-solid fa-circle-xmark'
}

function dateOnly(iso: string) {
  return formatFull(iso).split(' ')[0]
}

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
    showToast(extractError(error, '加载举报记录失败'), 'error')
  } finally {
    loading.value = false
  }
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

function handleHeaderTabChange(tab: 'hall' | 'workers' | null) {
  router.push({ path: '/', query: tab === 'workers' ? { tab: 'workers' } : {} })
}

function logout() {
  auth.logout()
  router.push('/login')
}

watch(activeSection, () => {
  selectedReportId.value = null
  selectedReceivedId.value = null
})

const showAppealModal = ref(false)

function onAppealSubmitted() {
  showAppealModal.value = false
  loadReports()
}

const hasPendingAppeal = computed(() =>
  myReports.value.some(r => r.type === 'appeal' && r.status === 'pending'),
)

const hasAnyBan = computed(() => {
  const u = me.value
  if (!u) return false
  return u.is_banned || u.ban_publish || u.ban_accept || u.ban_contact
})

const activePenaltyId = computed(() => {
  if (!hasAnyBan.value || receivedReports.value.length === 0) return null
  return receivedReports.value[0].id
})

onMounted(() => {
  loadReports()
})
</script>

<template>
  <AppToast :toast="toast" @dismiss="clearToast" />

  <div class="mr-page">
    <div class="mr-bg-gradient" />

    <HomeHeaderBar
      :active-tab="null"
      :app-title="appTitle"
      :is-authenticated="auth.isAuthenticated"
      :display-name="auth.displayName"
      :avatar-url="me?.avatar_url"
      :gender="me?.gender ?? null"
      @publish="router.push('/')"
      @open-my-panel="router.push('/tasks')"
      @open-settings="router.push('/settings')"
      @open-reports="loadReports"
      @open-chat="router.push('/chat')"
      @login="router.push('/login')"
      @logout="logout"
      @update:active-tab="handleHeaderTabChange"
    />

    <div class="mr-container">
      <header class="mr-page-header">
        <h1 class="mr-page-title">我的举报与申诉</h1>
        <p class="mr-page-subtitle">查看您提交的举报与收到的处罚</p>
      </header>

      <!-- Section Toggle -->
      <div class="mr-section-toggle">
        <div
          class="mr-section-slider"
          :style="{ transform: `translateX(${sectionIndex * 100}%)` }"
        />
        <button
          v-for="sec in SECTIONS"
          :key="sec.id"
          class="mr-section-btn"
          :class="{ 'mr-section-btn--active': activeSection === sec.id }"
          @click="activeSection = sec.id"
        >
          <i :class="sec.icon" />
          {{ sec.label }}
          <span v-if="sec.id === 'received' && hasAnyBan" class="mr-section-count">1</span>
        </button>
      </div>

      <!-- Loading Skeleton -->
      <div v-if="loading" class="mr-layout">
        <div class="mr-skel-list">
          <div class="mr-skel mr-skel--tabs" />
          <div class="mr-skel mr-skel--card" />
          <div class="mr-skel mr-skel--card" />
          <div class="mr-skel mr-skel--card" />
        </div>
        <div class="mr-skel-detail">
          <div class="mr-skel mr-skel--banner" />
          <div class="mr-skel mr-skel--block" />
        </div>
      </div>

      <!-- ═══ Section: 我提交的 ═══ -->
      <div v-else-if="activeSection === 'submitted'" class="mr-layout">
        <div
          class="mr-list-panel"
          :class="{ 'mr-list-panel--hidden': selectedReportId !== null }"
        >
          <div class="mr-list-header">
            <h2 class="mr-list-title">全部记录</h2>
          </div>

          <div class="mr-tabs">
            <div
              class="mr-tabs__slider"
              :style="{ transform: `translateX(${tabIndex * 100}%)` }"
            />
            <button
              v-for="tab in TABS"
              :key="tab.id"
              class="mr-tab"
              :class="activeTab === tab.id ? `mr-tab--active-${tab.id}` : ''"
              @click="activeTab = tab.id"
            >
              {{ tab.label }}
            </button>
          </div>

          <div class="mr-list-body">
            <div v-if="filteredReports.length === 0" class="mr-empty">
              <i class="fa-solid fa-file-lines" />
              <span>暂无相关举报记录</span>
            </div>

            <div v-else class="mr-list-items">
              <div
                v-for="report in filteredReports"
                :key="report.id"
                class="mr-card"
                :class="{ 'mr-card--selected': selectedReportId === report.id }"
                @click="selectReport(report.id)"
              >
                <div class="mr-card__top">
                  <span class="mr-card__id">单号 #{{ report.id }}</span>
                  <span
                    class="mr-badge"
                    :class="{
                      'mr-badge--pending': report.status === 'pending',
                      'mr-badge--approved': report.status === 'approved',
                      'mr-badge--rejected': report.status === 'rejected',
                    }"
                  >
                    <i :class="statusIcon(report.status)" />
                    {{ statusLabel(report.status) }}
                  </span>
                </div>

                <div class="mr-card__body">
                  <HomeAvatar
                    class="mr-card__avatar-img"
                    :avatar-url="report.type === 'appeal' ? report.reporter_avatar_url : report.reported_user_avatar_url"
                    :gender="report.type === 'appeal' ? (report.reporter_gender ?? null) : (report.reported_user_gender ?? null)"
                    size="lg"
                    alt="被举报人头像"
                  />
                  <div class="mr-card__info">
                    <div class="mr-card__target">
                      {{ typeLabel(report.type) }}：{{ reportDisplayName(report) }}
                    </div>
                    <div class="mr-card__reason">{{ report.reason }}</div>
                  </div>
                </div>

                <div class="mr-card__footer">
                  <span class="mr-card__date">提交于 {{ dateOnly(report.created_at) }}</span>
                  <span class="mr-card__action">
                    查看详情 <i class="fa-solid fa-chevron-right" />
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Detail Panel -->
        <div
          class="mr-detail-panel"
          :class="{ 'mr-detail-panel--hidden': selectedReportId === null }"
        >
          <div v-if="!selectedReport" class="mr-detail-placeholder">
            <i class="fa-solid fa-shield-halved" />
            <span>请在左侧选择一个举报记录查看详情</span>
          </div>

          <div v-else class="mr-detail-content">
            <div class="mr-detail-back-bar">
              <button class="mr-detail-back-btn" @click="deselectReport">
                <i class="fa-solid fa-arrow-left" />
                返回列表
              </button>
            </div>

            <!-- Status Banner -->
            <div
              v-if="selectedReport.status === 'pending'"
              class="mr-status-banner mr-status-banner--pending"
            >
              <i class="fa-solid fa-clock" />
              <div>
                <div class="mr-status-banner__title">平台正在核实中</div>
                <div class="mr-status-banner__message">
                  我们已收到您的反馈，正在调查处理。一般情况下，处理结果将在
                  24-48 小时内反馈给您，请耐心等待。
                </div>
              </div>
            </div>

            <div
              v-else-if="selectedReport.status === 'approved'"
              class="mr-status-banner mr-status-banner--approved"
            >
              <i class="fa-solid fa-circle-check" />
              <div class="mr-status-banner__body">
                <div class="mr-status-banner__title">
                  {{ selectedReport.type === 'report' ? '举报已通过' : '申诉已通过' }}
                </div>
                <div class="mr-status-banner__message">
                  <template v-if="selectedReport.type === 'report'">
                    经核实，举报成立，平台已对违规方采取相应措施。
                  </template>
                  <template v-else>
                    您的申诉已被管理员审核通过，账号封禁已解除，您现在可以正常使用平台所有功能。
                  </template>
                </div>
                <div v-if="selectedReport.type === 'report'" class="mr-penalty-box">
                  <div class="mr-penalty-box__row">
                    <i class="fa-solid fa-gavel" />
                    <span>{{ selectedReport.ban_penalty || '已对违规方执行处罚' }}</span>
                  </div>
                  <div v-if="selectedReport.admin_notes" class="mr-penalty-box__reason">
                    处罚理由：{{ selectedReport.admin_notes }}
                  </div>
                </div>
              </div>
            </div>

            <div
              v-else-if="selectedReport.status === 'rejected'"
              class="mr-status-banner mr-status-banner--rejected"
            >
              <i class="fa-solid fa-circle-xmark" />
              <div>
                <div class="mr-status-banner__title">
                  {{ selectedReport.type === 'report' ? '举报未通过' : '申诉未通过' }}
                </div>
                <div class="mr-status-banner__message">
                  <template v-if="selectedReport.type === 'report'">
                    抱歉，根据您提供的证据及平台核实，暂未发现明显违规行为。建议补充更多有效证据后重新提交。
                  </template>
                  <template v-else>
                    抱歉，经管理员审核，您的申诉暂未获得通过。如有异议，请确认材料后重新提交申诉。
                  </template>
                </div>
              </div>
            </div>

            <div
              v-if="selectedReport.status === 'rejected' && selectedReport.admin_notes"
              class="mr-admin-notes"
            >
              <div class="mr-admin-notes__header">
                <i class="fa-solid fa-comment-dots" />
                <span>管理员说明</span>
              </div>
              <div class="mr-admin-notes__body">{{ selectedReport.admin_notes }}</div>
            </div>

            <!-- Report Info Card -->
            <div class="mr-info-card">
              <h3 class="mr-info-card__title">
                {{ selectedReport.type === 'report' ? '我提交的举报' : '我提交的申诉' }}
              </h3>

              <div class="mr-info-target">
                <HomeAvatar
                  class="mr-info-target__avatar-img"
                  :avatar-url="selectedReport.type === 'appeal' ? selectedReport.reporter_avatar_url : selectedReport.reported_user_avatar_url"
                  :gender="selectedReport.type === 'appeal' ? (selectedReport.reporter_gender ?? null) : (selectedReport.reported_user_gender ?? null)"
                  size="lg"
                  :alt="selectedReport.type === 'report' ? '被举报人头像' : '申诉人头像'"
                />
                <div>
                  <div class="mr-info-target__label">
                    {{ selectedReport.type === 'report' ? '被举报人' : '申诉账号' }}
                  </div>
                  <div class="mr-info-target__name">{{ reportDisplayName(selectedReport) }}</div>
                </div>
              </div>

              <div class="mr-info-fields">
                <div>
                  <div class="mr-info-field__label">
                    {{ selectedReport.type === 'report' ? '举报事由' : '申诉事由' }}
                  </div>
                  <div class="mr-info-field__value">{{ selectedReport.reason }}</div>
                </div>

                <div v-if="selectedReport.evidence">
                  <div class="mr-info-field__label">
                    {{ selectedReport.type === 'report' ? '补充说明' : '申诉材料 / 说明' }}
                  </div>
                  <div class="mr-info-field__evidence">{{ selectedReport.evidence }}</div>
                </div>

                <div v-if="selectedReport.images?.length">
                  <div class="mr-info-field__label">截图证据</div>
                  <div class="mr-evidence-imgs">
                    <img
                      v-for="(src, i) in selectedReport.images"
                      :key="i"
                      :src="src"
                      class="mr-evidence-img"
                      alt="证据截图"
                      @click="lightboxSrc = src"
                    />
                  </div>
                </div>
              </div>

              <div class="mr-info-meta">
                <div class="mr-info-meta__item">
                  <span class="mr-info-meta__label">类型</span>
                  <span class="mr-badge" :class="selectedReport.type === 'report' ? 'mr-badge--report' : 'mr-badge--appeal'">
                    {{ typeLabel(selectedReport.type) }}
                  </span>
                </div>
                <div v-if="selectedReport.task_id" class="mr-info-meta__item">
                  <span class="mr-info-meta__label">关联任务</span>
                  <span class="mr-info-meta__value">#{{ selectedReport.task_id }}</span>
                </div>
                <div class="mr-info-meta__item">
                  <span class="mr-info-meta__label">提交时间</span>
                  <span class="mr-info-meta__value">{{ formatFull(selectedReport.created_at) }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ═══ Section: 我收到的处罚 ═══ -->
      <div v-else class="mr-layout">
        <div
          class="mr-list-panel"
          :class="{ 'mr-list-panel--hidden': selectedReceivedId !== null }"
        >
          <div class="mr-list-header">
            <h2 class="mr-list-title">处罚记录</h2>
          </div>

          <div class="mr-list-body">
            <div v-if="receivedReports.length === 0" class="mr-empty">
              <i class="fa-solid fa-check-circle" />
              <span>暂无处罚记录，继续保持良好表现！</span>
            </div>

            <div v-else class="mr-list-items">
              <div
                v-for="report in receivedReports"
                :key="report.id"
                class="mr-card mr-card--penalty"
                :class="{ 'mr-card--selected': selectedReceivedId === report.id }"
                @click="selectReceived(report.id)"
              >
                <div class="mr-card__top">
                  <span class="mr-card__id">处罚 #{{ report.id }}</span>
                  <span
                    class="mr-badge"
                    :class="report.id === activePenaltyId ? 'mr-badge--active-penalty' : 'mr-badge--approved'"
                  >
                    <i :class="report.id === activePenaltyId ? 'fa-solid fa-circle-dot' : 'fa-solid fa-gavel'" />
                    {{ report.id === activePenaltyId ? '处罚中' : '已结束' }}
                  </span>
                </div>
                <div class="mr-card__body">
                  <div class="mr-card__penalty-icon">
                    <i class="fa-solid fa-triangle-exclamation" />
                  </div>
                  <div class="mr-card__info">
                    <div class="mr-card__target">
                      {{ report.ban_penalty || '账号限制' }}
                    </div>
                    <div class="mr-card__reason">举报事由：{{ report.reason }}</div>
                  </div>
                </div>
                <div class="mr-card__footer">
                  <span class="mr-card__date">{{ dateOnly(report.created_at) }}</span>
                  <span class="mr-card__action">
                    查看详情 <i class="fa-solid fa-chevron-right" />
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Detail Panel (received) -->
        <div
          class="mr-detail-panel"
          :class="{ 'mr-detail-panel--hidden': selectedReceivedId === null }"
        >
          <div v-if="!selectedReceived" class="mr-detail-placeholder">
            <i class="fa-solid fa-gavel" />
            <span>请在左侧选择一条处罚记录查看详情</span>
          </div>

          <div v-else class="mr-detail-content">
            <div class="mr-detail-back-bar">
              <button class="mr-detail-back-btn" @click="deselectReceived">
                <i class="fa-solid fa-arrow-left" />
                返回列表
              </button>
            </div>

            <!-- Penalty Banner -->
            <div class="mr-status-banner mr-status-banner--approved">
              <i class="fa-solid fa-gavel" />
              <div class="mr-status-banner__body">
                <div class="mr-status-banner__title">你收到了平台处罚</div>
                <div class="mr-status-banner__message">
                  <template v-if="selectedReceived.is_admin_ban">
                    经平台管理员核查，对你的账号执行了以下处罚。如有异议，可提交申诉。
                  </template>
                  <template v-else>
                    因其他用户的举报，经平台核实后对你的账号执行了以下处罚。如有异议，可提交申诉。
                  </template>
                </div>
                <div class="mr-penalty-box">
                  <div class="mr-penalty-box__row">
                    <i class="fa-solid fa-ban" />
                    <span>{{ selectedReceived.ban_penalty || '已对你的账号执行处罚' }}</span>
                  </div>
                  <div v-if="selectedReceived.admin_notes" class="mr-penalty-box__reason">
                    处罚理由：{{ selectedReceived.admin_notes }}
                  </div>
                </div>
              </div>
            </div>

            <!-- Info card -->
            <div class="mr-info-card">
              <h3 class="mr-info-card__title">处罚详情</h3>

              <div v-if="!selectedReceived.is_admin_ban" class="mr-info-fields">
                <div>
                  <div class="mr-info-field__label">举报事由</div>
                  <div class="mr-info-field__value">{{ selectedReceived.reason }}</div>
                </div>
                <div v-if="selectedReceived.evidence">
                  <div class="mr-info-field__label">补充说明</div>
                  <div class="mr-info-field__evidence">{{ selectedReceived.evidence }}</div>
                </div>
                <div v-if="selectedReceived.images?.length">
                  <div class="mr-info-field__label">截图证据</div>
                  <div class="mr-evidence-imgs">
                    <img
                      v-for="(src, i) in selectedReceived.images"
                      :key="i"
                      :src="src"
                      class="mr-evidence-img"
                      alt="证据截图"
                      @click="lightboxSrc = src"
                    />
                  </div>
                </div>
              </div>

              <div class="mr-info-meta">
                <div class="mr-info-meta__item">
                  <span class="mr-info-meta__label">处罚时间</span>
                  <span class="mr-info-meta__value">{{ formatFull(selectedReceived.created_at) }}</span>
                </div>
              </div>
            </div>

            <div v-if="selectedReceived?.id === activePenaltyId" class="mr-appeal-bar">
              <button
                v-if="hasPendingAppeal"
                class="mr-appeal-btn mr-appeal-btn--disabled"
                disabled
              >
                <i class="fa-solid fa-hourglass-half" />
                已有待处理的申诉
              </button>
              <button
                v-else-if="hasAnyBan"
                class="mr-appeal-btn"
                @click="showAppealModal = true"
              >
                <i class="fa-solid fa-paper-plane" />
                对此提交申诉
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <LoginAppealModal
    v-model="showAppealModal"
    authenticated
    :initial-ban-until="me?.ban_until ?? null"
    @submitted="onAppealSubmitted"
  />

  <Teleport to="body">
    <Transition name="mr-lb">
      <div v-if="lightboxSrc" class="mr-lightbox" @click="lightboxSrc = null">
        <img :src="lightboxSrc" class="mr-lightbox__img" alt="证据截图预览" />
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped src="./my-reports-view.css"></style>

<style scoped>
.mr-section-toggle {
  display: flex;
  position: relative;
  margin-bottom: 20px;
  padding: 4px;
  background: rgba(255, 255, 255, 0.35);
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.4);
  backdrop-filter: blur(12px);
  max-width: 380px;
}
.mr-section-slider {
  position: absolute;
  top: 4px;
  left: 4px;
  width: calc(50% - 4px);
  height: calc(100% - 8px);
  background: rgba(255, 255, 255, 0.7);
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  pointer-events: none;
  z-index: 0;
}
.mr-section-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 10px 16px;
  border: none;
  border-radius: 12px;
  background: transparent;
  color: #6b7280;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: color 0.25s ease;
  position: relative;
  z-index: 1;
}
.mr-section-btn--active {
  color: #111827;
}
.mr-section-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  border-radius: 9px;
  background: #ef4444;
  color: #fff;
  font-size: 11px;
  font-weight: 600;
  line-height: 1;
}

.mr-card--penalty .mr-card__penalty-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  background: rgba(239, 68, 68, 0.1);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.mr-card--penalty .mr-card__penalty-icon i {
  font-size: 18px;
  color: #ef4444;
}

.mr-appeal-bar {
  padding: 16px 0;
}
.mr-appeal-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  height: 44px;
  background: #1c1c1c;
  color: #fff;
  border: none;
  border-radius: 16px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
}
.mr-appeal-btn:hover:not(:disabled) {
  background: #000;
  transform: translateY(-1px);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.2);
}
.mr-appeal-btn:active:not(:disabled) {
  transform: translateY(0);
}
.mr-appeal-btn--disabled {
  opacity: 0.6;
  cursor: not-allowed;
  background: #6b7280;
}

.mr-evidence-imgs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 6px;
}

.mr-evidence-img {
  width: 88px;
  height: 88px;
  object-fit: cover;
  border-radius: 10px;
  border: 1px solid var(--c-border);
  cursor: zoom-in;
}

.mr-lightbox {
  position: fixed;
  inset: 0;
  z-index: 9999;
  background: rgba(0, 0, 0, 0.88);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  cursor: zoom-out;
  backdrop-filter: blur(4px);
}

.mr-lightbox__img {
  max-width: 100%;
  max-height: 100%;
  border-radius: 12px;
  box-shadow: 0 8px 40px rgba(0, 0, 0, 0.5);
  object-fit: contain;
}

.mr-lb-enter-active,
.mr-lb-leave-active {
  transition: opacity 0.2s ease;
}

.mr-lb-enter-from,
.mr-lb-leave-to {
  opacity: 0;
}

@media (max-width: 640px) {
  .mr-section-toggle {
    max-width: 100%;
  }
}
</style>
