<script setup lang="ts">
import { proxyRefs } from 'vue'

import type { AdminDashboardModel } from '../../composables/admin/useAdminDashboard'

const props = defineProps<{
  model: AdminDashboardModel
}>()

const vm = proxyRefs(props.model)
</script>

<template>
  <section class="av-section">
    <h2 class="av-title">数据看板</h2>

    <div class="av-stats-grid">
      <div class="av-stat-card">
        <span class="av-stat__value">{{ vm.dashboard.total_users ?? '-' }}</span>
        <span class="av-stat__label">总用户</span>
      </div>
      <div class="av-stat-card">
        <span class="av-stat__value">{{ vm.dashboard.active_workers ?? '-' }}</span>
        <span class="av-stat__label">活跃接单者</span>
      </div>
      <div class="av-stat-card">
        <span class="av-stat__value">{{ vm.dashboard.total_tasks ?? '-' }}</span>
        <span class="av-stat__label">总任务</span>
      </div>
      <div class="av-stat-card">
        <span class="av-stat__value">{{ vm.dashboard.completed_tasks ?? '-' }}</span>
        <span class="av-stat__label">已完成</span>
      </div>
      <div class="av-stat-card av-stat-card--accent">
        <span class="av-stat__value">{{ vm.dashboard.pending_reports ?? '-' }}</span>
        <span class="av-stat__label">待处理举报</span>
      </div>
      <div class="av-stat-card">
        <span class="av-stat__value">{{ vm.dashboard.completion_rate ?? '-' }}</span>
        <span class="av-stat__label">完成率</span>
      </div>
    </div>

    <div class="card av-reg-card">
      <div class="av-reg-row">
        <div>
          <h4 class="av-reg-title">用户注册</h4>
          <p class="av-reg-desc">
            当前状态：
            <span class="badge" :class="vm.registrationEnabled ? 'badge-green' : 'badge-red'">
              {{ vm.registrationEnabled ? '已开启' : '已关闭' }}
            </span>
          </p>
        </div>
        <button
          class="btn"
          :class="vm.registrationEnabled ? 'btn-outline' : 'btn-primary'"
          :disabled="vm.savingRegistration"
          @click="vm.handleToggleRegistration"
        >
          {{ vm.savingRegistration ? '保存中...' : (vm.registrationEnabled ? '关闭注册' : '开启注册') }}
        </button>
      </div>
    </div>
  </section>
</template>

<style scoped>
.av-section {
  padding: 0;
}

.av-title {
  margin: 0 0 20px;
}

.av-stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(170px, 1fr));
  gap: 12px;
  margin-bottom: 20px;
}

.av-stat-card {
  background: var(--c-surface);
  border: 1px solid var(--c-border);
  border-radius: var(--radius-lg);
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.av-stat-card--accent {
  background: var(--c-danger-light);
  border-color: var(--c-danger-soft);
}

.av-stat__value {
  font-size: var(--text-2xl);
  font-weight: 700;
  color: var(--c-text);
}

.av-stat-card--accent .av-stat__value {
  color: var(--c-danger);
}

.av-stat__label {
  font-size: var(--text-sm);
  color: var(--c-text-muted);
}

.av-reg-card {
  max-width: 500px;
}

.av-reg-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}

.av-reg-title {
  margin: 0 0 4px;
}

.av-reg-desc {
  color: var(--c-text-muted);
  font-size: var(--text-sm);
  margin: 0;
}

@media (max-width: 768px) {
  .av-stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .av-reg-row {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
