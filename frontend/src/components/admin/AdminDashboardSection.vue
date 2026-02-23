<script setup lang="ts">
import { computed, proxyRefs } from 'vue'

import type { AdminDashboardModel } from '../../composables/admin/useAdminDashboard'
import AppDropdown from '../AppDropdown.vue'

const props = defineProps<{
  model: AdminDashboardModel
}>()

const vm = proxyRefs(props.model)

const completionRate = computed(() => `${((vm.dashboard.completion_rate || 0) * 100).toFixed(1)}%`)
const trendDayOptions = [
  { value: 7, label: '近 7 天' },
  { value: 14, label: '近 14 天' },
  { value: 30, label: '近 30 天' },
]

const peakValue = computed(() => {
  const all = vm.dashboard.trends.flatMap((d) => [d.new_users, d.new_tasks, d.new_reports, d.new_messages])
  return Math.max(1, ...all)
})

function ratio(v: number) {
  return Math.max(6, Math.round((v / peakValue.value) * 100))
}
</script>

<template>
  <section class="av-dashboard">
    <div class="av-head">
      <AppDropdown
        :model-value="vm.trendDays"
        :options="trendDayOptions"
        width="128px"
        min-width="128px"
        @update:model-value="vm.loadDashboard(Number($event || 7))"
      />
    </div>

    <div class="av-stats-grid">
      <div class="av-stat-card">
        <i class="fa-solid fa-users av-stat-card__deco av-stat-card__deco--blue"></i>
        <span class="av-stat-card__label">用户总数</span>
        <div class="av-stat-card__row">
          <strong class="av-stat-card__value">{{ vm.dashboard.total_users }}</strong>
        </div>
        <span class="av-stat-card__meta">24h 活跃 {{ vm.dashboard.active_users_24h }} / 7天新增 {{ vm.dashboard.new_users_7d }}</span>
      </div>
      <div class="av-stat-card">
        <i class="fa-solid fa-list-check av-stat-card__deco av-stat-card__deco--green"></i>
        <span class="av-stat-card__label">任务池</span>
        <div class="av-stat-card__row">
          <strong class="av-stat-card__value">{{ vm.dashboard.total_tasks }}</strong>
        </div>
        <span class="av-stat-card__meta">进行中 {{ vm.dashboard.in_progress_tasks }} / 已完成 {{ vm.dashboard.completed_tasks }}</span>
      </div>
      <div class="av-stat-card">
        <i class="fa-solid fa-chart-pie av-stat-card__deco av-stat-card__deco--amber"></i>
        <span class="av-stat-card__label">任务完成率</span>
        <div class="av-stat-card__row">
          <strong class="av-stat-card__value">{{ completionRate }}</strong>
        </div>
        <span class="av-stat-card__meta">逾期未完 {{ vm.dashboard.overdue_open_tasks }} / 均价 ¥{{ vm.dashboard.avg_task_price }}</span>
      </div>
      <div class="av-stat-card">
        <i class="fa-solid fa-shield-halved av-stat-card__deco av-stat-card__deco--rose"></i>
        <span class="av-stat-card__label">风险告警</span>
        <div class="av-stat-card__row">
          <strong class="av-stat-card__value">{{ vm.dashboard.pending_reports }}</strong>
        </div>
        <span class="av-stat-card__meta">近7天通过 {{ vm.dashboard.approved_reports_7d }} / 驳回 {{ vm.dashboard.rejected_reports_7d }}</span>
      </div>
      <div class="av-stat-card">
        <i class="fa-solid fa-comments av-stat-card__deco av-stat-card__deco--cyan"></i>
        <span class="av-stat-card__label">聊天活跃</span>
        <div class="av-stat-card__row">
          <strong class="av-stat-card__value">{{ vm.dashboard.chat_messages_24h }}</strong>
        </div>
        <span class="av-stat-card__meta">消息（24h） / 活跃接单者 {{ vm.dashboard.active_workers }}</span>
      </div>
      <div class="av-stat-card">
        <i class="fa-solid fa-bolt av-stat-card__deco av-stat-card__deco--violet"></i>
        <span class="av-stat-card__label">运营优先级</span>
        <div class="av-stat-card__row">
          <strong class="av-stat-card__value">{{ vm.dashboard.pinned_tasks + vm.dashboard.urgent_tasks }}</strong>
        </div>
        <span class="av-stat-card__meta">置顶 {{ vm.dashboard.pinned_tasks }} / 加急 {{ vm.dashboard.urgent_tasks }}</span>
      </div>
    </div>

    <div class="av-main-grid">
      <div class="card av-trend-card">
        <div class="av-trend-card__head">
          <div>
            <h3>趋势对比</h3>
            <p>多维趋势柱状图，帮助快速识别峰值与异常波动</p>
          </div>
        </div>
        <div class="av-trend-board">
          <div v-for="item in vm.dashboard.trends" :key="item.date" class="av-trend-col">
            <div class="av-bars">
              <span class="av-bar av-bar--users" :style="{ height: `${ratio(item.new_users)}%` }" />
              <span class="av-bar av-bar--tasks" :style="{ height: `${ratio(item.new_tasks)}%` }" />
              <span class="av-bar av-bar--reports" :style="{ height: `${ratio(item.new_reports)}%` }" />
              <span class="av-bar av-bar--messages" :style="{ height: `${ratio(item.new_messages)}%` }" />
            </div>
            <span class="av-trend-date">{{ item.date }}</span>
          </div>
        </div>
        <div class="av-legend">
          <span><i class="av-dot av-dot--users"></i> 新增用户</span>
          <span><i class="av-dot av-dot--tasks"></i> 新增任务</span>
          <span><i class="av-dot av-dot--reports"></i> 举报/申诉</span>
          <span><i class="av-dot av-dot--messages"></i> 聊天消息</span>
        </div>
      </div>

      <div class="card av-risk-card">
        <div class="av-risk-card__head">
          <h3>高风险用户</h3>
          <span v-if="vm.dashboard.top_risk_users.length" class="av-risk-card__badge">
            {{ vm.dashboard.top_risk_users.length }} 个预警
          </span>
        </div>
        <p>综合封禁次数、被拉黑次数、被举报次数计算</p>
        <div v-if="vm.dashboard.top_risk_users.length" class="av-risk-list">
          <div v-for="(u, idx) in vm.dashboard.top_risk_users" :key="u.user_id" class="av-risk-row">
            <div class="av-risk-row__dot">
              <span class="av-risk-row__indicator" :class="idx < 2 ? 'av-risk-row__indicator--danger' : 'av-risk-row__indicator--warning'" />
            </div>
            <div class="av-risk-row__body">
              <div class="av-risk-row__name">#{{ u.user_id }} {{ u.display_name }}</div>
              <div class="av-risk-row__chips">
                <span class="badge badge-red">封禁 {{ u.ban_count }}</span>
                <span class="badge badge-amber">被拉黑 {{ u.blocked_by_count }}</span>
                <span class="badge badge-default">被举报 {{ u.report_received_count }}</span>
              </div>
            </div>
          </div>
        </div>
        <div v-else class="av-risk-empty">
          <i class="fa-regular fa-circle-check"></i>
          <span>暂无高风险用户</span>
        </div>
      </div>
    </div>

    <div class="card av-reg-card">
      <div class="av-reg-row">
        <div>
          <h4 class="av-reg-title">用户注册开关</h4>
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
.av-dashboard {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.av-head {
  display: flex;
  justify-content: flex-end;
  align-items: center;
}

.av-stats-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.av-stat-card {
  position: relative;
  overflow: hidden;
  border-radius: var(--radius-2xl);
  padding: 22px;
  background: #fff;
  border: 1px solid rgba(226, 232, 240, 0.6);
  box-shadow: var(--shadow-card);
  display: flex;
  flex-direction: column;
  gap: 6px;
  transition: box-shadow 200ms var(--ease);
}

.av-stat-card:hover {
  box-shadow: var(--shadow-card-hover);
}

.av-stat-card__deco {
  position: absolute;
  top: 12px;
  right: 14px;
  font-size: 44px;
  opacity: 0.07;
  transition: opacity 200ms var(--ease);
}

.av-stat-card:hover .av-stat-card__deco {
  opacity: 0.14;
}

.av-stat-card__deco--blue { color: #3b82f6; }
.av-stat-card__deco--green { color: #059669; }
.av-stat-card__deco--amber { color: #d97706; }
.av-stat-card__deco--rose { color: #ef4444; }
.av-stat-card__deco--cyan { color: #06b6d4; }
.av-stat-card__deco--violet { color: #8b5cf6; }

.av-stat-card__label {
  color: #64748b;
  font-size: 13px;
  font-weight: 500;
  position: relative;
  z-index: 1;
}

.av-stat-card__row {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  position: relative;
  z-index: 1;
}

.av-stat-card__value {
  font-size: 32px;
  line-height: 1;
  color: var(--c-text);
  letter-spacing: -0.02em;
}

.av-stat-card__meta {
  font-size: 12px;
  color: #94a3b8;
  position: relative;
  z-index: 1;
}

.av-main-grid {
  display: grid;
  grid-template-columns: minmax(0, 2fr) minmax(0, 1fr);
  gap: 16px;
}

.av-trend-card {
  padding: 24px;
}

.av-trend-card__head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 6px;
}

.av-trend-card h3,
.av-risk-card h3 {
  margin: 0;
  font-size: 17px;
  font-weight: 700;
  color: var(--c-text);
}

.av-trend-card p,
.av-risk-card p {
  margin: 4px 0 16px;
  color: #94a3b8;
  font-size: 12px;
}

.av-trend-board {
  height: 220px;
  padding: 14px 14px 10px;
  border-radius: 16px;
  background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
  border: 1px solid rgba(226, 232, 240, 0.6);
  display: grid;
  grid-auto-flow: column;
  grid-auto-columns: minmax(20px, 1fr);
  align-items: end;
  gap: 7px;
}

.av-trend-col {
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 0;
}

.av-bars {
  width: 100%;
  height: 176px;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  gap: 3px;
}

.av-bar {
  width: 5px;
  border-radius: 999px;
  min-height: 6px;
  transition: height 0.3s var(--ease);
}

.av-bar--users { background: #3b82f6; }
.av-bar--tasks { background: #059669; }
.av-bar--reports { background: #ef4444; }
.av-bar--messages { background: #06b6d4; }

.av-trend-date {
  margin-top: 6px;
  font-size: 10px;
  color: #94a3b8;
}

.av-legend {
  margin-top: 12px;
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  color: #64748b;
  font-size: 12px;
}

.av-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 999px;
  margin-right: 5px;
}

.av-dot--users { background: #3b82f6; }
.av-dot--tasks { background: #059669; }
.av-dot--reports { background: #ef4444; }
.av-dot--messages { background: #06b6d4; }

.av-risk-card {
  padding: 24px;
}

.av-risk-card__head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.av-risk-card__badge {
  font-size: 11px;
  font-weight: 600;
  color: #ef4444;
  background: rgba(239, 68, 68, 0.06);
  padding: 3px 10px;
  border-radius: var(--radius-full);
}

.av-risk-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.av-risk-row {
  display: flex;
  gap: 12px;
}

.av-risk-row__dot {
  position: relative;
  padding-top: 4px;
}

.av-risk-row__indicator {
  display: block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.av-risk-row__indicator--danger {
  background: #ef4444;
  box-shadow: 0 0 8px rgba(239, 68, 68, 0.5);
}

.av-risk-row__indicator--warning {
  background: #f59e0b;
  box-shadow: 0 0 8px rgba(245, 158, 11, 0.5);
}

.av-risk-row__body {
  flex: 1;
}

.av-risk-row__name {
  font-weight: 600;
  font-size: 13px;
  color: var(--c-text);
  margin-bottom: 6px;
}

.av-risk-row__chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.av-risk-empty {
  color: #94a3b8;
  font-size: 13px;
  padding: 24px 0;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}

.av-risk-empty i {
  font-size: 28px;
  color: #cbd5e1;
}

.av-reg-card {
  border: 1.5px dashed rgba(203, 213, 225, 0.7);
  background: rgba(255, 255, 255, 0.5);
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
  color: #94a3b8;
  font-size: 13px;
  margin: 0;
}

@media (max-width: 1150px) {
  .av-stats-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .av-main-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .av-stats-grid {
    grid-template-columns: 1fr;
  }

  .av-reg-row {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
