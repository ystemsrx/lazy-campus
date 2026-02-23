<script setup lang="ts">
import { computed, proxyRefs, ref, watch } from 'vue'

import AdminChatHistoryDrawer from './AdminChatHistoryDrawer.vue'
import AdminReviewModal from './AdminReviewModal.vue'
import AdminTaskSnapshotDrawer from './AdminTaskSnapshotDrawer.vue'
import HomeAvatar from '../home/ui/HomeAvatar.vue'
import type { AdminReportsModel } from '../../composables/admin/useAdminReports'
import type { Report } from '../../types/api'

const props = defineProps<{
  model: AdminReportsModel
}>()

const vm = proxyRefs(props.model)
const adminLightboxSrc = ref<string | null>(null)
const selectedId = ref<number | null>(null)
const searchQuery = ref('')

const isAppealView = computed(() => vm.reportSubTab === 'appeal')

const STATUS_FILTERS = [
  { key: '', label: '全部' },
  { key: 'pending', label: '待处理' },
  { key: 'approved', label: '已通过' },
  { key: 'rejected', label: '已驳回' },
]

const filteredReports = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  if (!q) return vm.reports
  return (vm.reports as Report[]).filter(r =>
    String(r.id).includes(q)
    || r.reporter_name?.toLowerCase().includes(q)
    || r.reporter_nickname?.toLowerCase().includes(q)
    || r.reporter_account?.toLowerCase().includes(q)
    || r.reported_user_name?.toLowerCase().includes(q)
    || r.reported_user_nickname?.toLowerCase().includes(q)
    || r.reported_user_account?.toLowerCase().includes(q)
    || r.reason?.toLowerCase().includes(q)
    || r.evidence?.toLowerCase().includes(q),
  )
})

const selectedReport = computed<Report | null>(() =>
  selectedId.value !== null
    ? (vm.reports as Report[]).find(r => r.id === selectedId.value) ?? null
    : null,
)

watch([() => vm.reportSubTab, () => vm.reportStatusFilter], () => {
  selectedId.value = null
  searchQuery.value = ''
})

function dName(r: Report, role: 'reporter' | 'reported'): string {
  if (role === 'reporter')
    return r.reporter_nickname || r.reporter_name || r.reporter_account || '未知用户'
  return r.reported_user_nickname || r.reported_user_name || r.reported_user_account || '未知用户'
}

function avatar(r: Report, role: 'reporter' | 'reported'): string | null {
  return role === 'reporter' ? r.reporter_avatar_url : r.reported_user_avatar_url
}

function gender(r: Report, role: 'reporter' | 'reported'): 'male' | 'female' | null {
  return role === 'reporter' ? r.reporter_gender : r.reported_user_gender
}

function acct(r: Report, role: 'reporter' | 'reported'): string {
  return (role === 'reporter' ? r.reporter_account : r.reported_user_account) || '-'
}

function fmtDate(iso: string): string {
  return new Date(iso).toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })
}

function fmtDateTime(iso: string): string {
  return new Date(iso).toLocaleString('zh-CN', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit',
  })
}

function bClass(s: string) { return `rpt-badge--${s}` }

function bIcon(s: string) {
  return s === 'pending' ? 'fa-regular fa-clock'
    : s === 'approved' ? 'fa-solid fa-circle-check'
      : 'fa-solid fa-circle-xmark'
}

function bLabel(s: string) {
  return s === 'pending' ? '待处理' : s === 'approved' ? '已通过' : '已驳回'
}
</script>

