<script setup lang="ts">
import { Clock } from 'lucide-vue-next'

import type {
  MyTask,
  TaskTimelineGroup,
} from '../../composables/task-management/useTaskManagement'
import { getTaskIcon } from '../../utils/taskIcons'

defineProps<{
  groups: TaskTimelineGroup[]
  statusOf: (status: string) => { label: string; cls: string }
  isExpired: (iso: string) => boolean
  formatShort: (iso: string) => string
}>()

const emit = defineEmits<{
  (e: 'openTask', task: MyTask): void
}>()
</script>

<template>
  <div class="tm-timeline">
    <div class="tm-tl-header">
      <div class="tm-tl-date-col">日期</div>
      <div class="tm-tl-line-col"><div class="tm-tl-header-line"></div></div>
      <div class="tm-tl-content-col">任务</div>
    </div>

    <div v-for="(group, gi) in groups" :key="group.dateKey" class="tm-tl-row">
      <div class="tm-tl-date">
        <span v-if="group.showMonth" class="tm-tl-month">{{ group.month }}</span>
        <h2 :class="{ 'tm-tl-date--today': group.isToday }">{{ group.dateNum }}</h2>
        <span class="tm-tl-weekday">{{ group.weekday }}</span>
      </div>

      <div class="tm-tl-node">
        <div class="tm-tl-line" :class="{ 'tm-tl-line--last': gi === groups.length - 1 }"></div>
        <div class="tm-tl-dot" :class="{ 'tm-tl-dot--today': group.isToday }"></div>
      </div>

      <div class="tm-tl-cards">
        <div
          v-for="task in group.tasks"
          :key="`${task.myRole}-${task.id}`"
          class="tm-tl-card"
          :style="{ '--i': task._animIdx }"
          @click="emit('openTask', task)"
        >
          <div class="tm-tl-card__top">
            <div class="tm-tl-card__left">
              <h3 class="tm-tl-card__title">{{ task.title }}</h3>
              <p class="tm-tl-card__desc">{{ task.description }}</p>
            </div>
            <div class="tm-tl-card__icon" :style="{ backgroundColor: getTaskIcon(task.icon).bg }">
              <component :is="getTaskIcon(task.icon).component" :size="22" :style="{ color: getTaskIcon(task.icon).color }" />
            </div>
          </div>

          <div class="tm-tl-card__meta">
            <span class="badge" :class="statusOf(task.status).cls">{{ statusOf(task.status).label }}</span>
            <span v-if="task.deadline" class="tm-tl-card__deadline" :class="{ 'tm-danger': isExpired(task.deadline) }">
              <Clock :size="13" />
              {{ isExpired(task.deadline) ? '已过期' : formatShort(task.deadline) }}
            </span>
            <span class="tm-tl-card__price-inline">¥{{ task.price }}</span>
          </div>
        </div>
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

.tm-timeline {
  max-width: 800px;
  display: none;
}

.tm-tl-header {
  display: grid;
  grid-template-columns: 80px 40px 1fr;
  gap: 0;
  margin-bottom: 20px;
}

