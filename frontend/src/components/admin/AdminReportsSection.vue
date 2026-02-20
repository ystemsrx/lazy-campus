<script setup lang="ts">
import { proxyRefs } from 'vue'

import AppDropdown from '../AppDropdown.vue'
import AdminReviewModal from './AdminReviewModal.vue'
import AdminTaskSnapshotDrawer from './AdminTaskSnapshotDrawer.vue'
import type { AdminReportsModel } from '../../composables/admin/useAdminReports'

const props = defineProps<{
  model: AdminReportsModel
}>()

const vm = proxyRefs(props.model)
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
          <a
            v-if="report.task_id"
            class="av-task-link"
            @click.prevent="vm.openSnapshot(report.task_id)"
          >
            <i class="fa-solid fa-arrow-up-right-from-square av-task-link__icon"></i>
            任务 #{{ report.task_id }}
          </a>
          <span v-else class="av-report-type">账号申诉</span>
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
            <span class="av-report-card__label">证据</span>
            <span class="av-report-card__text">{{ report.evidence }}</span>
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
    :ban-reason="vm.reviewBanReason"
    :submitting="vm.reviewSubmitting"
    :ban-days="vm.BAN_DAYS"
    @update:ban-reason="vm.reviewBanReason = $event"
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
</template>

<style scoped>
.av-section {
  padding: 0;
}

.av-report-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
  gap: 16px;
}

.av-report-subtabs {
  display: flex;
  gap: 4px;
  background: var(--c-bg-secondary, #f1f5f9);
  border-radius: var(--radius-md);
  padding: 3px;
}

.av-report-subtab {
  padding: 7px 18px;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--c-text-muted);
  font-size: var(--text-sm);
  font-weight: 500;
  cursor: pointer;
  transition: all var(--dur-fast) var(--ease);
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
  gap: 12px;
  max-width: 700px;
}

.av-report-card__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.av-task-link {
  font-weight: 600;
  color: var(--c-accent);
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 5px;
  transition: color var(--dur-fast) var(--ease);
}

.av-task-link:hover {
  color: #4338ca;
  text-decoration: underline;
}

.av-task-link__icon {
  font-size: 11px;
}

.av-report-type {
  font-weight: 600;
  color: var(--c-text-muted);
}

.av-report-card__body {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.av-report-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--text-sm);
  margin-bottom: 4px;
}

.av-report-table th,
.av-report-table td {
  padding: 6px 10px;
  text-align: left;
  border-bottom: 1px solid var(--c-border);
}

.av-report-table th {
  color: var(--c-text-muted);
  font-weight: 500;
  background: var(--c-bg-secondary);
}

.av-report-table td:first-child {
  color: var(--c-text-muted);
  white-space: nowrap;
}

.av-report-card__col-row {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
}

.av-report-card__label {
  color: var(--c-text-muted);
  min-width: 80px;
  flex-shrink: 0;
}

.av-report-card__text {
  color: var(--c-text-secondary);
}

.av-report-card__actions {
  display: flex;
  gap: 8px;
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid var(--c-border-light);
}

.av-empty {
  text-align: center;
  color: var(--c-text-muted);
  padding: 48px 20px;
}

.av-empty__icon {
  font-size: 36px;
  display: block;
  margin-bottom: 12px;
  color: var(--c-border);
}
</style>
