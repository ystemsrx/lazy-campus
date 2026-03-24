<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import AppToast from "../components/AppToast.vue";
import AgentComposer from "../components/agent/AgentComposer.vue";
import AgentConversationRounds from "../components/agent/AgentConversationRounds.vue";
import AgentDeliverablesModal from "../components/agent/AgentDeliverablesModal.vue";
import AgentHeader from "../components/agent/AgentHeader.vue";
import AgentSidebar from "../components/agent/AgentSidebar.vue";
import HomeHeaderBar from "../components/home/HomeHeaderBar.vue";
import HomeTaskEditorModal from "../components/home/HomeTaskEditorModal.vue";
import {
  cancelAgentSession,
  deleteAgentDeliverables,
  downloadDeliverableZip,
  fetchAgentAvailability,
  fetchAgentMessages,
  fetchAgentSession,
  fetchMyAgentSessions,
  sendAgentMessage,
} from "../api/agent";
import {
  buildConversationRounds,
  isNearBottom,
} from "../components/agent/agentViewUtils";
import { useAppToast } from "../composables/useAppToast";
import { useQuickTaskPublish } from "../composables/useQuickTaskPublish";
import { useAuthStore } from "../stores/auth";
import type {
  AgentAvailability,
  AgentMessage,
  AgentMySessionItem,
  AgentSessionDetail,
} from "../types/api";
import { extractError } from "../utils/error";
import { nowLocal, parseUTC } from "../utils/time";

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();

const appTitle = import.meta.env.VITE_APP_TITLE || "校园任务平台";
const logoFile = import.meta.env.VITE_APP_LOGO as string | undefined;
const logoUrl = computed(() => (logoFile ? `/logos/${logoFile}` : null));
const sessionId = computed(() => String(route.params.sessionId || ""));
const { toast, showToast, clearToast } = useAppToast();
const {
  showCreateModal,
  newTask,
  publishCategories,
  canCreateWithAgent,
  createWithAgentSubmitting,
  openPublishModal,
  uploadTaskImage,
  submitPublishTask,
} = useQuickTaskPublish({ showToast });

const isMobile = ref(
  typeof window !== "undefined" ? window.innerWidth < 768 : false,
);

function checkMobile() {
  isMobile.value = window.innerWidth < 768;
}

const allSessions = ref<AgentMySessionItem[]>([]);
const loadingSessions = ref(true);
const searchQuery = ref("");

const filteredSessions = computed(() => {
  const q = searchQuery.value.trim().toLowerCase();
  if (!q) return allSessions.value;
  return allSessions.value.filter((s) =>
    s.task_title.toLowerCase().includes(q),
  );
});

const terminalHostname = computed(() => {
  return (
    appTitle
      .replace(/\s+/g, "-")
      .replace(/[A-Za-z]/g, (c: string) => c.toLowerCase()) + "@agent"
  );
});

async function loadSessions() {
  try {
    const result = await fetchMyAgentSessions({ page: 1, page_size: 100 });
    allSessions.value = result.items;
  } catch {
    /* ignore */
  } finally {
    loadingSessions.value = false;
  }
}

function selectSession(s: AgentMySessionItem) {
  router.push(`/agent/${s.session_id}`);
}

function updateSearchQuery(value: string) {
  searchQuery.value = value;
}

const availability = ref<AgentAvailability | null>(null);
const session = ref<AgentSessionDetail | null>(null);
const messages = ref<AgentMessage[]>([]);

const loading = ref(true);
const sending = ref(false);
const canceling = ref(false);
const inputText = ref("");
const pendingFiles = ref<File[]>([]);
const queuedDraft = ref<{ text: string; files: File[] } | null>(null);

const chatScrollRef = ref<HTMLDivElement | null>(null);
const terminalStickToBottomMap = ref(new Map<number, boolean>());
const snapIndices = ref(new Map<number, number>());
const snapStickToBottomMap = ref(new Map<number, boolean>());

let pollTimer: ReturnType<typeof setInterval> | null = null;
let pollBusy = false;
let lastMessageId = 0;
let sessionPollTimer: ReturnType<typeof setInterval> | null = null;
let activeSessionRequestId = 0;

function isStaleSessionRequest(
  targetSessionId: string,
  requestId: number,
): boolean {
  return (
    requestId !== activeSessionRequestId || targetSessionId !== sessionId.value
  );
}

