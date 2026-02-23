<script setup lang="ts">
import { computed, nextTick, proxyRefs, ref, watch } from 'vue'
import {
  Ban,
  ShieldCheck,
} from 'lucide-vue-next'

import HomeAvatar from '../home/ui/HomeAvatar.vue'
import ChatRichTextRenderer from '../chat/ChatRichTextRenderer.vue'
import AdminTaskSnapshotDrawer from './AdminTaskSnapshotDrawer.vue'
import type { AdminChatsModel } from '../../composables/admin/useAdminChats'
import type { ChatFilterMode } from '../../composables/admin/useAdminChats'
import { formatShort } from '../../utils/time'
import {
  getFileIconComponent,
  isImageMime,
  ATTACHMENT_MSG_PREFIX,
} from '../../composables/chat/attachmentUtils'

const props = defineProps<{
  model: AdminChatsModel
}>()

const vm = proxyRefs(props.model)

const TASK_STATUS_MAP: Record<string, string> = {
  open: '待接取',
  in_progress: '进行中',
  under_review: '审核中',
  completed: '已完成',
  canceled: '已取消',
}

function taskStatusLabel(status: string | null) {
  if (!status) return '未知'
  return TASK_STATUS_MAP[status] || status
}

function taskStatusCls(status: string | null) {
  if (!status) return ''
  if (status === 'completed') return 'ts-done'
  if (status === 'canceled') return 'ts-canceled'
  if (status === 'in_progress' || status === 'under_review') return 'ts-active'
  return 'ts-open'
}

const FILTERS: { key: ChatFilterMode; label: string; icon: string }[] = [
  { key: 'all', label: '全部对话', icon: 'fa-solid fa-comments' },
  { key: 'task', label: '任务关联', icon: 'fa-solid fa-list-check' },
  { key: 'direct', label: '接单私信', icon: 'fa-regular fa-comment-dots' },
]

const sliderIndex = computed(() => FILTERS.findIndex(f => f.key === vm.mode))

interface ChatDisplayRow {
  key: string
  title: string
  line1: string
  line2: string
  lastMsg: string | null
  active: boolean
  kind: 'direct' | 'task'
  raw: unknown
}

function buildDirectRows(): ChatDisplayRow[] {
  return vm.directConversations.map((item) => ({
    key: `d-${item.user_a_id}-${item.user_b_id}-${item.task_id ?? 0}`,
    title: `${item.user_a_display_name} ↔ ${item.user_b_display_name}`,
    line1: item.task_title ? `任务：${item.task_title}` : '私信会话',
    line2: `${item.message_count} 条 · ${item.last_message_time ? formatShort(item.last_message_time) : '-'}`,
    lastMsg: item.last_message,
    active: !!vm.selectedDirect
      && item.user_a_id === vm.selectedDirect.user_a_id
      && item.user_b_id === vm.selectedDirect.user_b_id
      && item.task_id === vm.selectedDirect.task_id,
    kind: 'direct',
    raw: item,
  }))
}

function buildTaskRows(): ChatDisplayRow[] {
  return vm.taskConversations.map((item) => ({
    key: `t-${item.task_id}-${item.session_assignee_id ?? 'none'}`,
    title: `#${item.task_id} ${item.task_title}`,
    line1: `${item.publisher_display_name}${item.session_assignee_display_name ? ' → ' + item.session_assignee_display_name : ''}`,
    line2: `${item.message_count} 条 · ${item.last_message_time ? formatShort(item.last_message_time) : '-'}`,
    lastMsg: item.last_message,
    active: !!vm.selectedTask
      && item.task_id === vm.selectedTask.task_id
      && item.session_assignee_id === vm.selectedTask.session_assignee_id,
    kind: 'task',
    raw: item,
  }))
}

const displayRows = computed<ChatDisplayRow[]>(() => {
  if (vm.mode === 'direct') return buildDirectRows()
  if (vm.mode === 'task') return [...buildDirectRows(), ...buildTaskRows()]
  return [...buildDirectRows(), ...buildTaskRows()]
})

