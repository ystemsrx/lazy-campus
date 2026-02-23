<script setup lang="ts">
import { proxyRefs, reactive, watch } from 'vue'

import { appConfirm } from '../AppConfirm.vue'
import type { AdminTasksModel } from '../../composables/admin/useAdminTasks'
import { formatShort } from '../../utils/time'
import AppDropdown from '../AppDropdown.vue'

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
]

const flagOptions = [
  { value: 'all', label: '全部任务' },
  { value: 'flagged', label: '仅高优先级' },
  { value: 'pinned', label: '仅置顶' },
  { value: 'urgent', label: '仅加急' },
]

const deletedOptions = [
  { value: 'all', label: '含已删除' },
  { value: 'normal', label: '仅正常' },
  { value: 'deleted', label: '仅已删除' },
]

const noteDraft = reactive<Record<number, string>>({})

watch(
  () => vm.tasks,
  (tasks) => {
    for (const t of tasks) {
      noteDraft[t.id] = t.admin_note || ''
    }
  },
  { immediate: true },
)

async function onDelete(taskId: number, taskTitle: string) {
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

function statusLabel(status: string) {
  if (status === 'open') return '待接取'
  if (status === 'in_progress') return '进行中'
  if (status === 'under_review') return '审核中'
  if (status === 'completed') return '已完成'
  if (status === 'canceled') return '已取消'
  return status
}

function statusClass(status: string) {
  if (status === 'completed') return 'badge-green'
  if (status === 'canceled') return 'badge-red'
  if (status === 'in_progress' || status === 'under_review') return 'badge-amber'
  return 'badge-default'
}

async function saveNote(taskId: number) {
  const task = vm.tasks.find(t => t.id === taskId)
  if (!task) return
  await vm.updateAdminNote(task, noteDraft[taskId] || '')
}
</script>

<template>
  <section class="av-tasks">
    <div class="av-tasks__head">
      <div>
        <h2>任务处置中心</h2>
        <p>查看所有任务，执行删除、置顶、加急、备注等主动处置</p>
      </div>
      <span class="av-tasks__total">共 {{ vm.total }} 条</span>
    </div>

    <div class="av-tasks__toolbar">
      <div class="av-tasks__search">
        <i class="fa-solid fa-magnifying-glass"></i>
        <input v-model="vm.taskSearch" class="form-input" placeholder="搜索标题/描述/地点" />
      </div>
      <AppDropdown v-model="vm.statusFilter" :options="statusOptions" width="136px" min-width="136px" />
      <AppDropdown v-model="vm.flagFilter" :options="flagOptions" width="136px" min-width="136px" />
      <AppDropdown v-model="vm.deletedFilter" :options="deletedOptions" width="120px" min-width="120px" />
    </div>

    <div v-if="vm.loading" class="av-tasks__loading"><div class="spinner"></div></div>
    <div v-else-if="vm.tasks.length === 0" class="av-tasks__empty">暂无任务数据</div>

    <template v-else>
      <div class="av-tasks__list">
        <article
          v-for="task in vm.tasks"
          :key="task.id"
          class="card av-task-card"
          :class="{
            'av-task-card--flagged': (task.is_pinned || task.is_urgent) && !task.is_deleted,
            'av-task-card--deleted': task.is_deleted,
          }"
        >
          <div class="av-task-card__top">
            <div class="av-task-card__title-wrap">
              <h4>#{{ task.id }} {{ task.title }}</h4>
              <div class="av-task-card__badges">
                <span v-if="task.is_deleted" class="badge badge-red"><i class="fa-solid fa-trash"></i> 已删除</span>
                <span class="badge" :class="statusClass(task.status)">{{ statusLabel(task.status) }}</span>
                <span v-if="task.is_pinned && !task.is_deleted" class="badge badge-blue"><i class="fa-solid fa-thumbtack"></i> 置顶</span>
                <span v-if="task.is_urgent && !task.is_deleted" class="badge badge-amber"><i class="fa-solid fa-bolt"></i> 加急</span>
              </div>
            </div>
            <strong class="av-task-card__price">¥{{ task.price }}</strong>
          </div>

          <div class="av-task-card__meta">
            <span>发布者：{{ task.publisher_display_name }}</span>
            <span>接单者：{{ task.assignee_display_name || '未接单' }}</span>
            <span>分类：{{ task.category_name || '未分类' }}</span>
            <span>举报：{{ task.report_count }}</span>
            <span>创建：{{ formatShort(task.created_at) }}</span>
            <span>截止：{{ task.deadline ? formatShort(task.deadline) : '未设置' }}</span>
          </div>

          <template v-if="!task.is_deleted">
            <div class="av-task-card__note">
              <input
                v-model="noteDraft[task.id]"
                class="form-input"
                placeholder="管理员备注（会通知任务参与者）"
              />
              <button class="btn btn-outline btn-sm" :disabled="vm.isOperating(task.id)" @click="saveNote(task.id)">
                保存备注
              </button>
            </div>

            <div class="av-task-card__actions">
              <button class="btn btn-outline btn-sm" :disabled="vm.isOperating(task.id)" @click="vm.togglePinned(task)">
                <i class="fa-solid fa-thumbtack"></i>
                {{ task.is_pinned ? '取消置顶' : '置顶' }}
              </button>
              <button class="btn btn-outline btn-sm" :disabled="vm.isOperating(task.id)" @click="vm.toggleUrgent(task)">
                <i class="fa-solid fa-bolt"></i>
                {{ task.is_urgent ? '取消加急' : '加急' }}
              </button>
              <button class="btn btn-danger btn-sm" :disabled="vm.isOperating(task.id)" @click="onDelete(task.id, task.title)">
                <i class="fa-solid fa-trash"></i>
                删除任务
              </button>
            </div>
          </template>
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
  </section>
