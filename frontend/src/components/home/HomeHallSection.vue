<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import AppDropdown from '../AppDropdown.vue'
import HomeCategoryChipsBar from './HomeCategoryChipsBar.vue'
import HomeTaskCard from './HomeTaskCard.vue'
import HomeEmptyState from './ui/HomeEmptyState.vue'
import type { Category, Task } from '../../types/api'

const props = defineProps<{
  searchQuery: string
  taskSort: string
  taskSortOptions: Array<{ value: string; label: string }>
  selectedCategory: number | null
  categories: Category[]
  totalTaskCount: number
  tasks: Task[]
  statusOf: (status: string) => { label: string; cls: string }
  genderLabel: (gender: string | null) => { label: string; icon: string; cls: string } | null
  categoryName: (id: number | null) => string | null
  isExpired: (iso: string) => boolean
  formatShort: (iso: string) => string
}>()

const emit = defineEmits<{
  (e: 'update:searchQuery', value: string): void
  (e: 'update:taskSort', value: string): void
  (e: 'update:selectedCategory', value: number | null): void
  (e: 'openTask', task: Task): void
}>()

const showMobileSort = ref(false)
const mobileSortRef = ref<HTMLElement | null>(null)

const searchValue = computed({
  get: () => props.searchQuery,
  set: (value: string) => emit('update:searchQuery', value),
})

const taskSortValue = computed({
  get: () => props.taskSort,
  set: (value: string | number | null) => emit('update:taskSort', String(value ?? 'ranking')),
})

const emptyText = computed(() =>
  props.searchQuery.trim() || props.selectedCategory !== null ? '未找到匹配的任务' : '暂无可接任务',
)

function setCategory(categoryId: number | null) {
  emit('update:selectedCategory', categoryId)
}

const listKey = ref(0)
const taskGridRef = ref<HTMLElement | null>(null)
let staggerTimer = 0

watch([() => props.selectedCategory, () => props.taskSort], async () => {
  const el = taskGridRef.value
  if (!el) return
  clearTimeout(staggerTimer)
  el.style.transition = 'none'
  el.style.opacity = '0'
  listKey.value++
  await nextTick()
  staggerTimer = window.setTimeout(() => {
    el.style.opacity = '1'
    requestAnimationFrame(() => { el.style.transition = '' })
  }, 30)
})

// === 桌面端 Sidebar 滑动指示器 ===
const sidebarItemEls = ref<HTMLElement[]>([])
const sidebarIndicatorTop = ref(0)
const sidebarIndicatorHeight = ref(0)
const sidebarIndicatorReady = ref(false)
const sidebarNoTransition = ref(true)

function setSidebarItem(el: unknown, idx: number) {
  if (el instanceof HTMLElement) {
    sidebarItemEls.value[idx] = el
  }
}

function updateSidebarIndicator() {
  const activeIdx =
    props.selectedCategory === null
      ? 0
      : props.categories.findIndex(c => c.id === props.selectedCategory) + 1
  const el = sidebarItemEls.value[activeIdx]
  if (!el) return
  sidebarIndicatorTop.value = el.offsetTop
  sidebarIndicatorHeight.value = el.offsetHeight
  if (!sidebarIndicatorReady.value) sidebarIndicatorReady.value = true
}

watch([() => props.selectedCategory, () => props.categories], async () => {
  await nextTick()
  updateSidebarIndicator()
})

function onClickOutside(e: MouseEvent) {
  if (mobileSortRef.value && !mobileSortRef.value.contains(e.target as Node)) {
    showMobileSort.value = false
  }
}

onMounted(async () => {
  document.addEventListener('mousedown', onClickOutside)
  await nextTick()
  updateSidebarIndicator()
  // 两帧后启用动画，避免初始定位触发过渡
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      sidebarNoTransition.value = false
    })
  })
})

onUnmounted(() => {
  document.removeEventListener('mousedown', onClickOutside)
  clearTimeout(staggerTimer)
})
</script>