const interactionLeft = computed(() => {
  if (!session.value) return 0;
  return Math.max(
    0,
    session.value.max_interactions - session.value.interaction_count,
  );
});

const queueAheadUsers = computed(() =>
  Math.max(0, session.value?.queue_ahead_users || 0),
);
const needsQueue = computed(() => Boolean(session.value?.queue_waiting));
const isCancelable = computed(
  () =>
    session.value?.status === "running" || session.value?.status === "queued",
);

const isTaskTerminal = computed(() => {
  const status = session.value?.task_status;
  return status === "completed" || status === "canceled";
});

const sendDisabled = computed(() => {
  if (!session.value) return true;
  if (sending.value) return true;
  if (isTaskTerminal.value) return true;
  if (!session.value.can_send) return true;
  if (session.value.interaction_count >= session.value.max_interactions)
    return true;
  return false;
});

const useDisabledComposeStyle = computed(() => {
  if (!session.value) return false;
  if (session.value.status === "running" || session.value.status === "queued")
    return true;
  if (isTaskTerminal.value) return true;
  if (!session.value.can_send) return true;
  if (session.value.interaction_count >= session.value.max_interactions)
    return true;
  return false;
});

const queueText = computed(() =>
  queueAheadUsers.value > 0 ? `前方还有 ${queueAheadUsers.value} 人` : "",
);

const RUNNING_STALE_HINT_SECONDS = 120;

function formatElapsedSilence(totalSeconds: number): string {
  if (totalSeconds < 60) return `${totalSeconds} 秒`;
  const minutes = Math.floor(totalSeconds / 60);
  if (minutes < 60) return `${minutes} 分钟`;
  const hours = Math.floor(minutes / 60);
  const remainMinutes = minutes % 60;
  return remainMinutes > 0
    ? `${hours} 小时 ${remainMinutes} 分钟`
    : `${hours} 小时`;
}

const runningSilentSeconds = computed(() => {
  if (session.value?.status !== "running" || !session.value.last_activity_at)
    return 0;
  const lastActivity = parseUTC(session.value.last_activity_at).getTime();
  return Math.max(0, Math.floor((Date.now() - lastActivity) / 1000));
});

const isSessionStalled = computed(
  () => runningSilentSeconds.value >= RUNNING_STALE_HINT_SECONDS,
);

const runningSilenceText = computed(() =>
  isSessionStalled.value
    ? `已 ${formatElapsedSilence(runningSilentSeconds.value)} 无新内容`
    : "",
);

const sessionStatusText = computed(() => {
  if (!session.value) return "空闲";
  if (isTaskTerminal.value)
    return session.value.task_status === "completed" ? "已完成" : "已取消";
  if (session.value.status === "error")
    return session.value.last_error || "执行失败，可重新发送";
  if (session.value.status === "running")
    return isSessionStalled.value
      ? `正在执行，但 ${runningSilenceText.value}`
      : "正在执行...";
  if (session.value.status === "queued")
    return queueAheadUsers.value > 0
      ? `排队中，${queueText.value}`
      : "排队中...";
  if (needsQueue.value)
    return queueAheadUsers.value > 0 ? `需排队，${queueText.value}` : "需排队";
  return "空闲";
});

const composePlaceholder = computed(() => {
  if (!session.value) return "描述你的目标、预期产物和约束条件...";
  if (session.value.task_status === "canceled")
    return "任务已取消，会话已关闭。";
  if (session.value.task_status === "completed")
    return "任务已完成，会话已关闭。";
  if (session.value.status === "error")
    return session.value.last_error || "上一次执行失败，可重新发送新的指令。";
  if (session.value.status === "queued")
    return queueAheadUsers.value > 0
      ? `排队中，${queueText.value}。`
      : "排队中，请稍候...";
  if (session.value.status === "running")
    return isSessionStalled.value
      ? `代理已长时间没有返回新内容，${runningSilenceText.value}。`
      : "代理正在执行中，可中断后继续输入。";
  if (needsQueue.value)
    return queueAheadUsers.value > 0
      ? `当前需排队，${queueText.value}。`
      : "当前需排队，请稍后发送。";
  if (!session.value.can_send) return "当前会话不可继续发送。";
  if (session.value.interaction_count >= session.value.max_interactions)
    return "交互次数已用尽。";
  return "描述你的目标、预期产物和约束条件...";
});