<template>
  <section class="rpt-container">
    <!-- ═══ LEFT: Report List ═══ -->
    <div class="rpt-list-panel" :class="{ 'rpt-list-panel--hidden-mobile': selectedId !== null }">
      <div class="rpt-list-head">
        <!-- Subtabs -->
        <div class="rpt-subtabs">
          <div
            class="rpt-subtabs__slider"
            :class="{ 'rpt-subtabs__slider--right': vm.reportSubTab === 'appeal' }"
          ></div>
          <button
            class="rpt-subtab"
            :class="{ 'rpt-subtab--active': vm.reportSubTab === 'report' }"
            @click="vm.reportSubTab = 'report'"
          >
            <i class="fa-solid fa-flag"></i>
            举报
          </button>
          <button
            class="rpt-subtab"
            :class="{ 'rpt-subtab--active': vm.reportSubTab === 'appeal' }"
            @click="vm.reportSubTab = 'appeal'"
          >
            <i class="fa-solid fa-hand"></i>
            申诉
          </button>
        </div>

        <!-- Search -->
        <div class="rpt-search-wrap">
          <i class="fa-solid fa-magnifying-glass rpt-search-icon"></i>
          <input
            v-model="searchQuery"
            type="text"
            class="rpt-search-input"
            placeholder="搜索单号、用户或关键字..."
          />
        </div>

        <!-- Status filter buttons -->
        <div class="rpt-filters">
          <button
            v-for="f in STATUS_FILTERS"
            :key="f.key"
            class="rpt-filter-btn"
            :class="{ 'rpt-filter-btn--active': vm.reportStatusFilter === f.key }"
            @click="vm.reportStatusFilter = f.key"
          >
            {{ f.label }}
          </button>
        </div>
      </div>

      <!-- Scrollable list -->
      <div class="rpt-list-body">
        <template v-if="filteredReports.length">
          <div
            v-for="report in filteredReports"
            :key="report.id"
            class="rpt-item"
            :class="{ 'rpt-item--selected': selectedId === report.id }"
            @click="selectedId = report.id"
          >
            <div class="rpt-item__top">
              <div class="rpt-item__top-left">
                <span class="rpt-item__id">#{{ report.id }}</span>
                <span v-if="report.task_id" class="rpt-item__source rpt-item__source--task">
                  <i class="fa-solid fa-list-check"></i>
                  <span class="rpt-item__source-text">#{{ report.task_id }}{{ report.task_title ? ' · ' + report.task_title : '' }}</span>
                </span>
                <span v-else-if="report.type === 'report'" class="rpt-item__source rpt-item__source--chat">
                  <i class="fa-regular fa-comment-dots"></i>
                  广场聊天
                </span>
                <span v-else class="rpt-item__source rpt-item__source--appeal">
                  <i class="fa-solid fa-hand"></i>
                  账号申诉
                </span>
              </div>
              <span class="rpt-badge" :class="bClass(report.status)">
                <i :class="bIcon(report.status)"></i>
                {{ bLabel(report.status) }}
              </span>
            </div>
            <h3 class="rpt-item__reason">{{ report.reason }}</h3>
            <div class="rpt-item__meta">
              <div class="rpt-item__avatar">
                <HomeAvatar
                  :avatar-url="avatar(report, 'reporter')"
                  :gender="gender(report, 'reporter')"
                />
              </div>
              <span class="rpt-item__name">{{ dName(report, 'reporter') }}</span>
              <template v-if="report.type === 'report' && report.reported_user_id">
                <span class="rpt-item__arrow">→</span>
                <span class="rpt-item__name">{{ dName(report, 'reported') }}</span>
              </template>
              <span class="rpt-item__date">{{ fmtDate(report.created_at) }}</span>
            </div>
          </div>
        </template>
        <div v-else class="rpt-empty-list">
          <i class="fa-regular fa-folder-open rpt-empty-list__icon"></i>
          <p>{{ isAppealView ? '没有找到相关的申诉记录' : '没有找到相关的举报记录' }}</p>
        </div>
      </div>
    </div>

    <!-- ═══ RIGHT: Detail Panel ═══ -->
    <div class="rpt-detail-panel" :class="{ 'rpt-detail-panel--show-mobile': selectedId !== null }">
      <template v-if="selectedReport">
        <!-- Header -->
        <div class="rpt-detail-head">
          <div class="rpt-detail-head__left">
            <button class="rpt-back-btn" @click="selectedId = null">
              <i class="fa-solid fa-arrow-left"></i>
            </button>
            <div>
              <h2 class="rpt-detail-title">
                {{ isAppealView ? '申诉详情' : '举报详情' }}
                <span class="rpt-badge" :class="bClass(selectedReport.status)">
                  <i :class="bIcon(selectedReport.status)"></i>
                  {{ bLabel(selectedReport.status) }}
                </span>
              </h2>
              <p class="rpt-detail-subtitle">
                工单号: #{{ selectedReport.id }} • 提交于 {{ fmtDateTime(selectedReport.created_at) }}
              </p>
            </div>
          </div>
        </div>

        <!-- Scrollable body -->
        <div class="rpt-detail-body">
          <!-- User cards -->
          <div class="rpt-user-grid" :class="{ 'rpt-user-grid--single': isAppealView || !selectedReport.reported_user_id }">
            <div class="rpt-user-card">
              <div class="rpt-user-avatar">
                <HomeAvatar
                  :avatar-url="avatar(selectedReport, 'reporter')"
                  :gender="gender(selectedReport, 'reporter')"
                  size="lg"
                />
              </div>
              <div>
                <p class="rpt-user-role rpt-user-role--blue">{{ isAppealView ? '申诉人' : '举报人' }}</p>
                <p class="rpt-user-name">{{ dName(selectedReport, 'reporter') }}</p>
                <p class="rpt-user-sub">{{ acct(selectedReport, 'reporter') }}</p>
              </div>
            </div>

            <div v-if="!isAppealView && selectedReport.reported_user_id" class="rpt-user-card rpt-user-card--reported">
              <div class="rpt-user-card__decor"></div>
              <div class="rpt-user-avatar">
                <HomeAvatar
                  :avatar-url="avatar(selectedReport, 'reported')"
                  :gender="gender(selectedReport, 'reported')"
                  size="lg"
                />
              </div>
              <div class="rpt-user-info">
                <p class="rpt-user-role rpt-user-role--rose">被举报人</p>
                <p class="rpt-user-name">{{ dName(selectedReport, 'reported') }}</p>
                <p class="rpt-user-sub">
                  <template v-if="selectedReport.reported_user_ban_count">
                    近期被封禁 {{ selectedReport.reported_user_ban_count }} 次
                  </template>
                  <template v-else>{{ acct(selectedReport, 'reported') }}</template>
                </p>
              </div>
            </div>
          </div>

          <!-- Reason & evidence -->
          <div class="rpt-section">
            <div class="rpt-section__head">
              <i class="fa-solid fa-circle-exclamation"></i>
              <h3>{{ isAppealView ? '申诉理由与说明' : '举报事由与说明' }}</h3>
            </div>
            <div class="rpt-section__body">
              <h4 class="rpt-reason-title">{{ selectedReport.reason }}</h4>
              <p v-if="selectedReport.evidence" class="rpt-reason-desc">
                {{ selectedReport.evidence }}
              </p>
            </div>
          </div>

          <!-- Evidence images -->
          <div v-if="selectedReport.images?.length" class="rpt-section">
            <div class="rpt-section__head">
              <i class="fa-solid fa-images"></i>
              <h3>截图证据</h3>
            </div>
            <div class="rpt-section__body">
              <div class="rpt-evidence-grid">
                <div
                  v-for="(src, i) in selectedReport.images"
                  :key="i"
                  class="rpt-evidence-item"
                  @click="adminLightboxSrc = src"
                >
                  <img :src="src" alt="证据截图" />
                  <div class="rpt-evidence-overlay">
                    <span>查看大图</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Related actions: 有 task_id = 任务举报（只看快照）；无 task_id = 广场聊天举报（只看聊天记录） -->
          <div v-if="selectedReport.type === 'report'" class="rpt-related">
            <button
              v-if="selectedReport.task_id"
              class="rpt-related-btn"
              @click="vm.openSnapshot(selectedReport.task_id!)"
            >
              <i class="fa-solid fa-layer-group"></i>
              查看任务快照 #{{ selectedReport.task_id }}
            </button>
            <button
              v-else
              class="rpt-related-btn"
              @click="vm.openChatHistory(selectedReport.id)"
            >
              <i class="fa-regular fa-comment-dots"></i>
              查看聊天记录
            </button>
          </div>

          <!-- Admin notes -->
          <div v-if="selectedReport.status !== 'pending' && selectedReport.admin_notes" class="rpt-section">
            <div class="rpt-section__head">
              <i class="fa-solid fa-pen-clip"></i>
              <h3>管理员备注</h3>
            </div>
            <div class="rpt-section__body">
              <p class="rpt-reason-desc">{{ selectedReport.admin_notes }}</p>
            </div>
          </div>

          <div class="rpt-detail-spacer"></div>
        </div>

        <!-- Bottom action bar -->
        <div class="rpt-action-bar">
          <template v-if="selectedReport.status === 'pending'">
            <span class="rpt-action-hint">请仔细核对证据后做出裁决</span>
            <div class="rpt-action-btns">
              <button class="rpt-btn rpt-btn--outline" @click="vm.handleReview(selectedReport, 'rejected')">
                驳回{{ isAppealView ? '申诉' : '举报' }}
              </button>
              <button class="rpt-btn rpt-btn--primary" @click="vm.handleReview(selectedReport, 'approved')">
                {{ isAppealView ? '通过申诉' : '通过并处罚' }}
              </button>
            </div>
          </template>
          <template v-else>
            <div
              class="rpt-action-result"
              :class="selectedReport.status === 'approved' ? 'rpt-action-result--approved' : 'rpt-action-result--rejected'"
            >
              <i :class="selectedReport.status === 'approved' ? 'fa-solid fa-circle-check' : 'fa-solid fa-circle-xmark'"></i>
              <template v-if="selectedReport.status === 'approved'">
                {{ isAppealView ? '此申诉已通过，用户限制已解除' : '此举报已通过，相关处罚已生效' }}
              </template>
              <template v-else>
                {{ isAppealView ? '此申诉已被驳回' : '此举报已被驳回' }}
              </template>
            </div>
          </template>
        </div>
      </template>

      <!-- Empty state -->
      <div v-else class="rpt-empty-detail">
        <div class="rpt-empty-detail__circle">
          <i class="fa-solid fa-shield-halved"></i>
        </div>
        <h3>{{ isAppealView ? '未选择申诉条目' : '未选择举报条目' }}</h3>
        <p>请在左侧列表中选择一个{{ isAppealView ? '申诉' : '举报' }}事件以查看详细信息。</p>
      </div>
    </div>
  </section>

  <AdminReviewModal
    :show="vm.showReviewModal"
    :target="vm.reviewTarget"
    :submitting="vm.reviewSubmitting"
    @close="vm.closeReviewModal"
    @confirm="vm.confirmReportReview"
  />

  <AdminTaskSnapshotDrawer
    :show="vm.showSnapshot"
    :loading="vm.snapshotLoading"
    :snapshot="vm.snapshot"
    :task-status-map="vm.TASK_STATUS_MAP"
    @close="vm.closeSnapshot"
  />

  <AdminChatHistoryDrawer
    :show="vm.showChatHistory"
    :loading="vm.chatHistoryLoading"
    :chat-history="vm.chatHistory"
    @close="vm.closeChatHistory"
  />

  <Teleport to="body">
    <Transition name="rpt-lb">
      <div v-if="adminLightboxSrc" class="rpt-lightbox" @click="adminLightboxSrc = null">
        <img :src="adminLightboxSrc" class="rpt-lightbox__img" alt="证据截图" />
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
/* ── Layout ── */
.rpt-container {
  display: flex;
  align-items: flex-start;
  min-height: calc(100vh - 72px);
  background: transparent;
}

