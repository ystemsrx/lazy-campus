<script setup lang="ts">
import { Search, X } from 'lucide-vue-next'
import { nextTick, onMounted, onUnmounted, proxyRefs, ref, watch } from 'vue'

import femaleAvatar from '../../assets/avatars/default-female.svg'
import maleAvatar from '../../assets/avatars/default-male.svg'
import type { AdminNewcomerRewardsModel } from '../../composables/admin/useAdminNewcomerRewards'
import AppDropdown from '../AppDropdown.vue'
import { formatFull } from '../../utils/time'

const props = defineProps<{
  model: AdminNewcomerRewardsModel
}>()

const vm = proxyRefs(props.model)
type NewcomerRewardTab = 'config' | 'history'

const tabsRef = ref<HTMLElement | null>(null)
const configTabLabelRef = ref<HTMLElement | null>(null)
const historyTabLabelRef = ref<HTMLElement | null>(null)
const isGrantModalOpen = ref(false)
const tabSliderStyle = ref<Record<string, string>>({
  transform: 'translateX(0px)',
  width: '0px',
  opacity: '0',
})

const rewardTypeMap: Record<string, string> = {
  agent_usage: '代理使用',
}

const logsTypeOptions = [
  { value: '', label: '所有奖励类型' },
  { value: 'agent_usage', label: '代理使用' },
]

const logsStatusOptions = [
  { value: '', label: '所有状态' },
  { value: 'success', label: '发放成功' },
  { value: 'failed', label: '发放失败' },
]

function visualWidthUnits(text: string) {
  let units = 0
  for (const char of text) {
    units += char.charCodeAt(0) > 255 ? 2 : 1
  }
  return units
}

function calcDropdownWidth(options: Array<{ label: string }>, minPx = 116, maxPx = 180) {
  const maxUnits = options.reduce((acc, option) => Math.max(acc, visualWidthUnits(option.label)), 0)
  const estimated = maxUnits * 7.5 + 50
  return `${Math.round(Math.min(maxPx, Math.max(minPx, estimated)))}px`
}

const logsTypeDropdownWidth = calcDropdownWidth(logsTypeOptions)
const logsStatusDropdownWidth = calcDropdownWidth(logsStatusOptions)

function updateTabSlider() {
  const tab = vm.activeSubTab as NewcomerRewardTab
  const activeLabel = tab === 'history' ? historyTabLabelRef.value : configTabLabelRef.value
  if (!tabsRef.value || !activeLabel) {
    tabSliderStyle.value = {
      transform: 'translateX(0px)',
      width: '0px',
      opacity: '0',
    }
    return
  }

  tabSliderStyle.value = {
    transform: `translateX(${activeLabel.offsetLeft}px)`,
    width: `${activeLabel.offsetWidth}px`,
    opacity: '1',
  }
}

onMounted(() => {
  nextTick(updateTabSlider)
  window.addEventListener('resize', updateTabSlider)
})

onUnmounted(() => {
  window.removeEventListener('resize', updateTabSlider)
})

watch(() => vm.activeSubTab, () => {
  nextTick(updateTabSlider)
})

function rewardTypeLabel(type: string) {
  return rewardTypeMap[type] || type
}

function rewardDetailLabel(type: string, detail: string) {
  if (type === 'agent_usage') return `${detail} 次`
  return detail
}

function timeRangeText(start: string | null, end: string | null) {
  const s = start ? start.slice(0, 10) : '立即开始'
  const e = end ? end.slice(0, 10) : '永久有效'
  return `${s} ~ ${e}`
}

function openGrantModal() {
  isGrantModalOpen.value = true
}

function closeGrantModal() {
  isGrantModalOpen.value = false
  vm.manualGrantUserSearchQuery = ''
  vm.manualGrantUserSearchResults = []
}

async function handleGrantSubmit() {
  const ok = await vm.submitManualGrant()
  if (ok) closeGrantModal()
}
</script>

