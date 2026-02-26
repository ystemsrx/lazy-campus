<script setup lang="ts">
import { proxyRefs } from 'vue'

import type { AdminActionLogsModel } from '../../composables/admin/useAdminActionLogs'
import { formatShort } from '../../utils/time'
import AppDropdown from '../AppDropdown.vue'

const ACTION_LABELS: Record<string, string> = {
  review_report: '审核举报',
  ban_user: '封禁用户',
  modify_ban: '修改处罚',
  unban_user: '解封用户（有责）',
  unban_user_innocent: '解封用户（无责）',
  update_user_profile: '修改用户资料',
  admin_add_blacklist: '添加黑名单',
  admin_remove_blacklist: '移除黑名单',
  admin_delete_task: '删除任务',
  admin_update_task: '修改任务属性',
  push_notification: '推送通知/公告',
  delete_notification_batch: '批量删除通知',
  registration_toggle: '注册开关切换',
}

const TARGET_TYPE_LABELS: Record<string, string> = {
  report: '举报',
  user: '用户',
  task: '任务',
  notification: '通知',
  platform_setting: '平台设置',
}

const ACTION_COLORS: Record<string, string> = {
  ban_user: 'badge-danger',
  modify_ban: 'badge-danger',
  unban_user: 'badge-success',
  unban_user_innocent: 'badge-success',
  review_report: 'badge-warning',
  admin_delete_task: 'badge-danger',
  push_notification: 'badge-info',
  delete_notification_batch: 'badge-muted',
  registration_toggle: 'badge-info',
  update_user_profile: 'badge-default',
  admin_update_task: 'badge-default',
  admin_add_blacklist: 'badge-warning',
  admin_remove_blacklist: 'badge-muted',
}

function actionLabel(action: string): string {
  return ACTION_LABELS[action] || action
}

function targetTypeLabel(type: string): string {
  return TARGET_TYPE_LABELS[type] || type
}

function badgeClass(action: string): string {
  return ACTION_COLORS[action] || 'badge-default'
}

const props = defineProps<{
  model: AdminActionLogsModel
}>()

const vm = proxyRefs(props.model)

function dropdownOptions() {
  return vm.actionOptions.map((v: string) => ({
    value: v,
    label: v === 'all' ? '全部动作' : actionLabel(v),
  }))
}
</script>

<template>
  <section class="av-logs">
    <div class="av-logs__toolbar">
      <div class="av-logs__search">
        <i class="fa-solid fa-magnifying-glass"></i>
        <input v-model="vm.query" class="form-input" placeholder="搜索动作/目标/详情" />
      </div>
      <AppDropdown v-model="vm.actionFilter" :options="dropdownOptions()" width="200px" min-width="200px" />
      <span class="av-logs__total">共 {{ vm.total }} 条</span>
    </div>

    <div class="av-logs__table-wrap">
      <table class="av-logs__table">
        <thead>
          <tr>
            <th>时间</th>
            <th>管理员</th>
            <th>动作</th>
            <th>目标</th>
            <th>详情</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="vm.loading">
            <td colspan="5" class="av-logs__state"><div class="spinner"></div></td>
          </tr>
          <tr v-else-if="vm.logs.length === 0">
            <td colspan="5" class="av-logs__state">
              <i class="fa-regular fa-folder-open" style="font-size: 20px; margin-bottom: 6px; display: block; color: #cbd5e1"></i>
              暂无日志
            </td>
          </tr>
          <template v-else>
            <tr v-for="log in vm.logs" :key="log.id">
              <td class="av-logs__time">
                <i class="fa-regular fa-clock"></i>
                {{ formatShort(log.created_at) }}
              </td>
              <td>
                <span class="av-logs__admin">
                  <i class="fa-solid fa-user-shield"></i>
                  {{ log.admin_identifier }}
                </span>
              </td>
              <td>
                <span class="badge" :class="badgeClass(log.action)">{{ actionLabel(log.action) }}</span>
              </td>
              <td>
                <span class="av-logs__target">
                  {{ targetTypeLabel(log.target_type) }}
                  <span class="av-logs__target-id">#{{ log.target_id }}</span>
                </span>
              </td>
              <td class="av-logs__detail">{{ log.detail || '-' }}</td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>

    <div v-if="vm.totalPages > 1" class="av-pagination">
      <button class="btn btn-ghost btn-sm" :disabled="vm.page <= 1" @click="vm.goPage(vm.page - 1)">
        <i class="fa-solid fa-chevron-left"></i>
      </button>
      <span>第 {{ vm.page }} / {{ vm.totalPages }} 页</span>
      <button class="btn btn-ghost btn-sm" :disabled="vm.page >= vm.totalPages" @click="vm.goPage(vm.page + 1)">
        <i class="fa-solid fa-chevron-right"></i>
      </button>
    </div>
  </section>
