<script setup lang="ts">
import { computed, proxyRefs } from 'vue'

import type { AdminChatsModel } from '../../composables/admin/useAdminChats'
import { formatShort } from '../../utils/time'

const props = defineProps<{
  model: AdminChatsModel
}>()

const vm = proxyRefs(props.model)

const titleText = computed(() => (vm.mode === 'direct' ? '私聊审计' : '任务聊天审计'))

interface ChatDisplayRow {
  key: string
  title: string
  line1: string
  line2: string
  active: boolean
  kind: 'direct' | 'task'
  raw: unknown
}

const displayRows = computed<ChatDisplayRow[]>(() => {
  if (vm.mode === 'direct') {
    return vm.directConversations.map((item) => ({
      key: `${item.user_a_id}-${item.user_b_id}-${item.task_id ?? 0}`,
      title: `${item.user_a_display_name} ↔ ${item.user_b_display_name}`,
      line1: item.task_title ? `任务：${item.task_title}` : '非任务会话',
      line2: `${item.message_count} 条 · ${item.last_message_time ? formatShort(item.last_message_time) : '-'}`,
      active: !!vm.selectedDirect
        && item.user_a_id === vm.selectedDirect.user_a_id
        && item.user_b_id === vm.selectedDirect.user_b_id
        && item.task_id === vm.selectedDirect.task_id,
      kind: 'direct',
      raw: item,
    }))
  }
  return vm.taskConversations.map((item) => ({
    key: `${item.task_id}-${item.session_assignee_id ?? 'none'}`,
    title: `#${item.task_id} ${item.task_title}`,
    line1: `发布者：${item.publisher_display_name}`,
    line2: `${item.message_count} 条 · ${item.last_message_time ? formatShort(item.last_message_time) : '-'}`,
    active: !!vm.selectedTask
      && item.task_id === vm.selectedTask.task_id
      && item.session_assignee_id === vm.selectedTask.session_assignee_id,
    kind: 'task',
    raw: item,
  }))
})

function openRow(row: ChatDisplayRow) {
  if (row.kind === 'direct') {
    vm.loadDirectMessages(row.raw as any)
    return
  }
  vm.loadTaskMessages(row.raw as any)
}
</script>

<template>
  <section class="av-chats">
    <div class="av-chats__head">
      <div>
        <h2>聊天审计中心</h2>
        <p>支持全量检索私聊与任务聊天，满足运营与合规排查需求</p>
      </div>
      <div class="av-chats__mode">
        <button class="av-mode-btn" :class="{ 'av-mode-btn--active': vm.mode === 'direct' }" @click="vm.switchMode('direct')">私聊</button>
        <button class="av-mode-btn" :class="{ 'av-mode-btn--active': vm.mode === 'task' }" @click="vm.switchMode('task')">任务聊天</button>
      </div>
    </div>

    <div class="av-chats__search">
      <i class="fa-solid fa-magnifying-glass"></i>
      <input v-model="vm.search" class="form-input" placeholder="搜索消息内容关键词" />
    </div>

    <div class="av-chat-grid">
      <aside class="av-chat-list card">
        <header>
          <h4>{{ titleText }}</h4>
          <span>{{ vm.total }} 条</span>
        </header>

        <div v-if="vm.loading" class="av-chat-list__loading"><div class="spinner"></div></div>
        <div v-else-if="vm.conversationList.length === 0" class="av-chat-list__empty">暂无会话</div>
        <template v-else>
          <button
            v-for="row in displayRows"
            :key="row.key"
            class="av-chat-list__item"
            :class="{ 'av-chat-list__item--active': row.active }"
            @click="openRow(row)"
          >
            <strong>{{ row.title }}</strong>
            <span>{{ row.line1 }}</span>
            <span>{{ row.line2 }}</span>
          </button>
        </template>

        <footer v-if="vm.totalPages > 1" class="av-chat-list__footer">
          <button class="btn btn-ghost btn-sm" :disabled="vm.page <= 1" @click="vm.goPage(vm.page - 1)">
            <i class="fa-solid fa-chevron-left"></i>
          </button>
          <span>{{ vm.page }} / {{ vm.totalPages }}</span>
          <button class="btn btn-ghost btn-sm" :disabled="vm.page >= vm.totalPages" @click="vm.goPage(vm.page + 1)">
            <i class="fa-solid fa-chevron-right"></i>
          </button>
        </footer>
      </aside>

      <div class="av-chat-messages card">
        <header class="av-chat-messages__head">
          <h4>消息详情</h4>
          <span v-if="vm.selectedDirect || vm.selectedTask">{{ vm.messages.length }} 条</span>
        </header>

        <div v-if="vm.messagesLoading" class="av-chat-messages__loading"><div class="spinner"></div></div>
        <div v-else-if="!vm.selectedDirect && !vm.selectedTask" class="av-chat-messages__empty">
          请选择左侧会话查看记录
        </div>
        <div v-else-if="vm.messages.length === 0" class="av-chat-messages__empty">
          当前会话暂无消息
        </div>
        <div v-else class="av-chat-messages__list">
          <article v-for="msg in vm.messages" :key="msg.id" class="av-msg">
            <div class="av-msg__head">
              <strong>{{ msg.sender_display_name }}</strong>
              <span>{{ msg.sub_label }} · {{ formatShort(msg.created_at) }}</span>
            </div>
            <p>{{ msg.content }}</p>
          </article>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.av-chats {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.av-chats__head {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 12px;
}

.av-chats__head h2 {
  margin: 0;
}

.av-chats__head p {
  margin: 4px 0 0;
  color: #94a3b8;
  font-size: 13px;
}

.av-chats__mode {
  display: flex;
  gap: 4px;
  background: #f1f5f9;
  border-radius: var(--radius-lg);
  padding: 4px;
}

.av-mode-btn {
  border: none;
  background: transparent;
  padding: 7px 14px;
  border-radius: var(--radius-md);
  font-size: 13px;
  color: #94a3b8;
  font-weight: 500;
  transition: all 200ms var(--ease);
}

.av-mode-btn--active {
  background: #fff;
  color: var(--c-accent);
  box-shadow: var(--shadow-sm);
}

.av-chats__search {
  position: relative;
  max-width: 420px;
}

.av-chats__search i {
  position: absolute;
  left: 14px;
  top: 50%;
  transform: translateY(-50%);
  color: #94a3b8;
  font-size: 13px;
}

.av-chats__search :deep(.form-input) {
  padding-left: 36px;
  border-radius: var(--radius-full);
  border: none;
  background: #f1f5f9;
}

.av-chats__search :deep(.form-input:focus) {
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.12);
}