<template>
  <section class="nr-root">
    <!-- Tab 切换 -->
    <div ref="tabsRef" class="nr-tabs">
      <input id="nr-tab-config" v-model="vm.activeSubTab" type="radio" name="nr-tab" value="config" class="nr-tabs__radio" />
      <label for="nr-tab-config" class="nr-tabs__label" ref="configTabLabelRef">
        <i class="fa-solid fa-gear"></i>
        奖励配置
      </label>
      <input id="nr-tab-history" v-model="vm.activeSubTab" type="radio" name="nr-tab" value="history" class="nr-tabs__radio" />
      <label for="nr-tab-history" class="nr-tabs__label" ref="historyTabLabelRef">
        <i class="fa-solid fa-clock-rotate-left"></i>
        发放历史记录
      </label>
      <div class="nr-tabs__slider" :style="tabSliderStyle" />
    </div>

    <!-- 奖励规则配置 -->
    <div v-if="vm.activeSubTab === 'config'" class="nr-panel">
      <div class="nr-panel__head">
        <div>
          <h3 class="nr-panel__title">奖励配置</h3>
          <p class="nr-panel__desc">配置奖励规则，并支持按指定用户手动发放。</p>
        </div>
        <div class="nr-panel__actions">
          <button class="btn btn-primary btn-sm" @click="vm.openAddModal">
            <i class="fa-solid fa-plus"></i>
            配置新人规则
          </button>
          <button class="btn btn-outline btn-sm" @click="openGrantModal">
            <i class="fa-solid fa-gift"></i>
            发放奖励
          </button>
        </div>
      </div>

      <div v-if="vm.rulesLoading" class="nr-empty">加载中…</div>

      <div v-else-if="!vm.rules.length" class="nr-empty-card">
        <i class="fa-solid fa-gift nr-empty-card__icon"></i>
        <h4>暂无奖励规则</h4>
        <p>当前没有配置任何新人奖励，新注册用户将不会获得奖励。</p>
        <button class="nr-empty-card__link" @click="vm.openAddModal">+ 立即添加第一条规则</button>
      </div>

      <div v-else class="nr-rule-list">
        <div
          v-for="rule in vm.rules"
          :key="rule.id"
          class="nr-rule"
          :class="{ 'nr-rule--disabled': !rule.enabled }"
        >
          <div class="nr-rule__left">
            <div class="nr-rule__icon" :class="{ 'nr-rule__icon--off': !rule.enabled }">
              <i class="fa-solid fa-robot"></i>
            </div>
            <div class="nr-rule__info">
              <div class="nr-rule__title-row">
                <strong>{{ rewardDetailLabel(rule.reward_type, rule.reward_detail) }}</strong>
                <span v-if="!rule.enabled" class="badge badge-default nr-rule__badge-off">已停用</span>
              </div>
              <div class="nr-rule__meta">
                <span class="nr-rule__type-tag">{{ rewardTypeLabel(rule.reward_type) }}</span>
                <span class="nr-rule__time">
                  <i class="fa-regular fa-clock"></i>
                  {{ timeRangeText(rule.start_time, rule.end_time) }}
                </span>
              </div>
            </div>
          </div>

          <div class="nr-rule__actions">
            <label class="nr-toggle">
              <input type="checkbox" :checked="rule.enabled" @change="vm.handleToggleRule(rule)" />
              <span class="nr-toggle__track" />
              <span class="nr-toggle__label">{{ rule.enabled ? '已启用' : '已停用' }}</span>
            </label>
            <div class="nr-rule__sep" />
            <button class="nr-icon-btn" title="编辑" @click="vm.openEditModal(rule)">
              <i class="fa-solid fa-pen-to-square"></i>
            </button>
            <button class="nr-icon-btn nr-icon-btn--danger" title="删除" @click="vm.handleDeleteRule(rule)">
              <i class="fa-solid fa-trash-can"></i>
            </button>
          </div>
        </div>

        <div class="nr-tip">
          <i class="fa-solid fa-circle-info"></i>
          <div>
            <p class="nr-tip__title">温馨提示</p>
            <p>处于"已启用"状态且在有效时间内的规则会自动生效。新注册用户或首次通过第三方登录的用户将自动获得对应奖励。</p>
          </div>
        </div>
      </div>
    </div>

    <!-- 发放历史记录 -->
    <div v-if="vm.activeSubTab === 'history'" class="nr-panel">
      <div class="nr-logs-toolbar">
        <div class="nr-logs-toolbar__left">
          <div class="nr-search">
            <i class="fa-solid fa-magnifying-glass"></i>
            <input v-model="vm.logsSearch" class="form-input" placeholder="搜索用户账号/姓名" />
          </div>
          <div class="nr-logs-filters">
            <AppDropdown
              v-model="vm.logsTypeFilter"
              :options="logsTypeOptions"
              :width="logsTypeDropdownWidth"
              :min-width="logsTypeDropdownWidth"
            />
            <AppDropdown
              v-model="vm.logsStatusFilter"
              :options="logsStatusOptions"
              :width="logsStatusDropdownWidth"
              :min-width="logsStatusDropdownWidth"
            />
          </div>
        </div>
      </div>

      <div v-if="vm.logsLoading" class="nr-empty">加载中…</div>
      <div v-else-if="!vm.logs.length" class="nr-empty">暂无发放记录</div>

      <div v-else class="nr-table-wrap">
        <table class="nr-table">
          <thead>
            <tr>
              <th>用户</th>
              <th>奖励类型</th>
              <th>奖励详情</th>
              <th>发放时间</th>
              <th>状态</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="log in vm.logs" :key="log.id">
              <td>
                <div class="nr-log-user">
                  <strong>{{ log.user_display_name }}</strong>
                  <span>{{ log.user_account }}</span>
                </div>
              </td>
              <td>
                <span class="badge badge-blue">{{ rewardTypeLabel(log.reward_type) }}</span>
              </td>
              <td>{{ rewardDetailLabel(log.reward_type, log.reward_detail) }}</td>
              <td>{{ formatFull(log.created_at) }}</td>
              <td>
                <span v-if="log.status === 'success'" class="nr-status nr-status--ok">
                  <i class="fa-solid fa-circle-check"></i> 成功
                </span>
                <span v-else class="nr-status nr-status--fail" :title="log.fail_reason || ''">
                  <i class="fa-solid fa-circle-xmark"></i> 失败
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="vm.logsTotalPages > 1" class="nr-pagination">
        <button class="btn btn-ghost btn-sm" :disabled="vm.logsPage <= 1" @click="vm.logsPage -= 1">上一页</button>
        <span>第 {{ vm.logsPage }} / {{ vm.logsTotalPages }} 页</span>
        <button class="btn btn-ghost btn-sm" :disabled="vm.logsPage >= vm.logsTotalPages" @click="vm.logsPage += 1">下一页</button>
      </div>
    </div>

    <!-- 添加/编辑规则弹窗 -->
    <Teleport to="body">
      <Transition name="nr-modal">
        <div v-if="vm.isModalOpen" class="nr-modal-overlay" @click.self="vm.closeModal">
          <div class="nr-modal">
            <div class="nr-modal__head">
              <h3>{{ vm.editingRule ? '编辑奖励规则' : '添加奖励规则' }}</h3>
              <button class="nr-icon-btn" @click="vm.closeModal">
                <i class="fa-solid fa-xmark"></i>
              </button>
            </div>

            <div class="nr-modal__body">
              <form id="nr-form" @submit.prevent="vm.saveRule">
                <div class="nr-form-section">
                  <h4><span class="nr-form-dot" />奖励内容</h4>

                  <label class="nr-label">奖励类型</label>
                  <div class="nr-type-grid">
                    <label
                      class="nr-type-card"
                      :class="{ 'nr-type-card--selected': vm.formData.reward_type === 'agent_usage' }"
                    >
                      <input v-model="vm.formData.reward_type" type="radio" name="reward_type" value="agent_usage" class="sr-only" />
                      <i class="fa-solid fa-robot"></i>
                      <span>代理使用</span>
                    </label>
                  </div>

                  <label class="nr-label">奖励详情</label>
                  <div v-if="vm.formData.reward_type === 'agent_usage'" class="nr-input-group">
                    <input
                      v-model="vm.formData.reward_detail"
                      type="number"
                      min="1"
                      class="form-input"
                      placeholder="输入赠送次数"
                    />
                    <span class="nr-input-group__suffix">次</span>
                  </div>
                </div>

                <hr class="nr-divider" />

                <div class="nr-form-section">
                  <h4><span class="nr-form-dot" />发放条件（时间段）</h4>
                  <div class="nr-form-hint">
                    设定该奖励规则的有效时间。在此时间内注册的新用户将自动获得该奖励。不填则立即开始且永久有效。
                  </div>
                  <div class="nr-time-row">
                    <div class="nr-time-field">
                      <label class="nr-label">生效时间 <span class="nr-label--optional">(可选)</span></label>
                      <div class="nr-date-input">
                        <i class="fa-regular fa-clock"></i>
                        <input v-model="vm.formData.start_time" type="date" class="form-input" />
                      </div>
                    </div>
                    <div class="nr-time-field">
                      <label class="nr-label">失效时间 <span class="nr-label--optional">(可选)</span></label>
                      <div class="nr-date-input">
                        <i class="fa-regular fa-clock"></i>
                        <input v-model="vm.formData.end_time" type="date" class="form-input" />
                      </div>
                    </div>
                  </div>
                </div>
              </form>
            </div>

            <div class="nr-modal__foot">
              <button type="button" class="btn btn-outline btn-sm" @click="vm.closeModal">取消</button>
              <button type="submit" form="nr-form" class="btn btn-primary btn-sm" :disabled="vm.formSaving">
                {{ vm.formSaving ? '保存中…' : '确定保存' }}
              </button>
            </div>
          </div>
        </div>
      </Transition>

      <Transition name="nr-modal">
        <div v-if="isGrantModalOpen" class="nr-modal-overlay" @click.self="closeGrantModal">
          <div class="nr-modal nr-modal--grant">
            <div class="nr-modal__head">
              <h3>发放奖励</h3>
              <button class="nr-icon-btn" @click="closeGrantModal">
                <i class="fa-solid fa-xmark"></i>
              </button>
            </div>

            <div class="nr-modal__body">
              <form id="nr-grant-form" @submit.prevent="handleGrantSubmit">
                <div class="nr-form-section">
                  <h4><span class="nr-form-dot" />发放设置</h4>

                  <label class="nr-label">奖励类型</label>
                  <div class="nr-type-grid">
                    <label
                      class="nr-type-card"
                      :class="{ 'nr-type-card--selected': vm.manualGrantForm.reward_type === 'agent_usage' }"
                    >
                      <input v-model="vm.manualGrantForm.reward_type" type="radio" name="grant_reward_type" value="agent_usage" class="sr-only" />
                      <i class="fa-solid fa-robot"></i>
                      <span>代理使用</span>
                    </label>
                  </div>

                  <label class="nr-label">奖励详情</label>
                  <div v-if="vm.manualGrantForm.reward_type === 'agent_usage'" class="nr-input-group">
                    <input
                      v-model="vm.manualGrantForm.reward_detail"
                      type="number"
                      min="1"
                      class="form-input"
                      placeholder="输入赠送次数"
                    />
                    <span class="nr-input-group__suffix">次</span>
                  </div>
                </div>

                <hr class="nr-divider" />

                <div class="nr-form-section">
                  <h4><span class="nr-form-dot" />指定用户</h4>
                  <div class="nr-grant-search">
                    <Search :size="16" class="nr-grant-search__icon" />
                    <input
                      v-model="vm.manualGrantUserSearchQuery"
                      class="nr-grant-search__input"
                      placeholder="搜索用户昵称、姓名或账号..."
                    />
                    <div v-if="vm.manualGrantSearching" class="nr-grant-search__spinner" />

                    <Transition name="nr-search-anim">
                      <div v-if="vm.manualGrantUserSearchResults.length > 0" class="nr-grant-search__results">
                        <div
                          v-for="user in vm.manualGrantUserSearchResults"
                          :key="user.id"
                          class="nr-grant-search__item"
                          @click="vm.addManualGrantUser(user)"
                        >
                          <div class="nr-grant-search__avatar">
                            <img :src="user.avatar_url ?? (user.gender === 'female' ? femaleAvatar : maleAvatar)" alt="" />
                          </div>
                          <div class="nr-grant-search__meta">
                            <span class="nr-grant-search__name">{{ user.display_name }}</span>
                            <span class="nr-grant-search__account">@{{ user.account }}</span>
                          </div>
                        </div>
                      </div>
                    </Transition>
                  </div>

                  <div v-if="vm.manualGrantSelectedUsers.length > 0" class="nr-grant-tags">
                    <span v-for="user in vm.manualGrantSelectedUsers" :key="user.id" class="nr-grant-tag">
                      {{ vm.formatManualGrantUserLabel(user) }}
                      <button type="button" class="nr-grant-tag__close" @click="vm.removeManualGrantUser(user.id)">
                        <X :size="12" />
                      </button>
                    </span>
                  </div>
                </div>
              </form>
            </div>

            <div class="nr-modal__foot">
              <button type="button" class="btn btn-outline btn-sm" @click="closeGrantModal">取消</button>
              <button
                type="submit"
                form="nr-grant-form"
                class="btn btn-primary btn-sm"
                :disabled="vm.manualGrantSubmitting"
              >
                {{ vm.manualGrantSubmitting ? '发放中…' : '发放奖励' }}
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </section>
</template>

