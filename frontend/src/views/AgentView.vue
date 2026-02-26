<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AppToast from '../components/AppToast.vue'
import ChatRichTextRenderer from '../components/chat/ChatRichTextRenderer.vue'
import HomeHeaderBar from '../components/home/HomeHeaderBar.vue'
import { deleteAgentDeliverables, downloadAgentDeliverable, downloadDeliverableZip, fetchAgentAvailability, fetchAgentMessages, fetchAgentSession, sendAgentMessage } from '../api/agent'
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
const zippingAll = ref(false)
const deletingSelected = ref(false)
const selectMode = ref(false)
const selectedNames = ref<Set<string>>(new Set())
const inputText = ref('')
const pendingFiles = ref<File[]>([])

const fileInputRef = ref<HTMLInputElement | null>(null)
const chatScrollRef = ref<HTMLDivElement | null>(null)

let pollTimer: ReturnType<typeof setInterval> | null = null
let pollBusy = false
let lastMessageId = 0

const interactionLeft = computed(() => {
  if (!session.value) return 0
  return Math.max(0, session.value.max_interactions - session.value.interaction_count)
})

const isTaskTerminal = computed(() => {
  const status = session.value?.task_status
  return status === 'completed' || status === 'canceled'
})

const sendDisabled = computed(() => {
  if (!session.value) return true
  if (sending.value) return true
  if (isTaskTerminal.value) return true
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

function parseToolArgs(raw: string | null): Record<string, any> {
  if (!raw) return {}
  try { return JSON.parse(raw) } catch { return {} }
}

function isShellTool(name: string | null): boolean {
  if (!name) return false
  const n = name.toLowerCase()
  return n === 'shell' || n === 'execute_command' || n === 'bash'
}

function isWriteFileTool(name: string | null): boolean {
  if (!name) return false
  const n = name.toLowerCase()
  return n === 'writefile' || n === 'write_file'
}

function isReadFileTool(name: string | null): boolean {
  if (!name) return false
  const n = name.toLowerCase()
  return n === 'readfile' || n === 'read_file'
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

async function handleDownloadZip() {
  if (!session.value) return
  zippingAll.value = true
  try {
    const names = selectMode.value && selectedNames.value.size > 0
      ? [...selectedNames.value]
      : []
    const blob = await downloadDeliverableZip(session.value.session_id, names)
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = 'deliverables.zip'
    link.click()
    URL.revokeObjectURL(url)
  } catch (error) {
    showToast(extractError(error, '打包下载失败'), 'error')
  } finally {
    zippingAll.value = false
  }
}

async function handleDeleteSelected() {
  if (!session.value || selectedNames.value.size === 0) return
  deletingSelected.value = true
  try {
    await deleteAgentDeliverables(session.value.session_id, [...selectedNames.value])
    selectedNames.value = new Set()
    await refreshSession()
  } catch (error) {
    showToast(extractError(error, '删除失败'), 'error')
  } finally {
    deletingSelected.value = false
  }
}

function toggleSelectMode() {
  selectMode.value = !selectMode.value
  if (!selectMode.value) selectedNames.value = new Set()
}

function toggleSelect(name: string) {
  const next = new Set(selectedNames.value)
  if (next.has(name)) next.delete(name)
  else next.add(name)
  selectedNames.value = next
}

function handleDeliverableClick(item: AgentDeliverable) {
  if (selectMode.value) {
    toggleSelect(item.name)
  } else {
    handleDownload(item)
  }
}

// --- Terminal ---

const terminalHostname = computed(() => {
  return appTitle.replace(/\s+/g, '-').replace(/[A-Za-z]/g, c => c.toLowerCase()) + '@agent'
})

function findClosingQuote(s: string, start: number): number {
  let i = start
  while (i < s.length) {
    if (s[i] === '\\') { i += 2; continue }
    if (s[i] === "'") return i
    i++
  }
  return -1
}

function unescapePythonStr(s: string): string {
  return s
    .replace(/\\\\/g, '\x00BS\x00')
    .replace(/\\n/g, '\n')
    .replace(/\\t/g, '\t')
    .replace(/\\r/g, '\r')
    .replace(/\\'/g, "'")
    .replace(/\x00BS\x00/g, '\\')
}

function extractToolOutputText(raw: string): { systemLines: string[], text: string } {
  if (!raw) return { systemLines: [], text: '' }
  let content = raw.trim()

  try {
    const parsed = JSON.parse(content)
    if (Array.isArray(parsed)) {
      content = parsed
        .filter((x: any) => x?.text != null)
        .map((x: any) => String(x.text))
        .join('\n')
    }
  } catch {
    if (content.startsWith("[{") || content.startsWith("[{'")) {
      const texts: string[] = []
      const marker = "'text': '"
      let pos = 0
      while (true) {
        const idx = content.indexOf(marker, pos)
        if (idx === -1) break
        const vStart = idx + marker.length
        const vEnd = findClosingQuote(content, vStart)
        if (vEnd === -1) break
        texts.push(unescapePythonStr(content.substring(vStart, vEnd)))
        pos = vEnd + 1
      }
      if (texts.length > 0) content = texts.join('\n')
    }
  }

  const systemLines: string[] = []
  const cleaned = content.replace(/<system>([\s\S]*?)<\/system>/g, (_, inner) => {
    systemLines.push(inner.trim())
    return ''
  })
  return { systemLines, text: cleaned.trim() }
}

interface TerminalEntry {
  id: number
  toolType: 'shell' | 'write-file' | 'read-file' | 'other'
  toolName: string
  command?: string
  filePath?: string
  rawArgs?: string
  systemLines: string[]
  outputText: string
  pending: boolean
  success: boolean | null
}

const snapIndices = ref(new Map<number, number>())

function handleSnapScroll(event: Event, roundId: number, total: number) {
  const el = event.target as HTMLElement
  const idx = Math.min(Math.round(el.scrollTop / 64), total - 1)
  snapIndices.value = new Map(snapIndices.value.set(roundId, idx))
}

interface ConversationRound {
  id: number
  userMessage: AgentMessage | null
  aiIntermediate: AgentMessage[]
  entries: TerminalEntry[]
  aiFinal: AgentMessage | null
}

const conversationRounds = computed<ConversationRound[]>(() => {
  const rounds: ConversationRound[] = []
  const msgs = messages.value

  const groups: AgentMessage[][] = []
  let cur: AgentMessage[] = []
  for (const msg of msgs) {
    if (msg.role === 'user') {
      if (cur.length > 0) groups.push(cur)
      cur = [msg]
    } else {
      cur.push(msg)
    }
  }
  if (cur.length > 0) groups.push(cur)

  for (const group of groups) {
    const round: ConversationRound = {
      id: group[0].id,
      userMessage: group[0].role === 'user' ? group[0] : null,
      aiIntermediate: [],
      entries: [],
      aiFinal: null,
    }

    for (let i = 0; i < group.length; i++) {
      const msg = group[i]
      if (msg.role !== 'assistant' && msg.role !== 'system') continue
      if (!msg.content?.trim()) continue
      const rest = group.slice(i + 1)
      const hasToolAfter = rest.some(m => m.role === 'tool_call')
      const hasLaterText = rest.some(m => m.role === 'assistant' && m.content?.trim())
      if (hasToolAfter || hasLaterText) {
        round.aiIntermediate.push(msg)
      } else {
        round.aiFinal = msg
      }
    }

    for (let i = 0; i < group.length; i++) {
      const msg = group[i]
      if (msg.role !== 'tool_call') continue
      const args = parseToolArgs(msg.tool_arguments)
      const toolName = msg.tool_name || 'Tool'
      let entry: TerminalEntry

      if (isShellTool(msg.tool_name)) {
        entry = { id: msg.id, toolType: 'shell', toolName, command: args.command || '', systemLines: [], outputText: '', pending: true, success: null }
      } else if (isWriteFileTool(msg.tool_name)) {
        entry = { id: msg.id, toolType: 'write-file', toolName, filePath: args.path || '', systemLines: [], outputText: '', pending: true, success: null }
      } else if (isReadFileTool(msg.tool_name)) {
        entry = { id: msg.id, toolType: 'read-file', toolName, filePath: args.path || '', systemLines: [], outputText: '', pending: true, success: null }
      } else {
        let pretty = msg.tool_arguments || ''
        try { pretty = JSON.stringify(JSON.parse(pretty), null, 2) } catch {}
        entry = { id: msg.id, toolType: 'other', toolName, rawArgs: pretty, systemLines: [], outputText: '', pending: true, success: null }
      }

      let outputMsg: AgentMessage | undefined
      if (msg.tool_call_id) {
        outputMsg = msgs.find(m => m.role === 'tool' && m.tool_call_id === msg.tool_call_id)
      }
      if (!outputMsg) {
        for (let j = i + 1; j < group.length; j++) {
          if (group[j].role === 'tool') { outputMsg = group[j]; break }
          if (group[j].role === 'tool_call') break
        }
      }
      if (outputMsg?.content) {
        const { systemLines, text } = extractToolOutputText(outputMsg.content)
        if (entry.toolType === 'shell') {
          const kept: string[] = []
          for (const line of systemLines) {
            if (/command executed successfully/i.test(line)) {
              entry.success = true
            } else if (/\berror\b/i.test(line)) {
              entry.success = false
              kept.push(line)
            } else {
              kept.push(line)
            }
          }
          entry.systemLines = kept
          if (entry.success === null) entry.success = true
        } else {
          entry.systemLines = systemLines
        }
        entry.outputText = text
        entry.pending = false
      }
      round.entries.push(entry)
    }

    rounds.push(round)
  }
  return rounds
})

watch(
  () => messages.value.length,
  () => {
    nextTick(() => {
      if (chatScrollRef.value) {
        chatScrollRef.value.scrollTop = chatScrollRef.value.scrollHeight
        chatScrollRef.value.querySelectorAll('.chat-ai-snap').forEach(el => {
          el.scrollTop = el.scrollHeight
        })
        chatScrollRef.value.querySelectorAll('.terminal-body').forEach(el => {
          el.scrollTop = el.scrollHeight
        })
      }
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
      @open-agent-tasks="router.push('/agent-tasks')"
      @login="router.push('/login')"
      @logout="auth.logout(); router.push('/login')"
      @update:active-tab="(tab) => router.push(tab === 'workers' ? '/?tab=workers' : '/')"
    />

    <main class="agent-page">
      <AppToast :toast="toast" @dismiss="clearToast" />

      <div class="agent-shell">
        <div class="agent-layout">
          <section class="agent-chat">
            <div ref="chatScrollRef" class="chat-scroll">
              <div v-if="loading" class="chat-empty">加载中...</div>
              <div v-else-if="conversationRounds.length === 0" class="chat-empty">还没有消息，先发送你的需求吧。</div>

              <div v-for="round in conversationRounds" :key="round.id" class="chat-round">
                <div v-if="round.userMessage" class="chat-bubble-row chat-bubble-row--right">
                  <div class="chat-bubble chat-bubble--user">
                    <ChatRichTextRenderer :content="round.userMessage.content || ''" />
                    <div v-if="round.userMessage.attachments?.length" class="chat-bubble-files">
                      <span v-for="att in round.userMessage.attachments" :key="att.stored_name" class="chat-file-chip">
                        <i class="fa-solid fa-file"></i> {{ att.name }}
                        <small>({{ formatFileSize(att.size) }})</small>
                      </span>
                    </div>
                  </div>
                </div>

                <div v-if="round.aiIntermediate.length" class="chat-ai-snap-wrap">
                  <div class="chat-ai-snap-head">
                    <i class="fa-solid fa-robot"></i>
                    <span>AI 代理</span>
                  </div>
                  <div class="chat-ai-snap-outer" :class="{ 'chat-ai-snap-outer--glow': session?.status === 'running' }">
                    <div class="chat-ai-snap" @scroll="handleSnapScroll($event, round.id, round.aiIntermediate.length)">
                      <div v-for="msg in round.aiIntermediate" :key="msg.id" class="chat-ai-snap-item">
                        <span>{{ msg.content }}</span>
                      </div>
                    </div>
                    <span class="chat-ai-snap-idx">{{ (snapIndices.get(round.id) ?? (round.aiIntermediate.length - 1)) + 1 }}/{{ round.aiIntermediate.length }}</span>
                  </div>
                </div>

                <div v-if="round.entries.length" class="terminal">
                  <div class="terminal-titlebar">
                    <div class="terminal-dots">
                      <span class="terminal-dot terminal-dot--red"></span>
                      <span class="terminal-dot terminal-dot--yellow"></span>
                      <span class="terminal-dot terminal-dot--green"></span>
                    </div>
                    <span class="terminal-hostname">{{ terminalHostname }}</span>
                  </div>
                  <div class="terminal-body">
                    <template v-for="entry in round.entries" :key="entry.id">
                      <div v-if="entry.toolType === 'shell'" class="terminal-entry">
                        <div class="terminal-prompt-line">
                          <span v-if="entry.success === true" class="terminal-status-dot terminal-status-dot--ok"></span>
                          <span v-else-if="entry.success === false" class="terminal-status-dot terminal-status-dot--err"></span>
                          <span class="terminal-user">{{ terminalHostname }}</span>:<span class="terminal-path">/workspace</span><span class="terminal-dollar">$</span> <span class="terminal-cmd">{{ entry.command }}</span>
                        </div>
                        <div v-for="(line, idx) in entry.systemLines" :key="'s'+idx" class="terminal-sys-line">{{ line }}</div>
                        <pre v-if="entry.outputText" class="terminal-pre">{{ entry.outputText }}</pre>
                        <div v-if="entry.pending && session?.status === 'running'" class="terminal-status">
                          <span class="terminal-blink">█</span>
                        </div>
                      </div>

                      <div v-else-if="entry.toolType === 'write-file'" class="terminal-entry">
                        <div class="terminal-write-box">
                          <div class="terminal-write-head">
                            <i class="fa-solid fa-file-pen"></i>
                            <span>WriteFile</span>
                          </div>
                          <div class="terminal-write-detail">
                            <span class="terminal-write-key">path</span>
                            <span class="terminal-write-val">{{ entry.filePath }}</span>
                          </div>
                          <div v-for="(line, idx) in entry.systemLines" :key="'s'+idx" class="terminal-write-ok">
                            <i class="fa-solid fa-check"></i> {{ line }}
                          </div>
                        </div>
                        <pre v-if="entry.outputText" class="terminal-pre">{{ entry.outputText }}</pre>
                        <div v-if="entry.pending && session?.status === 'running'" class="terminal-status">
                          <span class="terminal-blink">█</span>
                        </div>
                      </div>

                      <div v-else-if="entry.toolType === 'read-file'" class="terminal-entry">
                        <div class="terminal-write-box terminal-write-box--read">
                          <div class="terminal-write-head terminal-write-head--read">
                            <i class="fa-solid fa-file-lines"></i>
                            <span>ReadFile</span>
                          </div>
                          <div class="terminal-write-detail">
                            <span class="terminal-write-key">path</span>
                            <span class="terminal-write-val">{{ entry.filePath }}</span>
                          </div>
                          <div v-for="(line, idx) in entry.systemLines" :key="'s'+idx" class="terminal-write-ok">
                            <i class="fa-solid fa-check"></i> {{ line }}
                          </div>
                        </div>
                        <pre v-if="entry.outputText" class="terminal-pre">{{ entry.outputText }}</pre>
                        <div v-if="entry.pending && session?.status === 'running'" class="terminal-status">
                          <span class="terminal-blink">█</span>
                        </div>
                      </div>

                      <div v-else class="terminal-entry">
                        <div class="terminal-other-line">
                          <span class="terminal-other-icon">⚙</span>
                          <span class="terminal-other-name">{{ entry.toolName }}</span>
                        </div>
                        <pre v-if="entry.rawArgs" class="terminal-pre terminal-pre--args">{{ entry.rawArgs }}</pre>
                        <div v-for="(line, idx) in entry.systemLines" :key="'s'+idx" class="terminal-sys-line">{{ line }}</div>
                        <pre v-if="entry.outputText" class="terminal-pre">{{ entry.outputText }}</pre>
                        <div v-if="entry.pending && session?.status === 'running'" class="terminal-status">
                          <span class="terminal-blink">█</span>
                        </div>
                      </div>
                    </template>
                  </div>
                </div>

                <div v-if="round.aiFinal" class="chat-ai-final">
                  <div class="chat-ai-final-head">
                    <i class="fa-solid fa-robot"></i>
                    <span>AI 代理</span>
                  </div>
                  <div class="chat-ai-final-body">
                    <ChatRichTextRenderer :content="round.aiFinal.content || ''" />
                  </div>
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

              <div class="agent-hint-row">
                <p class="agent-hint">
                  <span v-if="isTaskTerminal">任务已{{ session?.task_status === 'completed' ? '完成' : '取消' }}，会话已关闭。</span>
                  <span v-else-if="session?.status === 'running'">代理正在执行中，可等待输出。</span>
                  <span v-else-if="interactionLeft <= 0">交互次数已用尽。</span>
                  <span v-else>单次最多 {{ maxFileCount }} 个文件，单个不超过 {{ maxFileSizeMb }} MB。</span>
                </p>
                <div class="agent-hint-badges">
                  <span class="badge badge-blue">已用 {{ session?.interaction_count ?? 0 }}/{{ session?.max_interactions ?? 8 }}</span>
                  <span class="badge" :class="interactionLeft > 0 ? 'badge-green' : 'badge-red'">剩余 {{ interactionLeft }}</span>
                </div>
              </div>
            </div>
          </section>

          <aside class="agent-side">
            <div class="agent-side__header">
              <div>
                <h3>交付文件</h3>
                <p class="agent-side__hint">来自 /workspace/deliverables</p>
              </div>
              <button
                v-if="session?.deliverables.length"
                class="agent-side-btn"
                :class="{ 'agent-side-btn--active': selectMode }"
                @click="toggleSelectMode"
              >
                <i :class="selectMode ? 'fa-solid fa-xmark' : 'fa-solid fa-list-check'"></i>
                {{ selectMode ? '取消' : '多选' }}
              </button>
            </div>

            <div v-if="selectMode && session?.deliverables.length" class="agent-side__select-bar">
              <span>已选 {{ selectedNames.size }} / {{ session?.deliverables.length }} 项</span>
              <button
                class="agent-side-delete-btn"
                :disabled="selectedNames.size === 0 || deletingSelected"
                @click="handleDeleteSelected"
              >
                <i class="fa-solid fa-trash"></i>
                {{ deletingSelected ? '删除中...' : '删除选中' }}
              </button>
            </div>

            <div class="agent-side__list">
              <div v-if="!(session?.deliverables.length)" class="agent-side__empty">暂无交付文件</div>

              <div
                v-for="item in session?.deliverables || []"
                :key="item.name"
                class="agent-deliverable"
                :class="{
                  'agent-deliverable--selected': selectMode && selectedNames.has(item.name),
                  'agent-deliverable--selectable': selectMode,
                  'agent-deliverable--loading': !selectMode && downloadingName === item.name,
                }"
                @click="handleDeliverableClick(item)"
              >
                <div v-if="selectMode" class="agent-deliverable__check">
                  <i :class="selectedNames.has(item.name) ? 'fa-solid fa-square-check' : 'fa-regular fa-square'"></i>
                </div>
                <div class="agent-deliverable__body">
                  <div class="agent-deliverable__meta">
                    <strong>{{ item.name }}</strong>
                    <span>{{ formatFileSize(item.size) }}</span>
                  </div>
                  <small>{{ formatFull(item.updated_at) }}</small>
                </div>
                <div v-if="!selectMode" class="agent-deliverable__action">
                  <i v-if="downloadingName === item.name" class="fa-solid fa-spinner fa-spin"></i>
                  <i v-else class="fa-solid fa-download"></i>
                </div>
              </div>
            </div>

            <button
              v-if="session?.deliverables.length"
              class="agent-side-zip-btn"
              :disabled="zippingAll"
              @click="handleDownloadZip"
            >
              <i class="fa-solid fa-file-zipper"></i>
              {{ zippingAll ? '打包中...' : (selectMode && selectedNames.size > 0 ? `打包下载（${selectedNames.size} 个）` : '打包下载全部') }}
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
  overflow: hidden;
}

.agent-layout {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 280px;
  gap: 14px;
  overflow: hidden;
}

/* ===== Chat Column ===== */

.agent-chat {
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
  gap: 12px;
}

.chat-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 4px 2px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.chat-scroll::-webkit-scrollbar { width: 6px; }
.chat-scroll::-webkit-scrollbar-track { background: transparent; }
.chat-scroll::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 3px; }

.chat-empty {
  color: #94a3b8;
  font-size: 13px;
  text-align: center;
  margin-top: 40px;
}

.chat-round {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

/* --- User Bubble --- */

.chat-bubble-row {
  display: flex;
}

.chat-bubble-row--right {
  justify-content: flex-end;
}

.chat-bubble {
  max-width: 80%;
  border-radius: 16px 16px 4px 16px;
  padding: 10px 14px;
  font-size: 14px;
  line-height: 1.6;
}

.chat-bubble--user {
  background: #2563eb;
  color: #fff;
}

.chat-bubble--user :deep(*) {
  color: #fff !important;
}

.chat-bubble-files {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}

.chat-file-chip {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.85);
  background: rgba(255, 255, 255, 0.15);
  border-radius: 999px;
  padding: 3px 10px;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.chat-file-chip small {
  opacity: 0.7;
}

/* --- AI Intermediate (snap-scroll) --- */

.chat-ai-snap-wrap {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.chat-ai-snap-head {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #64748b;
  padding-left: 2px;
}

.chat-ai-snap-head i {
  color: #2563eb;
  font-size: 13px;
}

.chat-ai-snap-outer {
  position: relative;
  border-radius: 12px;
}

.chat-ai-snap-outer--glow {
  padding: 2px;
  border-radius: 14px;
  overflow: hidden;
}

.chat-ai-snap-outer--glow::before {
  content: '';
  position: absolute;
  width: 200%;
  height: 200%;
  top: -50%;
  left: -50%;
  background: conic-gradient(#3b82f6, #8b5cf6, #ec4899, #f59e0b, #10b981, #3b82f6);
  animation: glowSpin 3s linear infinite;
}

.chat-ai-snap-outer--glow .chat-ai-snap {
  border: none;
  border-radius: 10px;
  position: relative;
  z-index: 1;
}

@keyframes glowSpin {
  to { transform: rotate(360deg); }
}

.chat-ai-snap-idx {
  position: absolute;
  bottom: 8px;
  right: 12px;
  font-size: 11px;
  color: #64748b;
  background: rgba(241, 245, 249, 0.92);
  padding: 1px 8px;
  border-radius: 4px;
  z-index: 2;
  font-variant-numeric: tabular-nums;
  pointer-events: none;
}

.chat-ai-snap-outer--glow .chat-ai-snap-idx {
  bottom: 10px;
  right: 14px;
}

.chat-ai-snap {
  height: 64px;
  overflow-y: auto;
  scroll-snap-type: y mandatory;
  overscroll-behavior-y: contain;
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
}

.chat-ai-snap::-webkit-scrollbar { width: 0; }

.chat-ai-snap-item {
  min-height: 64px;
  height: 64px;
  scroll-snap-align: start;
  display: flex;
  align-items: center;
  padding: 0 16px;
  font-size: 13px;
  color: #334155;
  line-height: 1.5;
  box-sizing: border-box;
}

.chat-ai-snap-item span {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* ===== Terminal ===== */

.terminal {
  display: flex;
  flex-direction: column;
  border-radius: 10px;
  overflow: hidden;
  background: #0d1117;
  border: 1px solid #30363d;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
}

.terminal-titlebar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  background: #1c2028;
  border-bottom: 1px solid #30363d;
  flex-shrink: 0;
  user-select: none;
}

.terminal-dots { display: flex; gap: 7px; }

.terminal-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
}

.terminal-dot--red    { background: #ff5f56; }
.terminal-dot--yellow { background: #ffbd2e; }
.terminal-dot--green  { background: #27c93f; }

.terminal-hostname {
  font-size: 12px;
  color: #8b949e;
  font-family: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', 'SF Mono', 'Menlo', monospace;
  font-weight: 500;
}

.terminal-body {
  max-height: 420px;
  overflow-y: auto;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  font-family: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', 'SF Mono', 'Menlo', monospace;
}

.terminal-body::-webkit-scrollbar { width: 6px; }
.terminal-body::-webkit-scrollbar-track { background: #0d1117; }
.terminal-body::-webkit-scrollbar-thumb { background: #30363d; border-radius: 3px; }
.terminal-body::-webkit-scrollbar-thumb:hover { background: #484f58; }

.terminal-status {
  color: #8b949e;
  font-size: 13px;
}

@keyframes termBlink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

.terminal-blink {
  animation: termBlink 1s step-end infinite;
  color: #58a6ff;
}

.terminal-entry {
  display: flex;
  flex-direction: column;
  gap: 2px;
  animation: termFade 0.25s ease;
}

@keyframes termFade {
  from { opacity: 0; transform: translateY(6px); }
  to   { opacity: 1; transform: translateY(0); }
}

/* Shell prompt */

.terminal-status-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 6px;
  vertical-align: middle;
}

.terminal-status-dot--ok { background: #3fb950; }
.terminal-status-dot--err { background: #f85149; }

.terminal-prompt-line {
  font-size: 13px;
  line-height: 1.6;
  word-break: break-all;
}

.terminal-user {
  color: #3fb950;
  font-weight: 600;
}

.terminal-path {
  color: #58a6ff;
}

.terminal-dollar {
  color: #3fb950;
}

.terminal-cmd {
  color: #f0f6fc;
}

.terminal-sys-line {
  color: #d29922;
  font-size: 12px;
  padding-left: 2px;
  line-height: 1.5;
}

.terminal-pre {
  margin: 0;
  font-size: 12px;
  color: #8b949e;
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.5;
  padding-left: 2px;
}

.terminal-pre--args {
  color: #79c0ff;
  font-size: 11px;
}

/* WriteFile card inside terminal */

.terminal-write-box {
  border: 1px solid #30363d;
  border-radius: 8px;
  background: #161b22;
  overflow: hidden;
}

.terminal-write-head {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-bottom: 1px solid #30363d;
  font-size: 12px;
  color: #d2a8ff;
  font-weight: 600;
}

.terminal-write-head i {
  font-size: 13px;
}

.terminal-write-head--read {
  color: #58a6ff;
}

.terminal-write-box--read {
  border-color: #1f3a5f;
}

.terminal-write-detail {
  padding: 6px 12px;
  font-size: 12px;
  display: flex;
  gap: 8px;
  align-items: baseline;
}

.terminal-write-key {
  color: #8b949e;
  flex-shrink: 0;
}

.terminal-write-val {
  color: #79c0ff;
  word-break: break-all;
}

.terminal-write-ok {
  padding: 4px 12px 6px;
  font-size: 12px;
  color: #3fb950;
}

.terminal-write-ok i {
  margin-right: 4px;
}

/* Other tool */

.terminal-other-line {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
}

.terminal-other-icon { color: #d29922; }
.terminal-other-name { color: #d29922; font-weight: 600; }

/* --- AI Final Output (below terminal) --- */

.chat-ai-final {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.chat-ai-final-head {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #64748b;
  padding-left: 2px;
}

.chat-ai-final-head i {
  color: #2563eb;
  font-size: 13px;
}

.chat-ai-final-body {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 14px 16px;
  color: #1e293b;
  font-size: 14px;
  line-height: 1.7;
}

/* ===== Input ===== */

.agent-input {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 12px 14px;
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

.agent-pending__item small { color: #64748b; }
.agent-pending__item button { border: none; background: transparent; color: #64748b; padding: 0; }

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

.agent-upload-btn.disabled { opacity: 0.5; cursor: not-allowed; }
.agent-upload-btn input { display: none; }

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

.agent-send-btn:disabled { background: #cbd5e1; cursor: not-allowed; }

.agent-hint-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-top: 6px;
}

.agent-hint {
  margin: 0;
  font-size: 11px;
  color: #64748b;
}

.agent-hint-badges {
  display: flex;
  gap: 6px;
  flex-shrink: 0;
}

/* ===== Sidebar ===== */

.agent-side {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 0;
  overflow: hidden;
}

.agent-side__list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.agent-side__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
}

.agent-side h3 { margin: 0; font-size: 16px; }

.agent-side__hint {
  margin: 4px 0 0;
  font-size: 12px;
  color: #64748b;
}

.agent-side-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  border-radius: 8px;
  border: 1px solid #cbd5e1;
  background: #f8fafc;
  color: #334155;
  font-size: 12px;
  cursor: pointer;
  white-space: nowrap;
  flex-shrink: 0;
  transition: background 0.15s, border-color 0.15s;
}

.agent-side-btn:hover:not(:disabled) { background: #f1f5f9; border-color: #94a3b8; }
.agent-side-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.agent-side-btn--active {
  background: #fee2e2;
  border-color: #fca5a5;
  color: #dc2626;
}

.agent-side-btn--active:hover:not(:disabled) { background: #fecaca; }

.agent-side-zip-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  width: 100%;
  padding: 8px 12px;
  border-radius: 10px;
  border: 1px solid #cbd5e1;
  background: #f8fafc;
  color: #334155;
  font-size: 13px;
  cursor: pointer;
  flex-shrink: 0;
  transition: background 0.15s, border-color 0.15s;
}

.agent-side-zip-btn:hover:not(:disabled) { background: #f1f5f9; border-color: #94a3b8; }
.agent-side-zip-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.agent-side__select-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 10px;
  border-radius: 10px;
  background: #f1f5f9;
  font-size: 12px;
  color: #475569;
}

.agent-side-delete-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border-radius: 8px;
  border: 1px solid #fca5a5;
  background: #fee2e2;
  color: #dc2626;
  font-size: 12px;
  cursor: pointer;
  transition: background 0.15s;
}

.agent-side-delete-btn:hover:not(:disabled) { background: #fecaca; }
.agent-side-delete-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.agent-side__empty { font-size: 13px; color: #94a3b8; }

.agent-deliverable {
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 8px 10px;
  background: #f8fafc;
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
  user-select: none;
}

.agent-deliverable:hover:not(.agent-deliverable--loading) { background: #f1f5f9; border-color: #94a3b8; }
.agent-deliverable--selectable { cursor: pointer; }
.agent-deliverable--selected { background: #eff6ff; border-color: #93c5fd; }
.agent-deliverable--loading { opacity: 0.7; cursor: wait; }

.agent-deliverable__check { color: #2563eb; font-size: 15px; flex-shrink: 0; }

.agent-deliverable__body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.agent-deliverable__meta {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  font-size: 12px;
}

.agent-deliverable__meta strong {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.agent-deliverable small { color: #64748b; font-size: 11px; }
.agent-deliverable__action { color: #94a3b8; font-size: 13px; flex-shrink: 0; }

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