</template>

<style scoped>
.av-tasks {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.av-tasks__head {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 12px;
}

.av-tasks__head h2 {
  margin: 0;
}

.av-tasks__head p {
  margin: 4px 0 0;
  color: #94a3b8;
  font-size: 13px;
}

.av-tasks__total {
  color: #94a3b8;
  font-size: 13px;
}

.av-tasks__toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.av-tasks__search {
  position: relative;
  width: min(440px, 100%);
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

.av-tasks__list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.av-task-card {
  padding: 20px !important;
  border: 1px solid rgba(226, 232, 240, 0.6) !important;
  border-radius: var(--radius-2xl) !important;
  background: #fff;
  box-shadow: var(--shadow-card) !important;
  transition: box-shadow 200ms var(--ease);
}

.av-task-card:hover {
  box-shadow: var(--shadow-card-hover) !important;
}

.av-task-card--flagged {
  background: rgba(255, 255, 255, 0.9);
  border-color: rgba(59, 130, 246, 0.15) !important;
}

.av-task-card--deleted {
  background: #fafafa;
  border-color: rgba(226, 232, 240, 0.4) !important;
  opacity: 0.65;
}

.av-task-card__top {
  display: flex;
  justify-content: space-between;
  gap: 10px;
}

.av-task-card__title-wrap h4 {
  margin: 0;
}

.av-task-card__badges {
  margin-top: 6px;
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.av-task-card__price {
  font-size: 24px;
  color: var(--c-text);
  font-weight: 700;
  letter-spacing: -0.02em;
}

.av-task-card__meta {
  margin-top: 10px;
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  color: #94a3b8;
  font-size: 12px;
}

.av-task-card__note {
  margin-top: 12px;
  display: flex;
  gap: 8px;
}

.av-task-card__note .form-input {
  border-radius: var(--radius-md);
}

.av-task-card__actions {
  margin-top: 12px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.av-task-card__actions .btn {
  border-radius: var(--radius-md);
}

.av-tasks__loading,
.av-tasks__empty {
  display: grid;
  place-items: center;
  padding: 48px 0;
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

@media (max-width: 720px) {
  .av-task-card__note {
    flex-direction: column;
  }
}
</style>