.rpt-list-panel {
  position: sticky;
  top: 0;
  width: 340px;
  height: calc(100vh - 72px);
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  border-right: 1px solid rgba(226, 232, 240, 0.6);
  background: #fff;
  overflow: hidden;
}

.rpt-detail-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #f8fafc;
  min-width: 0;
  min-height: calc(100vh - 72px);
}

/* ── List header ── */
.rpt-list-head {
  padding: 20px;
  border-bottom: 1px solid rgba(241, 245, 249, 0.8);
}

/* ── Subtabs ── */
.rpt-subtabs {
  position: relative;
  display: flex;
  background: #f1f5f9;
  border-radius: var(--radius-lg);
  padding: 4px;
  margin-bottom: 16px;
}

.rpt-subtabs__slider {
  position: absolute;
  top: 4px;
  left: 4px;
  width: calc(50% - 4px);
  height: calc(100% - 8px);
  background: #fff;
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  transition: transform 240ms cubic-bezier(0.4, 0, 0.2, 1);
  pointer-events: none;
}

.rpt-subtabs__slider--right {
  transform: translateX(100%);
}

.rpt-subtab {
  flex: 1;
  padding: 8px 16px;
  border: none;
  border-radius: var(--radius-md);
  background: transparent;
  color: #94a3b8;
  font-size: var(--text-sm);
  font-weight: 500;
  cursor: pointer;
  transition: color 200ms var(--ease);
  font-family: var(--font-sans);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  position: relative;
  z-index: 1;
}

