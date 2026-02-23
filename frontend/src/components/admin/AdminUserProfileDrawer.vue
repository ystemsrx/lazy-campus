<script setup lang="ts">
import { computed, onMounted, onUnmounted, proxyRefs, ref, watch } from 'vue'
import maleAvatar from '../../assets/avatars/default-male.svg'
import femaleAvatar from '../../assets/avatars/default-female.svg'

import type { AdminUsersModel } from '../../composables/admin/useAdminUsers'
import type { TaskSnapshot } from '../../composables/admin/useAdminReports'
import { fetchTaskSnapshot } from '../../api/moderation'
import AdminRadarChart from './AdminRadarChart.vue'
import AdminTaskSnapshotDrawer from './AdminTaskSnapshotDrawer.vue'
import AppDateTimePicker from '../AppDateTimePicker.vue'
import AppDropdown from '../AppDropdown.vue'
import AppSaveStatusBar from '../AppSaveStatusBar.vue'
import { formatShort } from '../../utils/time'

const TASK_STATUS_MAP: Record<string, string> = {
  open: '待接取',
  in_progress: '进行中',
  completed: '已完成',
  canceled: '已取消',
  under_review: '审核中',
}

const taskStatusBadge: Record<string, { label: string; cls: string }> = {
  open: { label: '待接取', cls: 'badge-blue' },
  in_progress: { label: '进行中', cls: 'badge-amber' },
  completed: { label: '已完成', cls: 'badge-green' },
  canceled: { label: '已取消', cls: 'badge-default' },
  under_review: { label: '审核中', cls: 'badge-amber' },
}

function taskStatus(status: string, isDeleted?: boolean) {
  if (isDeleted) return { label: '已删除', cls: 'badge-red' }
  return taskStatusBadge[status] || { label: status, cls: 'badge-default' }
}

const props = defineProps<{
  model: AdminUsersModel
}>()

const vm = proxyRefs(props.model)

const genderOptions = [
  { value: '', label: '未设置' },
  { value: 'male', label: '男' },
  { value: 'female', label: '女' },
]

const roleOptions = [
  { value: 'user', label: '普通用户' },
  { value: 'admin', label: '管理员' },
]

const avatarSrc = computed(() => {
  if (!vm.selectedProfile) return maleAvatar
  if (vm.selectedProfile.avatar_url) return vm.selectedProfile.avatar_url
  return vm.selectedProfile.gender === 'female' ? femaleAvatar : maleAvatar
})

// 移动端底部拖拽（与任务详情逻辑完全一致）
const drawerRef = ref<HTMLElement | null>(null)
let sheetDragStartY = 0
let sheetDragStartH = 0
let sheetCanExpand = false
let savedScrollY = 0

function resetSheetStyles() {
  const el = drawerRef.value
  if (!el) return
  el.style.maxHeight = ''
  el.style.transform = ''
  el.style.transition = ''
}

function onHandleTouchStart(e: TouchEvent) {
  const el = drawerRef.value
  if (!el) return
  sheetDragStartY = e.touches[0].clientY
  sheetDragStartH = el.getBoundingClientRect().height
  const body = el.querySelector('.aupd-body') as HTMLElement | null
  sheetCanExpand = body ? body.scrollHeight > body.clientHeight + 2 : false
  el.style.transition = 'none'
  document.addEventListener('touchmove', onHandleTouchMove, { passive: false })
  document.addEventListener('touchend', onHandleTouchEnd)
}

function onHandleTouchMove(e: TouchEvent) {
  const el = drawerRef.value
  if (!el) return
  e.preventDefault()
  const deltaY = e.touches[0].clientY - sheetDragStartY
  const vh = window.innerHeight
  if (deltaY < 0) {
    const absDelta = Math.abs(deltaY)
    if (sheetCanExpand) {
      const expansion = Math.round(Math.pow(absDelta, 0.75))
      const cap = vh * 0.06
      el.style.maxHeight = `${sheetDragStartH + Math.min(expansion, cap)}px`
      el.style.transform = ''
    } else {
      el.style.transform = `translateY(${-Math.round(Math.pow(absDelta, 0.6))}px)`
    }
  } else {
    el.style.maxHeight = ''
    el.style.transform = `translateY(${deltaY}px)`
  }
}

