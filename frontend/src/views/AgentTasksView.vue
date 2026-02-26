<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import AppToast from '../components/AppToast.vue'
import HomeHeaderBar from '../components/home/HomeHeaderBar.vue'
import HomeTaskEditorModal from '../components/home/HomeTaskEditorModal.vue'
import { fetchMyAgentSessions } from '../api/agent'
import { useAppToast } from '../composables/useAppToast'
import { useQuickTaskPublish } from '../composables/useQuickTaskPublish'
import { useAuthStore } from '../stores/auth'
import type { AgentMySessionItem } from '../types/api'
import { extractError } from '../utils/error'
import { formatFull, nowLocal } from '../utils/time'

const router = useRouter()
const auth = useAuthStore()
const appTitle = import.meta.env.VITE_APP_TITLE || '校园任务平台'
const { toast, showToast, clearToast } = useAppToast()
const {
  showCreateModal,
  newTask,
  publishCategories,
  canCreateWithAgent,
  createWithAgentSubmitting,
  openPublishModal,
  submitPublishTask,
} = useQuickTaskPublish({ showToast })

const sessions = ref<AgentMySessionItem[]>([])
const loading = ref(true)
const total = ref(0)
const page = ref(1)
const pageSize = 20

const totalPages = computed(() => Math.ceil(total.value / pageSize))

async function loadSessions() {
  loading.value = true
  try {
    const result = await fetchMyAgentSessions({ page: page.value, page_size: pageSize })
    sessions.value = result.items
    total.value = result.total
  } catch (error) {
    showToast(extractError(error, '加载代理任务失败'), 'error')
  } finally {
    loading.value = false
  }
}

function goToSession(session: AgentMySessionItem) {
  router.push(`/agent/${session.session_id}`)
}

function taskStatusLabel(status: string) {
  const map: Record<string, string> = {
    open: '进行中',
    in_progress: '进行中',
    under_review: '审核中',
    completed: '已完成',
    canceled: '已取消',
  }
  return map[status] ?? status
}

function taskStatusClass(status: string) {
  if (status === 'completed') return 'badge-green'
  if (status === 'canceled') return 'badge-red'
  if (status === 'under_review') return 'badge-yellow'
  return 'badge-blue'
}

function sessionStatusLabel(status: string) {
  if (status === 'running') return '运行中'
  if (status === 'idle') return '空闲'
  if (status === 'error') return '出错'
  return status
}

function isTerminal(session: AgentMySessionItem) {
  return session.task_status === 'completed' || session.task_status === 'canceled'
}

onMounted(() => {
  loadSessions()
})
</script>

<template>
  <div class="at-outer">
    <HomeHeaderBar
      :active-tab="null"
      :app-title="appTitle"
      :is-authenticated="auth.isAuthenticated"
      :display-name="auth.displayName"
      :avatar-url="auth.user?.avatar_url ?? null"
      :gender="auth.user?.gender ?? null"
      @publish="openPublishModal"
      @open-my-panel="router.push('/tasks')"
      @open-settings="router.push('/settings')"
      @open-reports="router.push('/reports')"
      @open-chat="router.push('/chat')"
      @open-agent-tasks="router.push('/agent-tasks')"
      @login="router.push('/login')"
      @logout="auth.logout(); router.push('/login')"
      @update:active-tab="(tab) => router.push(tab === 'workers' ? '/?tab=workers' : '/')"
    />

    <main class="at-main">
      <AppToast :toast="toast" @dismiss="clearToast" />

      <div class="at-shell">
        <header class="at-page-header">
          <div class="at-page-header__icon">
            <span class="at-ai-star">✨</span>
          </div>
          <div>
            <h1>代理任务</h1>
            <p>查看你与 AI 代理的所有历史会话</p>
          </div>
        </header>

        <div v-if="loading" class="at-loading">
          <i class="fa-solid fa-spinner fa-spin"></i> 加载中...
        </div>

        <div v-else-if="sessions.length === 0" class="at-empty">
          <i class="fa-solid fa-robot at-empty__icon"></i>
          <p>还没有代理任务记录</p>
          <p class="at-empty__hint">在任务大厅发布任务后，可通过 AI 代理来完成</p>
        </div>

        <div v-else class="at-list">
          <button
            v-for="session in sessions"
            :key="session.session_id"
            class="at-card"
            @click="goToSession(session)"
          >
            <div class="at-card__header">
              <div class="at-card__title-wrap">
                <span class="at-card__title">{{ session.task_title }}</span>
                <div class="at-card__badges">
                  <span class="badge" :class="taskStatusClass(session.task_status)">
                    {{ taskStatusLabel(session.task_status) }}
                  </span>
                  <span v-if="session.status === 'running'" class="badge badge-blue at-badge-running">
                    <i class="fa-solid fa-circle-notch fa-spin"></i> {{ sessionStatusLabel(session.status) }}
                  </span>
                </div>
              </div>

              <div class="at-card__actions">
                <span v-if="isTerminal(session)" class="at-readonly-hint">
                  <i class="fa-solid fa-lock"></i> 只读
                </span>
                <span v-else-if="session.can_send" class="at-send-hint">
                  <i class="fa-solid fa-circle-dot"></i> 可继续对话
                </span>
                <span v-else class="at-send-hint at-send-hint--exhausted">
                  <i class="fa-solid fa-circle-xmark"></i> 次数已满
                </span>
                <i class="fa-solid fa-chevron-right at-card__arrow"></i>
              </div>
            </div>

            <div class="at-card__body">
              <div class="at-card__progress">
                <div class="at-progress-bar">
                  <div
                    class="at-progress-bar__fill"
                    :style="{ width: `${Math.min(100, (session.interaction_count / session.max_interactions) * 100)}%` }"
                    :class="{ 'at-progress-bar__fill--full': session.interaction_count >= session.max_interactions }"
                  ></div>
                </div>
                <span class="at-progress-text">
                  已用 {{ session.interaction_count }} / {{ session.max_interactions }} 次
                </span>
              </div>

              <div class="at-card__meta">
                <span><i class="fa-regular fa-clock"></i> {{ formatFull(session.last_activity_at) }}</span>
              </div>
            </div>
          </button>
        </div>

        <div v-if="!loading && totalPages > 1" class="at-pagination">
          <button
            class="at-page-btn"
            :disabled="page <= 1"
            @click="page--; loadSessions()"
          >
            <i class="fa-solid fa-chevron-left"></i>
          </button>
          <span class="at-page-info">{{ page }} / {{ totalPages }}</span>
          <button
            class="at-page-btn"
            :disabled="page >= totalPages"
            @click="page++; loadSessions()"
          >
            <i class="fa-solid fa-chevron-right"></i>
          </button>
        </div>
      </div>
    </main>

    <HomeTaskEditorModal
      v-model="showCreateModal"
      mode="create"
      :form="newTask"
      :categories="publishCategories"
      :now-local="nowLocal"
      :show-agent-action="canCreateWithAgent"
      :agent-submitting="createWithAgentSubmitting"
      @submit="submitPublishTask"
      @submit-agent="submitPublishTask('agent')"
    />
  </div>
