<script setup lang="ts">
import { ClipboardList } from 'lucide-vue-next'
import type { ComponentPublicInstance } from 'vue'

import type {
  MyTask,
  TaskTimelineGroup,
} from '../../composables/task-management/useTaskManagement'
import TaskManagementDashboardSkeleton from './TaskManagementDashboardSkeleton.vue'
import TaskManagementRoleSwitcher from './TaskManagementRoleSwitcher.vue'
import TaskManagementStatusTabs from './TaskManagementStatusTabs.vue'
import TaskManagementTaskGrid from './TaskManagementTaskGrid.vue'
import TaskManagementTimeline from './TaskManagementTimeline.vue'

const props = defineProps<{
  loading: boolean
  activeRole: 'assignee' | 'publisher'
  activeStatus: 'pending' | 'progress' | 'completed'
  assigneeTotal: number
  assigneeProgress: number
  publisherTotal: number
  publisherPending: number
  currentTasks: MyTask[]
  displayedTasks: MyTask[]
  taskGroups: TaskTimelineGroup[]
  hasMore: boolean
  loadingMore: boolean
  emptyText: string
  statusOf: (status: string) => { label: string; cls: string }
  isExpired: (iso: string) => boolean
  formatShort: (iso: string) => string
  setSentinelRef: (el: Element | ComponentPublicInstance | null) => void
}>()

const emit = defineEmits<{
  (e: 'update:activeRole', value: 'assignee' | 'publisher'): void
  (e: 'update:activeStatus', value: 'pending' | 'progress' | 'completed'): void
  (e: 'openTask', task: MyTask): void
}>()
</script>

<template>
  <TaskManagementDashboardSkeleton v-if="loading" />

  <template v-else>
    <TaskManagementRoleSwitcher
      :model-value="activeRole"
      :assignee-total="assigneeTotal"
      :assignee-progress="assigneeProgress"
      :publisher-total="publisherTotal"
      :publisher-pending="publisherPending"
      @update:model-value="emit('update:activeRole', $event)"
    />

    <TaskManagementStatusTabs
      :active-role="activeRole"
      :model-value="activeStatus"
      :publisher-pending="publisherPending"
      @update:model-value="emit('update:activeStatus', $event)"
    />

    <template v-if="currentTasks.length">
      <TaskManagementTaskGrid
        :tasks="displayedTasks"
        :status-of="statusOf"
        :is-expired="isExpired"
        :format-short="formatShort"
        @open-task="emit('openTask', $event)"
      />

      <TaskManagementTimeline
        :groups="taskGroups"
        :status-of="statusOf"
        :is-expired="isExpired"
        :format-short="formatShort"
        @open-task="emit('openTask', $event)"
      />
    </template>

    <div v-if="hasMore && currentTasks.length" :ref="props.setSentinelRef" class="tm-tl-sentinel">
      <div v-if="loadingMore" class="spinner"></div>
    </div>

    <div v-if="!currentTasks.length" class="tm-empty">
      <ClipboardList :size="48" />
      <h3>暂无任务</h3>
      <p>{{ emptyText }}</p>
    </div>
  </template>
</template>

<style scoped>
.tm-tl-sentinel {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  min-height: 60px;
}

.tm-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 64px 20px;
  color: var(--c-text-muted);
  text-align: center;
}

.tm-empty h3 {
  margin: 16px 0 4px;
  font-size: 18px;
  color: var(--c-text-secondary);
}

.tm-empty p {
  margin: 0;
  font-size: 14px;
}
</style>
