<script setup lang="ts">
import { onMounted, onUnmounted, proxyRefs } from 'vue'

import type { AdminUsersModel } from '../../composables/admin/useAdminUsers'
import { formatShort } from '../../utils/time'
import AdminBanModal from './AdminBanModal.vue'

const props = defineProps<{
  model: AdminUsersModel
}>()

const vm = proxyRefs(props.model)

onMounted(() => {
  document.addEventListener('mousedown', vm.onClickOutsideUnban)
})

onUnmounted(() => {
  document.removeEventListener('mousedown', vm.onClickOutsideUnban)
})
</script>

<template>
  <section class="av-section">
    <div class="av-users-header">
      <h2>用户管理</h2>
      <span class="av-users-total">共 {{ vm.userTotal }} 人</span>
    </div>

    <div class="av-users-search">
      <i class="fa-solid fa-magnifying-glass av-search-icon"></i>
      <input
        v-model="vm.userSearch"
        class="form-input av-search-input"
        placeholder="搜索账号、姓名或昵称…"
      />
    </div>

    <div v-if="vm.userLoading" class="av-users-loading">
      <div class="spinner"></div>
    </div>

    <div v-else-if="vm.userList.length === 0" class="av-empty">
      <i class="fa-regular fa-user av-empty__icon"></i>
      {{ vm.userSearch ? '未找到匹配用户' : '暂无用户' }}
    </div>

    <template v-else>
      <div class="av-user-table">
        <div class="av-user-row av-user-row--header">
          <span class="av-user-col av-user-col--account">账号</span>
          <span class="av-user-col av-user-col--name">姓名</span>
          <span class="av-user-col av-user-col--nickname">昵称</span>
          <span class="av-user-col av-user-col--role">角色</span>
          <span class="av-user-col av-user-col--status">状态</span>
          <span class="av-user-col av-user-col--bancount">封禁</span>
          <span class="av-user-col av-user-col--action">操作</span>
        </div>
        <div
          v-for="user in vm.userList"
          :key="user.id"
          class="av-user-row"
          :class="{ 'av-user-row--banned': user.is_banned }"
        >
          <span class="av-user-col av-user-col--account" :title="user.account">{{ user.account }}</span>
          <span class="av-user-col av-user-col--name" :title="user.name">{{ user.name }}</span>
          <span class="av-user-col av-user-col--nickname" :title="user.nickname || '-'">{{ user.nickname || '-' }}</span>
          <span class="av-user-col av-user-col--role">
            <span class="badge" :class="user.role === 'admin' ? 'badge-blue' : 'badge-default'">
              {{ user.role === 'admin' ? '管理员' : '用户' }}
            </span>
          </span>
          <span class="av-user-col av-user-col--status">
            <span v-if="user.is_banned" class="badge badge-red" :title="user.ban_reason || ''">已封禁</span>
            <span v-else class="badge badge-green">正常</span>
            <span v-if="user.is_banned && user.ban_until" class="av-ban-until">至 {{ formatShort(user.ban_until) }}</span>
          </span>
          <span class="av-user-col av-user-col--bancount" :class="{ 'av-bancount--warn': user.ban_count > 0 }">
            {{ user.ban_count }}
          </span>
          <span class="av-user-col av-user-col--action">
            <button
              v-if="!user.is_banned"
              class="av-action-btn av-action-btn--ban"
              title="封禁该用户"
              @click="vm.openBanModal(user)"
            >
              <i class="fa-solid fa-ban"></i>
            </button>
            <div v-else class="av-unban-wrap">
              <button
                class="av-action-btn av-action-btn--unban"
                title="解封该用户"
                @click="vm.toggleUnbanMenu(user.id)"
              >
                <i class="fa-solid fa-lock-open"></i>
              </button>
              <Transition name="av-dropdown">
                <div v-if="vm.unbanOpenId === user.id" class="av-unban-menu">
                  <button
                    class="av-unban-menu__item"
                    :disabled="vm.unbanSubmitting"
                    @click="vm.confirmUnban(user, false)"
                  >
                    <i class="fa-solid fa-gavel av-unban-icon--liable"></i>
                    有责解封
                  </button>
                  <button
                    class="av-unban-menu__item"
                    :disabled="vm.unbanSubmitting"
                    @click="vm.confirmUnban(user, true)"
                  >
                    <i class="fa-solid fa-shield-halved av-unban-icon--innocent"></i>
                    无责解封
                  </button>
                </div>
              </Transition>
            </div>
          </span>
        </div>
      </div>

      <div v-if="vm.totalPages > 1" class="av-pagination">
        <button class="btn btn-ghost btn-sm" :disabled="vm.userPage <= 1" @click="vm.goPage(vm.userPage - 1)">
          <i class="fa-solid fa-chevron-left"></i>
        </button>
        <template v-for="page in vm.totalPages" :key="page">
          <button
            v-if="page === 1 || page === vm.totalPages || (page >= vm.userPage - 2 && page <= vm.userPage + 2)"
            class="av-page-btn"
            :class="{ 'av-page-btn--active': page === vm.userPage }"
            @click="vm.goPage(page)"
          >
            {{ page }}
          </button>
          <span
            v-else-if="page === vm.userPage - 3 || page === vm.userPage + 3"
            class="av-page-ellipsis"
          >
            …
          </span>
        </template>
        <button
          class="btn btn-ghost btn-sm"
          :disabled="vm.userPage >= vm.totalPages"
          @click="vm.goPage(vm.userPage + 1)"
        >
          <i class="fa-solid fa-chevron-right"></i>
        </button>
      </div>
    </template>
  </section>

  <AdminBanModal
    :show="vm.showBanModal"
    :user="vm.banTargetUser"
    :reason="vm.banReasonInput"
    :submitting="vm.banSubmitting"
    @update:reason="vm.banReasonInput = $event"
    @close="vm.closeBanModal"
    @confirm="vm.confirmBan"
  />
