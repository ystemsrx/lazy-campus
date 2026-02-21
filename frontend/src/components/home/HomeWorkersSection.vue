<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import AppDropdown from '../AppDropdown.vue'
import HomeAvatar from './ui/HomeAvatar.vue'
import HomeEmptyState from './ui/HomeEmptyState.vue'

import type { Category, WorkerProfile } from '../../types/api'

const props = defineProps<{
  workers: WorkerProfile[]
  workerSort: string
  workerSortOptions: Array<{ value: string; label: string }>
  categories: Category[]
  selectedCategory: number | null
  totalWorkerCount: number
  searchQuery: string
}>()

const emit = defineEmits<{
  (e: 'update:workerSort', value: string): void
  (e: 'update:selectedCategory', value: number | null): void
  (e: 'update:searchQuery', value: string): void
  (e: 'openWorker', worker: WorkerProfile): void
}>()

const searchValue = computed({
  get: () => props.searchQuery,
  set: (value: string) => emit('update:searchQuery', value),
})

const showMobileSort = ref(false)
const mobileSortRef = ref<HTMLElement | null>(null)

const workerSortValue = computed({
  get: () => props.workerSort,
  set: (value: string | number | null) => emit('update:workerSort', String(value ?? 'ranking')),
})

function setCategory(id: number | null) {
  emit('update:selectedCategory', id)
}

const workerGridRef = ref<HTMLElement | null>(null)
let staggerTimer = 0

watch(() => props.selectedCategory, async () => {
  const el = workerGridRef.value
  if (!el) return
  clearTimeout(staggerTimer)
  el.style.transition = 'none'
  el.style.opacity = '0'
  await nextTick()
  staggerTimer = window.setTimeout(() => {
    const items = el.querySelectorAll<HTMLElement>('.hv-stagger-item')
    items.forEach(item => { item.style.animation = 'none' })
    void el.offsetHeight
    items.forEach(item => { item.style.animation = '' })
    el.style.opacity = '1'
    requestAnimationFrame(() => { el.style.transition = '' })
  }, 30)
})

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
  clearTimeout(staggerTimer)
})
</script>

<template>
  <section class="hv-section hv-workers">
    <div class="hv-workers-toolbar">
      <div class="hv-search-wrap">
        <i class="fa-solid fa-magnifying-glass hv-search-icon"></i>
        <input v-model="searchValue" class="hv-search-input" placeholder="搜索接单者名称、简介..." />
      </div>

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

    <!-- Mobile: sticky chips bar -->
    <div v-if="categories.length" class="hv-mob-bar">
      <div class="hv-mob-bar__chips">
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
        <template v-if="workers.length">
          <div ref="workerGridRef" class="hv-worker-grid">
            <div
              v-for="(w, idx) in workers"
              :key="w.user_id"
              class="hv-worker-card hv-stagger-item"
              :style="{ '--stagger-delay': `${idx * 50}ms` }"
              @click="emit('openWorker', w)"
            >
              <div class="hv-worker-card__header">
                <HomeAvatar size="xl" :avatar-url="w.avatar_url" :gender="w.gender" />
                <div class="hv-worker-card__meta">
                  <div class="hv-worker-card__name-row">
                    <h4>{{ w.display_name }}<span class="hv-worker-card__score-inline">({{ w.overall_rating_avg.toFixed(1) }})</span></h4>
                    <p class="hv-worker-card__price hv-worker-card__price--desktop">{{ w.min_price ?? '-' }}~{{ w.max_price ?? '-' }}元</p>
                    <p class="hv-worker-card__price hv-worker-card__price--mobile">{{ w.min_price != null ? '¥' + w.min_price : '-' }}</p>
                  </div>
                  <div class="hv-worker-card__top-row">
                    <p class="hv-worker-card__role">
                      <i class="fa-solid fa-briefcase"></i>
                      完成{{ w.worker_completed_count }}
                    </p>
                  </div>
                  <div class="hv-worker-card__rating">
                    <i class="fa-solid fa-star hv-star-icon"></i>
                    <span>{{ w.overall_rating_avg.toFixed(1) }}</span>
                    <span class="hv-rating-text">
                      {{ w.overall_rating_count > 0 ? `(${w.overall_rating_count} 评价)` : '暂无评价' }}
                    </span>
                  </div>
                </div>
              </div>

              <p v-if="w.bio" class="hv-worker-card__bio">{{ w.bio }}</p>

              <div v-if="w.skill_tags.length" class="hv-worker-card__tags">
                <span v-for="tag in w.skill_tags" :key="tag.id" class="hv-worker-tag">{{ tag.name }}</span>
              </div>

              <div class="hv-worker-card__actions">
                <button class="hv-worker-card__btn-main" @click.stop="emit('openWorker', w)">查看详情</button>
                <button
                  v-if="w.blocked_by_count > 0"
                  class="hv-worker-card__btn-icon hv-worker-card__btn-icon--warn"
                  :title="`被 ${w.blocked_by_count} 人拉黑`"
                >
                  <i class="fa-solid fa-triangle-exclamation"></i>
                </button>
              </div>
            </div>
          </div>

        </template>

        <HomeEmptyState v-else icon="fa-solid fa-users" :text="selectedCategory !== null ? '该类别下暂无接单者' : '暂无接单者'" />
      </div>
    </div>
  </section>
