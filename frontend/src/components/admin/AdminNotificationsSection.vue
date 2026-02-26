<script setup lang="ts">
import { computed, proxyRefs, ref } from "vue";
import {
  AlertTriangle,
  Ban,
  Bell,
  CheckCircle,
  Clock,
  Eye,
  Info,
  Megaphone,
  Search,
  Send,
  Star,
  Trash2,
  User,
  Users,
  X,
} from "lucide-vue-next";
import maleAvatar from "../../assets/avatars/default-male.svg";
import femaleAvatar from "../../assets/avatars/default-female.svg";
import ChatRichTextRenderer from "../chat/ChatRichTextRenderer.vue";

import type { AdminNotificationsModel } from "../../composables/admin/useAdminNotifications";
import type { AdminUserItem } from "../../types/api";
import { parseUTC } from "../../utils/time";

const props = defineProps<{
  model: AdminNotificationsModel;
}>();

const vm = proxyRefs(props.model);
const richEditorRef = ref<HTMLTextAreaElement | null>(null);

const pushKindOptions = [
  { id: "notification" as const, label: "通知推送", icon: Bell },
  { id: "announcement" as const, label: "公告推送", icon: Megaphone },
];

const targetOptions = [
  { id: "all" as const, label: "全体用户", icon: Users },
  { id: "active" as const, label: "近3天活跃", icon: Clock },
  { id: "banned" as const, label: "受限用户", icon: Ban },
  { id: "custom" as const, label: "指定用户", icon: User },
];

const dismissOptions = [
  {
    id: "read" as const,
    label: "常规通知 (阅后即焚)",
    desc: "用户阅读后自动消失",
  },
  {
    id: "persistent" as const,
    label: "强制置顶 (需手动撤下)",
    desc: "用户端无法删除，需在已发送列表中管理",
  },
];

const iconOptions = [
  {
    type: "admin_notice",
    icon: Bell,
    label: "默认通知",
    color: "#3b82f6",
    bg: "rgba(59,130,246,0.08)",
    border: "rgba(59,130,246,0.3)",
  },
  {
    type: "admin_warning",
    icon: AlertTriangle,
    label: "警告",
    color: "#f59e0b",
    bg: "rgba(245,158,11,0.08)",
    border: "rgba(245,158,11,0.3)",
  },
  {
    type: "admin_success",
    icon: CheckCircle,
    label: "成功",
    color: "#22c55e",
    bg: "rgba(34,197,94,0.08)",
    border: "rgba(34,197,94,0.3)",
  },
  {
    type: "admin_info",
    icon: Info,
    label: "信息",
    color: "#06b6d4",
    bg: "rgba(6,182,212,0.08)",
    border: "rgba(6,182,212,0.3)",
  },
];

const iconMap: Record<string, any> = {
  admin_notice: Bell,
  admin_warning: AlertTriangle,
  admin_success: CheckCircle,
  admin_info: Info,
  admin_announcement: Megaphone,
};

function getIconForType(type: string) {
  return iconMap[type] || Bell;
}

const pushKindActiveIndex = computed(() =>
  pushKindOptions.findIndex((o) => o.id === vm.pushKind),
);
const dismissActiveIndex = computed(() =>
  dismissOptions.findIndex((o) => o.id === vm.dismissType),
);
const isAnnouncementMode = computed(() => vm.pushKind === "announcement");
const titleLabel = computed(() =>
  isAnnouncementMode.value ? "公告标题" : "通知标题",
);
const titlePlaceholder = computed(() =>
  isAnnouncementMode.value ? "输入公告标题..." : "输入简明扼要的标题...",
);
const descriptionLabel = computed(() =>
  isAnnouncementMode.value ? "公告正文" : "通知详情",
);
const descriptionPlaceholder = computed(() =>
  isAnnouncementMode.value
    ? "支持 Markdown：如 **加粗**、- 列表、[链接](https://...)"
    : "详细说明通知内容...",
);

const canSend = computed(() => {
  if (!vm.title.trim()) return false;
  if (isAnnouncementMode.value && !vm.description.trim()) return false;
  if (vm.targetMode === "custom" && vm.selectedUsers.length === 0) return false;
  return true;
});

const targetLabel = computed(() => {
  const opt = targetOptions.find((o) => o.id === vm.targetMode);
  return opt?.label || "";
});

