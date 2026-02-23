<script setup lang="ts">
import { onMounted, onUnmounted, proxyRefs } from 'vue'

import type { AdminUsersModel } from '../../composables/admin/useAdminUsers'
import { formatShort } from '../../utils/time'
import AdminReviewModal from './AdminReviewModal.vue'
import AdminUserProfileDrawer from './AdminUserProfileDrawer.vue'

const props = defineProps<{
  model: AdminUsersModel
}>()

const vm = proxyRefs(props.model)

function banLabels(user: { is_banned: boolean; ban_publish: boolean; ban_accept: boolean; ban_contact: boolean }): string[] {
  const labels: string[] = []
  if (user.is_banned) labels.push('登录')
  if (user.ban_publish) labels.push('发布')
  if (user.ban_accept) labels.push('接单')
  if (user.ban_contact) labels.push('联系')
  return labels
}

function onClickOutside(e: MouseEvent) {
  vm.onClickOutsideUnban(e)
}

onMounted(() => {
  document.addEventListener('mousedown', onClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('mousedown', onClickOutside)
})
</script>

<template>
  <section class="av-users">
    <div class="av-users__head">
      <div>
        <h2>用户管理</h2>
        <p>支持封禁管理、资料修改、黑名单代管、360画像查看</p>
      </div>
      <span class="av-users__total">共 {{ vm.userTotal }} 人</span>
    </div>

    <div class="av-users__search">
      <i class="fa-solid fa-magnifying-glass"></i>
      <input v-model="vm.userSearch" class="form-input" placeholder="搜索账号/姓名/昵称" />
    </div>

    <div v-if="vm.userLoading" class="av-users__loading"><div class="spinner"></div></div>
    <div v-else-if="vm.userList.length === 0" class="av-users__empty">暂无匹配用户</div>

    <template v-else>
      <div class="av-users__table-wrap">
        <table class="av-users__table">
          <thead>
            <tr>
              <th>用户</th>
              <th>状态</th>
              <th>评分</th>
              <th>任务</th>
              <th>风险</th>
              <th>最近活跃</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="user in vm.userList" :key="user.id" :class="{ 'av-users__tr--warn': banLabels(user).length > 0 }">
              <td>
                <div class="av-user-main">
                  <strong>{{ user.display_name }}</strong>
                  <span>#{{ user.id }} · {{ user.account }}</span>
                </div>
              </td>
              <td>
                <div class="av-user-status">
                  <span class="badge" :class="user.is_active ? 'badge-green' : 'badge-red'">{{ user.is_active ? '启用' : '停用' }}</span>
                  <span v-if="banLabels(user).length" class="badge badge-red">{{ banLabels(user).join('/') }}</span>
                  <span v-else class="badge badge-default">正常</span>
                </div>
              </td>
              <td>
                <div class="av-user-score">
                  <span>发 {{ user.publisher_rating_avg.toFixed(1) }}</span>
                  <span>接 {{ user.worker_rating_avg.toFixed(1) }}</span>
                </div>
              </td>
              <td>
                <div class="av-user-task">
                  <span>发 {{ user.published_task_count }}</span>
                  <span>接 {{ user.accepted_task_count }}</span>
                  <span>完 {{ user.completed_task_count }}</span>
                </div>
              </td>
              <td>
                <div class="av-user-risk">
                  <span>封禁 {{ user.ban_count }}</span>
                  <span>被拉黑 {{ user.blocked_by_count }}</span>
                  <span>被举报 {{ user.report_received_count }}</span>
                </div>
              </td>
              <td>{{ user.last_active ? formatShort(user.last_active) : '从未' }}</td>
              <td>
                <div class="av-user-actions">
                  <button class="av-action-btn" title="查看360画像" @click="vm.openUserProfile(user)">
                    <i class="fa-solid fa-id-card-clip"></i>
                  </button>
                  <button class="av-action-btn av-action-btn--ban" title="封禁/修改封禁" @click="vm.openBanModal(user)">
                    <i class="fa-solid fa-ban"></i>
                  </button>
                  <div class="av-unban-wrap">
                    <button
                      v-if="user.is_banned || user.ban_publish || user.ban_accept || user.ban_contact"
                      class="av-action-btn av-action-btn--unban"
                      title="解封"
                      @click="vm.toggleUnbanMenu(user.id)"
                    >
                      <i class="fa-solid fa-lock-open"></i>
                    </button>
                    <Transition name="fade">
                      <div v-if="vm.unbanOpenId === user.id" class="av-unban-menu">
                        <button :disabled="vm.unbanSubmitting" @click="vm.confirmUnban(user, false)">有责解封</button>
                        <button :disabled="vm.unbanSubmitting" @click="vm.confirmUnban(user, true)">无责解封</button>
                      </div>
                    </Transition>
                  </div>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="vm.totalPages > 1" class="av-pagination">
        <button class="btn btn-ghost btn-sm" :disabled="vm.userPage <= 1" @click="vm.goPage(vm.userPage - 1)">
          <i class="fa-solid fa-chevron-left"></i>
        </button>
        <span>第 {{ vm.userPage }} / {{ vm.totalPages }} 页</span>
        <button class="btn btn-ghost btn-sm" :disabled="vm.userPage >= vm.totalPages" @click="vm.goPage(vm.userPage + 1)">
          <i class="fa-solid fa-chevron-right"></i>
        </button>
      </div>
    </template>
  </section>

  <AdminReviewModal
    :show="vm.showBanModal"
    :submitting="vm.banSubmitting"
    :title="vm.banTargetUser && (vm.banTargetUser.is_banned || vm.banTargetUser.ban_publish || vm.banTargetUser.ban_accept || vm.banTargetUser.ban_contact) ? '修改封禁' : '封禁用户'"
    :target-name="vm.banTargetUser ? `${vm.banTargetUser.display_name}（${vm.banTargetUser.account}）` : ''"
    :ban-count="vm.banTargetUser?.ban_count ?? 0"
    :preselected-types="vm.banPreselectedTypes"
    confirm-label="确认限制"
    @close="vm.closeBanModal"
    @confirm="vm.confirmBan"
  />

  <AdminUserProfileDrawer :model="props.model" />
</template>

<style scoped>
.av-users {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.av-users__head {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 12px;
}

.av-users__head h2 {
  margin: 0;
}

.av-users__head p {
  margin: 4px 0 0;
  color: #94a3b8;
  font-size: 13px;
}

.av-users__total {
  color: #94a3b8;
  font-size: 13px;
}

.av-users__search {
  position: relative;
  max-width: 420px;
}

.av-users__search i {
  position: absolute;
  left: 14px;
  top: 50%;
  transform: translateY(-50%);
  color: #94a3b8;
  font-size: 13px;
}

.av-users__search :deep(.form-input) {
  padding-left: 36px;
  border-radius: var(--radius-full);
  border: none;
  background: #f1f5f9;
}

.av-users__search :deep(.form-input:focus) {
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.12);
}

.av-users__table-wrap {
  overflow: auto;
  border: 1px solid rgba(226, 232, 240, 0.6);
  border-radius: var(--radius-2xl);
  background: #fff;
  box-shadow: var(--shadow-card);
}

.av-users__table {
  width: 100%;
  border-collapse: collapse;
  min-width: 920px;
}

.av-users__table th {
  text-align: left;
  font-size: 11px;
  color: #94a3b8;
  padding: 14px 14px;
  background: rgba(248, 250, 252, 0.5);
  border-bottom: 1px solid rgba(226, 232, 240, 0.6);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-weight: 500;
}

.av-users__table td {
  padding: 14px;
  border-bottom: 1px solid rgba(241, 245, 249, 0.8);
  font-size: 13px;
  color: var(--c-text);
  vertical-align: middle;
}

.av-users__table tr:last-child td {
  border-bottom: none;
}

.av-users__table tbody tr {
  transition: background 200ms var(--ease);
}

.av-users__table tbody tr:hover {
  background: rgba(248, 250, 252, 0.5);
}

.av-users__tr--warn {
  background: rgba(255, 247, 237, 0.4) !important;
}

.av-user-main strong {
  display: block;
  line-height: 1.2;
  font-size: 13px;
  color: var(--c-text);
}

.av-user-main span {
  color: #94a3b8;
  font-size: 12px;
}

.av-user-status,
.av-user-score,
.av-user-task,
.av-user-risk {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  line-height: 1.2;
}

.av-user-score span,
.av-user-task span,
.av-user-risk span {
  font-size: 12px;
  color: #64748b;
}

.av-user-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  position: relative;
}