<style scoped>
.nr-root {
  display: flex;
  flex-direction: column;
  gap: 0;
}

/* ──── Tab bar ──── */
.nr-tabs {
  display: flex;
  gap: 0;
  background: #fff;
  border: 1px solid rgba(226, 232, 240, 0.8);
  border-bottom: none;
  border-radius: 16px 16px 0 0;
  padding: 16px 24px 0;
  position: relative;
}

.nr-tabs__radio {
  display: none;
}

.nr-tabs__label {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 0 8px 14px;
  margin-right: 24px;
  font-size: 13.5px;
  font-weight: 500;
  color: #64748b;
  cursor: pointer;
  transition: color 220ms ease;
  position: relative;
}

.nr-tabs__label i {
  font-size: 13px;
}

.nr-tabs__radio:checked + .nr-tabs__label {
  color: var(--c-accent, #3b82f6);
  font-weight: 600;
}

.nr-tabs__label:hover {
  color: #334155;
}

.nr-tabs__radio:checked + .nr-tabs__label:hover {
  color: var(--c-accent, #3b82f6);
}

.nr-tabs__slider {
  position: absolute;
  left: 0;
  bottom: 0;
  height: 2px;
  border-radius: 999px;
  background: var(--c-accent, #3b82f6);
  transition:
    transform 280ms cubic-bezier(0.22, 1, 0.36, 1),
    width 280ms cubic-bezier(0.22, 1, 0.36, 1),
    opacity 180ms ease;
  pointer-events: none;
}

/* ──── Panel ──── */
.nr-panel {
  background: #fff;
  border: 1px solid rgba(226, 232, 240, 0.8);
  border-top: 1px solid rgba(226, 232, 240, 0.5);
  border-radius: 0 0 16px 16px;
  padding: 20px;
  min-height: 420px;
}

.nr-panel__head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.nr-panel__title {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  color: var(--c-text, #0f172a);
}

.nr-panel__desc {
  margin: 4px 0 0;
  font-size: 12.5px;
  color: #94a3b8;
}

.nr-panel__actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.nr-grant-search {
  margin-top: 10px;
  position: relative;
  display: flex;
  align-items: center;
}

.nr-grant-search__icon {
  position: absolute;
  left: 12px;
  color: #94a3b8;
  pointer-events: none;
}

.nr-grant-search__input {
  width: 100%;
  padding: 9px 12px 9px 36px;
  border: 1px solid #dbe4ef;
  border-radius: 10px;
  font-size: 13px;
  background: #fff;
  transition: border-color 200ms ease, box-shadow 200ms ease;
}

.nr-grant-search__input:focus {
  outline: none;
  border-color: var(--c-accent, #3b82f6);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.12);
}

.nr-grant-search__input:disabled {
  background: #f1f5f9;
  color: #94a3b8;
}

.nr-grant-search__spinner {
  position: absolute;
  right: 12px;
  width: 15px;
  height: 15px;
  border: 2px solid #cbd5e1;
  border-top-color: var(--c-accent, #3b82f6);
  border-radius: 50%;
  animation: nr-spin 0.7s linear infinite;
}

.nr-grant-search__results {
  position: absolute;
  bottom: calc(100% + 4px);
  left: 0;
  right: 0;
  z-index: 30;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  box-shadow: 0 12px 30px rgba(15, 23, 42, 0.14);
  max-height: 240px;
  overflow-y: auto;
  padding: 4px;
  transform-origin: bottom center;
}

.nr-grant-search__item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 150ms ease;
}

.nr-grant-search__item:hover {
  background: rgba(59, 130, 246, 0.08);
}

.nr-grant-search__avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  overflow: hidden;
  flex-shrink: 0;
  background: #e2e8f0;
}

.nr-grant-search__avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.nr-grant-search__meta {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.nr-grant-search__name {
  font-size: 13px;
  color: #0f172a;
  font-weight: 500;
}

.nr-grant-search__account {
  font-size: 11.5px;
  color: #94a3b8;
}

.nr-grant-tags {
  margin-top: 10px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.nr-grant-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px 4px 10px;
  border-radius: 999px;
  border: 1px solid rgba(59, 130, 246, 0.25);
  color: var(--c-accent, #3b82f6);
  background: rgba(59, 130, 246, 0.08);
  font-size: 12px;
  font-weight: 500;
}

.nr-grant-tag__close {
  width: 17px;
  height: 17px;
  border: none;
  background: transparent;
  color: var(--c-accent, #3b82f6);
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.nr-grant-tag__close:hover {
  background: rgba(59, 130, 246, 0.2);
}

.nr-search-anim-enter-active,
.nr-search-anim-leave-active {
  transition: opacity 180ms ease, transform 180ms ease;
}

.nr-search-anim-enter-from,
.nr-search-anim-leave-to {
  opacity: 0;
  transform: translateY(4px) scale(0.98);
}

/* ──── Empty state ──── */
.nr-empty {
  text-align: center;
  color: #94a3b8;
  font-size: 13px;
  padding: 40px 0;
}

.nr-empty-card {
  text-align: center;
  padding: 48px 24px;
  background: #f8fafc;
  border: 1px dashed #cbd5e1;
  border-radius: 12px;
}

.nr-empty-card__icon {
  font-size: 40px;
  color: #cbd5e1;
  margin-bottom: 12px;
}

.nr-empty-card h4 {
  margin: 0 0 4px;
  font-size: 16px;
  color: var(--c-text, #0f172a);
}

.nr-empty-card p {
  margin: 0 0 16px;
  font-size: 13px;
  color: #94a3b8;
}

.nr-empty-card__link {
  background: none;
  border: none;
  color: var(--c-accent, #3b82f6);
  font-weight: 600;
  font-size: 13px;
  cursor: pointer;
}

.nr-empty-card__link:hover {
  text-decoration: underline;
}

/* ──── Rule list ──── */
.nr-rule-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.nr-rule {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 18px;
  border: 1px solid rgba(226, 232, 240, 0.8);
  border-radius: 14px;
  background: #fff;
  transition: box-shadow 200ms, opacity 200ms;
  flex-wrap: wrap;
  gap: 12px;
}

.nr-rule:hover {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.04);
}

.nr-rule--disabled {
  background: #f8fafc;
  opacity: 0.75;
}

.nr-rule__left {
  display: flex;
  align-items: center;
  gap: 14px;
  min-width: 0;
  flex: 1;
}

.nr-rule__icon {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  font-size: 18px;
  flex-shrink: 0;
  background: rgba(59, 130, 246, 0.08);
  color: var(--c-accent, #3b82f6);
}

.nr-rule__icon--off {
  background: #f1f5f9;
  color: #94a3b8;
}

.nr-rule__info {
  min-width: 0;
}

.nr-rule__title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.nr-rule__title-row strong {
  font-size: 15px;
  color: var(--c-text, #0f172a);
}

.nr-rule--disabled .nr-rule__title-row strong {
  color: #64748b;
}

.nr-rule__badge-off {
  font-size: 10px !important;
  padding: 1px 6px !important;
}

.nr-rule__meta {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 6px;
  flex-wrap: wrap;
}

.nr-rule__type-tag {
  display: inline-block;
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
  padding: 1px 8px;
  font-size: 11.5px;
  color: #475569;
}

.nr-rule__time {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12.5px;
  color: #94a3b8;
}

.nr-rule__time i {
  font-size: 12px;
  color: #cbd5e1;
}

.nr-rule__actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.nr-rule__sep {
  width: 1px;
  height: 22px;
  background: #e2e8f0;
}

/* ──── Toggle switch ──── */
.nr-toggle {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.nr-toggle input {
  display: none;
}

.nr-toggle__track {
  position: relative;
  width: 38px;
  height: 22px;
  border-radius: 99px;
  background: #cbd5e1;
  transition: background 200ms;
  flex-shrink: 0;
}

.nr-toggle__track::after {
  content: '';
  position: absolute;
  left: 3px;
  top: 3px;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #fff;
  transition: transform 200ms;
}

.nr-toggle input:checked + .nr-toggle__track {
  background: var(--c-accent, #3b82f6);
}

.nr-toggle input:checked + .nr-toggle__track::after {
  transform: translateX(16px);
}

.nr-toggle__label {
  font-size: 12.5px;
  font-weight: 500;
  color: #64748b;
}

/* ──── Icon buttons ──── */
.nr-icon-btn {
  border: none;
  background: transparent;
  color: #94a3b8;
  font-size: 14px;
  padding: 4px;
  border-radius: 6px;
  cursor: pointer;
  transition: color 200ms, background 200ms;
}

.nr-icon-btn:hover {
  color: var(--c-accent, #3b82f6);
  background: rgba(59, 130, 246, 0.06);
}

.nr-icon-btn--danger:hover {
  color: #ef4444;
  background: rgba(239, 68, 68, 0.06);
}

/* ──── Tip box ──── */
.nr-tip {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin-top: 16px;
  padding: 14px 16px;
  background: rgba(59, 130, 246, 0.04);
  border: 1px solid rgba(59, 130, 246, 0.12);
  border-radius: 10px;
}

.nr-tip > i {
  color: var(--c-accent, #3b82f6);
  font-size: 16px;
  margin-top: 2px;
  flex-shrink: 0;
}

.nr-tip__title {
  margin: 0 0 2px;
  font-weight: 600;
  font-size: 13px;
  color: #1e3a5f;
}

.nr-tip p {
  margin: 0;
  font-size: 12.5px;
  color: #1e3a5f;
  opacity: 0.85;
  line-height: 1.5;
}

/* ──── Logs toolbar ──── */
.nr-logs-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 14px;
  background: #f8fafc;
  border: 1px solid rgba(226, 232, 240, 0.6);
  border-radius: 10px;
  padding: 12px 14px;
}

.nr-logs-toolbar__left {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: nowrap;
  flex: 1;
}

.nr-search {
  position: relative;
  min-width: 240px;
  flex: 1;
  max-width: none;
}

.nr-search i {
  position: absolute;
  left: 10px;
  top: 50%;
  transform: translateY(-50%);
  color: #94a3b8;
  font-size: 12px;
}

.nr-search :deep(.form-input) {
  padding-left: 32px;
}

.nr-logs-filters {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.nr-logs-filters :deep(.app-dropdown) {
  flex-shrink: 0;
}

.nr-logs-filters :deep(.app-dropdown__trigger) {
  height: 36px;
  padding-top: 8px;
  padding-bottom: 8px;
  font-size: 13px;
}

/* ──── Table ──── */
.nr-table-wrap {
  overflow: auto;
  border: 1px solid rgba(226, 232, 240, 0.8);
  border-radius: 10px;
}

.nr-table {
  width: 100%;
  border-collapse: collapse;
  min-width: 680px;
}

.nr-table th,
.nr-table td {
  padding: 11px 14px;
  text-align: left;
  font-size: 13px;
  border-bottom: 1px solid rgba(226, 232, 240, 0.7);
}

.nr-table th {
  background: #f8fafc;
  font-weight: 600;
  font-size: 11.5px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: #64748b;
}

.nr-table tbody tr {
  transition: background 150ms;
}

.nr-table tbody tr:hover {
  background: #f8fafc;
}

.nr-log-user strong {
  display: block;
  font-size: 13px;
}

.nr-log-user span {
  color: #94a3b8;
  font-size: 11.5px;
}

.nr-status {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 13px;
}

.nr-status--ok {
  color: #16a34a;
}

.nr-status--fail {
  color: #ef4444;
}

/* ──── Pagination ──── */
.nr-pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
  font-size: 13px;
}

/* ──── Modal ──── */
.nr-modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  background: rgba(15, 23, 42, 0.3);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
}

.nr-modal {
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.12);
  width: 100%;
  max-width: 580px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.nr-modal--grant {
  overflow: visible;
}

.nr-modal__head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 18px 22px;
  border-bottom: 1px solid rgba(226, 232, 240, 0.6);
}

.nr-modal__head h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
}

.nr-modal__body {
  padding: 22px;
  overflow-y: auto;
  flex: 1;
}

.nr-modal--grant .nr-modal__body {
  overflow: visible;
}

.nr-modal__foot {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 14px 22px;
  border-top: 1px solid rgba(226, 232, 240, 0.6);
  background: #f8fafc;
  border-radius: 0 0 16px 16px;
}

/* ──── Form ──── */
.nr-form-section h4 {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 14px;
  font-size: 14.5px;
  font-weight: 600;
  color: var(--c-text, #0f172a);
}

.nr-form-dot {
  display: inline-block;
  width: 5px;
  height: 16px;
  border-radius: 99px;
  background: var(--c-accent, #3b82f6);
}

.nr-label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: #475569;
  margin-bottom: 8px;
}

.nr-label--optional {
  font-weight: 400;
  color: #94a3b8;
}

.nr-type-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 10px;
  margin-bottom: 16px;
}

.nr-type-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 14px 10px;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  cursor: pointer;
  transition: all 200ms;
  font-size: 13px;
  font-weight: 500;
  color: #475569;
}

.nr-type-card i {
  font-size: 18px;
  color: #94a3b8;
  transition: color 200ms;
}

.nr-type-card:hover {
  background: #f8fafc;
}

.nr-type-card--selected {
  border-color: var(--c-accent, #3b82f6);
  background: rgba(59, 130, 246, 0.04);
  color: var(--c-accent, #3b82f6);
  box-shadow: 0 0 0 1px var(--c-accent, #3b82f6);
}

.nr-type-card--selected i {
  color: var(--c-accent, #3b82f6);
}

.nr-input-group {
  display: flex;
  margin-bottom: 4px;
}

.nr-input-group .form-input {
  flex: 1;
  border-top-right-radius: 0;
  border-bottom-right-radius: 0;
}

.nr-input-group__suffix {
  display: flex;
  align-items: center;
  padding: 0 14px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-left: none;
  border-radius: 0 var(--radius-md, 8px) var(--radius-md, 8px) 0;
  font-size: 13px;
  color: #64748b;
}

.nr-divider {
  border: none;
  border-top: 1px solid rgba(226, 232, 240, 0.6);
  margin: 20px 0;
}

.nr-form-hint {
  font-size: 12px;
  color: #94a3b8;
  margin-bottom: 14px;
  line-height: 1.5;
}

.nr-time-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}

.nr-time-field {
  display: flex;
  flex-direction: column;
}

.nr-date-input {
  position: relative;
}

.nr-date-input i {
  position: absolute;
  left: 10px;
  top: 50%;
  transform: translateY(-50%);
  color: #94a3b8;
  font-size: 13px;
  pointer-events: none;
}

.nr-date-input .form-input {
  padding-left: 32px;
}

/* ──── Modal transitions ──── */
.nr-modal-enter-active {
  transition: opacity 200ms ease;
}

.nr-modal-enter-active .nr-modal {
  transition: transform 200ms cubic-bezier(0.34, 1.56, 0.64, 1), opacity 200ms ease;
}

.nr-modal-leave-active {
  transition: opacity 150ms ease;
}

.nr-modal-leave-active .nr-modal {
  transition: transform 150ms ease, opacity 150ms ease;
}

.nr-modal-enter-from {
  opacity: 0;
}

.nr-modal-enter-from .nr-modal {
  opacity: 0;
  transform: scale(0.95) translateY(10px);
}

.nr-modal-leave-to {
  opacity: 0;
}

.nr-modal-leave-to .nr-modal {
  opacity: 0;
  transform: scale(0.97);
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  border: 0;
}

@keyframes nr-spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 640px) {
  .nr-time-row {
    grid-template-columns: 1fr;
  }

  .nr-rule {
    flex-direction: column;
    align-items: flex-start;
  }

  .nr-rule__actions {
    width: 100%;
    justify-content: flex-end;
    border-top: 1px solid #f1f5f9;
    padding-top: 10px;
  }

  .nr-tabs {
    padding: 12px 16px 0;
  }

  .nr-panel {
    padding: 14px;
  }

  .nr-panel__actions {
    width: 100%;
  }

  .nr-logs-toolbar__left {
    flex-wrap: wrap;
  }

  .nr-search {
    min-width: 100%;
  }

  .nr-logs-filters {
    width: 100%;
    gap: 8px;
  }

  .nr-logs-filters :deep(.app-dropdown) {
    flex: 1;
  }
}
</style>
