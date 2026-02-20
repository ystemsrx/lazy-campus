<script setup lang="ts">
import { computed } from 'vue'
import AppDropdown from '../AppDropdown.vue'
import HomeAvatar from './ui/HomeAvatar.vue'
import HomeEmptyState from './ui/HomeEmptyState.vue'
import HomeStars from './ui/HomeStars.vue'
import type { WorkerProfile } from '../../types/api'

const props = defineProps<{
  workers: WorkerProfile[]
  workerSort: string
  workerSortOptions: Array<{ value: string; label: string }>
}>()

const emit = defineEmits<{
  (e: 'update:workerSort', value: string): void
}>()

const workerSortValue = computed({
  get: () => props.workerSort,
  set: (value: string | number | null) => emit('update:workerSort', String(value ?? 'ranking')),
})
</script>

<template>
  <section class="hv-section">
    <div class="hv-section__header">
      <h2>接单广场</h2>
      <span class="hv-section__count">{{ workers.length }} 位接单者</span>
      <AppDropdown
        v-model="workerSortValue"
        :options="workerSortOptions"
        width="auto"
        min-width="140px"
        class="hv-sort-dropdown"
      />
    </div>

    <div v-if="workers.length" class="hv-worker-grid">
      <div v-for="w in workers" :key="w.user_id" class="card hv-worker-card">
        <div class="hv-worker-card__header">
          <HomeAvatar size="lg" :avatar-url="w.avatar_url" :gender="w.gender" alt="worker avatar" />
          <div class="hv-worker-card__info">
            <h4>{{ w.display_name }}</h4>
            <div class="hv-worker-card__rating">
              <HomeStars :value="Math.round(w.worker_rating_avg)" />
              <span class="hv-worker-card__count">{{ w.worker_rating_avg.toFixed(1) }} 分 · {{ w.worker_rating_count }} 评价</span>
            </div>
          </div>
        </div>

        <div class="hv-worker-card__body">
          <div class="hv-worker-card__row">
            <span class="hv-worker-card__label">擅长</span>
            <span>{{ w.skills || '未设置' }}</span>
          </div>
          <div class="hv-worker-card__row">
            <span class="hv-worker-card__label">价格</span>
            <span>{{ w.min_price ?? '-' }} ~ {{ w.max_price ?? '-' }} 元</span>
          </div>
          <div v-if="w.blocked_by_count > 0" class="hv-worker-card__row">
            <span class="hv-worker-card__label">被拉黑</span>
            <span class="badge badge-red">{{ w.blocked_by_count }} 次</span>
          </div>
          <p v-if="w.bio" class="hv-worker-card__bio">{{ w.bio }}</p>
        </div>
      </div>
    </div>

    <HomeEmptyState v-else icon="fa-solid fa-users" text="暂无接单者" />
  </section>
</template>

<style scoped>
.hv-section__header {
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 20px;
}

.hv-section__count {
  font-size: var(--text-sm);
  color: var(--c-text-muted);
}

.hv-sort-dropdown {
  margin-left: auto;
}

.hv-worker-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 14px;
}

.hv-worker-card__header {
  display: flex;
  gap: 14px;
  align-items: center;
  margin-bottom: 14px;
}

.hv-worker-card__info h4 {
  margin: 0 0 2px;
}

.hv-worker-card__rating {
  display: flex;
  align-items: center;
  gap: 6px;
}

.hv-worker-card__count {
  font-size: var(--text-xs);
  color: var(--c-text-muted);
}

.hv-worker-card__body {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.hv-worker-card__row {
  display: flex;
  justify-content: space-between;
  font-size: var(--text-sm);
  color: var(--c-text-secondary);
}

.hv-worker-card__label {
  color: var(--c-text-muted);
  flex-shrink: 0;
}

.hv-worker-card__bio {
  margin: 6px 0 0;
  padding-top: 8px;
  border-top: 1px solid var(--c-border-light);
  font-size: var(--text-sm);
  color: var(--c-text-secondary);
  line-height: 1.55;
}

@media (max-width: 900px) {
  .hv-worker-grid {
    grid-template-columns: 1fr;
  }
}
</style>