.rpt-subtab:hover {
  color: var(--c-text);
}

.rpt-subtab--active {
  color: var(--c-accent);
}

/* ── Search ── */
.rpt-search-wrap {
  position: relative;
  margin-bottom: 14px;
}

.rpt-search-icon {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  color: #94a3b8;
  font-size: 13px;
  pointer-events: none;
}

.rpt-search-input {
  width: 100%;
  padding: 9px 14px 9px 34px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: var(--radius-lg);
  font-size: 13px;
  font-family: var(--font-sans);
  color: var(--c-text);
  outline: none;
  transition: border-color 200ms var(--ease), box-shadow 200ms var(--ease);
  box-sizing: border-box;
}

.rpt-search-input::placeholder {
  color: #94a3b8;
}

.rpt-search-input:focus {
  border-color: var(--c-accent);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.08);
}

/* ── Status filters ── */
.rpt-filters {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding-bottom: 2px;
}

.rpt-filter-btn {
  padding: 6px 12px;
  border-radius: var(--radius-md);
  font-size: 12px;
  font-weight: 500;
  border: 1px solid #e2e8f0;
  background: #fff;
  color: #64748b;
  cursor: pointer;
  transition: all 200ms var(--ease);
  white-space: nowrap;
  font-family: var(--font-sans);
}

