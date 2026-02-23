<script setup lang="ts">
import { computed, proxyRefs, ref } from 'vue'

import { fetchTaskSnapshot } from '../../api/moderation'
import type { AdminTasksModel } from '../../composables/admin/useAdminTasks'
import type { TaskSnapshot } from '../../composables/admin/useAdminReports'
import type { AdminTaskItem } from '../../types/api'
import { formatShort } from '../../utils/time'
import { appConfirm } from '../AppConfirm.vue'
import AppDropdown from '../AppDropdown.vue'
import AdminTaskSnapshotDrawer from './AdminTaskSnapshotDrawer.vue'

const props = defineProps<{
  model: AdminTasksModel
}>()

const vm = proxyRefs(props.model)

const statusOptions = [
  { value: 'all', label: '全部状态' },
  { value: 'open', label: '待接取' },
  { value: 'in_progress', label: '进行中' },
  { value: 'under_review', label: '审核中' },
  { value: 'completed', label: '已完成' },
  { value: 'canceled', label: '已取消' },
  { value: 'overdue', label: '已过期' },
  { value: 'deleted', label: '已删除' },
]

const flagOptions = [
  { value: 'all', label: '全部任务' },
  { value: 'flagged', label: '仅高优先级' },
  { value: 'pinned', label: '仅置顶' },
  { value: 'urgent', label: '仅加急' },
]


function isExpired(deadline: string | null): boolean {
  if (!deadline) return false
  return new Date(deadline) < new Date()
}

const TASK_STATUS_MAP: Record<string, string> = {
  open: '待接取',
  in_progress: '进行中',
  under_review: '审核中',
  completed: '已完成',
  canceled: '已取消',
}

const showSnapshot = ref(false)
const snapshotLoading = ref(false)
const snapshot = ref<TaskSnapshot | null>(null)
const currentTaskId = ref<number | null>(null)

// Always reads from reactive tasks array so optimistic updates are reflected
const currentTask = computed<AdminTaskItem | null>(() =>
  currentTaskId.value !== null ? (vm.tasks.find(t => t.id === currentTaskId.value) ?? null) : null,
)

async function openSnapshot(task: AdminTaskItem) {
  currentTaskId.value = task.id
  showSnapshot.value = true
  snapshotLoading.value = true
  snapshot.value = null
  try {
    snapshot.value = await fetchTaskSnapshot(task.id)
  } catch {
    showSnapshot.value = false
  } finally {
    snapshotLoading.value = false
  }
}

function closeSnapshot() {
  showSnapshot.value = false
}

function onDrawerSetDemoteLevel(level: number) {
  if (currentTask.value) vm.setDemoteLevel(currentTask.value, level)
}

async function onDelete(taskId: number, taskTitle: string, e: Event) {
  e.stopPropagation()
  const ok = await appConfirm({
    title: '确认删除任务',
    message: `删除后发布者与接单者会收到通知。确定删除「${taskTitle}」吗？`,
    confirmText: '确认删除',
    type: 'danger',
  })
  if (!ok) return
  const task = vm.tasks.find(t => t.id === taskId)
  if (!task) return
  await vm.deleteTask(task)
}

function statusLabel(status: string, isDeleted: boolean) {
  if (isDeleted && status === 'open') return ''
  return TASK_STATUS_MAP[status] || status
}

function statusClass(status: string) {
  if (status === 'completed') return 'badge-green'
  if (status === 'canceled') return 'badge-red'
  if (status === 'in_progress' || status === 'under_review') return 'badge-amber'
  return 'badge-default'
}

const demoteOptions = [
  { value: 0, label: '正常' },
  { value: 1, label: '略降' },
  { value: 2, label: '垫底' },
]

function onDemoteChange(task: AdminTaskItem, level: number, e: Event) {
  e.stopPropagation()
  vm.setDemoteLevel(task, level)
}

function onTogglePin(task: AdminTaskItem, e: Event) {
  e.stopPropagation()
  vm.togglePinned(task)
}