function openRow(row: ChatDisplayRow) {
  if (row.kind === 'direct') {
    vm.loadDirectMessages(row.raw as any)
    return
  }
  vm.loadTaskMessages(row.raw as any)
}

const hasSelection = computed(() => !!vm.selectedDirect || !!vm.selectedTask)

function isAttachmentMsg(content: string) {
  return content.startsWith(ATTACHMENT_MSG_PREFIX)
}

function getAttachmentName(content: string) {
  return content.replace(ATTACHMENT_MSG_PREFIX, '').trim()
}

function getMsgAttachments(rawMsgId: number) {
  return vm.attachments.filter(a => a.message_id === rawMsgId)
}

const bannedUsers = ref<Set<number>>(new Set())

function toggleBan(userId: number) {
  const willBan = !bannedUsers.value.has(userId)
  if (willBan) {
    bannedUsers.value.add(userId)
  } else {
    bannedUsers.value.delete(userId)
  }
  bannedUsers.value = new Set(bannedUsers.value)
  vm.toggleBanContact(userId, willBan)
}

function goBack() {
  vm.clearSelection()
}

const detailBodyRef = ref<HTMLElement | null>(null)

watch(() => vm.messagesLoading, (loading) => {
  if (!loading && vm.messages.length > 0) {
    nextTick(() => {
      if (detailBodyRef.value) {
        detailBodyRef.value.scrollTop = detailBodyRef.value.scrollHeight
      }
    })
  }
})
</script>

