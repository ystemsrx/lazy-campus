<script setup lang="ts">
import { proxyRefs } from 'vue'

import type { AdminAgentsModel } from '../../composables/admin/useAdminAgents'
import { formatFull, formatShort } from '../../utils/time'
import AgentToolCallCard from '../agent/AgentToolCallCard.vue'
import ChatRichTextRenderer from '../chat/ChatRichTextRenderer.vue'

const props = defineProps<{
  model: AdminAgentsModel
}>()

const vm = proxyRefs(props.model)

function roleLabel(role: string) {
  if (role === 'user') return '用户'
  if (role === 'assistant') return 'AI'
  if (role === 'tool_call') return '工具调用'
  if (role === 'tool') return '工具输出'
  return '系统'
}

</script>

<template>
  <section class="av-agent">
    <div class="av-agent-card">
      <div class="av-agent-card__head">
        <h3>全局开关</h3>
      </div>
      <div class="av-agent-switch-row">
        <span>AI 代理功能</span>
        <button class="btn btn-sm" :class="vm.agentEnabled ? 'btn-success' : 'btn-outline'" :disabled="vm.configSaving" @click="vm.toggleAgentEnabled">
          {{ vm.configSaving ? '保存中…' : vm.agentEnabled ? '已开启' : '已关闭' }}
        </button>
      </div>
    </div>

    <div class="av-agent-card">
      <div class="av-agent-card__head av-agent-card__head--usage">
        <h3>次数管理</h3>
        <div class="av-save-wrap">
          <div class="av-save-item" :class="{ 'av-save-item--visible': vm.quotaSaveStatus === 'saving' }">
            <span class="av-save-spinner"></span>
          </div>
          <div class="av-save-item av-save-item--saved" :class="{ 'av-save-item--visible': vm.quotaSaveStatus === 'saved' }">
            <svg width="17" height="17" viewBox="0 0 18 18" fill="none">
              <path d="M2 9l5 5L16 3" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
            <span>已保存</span>
          </div>
        </div>
      </div>

      <div class="av-agent-toolbar">
        <div class="av-agent-search">
          <i class="fa-solid fa-magnifying-glass"></i>
          <input v-model="vm.userSearch" class="form-input" placeholder="搜索账号/姓名/昵称" />
        </div>
        <div class="av-agent-grant">
          <input v-model.number="vm.usageAmount" class="form-input av-agent-grant__input" type="number" min="0" />
          <button class="btn btn-primary btn-sm" :disabled="vm.usageSubmitting || !vm.hasSelectedUsers" @click="vm.grantUsageToSelected">
            {{ vm.usageSubmitting ? '处理中…' : `发放已选（${vm.selectedUserIds.length}）` }}
          </button>
          <button class="btn btn-outline btn-sm" :disabled="vm.usageSubmitting || !vm.hasSelectedUsers" @click="vm.adjustUsageForSelected">
            {{ vm.usageSubmitting ? '处理中…' : `调整已选（${vm.selectedUserIds.length}）` }}
          </button>
          <button class="btn btn-outline btn-sm" :disabled="vm.usageSubmitting" @click="vm.grantUsageToAll">
            {{ vm.usageSubmitting ? '处理中…' : '发放所有人' }}
          </button>
          <button class="btn btn-danger btn-sm" :disabled="vm.usageSubmitting" @click="vm.adjustUsageForAll">
            {{ vm.usageSubmitting ? '处理中…' : '调整所有人' }}
          </button>
        </div>
      </div>

      <div class="av-agent-table-wrap">
        <table class="av-agent-table">
          <thead>
            <tr>
              <th style="width: 52px;">
                <input :checked="vm.allCurrentPageSelected" type="checkbox" @change="vm.toggleSelectAllCurrentPage" />
              </th>
              <th>用户</th>
              <th>状态</th>
              <th>代理剩余次数</th>
              <th>最近活跃</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="user in vm.userList" :key="user.id">
              <td>
                <input :checked="vm.isUserSelected(user.id)" type="checkbox" @change="vm.toggleUserSelection(user.id)" />
              </td>
              <td>
                <div class="av-agent-user">
                  <strong>{{ user.display_name }}</strong>
                  <span>#{{ user.id }} · {{ user.account }}</span>
                </div>
              </td>
              <td>
                <span class="badge" :class="user.is_active ? 'badge-green' : 'badge-red'">{{ user.is_active ? '启用' : '停用' }}</span>
              </td>
              <td>
                <div class="av-agent-inline-edit">
                  <input
                    v-model.number="vm.userQuotaDraftMap[user.id]"
                    class="form-input av-agent-inline-edit__input"
                    type="number"
                    min="0"
                    @input="vm.handleUserQuotaInput(user)"
                    @blur="vm.handleUserQuotaBlur(user)"
                    @keydown.enter.prevent="vm.handleUserQuotaBlur(user)"
                  />
                </div>
              </td>
              <td>{{ user.last_active ? formatShort(user.last_active) : '从未' }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="vm.userTotalPages > 1" class="av-agent-pagination">
        <button class="btn btn-ghost btn-sm" :disabled="vm.userPage <= 1" @click="vm.userPage -= 1">上一页</button>
        <span>第 {{ vm.userPage }} / {{ vm.userTotalPages }} 页</span>
        <button class="btn btn-ghost btn-sm" :disabled="vm.userPage >= vm.userTotalPages" @click="vm.userPage += 1">下一页</button>
      </div>
    </div>

    <div class="av-agent-card">
      <div class="av-agent-card__head">
        <h3>代理会话审计</h3>
      </div>

      <div class="av-agent-audit">
        <div class="av-agent-sessions">
          <div class="av-agent-search">
            <i class="fa-solid fa-magnifying-glass"></i>
            <input v-model="vm.sessionsSearch" class="form-input" placeholder="搜索任务标题或用户" />
          </div>

          <div class="av-agent-session-list">
            <button
              v-for="item in vm.sessionList"
              :key="item.session_id"
              class="av-agent-session-item"
              :class="{ 'av-agent-session-item--active': vm.selectedSessionId === item.session_id }"
              @click="vm.selectSession(item)"
            >
              <div class="av-agent-session-item__head">
                <strong>#{{ item.task_id }} {{ item.task_title }}</strong>
                <span class="badge" :class="item.status === 'running' ? 'badge-amber' : item.status === 'error' ? 'badge-red' : 'badge-default'">{{ item.status }}</span>
              </div>
              <p>{{ item.user_display_name }} · {{ item.interaction_count }}/{{ item.max_interactions }}</p>
              <small>{{ formatShort(item.updated_at) }}</small>
            </button>
          </div>

          <div v-if="vm.sessionTotalPages > 1" class="av-agent-pagination">
            <button class="btn btn-ghost btn-sm" :disabled="vm.sessionsPage <= 1" @click="vm.sessionsPage -= 1">上一页</button>
            <span>第 {{ vm.sessionsPage }} / {{ vm.sessionTotalPages }} 页</span>
            <button class="btn btn-ghost btn-sm" :disabled="vm.sessionsPage >= vm.sessionTotalPages" @click="vm.sessionsPage += 1">下一页</button>
          </div>
        </div>

        <div class="av-agent-messages">
          <div v-if="!vm.activeSession" class="av-agent-empty">选择左侧会话后可查看消息</div>
          <template v-else>
            <div class="av-agent-messages__head">
              <h4>{{ vm.activeSession.task_title }}</h4>
              <button class="btn btn-outline btn-sm" @click="vm.loadSessionMessages">刷新</button>
            </div>
            <div class="av-agent-message-list">
              <div v-if="vm.messagesLoading" class="av-agent-empty">加载中...</div>
              <div v-else-if="vm.sessionMessages.length === 0" class="av-agent-empty">暂无消息</div>

              <div v-for="msg in vm.sessionMessages" :key="msg.id" class="av-agent-message-item">
                <div class="av-agent-message-item__meta">
                  <strong>{{ roleLabel(msg.role) }}</strong>
                  <span>{{ formatFull(msg.created_at) }}</span>
                </div>
                <AgentToolCallCard
                  v-if="msg.role === 'tool_call'"
                  :tool-name="msg.tool_name"
                  :tool-arguments="msg.tool_arguments"
                  :tool-call-id="msg.tool_call_id"
                />
                <pre v-else-if="msg.role === 'tool'" class="av-agent-tool-output">{{ msg.content }}</pre>
                <div v-else-if="msg.role === 'system'" class="av-agent-system">{{ msg.content }}</div>
                <div v-else class="av-agent-rich-wrap">
                  <ChatRichTextRenderer :content="msg.content || ''" />
                </div>
              </div>
            </div>
          </template>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.av-agent {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.av-agent-card {
  border: 1px solid rgba(226, 232, 240, 0.8);
  border-radius: 16px;
  background: #fff;
  padding: 14px;
}

.av-agent-card__head h3 {
  margin: 0 0 12px;
  font-size: 16px;
}

.av-agent-card__head--usage {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.av-save-wrap {
  position: relative;
  width: 96px;
  height: 22px;
  display: flex;
  align-items: center;
  justify-content: flex-end;
}

.av-save-item {
  position: absolute;
  right: 0;
  display: flex;
  align-items: center;
  gap: 6px;
  opacity: 0;
  transform: translateY(-10px) scale(0.95);
  transition: opacity 500ms cubic-bezier(0.4, 0, 0.2, 1), transform 500ms cubic-bezier(0.4, 0, 0.2, 1);
  pointer-events: none;
}

.av-save-item--visible {
  opacity: 1;
  transform: translateY(0) scale(1);
}

.av-save-item--saved {
  color: #10b981;
  font-size: 13px;
  font-weight: 500;
  letter-spacing: 0.01em;
  transform: translateY(10px) scale(0.95);
}

.av-save-item--saved.av-save-item--visible {
  transform: translateY(0) scale(1);
}

.av-save-spinner {
  width: 18px;
  height: 18px;
  border: 2px solid rgba(148, 163, 184, 0.3);
  border-top-color: #94a3b8;
  border-radius: 50%;
  animation: av-save-spin 0.7s linear infinite;
}

@keyframes av-save-spin {
  to {
    transform: rotate(360deg);
  }
}

.av-agent-switch-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.av-agent-toolbar {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 10px;
  flex-wrap: wrap;
}

.av-agent-search {
  position: relative;
  min-width: 240px;
}

.av-agent-search i {
  position: absolute;
  left: 10px;
  top: 50%;
  transform: translateY(-50%);
  color: #94a3b8;
  font-size: 12px;
}

.av-agent-search :deep(.form-input) {
  padding-left: 32px;
}

.av-agent-grant {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.av-agent-grant__input {
  width: 84px;
}

.av-agent-inline-edit {
  display: flex;
  align-items: center;
  gap: 8px;
}

.av-agent-inline-edit__input {
  width: 78px;
}

.av-agent-table-wrap {
  overflow: auto;
}

.av-agent-table {
  width: 100%;
  border-collapse: collapse;
  min-width: 760px;
}

.av-agent-table th,
.av-agent-table td {
  border-bottom: 1px solid rgba(226, 232, 240, 0.8);
  padding: 10px 8px;
  text-align: left;
  font-size: 13px;
}

.av-agent-user strong {
  display: block;
}

.av-agent-user span {
  color: #94a3b8;
  font-size: 12px;
}

.av-agent-pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
}

.av-agent-audit {
  display: grid;
  grid-template-columns: 360px minmax(0, 1fr);
  gap: 12px;
}

.av-agent-sessions,
.av-agent-messages {
  border: 1px solid rgba(226, 232, 240, 0.8);
  border-radius: 12px;
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  height: 600px;
  min-height: 0;
  overflow: hidden;
}

.av-agent-session-list {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
  overflow-y: auto;
}

.av-agent-session-item {
  text-align: left;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  background: #fff;
  padding: 8px;
}

.av-agent-session-item--active {
  border-color: #3b82f6;
  background: #eff6ff;
}

.av-agent-session-item__head {
  display: flex;
  justify-content: space-between;
  gap: 8px;
}

.av-agent-session-item p {
  margin: 4px 0;
  color: #475569;
  font-size: 12px;
}

.av-agent-session-item small {
  color: #94a3b8;
  font-size: 11px;
}

.av-agent-messages__head {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  align-items: center;
}

.av-agent-messages__head h4 {
  margin: 0;
  font-size: 14px;
}

.av-agent-message-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.av-agent-message-item {
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 8px;
  background: #f8fafc;
}

.av-agent-message-item__meta {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  font-size: 11px;
  color: #94a3b8;
  margin-bottom: 6px;
}

.av-agent-rich-wrap {
  border-radius: 8px;
  padding: 8px;
  background: #fff;
}

.av-agent-tool-output {
  margin: 0;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 8px;
  max-height: 180px;
  overflow: auto;
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-word;
}

.av-agent-system {
  padding: 8px;
  border-radius: 8px;
  background: #fef3c7;
  color: #92400e;
  font-size: 12px;
}

.av-agent-empty {
  color: #94a3b8;
  font-size: 13px;
  text-align: center;
  margin-top: 14px;
}

@media (max-width: 1100px) {
  .av-agent-audit {
    grid-template-columns: 1fr;
  }
}
</style>