.tm-tl-date-col,
.tm-tl-content-col {
  font-size: 12px;
  font-weight: 600;
  color: var(--c-text-muted);
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.tm-tl-date-col {
  text-align: right;
  padding-right: 16px;
}

.tm-tl-content-col {
  padding-left: 16px;
}

.tm-tl-line-col {
  display: flex;
  justify-content: center;
  position: relative;
}

.tm-tl-header-line {
  position: absolute;
  top: 20px;
  bottom: -20px;
  width: 2px;
  background: var(--c-accent-soft);
}

.tm-tl-row {
  display: grid;
  grid-template-columns: 80px 40px 1fr;
  gap: 0;
}

.tm-tl-date {
  text-align: right;
  padding-right: 16px;
  padding-top: 8px;
}

.tm-tl-date h2 {
  font-size: 32px;
  font-weight: 800;
  letter-spacing: -0.02em;
  color: var(--c-text);
  line-height: 1;
  margin: 0;
}

.tm-tl-date--today {
  color: var(--c-accent) !important;
}

.tm-tl-month {
  font-size: 11px;
  color: var(--c-text-muted);
  font-weight: 500;
  display: block;
  margin-bottom: 2px;
}

.tm-tl-weekday {
  font-size: 12px;
  color: var(--c-text-muted);
  font-weight: 500;
  margin-top: 4px;
  display: block;
}

.tm-tl-node {
  position: relative;
  display: flex;
  justify-content: center;
}

.tm-tl-line {
  position: absolute;
  top: 0;
  bottom: -48px;
  width: 2px;
  background: var(--c-accent-soft);
}

.tm-tl-line--last {
  bottom: 0;
  height: 100%;
}

.tm-tl-dot {
  position: relative;
  top: 20px;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 3px solid var(--c-accent);
  background: #ffffff;
  z-index: 1;
  box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.1);
  flex-shrink: 0;
}

.tm-tl-dot--today {
  border-color: #10b981;
  box-shadow: 0 0 0 4px rgba(16, 185, 129, 0.15);
}

.tm-tl-cards {
  padding-left: 16px;
  padding-bottom: 48px;
  padding-top: 4px;
}

.tm-tl-card {
  display: flex;
  flex-direction: column;
  gap: 10px;
  background: #ffffff;
  border-radius: 16px;
  padding: 18px 20px;
  margin-bottom: 12px;
  border: 1px solid rgba(0, 0, 0, 0.04);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.03);
  cursor: pointer;
  transition: all 0.25s var(--ease);
  animation: tm-card-in 0.45s var(--ease) both;
  animation-delay: calc(var(--i, 0) * 60ms);
}

.tm-tl-card:last-child {
  margin-bottom: 0;
}

.tm-tl-card__top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
}

@media (hover: hover) {
  .tm-tl-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 30px rgba(0, 0, 0, 0.1);
    border-color: var(--c-accent);
  }
}

.tm-tl-card__left {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.tm-tl-card__title {
  font-size: 15px;
  font-weight: 600;
  color: var(--c-text);
  margin: 0;
  line-height: 1.3;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.tm-tl-card__desc {
  font-size: 13px;
  color: var(--c-text-secondary);
  margin: 0;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.tm-tl-card__meta {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.tm-tl-card__deadline {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--c-text-muted);
  font-weight: 500;
}

.tm-tl-card__price-inline {
  font-size: 15px;
  font-weight: 700;
  color: var(--c-accent);
  margin-left: auto;
}

.tm-tl-card__icon {
  width: 46px;
  height: 46px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.tm-danger {
  color: var(--c-danger) !important;
  font-weight: 600;
}

@media (max-width: 900px) {
  .tm-timeline {
    display: block;
    max-width: none;
  }

  .tm-tl-header {
    grid-template-columns: 44px 24px 1fr;
    margin-bottom: 12px;
  }

  .tm-tl-row {
    grid-template-columns: 44px 24px 1fr;
  }

  .tm-tl-date {
    padding-right: 6px;
  }

  .tm-tl-date h2 {
    font-size: 22px;
  }

  .tm-tl-weekday {
    font-size: 10px;
  }

  .tm-tl-cards {
    padding-left: 8px;
    padding-bottom: 32px;
  }

  .tm-tl-card {
    padding: 14px;
    border-radius: 14px;
    gap: 8px;
  }

  .tm-tl-card__top {
    gap: 10px;
  }

  .tm-tl-card__title {
    font-size: 14px;
  }

  .tm-tl-card__desc {
    font-size: 12px;
    -webkit-line-clamp: 1;
  }

  .tm-tl-card__icon {
    width: 36px;
    height: 36px;
    border-radius: 10px;
  }

  .tm-tl-card__price-inline {
    font-size: 14px;
  }
}
</style>