<template>
  <section class="ac">
    <!-- ═══ LEFT: List Panel ═══ -->
    <div class="ac__list-panel" :class="{ 'ac__list-panel--hidden-mobile': hasSelection }">
      <div class="ac__list-head">
        <!-- 搜索 -->
        <div class="ac__search-wrap">
          <i class="fa-solid fa-magnifying-glass ac__search-icon"></i>
          <input
            v-model="vm.search"
            type="text"
            class="ac__search-input"
            placeholder="搜索消息内容关键词..."
          />
        </div>

        <!-- 滑动选择器 -->
        <div class="ac__subtabs">
          <div
            class="ac__subtabs-slider"
            :style="{ transform: `translateX(${sliderIndex * 100}%)` }"
          ></div>
          <button
            v-for="f in FILTERS"
            :key="f.key"
            class="ac__subtab"
            :class="{ 'ac__subtab--active': vm.mode === f.key }"
            @click="vm.switchMode(f.key)"
          >
            <i :class="f.icon"></i>
            {{ f.label }}
          </button>
        </div>
      </div>

      <!-- 会话列表 -->
      <div class="ac__list-body">
        <div v-if="vm.loading" class="ac__list-loading"><div class="spinner"></div></div>
        <template v-else-if="displayRows.length">
          <div
            v-for="row in displayRows"
            :key="row.key"
            class="ac__item"
            :class="{ 'ac__item--selected': row.active }"
            @click="openRow(row)"
          >
            <div class="ac__item-top">
              <span class="ac__item-title">{{ row.title }}</span>
              <span class="ac__item-time">{{ row.line2.split('·').pop()?.trim() }}</span>
            </div>
            <p class="ac__item-sub">{{ row.line1 }}</p>
            <p v-if="row.lastMsg" class="ac__item-last">{{ row.lastMsg }}</p>
          </div>
        </template>
        <div v-else class="ac__list-empty">
          <i class="fa-regular fa-folder-open ac__list-empty-icon"></i>
          <p>暂无会话记录</p>
        </div>
      </div>

      <!-- 分页 -->
      <div v-if="vm.totalPages > 1" class="ac__list-footer">
        <button class="btn btn-ghost btn-sm" :disabled="vm.page <= 1" @click="vm.goPage(vm.page - 1)">
          <i class="fa-solid fa-chevron-left"></i>
        </button>
        <span>{{ vm.page }} / {{ vm.totalPages }}</span>
        <button class="btn btn-ghost btn-sm" :disabled="vm.page >= vm.totalPages" @click="vm.goPage(vm.page + 1)">
          <i class="fa-solid fa-chevron-right"></i>
        </button>
      </div>
    </div>

    <!-- ═══ RIGHT: Detail Panel ═══ -->
    <div class="ac__detail-panel" :class="{ 'ac__detail-panel--show-mobile': hasSelection }">
      <template v-if="hasSelection && !vm.messagesLoading">
        <!-- 顶栏：用户信息 -->
        <div class="ac__detail-head">
          <!-- 返回按钮（左锚） -->
          <button class="ac__back-btn" @click="goBack">
            <i class="fa-solid fa-arrow-left"></i>
          </button>

          <!-- 参与者区域（居中） -->
          <div class="ac__detail-head-center">
            <template v-if="vm.participantA">
              <div class="ac__head-user">
                <div class="ac__head-ava-col">
                  <div class="ac__head-ava-wrap">
                    <HomeAvatar
                      :avatar-url="vm.participantA.avatar_url"
                      :gender="vm.participantA.gender"
                      size="md"
                      :alt="vm.participantA.display_name"
                    />
                    <div v-if="bannedUsers.has(vm.participantA.id)" class="ac__head-ban-dot">
                      <Ban :size="8" />
                    </div>
                  </div>
                  <span class="ac__head-name ac__head-name--a">{{ vm.participantA.display_name }}</span>
                </div>
                <button
                  class="ac__ban-btn"
                  :class="{ 'ac__ban-btn--active': bannedUsers.has(vm.participantA.id) }"
                  :title="bannedUsers.has(vm.participantA.id) ? '解封联系' : '禁止联系'"
                  @click="toggleBan(vm.participantA.id)"
                >
                  <span class="ac__ban-btn-text">{{ bannedUsers.has(vm.participantA.id) ? '解封' : '禁止' }}</span>
                  <i class="ac__ban-btn-icon" :class="bannedUsers.has(vm.participantA.id) ? 'fa-solid fa-lock-open' : 'fa-solid fa-ban'"></i>
                </button>
              </div>

              <template v-if="vm.participantB">
                <span class="ac__head-sep">↔</span>
                <div class="ac__head-user">
                  <div class="ac__head-ava-col">
                    <div class="ac__head-ava-wrap">
                      <HomeAvatar
                        :avatar-url="vm.participantB.avatar_url"
                        :gender="vm.participantB.gender"
                        size="md"
                        :alt="vm.participantB.display_name"
                      />
                      <div v-if="bannedUsers.has(vm.participantB.id)" class="ac__head-ban-dot">
                        <Ban :size="8" />
                      </div>
                    </div>
                    <span class="ac__head-name ac__head-name--b">{{ vm.participantB.display_name }}</span>
                  </div>
                  <button
                    class="ac__ban-btn"
                    :class="{ 'ac__ban-btn--active': bannedUsers.has(vm.participantB.id) }"
                    :title="bannedUsers.has(vm.participantB.id) ? '解封联系' : '禁止联系'"
                    @click="toggleBan(vm.participantB.id)"
                  >
                    <span class="ac__ban-btn-text">{{ bannedUsers.has(vm.participantB.id) ? '解封' : '禁止' }}</span>
                    <i class="ac__ban-btn-icon" :class="bannedUsers.has(vm.participantB.id) ? 'fa-solid fa-lock-open' : 'fa-solid fa-ban'"></i>
                  </button>
                </div>
              </template>
            </template>
          </div>

          <!-- 消息数（右锚） -->
          <p class="ac__detail-subtitle">{{ vm.messages.length }} 条</p>
        </div>

        <!-- 可滚动内容 -->
        <div ref="detailBodyRef" class="ac__detail-body">
          <!-- 任务快照 -->
          <div
            v-if="vm.taskInfo"
            class="ac__task-card"
            @click="vm.openSnapshot(vm.taskInfo.id)"
          >
            <div class="ac__task-icon">
              <i class="fa-solid fa-list-check"></i>
            </div>
            <div class="ac__task-body">
              <div class="ac__task-top">
                <h4 class="ac__task-title">#{{ vm.taskInfo.id }} {{ vm.taskInfo.title }}</h4>
                <span class="ac__task-status" :class="taskStatusCls(vm.taskInfo.status)">
                  {{ taskStatusLabel(vm.taskInfo.status) }}
                </span>
              </div>
              <p v-if="vm.taskInfo.price != null" class="ac__task-price">¥{{ vm.taskInfo.price }}</p>
            </div>
          </div>

          <!-- 消息列表 -->
          <div v-if="vm.messages.length === 0" class="ac__no-msg">当前会话暂无消息</div>
          <div v-else class="ac__messages">
            <div
              v-for="msg in vm.messages"
              :key="msg.id"
              class="ac__msg"
              :class="{
                'ac__msg--left': vm.participantA && msg.sender_id === vm.participantA.id,
                'ac__msg--right': !vm.participantA || msg.sender_id !== vm.participantA.id,
              }"
            >
              <div class="ac__msg-row">
                <HomeAvatar
                  v-if="vm.participantA && msg.sender_id === vm.participantA.id"
                  :avatar-url="msg.sender_avatar_url"
                  :gender="msg.sender_gender"
                  size="sm"
                  :alt="msg.sender_display_name"
                  class="ac__msg-ava"
                />

                <div class="ac__msg-body">
                  <span
                    class="ac__msg-meta"
                    :class="{
                      'ac__msg-meta--right': !vm.participantA || msg.sender_id !== vm.participantA.id,
                      'ac__msg-meta--a': vm.participantA && msg.sender_id === vm.participantA.id,
                      'ac__msg-meta--b': !vm.participantA || msg.sender_id !== vm.participantA.id,
                    }"
                  >
                    {{ msg.sender_display_name }}
                    <span class="ac__msg-time">{{ formatShort(msg.created_at) }}</span>
                  </span>

                  <div
                    v-if="!isAttachmentMsg(msg.content)"
                    class="ac__bubble"
                    :class="{
                      'ac__bubble--left': vm.participantA && msg.sender_id === vm.participantA.id,
                      'ac__bubble--right': !vm.participantA || msg.sender_id !== vm.participantA.id,
                      'ac__bubble--blocked': msg.blocked,
                    }"
                  >
                    <ChatRichTextRenderer :content="msg.content" />
                  </div>

                  <div v-if="getMsgAttachments(msg.rawId).length" class="ac__atts">
                    <div v-for="att in getMsgAttachments(msg.rawId)" :key="att.id" class="ac__att-item">
                      <a :href="att.file_url" target="_blank" class="ac__att-link">
                        <img v-if="isImageMime(att.mime_type)" :src="att.file_url" class="ac__att-thumb" />
                        <div v-else class="ac__att-file">
                          <component :is="getFileIconComponent(att.mime_type, att.file_name)" :size="24" />
                          <span class="ac__att-ext">{{ att.file_name.split('.').pop()?.toUpperCase() }}</span>
                        </div>
                      </a>
                    </div>
                  </div>

                  <div v-else-if="isAttachmentMsg(msg.content) && getMsgAttachments(msg.rawId).length === 0" class="ac__atts">
                    <div class="ac__att-item">
                      <div class="ac__att-link ac__att-deleted">
                        <div class="ac__att-file">
                          <component :is="getFileIconComponent('', getAttachmentName(msg.content))" :size="24" />
                          <span class="ac__att-ext">{{ getAttachmentName(msg.content).split('.').pop()?.toUpperCase() || '文件' }}</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div v-if="msg.blocked" class="ac__msg-blocked">
                    <ShieldCheck :size="12" />
                    <span>此消息已被系统拦截</span>
                  </div>
                </div>

                <HomeAvatar
                  v-if="!vm.participantA || msg.sender_id !== vm.participantA.id"
                  :avatar-url="msg.sender_avatar_url"
                  :gender="msg.sender_gender"
                  size="sm"
                  :alt="msg.sender_display_name"
                  class="ac__msg-ava"
                />
              </div>
            </div>
          </div>

          <div class="ac__detail-spacer"></div>
        </div>
      </template>

      <!-- 加载中 -->
      <div v-else-if="vm.messagesLoading" class="ac__empty-detail">
        <div class="spinner"></div>
      </div>

      <!-- 空状态 -->
      <div v-else class="ac__empty-detail">
        <div class="ac__empty-circle">
          <i class="fa-solid fa-comments"></i>
        </div>
        <h3>未选择对话</h3>
        <p>请在左侧列表中选择一个会话以查看聊天详情。</p>
      </div>
    </div>

    <AdminTaskSnapshotDrawer
      :show="vm.showSnapshot"
      :loading="vm.snapshotLoading"
      :snapshot="vm.snapshot"
      :task-status-map="TASK_STATUS_MAP"
      @close="vm.closeSnapshot"
    />
  </section>
