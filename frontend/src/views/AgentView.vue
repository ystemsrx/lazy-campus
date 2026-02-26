<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AppToast from '../components/AppToast.vue'
import AgentToolCallCard from '../components/agent/AgentToolCallCard.vue'
import ChatRichTextRenderer from '../components/chat/ChatRichTextRenderer.vue'
import HomeHeaderBar from '../components/home/HomeHeaderBar.vue'
import { downloadAgentDeliverable, fetchAgentAvailability, fetchAgentMessages, fetchAgentSession, sendAgentMessage } from '../api/agent'
import { useAppToast } from '../composables/useAppToast'
import { useAuthStore } from '../stores/auth'
import type { AgentAvailability, AgentDeliverable, AgentMessage, AgentSessionDetail } from '../types/api'
import { extractError } from '../utils/error'
import { formatFull } from '../utils/time'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const appTitle = import.meta.env.VITE_APP_TITLE || '校园任务平台'
const sessionId = computed(() => String(route.params.sessionId || ''))
const { toast, showToast, clearToast } = useAppToast()

const availability = ref<AgentAvailability | null>(null)
const session = ref<AgentSessionDetail | null>(null)
const messages = ref<AgentMessage[]>([])

const loading = ref(true)
const sending = ref(false)
const downloadingName = ref<string | null>(null)
const inputText = ref('')
const pendingFiles = ref<File[]>([])

const fileInputRef = ref<HTMLInputElement | null>(null)
const messageContainerRef = ref<HTMLDivElement | null>(null)

let pollTimer: ReturnType<typeof setInterval> | null = null
let pollBusy = false
let lastMessageId = 0

const interactionLeft = computed(() => {
  if (!session.value) return 0
  return Math.max(0, session.value.max_interactions - session.value.interaction_count)
})

const sendDisabled = computed(() => {
  if (!session.value) return true
  if (sending.value) return true
  if (!session.value.can_send) return true
  if (session.value.interaction_count >= session.value.max_interactions) return true
  return false
})

const canSendNow = computed(() => {
  if (sendDisabled.value) return false
  return Boolean(inputText.value.trim() || pendingFiles.value.length > 0)
})

const maxFileCount = computed(() => availability.value?.max_files ?? 5)
const maxFileSizeMb = computed(() => availability.value?.max_file_size_mb ?? 50)

function roleLabel(role: AgentMessage['role']) {
  if (role === 'user') return '我'
  if (role === 'assistant') return 'AI 代理'
  if (role === 'tool_call') return '工具调用'
  if (role === 'tool') return '工具输出'
  return '系统'
}

function resetViewState() {
  loading.value = true
  messages.value = []
  lastMessageId = 0
  inputText.value = ''
  pendingFiles.value = []
  if (fileInputRef.value) fileInputRef.value.value = ''
}

async function refreshAvailability() {
  try {
    availability.value = await fetchAgentAvailability()
  } catch {
    availability.value = null
  }
}

async function refreshSession() {
  session.value = await fetchAgentSession(sessionId.value)
}

async function refreshMessages() {
  const newMessages = await fetchAgentMessages(sessionId.value, lastMessageId)
  if (newMessages.length === 0) return
  messages.value.push(...newMessages)
  lastMessageId = newMessages[newMessages.length - 1].id
}

async function pollSession() {
  if (pollBusy || !sessionId.value) return
  pollBusy = true
  try {
    await Promise.all([refreshSession(), refreshMessages()])
  } catch {
    // ignore polling errors
  } finally {
    pollBusy = false
  }
}

function startPolling() {
  stopPolling()
  pollTimer = setInterval(() => {
    pollSession().catch(() => {})
  }, 2000)
}

function stopPolling() {
  if (!pollTimer) return
  clearInterval(pollTimer)
  pollTimer = null
}

async function bootstrap() {
  if (!sessionId.value) {
    showToast('代理会话不存在', 'error')
    router.push('/tasks')
    return
  }
  resetViewState()
  try {
    await Promise.all([refreshAvailability(), refreshSession()])
    await refreshMessages()
  } catch (error) {
    showToast(extractError(error, '加载代理会话失败'), 'error')
    router.push('/tasks')
  } finally {
    loading.value = false
  }
}