const canSendNow = computed(() => {
  if (sendDisabled.value) return false;
  return Boolean(inputText.value.trim() || pendingFiles.value.length > 0);
});

const maxFileCount = computed(() => availability.value?.max_files ?? 5);
const maxFileSizeMb = computed(
  () => availability.value?.max_file_size_mb ?? 50,
);

const showDeliverableModal = ref(false);
const zippingAll = ref(false);
const deletingSelected = ref(false);
const selectedNames = ref<Set<string>>(new Set());

const deliverableCount = computed(
  () => session.value?.deliverables.length ?? 0,
);

const conversationRounds = computed(() =>
  buildConversationRounds(messages.value),
);

const showPendingRoundSkeleton = computed(() => {
  if (!session.value || session.value.status !== "running") return false;
  const rounds = conversationRounds.value;
  if (rounds.length === 0) return false;
  const last = rounds[rounds.length - 1];
  return (
    !!last.userMessage &&
    last.aiIntermediate.length === 0 &&
    last.entries.length === 0 &&
    !last.aiFinal
  );
});

const showSetupSkeleton = computed(() => {
  if (!showPendingRoundSkeleton.value) return false;
  return conversationRounds.value.length === 1;
});

const runningRoundId = computed<number | null>(() => {
  if (session.value?.status !== "running") return null;
  const rounds = conversationRounds.value;
  if (!rounds.length) return null;
  return rounds[rounds.length - 1].id;
});

const brailleFrames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"];
const brailleIndex = ref(0);
const brailleChar = computed(() => brailleFrames[brailleIndex.value]);
let brailleTimer: ReturnType<typeof setInterval> | null = null;

watch(showSetupSkeleton, (show) => {
  if (show) {
    brailleTimer = setInterval(() => {
      brailleIndex.value = (brailleIndex.value + 1) % brailleFrames.length;
    }, 80);
  } else if (brailleTimer) {
    clearInterval(brailleTimer);
    brailleTimer = null;
  }
});

function handleSnapScroll(payload: {
  event: Event;
  roundId: number;
  total: number;
}) {
  const el = payload.event.target as HTMLElement;
  const idx = Math.min(Math.round(el.scrollTop / 64), payload.total - 1);
  snapIndices.value = new Map(snapIndices.value.set(payload.roundId, idx));
  snapStickToBottomMap.value = new Map(
    snapStickToBottomMap.value.set(payload.roundId, isNearBottom(el)),
  );
}

function handleTerminalScroll(payload: { event: Event; roundId: number }) {
  const el = payload.event.target as HTMLElement;
  const shouldStick = isNearBottom(el);
  terminalStickToBottomMap.value = new Map(
    terminalStickToBottomMap.value.set(payload.roundId, shouldStick),
  );
}

function scrollToBottomOnEnter() {
  nextTick(() => {
    const root = chatScrollRef.value;
    if (!root) return;

    root.scrollTo({ top: root.scrollHeight, behavior: "auto" });

    root.querySelectorAll(".chat-ai-snap").forEach((el) => {
      const snapEl = el as HTMLElement;
      const roundId = Number(snapEl.dataset.roundId || "0");
      const total = snapEl.querySelectorAll(".chat-ai-snap-item").length;
      snapEl.scrollTo({ top: snapEl.scrollHeight, behavior: "auto" });
      if (roundId > 0) {
        snapStickToBottomMap.value = new Map(
          snapStickToBottomMap.value.set(roundId, true),
        );
        if (total > 0) {
          snapIndices.value = new Map(
            snapIndices.value.set(roundId, total - 1),
          );
        }
      }
    });

    root.querySelectorAll(".terminal-body").forEach((el) => {
      const terminalEl = el as HTMLElement;
      const roundId = Number(terminalEl.dataset.roundId || "0");
      terminalEl.scrollTo({ top: terminalEl.scrollHeight, behavior: "auto" });
      terminalStickToBottomMap.value = new Map(
        terminalStickToBottomMap.value.set(roundId, true),
      );
    });
  });
}

function resetViewState() {
  loading.value = true;
  session.value = null;
  messages.value = [];
  lastMessageId = 0;
  inputText.value = "";
  pendingFiles.value = [];
  queuedDraft.value = null;
  terminalStickToBottomMap.value = new Map();
  snapStickToBottomMap.value = new Map();
  snapIndices.value = new Map();
  selectedNames.value = new Set();
  showDeliverableModal.value = false;
}

