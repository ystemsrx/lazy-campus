<script setup lang="ts">
import { Clock } from 'lucide-vue-next'

import type { MyTask } from '../../composables/task-management/useTaskManagement'
import { getTaskIcon } from '../../utils/taskIcons'

defineProps<{
  tasks: MyTask[]
  statusOf: (status: string) => { label: string; cls: string }
  isExpired: (iso: string) => boolean
  formatShort: (iso: string) => string
}>()

const emit = defineEmits<{
  (e: 'openTask', task: MyTask): void
}>()
</script>

<template>
  <div class="tm-task-grid">
    <div
      v-for="(task, idx) in tasks"
      :key="`grid-${task.myRole}-${task.id}`"
      class="tm-task-card"
      :style="{ '--i': idx }"
      @click="emit('openTask', task)"
    >
      <div class="tm-task-card__header">
        <div class="tm-task-card__icon" :style="{ backgroundColor: getTaskIcon(task.icon).bg }">
          <component :is="getTaskIcon(task.icon).component" :size="22" :style="{ color: getTaskIcon(task.icon).color }" />
        </div>

        <div class="tm-task-card__info">
          <h3>{{ task.title }}</h3>
          <span class="tm-task-card__role">
            {{ task.myRole === 'publisher' && task.assignee_display_name
              ? '接单人: ' + task.assignee_display_name
              : task.myRole === 'assignee'
                ? '发布人: ' + task.publisher_display_name
                : '暂无接单人' }}
          </span>
        </div>

        <span class="badge" :class="statusOf(task.status).cls">{{ statusOf(task.status).label }}</span>
      </div>

      <p class="tm-task-card__desc">{{ task.description }}</p>

      <div class="tm-task-card__footer">
        <div class="tm-task-card__metas">
          <div v-if="task.deadline" class="tm-task-card__meta">
            <Clock :size="14" />
            <span :class="{ 'tm-danger': isExpired(task.deadline) }">
              {{ isExpired(task.deadline) ? '已过期' : formatShort(task.deadline) }}
            </span>
          </div>
          <div v-if="task.location" class="tm-task-card__meta">
            <span>{{ task.location }}</span>
          </div>
        </div>
        <span class="tm-task-card__price">¥{{ task.price }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
@keyframes tm-card-in {
  from {
    opacity: 0;
    transform: translateY(16px);
  }

  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.tm-task-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
  padding-bottom: 16px;
}

.tm-task-card {
  background: #ffffff;
  padding: 24px;
  border-radius: 24px;
  border: 1px solid rgba(0, 0, 0, 0.03);
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.04);
  display: flex;
  flex-direction: column;
  cursor: pointer;
  transition: all 0.3s var(--ease);
  animation: tm-card-in 0.45s var(--ease) both;
  animation-delay: calc(var(--i, 0) * 60ms);
}

@media (hover: hover) {
  .tm-task-card:hover {
    box-shadow: 0 8px 30px rgba(0, 0, 0, 0.1);
    transform: translateY(-2px);
  }
}

.tm-task-card__header {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  margin-bottom: 14px;
}

.tm-task-card__icon {
  width: 48px;
  height: 48px;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.tm-task-card__info {
  flex: 1;
  min-width: 0;
}

.tm-task-card__info h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  color: var(--c-text);
  line-height: 1.3;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.tm-task-card__role {
  font-size: 12px;
  color: var(--c-text-muted);
  margin-top: 2px;
  display: block;
}

.tm-task-card__desc {
  color: var(--c-text-secondary);
  font-size: 14px;
  line-height: 1.6;
  margin: 0 0 16px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  flex: 1;
}

.tm-task-card__footer {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  margin-top: auto;
}

.tm-task-card__metas {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.tm-task-card__meta {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--c-text-muted);
  font-weight: 500;
}

.tm-task-card__price {
  font-size: 20px;
  font-weight: 700;
  color: var(--c-accent);
}

.tm-danger {
  color: var(--c-danger) !important;
  font-weight: 600;
}

@media (max-width: 900px) {
  .tm-task-grid {
    display: none;
  }
}
</style>