function formatSentAt(iso: string): string {
  const d = parseUTC(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function onSelectUser(user: AdminUserItem) {
  vm.addUser(user);
}

function setPushKind(kind: "notification" | "announcement") {
  vm.setPushKind(kind);
}

function insertAround(prefix: string, suffix = "", placeholder = "文本") {
  const el = richEditorRef.value;
  const start = el?.selectionStart ?? vm.description.length;
  const end = el?.selectionEnd ?? vm.description.length;
  const selected = vm.description.slice(start, end) || placeholder;
  vm.description = `${vm.description.slice(0, start)}${prefix}${selected}${suffix}${vm.description.slice(end)}`;
  requestAnimationFrame(() => {
    if (!el) return;
    const cursor = start + prefix.length + selected.length + suffix.length;
    el.focus();
    el.setSelectionRange(cursor, cursor);
  });
}

function insertLine(prefix: string, placeholder = "内容") {
  const el = richEditorRef.value;
  const start = el?.selectionStart ?? vm.description.length;
  const end = el?.selectionEnd ?? vm.description.length;
  const selected = vm.description.slice(start, end) || placeholder;
  const lead = start > 0 && vm.description[start - 1] !== "\n" ? "\n" : "";
  const next = `${lead}${prefix}${selected}\n`;
  vm.description = `${vm.description.slice(0, start)}${next}${vm.description.slice(end)}`;
  requestAnimationFrame(() => {
    if (!el) return;
    const cursor = start + next.length;
    el.focus();
    el.setSelectionRange(cursor, cursor);
  });
}
</script>

<template>
  <section class="an">
    <div class="an__grid">
      <!-- Left: Push Form -->
      <div class="an__form-wrap">
        <form class="an__card" @submit.prevent="vm.send">
          <div class="an__card-head">
            <h2>新建推送</h2>
            <p>创建并向站内用户发送通知或公告</p>
          </div>

          <div class="an__card-body">
            <!-- 1. Push kind -->
            <div class="an__section">
              <label class="an__label"
                >推送类型 <span class="an__required">*</span></label
              >
              <div class="an__toggle-group an__toggle-group--kind">
                <span
                  class="an__toggle-indicator"
                  :style="{
                    transform: `translateX(${pushKindActiveIndex * 100}%)`,
                  }"
                />
                <button
                  v-for="opt in pushKindOptions"
                  :key="opt.id"
                  type="button"
                  class="an__toggle-btn an__toggle-btn--kind"
                  :class="{ 'an__toggle-btn--active': vm.pushKind === opt.id }"
                  @click="setPushKind(opt.id)"
                >
                  <component :is="opt.icon" :size="15" :stroke-width="1.8" />
                  <span>{{ opt.label }}</span>
                </button>
              </div>
              <p class="an__hint an__hint--inline">
                <template v-if="isAnnouncementMode">
                  公告会以弹窗形式触达用户，支持富文本正文。
                </template>
                <template v-else>
                  通知用于常规运营触达，支持多种图标样式。
                </template>
              </p>
            </div>

            <!-- 2. Target -->
            <div class="an__section">
              <label class="an__label"
                >推送目标 <span class="an__required">*</span></label
              >
              <div class="an__target-grid">
                <div
                  v-for="opt in targetOptions"
                  :key="opt.id"
                  class="an__target-card"
                  :class="{
                    'an__target-card--active': vm.targetMode === opt.id,
                  }"
                  @click="vm.targetMode = opt.id"
                >
                  <component
                    :is="opt.icon"
                    :size="20"
                    :stroke-width="1.5"
                    class="an__target-icon"
                  />
                  <span class="an__target-label">{{ opt.label }}</span>
                  <span
                    v-if="vm.targetMode === opt.id"
                    class="an__target-check"
                  >
                    <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                      <path
                        d="M3 7L6 10L11 4"
                        stroke="currentColor"
                        stroke-width="2"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                      />
                    </svg>
                  </span>
                </div>
              </div>

              <!-- User search for custom mode -->
              <div v-if="vm.targetMode === 'custom'" class="an__user-search">
                <div class="an__search-box">
                  <Search :size="16" class="an__search-icon" />
                  <input
                    v-model="vm.userSearchQuery"
                    class="an__search-input"
                    placeholder="搜索用户昵称、姓名或账号..."
                  />
                  <div v-if="vm.searching" class="an__search-spinner" />

                  <!-- Search results dropdown (inside search-box for correct overlay positioning) -->
                  <Transition name="an__search-anim">
                    <div
                      v-if="vm.userSearchResults.length > 0"
                      class="an__search-results"
                    >
                      <div
                        v-for="user in vm.userSearchResults"
                        :key="user.id"
                        class="an__search-item"
                        @click="onSelectUser(user)"
                      >
                        <div class="an__search-item-avatar">
                          <img
                            :src="
                              user.avatar_url ??
                              (user.gender === 'female'
                                ? femaleAvatar
                                : maleAvatar)
                            "
                            alt=""
                          />
                        </div>
                        <div class="an__search-item-info">
                          <span class="an__search-item-name">{{
                            user.display_name
                          }}</span>
                          <span class="an__search-item-account"
                            >@{{ user.account }}</span
                          >
                        </div>
                      </div>
                    </div>
                  </Transition>
                </div>

                <!-- Selected user tags -->
                <div v-if="vm.selectedUsers.length > 0" class="an__user-tags">
                  <span
                    v-for="user in vm.selectedUsers"
                    :key="user.id"
                    class="an__user-tag"
                  >
                    {{ vm.formatUserLabel(user) }}
                    <button
                      type="button"
                      class="an__user-tag-close"
                      @click="vm.removeUser(user.id)"
                    >
                      <X :size="12" />
                    </button>
                  </span>
                </div>
              </div>
            </div>

            <!-- 3. Content -->
            <div class="an__section an__section--gap">
              <label class="an__label" for="an-title"
                >{{ titleLabel }} <span class="an__required">*</span></label
              >
              <input
                id="an-title"
                v-model="vm.title"
                class="form-input"
                maxlength="200"
                :placeholder="titlePlaceholder"
              />

              <label class="an__label" for="an-desc">{{
                descriptionLabel
              }}</label>

              <Transition name="an__mode-fade" mode="out-in">
                <div
                  v-if="isAnnouncementMode"
                  key="announce-editor"
                  class="an__rich-wrap"
                >
                  <div class="an__rich-toolbar">
                    <button
                      type="button"
                      class="an__rich-tool"
                      @click="insertAround('**', '**', '加粗文本')"
                    >
                      <strong>B</strong>
                    </button>
                    <button
                      type="button"
                      class="an__rich-tool an__rich-tool--italic"
                      @click="insertAround('*', '*', '斜体文本')"
                    >
                      I
                    </button>
                    <button
                      type="button"
                      class="an__rich-tool"
                      @click="insertLine('## ', '二级标题')"
                    >
                      H2
                    </button>
                    <button
                      type="button"
                      class="an__rich-tool"
                      @click="insertLine('- ', '列表项')"
                    >
                      • 列表
                    </button>
                    <button
                      type="button"
                      class="an__rich-tool"
                      @click="
                        insertAround('[', '](https://example.com)', '链接标题')
                      "
                    >
                      链接
                    </button>
                    <button
                      type="button"
                      class="an__rich-tool"
                      @click="insertLine('> ', '引用内容')"
                    >
                      引用
                    </button>
                  </div>
                  <textarea
                    id="an-desc"
                    ref="richEditorRef"
                    v-model="vm.description"
                    class="form-textarea an__rich-textarea"
                    maxlength="2000"
                    :placeholder="descriptionPlaceholder"
                    rows="8"
                  />
                  <div class="an__preview">
                    <div class="an__preview-head">
                      <Eye :size="14" />
                      <span>实时预览</span>
                    </div>
                    <div class="an__preview-body">
                      <ChatRichTextRenderer
                        :content="
                          vm.description ||
                          '在上方输入公告正文后，这里会实时显示效果。'
                        "
                      />
                    </div>
                  </div>
                </div>
                <textarea
                  v-else
                  id="an-desc"
                  key="notice-editor"
                  v-model="vm.description"
                  class="form-textarea"
                  maxlength="2000"
                  :placeholder="descriptionPlaceholder"
                  rows="4"
                />
              </Transition>
            </div>

            <!-- 4. Dismiss type + Icon selection -->
            <div class="an__row">
              <div class="an__section">
                <div class="an__label-row">
                  <label class="an__label">{{
                    isAnnouncementMode ? "公告展示类型" : "通知展示类型"
                  }}</label>
                  <Transition name="an__hint-anim">
                    <p
                      v-if="vm.dismissType === 'persistent'"
                      class="an__hint an__hint--warning an__hint--inline"
                    >
                      <Info :size="12" />
                      置顶消息需管理员手动删除
                    </p>
                  </Transition>
                </div>
                <div class="an__toggle-group">
                  <span
                    class="an__toggle-indicator"
                    :style="{
                      transform: `translateX(${dismissActiveIndex * 100}%)`,
                    }"
                  />
                  <button
                    v-for="opt in dismissOptions"
                    :key="opt.id"
                    type="button"
                    class="an__toggle-btn"
                    :class="{
                      'an__toggle-btn--active': vm.dismissType === opt.id,
                    }"
                    @click="vm.dismissType = opt.id"
                  >
                    {{ opt.label }}
                  </button>
                </div>
              </div>

              <div class="an__section">
                <label class="an__label">{{
                  isAnnouncementMode ? "公告图标" : "显示图标"
                }}</label>
                <div v-if="isAnnouncementMode" class="an__announcement-icon">
                  <div class="an__announcement-icon__badge">
                    <Megaphone :size="20" :stroke-width="1.6" />
                  </div>
                  <div>
                    <p class="an__announcement-icon__title">
                      公告固定使用喇叭图标
                    </p>
                    <p class="an__announcement-icon__desc">
                      用户点击置顶公告可再次弹出公告弹窗
                    </p>
                  </div>
                </div>
                <div v-else class="an__icon-grid">
                  <button
                    v-for="opt in iconOptions"
                    :key="opt.type"
                    type="button"
                    class="an__icon-btn"
                    :class="{
                      'an__icon-btn--active': vm.notificationType === opt.type,
                    }"
                    :style="
                      vm.notificationType === opt.type
                        ? {
                            color: opt.color,
                            background: opt.bg,
                            borderColor: opt.border,
                            boxShadow: `0 0 0 1px ${opt.border}`,
                          }
                        : { color: opt.color }
                    "
                    :title="opt.label"
                    @click="vm.notificationType = opt.type"
                  >
                    <component :is="opt.icon" :size="20" :stroke-width="1.5" />
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- Footer -->
          <div class="an__card-foot">
            <span class="an__foot-info">
              即将发送给：<strong>{{ targetLabel }}</strong>
              <template
                v-if="vm.targetMode === 'custom' && vm.selectedUsers.length > 0"
              >
                （{{ vm.selectedUsers.length }} 人）
              </template>
            </span>
            <button
              type="submit"
              class="btn btn-primary an__send-btn"
              :disabled="vm.sending || !canSend"
            >
              <div v-if="vm.sending" class="an__spinner" />
              <Send v-else :size="16" />
              {{
                vm.sending
                  ? "发送中..."
                  : isAnnouncementMode
                    ? "立即推送公告"
                    : "立即推送通知"
              }}
            </button>
          </div>
        </form>
      </div>

      <!-- Right: Sent Notifications -->
      <div class="an__sent-wrap">
        <div class="an__card an__sent-card">
          <div class="an__sent-head">
            <div class="an__sent-title-row">
              <Star :size="16" class="an__sent-star" />
              <h2>已发送通知公告</h2>
            </div>
            <span class="an__sent-count">{{
              vm.sentNotifications.length
            }}</span>
          </div>

          <div class="an__sent-body">
            <div v-if="vm.loadingSent" class="an__sent-empty">
              <div class="an__spinner" />
              <p>加载中...</p>
            </div>

            <div
              v-else-if="vm.sentNotifications.length === 0"
              class="an__sent-empty"
            >
              <Bell :size="32" class="an__sent-empty-icon" />
              <p>暂无已发送的通知公告</p>
            </div>

            <div
              v-else
              v-for="msg in vm.sentNotifications"
              :key="msg.title + msg.type"
              class="an__sent-item"
            >
              <div class="an__sent-item-top">
                <div class="an__sent-item-left">
                  <div class="an__sent-item-icon">
                    <component
                      :is="getIconForType(msg.type)"
                      :size="16"
                      :stroke-width="1.5"
                    />
                  </div>
                  <div class="an__sent-item-info">
                    <h3>{{ msg.title }}</h3>
                    <p class="an__sent-item-meta">
                      {{
                        msg.dismiss_type === "persistent" ? "置顶" : "常规"
                      }}
                      · {{ formatSentAt(msg.sent_at) }}
                    </p>
                  </div>
                </div>
                <button
                  class="an__sent-delete"
                  :disabled="vm.deletingTitle === msg.title"
                  title="删除该批次通知"
                  @click="vm.deleteSentNotification(msg)"
                >
                  <Trash2 :size="14" />
                </button>
              </div>

              <div class="an__sent-item-stats">
                <div class="an__stat-row">
                  <span class="an__stat-label">
                    <Eye :size="14" /> 已读情况
                  </span>
                  <span class="an__stat-value">
                    {{ msg.read_count }} / {{ msg.remaining_count }}
                  </span>
                </div>
                <div class="an__stat-bar">
                  <div
                    class="an__stat-bar-fill"
                    :style="{
                      width:
                        msg.remaining_count > 0
                          ? `${Math.round((msg.read_count / msg.remaining_count) * 100)}%`
                          : '0%',
                    }"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.an__grid {
  display: grid;
  grid-template-columns: 1fr 380px;
  gap: 24px;
  align-items: start;
}

