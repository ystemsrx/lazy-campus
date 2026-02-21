<script setup lang="ts">
import { BarChart3, LayoutDashboard, Plus } from 'lucide-vue-next'

defineProps<{
  activeView: 'dashboard' | 'stats'
}>()

const emit = defineEmits<{
  (e: 'update:activeView', value: 'dashboard' | 'stats'): void
  (e: 'create'): void
}>()
</script>

<template>
  <aside class="tm-sidebar">
    <button
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
  transition: all 0.2s var(--ease);
  font-size: 11px;
  font-weight: 500;
  font-family: var(--font-sans);
  line-height: 1;
}

.tm-sidebar__btn:hover {
  background: var(--c-border-light);
  color: var(--c-text);
}

.tm-sidebar__btn--active {
  background: var(--c-accent-light);
  color: var(--c-accent);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
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