function formatFileSize(size: number) {
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / (1024 * 1024)).toFixed(1)} MB`
}

function pickFiles(event: Event) {
  const input = event.target as HTMLInputElement
  const files = Array.from(input.files || [])
  if (!files.length) return

  const limitCount = maxFileCount.value
  const limitSize = maxFileSizeMb.value * 1024 * 1024
  const next = [...pendingFiles.value]

  for (const file of files) {
    if (next.length >= limitCount) {
      showToast(`最多可添加 ${limitCount} 个文件`, 'warning')
      break
    }
    if (file.size > limitSize) {
      showToast(`「${file.name}」超过 ${maxFileSizeMb.value} MB 限制`, 'error')
      continue
    }
    next.push(file)
  }

  pendingFiles.value = next
  input.value = ''
}

function removePendingFile(index: number) {
  pendingFiles.value.splice(index, 1)
}

async function handleSend() {
  if (!canSendNow.value || !session.value) return
  sending.value = true
  try {
    await sendAgentMessage(session.value.session_id, {
      content: inputText.value.trim(),
      files: pendingFiles.value,
    })
    inputText.value = ''
    pendingFiles.value = []
    if (fileInputRef.value) fileInputRef.value.value = ''
    await Promise.all([pollSession(), refreshAvailability()])
  } catch (error) {
    showToast(extractError(error, '发送失败'), 'error')
  } finally {
    sending.value = false
  }
}

async function handleDownload(item: AgentDeliverable) {
  if (!session.value) return
  downloadingName.value = item.name
  try {
    const blob = await downloadAgentDeliverable(session.value.session_id, item.name)
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = item.name.split('/').pop() || item.name
    link.click()
    URL.revokeObjectURL(url)
  } catch (error) {
    showToast(extractError(error, '下载失败'), 'error')
  } finally {
    downloadingName.value = null
  }
}

watch(
  () => messages.value.length,
  () => {
    nextTick(() => {
      const container = messageContainerRef.value
      if (!container) return
      container.scrollTop = container.scrollHeight
    })
  },
)

watch(
  () => sessionId.value,
  () => {
    bootstrap().catch(() => {})
  },
  { immediate: true },
)

onMounted(() => {
  startPolling()
})

onUnmounted(() => {
  stopPolling()
})
</script>

<template>
  <div class="agent-outer">
    <HomeHeaderBar
      :active-tab="null"
      :app-title="appTitle"
      :is-authenticated="auth.isAuthenticated"
      :display-name="auth.displayName"
      :avatar-url="auth.user?.avatar_url ?? null"
      :gender="auth.user?.gender ?? null"
      @publish="router.push('/')"
      @open-my-panel="router.push('/tasks')"
      @open-settings="router.push('/settings')"
      @open-reports="router.push('/reports')"
      @open-chat="router.push('/chat')"
      @login="router.push('/login')"
      @logout="auth.logout(); router.push('/login')"
      @update:active-tab="(tab) => router.push(tab === 'workers' ? '/?tab=workers' : '/')"
    />

    <main class="agent-page">
      <AppToast :toast="toast" @dismiss="clearToast" />

      <div class="agent-shell">
        <header class="agent-header">
          <div>
            <h1>{{ session?.task_title || 'AI 代理会话' }}</h1>
            <p>请上传必要文件并描述需求。文件不会在选择时上传，点击发送后才会提交。</p>
          </div>
          <div class="agent-header__meta">
            <span class="badge badge-blue">已用 {{ session?.interaction_count ?? 0 }}/{{ session?.max_interactions ?? 8 }}</span>
            <span class="badge" :class="interactionLeft > 0 ? 'badge-green' : 'badge-red'">剩余 {{ interactionLeft }} 次</span>
          </div>
        </header>

        <div class="agent-layout">
          <section class="agent-chat">
            <div ref="messageContainerRef" class="agent-messages">
              <div v-if="loading" class="agent-empty">加载中...</div>
              <div v-else-if="messages.length === 0" class="agent-empty">还没有消息，先发送你的需求吧。</div>

              <div
                v-for="msg in messages"
                :key="msg.id"
                class="agent-message"
                :class="{
                  'agent-message--user': msg.role === 'user',
                  'agent-message--assistant': msg.role === 'assistant',
                  'agent-message--tool': msg.role === 'tool' || msg.role === 'tool_call',
                  'agent-message--system': msg.role === 'system',
                }"
              >
                <div class="agent-message__meta">
                  <strong>{{ roleLabel(msg.role) }}</strong>
                  <span>{{ formatFull(msg.created_at) }}</span>
                </div>

                <AgentToolCallCard
                  v-if="msg.role === 'tool_call'"
                  :tool-name="msg.tool_name"
                  :tool-arguments="msg.tool_arguments"
                  :tool-call-id="msg.tool_call_id"
                />

                <pre v-else-if="msg.role === 'tool'" class="agent-tool-output">{{ msg.content }}</pre>

                <div v-else-if="msg.role === 'system'" class="agent-system">{{ msg.content }}</div>

                <div v-else class="agent-bubble">
                  <ChatRichTextRenderer :content="msg.content || ''" />
                </div>

                <div v-if="msg.attachments.length" class="agent-attachments">
                  <span v-for="attachment in msg.attachments" :key="attachment.stored_name" class="agent-attachment-chip">
                    <i class="fa-solid fa-file"></i>
                    {{ attachment.name }}
                    <small>({{ formatFileSize(attachment.size) }})</small>
                  </span>
                </div>
              </div>
            </div>

            <div class="agent-input">
              <div v-if="pendingFiles.length" class="agent-pending">
                <div v-for="(file, index) in pendingFiles" :key="`${file.name}-${index}`" class="agent-pending__item">
                  <span>{{ file.name }}</span>
                  <small>{{ formatFileSize(file.size) }}</small>
                  <button type="button" @click="removePendingFile(index)"><i class="fa-solid fa-xmark"></i></button>
                </div>
              </div>

              <div class="agent-compose">
                <label class="agent-upload-btn" :class="{ disabled: sendDisabled }">
                  <i class="fa-solid fa-paperclip"></i>
                  <input
                    ref="fileInputRef"
                    type="file"
                    multiple
                    :disabled="sendDisabled"
                    @change="pickFiles"
                  />
                </label>

                <textarea
                  v-model="inputText"
                  class="agent-textarea"
                  :disabled="sendDisabled"
                  placeholder="描述你的目标、预期产物和约束条件..."
                />

                <button class="agent-send-btn" :disabled="!canSendNow" @click="handleSend">
                  {{ sending ? '发送中...' : '发送' }}
                </button>
              </div>

              <p class="agent-hint">
                单次最多 {{ maxFileCount }} 个文件，单个不超过 {{ maxFileSizeMb }} MB。
                <span v-if="session?.status === 'running'">代理正在执行中，可等待输出。</span>
                <span v-else-if="interactionLeft <= 0">交互次数已用尽，需重新开启代理会话。</span>
              </p>
            </div>
          </section>

          <aside class="agent-side">
            <h3>交付文件</h3>
            <p class="agent-side__hint">来自 /workspace/deliverables</p>

            <div v-if="!(session?.deliverables.length)" class="agent-side__empty">暂无交付文件</div>

            <button
              v-for="item in session?.deliverables || []"
              :key="item.name"
              class="agent-deliverable"
              :disabled="downloadingName === item.name"
              @click="handleDownload(item)"
            >
              <div class="agent-deliverable__meta">
                <strong>{{ item.name }}</strong>
                <span>{{ formatFileSize(item.size) }}</span>
              </div>
              <small>{{ formatFull(item.updated_at) }}</small>
            </button>
          </aside>
        </div>
      </div>
    </main>
  </div>
</template>

<style scoped>
.agent-outer {
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #f8fafc;
}

.agent-page {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  padding: 20px;
  overflow: hidden;
}

.agent-shell {
  max-width: 1280px;
  width: 100%;
  margin: 0 auto;
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow: hidden;
}

.agent-header {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  padding: 16px 18px;
  display: flex;
  justify-content: space-between;
  gap: 16px;
}

.agent-header h1 {
  margin: 0;
  font-size: 20px;
  color: #0f172a;
}

.agent-header p {
  margin: 6px 0 0;
  font-size: 13px;
  color: #64748b;
}

.agent-header__meta {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  flex-wrap: wrap;
}

.agent-layout {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 280px;
  gap: 14px;
  overflow: hidden;
}

.agent-chat {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

.agent-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.agent-empty {
  color: #94a3b8;
  font-size: 13px;
  text-align: center;
  margin-top: 24px;
}

.agent-message {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-width: 90%;
}

.agent-message--user {
  align-self: flex-end;
}

.agent-message--assistant,
.agent-message--tool,
.agent-message--system {
  align-self: flex-start;
}

.agent-message__meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
  color: #94a3b8;
}

.agent-message__meta strong {
  color: #334155;
}

.agent-bubble {
  border-radius: 12px;
  padding: 10px 12px;
  background: #f1f5f9;
  color: #0f172a;
}

.agent-message--user .agent-bubble {
  background: #2563eb;
  color: #fff;
}

.agent-message--user .agent-bubble :deep(*) {
  color: #fff;
}

.agent-system {
  border-radius: 12px;
  background: #fef3c7;
  border: 1px solid #fcd34d;
  color: #92400e;
  padding: 10px 12px;
  font-size: 13px;
}

.agent-tool-output {
  margin: 0;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 10px 12px;
  font-size: 12px;
  max-height: 220px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-word;
}

.agent-attachments {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.agent-attachment-chip {
  font-size: 11px;
  color: #334155;
  border: 1px solid #e2e8f0;
  border-radius: 999px;
  padding: 4px 8px;
  display: flex;
  align-items: center;
  gap: 4px;
  background: #fff;
}

.agent-input {
  border-top: 1px solid #e2e8f0;
  padding: 10px 12px 12px;
  flex-shrink: 0;
}

.agent-pending {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 8px;
}

.agent-pending__item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 4px 8px;
  font-size: 12px;
  color: #334155;
  background: #f8fafc;
}

.agent-pending__item small {
  color: #64748b;
}

.agent-pending__item button {
  border: none;
  background: transparent;
  color: #64748b;
  padding: 0;
}

.agent-compose {
  display: flex;
  gap: 8px;
  align-items: flex-end;
}

.agent-upload-btn {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  border: 1px solid #cbd5e1;
  display: grid;
  place-items: center;
  color: #475569;
  background: #fff;
  flex-shrink: 0;
  cursor: pointer;
}

.agent-upload-btn.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.agent-upload-btn input {
  display: none;
}

.agent-textarea {
  flex: 1;
  border: 1px solid #cbd5e1;
  border-radius: 12px;
  min-height: 72px;
  max-height: 160px;
  resize: vertical;
  font-size: 14px;
  padding: 10px 12px;
  font-family: inherit;
}

.agent-send-btn {
  border: none;
  background: #2563eb;
  color: #fff;
  border-radius: 10px;
  min-width: 72px;
  height: 36px;
  font-size: 13px;
}

.agent-send-btn:disabled {
  background: #cbd5e1;
  cursor: not-allowed;
}

.agent-hint {
  margin: 8px 2px 0;
  font-size: 11px;
  color: #64748b;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.agent-side {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 0;
  overflow-y: auto;
}

.agent-side h3 {
  margin: 0;
  font-size: 16px;
}

.agent-side__hint {
  margin: 0;
  font-size: 12px;
  color: #64748b;
}

.agent-side__empty {
  font-size: 13px;
  color: #94a3b8;
}

.agent-deliverable {
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 8px 10px;
  background: #f8fafc;
  display: flex;
  flex-direction: column;
  gap: 4px;
  text-align: left;
}

.agent-deliverable__meta {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  font-size: 12px;
}

.agent-deliverable small {
  color: #64748b;
  font-size: 11px;
}

@media (max-width: 1000px) {
  .agent-layout {
    grid-template-columns: 1fr;
    overflow-y: auto;
  }

  .agent-chat {
    min-height: 60vh;
  }

  .agent-side {
    min-height: 0;
    max-height: none;
  }
}
</style>