/* ── Card ── */
.an__card {
  border: 1px solid rgba(226, 232, 240, 0.6);
  border-radius: var(--radius-2xl);
  background: rgba(255, 255, 255, 0.8);
  box-shadow: var(--shadow-card);
  overflow: hidden;
}

.an__card-head {
  padding: 20px 24px;
  border-bottom: 1px solid var(--c-border-light);
  background: rgba(248, 250, 252, 0.5);
}

.an__card-head h2 {
  font-size: var(--text-lg);
  font-weight: 600;
  margin: 0;
}

.an__card-head p {
  font-size: var(--text-sm);
  color: var(--c-text-muted);
  margin: 4px 0 0;
}

.an__card-body {
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 28px;
}

.an__card-foot {
  padding: 16px 24px;
  border-top: 1px solid var(--c-border-light);
  background: rgba(248, 250, 252, 0.5);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

/* ── Section ── */
.an__section {
  display: flex;
  flex-direction: column;
}

.an__section--gap {
  gap: 12px;
}

.an__label {
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--c-text-secondary);
  margin-bottom: 10px;
}

.an__required {
  color: var(--c-danger);
}

/* ── Mode Switch ── */
.an__toggle-group--kind {
  max-width: 340px;
}

.an__toggle-btn--kind {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

/* ── Target Cards ── */
.an__target-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
}