</template>

<style scoped>
/* ---- toolbar ---- */
.hv-workers-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.hv-search-wrap {
  flex: 1;
  max-width: 320px;
  position: relative;
}

.hv-search-icon {
  position: absolute;
  left: 13px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--c-text-muted);
  font-size: var(--text-sm);
  pointer-events: none;
}

.hv-search-input {
  width: 100%;
  padding: 9px 13px 9px 38px;
  border: 1.5px solid var(--c-border);
  border-radius: var(--radius-full);
  background: var(--c-surface);
  color: var(--c-text);
  font-size: var(--text-base);
  transition: border-color var(--dur-fast) var(--ease), box-shadow var(--dur-fast) var(--ease);
}

.hv-search-input:focus {
  border-color: var(--c-accent);
  box-shadow: 0 0 0 3px var(--c-accent-soft);
}

.hv-search-input::placeholder {
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

.hv-sort-btn--active {
  border-color: var(--c-accent);
  color: var(--c-accent);
  background: var(--c-accent-light);
}
@media (hover: hover) {
  .hv-sort-btn:hover {
    border-color: var(--c-accent);
    color: var(--c-accent);
    background: var(--c-accent-light);
  }
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

@media (hover: hover) {
  .hv-sort-menu__item:hover {
    background: var(--c-accent-light);
    color: var(--c-accent);
  }
}

.hv-sort-menu__item--active {
  background: var(--c-accent-light);
  color: var(--c-accent);
  font-weight: 500;
}

.hv-sort-check {
  font-size: 12px;
}

/* ---- mobile sticky bar (hidden on desktop) ---- */
.hv-mob-bar {
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

@media (hover: hover) {
  .hv-chip:hover {
    border-color: var(--c-text-muted);
  }
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

@media (hover: hover) {
  .hv-sidebar__item:hover {
    background: var(--c-border-light);
    color: var(--c-text);
  }
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
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 18px;
}

.hv-worker-card {
  background: var(--c-surface);
  border-radius: var(--radius-xl);
  padding: 24px;
  border: 1px solid var(--c-border-light);
  box-shadow: var(--shadow-xs);
  cursor: pointer;
  display: flex;
  flex-direction: column;
  min-width: 0;
  overflow: hidden;
  transition: box-shadow var(--dur-normal) var(--ease),
              transform var(--dur-normal) var(--ease);
}

.hv-stagger-item {
  opacity: 0;
  transform: translateY(16px) scale(0.985);
  animation: hv-worker-enter 460ms var(--ease) forwards;
  animation-delay: var(--stagger-delay, 0ms);
}

@media (hover: hover) {
  .hv-worker-card:hover {
    box-shadow: var(--shadow-lg);
    transform: translateY(-2px);
  }
}

.hv-worker-card :deep(.hv-avatar) {
  width: 60px;
  height: 60px;
  border-radius: var(--radius-lg);
  font-size: 22px;
}

.hv-worker-card__header {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 16px;
}

.hv-worker-card__meta {
  flex: 1;
  min-width: 0;
}

.hv-worker-card__name-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 8px;
  min-width: 0;
}

.hv-worker-card__name-row h4 {
  margin: 0;
  font-size: var(--text-lg);
  font-weight: 700;
  color: var(--c-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  min-width: 0;
}

.hv-worker-card__score-inline {
  display: none;
  color: var(--c-text-muted);
  font-weight: 400;
  font-size: var(--text-xs);
  margin-left: 4px;
}

.hv-worker-card__top-row {
  margin-top: 3px;
}

.hv-worker-card__role {
  margin: 3px 0 0;
  font-size: var(--text-sm);
  color: var(--c-accent);
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 5px;
}

.hv-worker-card__role i {
  font-size: 10px;
}

.hv-worker-card__price {
  font-size: var(--text-lg);
  font-weight: 700;
  color: var(--c-text);
  white-space: nowrap;
  margin: 0;
  flex-shrink: 0;
}

.hv-worker-card__price--mobile {
  display: none;
}

.hv-worker-card__rating {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: var(--text-sm);
  font-weight: 500;
  color: #f59e0b;
  margin-top: 6px;
}

.hv-star-icon {
  font-size: 13px;
}

.hv-rating-text {
  color: var(--c-text-muted);
  font-weight: 400;
  margin-left: 2px;
}

.hv-worker-card__bio {
  font-size: var(--text-sm);
  color: var(--c-text-secondary);
  line-height: 1.6;
  margin: 0 0 16px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.hv-worker-card__tags {
  display: flex;
  flex-wrap: nowrap;
  gap: 8px;
  margin-bottom: 24px;
  overflow-x: auto;
  scrollbar-width: none;
  -webkit-overflow-scrolling: touch;
}

.hv-worker-card__tags::-webkit-scrollbar {
  display: none;
}

.hv-worker-tag {
  display: inline-block;
  padding: 4px 12px;
  border-radius: var(--radius-sm);
  background: var(--c-accent-light);
  color: var(--c-accent);
  font-size: var(--text-xs);
  font-weight: 500;
  white-space: nowrap;
}

.hv-worker-card__actions {
  display: flex;
  gap: 10px;
  margin-top: auto;
}

.hv-worker-card__btn-main {
  flex: 1;
  padding: 10px 16px;
  border-radius: var(--radius-md);
  border: none;
  background: var(--c-primary);
  color: var(--c-text-inverse);
  font-size: var(--text-sm);
  font-weight: 500;
  font-family: var(--font-sans);
  cursor: pointer;
  transition: background var(--dur-fast) var(--ease);
}

@media (hover: hover) {
  .hv-worker-card__btn-main:hover {
    background: var(--c-primary-hover);
  }
}

.hv-worker-card__btn-icon {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-md);
  border: 1.5px solid var(--c-border);
  background: transparent;
  color: var(--c-text-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-family: var(--font-sans);
  cursor: pointer;
  flex-shrink: 0;
  transition: all var(--dur-fast) var(--ease);
}

.hv-worker-card__btn-icon--warn {
  border-color: var(--c-danger-soft);
  color: var(--c-danger);
  background: var(--c-danger-light);
}

@media (hover: hover) {
  .hv-worker-card__btn-icon:hover {
    background: var(--c-border-light);
    border-color: var(--c-text-muted);
  }

  .hv-worker-card__btn-icon--warn:hover {
    background: var(--c-danger-soft);
    border-color: var(--c-danger);
  }
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

  .hv-mob-bar {
    display: flex;
    position: -webkit-sticky;
    position: sticky;
    top: 60px;
    z-index: 30;
    background: var(--c-bg);
    margin: 0 -16px;
    border-bottom: 1px solid var(--c-border-light);
  }

  .hv-mob-bar__chips {
    flex: 1;
    min-width: 0;
    display: flex;
    gap: 8px;
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    scrollbar-width: none;
    padding: 6px 16px;
  }

  .hv-mob-bar__chips::-webkit-scrollbar {
    display: none;
  }

  .hv-workers-layout {
    gap: 0;
  }

  .hv-worker-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 10px;
  }

  .hv-worker-card {
    padding: 14px;
  }

  .hv-stagger-item {
    animation-duration: 340ms;
  }

  .hv-worker-card :deep(.hv-avatar) {
    width: 40px;
    height: 40px;
    border-radius: var(--radius-md);
    font-size: 16px;
  }

  .hv-worker-card__header {
    gap: 10px;
    margin-bottom: 10px;
  }

  .hv-worker-card__score-inline {
    display: inline;
  }

  .hv-worker-card__rating {
    display: none;
  }

  .hv-worker-card__price--desktop {
    display: none;
  }

  .hv-worker-card__price--mobile {
    display: block;
    font-size: var(--text-sm);
    font-weight: 600;
  }

  .hv-worker-card__bio {
    margin-bottom: 10px;
  }

  .hv-worker-card__tags {
    margin-bottom: 14px;
  }

  .hv-worker-card__btn-main {
    padding: 8px 12px;
  }

  .hv-worker-card__btn-icon {
    width: 34px;
    height: 34px;
    font-size: 12px;
  }
}

@keyframes hv-worker-enter {
  from {
    opacity: 0;
    transform: translateY(16px) scale(0.985);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}
</style>
