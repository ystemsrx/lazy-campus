<script setup lang="ts">
import { proxyRefs, ref } from 'vue'

import AppDropdown from '../AppDropdown.vue'
import AdminChatHistoryDrawer from './AdminChatHistoryDrawer.vue'
import AdminReviewModal from './AdminReviewModal.vue'
import AdminTaskSnapshotDrawer from './AdminTaskSnapshotDrawer.vue'
import type { AdminReportsModel } from '../../composables/admin/useAdminReports'

const props = defineProps<{
  model: AdminReportsModel
}>()

const vm = proxyRefs(props.model)
const adminLightboxSrc = ref<string | null>(null)
</script>

<template>
  <section class="av-section">
    <div class="av-report-toolbar">
      <div class="av-report-subtabs">
        <button
          class="av-report-subtab"
          :class="{ 'av-report-subtab--active': vm.reportSubTab === 'report' }"
          @click="vm.reportSubTab = 'report'"
        >
          <i class="fa-solid fa-flag"></i>
          举报
        </button>
        <button
          class="av-report-subtab"
          :class="{ 'av-report-subtab--active': vm.reportSubTab === 'appeal' }"
          @click="vm.reportSubTab = 'appeal'"
        >
          <i class="fa-solid fa-hand"></i>
          申诉
        </button>
      </div>
      <AppDropdown
        v-model="vm.reportStatusFilter"
        :options="vm.STATUS_OPTIONS"
        width="auto"
        min-width="110px"
      />
    </div>

    <div v-if="vm.reports.length" class="av-report-list">
      <div v-for="report in vm.reports" :key="report.id" class="card av-report-card">
        <div class="av-report-card__header">
          <div class="av-report-card__header-left">
            <a
              v-if="report.task_id"
              class="av-task-link"
              @click.prevent="vm.openSnapshot(report.task_id)"
            >
              <i class="fa-solid fa-arrow-up-right-from-square av-task-link__icon"></i>
              任务 #{{ report.task_id }}
            </a>
            <span v-else class="av-report-type">{{ report.type === 'appeal' ? '账号申诉' : '账号举报' }}</span>
            <button
              v-if="report.type === 'report'"
              class="btn btn-ghost btn-xs av-chat-history-btn"
              @click="vm.openChatHistory(report.id)"
            >
              <i class="fa-regular fa-comment-dots"></i>
              查看聊天记录
            </button>
          </div>
          <span class="badge" :class="vm.reportStatusClass(report.status)">
            {{ vm.reportStatusLabel(report.status) }}
          </span>
        </div>

        <div class="av-report-card__body">
          <table class="av-report-table">
            <thead>
              <tr>
                <th>类型</th>
                <th>账号</th>
                <th>姓名</th>
                <th>昵称</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="vm.reportSubTab === 'report'">
                <td>举报用户</td>
                <td>{{ report.reporter_account || '-' }}</td>
                <td>{{ report.reporter_name || '-' }}</td>
                <td>{{ report.reporter_nickname || '-' }}</td>
              </tr>
              <tr>
                <td>{{ vm.reportSubTab === 'report' ? '被举报用户' : '申诉用户' }}</td>
                <td>
                  {{ (vm.reportSubTab === 'report' ? report.reported_user_account : report.reporter_account) || '-' }}
                </td>
                <td>
                  {{ (vm.reportSubTab === 'report' ? report.reported_user_name : report.reporter_name) || '-' }}
                </td>
                <td>
                  {{ (vm.reportSubTab === 'report' ? report.reported_user_nickname : report.reporter_nickname) || '-' }}
                </td>
              </tr>
            </tbody>
          </table>

          <div class="av-report-card__col-row">
            <span class="av-report-card__label">{{ vm.reportSubTab === 'report' ? '举报原因' : '申诉理由' }}</span>
            <span class="av-report-card__text">{{ report.reason }}</span>
          </div>
          <div v-if="report.evidence" class="av-report-card__col-row">
            <span class="av-report-card__label">补充说明</span>
            <span class="av-report-card__text">{{ report.evidence }}</span>
          </div>
          <div v-if="report.images?.length" class="av-report-card__col-row">
            <span class="av-report-card__label">截图证据</span>
            <div class="av-report-imgs">
              <img
                v-for="(src, i) in report.images"
                :key="i"
                :src="src"
                class="av-report-img"
                alt="证据截图"
                @click="adminLightboxSrc = src"
              />
            </div>
          </div>
        </div>

        <div v-if="report.status === 'pending'" class="av-report-card__actions">
          <button class="btn btn-success btn-sm" @click="vm.handleReview(report, 'approved')">
            <i class="fa-solid fa-check"></i>
            通过
          </button>
          <button class="btn btn-outline btn-sm" @click="vm.handleReview(report, 'rejected')">
            <i class="fa-solid fa-xmark"></i>
            驳回
          </button>
        </div>
      </div>
    </div>
    <div v-else class="av-empty">
      <i class="fa-regular fa-folder-open av-empty__icon"></i>
      {{ vm.reportSubTab === 'report' ? '暂无举报数据' : '暂无申诉数据' }}
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
    <Transition name="av-lb">
      <div v-if="adminLightboxSrc" class="av-lightbox" @click="adminLightboxSrc = null">
        <img :src="adminLightboxSrc" class="av-lightbox__img" alt="证据截图" />
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.av-section {
  padding: 0;
}

