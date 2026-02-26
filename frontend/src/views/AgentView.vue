<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AppToast from '../components/AppToast.vue'
import ChatRichTextRenderer from '../components/chat/ChatRichTextRenderer.vue'
import HomeHeaderBar from '../components/home/HomeHeaderBar.vue'
import HomeTaskEditorModal from '../components/home/HomeTaskEditorModal.vue'
import {
  cancelAgentSession,
  deleteAgentDeliverables,
  downloadDeliverableZip,
  fetchAgentAvailability,
  fetchAgentMessages,
  fetchAgentSession,
  fetchMyAgentSessions,
  sendAgentMessage,
} from '../api/agent'
import { getFileIconComponent } from '../composables/chat/attachmentUtils'
import { useAppToast } from '../composables/useAppToast'
import { useQuickTaskPublish } from '../composables/useQuickTaskPublish'
import { useAuthStore } from '../stores/auth'
import type {
  AgentAvailability,
  AgentDeliverable,
  AgentMessage,
  AgentMySessionItem,
  AgentSessionDetail,
} from '../types/api'
import { extractError } from '../utils/error'
import { formatChatTime, formatFull, nowLocal } from '../utils/time'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const appTitle = import.meta.env.VITE_APP_TITLE || '校园任务平台'
const sessionId = computed(() => String(route.params.sessionId || ''))
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

const isMobile = ref(typeof window !== 'undefined' ? window.innerWidth < 768 : false)
function checkMobile() { isMobile.value = window.innerWidth < 768 }

// ── Sidebar ──

const allSessions = ref<AgentMySessionItem[]>([])
const loadingSessions = ref(true)
const searchQuery = ref('')

const filteredSessions = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  if (!q) return allSessions.value
  return allSessions.value.filter(s => s.task_title.toLowerCase().includes(q))
})

async function loadSessions() {
  try {
    const result = await fetchMyAgentSessions({ page: 1, page_size: 100 })
    allSessions.value = result.items
  } catch { /* ignore */ }
  finally { loadingSessions.value = false }
}

function selectSession(s: AgentMySessionItem) {
  router.push(`/agent/${s.session_id}`)
}

function sessionStatusDot(s: AgentMySessionItem): string {
  if (s.status === 'running') return 'running'
  if (s.status === 'queued') return 'queued'
  if (s.task_status === 'completed') return 'done'
  if (s.task_status === 'canceled') return 'canceled'
  return ''
}

// ── Session & Messages ──

const availability = ref<AgentAvailability | null>(null)
const session = ref<AgentSessionDetail | null>(null)
const messages = ref<AgentMessage[]>([])

const loading = ref(true)
const sending = ref(false)
const canceling = ref(false)
const inputText = ref('')
const pendingFiles = ref<File[]>([])

const fileInputRef = ref<HTMLInputElement | null>(null)
const agentTextareaRef = ref<HTMLTextAreaElement | null>(null)
const chatScrollRef = ref<HTMLDivElement | null>(null)
const terminalStickToBottomMap = ref(new Map<number, boolean>())

function autoResizeTextarea() {
  nextTick(() => {
    const el = agentTextareaRef.value
    if (!el) return
    el.style.height = '0px'
    const height = Math.min(Math.max(el.scrollHeight, 38), 160)
    el.style.height = `${height}px`
    el.style.overflowY = el.scrollHeight > 160 ? 'auto' : 'hidden'
  })
}

watch(inputText, () => { autoResizeTextarea() }, { immediate: true })

let pollTimer: ReturnType<typeof setInterval> | null = null
let pollBusy = false
let lastMessageId = 0

const interactionLeft = computed(() => {
  if (!session.value) return 0
  return Math.max(0, session.value.max_interactions - session.value.interaction_count)
})

const queueAheadUsers = computed(() => {
  if (!session.value?.queue_waiting) return 0
  return Math.max(0, session.value.queue_ahead_users || 0)
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

const useDisabledComposeStyle = computed(() => {
  if (!session.value) return false
  if (session.value.status === 'running') return true
  if (isTaskTerminal.value) return true
  if (!session.value.can_send) return true
  if (session.value.interaction_count >= session.value.max_interactions) return true
  return false
})

const composePlaceholder = computed(() => {
  if (!session.value) return '描述你的目标、预期产物和约束条件...'
  if (session.value.task_status === 'canceled') return '任务已取消，会话已关闭。'
  if (session.value.task_status === 'completed') return '任务已完成，会话已关闭。'
  if (session.value.status === 'queued') return queueAheadUsers.value > 0 ? `排队中，前面还有 ${queueAheadUsers.value} 人。` : '排队中，请稍候...'
  if (session.value.status === 'running') return '代理正在执行中，可中断后继续输入。'
  if (!session.value.can_send) return '当前会话不可继续发送。'
  if (session.value.interaction_count >= session.value.max_interactions) return '交互次数已用尽。'
  return '描述你的目标、预期产物和约束条件...'
})

const canSendNow = computed(() => {
  if (sendDisabled.value) return false
  return Boolean(inputText.value.trim() || pendingFiles.value.length > 0)
})

const maxFileCount = computed(() => availability.value?.max_files ?? 5)
const maxFileSizeMb = computed(() => availability.value?.max_file_size_mb ?? 50)

// ── Deliverable Modal ──

const showDeliverableModal = ref(false)
const zippingAll = ref(false)
const deletingSelected = ref(false)
const selectedNames = ref<Set<string>>(new Set())

const deliverableCount = computed(() => session.value?.deliverables.length ?? 0)

// ── Tool Parsing ──

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

function isGlobTool(name: string | null): boolean {
  if (!name) return false
  return name.toLowerCase() === 'glob'
}

function isGrepTool(name: string | null): boolean {
  if (!name) return false
  return name.toLowerCase() === 'grep'
}

function isSearchWebTool(name: string | null): boolean {
  if (!name) return false
  const n = name.toLowerCase()
  return n === 'searchweb' || n === 'search_web' || n === 'websearch' || n === 'web_search'
}

function isFetchURLTool(name: string | null): boolean {
  if (!name) return false
  const n = name.toLowerCase()
  return n === 'fetchurl' || n === 'fetch_url'
}

function isSetTodoListTool(name: string | null): boolean {
  if (!name) return false
  const n = name.toLowerCase()
  return n === 'settodolist' || n === 'set_todo_list' || n === 'set_todolist'
}

function isTaskTool(name: string | null): boolean {
  if (!name) return false
  return name.toLowerCase() === 'task'
}

function isStrReplaceTool(name: string | null): boolean {
  if (!name) return false
  const n = name.toLowerCase()
  return n === 'strreplacefile' || n === 'str_replace_file' || n === 'str_replace' || n === 'str_replace_editor'
}

function isReadMediaTool(name: string | null): boolean {
  if (!name) return false
  const n = name.toLowerCase()
  return n === 'readmediafile' || n === 'read_media_file' || n === 'read_media'
}

function parseSearchResults(text: string): Array<{ title: string; url: string; summary: string }> {
  if (!text?.trim()) return []
  const results: Array<{ title: string; url: string; summary: string }> = []
  const blocks = text.split(/\n(?=Title:\s)/g)
  for (const block of blocks) {
    if (!block.trim()) continue
    const title = block.match(/^Title:\s*(.*)/m)?.[1]?.trim() || ''
    const url = block.match(/^URL:\s*(.*)/m)?.[1]?.trim() || ''
    const summaryMatch = block.match(/^Summary:\s*([\s\S]*?)(?=\nTitle:|\s*$)/m)
    const summary = summaryMatch?.[1]?.trim() || ''
    if (title || url) results.push({ title, url, summary })
  }
  return results
}

function parseFetchResult(text: string): { title: string; url: string; content: string } | null {
  if (!text?.trim()) return null
  const jsonStart = text.indexOf('{')
  if (jsonStart === -1) return null
  try {
    const jsonStr = text.substring(jsonStart)
    const obj = JSON.parse(jsonStr)
    if (obj && typeof obj === 'object') {
      return { title: obj.title || '', url: obj.url || '', content: (obj.markdown || obj.content || '').substring(0, 500) }
    }
  } catch {}
  return null
}

interface MediaOutputInfo {
  imagePath: string
  format: string
  size: string
  dimensions: string
  description: string
}

function parseMediaOutput(text: string): MediaOutputInfo {
  const imagePath = text.match(/<image\s+path="([^"]+)"/)?.[1] || ''
  const format = text.match(/\(([a-z]+\/[a-z]+)/i)?.[1] || ''
  const size = text.match(/,\s*([\d.]+\s*(?:bytes|KB|MB|GB))/i)?.[1] || ''
  const dimensions = text.match(/original size\s+(\d+x\d+)/i)?.[1] || ''
  const description = text.replace(/<image[\s\S]*?<\/image>/g, '').replace(/`[^`]+`/g, '').trim().split('.')[0] || ''
  return { imagePath, format, size, dimensions, description }
}

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

  let finalText = cleaned.trim()

  if (
    /['"]type['"]\s*:\s*['"]invalid_request_error['"]/.test(finalText) ||
    /['"]type['"]\s*:\s*['"]server_error['"]/.test(finalText) ||
    /['"]type['"]\s*:\s*['"]api_error['"]/.test(finalText)
  ) {
    const msgMatch = finalText.match(/['"]message['"]\s*:\s*['"](.*?)['"]/)
    finalText = msgMatch ? `[API Error] ${msgMatch[1]}` : '[API Error]'
  }

  return { systemLines, text: finalText }
}

const ANSI_ESCAPE_RE = /\x1B\[[0-?]*[ -/]*[@-~]/g

function stripAnsi(text: string): string {
  return text.replace(ANSI_ESCAPE_RE, '')
}

function startsWithErrorPrefix(text: string): boolean {
  if (!text) return false
  const firstContentLine = stripAnsi(text)
    .split('\n')
    .map(line => line.trimStart())
    .find(line => line.length > 0) || ''
  return firstContentLine.startsWith('ERROR:')
}

// ── Terminal ──

const terminalHostname = computed(() => {
  return appTitle.replace(/\s+/g, '-').replace(/[A-Za-z]/g, (c: string) => c.toLowerCase()) + '@agent'
})

interface TerminalEntry {
  id: number
  toolType: 'shell' | 'write-file' | 'read-file' | 'glob' | 'grep' | 'search-web' | 'fetch-url' | 'set-todo' | 'task' | 'str-replace' | 'read-media' | 'other'
  toolName: string
  command?: string
  promptPath?: string
  filePath?: string
  rawArgs?: string
  args?: Record<string, any>
  systemLines: string[]
  outputText: string
  hasErrorOutput: boolean
  pending: boolean
  success: boolean | null
}

const snapIndices = ref(new Map<number, number>())

function handleSnapScroll(event: Event, roundId: number, total: number) {
  const el = event.target as HTMLElement
  const idx = Math.min(Math.round(el.scrollTop / 64), total - 1)
  snapIndices.value = new Map(snapIndices.value.set(roundId, idx))
}

function isNearBottom(el: HTMLElement, threshold = 28): boolean {
  const distance = el.scrollHeight - (el.scrollTop + el.clientHeight)
  return distance <= threshold
}

function handleTerminalScroll(event: Event, roundId: number) {
  const el = event.target as HTMLElement
  const shouldStick = isNearBottom(el)
  terminalStickToBottomMap.value = new Map(terminalStickToBottomMap.value.set(roundId, shouldStick))
}

function scrollToBottomOnEnter() {
  nextTick(() => {
    const root = chatScrollRef.value
    if (!root) return

    root.scrollTo({ top: root.scrollHeight, behavior: 'auto' })

    root.querySelectorAll('.chat-ai-snap').forEach((el) => {
      const snapEl = el as HTMLElement
      snapEl.scrollTo({ top: snapEl.scrollHeight, behavior: 'auto' })
    })

    root.querySelectorAll('.terminal-body').forEach((el) => {
      const terminalEl = el as HTMLElement
      const roundId = Number(terminalEl.dataset.roundId || '0')
      terminalEl.scrollTo({ top: terminalEl.scrollHeight, behavior: 'auto' })
      terminalStickToBottomMap.value = new Map(terminalStickToBottomMap.value.set(roundId, true))
    })
  })
}

interface ConversationRound {
  id: number
  userMessage: AgentMessage | null
  aiIntermediate: AgentMessage[]
  entries: TerminalEntry[]
  aiFinal: AgentMessage | null
}

const TERMINAL_DEFAULT_CWD = '/workspace'
const TERMINAL_HOME_CWD = '/root'

function extractCdParseScope(command: string): string {
  let inSingle = false
  let inDouble = false
  let inBacktick = false
  let escaped = false

  for (let i = 0; i < command.length - 1; i++) {
    const ch = command[i]
    if (escaped) {
      escaped = false
      continue
    }
    if (ch === '\\') {
      escaped = true
      continue
    }
    if (!inDouble && !inBacktick && ch === "'") {
      inSingle = !inSingle
      continue
    }
    if (!inSingle && !inBacktick && ch === '"') {
      inDouble = !inDouble
      continue
    }
    if (!inSingle && !inDouble && ch === '`') {
      inBacktick = !inBacktick
      continue
    }
    if (inSingle || inDouble || inBacktick) continue

    if (ch === '<' && command[i + 1] === '<') {
      return command.slice(0, i)
    }
  }
  return command
}