.av-chat-grid {
  display: grid;
  grid-template-columns: minmax(280px, 0.95fr) minmax(0, 1.6fr);
  gap: 14px;
}

.av-chat-list {
  padding: 14px;
  display: flex;
  flex-direction: column;
  min-height: 540px;
  max-height: 74vh;
  border-radius: var(--radius-2xl);
}

.av-chat-list header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 4px 12px;
  border-bottom: 1px solid rgba(226, 232, 240, 0.6);
}

.av-chat-list header h4 {
  margin: 0;
  font-size: 15px;
}

.av-chat-list header span {
  font-size: 12px;
  color: #94a3b8;
}

.av-chat-list__item {
  text-align: left;
  margin-top: 8px;
  border: 1px solid rgba(226, 232, 240, 0.6);
  background: #f8fafc;
  border-radius: var(--radius-md);
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  transition: all 200ms var(--ease);
}

.av-chat-list__item strong {
  font-size: 13px;
  color: var(--c-text);
}

.av-chat-list__item span {
  font-size: 12px;
  color: #94a3b8;
}

.av-chat-list__item:hover {
  background: #f1f5f9;
}

.av-chat-list__item--active {
  border-color: rgba(59, 130, 246, 0.3);
  background: rgba(59, 130, 246, 0.04);
}

.av-chat-list__loading,
.av-chat-list__empty {
  flex: 1;
  display: grid;
  place-items: center;
  color: #94a3b8;
  font-size: 13px;
}

.av-chat-list__footer {
  margin-top: auto;
  padding-top: 12px;
  border-top: 1px solid rgba(226, 232, 240, 0.6);
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 10px;
  color: #64748b;
  font-size: 13px;
}

.av-chat-messages {
  min-height: 540px;
  max-height: 74vh;
  display: flex;
  flex-direction: column;
  border-radius: var(--radius-2xl);
}

.av-chat-messages__head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(226, 232, 240, 0.6);
}

.av-chat-messages__head h4 {
  margin: 0;
  font-size: 15px;
}

.av-chat-messages__head span {
  font-size: 12px;
  color: #94a3b8;
}

.av-chat-messages__loading,
.av-chat-messages__empty {
  flex: 1;
  display: grid;
  place-items: center;
  color: #94a3b8;
  font-size: 13px;
}

.av-chat-messages__list {
  margin-top: 12px;
  flex: 1;
  overflow: auto;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.av-msg {
  border: 1px solid rgba(226, 232, 240, 0.6);
  border-radius: var(--radius-lg);
  background: #f8fafc;
  padding: 12px;
}

.av-msg__head {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  align-items: baseline;
}

.av-msg__head strong {
  color: var(--c-text);
  font-size: 13px;
}

.av-msg__head span {
  color: #94a3b8;
  font-size: 12px;
}

.av-msg p {
  margin: 6px 0 0;
  color: var(--c-text-secondary);
  font-size: 13px;
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.6;
}

@media (max-width: 980px) {
  .av-chat-grid {
    grid-template-columns: 1fr;
  }

  .av-chat-list,
  .av-chat-messages {
    max-height: unset;
    min-height: 320px;
  }
}
</style>