</template>

<style scoped>
.at-outer {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f8fafc;
}

.at-main {
  flex: 1;
  padding: 28px 24px;
}

.at-shell {
  max-width: 800px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.at-page-header {
  display: flex;
  align-items: center;
  gap: 14px;
}

.at-page-header__icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  background: var(--c-accent-light, #eff6ff);
  color: var(--c-accent, #2563eb);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  flex-shrink: 0;
}

.at-ai-star {
  font-style: normal;
  line-height: 1;
}

.at-page-header h1 {
  margin: 0;
  font-size: 22px;
  color: #0f172a;
}

.at-page-header p {
  margin: 4px 0 0;
  font-size: 13px;
  color: #64748b;
}

.at-loading {
  text-align: center;
  padding: 60px 0;
  color: #94a3b8;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.at-empty {
  text-align: center;
  padding: 60px 20px;
  color: #94a3b8;
}

.at-empty__icon {
  font-size: 48px;
  margin-bottom: 16px;
  display: block;
  opacity: 0.4;
}

.at-empty p {
  margin: 0 0 6px;
  font-size: 15px;
  color: #64748b;
}

.at-empty__hint {
  font-size: 13px;
  color: #94a3b8 !important;
}

.at-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.at-card {
  display: flex;
  flex-direction: column;
  gap: 12px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  padding: 16px 18px;
  text-align: left;
  cursor: pointer;
  transition: border-color 0.18s ease, box-shadow 0.18s ease, transform 0.1s ease;
  width: 100%;
}

@media (hover: hover) {
  .at-card:hover {
    border-color: var(--c-accent, #2563eb);
    box-shadow: 0 2px 12px rgba(37, 99, 235, 0.1);
    transform: translateY(-1px);
  }
}

.at-card:active {
  transform: translateY(0);
}

.at-card__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.at-card__title-wrap {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}

.at-card__title {
  font-size: 15px;
  font-weight: 600;
  color: #0f172a;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.at-card__badges {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.at-badge-running {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.at-card__actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.at-readonly-hint {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #94a3b8;
}

.at-send-hint {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #22c55e;
}

.at-send-hint--exhausted {
  color: #f59e0b;
}

.at-card__arrow {
  font-size: 12px;
  color: #cbd5e1;
}

.at-card__body {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.at-card__progress {
  display: flex;
  align-items: center;
  gap: 10px;
}

.at-progress-bar {
  flex: 1;
  height: 6px;
  background: #f1f5f9;
  border-radius: 999px;
  overflow: hidden;
}

.at-progress-bar__fill {
  height: 100%;
  background: var(--c-accent, #2563eb);
  border-radius: 999px;
  transition: width 0.3s ease;
}

.at-progress-bar__fill--full {
  background: #f59e0b;
}

.at-progress-text {
  font-size: 12px;
  color: #64748b;
  white-space: nowrap;
}

.at-card__meta {
  display: flex;
  align-items: center;
  gap: 14px;
  font-size: 12px;
  color: #94a3b8;
}

.at-card__meta i {
  margin-right: 3px;
}

.at-pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding-top: 4px;
}

.at-page-btn {
  width: 34px;
  height: 34px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #fff;
  color: #475569;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background 0.15s ease;
}

.at-page-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

@media (hover: hover) {
  .at-page-btn:not(:disabled):hover {
    background: #f1f5f9;
  }
}

.at-page-info {
  font-size: 13px;
  color: #64748b;
}

/* badge overrides (same as project) */
.badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  font-weight: 500;
  padding: 2px 8px;
  border-radius: 999px;
}

.badge-blue {
  background: #dbeafe;
  color: #1d4ed8;
}

.badge-green {
  background: #dcfce7;
  color: #16a34a;
}

.badge-red {
  background: #fee2e2;
  color: #dc2626;
}

.badge-yellow {
  background: #fef9c3;
  color: #a16207;
}

@media (max-width: 600px) {
  .at-main {
    padding: 16px;
  }
}
</style>