function splitShellCommands(command: string): string[] {
  const source = extractCdParseScope(command)
  const parts: string[] = []
  let start = 0
  let inSingle = false
  let inDouble = false
  let inBacktick = false
  let escaped = false

  for (let i = 0; i < source.length; i++) {
    const ch = source[i]
    if (escaped) {
      escaped = false
      continue
    }
    if (ch === '\\') {
      escaped = true
      continue
    }
    if (!inDouble && !inBacktick && ch === "'") {
      inSingle = !inSingle
      continue
    }
    if (!inSingle && !inBacktick && ch === '"') {
      inDouble = !inDouble
      continue
    }
    if (!inSingle && !inDouble && ch === '`') {
      inBacktick = !inBacktick
      continue
    }
    if (inSingle || inDouble || inBacktick) continue

    const next = source[i + 1] || ''
    if ((ch === '&' && next === '&') || (ch === '|' && next === '|')) {
      const piece = source.slice(start, i).trim()
      if (piece) parts.push(piece)
      i++
      start = i + 1
      continue
    }
    if (ch === ';') {
      const piece = source.slice(start, i).trim()
      if (piece) parts.push(piece)
      start = i + 1
    }
  }

  const last = source.slice(start).trim()
  if (last) parts.push(last)
  return parts
}

function parseCdTarget(commandPart: string): string | null {
  const trimmed = commandPart.trim()
  const match = trimmed.match(/^(?:builtin\s+)?cd(?:\s+--)?(?:\s+([\s\S]*))?$/)
  if (!match) return null
  const raw = (match[1] || '').trim()
  if (!raw) return ''

  const first = raw.match(/^("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*'|[^\s]+)/)
  if (!first) return ''
  let token = first[1]

  if ((token.startsWith('"') && token.endsWith('"')) || (token.startsWith("'") && token.endsWith("'"))) {
    token = token.slice(1, -1)
  }

  return token
}

function normalizePosixPath(path: string): string {
  const parts = path.split('/').filter(Boolean)
  const out: string[] = []
  for (const part of parts) {
    if (part === '.') continue
    if (part === '..') {
      out.pop()
      continue
    }
    out.push(part)
  }
  return '/' + out.join('/')
}

function resolveCdTarget(cwd: string, prevCwd: string, rawTarget: string): { cwd: string, prevCwd: string } {
  let target = rawTarget.trim()
  if (!target) target = TERMINAL_HOME_CWD
  else if (target === '~') target = TERMINAL_HOME_CWD
  else if (target.startsWith('~/')) target = `${TERMINAL_HOME_CWD}/${target.slice(2)}`
  else if (target === '-') target = prevCwd
  else if (!target.startsWith('/')) target = `${cwd}/${target}`

  return {
    cwd: normalizePosixPath(target),
    prevCwd: cwd,
  }
}

function hasCdFailure(entry: TerminalEntry): boolean {
  const combined = [entry.outputText, ...entry.systemLines].join('\n')
  return /(?:^|\n)\s*(?:bash:\s*)?cd:\s.*(?:no such file|not a directory|can't cd|too many arguments|permission denied)/i.test(combined)
}

function inferNextCwd(entry: TerminalEntry, cwd: string, prevCwd: string): { cwd: string, prevCwd: string } {
  if (entry.toolType !== 'shell' || !entry.command) return { cwd, prevCwd }
  if (hasCdFailure(entry)) return { cwd, prevCwd }

  const parts = splitShellCommands(entry.command)
  if (!parts.length) return { cwd, prevCwd }

  let nextCwd = cwd
  let nextPrevCwd = prevCwd
  for (const part of parts) {
    const target = parseCdTarget(part)
    if (target === null) continue
    const next = resolveCdTarget(nextCwd, nextPrevCwd, target)
    nextCwd = next.cwd
    nextPrevCwd = next.prevCwd
  }
  return { cwd: nextCwd, prevCwd: nextPrevCwd }
}

const conversationRounds = computed<ConversationRound[]>(() => {
  const rounds: ConversationRound[] = []
  const msgs = messages.value
  let runningCwd = TERMINAL_DEFAULT_CWD
  let runningPrevCwd = TERMINAL_DEFAULT_CWD

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
        entry = { id: msg.id, toolType: 'shell', toolName, command: args.command || '', promptPath: runningCwd, systemLines: [], outputText: '', hasErrorOutput: false, pending: true, success: null }
      } else if (isWriteFileTool(msg.tool_name)) {
        entry = { id: msg.id, toolType: 'write-file', toolName, filePath: args.path || '', systemLines: [], outputText: '', hasErrorOutput: false, pending: true, success: null }
      } else if (isReadFileTool(msg.tool_name)) {
        entry = { id: msg.id, toolType: 'read-file', toolName, filePath: args.path || '', systemLines: [], outputText: '', hasErrorOutput: false, pending: true, success: null }
      } else if (isGlobTool(msg.tool_name)) {
        entry = { id: msg.id, toolType: 'glob', toolName, args, systemLines: [], outputText: '', hasErrorOutput: false, pending: true, success: null }
      } else if (isGrepTool(msg.tool_name)) {
        entry = { id: msg.id, toolType: 'grep', toolName, args, systemLines: [], outputText: '', hasErrorOutput: false, pending: true, success: null }
      } else if (isSearchWebTool(msg.tool_name)) {
        entry = { id: msg.id, toolType: 'search-web', toolName, args, systemLines: [], outputText: '', hasErrorOutput: false, pending: true, success: null }
      } else if (isFetchURLTool(msg.tool_name)) {
        entry = { id: msg.id, toolType: 'fetch-url', toolName, args, systemLines: [], outputText: '', hasErrorOutput: false, pending: true, success: null }
      } else if (isSetTodoListTool(msg.tool_name)) {
        entry = { id: msg.id, toolType: 'set-todo', toolName, args, systemLines: [], outputText: '', hasErrorOutput: false, pending: true, success: null }
      } else if (isTaskTool(msg.tool_name)) {
        entry = { id: msg.id, toolType: 'task', toolName, args, systemLines: [], outputText: '', hasErrorOutput: false, pending: true, success: null }
      } else if (isStrReplaceTool(msg.tool_name)) {
        entry = { id: msg.id, toolType: 'str-replace', toolName, filePath: args.path || '', args, systemLines: [], outputText: '', hasErrorOutput: false, pending: true, success: null }
      } else if (isReadMediaTool(msg.tool_name)) {
        entry = { id: msg.id, toolType: 'read-media', toolName, filePath: args.path || '', args, systemLines: [], outputText: '', hasErrorOutput: false, pending: true, success: null }
      } else {
        let pretty = msg.tool_arguments || ''
        try { pretty = JSON.stringify(JSON.parse(pretty), null, 2) } catch {}
        entry = { id: msg.id, toolType: 'other', toolName, rawArgs: pretty, systemLines: [], outputText: '', hasErrorOutput: false, pending: true, success: null }
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
        const systemHasError = systemLines.some(line => startsWithErrorPrefix(line))
        entry.hasErrorOutput = startsWithErrorPrefix(text) || systemHasError
        if (entry.toolType === 'shell') {
          const kept: string[] = []
          for (const line of systemLines) {
            if (startsWithErrorPrefix(line)) {
              entry.success = false
              kept.push(line)
            } else if (/command executed successfully/i.test(line)) {
              entry.success = true
            } else if (/\berror\b/i.test(line)) {
              entry.success = false
              kept.push(line)
            } else {
              kept.push(line)
            }
          }
          entry.systemLines = kept
          if (entry.hasErrorOutput) entry.success = false
          if (entry.success === null) entry.success = true
        } else {
          entry.systemLines = systemLines
        }
        entry.outputText = text
        entry.pending = false
      }
      const nextState = inferNextCwd(entry, runningCwd, runningPrevCwd)
      runningCwd = nextState.cwd
      runningPrevCwd = nextState.prevCwd
      round.entries.push(entry)
    }

    rounds.push(round)
  }
  return rounds
})

// ── Skeleton & Braille ──

const showPendingRoundSkeleton = computed(() => {
  if (!session.value || session.value.status !== 'running') return false
  const rounds = conversationRounds.value
  if (rounds.length === 0) return false
  const last = rounds[rounds.length - 1]
  return !!last.userMessage && last.aiIntermediate.length === 0 && last.entries.length === 0 && !last.aiFinal
})