async function refreshAvailability(
  targetSessionId = sessionId.value,
  requestId = activeSessionRequestId,
) {
  try {
    const nextAvailability = await fetchAgentAvailability();
    if (isStaleSessionRequest(targetSessionId, requestId)) return;
    availability.value = nextAvailability;
  } catch {
    if (isStaleSessionRequest(targetSessionId, requestId)) return;
    availability.value = null;
  }
}

async function refreshSession(
  targetSessionId = sessionId.value,
  requestId = activeSessionRequestId,
) {
  const nextSession = await fetchAgentSession(targetSessionId);
  if (isStaleSessionRequest(targetSessionId, requestId)) return;
  session.value = nextSession;
}

async function refreshMessages(
  targetSessionId = sessionId.value,
  requestId = activeSessionRequestId,
) {
  const afterId = lastMessageId;
  const newMessages = await fetchAgentMessages(targetSessionId, afterId);
  if (isStaleSessionRequest(targetSessionId, requestId)) return;
  if (newMessages.length === 0) return;
  const nextMessages =
    afterId === lastMessageId
      ? newMessages
      : newMessages.filter((msg) => msg.id > lastMessageId);
  if (nextMessages.length === 0) return;
  messages.value.push(...nextMessages);
  lastMessageId = nextMessages[nextMessages.length - 1].id;
}

async function pollSession() {
  const targetSessionId = sessionId.value;
  const requestId = activeSessionRequestId;
  if (pollBusy || !targetSessionId) return;
  pollBusy = true;
  try {
    await Promise.all([
      refreshSession(targetSessionId, requestId),
      refreshMessages(targetSessionId, requestId),
    ]);
  } catch {
    /* ignore */
  } finally {
    pollBusy = false;
  }
}

function startPolling() {
  stopPolling();
  pollTimer = setInterval(() => {
    pollSession().catch(() => {});
  }, 2000);
}

function stopPolling() {
  if (!pollTimer) return;
  clearInterval(pollTimer);
  pollTimer = null;
}

async function bootstrap() {
  const targetSessionId = sessionId.value;
  const requestId = ++activeSessionRequestId;
  if (!targetSessionId) {
    resetViewState();
    loading.value = false;
    return;
  }
  resetViewState();
  try {
    await Promise.all([
      refreshAvailability(targetSessionId, requestId),
      refreshSession(targetSessionId, requestId),
    ]);
    await refreshMessages(targetSessionId, requestId);
  } catch (error) {
    if (isStaleSessionRequest(targetSessionId, requestId)) return;
    showToast(extractError(error, "加载代理会话失败"), "error");
    router.push("/agent");
  } finally {
    if (isStaleSessionRequest(targetSessionId, requestId)) return;
    loading.value = false;
    scrollToBottomOnEnter();
  }
}

function pickFiles(files: File[]) {
  if (!files.length) return;

  const limitCount = maxFileCount.value;
  const limitSize = maxFileSizeMb.value * 1024 * 1024;
  const next = [...pendingFiles.value];

  for (const file of files) {
    if (next.length >= limitCount) {
      showToast(`最多可添加 ${limitCount} 个文件`, "warning");
      break;
    }
    if (file.size > limitSize) {
      showToast(`「${file.name}」超过 ${maxFileSizeMb.value} MB 限制`, "error");
      continue;
    }
    next.push(file);
  }

  pendingFiles.value = next;
}

function removePendingFile(index: number) {
  pendingFiles.value.splice(index, 1);
}

async function handleSend() {
  if (!canSendNow.value || !session.value) return;
  sending.value = true;
  const draft = {
    text: inputText.value.trim(),
    files: [...pendingFiles.value],
  };
  try {
    const result = await sendAgentMessage(session.value.session_id, {
      content: draft.text,
      files: draft.files,
    });
    queuedDraft.value = result.queued ? draft : null;
    inputText.value = "";
    pendingFiles.value = [];
    if (Math.max(0, result.queue_ahead_users || 0) > 0) {
      showToast(`排队中，前方还有 ${result.queue_ahead_users} 人`, "warning");
    }
    await Promise.all([pollSession(), refreshAvailability()]);
  } catch (error) {
    queuedDraft.value = null;
    showToast(extractError(error, "发送失败"), "error");
  } finally {
    sending.value = false;
  }
}

