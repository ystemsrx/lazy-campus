<script setup lang="ts">
import type { Task } from '../../types/api'
import { getTaskIcon } from '../../utils/taskIcons'

const props = defineProps<{
  task: Task
  statusOf: (status: string) => { label: string; cls: string }
  genderLabel: (gender: string | null) => { label: string; icon: string; cls: string } | null
  categoryName: (id: number | null) => string | null
  isExpired: (iso: string) => boolean
  formatShort: (iso: string) => string
}>()

const emit = defineEmits<{
  (e: 'select', task: Task): void
}>()
</script>

<template>
  <div
    class="card card-hover hv-task-card"
    :class="{ 'hv-task-card--pinned': task.is_pinned }"
    @click="emit('select', task)"
  >
    <div class="hv-task-card__top">
      <div class="hv-task-card__badges">
        <span class="badge" :class="statusOf(task.status).cls">{{ statusOf(task.status).label }}</span>
        <span
          v-if="task.required_gender && genderLabel(task.required_gender)"
          class="badge"
          :class="genderLabel(task.required_gender)!.cls"
        >
          <i :class="genderLabel(task.required_gender)!.icon" class="hv-task-card__gender-icon"></i>
          {{ genderLabel(task.required_gender)!.label }}
        </span>
      </div>
      <div class="hv-task-card__top-right">
        <span
          v-if="task.deadline"
          class="hv-task-card__deadline"
          :class="{ 'hv-task-card__deadline--expired': isExpired(task.deadline) }"
        >
          <i class="fa-regular fa-clock"></i>
          {{ isExpired(task.deadline) ? '已过期' : '截止 ' + formatShort(task.deadline) }}
        </span>
        <div
          class="hv-task-card__icon-wrap"
          :style="{ background: getTaskIcon(task.icon).bg }"
        >
          <component
            :is="getTaskIcon(task.icon).component"
            :size="14"
            :style="{ color: getTaskIcon(task.icon).color }"
          />
        </div>
      </div>
    </div>

    <h4 class="hv-task-card__title">{{ task.title }}</h4>
    <p class="hv-task-card__desc">{{ task.description }}</p>

    <div v-if="categoryName(task.category_id) || task.location" class="hv-task-card__tags">
      <span v-if="categoryName(task.category_id)" class="hv-task-card__tag">
        <i class="fa-solid fa-tag"></i> {{ categoryName(task.category_id) }}
      </span>
      <span v-if="task.location" class="hv-task-card__tag">
        <i class="fa-solid fa-location-dot"></i> {{ task.location }}
      </span>
    </div>

    <div class="hv-task-card__footer">
      <div class="hv-task-card__pub">
        <span class="hv-task-card__pub-label">发布者</span>
        <span class="hv-task-card__pub-name">
          {{ task.publisher_display_name }}
          <span v-if="task.publisher_rating_count > 0" class="hv-task-card__pub-score">
            ({{ task.publisher_rating_avg.toFixed(1) }})
          </span>
        </span>
        <span v-if="task.publisher_rating_count > 0" class="hv-task-card__pub-rating">
          <i class="fa-solid fa-star hv-task-card__star"></i>
          <span class="hv-task-card__rating-score">{{ task.publisher_rating_avg.toFixed(1) }}</span>
          <span class="hv-task-card__rating-count">({{ task.publisher_rating_count }}条评价)</span>
        </span>
      </div>
      <span class="hv-task-card__price">¥{{ task.price }}</span>
    </div>
  </div>
</template>

<style scoped>
.hv-task-card {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 22px;
}

.hv-task-card--pinned {
  border: 1.5px solid rgba(245, 158, 11, 0.45) !important;
  box-shadow: 0 0 14px -2px rgba(251, 191, 36, 0.22), 0 0 4px rgba(245, 158, 11, 0.10) !important;
}

@media (hover: hover) {
  .hv-task-card--pinned:hover {
    box-shadow: 0 0 22px -2px rgba(251, 191, 36, 0.32), 0 4px 16px rgba(0, 0, 0, 0.06) !important;
  }
}

.hv-task-card__top {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.hv-task-card__top-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.hv-task-card__icon-wrap {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.hv-task-card__badges {
  display: flex;
  gap: 6px;
  align-items: center;
  flex-wrap: wrap;
}

.hv-task-card__gender-icon {
  margin-right: 3px;
}

.hv-task-card__deadline {
  font-size: var(--text-xs);
  color: var(--c-text-muted);
  display: flex;
  align-items: center;
  gap: 5px;
  white-space: nowrap;
}

.hv-task-card__deadline--expired {
  color: var(--c-danger);
  font-weight: 600;
}

.hv-task-card__title {
  font-size: var(--text-lg);
  font-weight: 700;
  margin: 2px 0 0;
  line-height: 1.4;
  transition: color 0.2s;
}

@media (hover: hover) {
  .hv-task-card:hover .hv-task-card__title {
    color: var(--c-accent);
  }
}

.hv-task-card__desc {
  color: var(--c-text-secondary);
  font-size: var(--text-sm);
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  margin: 0;
}

.hv-task-card__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.hv-task-card__tag {
  background: var(--c-border-light);
  color: var(--c-text-secondary);
  padding: 3px 10px;
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  font-weight: 500;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  border: 1px solid var(--c-border);
}

.hv-task-card__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: auto;
  padding-top: 12px;
  border-top: 1px solid var(--c-border-light);
}

.hv-task-card__pub {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.hv-task-card__pub-label {
  font-size: var(--text-xs);
  color: var(--c-text-muted);
}

.hv-task-card__pub-name {
  font-size: var(--text-sm);
  font-weight: 500;
}

.hv-task-card__pub-score {
  display: none;
}

.hv-task-card__pub-rating {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: var(--text-xs);
  margin-top: 1px;
}

.hv-task-card__star {
  color: #f5a623;
  font-size: 11px;
}

.hv-task-card__rating-score {
  font-weight: 600;
  color: var(--c-text);
}

.hv-task-card__rating-count {
  color: var(--c-text-muted);
}

.hv-task-card__price {
  font-size: var(--text-xl);
  font-weight: 700;
  color: var(--c-accent);
}

@media (max-width: 900px) {
  .hv-task-card {
    padding: 12px;
    gap: 6px;
  }

  .hv-task-card__top {
    align-items: flex-start;
  }

  .hv-task-card__top-right {
    flex-direction: column;
    align-items: flex-end;
    gap: 4px;
  }

  .hv-task-card__deadline {
    font-size: 10px;
  }

  .hv-task-card__title {
    font-size: var(--text-sm);
    line-height: 1.35;
  }

  .hv-task-card__desc {
    font-size: var(--text-xs);
    -webkit-line-clamp: 2;
  }

  .hv-task-card__tags {
    display: none;
  }

  .hv-task-card__footer {
    padding-top: 8px;
  }

  .hv-task-card__pub-name {
    font-size: var(--text-xs);
  }

  .hv-task-card__pub-score {
    display: inline;
    color: var(--c-text-muted);
    font-weight: 400;
  }

  .hv-task-card__pub-rating {
    display: none;
  }

  .hv-task-card__price {
    font-size: var(--text-lg);
  }
}
</style>