function onToggleUrgent(task: AdminTaskItem, e: Event) {
  e.stopPropagation()
  vm.toggleUrgent(task)
}
</script>

<template>
  <section class="av-tasks">
    <div class="av-tasks__toolbar">
      <div class="av-tasks__search">
        <i class="fa-solid fa-magnifying-glass"></i>
        <input v-model="vm.taskSearch" class="form-input" placeholder="搜索标题/描述/地点" />
      </div>
      <AppDropdown v-model="vm.statusFilter" :options="statusOptions" width="136px" min-width="136px" />
      <AppDropdown v-model="vm.flagFilter" :options="flagOptions" width="136px" min-width="136px" />
      <span class="av-tasks__total">共 {{ vm.total }} 条</span>
    </div>

    <div v-if="vm.loading" class="av-tasks__loading"><div class="spinner"></div></div>
    <div v-else-if="vm.tasks.length === 0" class="av-tasks__empty">
      <i class="fa-regular fa-circle-xmark av-tasks__empty-icon"></i>
      <p>暂无相关的委托任务</p>
    </div>

    <template v-else>
      <div class="av-tasks__grid">
        <article
          v-for="task in vm.tasks"
          :key="task.id"
          class="av-card"
          :class="{
            'av-card--pinned': task.is_pinned && !task.is_deleted,
            'av-card--deleted': task.is_deleted,
          }"
          @click="openSnapshot(task)"
        >
          <!-- 顶部：ID + 徽章 + 价格 -->
          <div class="av-card__top">
            <span class="av-card__id">#{{ task.id }}</span>
            <div class="av-card__badges">
              <span v-if="task.is_deleted" class="badge badge-red"><i class="fa-solid fa-trash"></i></span>
              <span
                v-if="statusLabel(task.status, task.is_deleted)"
                class="badge"
                :class="statusClass(task.status)"
              >{{ statusLabel(task.status, task.is_deleted) }}</span>
              <span v-if="task.is_pinned && !task.is_deleted" class="av-badge-pin">
                <i class="fa-solid fa-thumbtack"></i>
              </span>
              <span v-if="task.report_count > 0" class="av-badge-report">
                <i class="fa-solid fa-flag"></i> {{ task.report_count }}
              </span>
            </div>
            <strong class="av-card__price">¥{{ task.price }}</strong>
          </div>

          <!-- 标题 -->
          <h3 class="av-card__title">{{ task.title }}</h3>

          <!-- 元信息 -->
          <div class="av-card__meta">
            <span class="av-card__meta-item">
              <i class="fa-solid fa-user"></i> {{ task.publisher_display_name }}
            </span>
            <span class="av-card__meta-item">
              <i class="fa-regular fa-clock"></i> {{ formatShort(task.created_at) }}
            </span>
            <span
              v-if="task.deadline"
              class="av-card__meta-item"
              :class="{ 'av-card__meta-expired': isExpired(task.deadline) }"
            >
              <i :class="isExpired(task.deadline) ? 'fa-solid fa-triangle-exclamation' : 'fa-regular fa-calendar-xmark'"></i>
              {{ isExpired(task.deadline) ? '已过期 ' : '截止 ' }}{{ formatShort(task.deadline) }}
            </span>
          </div>

          <!-- 操作区 -->
          <div v-if="!task.is_deleted" class="av-card__controls" @click.stop>
            <button
              class="av-ctrl-btn"
              :class="{ 'av-ctrl-btn--active-urgent': task.is_urgent }"
              :disabled="vm.isOperating(task.id)"
              title="加急"
              @click="onToggleUrgent(task, $event)"
            >
              <i class="fa-solid fa-bolt"></i>
            </button>

            <button
              class="av-ctrl-btn av-ctrl-btn--pin"
              :class="{ 'av-ctrl-btn--active-pin': task.is_pinned }"
              :disabled="vm.isOperating(task.id)"
              title="置顶"
              @click="onTogglePin(task, $event)"
            >
              <i class="fa-solid fa-thumbtack"></i>
            </button>

            <div class="av-demote-slider av-card__demote" @click.stop>
              <div
                class="av-demote-pill"
                :style="{ transform: `translateX(calc(${task.demote_level} * 100%))` }"
              ></div>
              <button
                v-for="opt in demoteOptions"
                :key="opt.value"
                class="av-demote-btn"
                :class="[`av-demote-lv${opt.value}`, { 'av-demote-btn--active': task.demote_level === opt.value }]"
                :disabled="vm.isOperating(task.id)"
                @click="onDemoteChange(task, opt.value, $event)"
              >
                {{ opt.label }}
              </button>
            </div>

            <button
              class="av-ctrl-btn av-ctrl-btn--danger"
              :disabled="vm.isOperating(task.id)"
              title="删除"
              @click="onDelete(task.id, task.title, $event)"
            >
              <i class="fa-solid fa-trash"></i>
            </button>
          </div>
        </article>
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
    </template>

    <AdminTaskSnapshotDrawer
      :show="showSnapshot"
      :loading="snapshotLoading"
      :snapshot="snapshot"
      :task-status-map="TASK_STATUS_MAP"
      :task-id="currentTask?.id ?? null"
      :demote-level="currentTask?.demote_level ?? 0"
      :is-operating-demote="currentTask ? vm.isOperating(currentTask.id) : false"
      @close="closeSnapshot"
      @set-demote-level="onDrawerSetDemoteLevel"
    />
  </section>