const showSetupSkeleton = computed(() => {
  if (!showPendingRoundSkeleton.value) return false
  return conversationRounds.value.length === 1
})

const brailleFrames = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
const brailleIndex = ref(0)
let brailleTimer: ReturnType<typeof setInterval> | null = null

const brailleChar = computed(() => brailleFrames[brailleIndex.value])

watch(showSetupSkeleton, (show) => {
  if (show) {
    brailleTimer = setInterval(() => {
      brailleIndex.value = (brailleIndex.value + 1) % brailleFrames.length
    }, 80)
  } else if (brailleTimer) {
    clearInterval(brailleTimer)
    brailleTimer = null
  }
})

// ── Last round glow detection ──

function isLastRound(roundId: number): boolean {
  const rounds = conversationRounds.value
  return rounds.length > 0 && rounds[rounds.length - 1].id === roundId
}

// ── Data Loading ──

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
  } catch { /* ignore */ }
  finally { pollBusy = false }
}

function startPolling() {
  stopPolling()
  pollTimer = setInterval(() => { pollSession().catch(() => {}) }, 2000)
}

function stopPolling() {
  if (!pollTimer) return
  clearInterval(pollTimer)
  pollTimer = null
}

async function bootstrap() {
  if (!sessionId.value) {
    loading.value = false
    return
  }
  resetViewState()
  try {
    await Promise.all([refreshAvailability(), refreshSession()])
    await refreshMessages()
  } catch (error) {
    showToast(extractError(error, '加载代理会话失败'), 'error')
    router.push('/agent')
  } finally {
    loading.value = false
    scrollToBottomOnEnter()
  }
}

// ── File Handling ──