.av-action-btn {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-md);
  border: none;
  background: #f1f5f9;
  color: #64748b;
  font-size: 13px;
  transition: all 200ms var(--ease);
}

@media (hover: hover) {
  .av-action-btn:hover {
    background: rgba(59, 130, 246, 0.08);
    color: var(--c-accent);
  }
}

.av-action-btn--ban {
  color: #ea580c;
  background: rgba(255, 237, 213, 0.6);
}

.av-action-btn--ban:hover {
  background: rgba(255, 237, 213, 0.9) !important;
  color: #c2410c !important;
}

.av-action-btn--unban {
  color: #059669;
  background: rgba(220, 252, 231, 0.6);
}

.av-action-btn--unban:hover {
  background: rgba(220, 252, 231, 0.9) !important;
  color: #047857 !important;
}

.av-unban-menu {
  position: absolute;
  top: calc(100% + 6px);
  right: 0;
  z-index: 5;
  background: #fff;
  border: 1px solid rgba(226, 232, 240, 0.6);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  display: flex;
  flex-direction: column;
  min-width: 100px;
  overflow: hidden;
}

.av-unban-menu button {
  border: none;
  background: transparent;
  padding: 9px 12px;
  font-size: 13px;
  text-align: left;
  color: var(--c-text);
  transition: background 200ms var(--ease);
}

.av-unban-menu button:hover:not(:disabled) {
  background: #f1f5f9;
}

.av-users__loading,
.av-users__empty {
  display: grid;
  place-items: center;
  padding: 40px 0;
  color: #94a3b8;
}

.av-pagination {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  color: #64748b;
  font-size: 13px;
}
</style>