.rpt-filter-btn--active {
  background: rgba(59, 130, 246, 0.06);
  color: var(--c-accent);
  border-color: rgba(59, 130, 246, 0.2);
}

/* ── List body ── */
.rpt-list-body {
  flex: 1;
  overflow-y: auto;
}

/* ── List items ── */
.rpt-item {
  padding: 14px 16px;
  cursor: pointer;
  border-left: 4px solid transparent;
  border-bottom: 1px solid rgba(241, 245, 249, 0.8);
  transition: all 150ms var(--ease);
}

.rpt-item:hover {
  background: rgba(248, 250, 252, 0.8);
}

.rpt-item--selected {
  background: rgba(59, 130, 246, 0.04);
  border-left-color: var(--c-accent);
}

.rpt-item__top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
  gap: 6px;
}

.rpt-item__top-left {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}

.rpt-item__id {
  font-size: 12px;
  font-weight: 500;
  color: #94a3b8;
  flex-shrink: 0;
}

.rpt-item__source {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 11px;
  font-weight: 500;
  padding: 2px 7px;
  border-radius: 4px;
  max-width: 130px;
  overflow: hidden;
}

.rpt-item__source i {
  font-size: 10px;
  flex-shrink: 0;
}

.rpt-item__source-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.rpt-item__source--task {
  background: rgba(59, 130, 246, 0.07);
  color: #3b82f6;
}