function formatFileSize(size: number) {
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / (1024 * 1024)).toFixed(1)} MB`
}

function getAgentFileIcon(name: string, mime = '') {
  return getFileIconComponent(mime, name)
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

// ── Send & Cancel ──

async function handleSend() {
  if (!canSendNow.value || !session.value) return
  sending.value = true
  try {
    const result = await sendAgentMessage(session.value.session_id, {
      content: inputText.value.trim(),
      files: pendingFiles.value,
    })
    inputText.value = ''
    pendingFiles.value = []
    if (fileInputRef.value) fileInputRef.value.value = ''
    if (result.queue_ahead_users > 0) {
      showToast(`排队中，前面还有 ${result.queue_ahead_users} 人`, 'warning')
    }
    await Promise.all([pollSession(), refreshAvailability()])
  } catch (error) {
    showToast(extractError(error, '发送失败'), 'error')
  } finally {
    sending.value = false
  }
}

async function handleCancel() {
  if (!session.value || canceling.value) return
  canceling.value = true
  try {
    const result = await cancelAgentSession(session.value.session_id)
    await pollSession()
    showToast(result.canceled ? '已请求中断' : '当前没有可中断的运行任务', result.canceled ? 'success' : 'warning')
  } catch (error: any) {
    const status = error?.response?.status
    if (status === 404 || status === 405) {
      showToast('后端暂不支持中断功能', 'warning')
    } else {
      showToast(extractError(error, '中断失败'), 'error')
    }
  } finally {
    canceling.value = false
  }
}

// ── Deliverable Actions ──

async function handleDownloadZip() {
  if (!session.value) return
  zippingAll.value = true
  try {
    const names = selectedNames.value.size > 0
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

function toggleSelect(name: string) {
  const next = new Set(selectedNames.value)
  if (next.has(name)) next.delete(name)
  else next.add(name)
  selectedNames.value = next
}

function handleDeliverableClick(item: AgentDeliverable) {
  toggleSelect(item.name)
}

// ── Watchers ──

watch(
  () => messages.value.length,
  () => {
    nextTick(() => {
      if (!chatScrollRef.value) return

      // Process area should always animate to the newest generation snippet.
      chatScrollRef.value.querySelectorAll('.chat-ai-snap').forEach((el) => {
        const snapEl = el as HTMLElement
        snapEl.scrollTo({ top: snapEl.scrollHeight, behavior: 'smooth' })
      })

      // Terminal follows only when user is already near the bottom.
      chatScrollRef.value.querySelectorAll('.terminal-body').forEach((el) => {
        const terminalEl = el as HTMLElement
        const roundId = Number(terminalEl.dataset.roundId || '0')
        const shouldStick = terminalStickToBottomMap.value.get(roundId) ?? isNearBottom(terminalEl)
        if (!shouldStick) return
        terminalEl.scrollTo({ top: terminalEl.scrollHeight, behavior: 'smooth' })
        terminalStickToBottomMap.value = new Map(terminalStickToBottomMap.value.set(roundId, true))
      })
    })
  },
)

watch(
  () => sessionId.value,
  () => { bootstrap().catch(() => {}) },
  { immediate: true },
)

let sessionPollTimer: ReturnType<typeof setInterval> | null = null

onMounted(() => {
  checkMobile()
  window.addEventListener('resize', checkMobile)
  startPolling()
  loadSessions()
  sessionPollTimer = setInterval(() => { loadSessions() }, 10000)
})

onUnmounted(() => {
  window.removeEventListener('resize', checkMobile)
  stopPolling()
  if (brailleTimer) clearInterval(brailleTimer)
  if (sessionPollTimer) clearInterval(sessionPollTimer)
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

    <div class="agent-page">
      <AppToast :toast="toast" @dismiss="clearToast" />

      <!-- ── Left Sidebar ── -->
      <aside class="agent-sidebar" :class="{ 'sidebar-hidden': sessionId && isMobile }">
        <div class="sidebar-header">
          <h1 class="sidebar-title">代理任务</h1>
          <div class="sidebar-search">
            <i class="fa-solid fa-search search-icon"></i>
            <input v-model="searchQuery" type="text" placeholder="搜索..." class="search-input" />
          </div>
        </div>
        <div class="session-list">
          <button
            v-for="s in filteredSessions"
            :key="s.session_id"
            class="session-item"
            :class="{ active: s.session_id === sessionId }"
            @click="selectSession(s)"
          >
            <div class="session-item-top">
              <span class="session-item-title">{{ s.task_title }}</span>
              <span class="session-item-time">{{ formatChatTime(s.last_activity_at) }}</span>
            </div>
            <div class="session-item-bottom">
              <span class="session-item-preview">已用 {{ s.interaction_count }}/{{ s.max_interactions }}</span>
              <span v-if="sessionStatusDot(s) === 'running'" class="session-dot session-dot--running"></span>
              <span v-else-if="sessionStatusDot(s) === 'queued'" class="session-dot session-dot--queued"></span>
              <span v-else-if="sessionStatusDot(s) === 'done'" class="session-dot session-dot--done"></span>
              <span v-else-if="sessionStatusDot(s) === 'canceled'" class="session-dot session-dot--canceled"></span>
            </div>
          </button>

          <div v-if="loadingSessions" class="session-empty">
            <i class="fa-solid fa-spinner fa-spin"></i> 加载中...
          </div>
          <div v-else-if="filteredSessions.length === 0" class="session-empty">
            <i class="fa-solid fa-robot session-empty-icon"></i>
            <p>暂无代理任务</p>
          </div>
        </div>
      </aside>

      <!-- ── Right Main ── -->
      <main class="agent-main" :class="{ 'main-hidden': !sessionId && isMobile }">
        <div v-if="!sessionId" class="agent-empty-state">
          <i class="fa-solid fa-robot agent-empty-icon"></i>
          <p>从左侧选择一个代理会话</p>
        </div>

        <template v-else>
          <!-- Header -->
          <div class="agent-header">
            <div class="header-left">
              <button v-if="isMobile" class="icon-btn back-btn" @click="router.push('/agent')">
                <i class="fa-solid fa-arrow-left"></i>
              </button>
              <div class="header-avatar">
                <i class="fa-solid fa-robot"></i>
              </div>
              <div>
                <h2 class="header-title">{{ session?.task_title || '代理会话' }}</h2>
                <p class="header-status" :class="{ 'status-running': session?.status === 'running', 'status-queued': session?.status === 'queued' }">
                  {{ session?.status === 'running' ? '正在执行...' : session?.status === 'queued' ? (queueAheadUsers > 0 ? `排队中，前面还有 ${queueAheadUsers} 人` : '排队中...') : isTaskTerminal ? (session?.task_status === 'completed' ? '已完成' : '已取消') : '空闲' }}
                </p>
              </div>
            </div>
            <div class="header-actions">
              <button class="icon-btn" title="交付文件" @click="showDeliverableModal = true">
                <i class="fa-solid fa-paperclip"></i>
                <span v-if="deliverableCount > 0" class="att-count-badge">{{ deliverableCount }}</span>
              </button>
            </div>
          </div>

          <!-- Chat Scroll -->
          <div ref="chatScrollRef" class="chat-scroll">
            <div v-if="loading" class="chat-empty">加载中...</div>
            <div v-else-if="conversationRounds.length === 0 && !showSetupSkeleton" class="chat-empty">还没有消息，先发送你的需求吧。</div>

            <div v-for="(round, roundIndex) in conversationRounds" :key="round.id" class="chat-round">
              <!-- User message -->
              <div v-if="round.userMessage" class="chat-bubble-row chat-bubble-row--right">
                <div class="chat-bubble chat-bubble--user">
                  <ChatRichTextRenderer :content="round.userMessage.content || ''" />
                  <div v-if="round.userMessage.attachments?.length" class="chat-bubble-files">
                    <span v-for="att in round.userMessage.attachments" :key="att.stored_name" class="chat-file-chip">
                      <component :is="getAgentFileIcon(att.name)" :size="14" class="agent-file-icon" />
                      {{ att.name }}
                      <small>({{ formatFileSize(att.size) }})</small>
                    </span>
                  </div>
                </div>
              </div>

              <!-- Skeleton: shown only on last round when waiting for first AI response -->
              <template v-if="showPendingRoundSkeleton && roundIndex === conversationRounds.length - 1">
                <div class="chat-ai-snap-wrap">
                  <div class="chat-ai-snap-outer chat-ai-snap-outer--glow">
                    <div class="chat-ai-snap skeleton-snap">
                      <div class="skeleton-lines">
                        <div class="skeleton-line skeleton-line--long"></div>
                        <div class="skeleton-line skeleton-line--short"></div>
                      </div>
                    </div>
                  </div>
                </div>

                <div v-if="showSetupSkeleton" class="terminal">
                  <div class="terminal-titlebar">
                    <div class="terminal-dots">
                      <span class="terminal-dot terminal-dot--red"></span>
                      <span class="terminal-dot terminal-dot--yellow"></span>
                      <span class="terminal-dot terminal-dot--green"></span>
                    </div>
                    <span class="terminal-hostname">{{ terminalHostname }}</span>
                  </div>
                  <div class="terminal-body">
                    <div class="terminal-setup">
                      <span class="terminal-setup-text">Setting up the environment</span>
                      <span class="terminal-setup-spinner">{{ brailleChar }}</span>
                    </div>
                  </div>
                </div>
              </template>

              <!-- AI Intermediate (snap-scroll) -->
              <div v-if="round.aiIntermediate.length" class="chat-ai-snap-wrap">
                <div
                  class="chat-ai-snap-outer"
                  :class="{ 'chat-ai-snap-outer--glow': session?.status === 'running' && isLastRound(round.id) }"
                >
                  <div class="chat-ai-snap" @scroll="handleSnapScroll($event, round.id, round.aiIntermediate.length)">
                    <div v-for="msg in round.aiIntermediate" :key="msg.id" class="chat-ai-snap-item">
                      <span>{{ msg.content }}</span>
                    </div>
                  </div>
                  <span class="chat-ai-snap-idx">{{ (snapIndices.get(round.id) ?? (round.aiIntermediate.length - 1)) + 1 }}/{{ round.aiIntermediate.length }}</span>
                </div>
              </div>

              <!-- Terminal -->
              <div v-if="round.entries.length" class="terminal">
                <div class="terminal-titlebar">
                  <div class="terminal-dots">
                    <span class="terminal-dot terminal-dot--red"></span>
                    <span class="terminal-dot terminal-dot--yellow"></span>
                    <span class="terminal-dot terminal-dot--green"></span>
                  </div>
                  <span class="terminal-hostname">{{ terminalHostname }}</span>
                </div>
                <div class="terminal-body" :data-round-id="round.id" @scroll="handleTerminalScroll($event, round.id)">
                  <template v-for="entry in round.entries" :key="entry.id">
                    <div v-if="entry.toolType === 'shell'" class="terminal-entry">
                      <div class="terminal-prompt-line">
                        <span v-if="entry.success === true" class="terminal-status-icon terminal-status-icon--ok"><i class="fa-solid fa-check"></i></span>
                        <span v-else-if="entry.success === false" class="terminal-status-icon terminal-status-icon--err"><i class="fa-solid fa-xmark"></i></span>
                        <span class="terminal-user">{{ terminalHostname }}</span>:<span class="terminal-path">{{ entry.promptPath || TERMINAL_DEFAULT_CWD }}</span><span class="terminal-dollar">$</span> <span class="terminal-cmd">{{ entry.command }}</span>
                      </div>
                      <div v-for="(line, idx) in entry.systemLines" :key="'s'+idx" class="terminal-sys-line">{{ line }}</div>
                      <pre v-if="entry.outputText" class="terminal-pre" :class="{ 'terminal-pre--error': entry.hasErrorOutput }">{{ entry.outputText }}</pre>
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
                        <div
                          v-for="(line, idx) in entry.systemLines"
                          :key="'s'+idx"
                          class="terminal-write-ok"
                          :class="{ 'terminal-write-ok--error': startsWithErrorPrefix(line) || entry.hasErrorOutput }"
                        >
                          <i :class="(startsWithErrorPrefix(line) || entry.hasErrorOutput) ? 'fa-solid fa-xmark' : 'fa-solid fa-check'"></i> {{ line }}
                        </div>
                      </div>
                      <pre v-if="entry.outputText" class="terminal-pre" :class="{ 'terminal-pre--error': entry.hasErrorOutput }">{{ entry.outputText }}</pre>
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
                        <div
                          v-for="(line, idx) in entry.systemLines"
                          :key="'s'+idx"
                          class="terminal-write-ok"
                          :class="{ 'terminal-write-ok--error': startsWithErrorPrefix(line) || entry.hasErrorOutput }"
                        >
                          <i :class="(startsWithErrorPrefix(line) || entry.hasErrorOutput) ? 'fa-solid fa-xmark' : 'fa-solid fa-check'"></i> {{ line }}
                        </div>
                        <div v-if="entry.outputText" class="terminal-readfile-output">
                          <div class="terminal-readfile-output-label">
                            <i class="fa-solid fa-align-left"></i>
                            <span>文件内容</span>
                          </div>
                          <pre class="terminal-readfile-pre" :class="{ 'terminal-readfile-pre--error': entry.hasErrorOutput }">{{ entry.outputText }}</pre>
                        </div>
                        <div v-if="entry.pending && session?.status === 'running'" class="terminal-task-pending">
                          <span class="terminal-blink">█</span>
                        </div>
                      </div>
                    </div>

                    <div v-else-if="entry.toolType === 'glob'" class="terminal-entry">
                      <div class="terminal-tool-box terminal-tool-box--glob">
                        <div class="terminal-tool-head terminal-tool-head--glob">
                          <i class="fa-solid fa-folder-tree"></i>
                          <span>Glob</span>
                        </div>
                        <div class="terminal-tool-detail">
                          <span class="terminal-tool-key">pattern</span>
                          <span class="terminal-tool-val terminal-tool-val--highlight">{{ entry.args?.pattern }}</span>
                        </div>
                        <div v-if="!entry.pending && entry.outputText" class="terminal-tool-body">
                          <template v-for="(line, idx) in entry.outputText.split('\n')" :key="idx">
                            <div v-if="line.trim()" :class="(/^Found \d|^No match/i).test(line) ? 'terminal-tool-info' : 'terminal-tool-file'">
                              <i :class="(/^Found \d|^No match/i).test(line) ? 'fa-solid fa-circle-info' : 'fa-regular fa-file-code'"></i>
                              <span>{{ line }}</span>
                            </div>
                          </template>
                        </div>
                      </div>
                      <div v-if="entry.pending && session?.status === 'running'" class="terminal-status">
                        <span class="terminal-blink">█</span>
                      </div>
                    </div>

                    <div v-else-if="entry.toolType === 'grep'" class="terminal-entry">
                      <div class="terminal-tool-box terminal-tool-box--grep">
                        <div class="terminal-tool-head terminal-tool-head--grep">
                          <i class="fa-solid fa-magnifying-glass-code"></i>
                          <span>Grep</span>
                        </div>
                        <div class="terminal-tool-detail">
                          <span class="terminal-tool-key">pattern</span>
                          <span class="terminal-tool-val terminal-tool-val--highlight">{{ entry.args?.pattern }}</span>
                        </div>
                        <div v-if="entry.args?.path" class="terminal-tool-detail">
                          <span class="terminal-tool-key">path</span>
                          <span class="terminal-tool-val">{{ entry.args.path }}</span>
                        </div>
                        <div v-if="entry.args?.output_mode" class="terminal-tool-detail">
                          <span class="terminal-tool-key">mode</span>
                          <span class="terminal-tool-val">{{ entry.args.output_mode }}</span>
                        </div>
                        <div v-if="!entry.pending && entry.outputText" class="terminal-tool-body">
                          <template v-for="(line, idx) in entry.outputText.split('\n')" :key="idx">
                            <div v-if="line.trim()" :class="(/^No match/i).test(line) ? 'terminal-tool-info' : 'terminal-tool-file'">
                              <i :class="(/^No match/i).test(line) ? 'fa-solid fa-circle-info' : 'fa-solid fa-font'"></i>
                              <span>{{ line }}</span>
                            </div>
                          </template>
                        </div>
                      </div>
                      <div v-if="entry.pending && session?.status === 'running'" class="terminal-status">
                        <span class="terminal-blink">█</span>
                      </div>
                    </div>

                    <div v-else-if="entry.toolType === 'search-web'" class="terminal-entry">
                      <div class="terminal-tool-box terminal-tool-box--search-web">
                        <div class="terminal-tool-head terminal-tool-head--search-web">
                          <i class="fa-solid fa-globe"></i>
                          <span>SearchWeb</span>
                        </div>
                        <div class="terminal-tool-detail">
                          <span class="terminal-tool-key">query</span>
                          <span class="terminal-tool-val terminal-tool-val--highlight">{{ entry.args?.query }}</span>
                        </div>
                        <template v-if="!entry.pending && entry.outputText">
                          <template v-for="results in [parseSearchResults(entry.outputText)]" :key="0">
                            <div v-if="results.length" class="terminal-tool-body">
                              <div v-for="(result, idx) in results" :key="idx" class="terminal-search-item">
                                <div class="terminal-search-title">
                                  <i class="fa-solid fa-arrow-up-right-from-square"></i>
                                  <a v-if="result.url" :href="result.url" target="_blank" rel="noopener">{{ result.title || result.url }}</a>
                                  <span v-else>{{ result.title }}</span>
                                </div>
                                <div v-if="result.url" class="terminal-search-url">{{ result.url }}</div>
                                <div v-if="result.summary" class="terminal-search-summary">{{ result.summary }}</div>
                              </div>
                            </div>
                            <pre v-else class="terminal-pre terminal-pre--incard" :class="{ 'terminal-pre--error': entry.hasErrorOutput }">{{ entry.outputText }}</pre>
                          </template>
                        </template>
                      </div>
                      <div v-if="entry.pending && session?.status === 'running'" class="terminal-status">
                        <span class="terminal-blink">█</span>
                      </div>
                    </div>

                    <div v-else-if="entry.toolType === 'fetch-url'" class="terminal-entry">
                      <div class="terminal-tool-box terminal-tool-box--fetch-url">
                        <div class="terminal-tool-head terminal-tool-head--fetch-url">
                          <i class="fa-solid fa-link"></i>
                          <span>FetchURL</span>
                        </div>
                        <div class="terminal-tool-detail">
                          <span class="terminal-tool-key">url</span>
                          <a class="terminal-tool-link" :href="entry.args?.url" target="_blank" rel="noopener">{{ entry.args?.url }}</a>
                        </div>
                        <template v-if="!entry.pending && entry.outputText">
                          <template v-for="fetchData in [parseFetchResult(entry.outputText)]" :key="0">
                            <div v-if="fetchData" class="terminal-fetch-preview">
                              <div v-if="fetchData.title" class="terminal-fetch-title">{{ fetchData.title }}</div>
                              <div v-if="fetchData.content" class="terminal-fetch-content">{{ fetchData.content }}</div>
                            </div>
                            <pre v-else class="terminal-pre terminal-pre--incard" :class="{ 'terminal-pre--error': entry.hasErrorOutput }">{{ entry.outputText }}</pre>
                          </template>
                        </template>
                      </div>
                      <div v-if="entry.pending && session?.status === 'running'" class="terminal-status">
                        <span class="terminal-blink">█</span>
                      </div>
                    </div>

                    <div v-else-if="entry.toolType === 'set-todo'" class="terminal-entry">
                      <div class="terminal-tool-box terminal-tool-box--todo">
                        <div class="terminal-tool-head terminal-tool-head--todo">
                          <i class="fa-solid fa-list-check"></i>
                          <span>SetTodoList</span>
                        </div>
                        <div v-if="entry.args?.todos?.length" class="terminal-todo-list">
                          <div v-for="(todo, idx) in entry.args.todos" :key="idx" class="terminal-todo-item">
                            <i :class="todo.status === 'done' ? 'fa-solid fa-circle-check terminal-todo--done' : todo.status === 'in_progress' ? 'fa-solid fa-circle-dot terminal-todo--progress' : 'fa-regular fa-circle terminal-todo--pending'"></i>
                            <span class="terminal-todo-title" :class="{ 'terminal-todo-title--done': todo.status === 'done' }">{{ todo.title }}</span>
                            <span class="terminal-todo-badge" :class="'terminal-todo-badge--' + (todo.status || 'pending')">{{ todo.status }}</span>
                          </div>
                        </div>
                        <div v-if="!entry.pending && entry.outputText" class="terminal-tool-ok-line" :class="{ 'terminal-tool-ok-line--error': entry.hasErrorOutput }">
                          <i :class="entry.hasErrorOutput ? 'fa-solid fa-xmark' : 'fa-solid fa-check'"></i> {{ entry.outputText }}
                        </div>
                      </div>
                      <div v-if="entry.pending && session?.status === 'running'" class="terminal-status">
                        <span class="terminal-blink">█</span>
                      </div>
                    </div>

                    <div v-else-if="entry.toolType === 'task'" class="terminal-entry">
                      <div class="terminal-tool-box terminal-tool-box--task">
                        <div class="terminal-tool-head terminal-tool-head--task">
                          <i class="fa-solid fa-robot"></i>
                          <span>Task</span>
                          <span v-if="entry.args?.subagent_name" class="terminal-task-badge">{{ entry.args.subagent_name }}</span>
                        </div>
                        <div v-if="entry.args?.description" class="terminal-tool-detail">
                          <span class="terminal-tool-key">desc</span>
                          <span class="terminal-tool-val">{{ entry.args.description }}</span>
                        </div>
                        <div v-if="entry.outputText" class="terminal-task-output">
                          <div class="terminal-task-output-label">
                            <i class="fa-solid fa-comment-dots"></i>
                            <span>子代理输出</span>
                          </div>
                          <pre class="terminal-task-pre" :class="{ 'terminal-task-pre--error': entry.hasErrorOutput }">{{ entry.outputText }}</pre>
                        </div>
                        <div v-if="entry.pending && session?.status === 'running'" class="terminal-task-pending">
                          <span class="terminal-blink">█</span>
                        </div>
                      </div>
                    </div>

                    <div v-else-if="entry.toolType === 'str-replace'" class="terminal-entry">
                      <div class="terminal-tool-box terminal-tool-box--str-replace">
                        <div class="terminal-tool-head terminal-tool-head--str-replace">
                          <i class="fa-solid fa-pen-to-square"></i>
                          <span>StrReplaceFile</span>
                        </div>
                        <div class="terminal-tool-detail">
                          <span class="terminal-tool-key">path</span>
                          <span class="terminal-tool-val">{{ entry.filePath }}</span>
                        </div>
                        <div v-if="entry.args?.edit" class="terminal-diff">
                          <div class="terminal-diff-old">
                            <span class="terminal-diff-label">-</span>
                            <code>{{ entry.args.edit.old }}</code>
                          </div>
                          <div class="terminal-diff-new">
                            <span class="terminal-diff-label">+</span>
                            <code>{{ entry.args.edit.new }}</code>
                          </div>
                        </div>
                        <div v-if="!entry.pending && entry.outputText" class="terminal-tool-ok-line" :class="{ 'terminal-tool-ok-line--error': entry.hasErrorOutput }">
                          <i :class="entry.hasErrorOutput ? 'fa-solid fa-xmark' : 'fa-solid fa-check'"></i> {{ entry.outputText }}
                        </div>
                      </div>
                      <div v-if="entry.pending && session?.status === 'running'" class="terminal-status">
                        <span class="terminal-blink">█</span>
                      </div>
                    </div>

                    <div v-else-if="entry.toolType === 'read-media'" class="terminal-entry">
                      <template v-for="media in [parseMediaOutput(entry.outputText)]" :key="0">
                        <div class="terminal-tool-box terminal-tool-box--read-media">
                          <div class="terminal-tool-head terminal-tool-head--read-media">
                            <i class="fa-solid fa-image"></i>
                            <span>ReadMediaFile</span>
                          </div>
                          <div class="terminal-tool-detail">
                            <i
                              v-if="!entry.pending && !entry.hasErrorOutput && entry.outputText"
                              class="fa-solid fa-check terminal-readmedia-path-ok"
                            ></i>
                            <span class="terminal-tool-key">path</span>
                            <span class="terminal-tool-val">{{ entry.filePath }}</span>
                          </div>
                          <div
                            v-if="!entry.pending && entry.outputText && (media.dimensions || media.format || media.size)"
                            class="terminal-media-preview"
                          >
                            <div class="terminal-media-meta">
                              <div v-if="media.dimensions" class="terminal-media-chip">
                                <i class="fa-solid fa-expand"></i>
                                <span>{{ media.dimensions }}</span>
                              </div>
                              <div v-if="media.format" class="terminal-media-chip">
                                <i class="fa-solid fa-file-image"></i>
                                <span>{{ media.format }}</span>
                              </div>
                              <div v-if="media.size" class="terminal-media-chip">
                                <i class="fa-solid fa-weight-hanging"></i>
                                <span>{{ media.size }}</span>
                              </div>
                            </div>
                          </div>
                          <div v-if="entry.pending && session?.status === 'running'" class="terminal-task-pending">
                            <span class="terminal-blink">█</span>
                          </div>
                        </div>
                      </template>
                    </div>

                    <div v-else class="terminal-entry">
                      <div class="terminal-other-line">
                        <span class="terminal-other-icon">⚙</span>
                        <span class="terminal-other-name">{{ entry.toolName }}</span>
                      </div>
                      <pre v-if="entry.rawArgs" class="terminal-pre terminal-pre--args">{{ entry.rawArgs }}</pre>
                      <div v-for="(line, idx) in entry.systemLines" :key="'s'+idx" class="terminal-sys-line">{{ line }}</div>
                      <pre v-if="entry.outputText" class="terminal-pre" :class="{ 'terminal-pre--error': entry.hasErrorOutput }">{{ entry.outputText }}</pre>
                      <div v-if="entry.pending && session?.status === 'running'" class="terminal-status">
                        <span class="terminal-blink">█</span>
                      </div>
                    </div>
                  </template>
                </div>
              </div>

              <!-- AI Final -->
              <div v-if="round.aiFinal" class="chat-ai-final bubble-other">
                <ChatRichTextRenderer :content="round.aiFinal.content || ''" />
              </div>
            </div>
          </div>

          <!-- Input -->
          <div class="agent-input">
            <div class="agent-input-inner">
              <div v-if="pendingFiles.length" class="agent-pending">
                <div v-for="(file, index) in pendingFiles" :key="`${file.name}-${index}`" class="agent-pending__item">
                  <component :is="getAgentFileIcon(file.name, file.type)" :size="14" class="agent-file-icon" />
                  <span>{{ file.name }}</span>
                  <small>{{ formatFileSize(file.size) }}</small>
                  <button type="button" @click="removePendingFile(index)"><i class="fa-solid fa-xmark"></i></button>
                </div>
              </div>

              <div class="agent-compose" :class="{ 'agent-compose--disabled': useDisabledComposeStyle }">
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
                  ref="agentTextareaRef"
                  v-model="inputText"
                  class="agent-textarea"
                  :disabled="sendDisabled"
                  :placeholder="composePlaceholder"
                />

                <button
                  v-if="session?.status === 'running'"
                  class="agent-cancel-btn"
                  :disabled="canceling"
                  :title="canceling ? '中断中...' : '中断'"
                  @click="handleCancel"
                >
                  <i :class="canceling ? 'fa-solid fa-spinner fa-spin' : 'fa-solid fa-stop'"></i>
                </button>
                <button v-else class="agent-send-btn" :class="{ active: canSendNow }" :disabled="!canSendNow" :title="sending ? '发送中...' : '发送'" @click="handleSend">
                  <i :class="sending ? 'fa-solid fa-spinner fa-spin' : 'fa-solid fa-arrow-up'"></i>
                </button>
              </div>

              <div class="agent-hint-row">
                <p class="agent-hint">
                  <span v-if="session?.task_status === 'completed'">任务已完成，会话已关闭。</span>
                  <span v-else-if="session?.status === 'queued'">{{ queueAheadUsers > 0 ? `排队中，前面还有 ${queueAheadUsers} 人。` : '排队中，请稍候...' }}</span>
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
          </div>
        </template>
      </main>

      <!-- ── Deliverable Modal ── -->
      <Teleport to="body">
        <Transition name="modal-fade">
          <div v-if="showDeliverableModal" class="modal-overlay" @click.self="showDeliverableModal = false">
            <div class="modal-panel">
              <div class="modal-header">
                <h3>交付文件</h3>
                <div class="modal-select-stats">
                  <span class="modal-count modal-count--select">
                    <span class="modal-count-num modal-count-num--left">{{ selectedNames.size }}</span>
                    <span class="modal-count-slash">/</span>
                    <span class="modal-count-num modal-count-num--right">{{ deliverableCount }}</span>
                  </span>
                </div>
                <div class="modal-header-actions">
                  <button
                    v-if="deliverableCount > 0"
                    class="modal-action-btn modal-action-btn--danger"
                    :disabled="selectedNames.size === 0 || deletingSelected"
                    @click="handleDeleteSelected"
                  >
                    <i :class="deletingSelected ? 'fa-solid fa-spinner fa-spin' : 'fa-solid fa-trash'"></i>
                    删除
                  </button>
                  <button class="icon-btn modal-close-btn" @click="showDeliverableModal = false">
                    <i class="fa-solid fa-xmark"></i>
                  </button>
                </div>
              </div>

              <div class="modal-body">
                <div v-if="!deliverableCount" class="modal-empty">
                  <i class="fa-solid fa-folder-open modal-empty-icon"></i>
                  <p>暂无交付文件</p>
                </div>

                <div v-else class="deliverable-list">
                  <div
                    v-for="item in session?.deliverables || []"
                    :key="item.name"
                    class="deliverable-item"
                    :class="{ 'deliverable-item--selected': selectedNames.has(item.name) }"
                    @click="handleDeliverableClick(item)"
                  >
                    <div class="deliverable-check">
                      <i :class="selectedNames.has(item.name) ? 'fa-solid fa-square-check' : 'fa-regular fa-square'"></i>
                    </div>
                    <div class="deliverable-icon">
                      <component :is="getAgentFileIcon(item.name)" :size="18" class="agent-file-icon" />
                    </div>
                    <div class="deliverable-info">
                      <span class="deliverable-name">{{ item.name }}</span>
                      <span class="deliverable-meta">{{ formatFileSize(item.size) }} · {{ formatFull(item.updated_at) }}</span>
                    </div>
                  </div>
                </div>
              </div>

              <div v-if="deliverableCount > 0" class="modal-footer">
                <button class="modal-zip-btn" :disabled="zippingAll" @click="handleDownloadZip">
                  <i class="fa-solid fa-file-zipper"></i>
                  {{ zippingAll ? '打包中...' : (selectedNames.size > 0 ? `打包下载（${selectedNames.size} 个）` : '打包下载全部') }}
                </button>
              </div>
            </div>
          </div>
        </Transition>
      </Teleport>

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
  </div>
</template>

<style>
@property --border-angle {
  syntax: '<angle>';
  initial-value: 0deg;
  inherits: false;
}
</style>

<style scoped>
/* ===== Outer Layout (matches ChatView) ===== */

.agent-outer {
  display: flex;
  flex-direction: column;
  height: 100dvh;
  width: 100%;
  overflow: hidden;
}

.agent-page {
  display: flex;
  flex: 1;
  min-height: 0;
  width: 100%;
  background: var(--c-bg, #f1f5f9);
  overflow: hidden;
}

/* ===== Left Sidebar (matches ChatConversationSidebar) ===== */

@keyframes agent-rise {
  from { opacity: 0; transform: translateY(16px); }
  to   { opacity: 1; transform: translateY(0); }
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
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.search-input::placeholder { color: var(--c-text-muted, #94a3b8); }
.search-input:focus {
  border-color: var(--c-accent, #2563eb);
  box-shadow: 0 0 0 3px var(--c-accent-soft, rgba(37, 99, 235, 0.15));
}

.session-list {
  flex: 1;
  overflow-y: auto;
  padding: 4px 0;
}

.session-list::-webkit-scrollbar { width: 4px; }
.session-list::-webkit-scrollbar-track { background: transparent; }
.session-list::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 2px; }

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
  transition: background 0.15s ease, border-color 0.15s ease;
}

.session-item:hover {
  background: var(--c-bg, #f1f5f9);
}

.session-item.active {
  background: var(--c-accent-light, #eff6ff);
  border-color: var(--c-accent-soft, rgba(37, 99, 235, 0.2));
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
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

.session-item.active .session-item-title { color: #1e3a5f; }

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

.session-dot--running { background: #3b82f6; animation: dotPulse 1.5s ease-in-out infinite; }
.session-dot--queued { background: #f59e0b; animation: dotPulse 1.5s ease-in-out infinite; }
.session-dot--done { background: #22c55e; }
.session-dot--canceled { background: #94a3b8; }

@keyframes dotPulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
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

.session-empty p { margin: 0; }

/* ===== Right Main ===== */

.agent-main {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
  background: #f8fafc;
  position: relative;
  animation: agent-rise 0.48s cubic-bezier(0.22, 1, 0.36, 1) 0.08s both;
}

.agent-empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--c-text-muted, #94a3b8);
  gap: 16px;
}

.agent-empty-icon {
  font-size: 64px;
  opacity: 0.15;
}

.agent-empty-state p { margin: 0; font-size: 14px; }

/* ===== Header (matches ChatHeaderPanel) ===== */

.agent-header {
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--c-border, #e2e8f0);
  padding: 12px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
  z-index: 10;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.back-btn { margin-left: -8px; }

.header-avatar {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  background: linear-gradient(135deg, #3b82f6, #8b5cf6);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 18px;
  flex-shrink: 0;
}

.header-title {
  font-size: var(--text-base, 15px);
  font-weight: 700;
  color: var(--c-text, #1e293b);
  line-height: 1.2;
  margin: 0;
}

.header-status {
  font-size: 11px;
  color: var(--c-text-muted, #94a3b8);
  margin: 2px 0 0;
  line-height: 1.3;
}

.header-status.status-running { color: #3b82f6; font-weight: 500; }
.header-status.status-queued { color: #d97706; font-weight: 500; }

.header-actions {
  display: flex;
  align-items: center;
  gap: 2px;
  flex-shrink: 0;
}

.icon-btn {
  padding: 8px;
  border-radius: 50%;
  background: transparent;
  border: none;
  color: var(--c-text-muted, #94a3b8);
  cursor: pointer;
  transition: all 0.15s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  font-size: 16px;
}

.icon-btn:hover {
  background: var(--c-bg, #f1f5f9);
  color: var(--c-text, #1e293b);
}

.att-count-badge {
  position: absolute;
  top: -2px;
  right: -2px;
  background: var(--c-accent, #2563eb);
  color: white;
  font-size: 9px;
  font-weight: 700;
  min-width: 16px;
  height: 16px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* ===== Chat Scroll ===== */

.chat-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 24px;
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

.chat-ai-snap-wrap,
.terminal,
.chat-ai-final {
  width: min(60%, 980px);
  margin-left: auto;
  margin-right: auto;
}

/* --- User Bubble --- */

.chat-bubble-row { display: flex; }
.chat-bubble-row--right { justify-content: flex-end; }

.chat-bubble-row--right {
  width: min(60%, 980px);
  margin-left: auto;
  margin-right: auto;
}

.chat-bubble {
  max-width: 80%;
  border-radius: 16px 16px 4px 16px;
  padding: 10px 14px;
  font-size: 14px;
  line-height: 1.6;
}

.chat-bubble--user {
  background: var(--c-accent, #2563eb);
  color: #fff;
}

.chat-bubble--user :deep(*) { color: #fff !important; }

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

.chat-file-chip small { opacity: 0.7; }
.agent-file-icon { flex-shrink: 0; }

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

/* ── Border-trace glow effect ── */
.chat-ai-snap-outer--glow {
  padding: 2px;
  border-radius: 14px;
}

.chat-ai-snap-outer--glow::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  padding: 2px;
  background: conic-gradient(
    from var(--border-angle, 0deg),
    transparent 0%,
    transparent 55%,
    rgba(59, 130, 246, 0.08) 62%,
    rgba(99, 102, 241, 0.2) 68%,
    rgba(59, 130, 246, 0.5) 74%,
    #3b82f6 80%,
    rgba(99, 102, 241, 0.5) 84%,
    rgba(59, 130, 246, 0.15) 88%,
    transparent 93%
  );
  -webkit-mask:
    linear-gradient(#fff 0 0) content-box,
    linear-gradient(#fff 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  animation: borderTrace 3s linear infinite;
}

@keyframes borderTrace {
  to { --border-angle: 360deg; }
}

.chat-ai-snap-outer--glow .chat-ai-snap {
  border: none;
  border-radius: 10px;
  position: relative;
  z-index: 1;
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

/* --- Skeleton snap --- */

.skeleton-snap {
  display: flex;
  align-items: center;
  padding: 0 16px;
  border: none !important;
  border-radius: 10px;
  position: relative;
  z-index: 1;
}

.skeleton-lines {
  display: flex;
  flex-direction: column;
  gap: 10px;
  width: 100%;
  padding: 14px 0;
}

.skeleton-line {
  height: 14px;
  border-radius: 6px;
  background: linear-gradient(90deg, #e2e8f0 25%, #f1f5f9 50%, #e2e8f0 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s ease-in-out infinite;
}

.skeleton-line--long { width: 80%; }
.skeleton-line--short { width: 50%; }

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
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

.terminal-status { color: #8b949e; font-size: 13px; }

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

.terminal-status-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 14px;
  margin-right: 6px;
}

.terminal-status-icon--ok { color: #3fb950; }
.terminal-status-icon--err { color: #f85149; }

.terminal-prompt-line {
  font-size: 13px;
  line-height: 1.6;
  word-break: break-all;
}

.terminal-user { color: #3fb950; font-weight: 600; }
.terminal-path { color: #58a6ff; }
.terminal-dollar { color: #3fb950; }
.terminal-cmd { color: #f0f6fc; }

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

.terminal-pre--args { color: #79c0ff; font-size: 11px; }
.terminal-pre--error { color: #fca5a5; }
.terminal-pre--error::before { content: "✗ "; color: #f87171; font-weight: 700; }

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

.terminal-write-head i { font-size: 13px; }
.terminal-write-head--read { color: #58a6ff; }
.terminal-write-box--read { border-color: #1f3a5f; }

.terminal-write-detail {
  padding: 6px 12px;
  font-size: 12px;
  display: flex;
  gap: 8px;
  align-items: baseline;
}

.terminal-write-key { color: #8b949e; flex-shrink: 0; }
.terminal-write-val { color: #79c0ff; word-break: break-all; }

.terminal-write-ok {
  padding: 4px 12px 6px;
  font-size: 12px;
  color: #3fb950;
}

.terminal-write-ok i { margin-right: 4px; }
.terminal-write-ok--error { color: #fda4af; }

.terminal-other-line {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
}

.terminal-other-icon { color: #d29922; }
.terminal-other-name { color: #d29922; font-weight: 600; }

/* --- Terminal setup spinner --- */

.terminal-setup {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #8b949e;
  padding: 4px 0;
}

.terminal-setup-text { color: #58a6ff; }

.terminal-setup-spinner {
  color: #3fb950;
  font-size: 14px;
  width: 16px;
  text-align: center;
}

/* ===== AI Final Output ===== */

.chat-ai-final {
  display: block;
  padding: 0;
  color: #1e293b;
  font-size: 14px;
  line-height: 1.7;
}

/* ===== Rich Text Deep Styles (matching ChatMessageList) ===== */

:deep(.rich-text) p {
  margin-top: 0.25em;
  margin-bottom: 0.25em;
}

:deep(.rich-text) p:first-child { margin-top: 0; }
:deep(.rich-text) p:last-child { margin-bottom: 0; }

:deep(.rich-text) ul,
:deep(.rich-text) ol {
  padding-left: 1.5em;
  margin: 0.25em 0;
}

:deep(.rich-text) ul { list-style-type: disc; }
:deep(.rich-text) ol { list-style-type: decimal; }
:deep(.rich-text) ul ul { list-style-type: circle; }
:deep(.rich-text) ul ul ul { list-style-type: square; }

:deep(.rich-text) li { margin: 0.1em 0; }

:deep(.rich-text) li > ul,
:deep(.rich-text) li > ol { margin: 0; }

:deep(.rich-text) blockquote {
  border-left: 3px solid var(--c-accent, #2563eb);
  margin: 0.4em 0;
  padding: 0.3em 0.8em;
  background: rgba(0, 0, 0, 0.03);
  border-radius: 0 6px 6px 0;
  color: var(--c-text-secondary, #475569);
}

:deep(.rich-text) blockquote p { margin: 0.15em 0; }

:deep(.rich-text) pre,
:deep(.rich-text) pre.hljs-pre {
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

:deep(.rich-text) pre code,
:deep(.rich-text) pre.hljs-pre code {
  font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
  background: transparent;
  padding: 0;
  border-radius: 0;
  font-size: inherit;
  color: inherit;
}

:deep(.rich-text) code {
  font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
  background: rgba(0, 0, 0, 0.06);
  padding: 1px 5px;
  border-radius: 4px;
  font-size: 0.85em;
}

:deep(.code-lang) {
  position: absolute;
  top: 8px;
  left: 12px;
  font-size: 11px;
  font-weight: 600;
  color: #9ca3af;
  font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
  user-select: none;
  letter-spacing: 0.03em;
}

:deep(.code-copy-btn) {
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

:deep(.code-copy-btn:hover) {
  background: #e5e7eb;
  color: #111827;
}

:deep(.code-copy-btn .icon-check) { display: none; }
:deep(.code-copy-btn.copied .icon-copy) { display: none; }
:deep(.code-copy-btn.copied .icon-check) { display: flex; color: #16a34a; }

:deep(.rich-text) table {
  width: 100%;
  border-collapse: collapse;
  margin: 0.4em 0;
  font-size: 0.9em;
}

:deep(.rich-text) th,
:deep(.rich-text) td {
  padding: 6px 10px;
  text-align: left;
}

:deep(.rich-text) th {
  font-weight: 600;
  border-bottom: 2px solid var(--c-text-muted, #94a3b8);
}

:deep(.rich-text) td { border-bottom: 1px solid var(--c-border, #e2e8f0); }
:deep(.rich-text) tr:last-child td { border-bottom: none; }

:deep(.rich-text) hr {
  border: none;
  border-top: 1px solid var(--c-border, #e2e8f0);
  margin: 0.5em 0;
}

:deep(.rich-text) img {
  width: 25vw;
  min-width: 150px;
  max-width: 100%;
  height: auto;
  border-radius: 8px;
  display: block;
  margin: 0 auto;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}

:deep(.bubble-other .rich-text) {
  color: var(--c-text, #1e293b);
  width: 100%;
}

:deep(.bubble-other .rich-text) a {
  color: var(--c-accent, #2563eb);
  text-decoration: underline;
}

:deep(.bubble-own .rich-text) { color: white !important; }

:deep(.bubble-own .rich-text) a {
  color: #bfdbfe;
  text-decoration: underline;
}

:deep(.bubble-own .rich-text) pre {
  background: rgba(0, 0, 0, 0.25);
  color: #e2e8f0;
  border-color: rgba(255, 255, 255, 0.15);
}

:deep(.bubble-own .rich-text) pre code {
  background: transparent;
  color: inherit;
}

:deep(.bubble-own .rich-text) code {
  background: rgba(255, 255, 255, 0.2);
  color: white;
}

:deep(.bubble-own .code-copy-btn) {
  color: rgba(255, 255, 255, 0.6);
}

:deep(.bubble-own .code-copy-btn:hover) {
  background: rgba(255, 255, 255, 0.15);
  color: white;
}

:deep(.bubble-own .code-lang) {
  color: rgba(255, 255, 255, 0.45);
}

:deep(.bubble-own .rich-text) blockquote {
  border-left-color: rgba(255, 255, 255, 0.5);
  background: rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.85);
}

:deep(.latex-error) {
  color: var(--c-danger, #ef4444);
  font-size: var(--text-xs, 11px);
  background: var(--c-danger-light, #fef2f2);
  padding: 1px 4px;
  border-radius: 4px;
}

/* ===== Input ===== */

.agent-input {
  background: #fff;
  border-top: 1px solid var(--c-border, #e2e8f0);
  padding: 12px 24px;
  flex-shrink: 0;
}

.agent-input-inner {
  width: min(60%, 980px);
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 0;
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
.agent-pending__item button { border: none; background: transparent; color: #64748b; padding: 0; cursor: pointer; }

.agent-compose {
  display: flex;
  align-items: flex-end;
  background: var(--c-bg, #f1f5f9);
  border: 1.5px solid var(--c-border, #e2e8f0);
  border-radius: 24px;
  padding: 4px;
  transition: border-color 0.15s ease, background 0.15s ease;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
}

.agent-compose:focus-within {
  background: #fff;
  border-color: var(--c-accent, #2563eb);
}

.agent-compose--disabled {
  background: #fff5f5;
  border-color: #fca5a5;
}

.agent-compose--disabled:focus-within {
  background: #fff5f5;
  border-color: #fca5a5;
}

.agent-compose--disabled .agent-textarea {
  color: #ef4444;
}

.agent-compose--disabled .agent-textarea::placeholder {
  color: #ef4444;
  opacity: 0.8;
}

.agent-compose--disabled .agent-upload-btn,
.agent-compose--disabled .agent-send-btn {
  opacity: 0.4;
}

.agent-upload-btn {
  width: 38px;
  height: 38px;
  flex-shrink: 0;
  border-radius: 50%;
  border: none;
  background: transparent;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--c-text-secondary, #64748b);
  cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease;
  font-size: 15px;
}

.agent-upload-btn:hover { background: var(--c-border, #e2e8f0); }
.agent-upload-btn.disabled { opacity: 0.5; cursor: not-allowed; }
.agent-upload-btn input { display: none; }

.agent-textarea {
  flex: 1;
  border: none;
  background: transparent;
  border-radius: 0;
  height: 38px;
  max-height: 160px;
  resize: none;
  overflow-y: hidden;
  font-size: 14px;
  padding: 9px 8px;
  font-family: inherit;
  outline: none;
  color: var(--c-text, #1e293b);
  line-height: 20px;
}

.agent-textarea::placeholder { color: var(--c-text-muted, #94a3b8); }

.agent-send-btn {
  width: 38px;
  height: 38px;
  flex-shrink: 0;
  border-radius: 50%;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  background: var(--c-border, #e2e8f0);
  color: var(--c-text-muted, #94a3b8);
  cursor: not-allowed;
  transition: background 0.15s ease, color 0.15s ease, transform 0.1s ease;
  min-width: unset;
}

.agent-send-btn.active {
  background: var(--c-accent, #2563eb);
  color: #fff;
  cursor: pointer;
}

.agent-send-btn.active:hover { background: #1d4ed8; transform: scale(1.05); }
.agent-send-btn.active:active { transform: scale(0.95); }

.agent-cancel-btn {
  width: 38px;
  height: 38px;
  flex-shrink: 0;
  border-radius: 50%;
  border: none;
  background: #fee2e2;
  color: #dc2626;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 15px;
  cursor: pointer;
  transition: background 0.15s ease;
  min-width: unset;
}

.agent-cancel-btn:hover:not(:disabled) { background: #fecaca; }
.agent-cancel-btn:disabled { opacity: 0.6; cursor: not-allowed; }

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

.badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  font-weight: 500;
  padding: 2px 8px;
  border-radius: 999px;
}

.badge-blue { background: #dbeafe; color: #1d4ed8; }
.badge-green { background: #dcfce7; color: #16a34a; }
.badge-red { background: #fee2e2; color: #dc2626; }

/* ===== Deliverable Modal ===== */

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  backdrop-filter: blur(4px);
}

.modal-panel {
  background: var(--c-surface, #fff);
  border-radius: var(--radius-lg, 16px);
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
  width: min(520px, 92vw);
  max-height: 80vh;
  display: flex;
  flex-direction: column;
}

.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.22s ease;
}

.modal-fade-enter-from,
.modal-fade-leave-to { opacity: 0; }

.modal-fade-enter-active .modal-panel,
.modal-fade-leave-active .modal-panel {
  transition: transform 0.22s ease, opacity 0.22s ease;
}

.modal-fade-enter-from .modal-panel {
  transform: scale(0.95) translateY(10px);
  opacity: 0;
}

.modal-fade-leave-to .modal-panel {
  transform: scale(0.96) translateY(6px);
  opacity: 0;
}

.modal-header {
  padding: 16px 20px;
  border-bottom: 1px solid var(--c-border, #e2e8f0);
  display: flex;
  align-items: center;
  gap: 12px;
}

.modal-header h3 {
  font-size: var(--text-lg, 18px);
  font-weight: 700;
  flex: 1;
  margin: 0;
}

.modal-count {
  font-size: var(--text-sm, 13px);
  color: var(--c-text-muted, #94a3b8);
  font-weight: 500;
}

.modal-select-stats {
  display: inline-flex;
  align-items: center;
  justify-content: flex-end;
  min-width: 86px;
  flex-shrink: 0;
}

.modal-count--select {
  display: inline-flex;
  align-items: center;
  justify-content: flex-end;
  min-width: 7ch;
  gap: 1px;
  font-variant-numeric: tabular-nums;
}

.modal-count-num {
  display: inline-block;
}

.modal-count-num--left {
  min-width: 3ch;
  text-align: right;
}

.modal-count-num--right {
  min-width: 3ch;
  text-align: left;
}

.modal-count-slash {
  display: inline-block;
  line-height: 1;
}

.modal-header-actions {
  display: flex;
  align-items: center;
  gap: 4px;
}

.modal-close-btn {
  width: 30px;
  height: 30px;
  padding: 0;
  border-radius: 50%;
  aspect-ratio: 1 / 1;
  flex-shrink: 0;
}

.modal-action-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border-radius: 8px;
  border: 1px solid #cbd5e1;
  background: #f8fafc;
  color: #334155;
  font-size: 12px;
  cursor: pointer;
  white-space: nowrap;
  transition: background 0.15s, border-color 0.15s;
}

.modal-action-btn:hover { background: #f1f5f9; border-color: #94a3b8; }

.modal-action-btn--danger {
  background: #fee2e2;
  border-color: #fca5a5;
  color: #dc2626;
}

.modal-action-btn--danger:hover { background: #fecaca; border-color: #f87171; color: #b91c1c; }
.modal-action-btn--danger:disabled { opacity: 0.45; cursor: not-allowed; }

.modal-body {
  padding: 16px 20px;
  overflow-y: auto;
  flex: 1;
}

.modal-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 32px;
  color: var(--c-text-muted, #94a3b8);
  gap: 8px;
}

.modal-empty-icon { font-size: 32px; opacity: 0.15; }
.modal-empty p { margin: 0; font-size: 13px; }

.deliverable-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.deliverable-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid var(--c-border, #e2e8f0);
  cursor: pointer;
  transition: border-color 0.15s ease, background 0.15s ease;
  user-select: none;
}

@media (hover: hover) {
  .deliverable-item:hover {
    border-color: var(--c-accent, #2563eb);
    background: #fafbff;
  }
}

@media (hover: none) {
  .deliverable-item:active {
    border-color: var(--c-accent, #2563eb);
    background: #fafbff;
  }
}

.deliverable-item--selected {
  background: #eff6ff;
  border-color: #93c5fd;
}

.deliverable-check {
  color: #2563eb;
  font-size: 16px;
  flex-shrink: 0;
}

.deliverable-icon {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  background: var(--c-bg, #f1f5f9);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--c-text-muted, #94a3b8);
  font-size: 16px;
  flex-shrink: 0;
}

.deliverable-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.deliverable-name {
  font-size: var(--text-sm, 13px);
  font-weight: 500;
  color: var(--c-text, #1e293b);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.deliverable-meta {
  font-size: var(--text-xs, 11px);
  color: var(--c-text-muted, #94a3b8);
}

.modal-footer {
  padding: 12px 20px;
  border-top: 1px solid var(--c-border, #e2e8f0);
}

.modal-zip-btn {
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
  transition: background 0.15s, border-color 0.15s;
}

.modal-zip-btn:hover:not(:disabled) { background: #f1f5f9; border-color: #94a3b8; }
.modal-zip-btn:disabled { opacity: 0.5; cursor: not-allowed; }

/* ===== Tool Cards (unified) ===== */

.terminal-tool-box {
  border: 1px solid #30363d;
  border-radius: 8px;
  background: #161b22;
  overflow: hidden;
}

.terminal-tool-head {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-bottom: 1px solid #30363d;
  font-size: 12px;
  font-weight: 600;
}

.terminal-tool-head i { font-size: 13px; }

.terminal-tool-head--glob { color: #fbbf24; }
.terminal-tool-head--grep { color: #fb923c; }
.terminal-tool-head--search-web { color: #34d399; }
.terminal-tool-head--fetch-url { color: #22d3ee; }
.terminal-tool-head--todo { color: #a78bfa; }
.terminal-tool-head--task { color: #f0abfc; }
.terminal-tool-head--str-replace { color: #d2a8ff; }
.terminal-tool-head--read-media { color: #fb7185; }

.terminal-tool-box--glob { border-color: #3d3520; }
.terminal-tool-box--grep { border-color: #3d2e20; }
.terminal-tool-box--search-web { border-color: #1a3d2e; }
.terminal-tool-box--fetch-url { border-color: #1a3040; }
.terminal-tool-box--todo { border-color: #2d2540; }
.terminal-tool-box--task { border-color: #3d2040; }
.terminal-tool-box--str-replace { border-color: #2d2540; }
.terminal-tool-box--read-media { border-color: #3d2030; }

.terminal-tool-detail {
  padding: 6px 12px;
  font-size: 12px;
  display: flex;
  gap: 8px;
  align-items: baseline;
}

.terminal-tool-key { color: #8b949e; flex-shrink: 0; }
.terminal-tool-val { color: #79c0ff; word-break: break-all; }
.terminal-tool-val--highlight { color: #ffa657; font-weight: 500; }

.terminal-tool-link {
  color: #58a6ff;
  text-decoration: none;
  word-break: break-all;
}
.terminal-tool-link:hover { text-decoration: underline; }

.terminal-tool-body {
  padding: 4px 12px 8px;
  border-top: 1px solid #21262d;
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.terminal-tool-info {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #8b949e;
  padding: 3px 0;
}

.terminal-tool-info i { color: #58a6ff; font-size: 11px; }

.terminal-tool-file {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #c9d1d9;
  padding: 3px 0;
}

.terminal-tool-file i { color: #8b949e; font-size: 11px; }

.terminal-tool-empty {
  padding: 8px 12px;
  font-size: 12px;
  color: #484f58;
  font-style: italic;
}

.terminal-tool-ok-line {
  padding: 6px 12px;
  font-size: 12px;
  color: #3fb950;
  border-top: 1px solid #21262d;
}

.terminal-tool-ok-line i { margin-right: 4px; }
.terminal-tool-ok-line--error { color: #fda4af; }

.terminal-pre--incard {
  margin: 0;
  padding: 8px 12px;
  border-radius: 0;
  border-top: 1px solid #21262d;
}

/* --- SearchWeb results --- */

.terminal-search-item {
  padding: 8px 0;
  border-bottom: 1px solid #21262d;
}

.terminal-search-item:last-child { border-bottom: none; }

.terminal-search-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
}

.terminal-search-title i { color: #34d399; font-size: 10px; flex-shrink: 0; }

.terminal-search-title a {
  color: #58a6ff;
  text-decoration: none;
  font-weight: 500;
}

.terminal-search-title a:hover { text-decoration: underline; }

.terminal-search-url {
  font-size: 11px;
  color: #3fb950;
  margin-top: 2px;
  padding-left: 16px;
  word-break: break-all;
}

.terminal-search-summary {
  font-size: 12px;
  color: #8b949e;
  margin-top: 4px;
  padding-left: 16px;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* --- FetchURL preview --- */

.terminal-fetch-preview {
  padding: 8px 12px;
  border-top: 1px solid #21262d;
}

.terminal-fetch-title {
  font-size: 13px;
  color: #c9d1d9;
  font-weight: 600;
  margin-bottom: 4px;
}

.terminal-fetch-content {
  font-size: 12px;
  color: #8b949e;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 4;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* --- SetTodoList --- */

.terminal-todo-list {
  padding: 6px 12px 8px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.terminal-todo-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  padding: 4px 0;
}

.terminal-todo--done { color: #3fb950; }
.terminal-todo--progress { color: #58a6ff; }
.terminal-todo--pending { color: #d29922; }

.terminal-todo-title { color: #c9d1d9; flex: 1; min-width: 0; }
.terminal-todo-title--done { text-decoration: line-through; color: #8b949e; }

.terminal-todo-badge {
  font-size: 10px;
  font-weight: 500;
  padding: 1px 6px;
  border-radius: 4px;
  flex-shrink: 0;
}

.terminal-todo-badge--done { background: rgba(63, 185, 80, 0.15); color: #3fb950; }
.terminal-todo-badge--in_progress { background: rgba(88, 166, 255, 0.15); color: #58a6ff; }
.terminal-todo-badge--pending { background: rgba(210, 153, 34, 0.12); color: #d29922; }
.terminal-todo-badge--canceled { background: rgba(248, 81, 73, 0.15); color: #f85149; }

/* --- ReadFile output --- */

.terminal-readfile-output {
  border-top: 1px solid #21262d;
}

.terminal-readfile-output-label {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px 4px;
  font-size: 11px;
  color: #8b949e;
  font-weight: 600;
}

.terminal-readfile-output-label i { color: #58a6ff; font-size: 10px; }

.terminal-readfile-pre {
  margin: 0;
  padding: 4px 12px 10px;
  font-size: 12px;
  color: #8b949e;
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.5;
  max-height: 240px;
  overflow-y: auto;
  font-family: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', 'SF Mono', 'Menlo', monospace;
}

.terminal-readfile-pre--error { color: #fca5a5; }
.terminal-readfile-pre--error::before { content: "✗ "; color: #f87171; font-weight: 700; }

.terminal-readfile-pre::-webkit-scrollbar { width: 4px; }
.terminal-readfile-pre::-webkit-scrollbar-track { background: #0d1117; }
.terminal-readfile-pre::-webkit-scrollbar-thumb { background: #30363d; border-radius: 2px; }

/* --- Task badge + output --- */

.terminal-task-badge {
  margin-left: auto;
  font-size: 11px;
  font-weight: 500;
  padding: 1px 8px;
  border-radius: 4px;
  background: rgba(240, 171, 252, 0.1);
  color: #f0abfc;
  border: 1px solid rgba(240, 171, 252, 0.2);
}

.terminal-task-output {
  border-top: 1px solid #21262d;
}

.terminal-task-output-label {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px 4px;
  font-size: 11px;
  color: #8b949e;
  font-weight: 600;
}

.terminal-task-output-label i { color: #c9aef5; font-size: 10px; }

.terminal-task-pre {
  margin: 0;
  padding: 4px 12px 10px;
  font-size: 12px;
  color: #8b949e;
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.5;
  max-height: 240px;
  overflow-y: auto;
  font-family: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', 'SF Mono', 'Menlo', monospace;
}

.terminal-task-pre--error { color: #fca5a5; }
.terminal-task-pre--error::before { content: "✗ "; color: #f87171; font-weight: 700; }

.terminal-task-pending {
  padding: 6px 12px 8px;
  border-top: 1px solid #21262d;
  color: #8b949e;
  font-size: 13px;
}

/* --- StrReplaceFile diff --- */

.terminal-diff {
  border-top: 1px solid #21262d;
  font-family: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', 'SF Mono', 'Menlo', monospace;
}

.terminal-diff-old {
  display: flex;
  gap: 8px;
  padding: 4px 12px;
  background: rgba(248, 81, 73, 0.1);
  font-size: 12px;
  align-items: flex-start;
}

.terminal-diff-new {
  display: flex;
  gap: 8px;
  padding: 4px 12px;
  background: rgba(63, 185, 80, 0.1);
  font-size: 12px;
  align-items: flex-start;
}

.terminal-diff-label {
  flex-shrink: 0;
  width: 14px;
  text-align: center;
  font-weight: 700;
}

.terminal-diff-old .terminal-diff-label { color: #f85149; }
.terminal-diff-new .terminal-diff-label { color: #3fb950; }

.terminal-diff-old code {
  color: #ffa198;
  background: transparent;
  font-size: inherit;
  padding: 0;
  word-break: break-all;
  white-space: pre-wrap;
}

.terminal-diff-new code {
  color: #7ee787;
  background: transparent;
  font-size: inherit;
  padding: 0;
  word-break: break-all;
  white-space: pre-wrap;
}

/* --- ReadMediaFile --- */

.terminal-media-preview {
  padding: 10px 14px 12px;
  border-top: 1px solid #21262d;
}

.terminal-media-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.terminal-media-chip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 3px 10px;
  border-radius: 999px;
  background: #21262d;
  border: 1px solid #30363d;
  font-size: 12px;
  color: #c9d1d9;
}

.terminal-readmedia-path-ok {
  color: #3fb950;
  font-size: 12px;
}

.terminal-media-chip i { color: #fb7185; font-size: 10px; }

/* ===== Responsive ===== */

@media (max-width: 768px) {
  .agent-sidebar { width: 100%; }
  .sidebar-hidden { display: none; }
  .main-hidden { display: none; }

  .agent-header { padding: 12px 16px; }
  .chat-scroll { padding: 16px; }
  .agent-input { padding: 12px 16px; }
  .agent-input-inner { width: 100%; }

  .chat-ai-snap-wrap,
  .terminal,
  .chat-ai-final {
    width: 100%;
  }

  .chat-bubble-row--right {
    width: 100%;
  }
}
</style>