</template>

<style scoped>
.av-logs {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.av-logs__toolbar {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  align-items: center;
}

.av-logs__search {
  position: relative;
  width: min(420px, 100%);
}

.av-logs__search i {
  position: absolute;
  left: 14px;
  top: 50%;
  transform: translateY(-50%);
  color: #94a3b8;
  font-size: 13px;
}

.av-logs__search :deep(.form-input) {
  padding-left: 36px;
  border-radius: var(--radius-full);
  border: none;
  background: #f1f5f9;
}

.av-logs__search :deep(.form-input:focus) {
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.12);
}

.av-logs__total {
  margin-left: auto;
  color: #94a3b8;
  font-size: 13px;
  white-space: nowrap;
}

.av-logs__table-wrap {
  overflow: auto;
  border: 1px solid rgba(226, 232, 240, 0.6);
  border-radius: var(--radius-2xl);
  background: #fff;
  box-shadow: var(--shadow-card);
}

.av-logs__table {
  width: 100%;
  border-collapse: collapse;
  min-width: 880px;
}

.av-logs__table th {
  text-align: left;
  font-size: 11px;
  color: #94a3b8;
  padding: 14px;
  background: rgba(248, 250, 252, 0.5);
  border-bottom: 1px solid rgba(226, 232, 240, 0.6);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-weight: 500;
}

.av-logs__table td {
  padding: 14px;
  border-bottom: 1px solid rgba(241, 245, 249, 0.8);
  font-size: 13px;
  color: var(--c-text);
}

.av-logs__table tr:last-child td {
  border-bottom: none;
}

.av-logs__table tbody tr {
  transition: background 200ms var(--ease);
}

.av-logs__table tbody tr:hover {
  background: rgba(248, 250, 252, 0.5);
}

.av-logs__time {
  color: #64748b;
  white-space: nowrap;
}

.av-logs__time i {
  margin-right: 6px;
  font-size: 12px;
  color: #94a3b8;
}

.av-logs__admin {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #475569;
  font-weight: 500;
}

.av-logs__admin i {
  font-size: 12px;
  color: #94a3b8;
}

.av-logs__target {
  color: #475569;
}

.av-logs__target-id {
  color: #94a3b8;
  font-size: 12px;
  margin-left: 2px;
}

.av-logs__detail {
  color: #64748b;
  max-width: 420px;
  white-space: normal;
  word-break: break-word;
}

.av-logs__state {
  text-align: center;
  color: #94a3b8;
  padding: 32px;
}

.badge {
  display: inline-block;
  padding: 3px 10px;
  border-radius: 9999px;
  font-size: 12px;
  font-weight: 500;
  line-height: 1.5;
  white-space: nowrap;
}

.badge-default {
  background: #f1f5f9;
  color: #475569;
}

.badge-danger {
  background: #fef2f2;
  color: #dc2626;
}

.badge-success {
  background: #f0fdf4;
  color: #16a34a;
}

.badge-warning {
  background: #fffbeb;
  color: #d97706;
}

.badge-info {
  background: #eff6ff;
  color: #2563eb;
}

.badge-muted {
  background: #f8fafc;
  color: #94a3b8;
}

.av-pagination {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 10px;
  color: #64748b;
  font-size: 13px;
}
</style>