</template>

<style scoped>
/* ══ Layout — mirrors AdminReportsSection ══ */
.ac {
  display: flex;
  align-items: flex-start;
  flex: 1;
  min-height: 0;
  height: 100%;
  background: transparent;
}

/* ── Left list panel ── */
.ac__list-panel {
  width: 340px;
  height: 100%;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  border-right: 1px solid rgba(226, 232, 240, 0.6);
  background: #fff;
  overflow: hidden;
}

/* ── List header ── */
.ac__list-head {
  padding: 20px;
  border-bottom: 1px solid rgba(241, 245, 249, 0.8);
}

/* ── Slider tabs ── */
.ac__subtabs {
  position: relative;
  display: flex;
  background: #f1f5f9;
  border-radius: var(--radius-lg);
  padding: 4px;
  margin-top: 12px;
}

.ac__subtabs-slider {
  position: absolute;
  top: 4px;
  left: 4px;
  width: calc(33.333% - 2.67px);
  height: calc(100% - 8px);
  background: #fff;
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  transition: transform 240ms cubic-bezier(0.4, 0, 0.2, 1);
  pointer-events: none;
}

.ac__subtab {
  flex: 1;
  padding: 7px 8px;
  border: none;
  border-radius: var(--radius-md);
  background: transparent;
  color: #94a3b8;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: color 200ms var(--ease);
  font-family: var(--font-sans);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  position: relative;
  z-index: 1;
}