function onHandleTouchEnd() {
  document.removeEventListener('touchmove', onHandleTouchMove)
  document.removeEventListener('touchend', onHandleTouchEnd)
  const el = drawerRef.value
  if (!el) return
  const match = el.style.transform.match(/translateY\(([^)]+)px\)/)
  const currentTranslateY = match ? parseFloat(match[1]) : 0
  const vh = window.innerHeight
  if (currentTranslateY > 120) {
    el.style.transition = 'transform 0.35s cubic-bezier(0.32, 0.72, 0, 1)'
    el.style.transform = `translateY(${vh}px)`
    setTimeout(() => vm.closeUserProfile(), 350)
    return
  }
  el.style.transition =
    'max-height 0.35s cubic-bezier(0.32, 0.72, 0, 1), transform 0.35s cubic-bezier(0.32, 0.72, 0, 1)'
  el.style.maxHeight = `${sheetDragStartH}px`
  el.style.transform = 'translateY(0px)'
  setTimeout(() => {
    el.style.transition = ''
    el.style.transform = ''
    el.style.maxHeight = ''
  }, 350)
}

watch(
  () => vm.profileOpen,
  (open) => {
    if (open) {
      savedScrollY = window.scrollY
      document.body.style.position = 'fixed'
      document.body.style.top = `-${savedScrollY}px`
      document.body.style.width = '100%'
      // 等 DOM 渲染后重置拖拽状态
      setTimeout(resetSheetStyles, 0)
    } else {
      document.body.style.position = ''
      document.body.style.top = ''
      document.body.style.width = ''
      window.scrollTo(0, savedScrollY)
    }
  },
  { immediate: true },
)

// 黑名单搜索框外部点击关闭
const blSearchRef = ref<HTMLElement | null>(null)
function onDocClick(e: MouseEvent) {
  if (blSearchRef.value && !blSearchRef.value.contains(e.target as Node)) {
    vm.closeBlacklistSearch()
  }
}
onMounted(() => document.addEventListener('mousedown', onDocClick))
onUnmounted(() => {
  document.removeEventListener('mousedown', onDocClick)
  document.removeEventListener('touchmove', onHandleTouchMove)
  document.removeEventListener('touchend', onHandleTouchEnd)
  document.body.style.position = ''
  document.body.style.top = ''
  document.body.style.width = ''
})

// 任务快照（复用举报审核中的 AdminTaskSnapshotDrawer）
const snapshotShow = ref(false)
const snapshotLoading = ref(false)
const snapshotData = ref<TaskSnapshot | null>(null)

async function openTaskSnapshot(taskId: number) {
  snapshotShow.value = true
  snapshotLoading.value = true
  snapshotData.value = null
  try {
    snapshotData.value = await fetchTaskSnapshot(taskId)
  } catch {
    snapshotShow.value = false
  } finally {
    snapshotLoading.value = false
  }
}
</script>