.an__target-card {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 16px 8px;
  border-radius: var(--radius-md);
  border: 1px solid var(--c-border);
  background: var(--c-surface);
  cursor: pointer;
  transition: all 200ms var(--ease);
  user-select: none;
}

.an__target-card:hover {
  border-color: #cbd5e1;
  background: #f8fafc;
}

.an__target-card--active {
  background: var(--c-accent-light);
  border-color: var(--c-accent-soft);
  box-shadow: 0 0 0 1px var(--c-accent);
}

.an__target-card--active:hover {
  background: var(--c-accent-light);
  border-color: var(--c-accent);
}

.an__target-icon {
  color: var(--c-text-muted);
  margin-bottom: 8px;
}

.an__target-card--active .an__target-icon {
  color: var(--c-accent);
}

.an__target-label {
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--c-text-secondary);
}

.an__target-card--active .an__target-label {
  color: var(--c-accent);
}

.an__target-check {
  position: absolute;
  top: 6px;
  right: 6px;
  color: var(--c-accent);
}

/* ── User Search ── */
.an__user-search {
  margin-top: 12px;
}

.an__search-box {
  position: relative;
  display: flex;
  align-items: center;
}

.an__search-icon {
  position: absolute;
  left: 12px;
  color: var(--c-text-muted);
  pointer-events: none;
}

