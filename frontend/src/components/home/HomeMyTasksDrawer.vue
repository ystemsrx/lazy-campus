<script setup lang="ts">
import HomeDrawer from './ui/HomeDrawer.vue'
import type { Task } from '../../types/api'

defineProps<{
  modelValue: boolean
  myPublished: Task[]
  myAccepted: Task[]
  statusOf: (status: string) => { label: string; cls: string }
  isExpired: (iso: string | null) => boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'openTask', task: Task): void
}>()

function handleOpenTask(task: Task) {
  emit('update:modelValue', false)
  emit('openTask', task)
}
</script>

<template>
  <HomeDrawer
    :model-value="modelValue"
    title="我的任务"
    body-class="hv-my-body"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <div class="hv-my-tasks-vertical">
      <div class="hv-my-col">
        <h4>我发布的 <span class="badge badge-default">{{ myPublished.length }}</span></h4>
        <div v-if="myPublished.length" class="hv-record-list">
          <div v-for="t in myPublished" :key="t.id" class="hv-record card card-hover" @click="handleOpenTask(t)">
            <div class="hv-record__top">
              <span class="hv-record__title">{{ t.title }}</span>
              <div class="hv-record__badges">
                <span v-if="t.status === 'open' && isExpired(t.deadline)" class="badge badge-red">已过期</span>
                <span class="badge" :class="statusOf(t.status).cls">{{ statusOf(t.status).label }}</span>
              </div>
            </div>
            <div class="hv-record__meta">
              ¥{{ t.price }}
              <template v-if="t.assignee_display_name"> · 接单者：{{ t.assignee_display_name }}</template>
            </div>
          </div>
        </div>
        <p v-else class="hv-empty-text">暂无发布的任务</p>
      </div>

      <div class="hv-my-col">
        <h4>我接取的 <span class="badge badge-default">{{ myAccepted.length }}</span></h4>
        <div v-if="myAccepted.length" class="hv-record-list">
          <div v-for="t in myAccepted" :key="t.id" class="hv-record card card-hover" @click="handleOpenTask(t)">
            <div class="hv-record__top">
              <span class="hv-record__title">{{ t.title }}</span>
              <span class="badge" :class="statusOf(t.status).cls">{{ statusOf(t.status).label }}</span>
            </div>
            <div class="hv-record__meta">¥{{ t.price }} · 发布者：{{ t.publisher_display_name }}</div>
          </div>
        </div>
        <p v-else class="hv-empty-text">暂无接取的任务</p>
      </div>
    </div>
  </HomeDrawer>
</template>

<style scoped>
.hv-my-body {
  padding: 20px 24px;
}

.hv-my-tasks-vertical {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.hv-my-col h4 {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.hv-record-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.hv-record {
  padding: 14px 16px !important;
}

.hv-record__top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

.hv-record__badges {
  display: flex;
  gap: 5px;
  align-items: center;
  flex-shrink: 0;
}

.hv-record__title {
  font-weight: 600;
  font-size: var(--text-base);
}

.hv-record__meta {
  font-size: var(--text-sm);
  color: var(--c-text-muted);
  margin-top: 4px;
}

.hv-empty-text {
  color: var(--c-text-muted);
  font-size: var(--text-sm);
  padding: 20px 0;
}
</style>