<template>
  <Teleport to="body">
    <Transition name="aupd">
      <div v-if="vm.profileOpen" class="aupd-overlay" @mousedown.self="vm.closeUserProfile">
        <div ref="drawerRef" class="aupd-drawer">
          <div class="aupd-sheet-handle" @touchstart.passive="onHandleTouchStart">
            <div class="aupd-sheet-handle__bar"></div>
          </div>
          <header class="aupd-header">
            <h3>用户 360 画像</h3>
            <div class="aupd-header__right">
              <AppSaveStatusBar :status="vm.profileSaveStatus" saved-text="已自动保存" />
              <button class="btn btn-ghost btn-sm" @click="vm.closeUserProfile">
                <i class="fa-solid fa-xmark"></i>
              </button>
            </div>
          </header>

          <div class="aupd-body">
          <div v-if="vm.profileLoading" class="aupd-loading">
            <div class="spinner"></div>
          </div>

          <template v-else-if="vm.selectedProfile">
            <section class="aupd-top">
              <img :src="avatarSrc" class="aupd-avatar" alt="avatar" />
              <div class="aupd-top__meta">
                <h4>{{ vm.selectedProfile.display_name }}</h4>
                <p>#{{ vm.selectedProfile.id }} · {{ vm.selectedProfile.account }}</p>
                <div class="aupd-top__badges">
                  <span class="badge" :class="vm.selectedProfile.is_active ? 'badge-green' : 'badge-red'">
                    {{ vm.selectedProfile.is_active ? '活跃' : '停用' }}
                  </span>
                  <span class="badge" :class="vm.selectedProfile.is_banned ? 'badge-red' : 'badge-default'">
                    {{ vm.selectedProfile.is_banned ? '登录受限' : '登录正常' }}
                  </span>
                  <span class="badge badge-amber">封禁次数 {{ vm.selectedProfile.ban_count }}</span>
                </div>
              </div>
            </section>

            <div class="aupd-two-col">
              <section class="aupd-panel card">
                <h5 class="aupd-panel__title"><i class="fa-solid fa-chart-radar"></i> 能力雷达</h5>
                <AdminRadarChart :metrics="vm.selectedProfile.radar" :size="220" />
              </section>

              <section class="aupd-panel card">
                <h5 class="aupd-panel__title"><i class="fa-solid fa-chart-simple"></i> 关键指标</h5>
                <div class="aupd-kpi">
                  <div class="aupd-kpi__item">
                    <span>发布任务</span>
                    <strong>{{ vm.selectedProfile.published_task_count }}</strong>
                  </div>
                  <div class="aupd-kpi__item">
                    <span>接取任务</span>
                    <strong>{{ vm.selectedProfile.accepted_task_count }}</strong>
                  </div>
                  <div class="aupd-kpi__item">
                    <span>被举报</span>
                    <strong>{{ vm.selectedProfile.report_received_count }}</strong>
                  </div>
                  <div class="aupd-kpi__item">
                    <span>聊天消息</span>
                    <strong>{{ vm.selectedProfile.chat_message_count }}</strong>
                  </div>
                  <div class="aupd-kpi__item">
                    <span>发布者评分</span>
                    <strong>{{ vm.selectedProfile.publisher_rating_avg.toFixed(1) }}</strong>
                  </div>
                  <div class="aupd-kpi__item">
                    <span>接单者评分</span>
                    <strong>{{ vm.selectedProfile.worker_rating_avg.toFixed(1) }}</strong>
                  </div>
                </div>
              </section>
            </div>

            <section class="aupd-panel card">
              <h5 class="aupd-panel__title"><i class="fa-solid fa-user-pen"></i> 基本资料</h5>
              <div class="aupd-row">
                <label class="form-group">
                  <span class="form-label">姓名</span>
                  <input v-model="vm.profileForm.name" class="form-input" />
                </label>
                <label class="form-group">
                  <span class="form-label">昵称</span>
                  <input v-model="vm.profileForm.nickname" class="form-input" />
                </label>
              </div>
              <div class="aupd-row">
                <label class="form-group">
                  <span class="form-label">邮箱</span>
                  <input v-model="vm.profileForm.email" class="form-input" />
                </label>
                <label class="form-group">
                  <span class="form-label">性别</span>
                  <AppDropdown
                    v-model="vm.profileForm.gender"
                    :options="genderOptions"
                    width="100%"
                    min-width="100%"
                  />
                </label>
              </div>
              <label class="form-group">
                <span class="form-label">角色</span>
                <AppDropdown
                  v-model="vm.profileForm.role"
                  :options="roleOptions"
                  width="100%"
                  min-width="100%"
                />
              </label>
            </section>

            <section class="aupd-panel card">
              <h5 class="aupd-panel__title"><i class="fa-solid fa-shield-halved"></i> 封禁管控</h5>
              <div class="aupd-check-grid">
                <label><input v-model="vm.profileForm.is_active" type="checkbox" /> 启用账号</label>
                <label><input v-model="vm.profileForm.is_banned" type="checkbox" /> 限制登录</label>
                <label><input v-model="vm.profileForm.ban_publish" type="checkbox" /> 禁止发布</label>
                <label><input v-model="vm.profileForm.ban_accept" type="checkbox" /> 禁止接单</label>
                <label><input v-model="vm.profileForm.ban_contact" type="checkbox" /> 禁止联系</label>
              </div>
              <div class="form-row aupd-ban-details">
                <label class="form-group">
                  <span class="form-label">封禁截止时间</span>
                  <AppDateTimePicker
                    v-model="vm.profileForm.ban_until_local"
                    placeholder="设置解封时间"
                  />
                </label>
                <label class="form-group">
                  <span class="form-label">封禁次数</span>
                  <input v-model.number="vm.profileForm.ban_count" class="form-input" type="number" min="0" />
                </label>
              </div>
              <label class="form-group">
                <span class="form-label">封禁理由</span>
                <textarea v-model="vm.profileForm.ban_reason" class="form-textarea" rows="2" />
              </label>
            </section>

            <section class="aupd-panel card">
              <h5 class="aupd-panel__title"><i class="fa-solid fa-briefcase"></i> 接单档案</h5>
              <div class="aupd-check-grid aupd-check-grid--compact">
                <label><input v-model="vm.profileForm.worker_enabled" type="checkbox" /> 启用接单</label>
                <label><input v-model="vm.profileForm.worker_show_contact" type="checkbox" /> 公开联系方式</label>
              </div>
              <label class="form-group">
                <span class="form-label">技能 ID（逗号分隔）</span>
                <input v-model="vm.profileForm.worker_skill_tag_ids_text" class="form-input" placeholder="例如 1,2,3" />
              </label>
              <div class="aupd-row">
                <label class="form-group">
                  <span class="form-label">电话</span>
                  <input v-model="vm.profileForm.worker_phone" class="form-input" />
                </label>
                <label class="form-group">
                  <span class="form-label">微信</span>
                  <input v-model="vm.profileForm.worker_wechat" class="form-input" />
                </label>
              </div>
              <div class="aupd-row">
                <label class="form-group">
                  <span class="form-label">最低报价</span>
                  <input v-model="vm.profileForm.worker_min_price" class="form-input" />
                </label>
                <label class="form-group">
                  <span class="form-label">最高报价</span>
                  <input v-model="vm.profileForm.worker_max_price" class="form-input" />
                </label>
              </div>
              <label class="form-group">
                <span class="form-label">个人简介</span>
                <textarea v-model="vm.profileForm.worker_bio" class="form-textarea" rows="2" />
              </label>
            </section>

            <section class="aupd-panel card">
              <h5 class="aupd-panel__title"><i class="fa-solid fa-user-slash"></i> 黑名单管理</h5>
              <div class="aupd-bl-head">
                <div ref="blSearchRef" class="aupd-bl-search">
                  <i class="fa-solid fa-magnifying-glass aupd-bl-search__icon"></i>
                  <input
                    v-model="vm.blacklistSearchQuery"
                    class="form-input aupd-bl-search__input"
                    placeholder="搜索用户以添加黑名单..."
                  />
                  <div v-if="vm.blacklistSearchLoading" class="aupd-bl-search__spin"><div class="spinner spinner--sm"></div></div>
                  <Transition name="fade">
                    <div v-if="vm.blacklistSearchOpen && vm.blacklistSearchResults.length" class="aupd-bl-dropdown">
                      <button
                        v-for="u in vm.blacklistSearchResults"
                        :key="u.id"
                        class="aupd-bl-dropdown__item"
                        @click="vm.selectBlacklistUser(u)"
                      >
                        <span class="aupd-bl-dropdown__name">
                          {{ u.display_name }}
                          <span v-if="u.name && u.name !== u.display_name" class="aupd-bl-dropdown__realname">（{{ u.name }}）</span>
                        </span>
                        <span class="aupd-bl-dropdown__sub">#{{ u.id }} · {{ u.account }}</span>
                      </button>
                    </div>
                  </Transition>
                </div>
                <div class="aupd-bl-count">
                  <span class="form-label">被拉黑</span>
                  <input v-model.number="vm.profileForm.blocked_by_count" class="form-input aupd-bl-count__input" type="number" min="0" />
                </div>
              </div>

              <div v-if="vm.blacklistLoading" class="aupd-blacklist-loading"><div class="spinner"></div></div>
              <div v-else-if="vm.blacklistItems.length === 0" class="aupd-blacklist-empty">当前黑名单为空</div>
              <div v-else class="aupd-blacklist-list">
                <div v-for="item in vm.blacklistItems" :key="item.blocked_user_id" class="aupd-blacklist-item">
                  <div class="aupd-blacklist-item__info">
                    <span class="aupd-blacklist-item__name">
                      {{ item.blocked_display_name }}
                      <span v-if="item.blocked_name" class="aupd-blacklist-item__realname">（{{ item.blocked_name }}）</span>
                    </span>
                    <span class="aupd-blacklist-item__sub">#{{ item.blocked_user_id }} · {{ item.blocked_account }}</span>
                  </div>
                  <button class="btn btn-outline btn-sm" :disabled="vm.blacklistSubmitting" @click="vm.removeBlacklistItem(item.blocked_user_id)">
                    移除
                  </button>
                </div>
              </div>
            </section>

            <section class="aupd-panel card">
              <h5 class="aupd-panel__title"><i class="fa-solid fa-list-check"></i> 关联任务</h5>
              <div class="aupd-task-tabs">
                <span class="aupd-task-tab__slider" :class="{ 'aupd-task-tab__slider--right': vm.profileTaskTab === 'accepted' }"></span>
                <button
                  class="aupd-task-tab"
                  :class="{ 'aupd-task-tab--active': vm.profileTaskTab === 'published' }"
                  @click="vm.profileTaskTab = 'published'"
                >
                  发布 ({{ vm.selectedProfile.published_task_count }})
                </button>
                <button
                  class="aupd-task-tab"
                  :class="{ 'aupd-task-tab--active': vm.profileTaskTab === 'accepted' }"
                  @click="vm.profileTaskTab = 'accepted'"
                >
                  接取 ({{ vm.selectedProfile.accepted_task_count }})
                </button>
              </div>
              <div v-if="vm.profileTasksLoading" class="aupd-blacklist-loading"><div class="spinner"></div></div>
              <div v-else-if="vm.profileTasks.length === 0" class="aupd-blacklist-empty">暂无任务</div>
              <div v-else class="aupd-task-grid">
                <button
                  v-for="t in vm.profileTasks"
                  :key="t.id"
                  class="aupd-task-card"
                  @click="openTaskSnapshot(t.id)"
                >
                  <div class="aupd-task-card__top">
                    <span class="aupd-task-card__title">{{ t.title }}</span>
                    <span class="badge aupd-task-card__badge" :class="taskStatus(t.status, t.is_deleted).cls">{{ taskStatus(t.status, t.is_deleted).label }}</span>
                  </div>
                  <div class="aupd-task-card__meta">
                    <span><i class="fa-solid fa-yen-sign"></i> {{ t.price }}</span>
                    <span v-if="t.deadline"><i class="fa-regular fa-clock"></i> {{ formatShort(t.deadline) }}</span>
                    <span><i class="fa-regular fa-calendar"></i> {{ formatShort(t.created_at) }}</span>
                  </div>
                  <div v-if="vm.profileTaskTab === 'published' && t.assignee_display_name" class="aupd-task-card__who">
                    <i class="fa-solid fa-user"></i> {{ t.assignee_display_name }}
                  </div>
                  <div v-if="vm.profileTaskTab === 'accepted'" class="aupd-task-card__who">
                    <i class="fa-solid fa-user"></i> {{ t.publisher_display_name }}
                  </div>
                </button>
              </div>
            </section>
          </template>
          </div><!-- /aupd-body -->
        </div>
      </div>
    </Transition>
  </Teleport>

  <AdminTaskSnapshotDrawer
    :show="snapshotShow"
    :loading="snapshotLoading"
    :snapshot="snapshotData"
    :task-status-map="TASK_STATUS_MAP"
    @close="snapshotShow = false"
  />