.rpt-item__source--chat {
  background: rgba(168, 85, 247, 0.07);
  color: #a855f7;
}

.rpt-item__source--appeal {
  background: rgba(249, 115, 22, 0.07);
  color: #f97316;
}

.rpt-item__reason {
  font-size: 13px;
  font-weight: 600;
  color: var(--c-text);
  margin: 0 0 8px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.rpt-item__meta {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #94a3b8;
}

.rpt-item__avatar {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  overflow: hidden;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.rpt-item__avatar :deep(.hv-avatar) {
  width: 20px;
  height: 20px;
}

.rpt-item__name {
  max-width: 80px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.rpt-item__arrow {
  color: #cbd5e1;
  flex-shrink: 0;
}

.rpt-item__date {
  margin-left: auto;
  color: #94a3b8;
  flex-shrink: 0;
}

/* ── Status badge ── */
.rpt-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 10px;
  border-radius: 9999px;
  font-size: 12px;
  font-weight: 500;
  border: 1px solid;
  white-space: nowrap;
  line-height: 1.4;
}

.rpt-badge i {
  font-size: 11px;
}

.rpt-badge--pending {
  background: #fffbeb;
  color: #b45309;
  border-color: #fde68a;
}

.rpt-badge--approved {
  background: #ecfdf5;
  color: #047857;
  border-color: #a7f3d0;
}

.rpt-badge--rejected {
  background: #f3f4f6;
  color: #4b5563;
  border-color: #e5e7eb;
}

/* ── Detail header ── */
.rpt-detail-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 28px;
  background: rgba(255, 255, 255, 0.9);
  border-bottom: 1px solid rgba(226, 232, 240, 0.6);
  flex-shrink: 0;
  position: sticky;
  top: 0;
  z-index: 20;
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
}

.rpt-detail-head__left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.rpt-back-btn {
  display: none;
  width: 36px;
  height: 36px;
  border: none;
  background: transparent;
  color: #64748b;
  font-size: 16px;
  border-radius: 50%;
  cursor: pointer;
  transition: all 200ms var(--ease);
  align-items: center;
  justify-content: center;
}

.rpt-back-btn:hover {
  background: #f1f5f9;
  color: var(--c-text);
}

.rpt-detail-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--c-text);
  margin: 0;
  display: flex;
  align-items: center;
  gap: 12px;
}

.rpt-detail-subtitle {
  margin: 4px 0 0;
  font-size: 12px;
  color: #94a3b8;
}

/* ── Detail body ── */
.rpt-detail-body {
  flex: 1;
  padding: 28px 28px 8px;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

/* ── User cards ── */
.rpt-user-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.rpt-user-grid--single {
  grid-template-columns: 1fr;
  max-width: 360px;
}

.rpt-user-card {
  background: #fff;
  padding: 16px;
  border-radius: var(--radius-2xl);
  border: 1px solid rgba(226, 232, 240, 0.6);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03);
  display: flex;
  align-items: center;
  gap: 14px;
  position: relative;
  overflow: hidden;
}

.rpt-user-card__decor {
  position: absolute;
  top: 0;
  right: 0;
  width: 56px;
  height: 56px;
  background: rgba(244, 63, 94, 0.05);
  border-radius: 0 0 0 100%;
}