.an__search-input {
  width: 100%;
  padding: 10px 12px 10px 36px;
  border: 1px solid var(--c-border);
  border-radius: var(--radius-md);
  font-size: var(--text-base);
  background: #f8fafc;
  transition:
    border-color 200ms var(--ease),
    background 200ms var(--ease),
    box-shadow 200ms var(--ease);
}

.an__search-input:focus {
  background: var(--c-surface);
  border-color: var(--c-accent);
  box-shadow: 0 0 0 3px var(--c-accent-soft);
}

.an__search-spinner {
  position: absolute;
  right: 12px;
  width: 16px;
  height: 16px;
  border: 2px solid var(--c-border);
  border-top-color: var(--c-accent);
  border-radius: 50%;
  animation: an-spin 0.6s linear infinite;
}

.an__search-results {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  right: 0;
  background: var(--c-surface);
  border: 1px solid var(--c-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-xl);
  z-index: 50;
  max-height: 240px;
  overflow-y: auto;
  padding: 4px;
  transform-origin: top center;
}

.an__search-anim-enter-active {
  transition:
    opacity 200ms var(--ease),
    transform 200ms var(--ease);
}

.an__search-anim-leave-active {
  transition:
    opacity 150ms var(--ease),
    transform 150ms var(--ease);
}