.av-report-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
  gap: 16px;
}

.av-report-subtabs {
  display: flex;
  gap: 4px;
  background: #f1f5f9;
  border-radius: var(--radius-lg);
  padding: 4px;
}

.av-report-subtab {
  padding: 8px 20px;
  border: none;
  border-radius: var(--radius-md);
  background: transparent;
  color: #94a3b8;
  font-size: var(--text-sm);
  font-weight: 500;
  cursor: pointer;
  transition: all 200ms var(--ease);
  font-family: var(--font-sans);
  display: flex;
  align-items: center;
  gap: 6px;
}

.av-report-subtab:hover {
  color: var(--c-text);
}

.av-report-subtab--active {
  background: #fff;
  color: var(--c-accent);
  box-shadow: var(--shadow-sm);
}

.av-report-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
  max-width: 720px;
}

.av-report-card {
  border-radius: var(--radius-2xl) !important;
  border: 1px solid rgba(226, 232, 240, 0.6) !important;
  box-shadow: var(--shadow-card) !important;
  padding: 24px !important;
}

.av-report-card__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}

.av-report-card__header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.av-chat-history-btn {
  font-size: 12px;
  color: #94a3b8;
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border-radius: var(--radius-sm);
  transition: color 200ms var(--ease), background 200ms var(--ease);
}

.av-chat-history-btn:hover {
  color: var(--c-accent);
  background: rgba(59, 130, 246, 0.06);
}

.av-task-link {
  font-weight: 600;
  color: var(--c-accent);
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 5px;
  transition: color 200ms var(--ease);
}

.av-task-link:hover {
  color: #2563eb;
  text-decoration: underline;
}

.av-task-link__icon {
  font-size: 11px;
}

.av-report-type {
  font-weight: 600;
  color: #94a3b8;
}

.av-report-card__body {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.av-report-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--text-sm);
  margin-bottom: 4px;
  border-radius: var(--radius-md);
  overflow: hidden;
}

.av-report-table th,
.av-report-table td {
  padding: 8px 12px;
  text-align: left;
  border-bottom: 1px solid rgba(226, 232, 240, 0.6);
}

.av-report-table th {
  color: #94a3b8;
  font-weight: 500;
  background: #f8fafc;
  font-size: 12px;
}

.av-report-table td:first-child {
  color: #94a3b8;
  white-space: nowrap;
}

.av-report-card__col-row {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 3px;
}

.av-report-card__label {
  color: #94a3b8;
  min-width: 80px;
  flex-shrink: 0;
  font-size: 12px;
  font-weight: 500;
}

.av-report-card__text {
  color: var(--c-text-secondary);
  font-size: 13px;
  background: #f8fafc;
  padding: 10px 14px;
  border-radius: var(--radius-lg);
  border: 1px solid rgba(226, 232, 240, 0.6);
  line-height: 1.6;
  width: 100%;
}

.av-report-card__actions {
  display: flex;
  gap: 10px;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid rgba(241, 245, 249, 0.8);
}

.av-report-card__actions .btn {
  border-radius: var(--radius-lg);
  padding: 10px 20px;
}

.av-empty {
  text-align: center;
  color: #94a3b8;
  padding: 60px 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.av-empty__icon {
  font-size: 40px;
  display: block;
  margin-bottom: 8px;
  color: #cbd5e1;
}

.av-report-imgs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 4px;
}

.av-report-img {
  width: 80px;
  height: 80px;
  object-fit: cover;
  border-radius: var(--radius-md);
  border: 1px solid rgba(226, 232, 240, 0.6);
  cursor: zoom-in;
  transition: opacity 200ms var(--ease);
}

.av-report-img:hover {
  opacity: 0.85;
}

.av-lightbox {
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

.av-lightbox__img {
  max-width: 100%;
  max-height: 100%;
  border-radius: var(--radius-lg);
  box-shadow: 0 8px 40px rgba(0, 0, 0, 0.5);
  object-fit: contain;
}

.av-lb-enter-active,
.av-lb-leave-active {
  transition: opacity 0.2s ease;
}

.av-lb-enter-from,
.av-lb-leave-to {
  opacity: 0;
}
</style>
