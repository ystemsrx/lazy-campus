<script setup lang="ts">
import type { Report } from '../../../types/api'
import type { ReportsTabType } from '../../../composables/reports/useMyReportsData'
import { reportDateOnly, reportDisplayName, reportStatusIcon, reportStatusLabel, reportTypeLabel } from '../../../utils/reports'
import { formatFull } from '../../../utils/time'
import ReportRecordCard from '../presentation/ReportRecordCard.vue'
import SubmittedReportDetail from '../presentation/SubmittedReportDetail.vue'

defineProps<{
  tabs: ReadonlyArray<{ id: ReportsTabType; label: string }>
  activeTab: ReportsTabType
  tabIndex: number
  reports: Report[]
  selectedReportId: number | null
  selectedReport: Report | null
}>()

const emit = defineEmits<{
  'update:active-tab': [tab: ReportsTabType]
  'select-report': [id: number]
  'deselect-report': []
  'preview-image': [src: string]
}>()
</script>

<template>
  <div class="mr-layout">
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
          v-for="tab in tabs"
          :key="tab.id"
          class="mr-tab"
          :class="activeTab === tab.id ? `mr-tab--active-${tab.id}` : ''"
          @click="emit('update:active-tab', tab.id)"
        >
          {{ tab.label }}
        </button>
      </div>

      <div class="mr-list-body">
        <div v-if="reports.length === 0" class="mr-empty">
          <i class="fa-solid fa-file-lines" />
          <span>暂无相关举报记录</span>
        </div>

        <div v-else class="mr-list-items">
          <ReportRecordCard
            v-for="report in reports"
            :key="report.id"
            :report="report"
            :selected="selectedReportId === report.id"
            :status-label="reportStatusLabel(report.status)"
            :status-icon="reportStatusIcon(report.status)"
            :type-label="reportTypeLabel(report.type)"
            :display-name="reportDisplayName(report)"
            :date-text="reportDateOnly(report.created_at)"
            @select="emit('select-report', report.id)"
          />
        </div>
      </div>
    </div>

    <div
      class="mr-detail-panel"
      :class="{ 'mr-detail-panel--hidden': selectedReportId === null }"
    >
      <div v-if="!selectedReport" class="mr-detail-placeholder">
        <i class="fa-solid fa-shield-halved" />
        <span>请在左侧选择一个举报记录查看详情</span>
      </div>

      <SubmittedReportDetail
        v-else
        :report="selectedReport"
        :display-name="reportDisplayName(selectedReport)"
        :type-label="reportTypeLabel(selectedReport.type)"
        :created-at-text="formatFull(selectedReport.created_at)"
        @back="emit('deselect-report')"
        @preview-image="emit('preview-image', $event)"
      />
    </div>
  </div>
</template>