.ac__subtab--active {
  color: var(--c-accent);
}

/* ── Search ── */
.ac__search-wrap {
  position: relative;
}

.ac__search-icon {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  color: #94a3b8;
  font-size: 13px;
  pointer-events: none;
}

.ac__search-input {
  width: 100%;
  padding: 9px 14px 9px 34px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: var(--radius-lg);
  font-size: 13px;
  font-family: var(--font-sans);
  color: var(--c-text);
  outline: none;
  transition: border-color 200ms var(--ease), box-shadow 200ms var(--ease);
  box-sizing: border-box;
}

.ac__search-input::placeholder {
  color: #94a3b8;
}

.ac__search-input:focus {
  border-color: var(--c-accent);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.08);
}

/* ── List body ── */
.ac__list-body {
  flex: 1;
  overflow-y: auto;
}

.ac__list-loading {
  display: flex;
  justify-content: center;
  padding: 48px;
}

/* ── List items ── */
.ac__item {
  padding: 14px 16px;
  cursor: pointer;
  border-left: 4px solid transparent;
  border-bottom: 1px solid rgba(241, 245, 249, 0.8);
  transition: all 150ms var(--ease);
}

.ac__item:hover {
  background: rgba(248, 250, 252, 0.8);
}

.ac__item--selected {
  background: rgba(59, 130, 246, 0.04);
  border-left-color: var(--c-accent);
}

.ac__item-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
  gap: 8px;
}

.ac__item-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--c-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ac__item-time {
  font-size: 12px;
  color: #94a3b8;
  flex-shrink: 0;
}

.ac__item-sub {
  font-size: 12px;
  color: #94a3b8;
  margin: 0 0 4px;
}

.ac__item-last {
  font-size: 12px;
  color: #64748b;
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ac__list-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  color: #94a3b8;
}

.ac__list-empty-icon {
  font-size: 36px;
  color: #cbd5e1;
  margin-bottom: 12px;
}

.ac__list-empty p {
  margin: 0;
  font-size: 13px;
}

/* ── Pagination ── */
.ac__list-footer {
  padding: 12px 16px;
  border-top: 1px solid rgba(241, 245, 249, 0.8);
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 10px;
  color: #64748b;
  font-size: 13px;
}