</template>

<style scoped>
/* ── Overlay ── */
.aupd-overlay {
  position: fixed;
  inset: 0;
  z-index: 160;
  background: rgba(15, 23, 42, 0.2);
  backdrop-filter: blur(4px);
  -webkit-backdrop-filter: blur(4px);
  display: flex;
  justify-content: flex-end;
}

/* ── Drawer shell ── */
.aupd-drawer {
  width: min(880px, 100vw);
  background: #f8fafc;
  height: 100vh;
  display: flex;
  flex-direction: column;
  box-shadow: -4px 0 24px rgba(0, 0, 0, 0.08);
}

/* ── Drag handle (hidden on desktop) ── */
.aupd-sheet-handle {
  display: none;
  justify-content: center;
  align-items: center;
  padding: 10px 0 4px;
  flex-shrink: 0;
  touch-action: none;
}

.aupd-sheet-handle__bar {
  width: 40px;
  height: 4px;
  border-radius: 2px;
  background: #cbd5e1;
  transition: background 200ms var(--ease);
}

.aupd-sheet-handle:active .aupd-sheet-handle__bar {
  background: #94a3b8;
}

/* ── Header ── */
.aupd-header {
  flex-shrink: 0;
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 18px 22px;
  border-bottom: 1px solid rgba(226, 232, 240, 0.6);
}

