<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import AppDropdown from '../AppDropdown.vue'
import HomeAvatar from './ui/HomeAvatar.vue'
import HomeEmptyState from './ui/HomeEmptyState.vue'
import HomeStars from './ui/HomeStars.vue'
import type { Category, WorkerProfile } from '../../types/api'

const props = defineProps<{
  workers: WorkerProfile[]
  workerSort: string
  workerSortOptions: Array<{ value: string; label: string }>
  categories: Category[]
  selectedCategory: number | null
  totalWorkerCount: number
}>()

const emit = defineEmits<{
  (e: 'update:workerSort', value: string): void
  (e: 'update:selectedCategory', value: number | null): void
  (e: 'openWorker', worker: WorkerProfile): void
}>()

const showMobileSort = ref(false)
const mobileSortRef = ref<HTMLElement | null>(null)

const workerSortValue = computed({
  get: () => props.workerSort,
  set: (value: string | number | null) => emit('update:workerSort', String(value ?? 'ranking')),
})

function setCategory(id: number | null) {
  emit('update:selectedCategory', id)
}

function onClickOutside(e: MouseEvent) {
  if (mobileSortRef.value && !mobileSortRef.value.contains(e.target as Node)) {
    showMobileSort.value = false
  }
}

onMounted(() => {
  document.addEventListener('mousedown', onClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('mousedown', onClickOutside)
})
</script>

<template>
  <section class="hv-section hv-workers">
    <div class="hv-workers-toolbar">
      <h2>接单广场</h2>
      <span class="hv-workers-toolbar__count">{{ workers.length }} 位接单者</span>

      <AppDropdown
        v-model="workerSortValue"
        :options="workerSortOptions"
        width="auto"
        min-width="140px"
        class="hv-sort-desktop"
      />

      <div ref="mobileSortRef" class="hv-sort-mobile-wrap">
        <button class="hv-sort-btn" :class="{ 'hv-sort-btn--active': showMobileSort }" @click="showMobileSort = !showMobileSort">
          <i class="fa-solid fa-arrow-down-wide-short"></i>
        </button>
        <Transition name="app-dropdown">
          <div v-if="showMobileSort" class="hv-sort-menu">
            <button
              v-for="opt in workerSortOptions"
              :key="opt.value"
              class="hv-sort-menu__item"
              :class="{ 'hv-sort-menu__item--active': workerSort === opt.value }"
              @click="workerSortValue = opt.value; showMobileSort = false"
            >
              {{ opt.label }}
              <i v-if="workerSort === opt.value" class="fa-solid fa-check hv-sort-check"></i>
            </button>
          </div>
        </Transition>
      </div>
    </div>

    <!-- mobile: sticky chips -->
    <div v-if="categories.length" class="hv-category-chips">
      <button
        class="hv-chip"
        :class="{ 'hv-chip--active': selectedCategory === null }"
        @click="setCategory(null)"
      >
        全部 ({{ totalWorkerCount }})
      </button>
      <button
        v-for="c in categories"
        :key="c.id"
        class="hv-chip"
        :class="{ 'hv-chip--active': selectedCategory === c.id }"
        @click="setCategory(c.id)"
      >
        {{ c.name }} ({{ c.worker_count }})
      </button>
    </div>

    <div class="hv-workers-layout">
      <!-- desktop: sidebar -->
      <aside v-if="categories.length" class="hv-sidebar">
        <button
          class="hv-sidebar__item"
          :class="{ 'hv-sidebar__item--active': selectedCategory === null }"
          @click="setCategory(null)"
        >
          <i class="fa-solid fa-layer-group"></i> 全部接单者
          <span class="hv-sidebar__count">({{ totalWorkerCount }})</span>
        </button>
        <button
          v-for="c in categories"
          :key="c.id"
          class="hv-sidebar__item"
          :class="{ 'hv-sidebar__item--active': selectedCategory === c.id }"
          @click="setCategory(c.id)"
        >
          {{ c.name }}
          <span class="hv-sidebar__count">({{ c.worker_count }})</span>
        </button>
      </aside>

      <div class="hv-workers-content">
        <div v-if="workers.length" class="hv-worker-grid">
          <div v-for="w in workers" :key="w.user_id" class="card hv-worker-card card-hover" @click="emit('openWorker', w)">
            <div class="hv-worker-card__header">
              <HomeAvatar size="lg" :avatar-url="w.avatar_url" :gender="w.gender" alt="worker avatar" />
              <div class="hv-worker-card__info">
                <h4>
                  {{ w.display_name }}
                  <span v-if="w.overall_rating_count > 0" class="hv-worker-card__score-inline">({{ w.overall_rating_avg.toFixed(1) }})</span>
                </h4>
                <div class="hv-worker-card__rating">
                  <HomeStars :value="Math.round(w.overall_rating_avg)" />
                  <span class="hv-worker-card__count">
                    {{ w.overall_rating_count > 0 ? `${w.overall_rating_avg.toFixed(1)} 分 · ${w.overall_rating_count} 评价` : '暂无评分' }}
                  </span>
                </div>
              </div>
            </div>

            <div class="hv-worker-card__body">
              <div v-if="w.skill_tags.length" class="hv-worker-card__tags">
                <span v-for="tag in w.skill_tags" :key="tag.id" class="hv-worker-tag">{{ tag.name }}</span>
              </div>
              <div class="hv-worker-card__row">
                <span class="hv-worker-card__label">价格</span>
                <span>{{ w.min_price ?? '-' }} ~ {{ w.max_price ?? '-' }} 元</span>
              </div>
              <div class="hv-worker-card__row">
                <span class="hv-worker-card__label">完成</span>
                <span>{{ w.worker_completed_count }} 单</span>
              </div>
              <div v-if="w.blocked_by_count > 0" class="hv-worker-card__row">
                <span class="hv-worker-card__label">被拉黑</span>
                <span class="badge badge-red">{{ w.blocked_by_count }} 次</span>
              </div>
              <p v-if="w.bio" class="hv-worker-card__bio">{{ w.bio }}</p>
            </div>
          </div>
        </div>

        <HomeEmptyState v-else icon="fa-solid fa-users" :text="selectedCategory !== null ? '该类别下暂无接单者' : '暂无接单者'" />
      </div>
    </div>
  </section>
</template>

<style scoped>
/* ---- toolbar ---- */
.hv-workers-toolbar {
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 16px;
}

.hv-workers-toolbar__count {
  font-size: var(--text-sm);
  color: var(--c-text-muted);
}

.hv-sort-desktop {
  flex-shrink: 0;
  margin-left: auto;
}

.hv-sort-mobile-wrap {
  display: none;
  position: relative;
}

.hv-sort-btn {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  border: 1.5px solid var(--c-border);
  background: var(--c-surface);
  color: var(--c-text-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 15px;
  transition: all var(--dur-fast) var(--ease);
  flex-shrink: 0;
}

.hv-sort-btn:hover,
.hv-sort-btn--active {
  border-color: var(--c-accent);
  color: var(--c-accent);
  background: var(--c-accent-light);
}

.hv-sort-menu {
  position: absolute;
  top: calc(100% + 6px);
  right: 0;
  min-width: 170px;
  background: #ffffff;
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xl);
  z-index: 1000;
  padding: 5px;
  transform-origin: top right;
}

.hv-sort-menu__item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  width: 100%;
  padding: 9px 12px;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--c-text);
  font-size: var(--text-base);
  font-family: var(--font-sans);
  cursor: pointer;
  text-align: left;
  white-space: nowrap;
  transition: background var(--dur-fast) var(--ease), color var(--dur-fast) var(--ease);
}