.an__search-anim-enter-from {
  opacity: 0;
  transform: scaleY(0.88) translateY(-6px);
}

.an__search-anim-leave-to {
  opacity: 0;
  transform: scaleY(0.94) translateY(-3px);
}

.an__search-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background 150ms var(--ease);
}

.an__search-item:hover {
  background: var(--c-accent-light);
}

.an__search-item-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--c-border-light);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  flex-shrink: 0;
  color: var(--c-text-muted);
}

.an__search-item-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.an__search-item-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.an__search-item-name {
  font-size: var(--text-base);
  font-weight: 500;
  color: var(--c-text);
}

.an__search-item-account {
  font-size: var(--text-xs);
  color: var(--c-text-muted);
}

/* ── User Tags ── */
.an__user-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 10px;
}

.an__user-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px 4px 10px;
  background: var(--c-accent-light);
  color: var(--c-accent);
  border: 1px solid var(--c-accent-soft);
  border-radius: var(--radius-full);
  font-size: var(--text-sm);
  font-weight: 500;
}

.an__user-tag-close {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  border: none;
  background: none;
  color: var(--c-accent);
  border-radius: 50%;
  padding: 0;
  transition:
    background 150ms var(--ease),
    color 150ms var(--ease);
}

.an__user-tag-close:hover {
  background: var(--c-accent-soft);
  color: var(--c-accent-hover);
}

/* ── Rich Text ── */
.an__mode-fade-enter-active,
.an__mode-fade-leave-active {
  transition:
    opacity 220ms var(--ease),
    transform 220ms var(--ease);
}

.an__mode-fade-enter-from,
.an__mode-fade-leave-to {
  opacity: 0;
  transform: translateY(6px);
}

.an__rich-wrap {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.an__rich-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 8px;
  border: 1px solid var(--c-border);
  border-radius: var(--radius-md);
  background: #f8fafc;
}

.an__rich-tool {
  border: 1px solid var(--c-border);
  background: #fff;
  color: var(--c-text-secondary);
  border-radius: 8px;
  font-size: 12px;
  font-weight: 600;
  min-width: 36px;
  height: 30px;
  padding: 0 10px;
  transition: all 180ms var(--ease);
}

.an__rich-tool--italic {
  font-style: italic;
}

.an__rich-tool:hover {
  border-color: var(--c-accent-soft);
  color: var(--c-accent);
  background: #eff6ff;
}

.an__rich-textarea {
  min-height: 150px;
  font-family:
    "JetBrains Mono", "Fira Code", ui-monospace, SFMono-Regular, Menlo,
    Consolas, monospace;
  line-height: 1.6;
}

.an__preview {
  border: 1px solid var(--c-border);
  border-radius: var(--radius-md);
  overflow: hidden;
  background: #fff;
}

.an__preview-head {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  font-size: var(--text-xs);
  font-weight: 600;
  color: var(--c-text-secondary);
  background: #f8fafc;
  border-bottom: 1px solid var(--c-border-light);
}

.an__preview-body {
  max-height: 260px;
  overflow: auto;
  padding: 12px 14px;
}

.an__preview-body :deep(.rich-text) {
  font-size: 13px;
  line-height: 1.65;
  color: var(--c-text);
}

.an__preview-body :deep(.rich-text p) {
  margin: 0 0 8px;
}

.an__preview-body :deep(.rich-text p:last-child) {
  margin-bottom: 0;
}