.rpt-user-avatar {
  flex-shrink: 0;
  position: relative;
  z-index: 1;
}

.rpt-user-info {
  position: relative;
  z-index: 1;
}

.rpt-user-role {
  font-size: 12px;
  font-weight: 500;
  margin: 0 0 2px;
}

.rpt-user-role--blue {
  color: #3b82f6;
}

.rpt-user-role--rose {
  color: #f43f5e;
}

.rpt-user-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--c-text);
  margin: 0;
}

.rpt-user-sub {
  font-size: 12px;
  color: #94a3b8;
  margin: 2px 0 0;
}

/* ── Content sections ── */
.rpt-section {
  background: #fff;
  border-radius: var(--radius-2xl);
  border: 1px solid rgba(226, 232, 240, 0.6);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03);
  overflow: hidden;
}

.rpt-section__head {
  padding: 14px 20px;
  background: rgba(248, 250, 252, 0.5);
  border-bottom: 1px solid rgba(241, 245, 249, 0.8);
  display: flex;
  align-items: center;
  gap: 8px;
}

.rpt-section__head i {
  color: #64748b;
  font-size: 14px;
}

.rpt-section__head h3 {
  margin: 0;
  font-size: 13px;
  font-weight: 600;
  color: var(--c-text);
}

.rpt-section__body {
  padding: 20px;
}

.rpt-reason-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--c-text);
  margin: 0 0 12px;
}

.rpt-reason-desc {
  font-size: 13px;
  color: var(--c-text-secondary);
  line-height: 1.7;
  margin: 0;
  background: #f8fafc;
  padding: 14px 16px;
  border-radius: var(--radius-lg);
  border: 1px solid rgba(241, 245, 249, 0.8);
}

/* ── Evidence images ── */
.rpt-evidence-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.rpt-evidence-item {
  width: 100px;
  height: 100px;
  border-radius: var(--radius-lg);
  overflow: hidden;
  border: 1px solid rgba(226, 232, 240, 0.6);
  cursor: zoom-in;
  position: relative;
}

.rpt-evidence-item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 300ms var(--ease);
}

.rpt-evidence-item:hover img {
  transform: scale(1.05);
}

.rpt-evidence-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 200ms var(--ease);
}

.rpt-evidence-item:hover .rpt-evidence-overlay {
  opacity: 1;
}

.rpt-evidence-overlay span {
  color: #fff;
  font-size: 12px;
  font-weight: 500;
}

/* ── Related links ── */
.rpt-related {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.rpt-related-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 10px 16px;
  background: #fff;
  border: 1px solid rgba(226, 232, 240, 0.6);
  border-radius: var(--radius-lg);
  color: var(--c-accent);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  font-family: var(--font-sans);
  transition: all 200ms var(--ease);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03);
}

.rpt-related-btn:hover {
  background: rgba(59, 130, 246, 0.04);
  border-color: rgba(59, 130, 246, 0.2);
}

.rpt-related-btn i {
  font-size: 12px;
}

.rpt-detail-spacer {
  height: 16px;
}

/* ── Action bar ── */
.rpt-action-bar {
  padding: 16px 28px;
  background: rgba(255, 255, 255, 0.9);
  border-top: 1px solid rgba(226, 232, 240, 0.6);
  display: flex;
  align-items: center;
  justify-content: space-between;
  position: sticky;
  bottom: 0;
  z-index: 20;
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  box-shadow: 0 -4px 20px -10px rgba(0, 0, 0, 0.08);
}

.rpt-action-hint {
  font-size: 13px;
  color: #94a3b8;
}

.rpt-action-btns {
  display: flex;
  gap: 10px;
}

.rpt-btn {
  padding: 10px 22px;
  border-radius: var(--radius-lg);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  font-family: var(--font-sans);
  border: none;
  transition: all 200ms var(--ease);
}

.rpt-btn--outline {
  background: #fff;
  color: var(--c-text-secondary);
  border: 1px solid #cbd5e1;
}