.hv-sort-menu__item:hover {
  background: var(--c-accent-light);
  color: var(--c-accent);
}

.hv-sort-menu__item--active {
  background: var(--c-accent-light);
  color: var(--c-accent);
  font-weight: 500;
}

.hv-sort-check {
  font-size: 12px;
}

/* ---- mobile chips (hidden on desktop) ---- */
.hv-category-chips {
  display: none;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
  gap: 8px;
  padding: 10px 0 2px;
  scrollbar-width: none;
}

.hv-category-chips::-webkit-scrollbar {
  display: none;
}

.hv-chip {
  flex-shrink: 0;
  padding: 6px 16px;
  border-radius: var(--radius-full);
  border: 1.5px solid var(--c-border);
  background: var(--c-surface);
  color: var(--c-text-secondary);
  font-size: var(--text-sm);
  font-weight: 500;
  font-family: var(--font-sans);
  white-space: nowrap;
  transition: all var(--dur-fast) var(--ease);
  cursor: pointer;
}

.hv-chip:hover {
  border-color: var(--c-text-muted);
}

.hv-chip--active {
  background: var(--c-accent);
  color: var(--c-text-inverse);
  border-color: var(--c-accent);
}

/* ---- layout: sidebar + content ---- */
.hv-workers-layout {
  display: flex;
  gap: 24px;
}