<template>
  <section class="hv-section hv-hall">
    <div class="hv-hall-toolbar">
      <div class="hv-search-wrap">
        <i class="fa-solid fa-magnifying-glass hv-search-icon"></i>
        <input v-model="searchValue" class="hv-search-input" placeholder="搜索任务标题、描述..." />
      </div>

      <AppDropdown
        v-model="taskSortValue"
        :options="taskSortOptions"
        width="auto"
        min-width="160px"
        class="hv-sort-desktop"
      />

      <div ref="mobileSortRef" class="hv-sort-mobile-wrap">
        <button class="hv-sort-btn" :class="{ 'hv-sort-btn--active': showMobileSort }" @click="showMobileSort = !showMobileSort">
          <i class="fa-solid fa-arrow-down-wide-short"></i>
        </button>
        <Transition name="app-dropdown">
          <div v-if="showMobileSort" class="hv-sort-menu">
            <button
              v-for="opt in taskSortOptions"
              :key="opt.value"
              class="hv-sort-menu__item"
              :class="{ 'hv-sort-menu__item--active': taskSort === opt.value }"
              @click="taskSortValue = opt.value; showMobileSort = false"
            >
              {{ opt.label }}
              <i v-if="taskSort === opt.value" class="fa-solid fa-check hv-sort-check"></i>
            </button>
          </div>
        </Transition>
      </div>
    </div>

    <HomeCategoryChipsBar
      :categories="categories"
      :selected-category="selectedCategory"
      @update:selected-category="setCategory"
    />

    <div class="hv-hall-layout">
      <aside class="hv-sidebar">
        <div
          v-if="sidebarIndicatorReady"
          class="hv-sidebar__indicator"
          :class="{ 'hv-sidebar__indicator--no-transition': sidebarNoTransition }"
          :style="{ top: `${sidebarIndicatorTop}px`, height: `${sidebarIndicatorHeight}px` }"
        ></div>
        <button
          :ref="el => setSidebarItem(el, 0)"
          class="hv-sidebar__item"
          :class="{ 'hv-sidebar__item--active': selectedCategory === null }"
          @click="setCategory(null)"
        >
          <i class="fa-solid fa-layer-group"></i> 全部任务
          <span class="hv-sidebar__count">({{ totalTaskCount }})</span>
        </button>
        <button
          v-for="(c, idx) in categories"
          :key="c.id"
          :ref="el => setSidebarItem(el, idx + 1)"
          class="hv-sidebar__item"
          :class="{ 'hv-sidebar__item--active': selectedCategory === c.id }"
          @click="setCategory(c.id)"
        >
          {{ c.name }}
          <span class="hv-sidebar__count">({{ c.task_count }})</span>
        </button>
      </aside>

      <div class="hv-hall-content">
        <template v-if="tasks.length">
          <div ref="taskGridRef" class="hv-task-grid">
            <HomeTaskCard
              v-for="(task, idx) in tasks"
              :key="`${listKey}-${task.id}`"
              class="hv-stagger-item"
              :style="{ '--stagger-delay': `${idx * 45}ms` }"
              :task="task"
              :status-of="statusOf"
              :gender-label="genderLabel"
              :category-name="categoryName"
              :is-expired="isExpired"
              :format-short="formatShort"
              @select="emit('openTask', $event)"
            />
          </div>
        </template>

        <HomeEmptyState v-else icon="fa-solid fa-inbox" :text="emptyText" />
      </div>
    </div>
  </section>
</template>

<style scoped>
.hv-hall-toolbar {
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

.hv-hall-layout {
  display: flex;
  gap: 24px;
}

.hv-hall-content {
  flex: 1;
  min-width: 0;
}

.hv-sidebar {
  position: sticky;
  top: 84px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  width: 160px;
  flex-shrink: 0;
  align-self: flex-start;
}

.hv-sidebar__indicator {
  position: absolute;
  left: 0;
  right: 0;
  border-radius: var(--radius-md);
  background: var(--c-accent-light);
  transition: top 0.28s cubic-bezier(0.4, 0, 0.2, 1), height 0.28s cubic-bezier(0.4, 0, 0.2, 1);
  pointer-events: none;
  z-index: 0;
}

.hv-sidebar__indicator--no-transition {
  transition: none;
}

.hv-sidebar__item {
  position: relative;
  z-index: 1;
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
  transition: color var(--dur-fast) var(--ease);
  white-space: nowrap;
  cursor: pointer;
}

@media (hover: hover) {
  .hv-sidebar__item:not(.hv-sidebar__item--active):hover {
    color: var(--c-text);
  }
}

.hv-sidebar__item--active {
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

.hv-task-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.hv-stagger-item {
  opacity: 0;
  transform: translateY(16px) scale(0.985);
  animation: hv-card-enter 420ms var(--ease) forwards;
  animation-delay: var(--stagger-delay, 0ms);
}

.badge-pink {
  background: #fce7f3;
  color: #be185d;
}

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

@media (max-width: 900px) {
  .hv-hall-toolbar {
    margin-bottom: 8px;
  }

  .hv-sidebar {
    display: none;
  }

  .hv-sort-desktop {
    display: none !important;
  }

  .hv-sort-mobile-wrap {
    display: block;
  }

  .hv-search-wrap {
    max-width: none;
  }

  .hv-hall-layout {
    gap: 0;
  }

  .hv-task-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 10px;
  }

  .hv-stagger-item {
    animation-duration: 320ms;
  }

  /* Reserve space for the fixed FAB publish button */
  .hv-hall-content {
    padding-bottom: 88px;
  }
}

@keyframes hv-card-enter {
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
