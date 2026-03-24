<script setup lang="ts">
import { computed } from "vue";

import type { AgentMySessionItem } from "../../types/api";
import { formatChatTime } from "../../utils/time";
import { sessionStatusDot } from "./agentViewUtils";

const props = defineProps<{
  sessions: AgentMySessionItem[];
  loadingSessions: boolean;
  searchQuery: string;
  activeSessionId: string;
  isMobile: boolean;
  hasActiveSession: boolean;
}>();

const emit = defineEmits<{
  (e: "update:searchQuery", value: string): void;
  (e: "select-session", session: AgentMySessionItem): void;
}>();

const searchModel = computed({
  get: () => props.searchQuery,
  set: (value: string) => emit("update:searchQuery", value),
});
</script>

<template>
  <aside
    class="agent-sidebar"
    :class="{ 'sidebar-hidden': hasActiveSession && isMobile }"
  >
    <div class="sidebar-header">
      <h1 class="sidebar-title">代理任务</h1>
      <div class="sidebar-search">
        <i class="fa-solid fa-search search-icon"></i>
        <input
          v-model="searchModel"
          type="text"
          placeholder="搜索..."
          class="search-input"
        />
      </div>
    </div>
    <div class="session-list">
      <button
        v-for="s in sessions"
        :key="s.session_id"
        class="session-item"
        :class="{ active: s.session_id === activeSessionId }"
        @click="emit('select-session', s)"
      >
        <div class="session-item-top">
          <span class="session-item-title">{{ s.task_title }}</span>
          <span class="session-item-time">{{
            formatChatTime(s.last_activity_at)
          }}</span>
        </div>
        <div class="session-item-bottom">
          <span class="session-item-preview"
            >已用 {{ s.interaction_count }}/{{ s.max_interactions }}</span
          >
          <span
            v-if="sessionStatusDot(s) === 'running'"
            class="session-dot session-dot--running"
          ></span>
          <span
            v-else-if="sessionStatusDot(s) === 'queued'"
            class="session-dot session-dot--queued"
          ></span>
          <span
            v-else-if="sessionStatusDot(s) === 'done'"
            class="session-dot session-dot--done"
          ></span>
          <span
            v-else-if="sessionStatusDot(s) === 'error'"
            class="session-dot session-dot--error"
          ></span>
          <span
            v-else-if="sessionStatusDot(s) === 'canceled'"
            class="session-dot session-dot--canceled"
          ></span>
        </div>
      </button>

      <div v-if="loadingSessions" class="session-empty">
        <i class="fa-solid fa-spinner fa-spin"></i> 加载中...
      </div>
      <div v-else-if="sessions.length === 0" class="session-empty">
        <i class="fa-solid fa-robot session-empty-icon"></i>
        <p>暂无代理任务</p>
      </div>
    </div>
  </aside>
</template>

<style scoped>
@keyframes agent-rise {
  from {
    opacity: 0;
    transform: translateY(16px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.agent-sidebar {
  display: flex;
  flex-direction: column;
  width: 320px;
  background: var(--c-surface, #fff);
  border-right: 1px solid var(--c-border, #e2e8f0);
  flex-shrink: 0;
  z-index: 20;
  animation: agent-rise 0.48s cubic-bezier(0.22, 1, 0.36, 1) 0ms both;
}

.sidebar-header {
  padding: 10px 16px;
  border-bottom: 1px solid var(--c-border-light, #f1f5f9);
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.sidebar-title {
  font-size: var(--text-lg, 18px);
  font-weight: 700;
  white-space: nowrap;
  flex-shrink: 0;
  background: linear-gradient(135deg, var(--c-accent, #2563eb), #7c3aed);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.sidebar-search {
  flex: 1;
  min-width: 0;
  position: relative;
  display: flex;
  align-items: center;
}

.search-icon {
  position: absolute;
  left: 10px;
  color: var(--c-text-muted, #94a3b8);
  pointer-events: none;
  font-size: 12px;
}

.search-input {
  width: 100%;
  padding: 6px 12px 6px 30px;
  background: var(--c-bg, #f1f5f9);
  border: 1.5px solid var(--c-border, #e2e8f0);
  border-radius: 999px;
  font-size: var(--text-sm, 13px);
  color: var(--c-text, #1e293b);
  outline: none;
  transition:
    border-color 0.15s ease,
    box-shadow 0.15s ease;
}

.search-input::placeholder {
  color: var(--c-text-muted, #94a3b8);
}

.search-input:focus {
  border-color: var(--c-accent, #2563eb);
  box-shadow: 0 0 0 3px var(--c-accent-soft, rgba(37, 99, 235, 0.15));
}

.session-list {
  flex: 1;
  overflow-y: auto;
  padding: 4px 0;
}

.session-list::-webkit-scrollbar {
  width: 4px;
}

.session-list::-webkit-scrollbar-track {
  background: transparent;
}

.session-list::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 2px;
}

.session-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  width: calc(100% - 16px);
  margin: 2px 8px;
  padding: 10px 12px;
  border-radius: 12px;
  cursor: pointer;
  border: 1px solid transparent;
  background: transparent;
  text-align: left;
  transition:
    background 0.15s ease,
    border-color 0.15s ease;
}

.session-item:hover {
  background: var(--c-bg, #f1f5f9);
}

.session-item.active {
  background: var(--c-accent-light, #eff6ff);
  border-color: var(--c-accent-soft, rgba(37, 99, 235, 0.2));
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

.session-item-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

.session-item-title {
  font-size: var(--text-sm, 13px);
  font-weight: 600;
  color: var(--c-text, #1e293b);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
}

.session-item.active .session-item-title {
  color: #1e3a5f;
}

.session-item-time {
  font-size: var(--text-xs, 11px);
  color: var(--c-text-muted, #94a3b8);
  flex-shrink: 0;
}

.session-item-bottom {
  display: flex;
  align-items: center;
  gap: 6px;
}

.session-item-preview {
  font-size: var(--text-xs, 11px);
  color: var(--c-text-muted, #94a3b8);
  flex: 1;
}

.session-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.session-dot--running {
  background: #3b82f6;
  animation: dotPulse 1.5s ease-in-out infinite;
}

.session-dot--queued {
  background: #f59e0b;
  animation: dotPulse 1.5s ease-in-out infinite;
}

.session-dot--done {
  background: #22c55e;
}

.session-dot--error {
  background: #ef4444;
}

.session-dot--canceled {
  background: #94a3b8;
}

@keyframes dotPulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.4;
  }
}

.session-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 16px;
  color: var(--c-text-muted, #94a3b8);
  gap: 8px;
  font-size: 13px;
}

.session-empty-icon {
  font-size: 32px;
  opacity: 0.15;
}

.session-empty p {
  margin: 0;
}

@media (max-width: 768px) {
  .agent-sidebar {
    width: 100%;
  }

  .sidebar-hidden {
    display: none;
  }
}
</style>