.hv-workers-content {
  flex: 1;
  min-width: 0;
}

/* ---- desktop sidebar ---- */
.hv-sidebar {
  display: flex;
  flex-direction: column;
  gap: 4px;
  width: 160px;
  flex-shrink: 0;
  position: sticky;
  top: 84px;
  align-self: flex-start;
}

.hv-sidebar__item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 14px;
  border: none;
  border-radius: var(--radius-md);
  background: transparent;
  color: var(--c-text-secondary);
  font-size: var(--text-base);
  font-weight: 500;
  font-family: var(--font-sans);
  text-align: left;
  transition: all var(--dur-fast) var(--ease);
  white-space: nowrap;
  cursor: pointer;
}

.hv-sidebar__item:hover {
  background: var(--c-border-light);
  color: var(--c-text);
}

.hv-sidebar__item--active {
  background: var(--c-accent-light);
  color: var(--c-accent);
  font-weight: 600;
}

.hv-sidebar__count {
  color: var(--c-text-muted);
  font-weight: 400;
  font-size: var(--text-xs);
  margin-left: auto;
}

.hv-sidebar__item--active .hv-sidebar__count {
  color: var(--c-accent);
  opacity: 0.7;
}

/* ---- worker cards ---- */
.hv-worker-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 14px;
}

.hv-worker-card {
  cursor: pointer;
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

.hv-worker-card__score-inline {
  display: none;
  color: var(--c-text-muted);
  font-weight: 400;
  font-size: var(--text-xs);
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

.hv-worker-card__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 4px;
}

.hv-worker-tag {
  display: inline-block;
  padding: 3px 10px;
  border-radius: var(--radius-full);
  background: var(--c-accent-light);
  color: var(--c-accent);
  font-size: var(--text-xs);
  font-weight: 500;
  white-space: nowrap;
  flex-shrink: 0;
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
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* ---- transitions ---- */
.app-dropdown-enter-active {
  transition: opacity var(--dur-normal) var(--ease), transform var(--dur-normal) var(--ease);
}

.app-dropdown-leave-active {
  transition: opacity 180ms var(--ease), transform 180ms var(--ease);
}

.app-dropdown-enter-from {
  opacity: 0;
  transform: scaleY(0.88) translateY(-6px);
}

.app-dropdown-leave-to {
  opacity: 0;
  transform: scaleY(0.94) translateY(-3px);
}

/* ---- mobile ---- */
@media (max-width: 900px) {
  .hv-sidebar {
    display: none;
  }

  .hv-sort-desktop {
    display: none !important;
  }

  .hv-sort-mobile-wrap {
    display: block;
    margin-left: auto;
  }

  .hv-category-chips {
    display: flex;
    position: sticky;
    top: 60px;
    z-index: 30;
    background: var(--c-bg);
    margin: 0 -16px;
    padding: 6px 16px;
    border-bottom: 1px solid var(--c-border-light);
  }

  .hv-workers-layout {
    gap: 0;
  }

  .hv-worker-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 10px;
  }

  .hv-worker-card {
    min-width: 0;
    overflow: hidden;
  }

  .hv-worker-card__body {
    min-width: 0;
  }

  .hv-worker-card__score-inline {
    display: inline;
  }

  .hv-worker-card__rating {
    display: none;
  }

  .hv-worker-card__tags {
    flex-wrap: nowrap;
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    scrollbar-width: none;
    padding-bottom: 2px;
  }

  .hv-worker-card__tags::-webkit-scrollbar {
    display: none;
  }
}
</style>