.an__preview-body :deep(.rich-text ul),
.an__preview-body :deep(.rich-text ol) {
  margin: 8px 0;
  padding-left: 18px;
}

.an__preview-body :deep(.rich-text blockquote) {
  margin: 8px 0;
  padding: 6px 10px;
  border-left: 3px solid #8b5cf6;
  background: rgba(139, 92, 246, 0.07);
}

.an__preview-body :deep(.rich-text pre) {
  margin: 8px 0;
  border-radius: 10px;
}

.an__preview-body :deep(.rich-text code) {
  font-family:
    "JetBrains Mono", "Fira Code", ui-monospace, SFMono-Regular, Menlo,
    Consolas, monospace;
}

.an__preview-body :deep(.rich-text img) {
  display: block;
  width: 40%;
  max-width: 40%;
  height: auto;
  margin: 10px auto;
  border-radius: 10px;
}

/* ── Announcement icon card ── */
.an__announcement-icon {
  display: flex;
  align-items: center;
  gap: 10px;
  border: 1px solid rgba(139, 92, 246, 0.3);
  background: rgba(139, 92, 246, 0.08);
  border-radius: var(--radius-md);
  padding: 12px;
}

.an__announcement-icon__badge {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: rgba(139, 92, 246, 0.2);
  color: #7c3aed;
  display: grid;
  place-items: center;
  flex-shrink: 0;
}

.an__announcement-icon__title {
  margin: 0;
  font-size: var(--text-sm);
  font-weight: 600;
  color: #6d28d9;
}

.an__announcement-icon__desc {
  margin: 2px 0 0;
  font-size: var(--text-xs);
  color: #7c3aed;
}

/* ── Row layout ── */
.an__row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}

/* ── Label row ── */
.an__label-row {
  display: flex;
  align-items: baseline;
  gap: 10px;
  flex-wrap: wrap;
}

.an__label-row .an__label {
  flex-shrink: 0;
}

/* ── Toggle Group ── */
.an__toggle-group {
  display: flex;
  background: var(--c-border-light);
  padding: 3px;
  border-radius: var(--radius-md);
  position: relative;
}

.an__toggle-indicator {
  position: absolute;
  top: 3px;
  bottom: 3px;
  left: 3px;
  width: calc((100% - 6px) / 2);
  background: var(--c-surface);
  border-radius: var(--radius-sm);
  box-shadow: var(--shadow-sm);
  transition: transform 300ms var(--ease);
  pointer-events: none;
  z-index: 0;
}

.an__toggle-btn {
  flex: 1;
  padding: 8px 10px;
  font-size: var(--text-sm);
  font-weight: 500;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--c-text-muted);
  transition: color 200ms var(--ease);
  white-space: nowrap;
  position: relative;
  z-index: 1;
}

.an__toggle-btn--active {
  color: var(--c-text);
}

.an__hint {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 8px;
  font-size: var(--text-xs);
  color: var(--c-text-muted);
}

.an__hint--inline {
  margin-top: 0;
  margin-bottom: 10px;
}

.an__hint--warning {
  color: var(--c-warning);
}

.an__hint-anim-enter-active {
  transition:
    opacity 200ms var(--ease),
    transform 200ms var(--ease);
}

.an__hint-anim-leave-active {
  transition:
    opacity 150ms var(--ease),
    transform 150ms var(--ease);
}

.an__hint-anim-enter-from {
  opacity: 0;
  transform: translateX(-6px);
}

.an__hint-anim-leave-to {
  opacity: 0;
  transform: translateX(-4px);
}

/* ── Icon Grid ── */
.an__icon-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.an__icon-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--c-border);
  background: var(--c-surface);
  transition: all 200ms var(--ease);
}

.an__icon-btn:hover {
  border-color: #cbd5e1;
  background: #f8fafc;
  opacity: 0.85;
}

.an__icon-btn--active {
  box-shadow: 0 0 0 1px currentColor;
}

/* ── Footer ── */
.an__foot-info {
  font-size: var(--text-sm);
  color: var(--c-text-muted);
}

.an__foot-info strong {
  color: var(--c-text-secondary);
  font-weight: 600;
}

.an__send-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 24px;
  border-radius: var(--radius-md);
  font-weight: 500;
}