</template>

<style scoped>
.av-tasks {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.av-tasks__toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.av-tasks__search {
  position: relative;
  width: min(360px, 100%);
}

.av-tasks__search i {
  position: absolute;
  left: 14px;
  top: 50%;
  transform: translateY(-50%);
  color: #94a3b8;
  font-size: 13px;
}

.av-tasks__search :deep(.form-input) {
  padding-left: 36px;
  border-radius: var(--radius-full);
  border: none;
  background: #f1f5f9;
}

.av-tasks__search :deep(.form-input:focus) {
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.12);
}

.av-tasks__total {
  color: #94a3b8;
  font-size: 13px;
  margin-left: auto;
  white-space: nowrap;
}

/* === Grid === */

.av-tasks__grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
}

@media (min-width: 1024px) {
  .av-tasks__grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

/* === Card === */

.av-card {
  background: #fff;
  border-radius: 14px;
  border: 1px solid rgba(226, 232, 240, 0.7);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
  padding: 14px 16px;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.av-card:hover {
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.08);
  transform: translateY(-1px);
}

.av-card--pinned {
  border-color: rgba(251, 191, 36, 0.5);
  box-shadow: 0 2px 12px -2px rgba(251, 191, 36, 0.18);
}

.av-card--pinned:hover {
  box-shadow: 0 4px 18px -3px rgba(251, 191, 36, 0.28);
}

.av-card--deleted {
  background: #fafafa;
  border-color: rgba(226, 232, 240, 0.4);
  opacity: 0.6;
}

/* Top row: ID · badges · price */

.av-card__top {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}

.av-card__id {
  font-size: 11px;
  color: #94a3b8;
  font-weight: 600;
  white-space: nowrap;
  flex-shrink: 0;
}

.av-card__badges {
  display: flex;
  gap: 4px;
  align-items: center;
  flex: 1;
  min-width: 0;
  overflow: hidden;
}

.av-card__badges .badge {
  font-size: 10px;
  padding: 1px 6px;
  flex-shrink: 0;
}

.av-badge-pin {
  display: inline-flex;
  align-items: center;
  font-size: 10px;
  font-weight: 700;
  padding: 1px 6px;
  border-radius: 100px;
  background: linear-gradient(135deg, #fffbeb, #fef3c7);
  color: #b45309;
  border: 1px solid rgba(251, 191, 36, 0.4);
  flex-shrink: 0;
}

.av-badge-report {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 10px;
  font-weight: 600;
  padding: 1px 6px;
  border-radius: 100px;
  background: #fff1f2;
  color: #e11d48;
  border: 1px solid rgba(225, 29, 72, 0.15);
  flex-shrink: 0;
}

.av-card__price {
  font-size: 16px;
  color: #0f172a;
  font-weight: 700;
  letter-spacing: -0.02em;
  white-space: nowrap;
  flex-shrink: 0;
  margin-left: auto;
}

/* Title */

.av-card__title {
  margin: 0;
  font-size: 14px;
  font-weight: 700;
  color: #0f172a;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* Meta */

.av-card__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  font-size: 11px;
  color: #94a3b8;
}

.av-card__meta-item {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.av-card__meta-expired {
  color: #ef4444;
  font-weight: 600;
}

/* Controls */

.av-card__controls {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  padding-top: 8px;
  border-top: 1px solid #f1f5f9;
  margin-top: auto;
}

.av-ctrl-btn {
  width: 30px;
  height: 30px;
  border-radius: 8px;
  border: none;
  background: #f1f5f9;
  color: #94a3b8;
  font-size: 12px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  flex-shrink: 0;
}

.av-ctrl-btn:hover {
  background: #e2e8f0;
  color: #64748b;
}

.av-ctrl-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.av-ctrl-btn--active-urgent {
  background: #fff1f2;
  color: #e11d48;
  box-shadow: 0 0 0 1px rgba(225, 29, 72, 0.25);
}

.av-ctrl-btn--active-urgent:hover {
  background: #ffe4e6;
}

.av-ctrl-btn--pin {
  border: 1.5px solid rgba(217, 179, 56, 0.4);
}

.av-ctrl-btn--active-pin {
  background: #fffbeb;
  color: #d97706;
  border-color: #f59e0b;
  box-shadow: 0 0 0 1px rgba(245, 158, 11, 0.35);
}

.av-ctrl-btn--active-pin:hover {
  background: #fef3c7;
}

.av-ctrl-btn--danger {
  background: transparent;
  color: #cbd5e1;
  margin-left: auto;
}

.av-ctrl-btn--danger:hover {
  background: #fff1f2;
  color: #ef4444;
}

/* Demote Slider */

.av-demote-slider {
  position: relative;
  display: flex;
  background: rgba(241, 245, 249, 0.9);
  padding: 2px;
  border-radius: 8px;
  border: 1px solid rgba(226, 232, 240, 0.6);
  flex: 1;
  min-width: 0;
}

/* Sliding pill indicator */
.av-demote-pill {
  position: absolute;
  top: 2px;
  bottom: 2px;
  left: 2px;
  width: calc((100% - 4px) / 3);
  background: #fff;
  border-radius: 6px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  pointer-events: none;
  z-index: 0;
}

.av-demote-btn {
  flex: 1;
  padding: 3px 0;
  font-size: 11px;
  font-weight: 600;
  border: none;
  background: transparent;
  color: #94a3b8;
  border-radius: 6px;
  cursor: pointer;
  transition: color 0.2s ease;
  white-space: nowrap;
  text-align: center;
  position: relative;
  z-index: 1;
}

/* Color-coded active states */
.av-demote-lv0.av-demote-btn--active { color: #16a34a; }
.av-demote-lv1.av-demote-btn--active { color: #d97706; }
.av-demote-lv2.av-demote-btn--active { color: #dc2626; }

.av-demote-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

/* Hide demote slider on mobile — moved into snapshot drawer */
@media (max-width: 900px) {
  .av-card__demote {
    display: none;
  }
}

/* States */

.av-tasks__loading,
.av-tasks__empty {
  display: grid;
  place-items: center;
  padding: 48px 0;
  color: #94a3b8;
}

.av-tasks__empty-icon {
  font-size: 40px;
  color: #cbd5e1;
  margin-bottom: 10px;
}

.av-tasks__empty p {
  margin: 0;
  font-weight: 500;
}

/* Pagination */

.av-pagination {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 10px;
  color: #64748b;
  font-size: 13px;
}
</style>