</template>

<style scoped>
.av-section {
  padding: 0;
}

.av-users-header {
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 16px;
}

.av-users-total {
  font-size: var(--text-sm);
  color: var(--c-text-muted);
  font-weight: 500;
}

.av-users-search {
  position: relative;
  max-width: 400px;
  margin-bottom: 16px;
}

.av-search-icon {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--c-text-muted);
  font-size: var(--text-sm);
  pointer-events: none;
}

.av-search-input {
  padding-left: 36px !important;
}

.av-users-loading {
  display: flex;
  justify-content: center;
  padding: 40px 0;
}

.av-empty {
  text-align: center;
  color: var(--c-text-muted);
  padding: 48px 20px;
}

.av-empty__icon {
  font-size: 36px;
  display: block;
  margin-bottom: 12px;
  color: var(--c-border);
}

.av-user-table {
  border: 1px solid var(--c-border);
  border-radius: var(--radius-lg);
  background: var(--c-surface);
}

.av-user-row {
  display: grid;
  grid-template-columns: 1.2fr 1fr 1fr 80px 80px 52px 64px;
  align-items: center;
  padding: 0 16px;
  min-height: 46px;
  font-size: var(--text-sm);
  border-bottom: 1px solid var(--c-border-light);
  transition: background var(--dur-fast) var(--ease);
}

.av-user-row:last-child {
  border-bottom: none;
  border-radius: 0 0 var(--radius-lg) var(--radius-lg);
}

.av-user-row:not(.av-user-row--header):hover {
  background: var(--c-border-light);
}

.av-user-row--header {
  background: var(--c-bg);
  font-weight: 600;
  color: var(--c-text-muted);
  font-size: var(--text-xs);
  text-transform: uppercase;
  letter-spacing: 0.03em;
  min-height: 40px;
  border-bottom: 1px solid var(--c-border);
  border-radius: var(--radius-lg) var(--radius-lg) 0 0;
}

