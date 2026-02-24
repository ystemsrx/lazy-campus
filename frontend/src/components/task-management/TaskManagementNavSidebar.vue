<script setup lang="ts">
import { ref, watch, onMounted, nextTick } from 'vue'
import { BarChart3, LayoutDashboard, Plus } from 'lucide-vue-next'

const props = defineProps<{
  activeView: 'dashboard' | 'stats'
}>()

const emit = defineEmits<{
  (e: 'update:activeView', value: 'dashboard' | 'stats'): void
  (e: 'create'): void
}>()

const sidebarRef = ref<HTMLElement | null>(null)
const dashBtnRef = ref<HTMLElement | null>(null)
const statsBtnRef = ref<HTMLElement | null>(null)
const isAnimating = ref(false)
const indicatorStyle = ref<Record<string, string>>({ top: '0px', height: '0px' })

function updateIndicator(animate = true) {
  const sidebar = sidebarRef.value
  const btn = props.activeView === 'dashboard' ? dashBtnRef.value : statsBtnRef.value
  if (!sidebar || !btn) return
  const sr = sidebar.getBoundingClientRect()
  const br = btn.getBoundingClientRect()
  isAnimating.value = animate
  indicatorStyle.value = {
    top: `${br.top - sr.top}px`,
    height: `${br.height}px`,
  }
}

watch(() => props.activeView, async () => {
  await nextTick()
  updateIndicator(true)
})

onMounted(async () => {
  await nextTick()
  updateIndicator(false)
  requestAnimationFrame(() => { isAnimating.value = true })
})
</script>

<template>
  <aside ref="sidebarRef" class="tm-sidebar">
    <div
      class="tm-sidebar__indicator"
      :class="{ 'tm-sidebar__indicator--animated': isAnimating }"
      :style="indicatorStyle"
    />

    <button
      ref="dashBtnRef"
      class="tm-sidebar__btn"
      :class="{ 'tm-sidebar__btn--active': activeView === 'dashboard' }"
      @click="emit('update:activeView', 'dashboard')"
    >
      <LayoutDashboard :size="22" />
      <span>任务</span>
    </button>

    <button class="tm-sidebar__add-btn" @click="emit('create')">
      <Plus :size="22" />
      <span>发布</span>
    </button>

    <button
      ref="statsBtnRef"
      class="tm-sidebar__btn"
      :class="{ 'tm-sidebar__btn--active': activeView === 'stats' }"
      @click="emit('update:activeView', 'stats')"
    >
      <BarChart3 :size="22" />
      <span>统计</span>
    </button>
  </aside>
</template>

<style scoped>
.tm-sidebar {
  width: 80px;
  background: #ffffff;
  border-right: 1px solid var(--c-border-light);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 20px;
  position: fixed;
  top: 60px;
  left: 0;
  bottom: 0;
  z-index: 10;
  box-shadow: 4px 0 24px rgba(0, 0, 0, 0.02);
}

.tm-sidebar__indicator {
  position: absolute;
  left: 8px;
  right: 8px;
  border-radius: 14px;
  background: var(--c-accent-light);
  pointer-events: none;
  z-index: 0;
}

.tm-sidebar__indicator--animated {
  transition:
    top 0.38s cubic-bezier(0.16, 1, 0.3, 1),
    height 0.38s cubic-bezier(0.16, 1, 0.3, 1);
}

.tm-sidebar__btn {
  width: 64px;
  padding: 10px 6px;
  border-radius: 14px;
  border: none;
  background: transparent;
  color: var(--c-text-muted);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 5px;
  cursor: pointer;
  transition: color 0.2s var(--ease);
  font-size: 11px;
  font-weight: 500;
  font-family: var(--font-sans);
  line-height: 1;
  position: relative;
  z-index: 1;
}

.tm-sidebar__btn:hover {
  color: var(--c-text);
}

.tm-sidebar__btn--active {
  color: var(--c-accent);
}

.tm-sidebar__add-btn {
  width: 64px;
  padding: 10px 6px;
  border-radius: 14px;
  background: #0f172a;
  color: #ffffff;
  border: none;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 5px;
  cursor: pointer;
  box-shadow: 0 4px 16px rgba(15, 23, 42, 0.28);
  transition: all 0.2s var(--ease);
  font-size: 11px;
  font-weight: 600;
  font-family: var(--font-sans);
  line-height: 1;
  position: relative;
  z-index: 1;
}

.tm-sidebar__add-btn:hover {
  background: #1e293b;
  transform: translateY(-1px);
  box-shadow: 0 6px 20px rgba(15, 23, 42, 0.35);
}

@media (max-width: 900px) {
  .tm-sidebar {
    display: none;
  }
}
</style>
