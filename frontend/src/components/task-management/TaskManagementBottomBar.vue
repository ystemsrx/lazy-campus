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
  <nav class="tm-bottombar">
    <button
      class="tm-bottombar__item"
      :class="{ 'tm-bottombar__item--active': activeView === 'dashboard' }"
      @click="emit('update:activeView', 'dashboard')"
    >
      <LayoutDashboard :size="22" />
      <span>任务</span>
    </button>

    <button class="tm-bottombar__item tm-bottombar__item--add" @click="emit('create')">
      <div class="tm-bottombar__add-circle">
        <Plus :size="22" />
      </div>
      <span>发布</span>
    </button>

    <button
      class="tm-bottombar__item"
      :class="{ 'tm-bottombar__item--active': activeView === 'stats' }"
      @click="emit('update:activeView', 'stats')"
    >
      <BarChart3 :size="22" />
      <span>统计</span>
    </button>
  </nav>
</template>

<style scoped>
.tm-bottombar {
  display: none;
}

@media (max-width: 900px) {
  .tm-bottombar {
    display: flex;
    justify-content: space-around;
    align-items: flex-end;
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    background: #ffffff;
    border-top: 1px solid var(--c-border-light);
    padding: 6px 0;
    padding-bottom: calc(6px + env(safe-area-inset-bottom, 0px));
    z-index: 50;
  }

  .tm-bottombar__item {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 3px;
    padding: 6px 20px;
    border: none;
    background: transparent;
    color: var(--c-text-muted);
    font-size: 11px;
    font-weight: 500;
    font-family: var(--font-sans);
    cursor: pointer;
    transition: color 0.2s var(--ease);
    flex: 1;
  }

  .tm-bottombar__item--active {
    color: var(--c-accent);
  }

  .tm-bottombar__item--add {
    color: var(--c-text);
  }

  .tm-bottombar__add-circle {
    width: 44px;
    height: 44px;
    border-radius: 50%;
    background: #0f172a;
    color: #ffffff;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 4px 15px rgba(15, 23, 42, 0.35);
    margin-top: -20px;
    transition: background 0.2s var(--ease);
  }

  .tm-bottombar__item--add:hover .tm-bottombar__add-circle {
    background: #1e293b;
  }
}
</style>