.rpt-btn--outline:hover {
  background: #f8fafc;
}

.rpt-btn--primary {
  background: var(--c-accent);
  color: #fff;
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.25);
}

.rpt-btn--primary:hover {
  filter: brightness(1.06);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
}

.rpt-action-result {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px;
  border-radius: var(--radius-lg);
  font-size: 13px;
  border: 1px solid;
}

.rpt-action-result--approved {
  background: #f0fdf4;
  color: #15803d;
  border-color: #bbf7d0;
}

.rpt-action-result--approved i {
  color: #22c55e;
}

.rpt-action-result--rejected {
  background: #f8fafc;
  color: #64748b;
  border-color: #e2e8f0;
}

.rpt-action-result--rejected i {
  color: #94a3b8;
}

/* ── Empty states ── */
.rpt-empty-list {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  color: #94a3b8;
}

.rpt-empty-list__icon {
  font-size: 36px;
  color: #cbd5e1;
  margin-bottom: 12px;
}

.rpt-empty-list p {
  margin: 0;
  font-size: 13px;
}

.rpt-empty-detail {
  flex: 1;
  min-height: calc(100vh - 72px);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #94a3b8;
  background: rgba(248, 250, 252, 0.5);
}

.rpt-empty-detail__circle {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: #f1f5f9;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 20px;
}

.rpt-empty-detail__circle i {
  font-size: 32px;
  color: #cbd5e1;
}

.rpt-empty-detail h3 {
  font-size: 16px;
  font-weight: 600;
  color: #64748b;
  margin: 0 0 8px;
}

.rpt-empty-detail p {
  font-size: 13px;
  color: #94a3b8;
  max-width: 320px;
  text-align: center;
  margin: 0;
}

/* ── Lightbox ── */
.rpt-lightbox {
  position: fixed;
  inset: 0;
  z-index: 9999;
  background: rgba(0, 0, 0, 0.85);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  cursor: zoom-out;
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
}

.rpt-lightbox__img {
  max-width: 100%;
  max-height: 100%;
  border-radius: var(--radius-lg);
  box-shadow: 0 8px 40px rgba(0, 0, 0, 0.5);
  object-fit: contain;
}

.rpt-lb-enter-active,
.rpt-lb-leave-active {
  transition: opacity 0.2s ease;
}

.rpt-lb-enter-from,
.rpt-lb-leave-to {
  opacity: 0;
}

/* ── Responsive ── */
@media (max-width: 768px) {
  .rpt-container {
    flex-direction: column;
    align-items: stretch;
    min-height: auto;
  }

  .rpt-list-panel {
    position: static;
    width: 100%;
    height: auto;
    border-right: none;
    border-bottom: 1px solid rgba(226, 232, 240, 0.6);
  }

  .rpt-list-panel--hidden-mobile {
    display: none;
  }

  .rpt-detail-panel {
    display: none;
    min-height: auto;
  }

  .rpt-detail-panel--show-mobile {
    display: flex;
  }

  .rpt-back-btn {
    display: inline-flex;
  }

  .rpt-detail-head {
    padding: 14px 16px;
  }

  .rpt-detail-body {
    padding: 16px;
  }

  .rpt-action-bar {
    padding: 12px 16px;
    flex-direction: column;
    gap: 10px;
  }

  .rpt-action-hint {
    display: none;
  }

  .rpt-action-btns {
    width: 100%;
  }

  .rpt-action-btns .rpt-btn {
    flex: 1;
  }

  .rpt-user-grid {
    grid-template-columns: 1fr;
  }

  .rpt-user-grid--single {
    max-width: none;
  }

  .rpt-empty-detail {
    min-height: 60vh;
  }
}

@media (min-width: 769px) and (max-width: 1100px) {
  .rpt-list-panel {
    width: 280px;
  }
}
</style>
