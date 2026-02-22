<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { fetchMyReports } from '../api/moderation'
import AppToast from '../components/AppToast.vue'
import HomeAvatar from '../components/home/ui/HomeAvatar.vue'
import HomeHeaderBar from '../components/home/HomeHeaderBar.vue'
import { useAppToast } from '../composables/useAppToast'
import { useAuthStore } from '../stores/auth'
import type { Report } from '../types/api'
import { extractError } from '../utils/error'
import { formatFull } from '../utils/time'

// 与管理端保持一致，第 N 次封禁对应的天数
const BAN_DAYS = [1, 3, 7]

function banDuration(report: Report): number {
  const count = report.reported_user_ban_count ?? 0
  return BAN_DAYS[Math.min(count, BAN_DAYS.length - 1)]
}

function banCount(report: Report): number {
  return (report.reported_user_ban_count ?? 0) + 1
}

const router = useRouter()
const auth = useAuthStore()
const appTitle = import.meta.env.VITE_APP_TITLE || '校园任务平台'
const me = computed(() => auth.user)

const { toast, showToast, clearToast } = useAppToast()
const lightboxSrc = ref<string | null>(null)

const loading = ref(false)
const myReports = ref<Report[]>([])
const activeTab = ref<'all' | 'processing' | 'completed'>('all')
const selectedReportId = ref<number | null>(null)

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
    myReports.value = await fetchMyReports()
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

function handleHeaderTabChange(tab: 'hall' | 'workers' | null) {
  router.push({ path: '/', query: tab === 'workers' ? { tab: 'workers' } : {} })
}

function logout() {
  auth.logout()
  router.push('/login')
}

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
        <p class="mr-page-subtitle">查看您提交的所有举报与申诉处理进度</p>
      </header>

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

      <!-- Main Content -->
      <div v-else class="mr-layout">
        <!-- List Panel -->
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
                    :avatar-url="null"
                    :gender="null"
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
          <!-- Placeholder when nothing selected (desktop) -->
          <div v-if="!selectedReport" class="mr-detail-placeholder">
            <i class="fa-solid fa-shield-halved" />
            <span>请在左侧选择一个举报记录查看详情</span>
          </div>

          <!-- Detail Content -->
          <div v-else class="mr-detail-content">
            <!-- Mobile Back Bar -->
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
                <!-- 举报通过时显示封禁处罚结果 -->
                <div v-if="selectedReport.type === 'report'" class="mr-penalty-box">
                  <div class="mr-penalty-box__row">
                    <i class="fa-solid fa-gavel" />
                    <span>
                      已对被举报用户执行第 {{ banCount(selectedReport) }} 次封禁，封禁
                      <strong>{{ banDuration(selectedReport) }} 天</strong>
                    </span>
                  </div>
                  <div v-if="selectedReport.admin_notes" class="mr-penalty-box__reason">
                    封禁理由：{{ selectedReport.admin_notes }}
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

            <!-- Admin Notes（仅驳回时显示独立说明卡片） -->
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
                  :avatar-url="null"
                  :gender="null"
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
    </div>
  </div>

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
</style>