async function handleCancel() {
  if (!session.value || canceling.value) return;
  canceling.value = true;
  try {
    const result = await cancelAgentSession(session.value.session_id);
    if (result.canceled && result.mode === "queued") {
      if (result.removed_message_id != null) {
        messages.value = messages.value.filter(
          (msg) => msg.id !== result.removed_message_id,
        );
        lastMessageId =
          messages.value.length > 0
            ? messages.value[messages.value.length - 1].id
            : 0;
      }
      const restoredText = (
        queuedDraft.value?.text ??
        result.restored_content ??
        ""
      ).trim();
      const restoredFiles = queuedDraft.value?.files ?? [];
      inputText.value = restoredText;
      pendingFiles.value = [...restoredFiles];
      showToast("已终止排队", "success");
      queuedDraft.value = null;
    } else if (result.canceled && result.mode === "running") {
      showToast("已中断当前执行", "success");
      queuedDraft.value = null;
    } else {
      showToast("当前没有可终止的排队或运行任务", "warning");
    }
    await pollSession();
  } catch (error: any) {
    const status = error?.response?.status;
    if (status === 404 || status === 405) {
      showToast("暂不支持中断功能", "warning");
    } else {
      showToast(extractError(error, "中断失败"), "error");
    }
  } finally {
    canceling.value = false;
  }
}

async function handleDownloadZip() {
  if (!session.value) return;
  zippingAll.value = true;
  try {
    const names = selectedNames.value.size > 0 ? [...selectedNames.value] : [];
    const blob = await downloadDeliverableZip(session.value.session_id, names);
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "deliverables.zip";
    link.click();
    URL.revokeObjectURL(url);
  } catch (error) {
    showToast(extractError(error, "打包下载失败"), "error");
  } finally {
    zippingAll.value = false;
  }
}

async function handleDeleteSelected() {
  if (!session.value || selectedNames.value.size === 0) return;
  deletingSelected.value = true;
  try {
    await deleteAgentDeliverables(session.value.session_id, [
      ...selectedNames.value,
    ]);
    selectedNames.value = new Set();
    await refreshSession();
  } catch (error) {
    showToast(extractError(error, "删除失败"), "error");
  } finally {
    deletingSelected.value = false;
  }
}

function toggleSelect(name: string) {
  const next = new Set(selectedNames.value);
  if (next.has(name)) next.delete(name);
  else next.add(name);
  selectedNames.value = next;
}

watch(
  () => messages.value.length,
  () => {
    nextTick(() => {
      if (!chatScrollRef.value) return;

      chatScrollRef.value.querySelectorAll(".chat-ai-snap").forEach((el) => {
        const snapEl = el as HTMLElement;
        const roundId = Number(snapEl.dataset.roundId || "0");
        const shouldStick =
          snapStickToBottomMap.value.get(roundId) ?? isNearBottom(snapEl);
        if (!shouldStick) return;
        const total = snapEl.querySelectorAll(".chat-ai-snap-item").length;
        snapEl.scrollTo({ top: snapEl.scrollHeight, behavior: "smooth" });
        snapStickToBottomMap.value = new Map(
          snapStickToBottomMap.value.set(roundId, true),
        );
        if (total > 0) {
          snapIndices.value = new Map(
            snapIndices.value.set(roundId, total - 1),
          );
        }
      });

      chatScrollRef.value.querySelectorAll(".terminal-body").forEach((el) => {
        const terminalEl = el as HTMLElement;
        const roundId = Number(terminalEl.dataset.roundId || "0");
        const shouldStick =
          terminalStickToBottomMap.value.get(roundId) ??
          isNearBottom(terminalEl);
        if (!shouldStick) return;
        terminalEl.scrollTo({
          top: terminalEl.scrollHeight,
          behavior: "smooth",
        });
        terminalStickToBottomMap.value = new Map(
          terminalStickToBottomMap.value.set(roundId, true),
        );
      });
    });
  },
);

watch(
  () => sessionId.value,
  () => {
    bootstrap().catch(() => {});
  },
  { immediate: true },
);

onMounted(() => {
  checkMobile();
  window.addEventListener("resize", checkMobile);
  startPolling();
  loadSessions();
  sessionPollTimer = setInterval(() => {
    loadSessions();
  }, 10000);
});