.aupd-header h3 {
  margin: 0;
  font-size: 17px;
  font-weight: 700;
}

/* ── Scrollable body ── */
.aupd-body {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 16px 0 20px;
}

.aupd-loading {
  min-height: 220px;
  display: grid;
  place-items: center;
}

/* ── User top card ── */
.aupd-top {
  margin: 0 16px;
  padding: 18px;
  border-radius: var(--radius-2xl);
  background: #fff;
  border: 1px solid rgba(226, 232, 240, 0.6);
  box-shadow: var(--shadow-card);
  display: flex;
  align-items: center;
  gap: 14px;
}

.aupd-avatar {
  width: 72px;
  height: 72px;
  border-radius: 50%;
  object-fit: cover;
  border: 2px solid rgba(255, 255, 255, 0.95);
  flex-shrink: 0;
}

.aupd-top__meta h4 {
  margin: 0;
}

.aupd-top__meta p {
  margin: 4px 0 8px;
  color: #94a3b8;
  font-size: 13px;
}

.aupd-top__badges {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

/* ── Two-column layout ── */
.aupd-two-col {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
  margin: 0 16px;
}

.aupd-two-col > .aupd-panel {
  margin: 0;
}

/* ── Panel cards ── */
.aupd-panel {
  margin: 0 16px;
  padding: 18px;
  border-radius: var(--radius-2xl) !important;
  border: 1px solid rgba(226, 232, 240, 0.6) !important;
  box-shadow: var(--shadow-card) !important;
}

.aupd-panel__title {
  margin: 0 0 12px;
  font-size: 14px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--c-text);
}