.av-user-row--banned {
  background: var(--c-danger-light);
}

.av-user-row--banned:hover {
  background: var(--c-danger-soft) !important;
}

.av-user-col {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  padding: 4px 0;
}

.av-user-col--action {
  display: flex;
  justify-content: center;
  overflow: visible;
  position: relative;
}

.av-user-col--bancount {
  text-align: center;
  font-weight: 600;
  color: var(--c-text-muted);
}

.av-bancount--warn {
  color: var(--c-danger) !important;
}

.av-ban-until {
  display: block;
  font-size: 11px;
  color: var(--c-danger);
  margin-top: 2px;
  white-space: nowrap;
}

.av-action-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  font-size: 14px;
  transition: all var(--dur-fast) var(--ease);
}

.av-action-btn--ban {
  color: var(--c-text-muted);
}

.av-action-btn--ban:hover {
  color: var(--c-danger);
  background: var(--c-danger-light);
}

.av-action-btn--unban {
  color: var(--c-success);
}

.av-action-btn--unban:hover {
  color: #047857;
  background: var(--c-success-light);
}

.av-unban-wrap {
  position: relative;
  display: inline-flex;
  justify-content: center;
}

.av-unban-menu {
  position: absolute;
  right: 50%;
  transform: translateX(50%);
  top: calc(100% + 4px);
  z-index: 50;
  min-width: 130px;
  background: var(--c-surface);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-xl);
  padding: 4px;
  transform-origin: top center;
}

.av-unban-menu__item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 8px 12px;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--c-text);
  font-size: var(--text-sm);
  font-family: var(--font-sans);
  white-space: nowrap;
  text-align: left;
  transition: background var(--dur-fast) var(--ease);
}

.av-unban-menu__item:hover:not(:disabled) {
  background: var(--c-accent-light);
  color: var(--c-accent);
}

.av-unban-menu__item:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.av-unban-menu__item i {
  font-size: 13px;
  width: 16px;
  text-align: center;
  flex-shrink: 0;
}

.av-unban-icon--liable {
  color: var(--c-warning);
}

.av-unban-icon--innocent {
  color: var(--c-success);
}

.av-dropdown-enter-active {
  transition:
    opacity var(--dur-normal) var(--ease),
    transform var(--dur-normal) var(--ease);
}

.av-dropdown-leave-active {
  transition:
    opacity 150ms var(--ease),
    transform 150ms var(--ease);
}

.av-dropdown-enter-from {
  opacity: 0;
  transform: translateX(50%) scaleY(0.88) translateY(-4px);
}

.av-dropdown-leave-to {
  opacity: 0;
  transform: translateX(50%) scaleY(0.94) translateY(-2px);
}

.av-pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  margin-top: 16px;
}

.av-page-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 32px;
  height: 32px;
  padding: 0 8px;
  border: 1px solid var(--c-border);
  border-radius: var(--radius-sm);
  background: var(--c-surface);
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--c-text-secondary);
  transition: all var(--dur-fast) var(--ease);
}

.av-page-btn:hover {
  border-color: var(--c-accent);
  color: var(--c-accent);
}

.av-page-btn--active {
  background: var(--c-accent);
  border-color: var(--c-accent);
  color: var(--c-text-inverse);
}

.av-page-btn--active:hover {
  background: var(--c-accent-hover);
  color: var(--c-text-inverse);
}

.av-page-ellipsis {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  color: var(--c-text-muted);
  font-size: var(--text-sm);
}

@media (max-width: 768px) {
  .av-users-search {
    max-width: 100%;
  }

  .av-user-row {
    grid-template-columns: 1fr 60px 44px 48px;
  }

  .av-user-col--name,
  .av-user-col--nickname,
  .av-user-col--role {
    display: none;
  }

  .av-user-row--header .av-user-col--name,
  .av-user-row--header .av-user-col--nickname,
  .av-user-row--header .av-user-col--role {
    display: none;
  }
}
</style>
