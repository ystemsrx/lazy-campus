<script setup lang="ts">
import HomeDrawer from './ui/HomeDrawer.vue'
import type { Report } from '../../types/api'

defineProps<{
  modelValue: boolean
  myReports: Report[]
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
}>()

function reportStatusLabel(status: string) {
  return status === 'pending' ? '待审核' : status === 'approved' ? '已通过' : '已驳回'
}

function reportTypeLabel(type: string) {
  return type === 'report' ? '举报' : '申诉'
}
</script>

<template>
  <HomeDrawer
    :model-value="modelValue"
    title="我的举报"
    body-class="hv-report-body"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <div v-if="myReports.length" class="hv-record-list">
      <div v-for="r in myReports" :key="r.id" class="card hv-report-item">
        <div class="hv-record__top">
          <span class="badge badge-default">{{ reportTypeLabel(r.type) }}</span>
          <span
            class="badge"
            :class="r.status === 'pending' ? 'badge-amber' : r.status === 'approved' ? 'badge-green' : 'badge-red'"
          >
            {{ reportStatusLabel(r.status) }}
          </span>
        </div>
        <p class="hv-report-item__reason">{{ r.reason }}</p>
      </div>
    </div>
    <p v-else class="hv-empty-text">暂无举报记录</p>
  </HomeDrawer>
</template>

<style scoped>
.hv-report-body {
  padding: 20px 24px;
}

.hv-record-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.hv-record__top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

.hv-report-item {
  padding: 14px 16px !important;
}

.hv-report-item__reason {
  margin: 6px 0 0;
  color: var(--c-text-secondary);
  font-size: var(--text-sm);
}

.hv-empty-text {
  color: var(--c-text-muted);
  font-size: var(--text-sm);
  padding: 20px 0;
}
</style>