.aupd-panel__title i {
  font-size: 13px;
  color: #94a3b8;
}

/* ── KPI grid ── */
.aupd-kpi {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.aupd-kpi__item {
  border-radius: var(--radius-lg);
  background: #f8fafc;
  border: 1px solid rgba(226, 232, 240, 0.6);
  padding: 12px;
}

.aupd-kpi__item span {
  color: #94a3b8;
  font-size: 12px;
  display: block;
}

.aupd-kpi__item strong {
  font-size: 22px;
  color: var(--c-text);
  letter-spacing: -0.02em;
}

/* ── Ban details: 三字段同行 ── */
.aupd-ban-details {
  margin-top: 12px;
  display: flex;
  gap: 12px;
}

.aupd-ban-details .form-group {
  flex: 1;
  min-width: 0;
}

/* ── Always-inline 2-col row (never collapses on mobile) ── */
.aupd-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

/* ── Checkbox group ── */
.aupd-check-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

.aupd-check-grid label {
  border: 1px solid rgba(226, 232, 240, 0.6);
  background: #f8fafc;
  border-radius: var(--radius-md);
  padding: 8px 12px;
  font-size: 13px;
  display: inline-flex;
  gap: 6px;
  align-items: center;
  transition: background 200ms var(--ease);
  cursor: pointer;
  white-space: nowrap;
}

.aupd-check-grid label:hover {
  background: #f1f5f9;
}

/* ── Blacklist head: search + count ── */
.aupd-bl-head {
  display: flex;
  gap: 12px;
  align-items: flex-end;
  margin-bottom: 10px;
}

.aupd-bl-search {
  flex: 1;
  position: relative;
  min-width: 0;
  basis: 0;
}

.aupd-bl-search__icon {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  color: #94a3b8;
  font-size: 12px;
  pointer-events: none;
}

.aupd-bl-search__input {
  padding-left: 34px !important;
  border-radius: var(--radius-full) !important;
  border: none !important;
  background: #f1f5f9 !important;
}

.aupd-bl-search__input:focus {
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.12) !important;
}