/* ── Spinner ── */
.an__spinner {
  width: 16px;
  height: 16px;
  border: 2px solid var(--c-border);
  border-top-color: var(--c-accent);
  border-radius: 50%;
  animation: an-spin 0.6s linear infinite;
}

.an__send-btn .an__spinner {
  border-color: rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
}

@keyframes an-spin {
  to {
    transform: rotate(360deg);
  }
}

/* ── Sent Panel ── */
.an__sent-wrap {
  position: sticky;
  top: 0;
}

.an__sent-card {
  max-height: calc(100vh - 200px);
  display: flex;
  flex-direction: column;
}

.an__sent-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--c-border-light);
  background: rgba(248, 250, 252, 0.5);
}

.an__sent-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.an__sent-title-row h2 {
  font-size: var(--text-base);
  font-weight: 600;
  margin: 0;
}

.an__sent-star {
  color: #f59e0b;
}

.an__sent-count {
  background: var(--c-border-light);
  color: var(--c-text-secondary);
  font-size: var(--text-xs);
  font-weight: 600;
  padding: 2px 8px;
  border-radius: var(--radius-full);
}

.an__sent-body {
  flex: 1;
  overflow-y: auto;
  overscroll-behavior: contain;
}

.an__sent-body::-webkit-scrollbar {
  width: 4px;
}

.an__sent-body::-webkit-scrollbar-thumb {
  background: #e2e8f0;
  border-radius: 4px;
}

.an__sent-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 24px;
  text-align: center;
  color: var(--c-text-muted);
  gap: 8px;
}

.an__sent-empty-icon {
  opacity: 0.2;
  margin-bottom: 4px;
}

.an__sent-empty p {
  font-size: var(--text-sm);
  margin: 0;
}

/* ── Sent Item ── */
.an__sent-item {
  padding: 16px 20px;
  border-bottom: 1px solid var(--c-border-light);
  transition: background 150ms var(--ease);
}

.an__sent-item:hover {
  background: rgba(248, 250, 252, 0.6);
}

.an__sent-item:last-child {
  border-bottom: none;
}

.an__sent-item-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
}

.an__sent-item-left {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  min-width: 0;
}

.an__sent-item-icon {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-sm);
  background: var(--c-border-light);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: var(--c-text-secondary);
}

.an__sent-item-info {
  min-width: 0;
}

.an__sent-item-info h3 {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--c-text);
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.an__sent-item-meta {
  font-size: var(--text-xs);
  color: var(--c-text-muted);
  margin: 2px 0 0;
}

.an__sent-delete {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  background: none;
  color: var(--c-text-muted);
  border-radius: var(--radius-sm);
  opacity: 0;
  transition: all 150ms var(--ease);
  flex-shrink: 0;
}

.an__sent-item:hover .an__sent-delete {
  opacity: 1;
}

.an__sent-delete:hover {
  color: var(--c-danger);
  background: var(--c-danger-light);
}

.an__sent-delete:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* ── Stats ── */
.an__sent-item-stats {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(226, 232, 240, 0.4);
}

.an__stat-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.an__stat-label {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: var(--text-xs);
  color: var(--c-text-muted);
}

.an__stat-value {
  font-size: var(--text-xs);
  font-weight: 600;
  color: var(--c-text-secondary);
}

.an__stat-bar {
  width: 100%;
  height: 4px;
  background: var(--c-border-light);
  border-radius: 2px;
  overflow: hidden;
}

.an__stat-bar-fill {
  height: 100%;
  background: var(--c-success);
  border-radius: 2px;
  transition: width 500ms var(--ease);
}

/* ── Responsive ── */
@media (max-width: 1200px) {
  .an__grid {
    grid-template-columns: 1fr;
  }

  .an__sent-wrap {
    position: static;
  }

  .an__sent-card {
    max-height: none;
  }
}

@media (max-width: 640px) {
  .an__target-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .an__row {
    grid-template-columns: 1fr;
  }

  .an__card-body {
    padding: 16px;
  }

  .an__card-foot {
    flex-direction: column;
    align-items: stretch;
    text-align: center;
  }

  .an__toggle-group--kind {
    max-width: none;
  }

  .an__rich-tool {
    flex: 1;
    min-width: 64px;
  }

  .an__preview-body {
    max-height: 220px;
  }
}
</style>
