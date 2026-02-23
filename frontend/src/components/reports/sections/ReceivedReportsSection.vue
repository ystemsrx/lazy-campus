<script setup lang="ts">
import type { Report } from '../../../types/api'
import PenaltyRecordCard from '../presentation/PenaltyRecordCard.vue'
import ReceivedPenaltyDetail from '../presentation/ReceivedPenaltyDetail.vue'
import { reportDateOnly } from '../../../utils/reports'
import { formatFull } from '../../../utils/time'

defineProps<{
  reports: Report[]
  selectedReceivedId: number | null
  selectedReceived: Report | null
  activePenaltyId: number | null
  hasPendingAppeal: boolean
  hasAnyBan: boolean
}>()

const emit = defineEmits<{
  'select-received': [id: number]
  'deselect-received': []
  'preview-image': [src: string]
  'open-appeal': []
}>()
</script>

<template>
  <div class="mr-layout">
    <div
      class="mr-list-panel"
      :class="{ 'mr-list-panel--hidden': selectedReceivedId !== null }"
    >
      <div class="mr-list-header">
        <h2 class="mr-list-title">处罚记录</h2>
      </div>

      <div class="mr-list-body">
        <div v-if="reports.length === 0" class="mr-empty">
          <i class="fa-solid fa-check-circle" />
          <span>暂无处罚记录，继续保持良好表现！</span>
        </div>

        <div v-else class="mr-list-items">
          <PenaltyRecordCard
            v-for="report in reports"
            :key="report.id"
            :report="report"
            :selected="selectedReceivedId === report.id"
            :active-penalty="report.id === activePenaltyId"
            :date-text="reportDateOnly(report.created_at)"
            @select="emit('select-received', report.id)"
          />
        </div>
      </div>
    </div>

    <div
      class="mr-detail-panel"
      :class="{ 'mr-detail-panel--hidden': selectedReceivedId === null }"
    >
      <div v-if="!selectedReceived" class="mr-detail-placeholder">
        <i class="fa-solid fa-gavel" />
        <span>请在左侧选择一条处罚记录查看详情</span>
      </div>

      <ReceivedPenaltyDetail
        v-else
        :report="selectedReceived"
        :created-at-text="formatFull(selectedReceived.created_at)"
        :is-active-penalty="selectedReceived.id === activePenaltyId"
        :has-pending-appeal="hasPendingAppeal"
        :has-any-ban="hasAnyBan"
        @back="emit('deselect-received')"
        @preview-image="emit('preview-image', $event)"
        @open-appeal="emit('open-appeal')"
      />
    </div>
  </div>
</template>