.aupd-bl-search__spin {
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
}

.aupd-bl-dropdown {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  right: 0;
  z-index: 10;
  background: #fff;
  border: 1px solid rgba(226, 232, 240, 0.6);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  max-height: 240px;
  overflow-y: auto;
}

.aupd-bl-dropdown__item {
  width: 100%;
  border: none;
  background: transparent;
  padding: 10px 14px;
  text-align: left;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  transition: background 150ms var(--ease);
  cursor: pointer;
}

.aupd-bl-dropdown__item:hover {
  background: #f1f5f9;
}

.aupd-bl-dropdown__item + .aupd-bl-dropdown__item {
  border-top: 1px solid rgba(241, 245, 249, 0.8);
}

.aupd-bl-dropdown__name {
  font-size: 13px;
  font-weight: 500;
  color: var(--c-text);
}

.aupd-bl-dropdown__realname {
  font-weight: 400;
  color: #64748b;
}

.aupd-bl-dropdown__sub {
  font-size: 12px;
  color: #94a3b8;
  white-space: nowrap;
}

.aupd-bl-count {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
  min-width: 0;
  basis: 0;
}

.aupd-bl-count .form-label {
  font-size: 11px;
}

.aupd-bl-count__input {
  text-align: center;
}

.aupd-blacklist-empty {
  color: #6f8096;
  font-size: 13px;
  padding: 10px 0;
}

.aupd-blacklist-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 10px;
}

.aupd-blacklist-item {
  border: 1px solid rgba(226, 232, 240, 0.6);
  border-radius: var(--radius-md);
  padding: 12px;
  background: #f8fafc;
  display: flex;
  justify-content: space-between;
  gap: 8px;
  align-items: center;
}

.aupd-blacklist-item p {
  margin: 3px 0 0;
  color: #94a3b8;
  font-size: 12px;
}

.aupd-blacklist-item__info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.aupd-blacklist-item__name {
  font-size: 13px;
  font-weight: 500;
  color: var(--c-text);
}

.aupd-blacklist-item__realname {
  font-weight: 400;
  color: #64748b;
}

.aupd-blacklist-item__sub {
  font-size: 12px;
  color: #94a3b8;
}

.aupd-blacklist-loading {
  display: grid;
  place-items: center;
  padding: 12px;
}

/* ── Header right: save status + close ── */
.aupd-header__right {
  display: flex;
  align-items: center;
  gap: 4px;
}

.aupd-header__right :deep(.asb-bar) {
  margin-top: 0;
  padding-top: 0;
  border-top: none;
  height: auto;
}

