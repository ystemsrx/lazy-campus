<script setup lang="ts">
export type AdminTabKey = 'dashboard' | 'reports' | 'users' | 'categories'

interface AdminTabItem {
  key: AdminTabKey
  label: string
  icon: string
}

defineProps<{
  activeTab: AdminTabKey
}>()

const tabs: AdminTabItem[] = [
  { key: 'dashboard', label: '数据看板', icon: 'fa-solid fa-chart-line' },
  { key: 'reports', label: '举报 / 申诉', icon: 'fa-solid fa-flag' },
  { key: 'users', label: '用户管理', icon: 'fa-solid fa-users-gear' },
  { key: 'categories', label: '类别管理', icon: 'fa-solid fa-tags' },
]

const emit = defineEmits<{
  'tab-change': [key: AdminTabKey]
  logout: []
}>()

function onTabClick(key: AdminTabKey) {
  emit('tab-change', key)
}
</script>

<template>
  <header class="av-header">
    <div class="av-header__brand">
      <div class="av-logo">A</div>
      <span class="av-header__title">管理员控制台</span>
    </div>

    <nav class="av-tabs">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        class="av-tab"
        :class="{ 'av-tab--active': activeTab === tab.key }"
        @click="onTabClick(tab.key)"
      >
        <i :class="tab.icon"></i>
        {{ tab.label }}
      </button>
    </nav>

    <div class="av-header__right">
      <button class="btn btn-ghost btn-sm" @click="$emit('logout')">
        <i class="fa-solid fa-right-from-bracket"></i>
        退出
      </button>
    </div>
  </header>
</template>

<style scoped>
.av-header {
  position: sticky;
  top: 0;
  z-index: 40;
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 0 24px;
  height: 60px;
  background: rgba(255, 255, 255, 0.82);
  backdrop-filter: blur(14px);
  border-bottom: 1px solid var(--c-border);
}

.av-header__brand {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.av-logo {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-sm);
  background: var(--c-primary);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 16px;
}

.av-header__title {
  font-weight: 700;
  font-size: var(--text-lg);
  color: var(--c-text);
}

.av-tabs {
  display: flex;
  gap: 4px;
}

.av-tab {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border: none;
  background: transparent;
  color: var(--c-text-muted);
  font-size: var(--text-sm);
  font-weight: 500;
  border-radius: var(--radius-sm);
  transition:
    color var(--dur-fast) var(--ease),
    background var(--dur-fast) var(--ease);
}

.av-tab:hover {
  color: var(--c-text);
  background: var(--c-border-light);
}

.av-tab--active {
  color: var(--c-accent);
  background: var(--c-accent-light);
}

.av-header__right {
  margin-left: auto;
  flex-shrink: 0;
}

@media (max-width: 768px) {
  .av-header {
    padding: 0 14px;
    gap: 10px;
  }

  .av-header__title {
    display: none;
  }

  .av-tabs {
    overflow-x: auto;
  }
}
</style>