onUnmounted(() => {
  activeSessionRequestId += 1;
  window.removeEventListener("resize", checkMobile);
  stopPolling();
  if (brailleTimer) clearInterval(brailleTimer);
  if (sessionPollTimer) clearInterval(sessionPollTimer);
});
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
      @logout="
        auth.logout();
        router.push('/login');
      "
      @update:active-tab="
        (tab) => router.push(tab === 'workers' ? '/?tab=workers' : '/')
      "
    />

    <div class="agent-page">
      <AppToast :toast="toast" @dismiss="clearToast" />

      <AgentSidebar
        :sessions="filteredSessions"
        :loading-sessions="loadingSessions"
        :search-query="searchQuery"
        :active-session-id="sessionId"
        :is-mobile="isMobile"
        :has-active-session="Boolean(sessionId)"
        @update:search-query="updateSearchQuery"
        @select-session="selectSession"
      />

      <main
        class="agent-main"
        :class="{ 'main-hidden': !sessionId && isMobile }"
      >
        <div v-if="!sessionId" class="agent-empty-state">
          <i class="fa-solid fa-robot agent-empty-icon"></i>
          <p>从左侧选择一个代理会话</p>
        </div>

        <template v-else>
          <AgentHeader
            :is-mobile="isMobile"
            :logo-url="logoUrl"
            :title="session?.task_title || '代理会话'"
            :status-text="sessionStatusText"
            :is-running="session?.status === 'running'"
            :is-queued="session?.status === 'queued' || needsQueue"
            :is-stalled="isSessionStalled"
            :is-error="session?.status === 'error'"
            :deliverable-count="deliverableCount"
            @back="router.push('/agent')"
            @open-deliverables="showDeliverableModal = true"
          />

          <div ref="chatScrollRef" class="chat-scroll">
            <AgentConversationRounds
              :loading="loading"
              :conversation-rounds="conversationRounds"
              :show-pending-round-skeleton="showPendingRoundSkeleton"
              :show-setup-skeleton="showSetupSkeleton"
              :terminal-hostname="terminalHostname"
              :braille-char="brailleChar"
              :snap-indices="snapIndices"
              :is-session-running="session?.status === 'running'"
              :running-round-id="runningRoundId"
              @snap-scroll="handleSnapScroll"
              @terminal-scroll="handleTerminalScroll"
            />
          </div>

          <AgentComposer
            v-model="inputText"
            :pending-files="pendingFiles"
            :send-disabled="sendDisabled"
            :use-disabled-compose-style="useDisabledComposeStyle"
            :compose-placeholder="composePlaceholder"
            :is-cancelable="isCancelable"
            :canceling="canceling"
            :can-send-now="canSendNow"
            :sending="sending"
            :session-status="session?.status ?? null"
            :task-status="session?.task_status ?? null"
            :queue-ahead-users="queueAheadUsers"
            :queue-text="queueText"
            :needs-queue="needsQueue"
            :interaction-left="interactionLeft"
            :interaction-count="session?.interaction_count ?? 0"
            :max-interactions="session?.max_interactions ?? 8"
            :max-file-count="maxFileCount"
            :max-file-size-mb="maxFileSizeMb"
            @pick-files="pickFiles"
            @remove-file="removePendingFile"
            @send="handleSend"
            @cancel="handleCancel"
          />
        </template>
      </main>

      <AgentDeliverablesModal
        v-model:show="showDeliverableModal"
        :deliverables="session?.deliverables || []"
        :selected-names="selectedNames"
        :deleting-selected="deletingSelected"
        :zipping-all="zippingAll"
        @toggle-select="toggleSelect"
        @delete-selected="handleDeleteSelected"
        @download-zip="handleDownloadZip"
      />

      <HomeTaskEditorModal
        v-model="showCreateModal"
        mode="create"
        :form="newTask"
        :categories="publishCategories"
        :now-local="nowLocal"
        :show-agent-action="canCreateWithAgent"
        :agent-submitting="createWithAgentSubmitting"
        :upload-task-image="uploadTaskImage"
        @submit="submitPublishTask"
        @submit-agent="submitPublishTask('agent')"
      />
    </div>
  </div>
</template>

<style scoped>
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

.agent-empty-state p {
  margin: 0;
  font-size: 14px;
}

.chat-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.chat-scroll::-webkit-scrollbar {
  width: 6px;
}

.chat-scroll::-webkit-scrollbar-track {
  background: transparent;
}

.chat-scroll::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 3px;
}

@media (max-width: 768px) {
  .main-hidden {
    display: none;
  }

  .chat-scroll {
    padding: 16px;
  }
}
</style>