/* ── Task tabs & cards ── */
.aupd-task-tabs {
  position: relative;
  display: flex;
  background: #f1f5f9;
  border-radius: var(--radius-md);
  padding: 3px;
  margin-bottom: 12px;
}

.aupd-task-tab__slider {
  position: absolute;
  top: 3px;
  bottom: 3px;
  left: 3px;
  width: calc(50% - 3px);
  background: #fff;
  border-radius: calc(var(--radius-md) - 2px);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
  transition: transform 220ms cubic-bezier(0.4, 0, 0.2, 1);
  pointer-events: none;
}

.aupd-task-tab__slider--right {
  transform: translateX(100%);
}

.aupd-task-tab {
  flex: 1;
  border: none;
  background: transparent;
  padding: 7px 0;
  font-size: 13px;
  font-weight: 500;
  color: #64748b;
  border-radius: 6px;
  transition: color 200ms var(--ease);
  cursor: pointer;
  position: relative;
}

.aupd-task-tab--active {
  color: var(--c-accent);
}

.aupd-task-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.aupd-task-card {
  border: 1px solid rgba(226, 232, 240, 0.6);
  border-radius: var(--radius-lg);
  background: #f8fafc;
  padding: 12px;
  text-align: left;
  display: flex;
  flex-direction: column;
  gap: 6px;
  transition: border-color 200ms var(--ease), box-shadow 200ms var(--ease);
  cursor: pointer;
}

.aupd-task-card:hover {
  border-color: rgba(59, 130, 246, 0.3);
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.08);
}

.aupd-task-card__top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 6px;
}

.aupd-task-card__title {
  font-size: 13px;
  font-weight: 600;
  color: var(--c-text);
  line-height: 1.3;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  flex: 1;
  min-width: 0;
}

.aupd-task-card__badge {
  flex-shrink: 0;
  font-size: 11px;
}

.aupd-task-card__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  font-size: 12px;
  color: #94a3b8;
}

.aupd-task-card__meta i {
  margin-right: 2px;
}

.aupd-task-card__who {
  font-size: 12px;
  color: #64748b;
}

.aupd-task-card__who i {
  margin-right: 3px;
  font-size: 11px;
}

/* ── Transitions ── */
.aupd-enter-active {
  transition: opacity 0.28s var(--ease);
}
.aupd-leave-active {
  transition: opacity 0.2s var(--ease);
}
.aupd-enter-active .aupd-drawer {
  transition: transform 0.28s var(--ease);
}
.aupd-leave-active .aupd-drawer {
  transition: transform 0.2s var(--ease);
}

.aupd-enter-from,
.aupd-leave-to {
  opacity: 0;
}
.aupd-enter-from .aupd-drawer,
.aupd-leave-to .aupd-drawer {
  transform: translateX(100%);
}

/* ── Mobile: bottom sheet ── */
@media (max-width: 900px) {
  .aupd-overlay {
    flex-direction: column;
    justify-content: flex-end;
    align-items: stretch;
  }

  .aupd-drawer {
    width: 100% !important;
    height: auto !important;
    max-height: 92vh;
    border-radius: 16px 16px 0 0;
    box-shadow: 0 80px 0 0 #f8fafc, 0 -4px 20px rgba(0, 0, 0, 0.1);
    overflow: hidden;
  }

  .aupd-header .btn-ghost {
    display: none;
  }

  .aupd-sheet-handle {
    display: flex;
  }

  .aupd-enter-from .aupd-drawer,
  .aupd-leave-to .aupd-drawer {
    transform: translateY(100%);
  }

  .aupd-two-col {
    grid-template-columns: 1fr;
    margin: 0 12px;
  }

  .aupd-panel {
    margin: 0 12px;
  }

  .aupd-top {
    margin: 0 12px;
  }

  .aupd-ban-details {
    flex-wrap: wrap;
  }

  .aupd-check-grid label {
    flex: 0 0 calc(33.333% - 6px);
  }

  .aupd-task-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .aupd-kpi {
    grid-template-columns: 1fr;
  }
}
</style>
