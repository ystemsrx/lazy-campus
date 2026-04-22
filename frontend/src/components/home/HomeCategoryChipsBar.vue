<script setup lang="ts">
import { nextTick, onMounted, ref, watch } from 'vue'
import type { Category } from '../../types/api'

const props = defineProps<{
  categories: Category[]
  selectedCategory: number | null
  totalCount?: number | null
  countKey?: 'task_count' | 'worker_count'
  allLabel?: string
}>()

const emit = defineEmits<{
  (e: 'update:selectedCategory', value: number | null): void
}>()

function setCategory(id: number | null) {
  emit('update:selectedCategory', id)
}

const containerRef = ref<HTMLElement | null>(null)
const itemEls = ref<HTMLElement[]>([])
const indicatorLeft = ref(0)
const indicatorWidth = ref(0)
const indicatorReady = ref(false)
const noTransition = ref(true)

function setItem(el: unknown, idx: number) {
  if (el instanceof HTMLElement) {
    itemEls.value[idx] = el
  }
}

function scrollChipIntoView(el: HTMLElement) {
  const container = containerRef.value
  if (!container) return
  const elLeft = el.offsetLeft
  const elRight = elLeft + el.offsetWidth
  const scrollLeft = container.scrollLeft
  const containerWidth = container.clientWidth
  if (elLeft < scrollLeft) {
    container.scrollTo({ left: elLeft - 8, behavior: 'smooth' })
  } else if (elRight > scrollLeft + containerWidth) {
    container.scrollTo({ left: elRight - containerWidth + 8, behavior: 'smooth' })
  }
}

function updateIndicator(scrollActive = false) {
  const activeIdx =
    props.selectedCategory === null
      ? 0
      : props.categories.findIndex(c => c.id === props.selectedCategory) + 1
  const el = itemEls.value[activeIdx]
  if (!el) return
  indicatorLeft.value = el.offsetLeft
  indicatorWidth.value = el.offsetWidth
  if (!indicatorReady.value) indicatorReady.value = true
  if (scrollActive) scrollChipIntoView(el)
}

watch([() => props.selectedCategory, () => props.categories], async () => {
  await nextTick()
  updateIndicator(true)
})

onMounted(async () => {
  await nextTick()
  updateIndicator()
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      noTransition.value = false
    })
  })
})
</script>

<template>
  <div class="hcc-bar">
    <div ref="containerRef" class="hcc-chips">
      <div
        v-if="indicatorReady"
        class="hcc-indicator"
        :class="{ 'hcc-indicator--no-transition': noTransition }"
        :style="{ left: `${indicatorLeft}px`, width: `${indicatorWidth}px` }"
      ></div>
      <button
        :ref="el => setItem(el, 0)"
        class="hcc-chip"
        :class="{ 'hcc-chip--active': selectedCategory === null }"
        @click="setCategory(null)"
      >
        {{ allLabel ?? '全部' }}<span
          v-if="countKey && totalCount != null"
          class="hcc-chip__count"
        >({{ totalCount }})</span>
      </button>
      <button
        v-for="(c, idx) in categories"
        :key="c.id"
        :ref="el => setItem(el, idx + 1)"
        class="hcc-chip"
        :class="{ 'hcc-chip--active': selectedCategory === c.id }"
        @click="setCategory(c.id)"
      >
        {{ c.name }}<span
          v-if="countKey"
          class="hcc-chip__count"
        >({{ c[countKey] }})</span>
      </button>
    </div>
  </div>
</template>

<style scoped>
.hcc-bar {
  display: none;
}

.hcc-chips {
  position: relative;
  display: flex;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: none;
  background: var(--c-border-light);
  border-radius: 999px;
  padding: 3px;
  gap: 0;
}

.hcc-chips::-webkit-scrollbar {
  display: none;
}

.hcc-indicator {
  position: absolute;
  top: 3px;
  bottom: 3px;
  border-radius: 999px;
  background: var(--c-surface);
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.10), 0 0.5px 1px rgba(0, 0, 0, 0.06);
  transition: left 0.28s cubic-bezier(0.4, 0, 0.2, 1), width 0.28s cubic-bezier(0.4, 0, 0.2, 1);
  pointer-events: none;
  z-index: 0;
}

.hcc-indicator--no-transition {
  transition: none;
}

.hcc-chip {
  position: relative;
  z-index: 1;
  flex-shrink: 0;
  padding: 6px 16px;
  border-radius: 999px;
  border: none;
  background: transparent;
  color: var(--c-text-secondary);
  font-size: var(--text-sm);
  font-weight: 500;
  font-family: var(--font-sans);
  white-space: nowrap;
  cursor: pointer;
  transition: color var(--dur-fast) var(--ease);
}

@media (hover: hover) {
  .hcc-chip:hover {
    color: var(--c-text);
  }
}

.hcc-chip--active {
  color: var(--c-accent);
  font-weight: 600;
}

.hcc-chip__count {
  margin-left: 4px;
  opacity: 0.7;
  font-weight: 400;
}

@media (max-width: 900px) {
  .hcc-bar {
    display: block;
    position: -webkit-sticky;
    position: sticky;
    top: 60px;
    z-index: 30;
    background: var(--c-bg);
    margin: 0 -16px;
    padding: 6px 16px;
    border-bottom: 1px solid var(--c-border-light);
  }
}
</style>