/* ══ Right detail panel ══ */
.ac__detail-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #f8fafc;
  min-width: 0;
  height: 100%;
  min-height: 0;
}

/* ── Detail header ── */
.ac__detail-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 24px;
  background: rgba(255, 255, 255, 0.9);
  border-bottom: 1px solid rgba(226, 232, 240, 0.6);
  flex-shrink: 0;
  z-index: 20;
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  gap: 8px;
}

.ac__detail-head-center {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  flex: 1;
  min-width: 0;
}

.ac__back-btn {
  display: none;
  width: 36px;
  height: 36px;
  border: none;
  background: transparent;
  color: #64748b;
  font-size: 16px;
  border-radius: 50%;
  cursor: pointer;
  transition: all 200ms var(--ease);
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.ac__back-btn:hover {
  background: #f1f5f9;
  color: var(--c-text);
}

.ac__detail-subtitle {
  font-size: 12px;
  color: #94a3b8;
  white-space: nowrap;
  flex-shrink: 0;
  margin: 0;
}

/* ── Head user inline ── */
.ac__head-user {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}

/* column: avatar on top, name below */
.ac__head-ava-col {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  min-width: 0;
}

.ac__head-ava-wrap {
  position: relative;
  flex-shrink: 0;
}

.ac__head-ban-dot {
  position: absolute;
  bottom: -1px;
  right: -1px;
  width: 14px;
  height: 14px;
  background: #ef4444;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  border: 1.5px solid #fff;
}

.ac__head-name {
  font-size: 12px;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  line-height: 1.3;
  max-width: 80px;
}

.ac__head-name--a { color: #3b82f6; }
.ac__head-name--b { color: #14b8a6; }

.ac__head-sep {
  color: #cbd5e1;
  font-size: 14px;
  flex-shrink: 0;
}

/* ban button — desktop shows text, mobile shows icon */
.ac__ban-btn-icon {
  display: none;
  font-size: 12px;
}

/* ── Detail body ── */
.ac__detail-body {
  flex: 1;
  padding: 20px 24px 8px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow-y: auto;
}

.ac__detail-spacer {
  height: 16px;
}

/* ── Ban button (header) ── */
.ac__ban-btn {
  padding: 3px 10px;
  font-size: 10px;
  font-weight: 500;
  border: 1px solid #e2e8f0;
  border-radius: var(--radius-full);
  cursor: pointer;
  transition: all 200ms var(--ease);
  background: #fff;
  color: #64748b;
  font-family: var(--font-sans);
  white-space: nowrap;
  flex-shrink: 0;
}

.ac__ban-btn:hover {
  background: #f8fafc;
}

.ac__ban-btn--active {
  background: #fef2f2;
  color: #dc2626;
  border-color: #fecaca;
}

.ac__ban-btn--active:hover {
  background: #fee2e2;
}

/* ── Task card ── */
.ac__task-card {
  display: flex;
  align-items: stretch;
  background: #fff;
  border: 1px solid rgba(226, 232, 240, 0.6);
  border-radius: var(--radius-2xl);
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03);
  cursor: pointer;
  transition: box-shadow 200ms var(--ease), border-color 200ms var(--ease);
}

.ac__task-card:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  border-color: rgba(59, 130, 246, 0.3);
}

.ac__task-icon {
  width: 56px;
  min-height: 56px;
  background: #f1f5f9;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: var(--c-accent);
  font-size: 20px;
}

.ac__task-body {
  padding: 10px 16px;
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  min-width: 0;
}

.ac__task-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

.ac__task-title {
  margin: 0;
  font-size: 13px;
  font-weight: 600;
  color: var(--c-text);
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ac__task-status {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: var(--radius-md);
  white-space: nowrap;
  font-weight: 500;
  flex-shrink: 0;
}

.ts-open { background: #eff6ff; color: #3b82f6; }
.ts-active { background: #fffbeb; color: #d97706; }
.ts-done { background: #f0fdf4; color: #16a34a; }
.ts-canceled { background: #fef2f2; color: #dc2626; }

.ac__task-price {
  margin: 4px 0 0;
  font-size: 14px;
  font-weight: 700;
  color: var(--c-accent);
}

/* ── Messages ── */
.ac__no-msg {
  text-align: center;
  color: #94a3b8;
  font-size: 13px;
  padding: 32px 0;
}

.ac__messages {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.ac__msg {
  display: flex;
  flex-direction: column;
}

.ac__msg--left { align-items: flex-start; }
.ac__msg--right { align-items: flex-end; }

.ac__msg-row {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  max-width: 80%;
}

.ac__msg-ava {
  flex-shrink: 0;
  margin-bottom: 4px;
}

.ac__msg-ava :deep(img) {
  border: 1px solid #e2e8f0;
}

.ac__msg-body {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.ac__msg-meta {
  font-size: 11px;
  margin-bottom: 4px;
  padding: 0 4px;
  font-weight: 500;
}

.ac__msg-meta--a { color: #3b82f6; }
.ac__msg-meta--b { color: #14b8a6; }
.ac__msg-meta--right { text-align: right; }

.ac__msg-time {
  color: #94a3b8;
  font-weight: 400;
  margin-left: 6px;
}

.ac__bubble {
  padding: 10px 16px;
  border-radius: 16px;
  font-size: 13px;
  line-height: 1.6;
  word-break: break-word;
}

.ac__bubble--left {
  background: #fff;
  color: var(--c-text);
  border: 1px solid rgba(226, 232, 240, 0.6);
  border-bottom-left-radius: 4px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03);
}

.ac__bubble--right {
  background: rgba(59, 130, 246, 0.06);
  color: var(--c-text);
  border: 1px solid rgba(59, 130, 246, 0.12);
  border-bottom-right-radius: 4px;
}

.ac__bubble--blocked { opacity: 0.5; }

.ac__msg-blocked {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 4px;
  font-size: 11px;
  color: #ef4444;
  padding: 0 4px;
}

/* ── Attachments ── */
.ac__atts {
  display: flex;
  gap: 8px;
  margin-top: 6px;
  flex-wrap: wrap;
}

.ac__att-item {
  width: 72px;
  height: 72px;
  flex-shrink: 0;
}

.ac__att-link {
  display: block;
  width: 100%;
  height: 100%;
  border-radius: 10px;
  overflow: hidden;
  border: 1.5px solid #cbd5e1;
  transition: box-shadow 150ms var(--ease), transform 150ms var(--ease);
}

.ac__att-link:hover {
  box-shadow: var(--shadow-md);
  transform: scale(1.04);
}

.ac__att-thumb {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.ac__att-file {
  width: 100%;
  height: 100%;
  background: #f8fafc;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  color: #94a3b8;
}

.ac__att-ext {
  font-size: 9px;
  font-weight: 700;
  color: #94a3b8;
  max-width: 56px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ac__att-deleted {
  opacity: 0.5;
  cursor: default;
}

/* ── Empty state ── */
.ac__empty-detail {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #94a3b8;
  background: rgba(248, 250, 252, 0.5);
}

.ac__empty-circle {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: #f1f5f9;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 20px;
}

.ac__empty-circle i {
  font-size: 32px;
  color: #cbd5e1;
}

.ac__empty-detail h3 {
  font-size: 16px;
  font-weight: 600;
  color: #64748b;
  margin: 0 0 8px;
}

.ac__empty-detail p {
  font-size: 13px;
  color: #94a3b8;
  max-width: 320px;
  text-align: center;
  margin: 0;
}

/* ── Rich text ── */
.ac__bubble :deep(.rich-text) p {
  margin-top: 0.25em;
  margin-bottom: 0.25em;
}
.ac__bubble :deep(.rich-text) p:first-child { margin-top: 0; }
.ac__bubble :deep(.rich-text) p:last-child { margin-bottom: 0; }

.ac__bubble :deep(.rich-text) ul,
.ac__bubble :deep(.rich-text) ol {
  padding-left: 1.5em;
  margin: 0.25em 0;
}

.ac__bubble :deep(.rich-text) ul { list-style-type: disc; }
.ac__bubble :deep(.rich-text) ol { list-style-type: decimal; }
.ac__bubble :deep(.rich-text) li { margin: 0.1em 0; }

.ac__bubble :deep(.rich-text) blockquote {
  border-left: 3px solid var(--c-accent);
  margin: 0.4em 0;
  padding: 0.3em 0.8em;
  background: rgba(0, 0, 0, 0.03);
  border-radius: 0 6px 6px 0;
  color: var(--c-text-secondary);
}

.ac__bubble :deep(.rich-text) pre {
  position: relative;
  background: #f3f4f6;
  color: #1f2937;
  padding: 12px 14px;
  padding-top: 34px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 0.4em 0;
  font-size: 0.85em;
  line-height: 1.5;
  border: 1px solid #e5e7eb;
}

.ac__bubble :deep(.rich-text) pre code {
  font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
  background: transparent;
  padding: 0;
  color: inherit;
}

.ac__bubble :deep(.code-copy-btn) {
  position: absolute;
  top: 7px;
  right: 8px;
  padding: 4px 6px;
  border: none;
  border-radius: 5px;
  background: transparent;
  color: #6b7280;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.15s, color 0.15s;
  line-height: 0;
}

.ac__bubble :deep(.code-copy-btn:hover) {
  background: #e5e7eb;
  color: #111827;
}

.ac__bubble :deep(.code-copy-btn .icon-check) {
  display: none;
}

.ac__bubble :deep(.code-copy-btn.copied .icon-copy) {
  display: none;
}

.ac__bubble :deep(.code-copy-btn.copied .icon-check) {
  display: flex;
  color: #16a34a;
}

.ac__bubble :deep(.code-lang) {
  position: absolute;
  top: 8px;
  left: 12px;
  font-size: 11px;
  font-weight: 600;
  color: #9ca3af;
  font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
  text-transform: lowercase;
  letter-spacing: 0.04em;
}

.ac__bubble :deep(.rich-text) code {
  font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
  background: rgba(0, 0, 0, 0.06);
  padding: 1px 5px;
  border-radius: 4px;
  font-size: 0.85em;
}

.ac__bubble :deep(.rich-text) img {
  width: 25vw;
  min-width: 150px;
  max-width: 100%;
  height: auto;
  border-radius: 8px;
  display: block;
  margin: 0 auto;
  box-shadow: var(--shadow-xs);
}

.ac__bubble :deep(.rich-text) a {
  color: var(--c-accent);
  text-decoration: underline;
}

/* ── Responsive ── */
@media (max-width: 768px) {
  .ac {
    flex-direction: column;
    align-items: stretch;
    height: auto;
    min-height: unset;
  }

  .ac__list-panel {
    position: static;
    width: 100%;
    height: auto;
    border-right: none;
    border-bottom: 1px solid rgba(226, 232, 240, 0.6);
  }

  .ac__list-panel--hidden-mobile {
    display: none;
  }

  .ac__detail-panel {
    display: none;
    position: fixed;
    top: 60px;
    left: 0;
    right: 0;
    bottom: 0;
    height: calc(100vh - 60px);
    height: calc(100dvh - 60px);
    z-index: 50;
  }

  .ac__detail-panel--show-mobile {
    display: flex;
  }

  .ac__back-btn {
    display: inline-flex;
  }

  .ac__detail-head {
    padding: 10px 14px;
  }

  .ac__detail-body {
    padding: 16px;
  }

  /* Mobile: avatar+name col on left, icon ban button on right */
  .ac__head-user {
    flex-direction: row;
    align-items: center;
    gap: 4px;
  }

  .ac__head-name {
    font-size: 10px;
    max-width: 52px;
  }

  .ac__ban-btn {
    padding: 5px;
    border-radius: 50%;
    border: none;
    width: 24px;
    height: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }

  .ac__ban-btn-text {
    display: none;
  }

  .ac__ban-btn-icon {
    display: inline;
    font-size: 10px;
  }

  .ac__head-sep {
    font-size: 11px;
  }

  .ac__detail-head-center {
    gap: 6px;
  }

  .ac__msg-row {
    max-width: 95%;
  }

  .ac__empty-detail {
    min-height: 60vh;
  }
}

@media (min-width: 769px) and (max-width: 1100px) {
  .ac__list-panel {
    width: 280px;
  }
}
</style>
