<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  Search,
  Paperclip,
  ArrowUp,
  ArrowLeft,
  ShieldAlert,
  ShieldOff,
  MessageSquare,
  Compass,
  ChevronUp,
  Plus,
  Check,
  CheckCheck,
  X,
  Trash2,
  Download,
  FileText,
  FileSpreadsheet,
  FileImage,
  FileArchive,
  FileCode,
  File as FileIcon,
  Film,
  Music,
  Flag,
  Star,
  User as UserIcon,
} from "lucide-vue-next";
import HomeAvatar from "../components/home/ui/HomeAvatar.vue";
import HomeStars from "../components/home/ui/HomeStars.vue";
import HomeReportModal from "../components/home/HomeReportModal.vue";
import HomeHeaderBar from "../components/home/HomeHeaderBar.vue";
import AppToast from "../components/AppToast.vue";
import { appConfirm } from "../components/AppConfirm.vue";
import { useAppToast } from "../composables/useAppToast";
import { getTaskIcon } from "../utils/taskIcons";
import {
  formatChatTime,
  formatFull,
  formatLastSeen,
  isExpired,
} from "../utils/time";
import { useAuthStore } from "../stores/auth";
import { useNotificationStore } from "../stores/notifications";
import {
  fetchConversations,
  fetchMessages,
  sendMessage,
  markRead,
  fetchAttachments,
  uploadAttachment,
  deleteAttachment,
} from "../api/chat";
import {
  fetchUserPublic,
  fetchWorkerDetail,
  fetchUserReviews,
} from "../api/users";
import { fetchTask } from "../api/tasks";
import { blockUser, unblockUser } from "../api/moderation";
import type { WorkerProfile, UserReview, Task } from "../types/api";
import type {
  ChatMessage,
  Conversation,
  ChatAttachment,
  AttachmentCount,
} from "../types/chat";

import { marked } from "marked";
import DOMPurify from "dompurify";
import katex from "katex";
import "katex/dist/katex.min.css";
import hljs from "highlight.js";
import "highlight.js/styles/github.css";

// ── State ─────────────────────────────────────────────────────────────
const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const notifStore = useNotificationStore();
const myId = computed(() => auth.user?.id ?? 0);

const appTitle = import.meta.env.VITE_APP_TITLE || '校园任务平台';
const isAuthenticated = computed(() => auth.isAuthenticated);
const displayName = computed(() => auth.displayName);
const avatarUrl = computed(() => auth.user?.avatar_url ?? null);
const avatarGender = computed(() => auth.user?.gender ?? null);

const conversations = ref<Conversation[]>([]);
const activeConv = ref<Conversation | null>(null);
const messages = ref<ChatMessage[]>([]);
const inputText = ref("");
const searchQuery = ref("");
const isBannerCollapsed = ref(false);
const loading = ref(false);
const sending = ref(false);

const messagesContainer = ref<HTMLDivElement | null>(null);
const textareaRef = ref<HTMLTextAreaElement | null>(null);

const showAttachmentModal = ref(false);
const attachments = ref<ChatAttachment[]>([]);
const attachmentCount = ref<AttachmentCount>({ count: 0, limit: 5 });
const uploadingFile = ref(false);

const showUserDetailModal = ref(false);
const peerWorkerProfile = ref<WorkerProfile | null>(null);
const peerWorkerReviews = ref<UserReview[]>([]);

const showReportModal = ref(false);

const isMobile = ref(false);
const { toast, showToast, clearToast } = useAppToast();
let pollTimer: ReturnType<typeof setInterval> | null = null;

// ── Conversation list: hide / swipe / context-menu ───────────────────
const HIDDEN_STORAGE_KEY = `chat-hidden-convs-${auth.user?.id ?? "guest"}`;

function loadHiddenKeys(): Set<string> {
  try {
    const raw = localStorage.getItem(HIDDEN_STORAGE_KEY);
    return raw ? new Set(JSON.parse(raw) as string[]) : new Set();
  } catch {
    return new Set();
  }
}

function saveHiddenKeys(s: Set<string>) {
  try {
    localStorage.setItem(HIDDEN_STORAGE_KEY, JSON.stringify([...s]));
  } catch {
    /* ignore */
  }
}

const hiddenConvKeys = ref<Set<string>>(loadHiddenKeys());
const swipedKey = ref<string | null>(null);
const swipeStartX = ref(0);

// desktop right-click context menu
const ctxMenu = ref<{ x: number; y: number; key: string } | null>(null);

function convKey(conv: { peer_id: number; task_id: number | null }) {
  return `${conv.peer_id}-${conv.task_id}`;
}

// mobile swipe handlers
function onSwipeStart(e: TouchEvent, key: string) {
  swipeStartX.value = e.touches[0].clientX;
  if (swipedKey.value !== key) swipedKey.value = null;
}

function onSwipeMove(e: TouchEvent, key: string) {
  const dx = swipeStartX.value - e.touches[0].clientX;
  if (dx > 40) swipedKey.value = key;
  else if (dx < -10) swipedKey.value = null;
}

function onSwipeEnd() {
  /* keep current state */
}

function closeSwipe() {
  swipedKey.value = null;
}

// desktop context menu
function onContextMenu(e: MouseEvent, key: string) {
  e.preventDefault();
  e.stopPropagation();
  ctxMenu.value = { x: e.clientX, y: e.clientY, key };
}

function closeCtxMenu() {
  ctxMenu.value = null;
}

function hideConv(key: string) {
  const next = new Set([...hiddenConvKeys.value, key]);
  hiddenConvKeys.value = next;
  saveHiddenKeys(next);
  swipedKey.value = null;
  ctxMenu.value = null;
  if (activeConv.value && convKey(activeConv.value) === key) {
    activeConv.value = null;
  }
}

function unhideConv(key: string) {
  if (!hiddenConvKeys.value.has(key)) return;
  const next = new Set(hiddenConvKeys.value);
  next.delete(key);
  hiddenConvKeys.value = next;
  saveHiddenKeys(next);
}

// ── File type icon mapping ────────────────────────────────────────────
function getFileIconComponent(mime: string, name: string) {
  const ext = name.split(".").pop()?.toLowerCase() || "";
  if (
    mime.startsWith("image/") ||
    [
      "jpg",
      "jpeg",
      "png",
      "gif",
      "webp",
      "bmp",
      "svg",
      "ico",
      "tiff",
      "avif",
    ].includes(ext)
  )
    return FileImage;
  if (
    mime.startsWith("video/") ||
    [
      "mp4",
      "mov",
      "avi",
      "mkv",
      "webm",
      "flv",
      "wmv",
      "m4v",
      "ogv",
      "ts",
    ].includes(ext)
  )
    return Film;
  if (
    mime.startsWith("audio/") ||
    ["mp3", "wav", "ogg", "flac", "aac", "m4a", "opus", "wma", "aiff"].includes(
      ext,
    )
  )
    return Music;
  if (["pdf"].includes(ext)) return FileText;
  if (["doc", "docx", "odt", "rtf"].includes(ext)) return FileText;
  if (["xls", "xlsx", "csv", "ods"].includes(ext)) return FileSpreadsheet;
  if (["ppt", "pptx", "odp"].includes(ext)) return FileText;
  if (["zip", "rar", "7z", "tar", "gz", "bz2", "xz", "zst"].includes(ext))
    return FileArchive;
  if (
    [
      "js",
      "ts",
      "py",
      "java",
      "c",
      "cpp",
      "h",
      "go",
      "rs",
      "rb",
      "php",
      "html",
      "css",
      "json",
      "xml",
      "yaml",
      "yml",
      "sh",
      "bat",
      "sql",
      "vue",
      "jsx",
      "tsx",
      "swift",
      "kt",
    ].includes(ext)
  )
    return FileCode;
  return FileIcon;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / (1024 * 1024)).toFixed(1) + " MB";
}

function isImageMime(mime: string): boolean {
  return mime.startsWith("image/");
}

// ── Code copy handler (delegated, attached to chat-page) ─────────────
function handleCopyCode(e: MouseEvent) {
  const btn = (e.target as HTMLElement).closest(
    ".code-copy-btn",
  ) as HTMLElement | null;
  if (!btn) return;
  const pre = btn.closest("pre");
  if (!pre) return;
  const code = pre.querySelector("code")?.innerText ?? "";
  navigator.clipboard.writeText(code).then(() => {
    btn.classList.add("copied");
    setTimeout(() => btn.classList.remove("copied"), 1500);
  });
}

// ── Rich text rendering ───────────────────────────────────────────────
function renderRichText(raw: string): string {
  let text = raw || "";
  let counter = 0;
  const mathMap: Record<string, { math: string; displayMode: boolean }> = {};

  const saveMath = (math: string, displayMode: boolean): string => {
    const id = `MATHPLACEHOLDER${counter++}END`;
    mathMap[id] = { math, displayMode };
    return id;
  };

  text = text.replace(/\$\$([\s\S]+?)\$\$/g, (_, m) => saveMath(m, true));
  text = text.replace(/\\\[([\s\S]+?)\\\]/g, (_, m) => saveMath(m, true));
  text = text.replace(/\\\(([\s\S]+?)\\\)/g, (_, m) => saveMath(m, false));
  text = text.replace(
    /(^|[^\\])\$([^$\n]+?)\$/g,
    (_, prefix, m) => prefix + saveMath(m, false),
  );

  const renderer = new marked.Renderer();
  renderer.code = ({
    text: codeText,
    lang,
  }: {
    text: string;
    lang?: string;
  }) => {
    const result = lang
      ? hljs.getLanguage(lang)
        ? hljs.highlight(codeText, { language: lang })
        : hljs.highlightAuto(codeText)
      : hljs.highlightAuto(codeText);
    const highlighted = result.value;
    const copySvg = `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="14" height="14" x="8" y="8" rx="2" ry="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/></svg>`;
    const checkSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>`;
    const langLabel = lang ? `<span class="code-lang">${lang}</span>` : "";
    return `<pre class="hljs-pre">${langLabel}<button class="code-copy-btn" title="复制代码"><span class="icon-copy">${copySvg}</span><span class="icon-check">${checkSvg}</span></button><code class="hljs">${highlighted}</code></pre>`;
  };

  let parsedHtml = marked.parse(text, {
    breaks: true,
    gfm: true,
    renderer,
  }) as string;

  parsedHtml = DOMPurify.sanitize(parsedHtml, {
    ALLOWED_TAGS: [
      "b",
      "i",
      "em",
      "strong",
      "a",
      "p",
      "br",
      "ul",
      "ol",
      "li",
      "span",
      "div",
      "code",
      "pre",
      "h1",
      "h2",
      "h3",
      "h4",
      "h5",
      "h6",
      "blockquote",
      "img",
      "table",
      "thead",
      "tbody",
      "tr",
      "th",
      "td",
      "hr",
      "del",
      "s",
      "button",
      "svg",
      "rect",
      "path",
      "polyline",
    ],
    ALLOWED_ATTR: [
      "href",
      "title",
      "class",
      "style",
      "src",
      "alt",
      "target",
      "rel",
      "xmlns",
      "width",
      "height",
      "viewBox",
      "fill",
      "stroke",
      "stroke-width",
      "stroke-linecap",
      "stroke-linejoin",
      "x",
      "y",
      "rx",
      "ry",
      "d",
      "points",
    ],
  });

  for (const id in mathMap) {
    const { math, displayMode } = mathMap[id];
    try {
      const rendered = katex.renderToString(math, {
        displayMode,
        throwOnError: false,
      });
      parsedHtml = parsedHtml.replace(id, rendered);
    } catch {
      parsedHtml = parsedHtml.replace(
        id,
        '<span class="latex-error">[LaTeX 错误]</span>',
      );
    }
  }

  return parsedHtml;
}

// ── Responsive ────────────────────────────────────────────────────────
function checkMobile() {
  isMobile.value = window.innerWidth < 768;
}

// ── Data loading ──────────────────────────────────────────────────────
async function loadConversations() {
  try {
    const freshList = await fetchConversations();

    const activePeer = activeConv.value?.peer_id;
    const activeTask = activeConv.value?.task_id;

    if (activePeer !== undefined) {
      const existsInFresh = freshList.some(
        (c) => c.peer_id === activePeer && c.task_id === activeTask,
      );
      if (!existsInFresh && activeConv.value) {
        freshList.unshift(activeConv.value);
      }
    }

    conversations.value = freshList;

    // auto-unhide any hidden conversation that now has new unread messages
    for (const c of freshList) {
      const k = convKey(c);
      if (hiddenConvKeys.value.has(k) && c.unread_count > 0) {
        unhideConv(k);
      }
    }

    if (activeConv.value) {
      const updated = freshList.find(
        (c) =>
          c.peer_id === activeConv.value!.peer_id &&
          c.task_id === activeConv.value!.task_id,
      );
      if (updated) activeConv.value = updated;
    }
  } catch {
    /* ignore */
  }
}

async function loadMessages() {
  if (!activeConv.value) return;
  loading.value = true;
  try {
    messages.value = await fetchMessages(
      activeConv.value.peer_id,
      activeConv.value.task_id,
    );
    await markRead(activeConv.value.peer_id, activeConv.value.task_id);
    notifStore.pollCount();
    if (activeConv.value) activeConv.value.unread_count = 0;
  } catch {
    /* ignore */
  }
  loading.value = false;
  await nextTick();
  scrollToBottom();
}

async function openAttachmentModal() {
  if (!activeConv.value) return;
  showAttachmentModal.value = true;
  await loadAllAttachments();
}

function scrollToBottom() {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
  }
}

// ── Actions ───────────────────────────────────────────────────────────
async function selectConversation(conv: Conversation) {
  const key = convKey(conv);
  unhideConv(key); // re-show if it was hidden
  activeConv.value = conv;
  messages.value = [];
  attachments.value = [];
  taskPreview.value = null;
  peerWorkerProfile.value = null;
  peerWorkerReviews.value = [];

  const query: Record<string, string> = { peer: String(conv.peer_id) };
  if (conv.task_id) query.task = String(conv.task_id);
  router.replace({ path: "/chat", query });

  const tasks: Promise<unknown>[] = [
    loadMessages(),
    loadAllAttachments(),
    prefetchPeerProfile(conv.peer_id),
  ];
  if (conv.task_id) tasks.push(prefetchTaskDetail(conv.task_id));
  await Promise.all(tasks);
}

async function loadAllAttachments() {
  if (!activeConv.value) return;
  try {
    attachments.value = await fetchAttachments(
      activeConv.value.peer_id,
      activeConv.value.task_id,
    );
    attachmentCount.value = { count: attachments.value.length, limit: 5 };
  } catch {
    /* ignore */
  }
}

async function handleSend() {
  if (
    !inputText.value.trim() ||
    !activeConv.value ||
    isBlocked.value ||
    sending.value
  )
    return;
  sending.value = true;
  try {
    const msg = await sendMessage(
      activeConv.value.peer_id,
      inputText.value.trim(),
      activeConv.value.task_id,
    );
    messages.value.push(msg);
    inputText.value = "";
    await nextTick();
    scrollToBottom();
    loadConversations();
  } catch {
    /* ignore */
  }
  sending.value = false;
}

function handleKeyDown(e: KeyboardEvent) {
  if (isMobile.value) return;
  if (e.key === "Enter" && !e.shiftKey && !e.ctrlKey && !e.metaKey) {
    e.preventDefault();
    handleSend();
  }
}

async function handleFileUpload(e: Event) {
  const input = e.target as HTMLInputElement;
  const files = input.files;
  if (!files || files.length === 0 || !activeConv.value) return;

  const fileList = Array.from(files);

  if (fileList.length > 5) {
    showToast("一次最多选择 5 个文件", "warning");
    input.value = "";
    return;
  }

  const remaining = attachmentCount.value.limit - attachmentCount.value.count;
  if (remaining <= 0) {
    showToast(
      `每个会话最多上传 ${attachmentCount.value.limit} 个附件，请先删除已有附件`,
      "warning",
    );
    input.value = "";
    return;
  }

  const toUpload = fileList.slice(0, remaining).filter((f) => {
    if (f.size > 10 * 1024 * 1024) {
      showToast(`「${f.name}」超过 10 MB，已跳过`, "error");
      return false;
    }
    return true;
  });

  if (toUpload.length === 0) {
    input.value = "";
    return;
  }
  if (fileList.length > remaining) {
    showToast(
      `附件剩余配额 ${remaining} 个，已自动截取前 ${toUpload.length} 个文件`,
      "warning",
    );
  }

  uploadingFile.value = true;
  try {
    // 多文件批量上传：发一条汇总消息，所有文件归到同一条消息（同一行展示）
    const fileNames = toUpload.map((f) => f.name).join("、");
    const msgContent =
      toUpload.length === 1
        ? `${ATTACHMENT_MSG_PREFIX} ${toUpload[0].name}`
        : `${ATTACHMENT_MSG_PREFIX} ${fileNames}（共 ${toUpload.length} 个文件）`;

    const msg = await sendMessage(
      activeConv.value!.peer_id,
      msgContent,
      activeConv.value!.task_id,
    );
    messages.value.push(msg);
    await nextTick();
    scrollToBottom();

    // 并发上传所有文件，均挂到同一条消息下
    const results = await Promise.allSettled(
      toUpload.map((f) =>
        uploadAttachment(
          activeConv.value!.peer_id,
          f,
          activeConv.value!.task_id,
          msg.id,
        ),
      ),
    );
    for (const r of results) {
      if (r.status === "fulfilled") {
        attachments.value.unshift(r.value);
        attachmentCount.value.count++;
      }
    }
    const failCount = results.filter((r) => r.status === "rejected").length;
    if (failCount > 0) showToast(`${failCount} 个文件上传失败`, "error");
  } catch (err: any) {
    showToast(err?.response?.data?.detail || "上传失败", "error");
  }
  uploadingFile.value = false;
  input.value = "";
}

async function handleDeleteAttachment(att: ChatAttachment) {
  const confirmed = await appConfirm({
    title: "删除附件",
    message: `确定删除附件「${att.file_name}」吗？删除后不可恢复。`,
    confirmText: "删除",
    type: "danger",
  });
  if (!confirmed) return;
  try {
    await deleteAttachment(att.id);
    attachments.value = attachments.value.filter((a) => a.id !== att.id);
    attachmentCount.value.count--;
    showToast("附件已删除", "success");
  } catch {
    /* ignore */
  }
}

function goBack() {
  activeConv.value = null;
}

// ── Task preview modal ────────────────────────────────────────────────
const taskPreview = ref<Task | null>(null);
const showTaskPreview = ref(false);

function openTaskDetail() {
  if (!activeConv.value?.task_id) return;
  showTaskPreview.value = true;
}

async function prefetchTaskDetail(taskId: number) {
  try {
    taskPreview.value = await fetchTask(taskId);
  } catch {
    /* ignore */
  }
}

async function prefetchPeerProfile(peerId: number) {
  try {
    const [profile, reviews] = await Promise.all([
      fetchWorkerDetail(peerId),
      fetchUserReviews(peerId, "worker"),
    ]);
    peerWorkerProfile.value = profile;
    peerWorkerReviews.value = reviews;
  } catch {
    /* not a worker or not found */
  }
}

function openUserDetail() {
  if (!activeConv.value) return;
  showUserDetailModal.value = true;
}

function openReportModal() {
  if (!activeConv.value) return;
  showReportModal.value = true;
}

async function handleBlockToggle() {
  if (!activeConv.value) return;
  const conv = activeConv.value;
  if (conv.blocked_by_me) {
    const confirmed = await appConfirm({
      title: "解除拉黑",
      message: `确定解除对「${conv.peer_name}」的拉黑吗？`,
      confirmText: "解除拉黑",
      type: "warning",
    });
    if (!confirmed) return;
    try {
      await unblockUser(conv.peer_id);
      showToast(`已解除对「${conv.peer_name}」的拉黑`, "success");
      await loadConversations();
    } catch (e: any) {
      showToast(e?.response?.data?.detail || "操作失败", "error");
    }
  } else {
    const confirmed = await appConfirm({
      title: "拉黑用户",
      message: `确定拉黑「${conv.peer_name}」吗？拉黑后双方将无法发送消息。`,
      confirmText: "拉黑",
      type: "danger",
    });
    if (!confirmed) return;
    try {
      await blockUser({ blocked_user_id: conv.peer_id });
      showToast(`已拉黑「${conv.peer_name}」`, "success");
      await loadConversations();
    } catch (e: any) {
      showToast(e?.response?.data?.detail || "操作失败", "error");
    }
  }
}

// ── Textarea auto-resize ──────────────────────────────────────────────
watch(inputText, () => {
  nextTick(() => {
    const el = textareaRef.value;
    if (!el) return;
    el.style.height = "0px";
    const h = Math.min(Math.max(el.scrollHeight, 38), 120);
    el.style.height = h + "px";
    el.style.overflowY = el.scrollHeight > 120 ? "auto" : "hidden";
  });
});

// ── Computed ──────────────────────────────────────────────────────────
const isBlocked = computed(() => {
  if (!activeConv.value) return false;
  return activeConv.value.blocked_by_me || activeConv.value.blocked_by_them;
});

const blockReason = computed(() => {
  if (!activeConv.value) return "";
  if (activeConv.value.blocked_by_me && activeConv.value.blocked_by_them)
    return "双方已相互拉黑";
  if (activeConv.value.blocked_by_me) return "您已拉黑此用户";
  if (activeConv.value.blocked_by_them) return "对方已将您拉黑";
  return "";
});

const filteredConversations = computed(() => {
  const base = conversations.value.filter(
    (c) => !hiddenConvKeys.value.has(convKey(c)),
  );
  if (!searchQuery.value.trim()) return base;
  const q = searchQuery.value.toLowerCase();
  return base.filter(
    (c) =>
      c.peer_name.toLowerCase().includes(q) ||
      (c.task_title && c.task_title.toLowerCase().includes(q)),
  );
});

const statusMap: Record<string, { label: string; cls: string }> = {
  open: { label: "待接取", cls: "status-open" },
  in_progress: { label: "进行中", cls: "status-active" },
  completed: { label: "已完成", cls: "status-done" },
  canceled: { label: "已取消", cls: "status-canceled" },
  under_review: { label: "进行中", cls: "status-active" },
};

function snapshotStatusLabel(s: string | null): string {
  if (!s) return "未知";
  return statusMap[s]?.label ?? s;
}

function snapshotStatusClass(s: string | null): string {
  if (!s) return "";
  return statusMap[s]?.cls ?? "";
}

const ATTACHMENT_MSG_PREFIX = "📎 [附件]";

function isAttachmentOnly(msg: ChatMessage): boolean {
  return msg.content.startsWith(ATTACHMENT_MSG_PREFIX);
}

function getAttachmentFileName(msg: ChatMessage): string {
  return msg.content.replace(ATTACHMENT_MSG_PREFIX, "").trim();
}

function getMessageAttachments(msgId: number): ChatAttachment[] {
  return attachments.value.filter((a) => a.message_id === msgId);
}

const peerOnlineStatus = computed(() => {
  if (!activeConv.value) return { online: false, text: "" };
  return formatLastSeen(activeConv.value.peer_last_active);
});

// ── Lifecycle ─────────────────────────────────────────────────────────
onMounted(async () => {
  checkMobile();
  window.addEventListener("resize", checkMobile);

  await loadConversations();

  const peerId = Number(route.query.peer);
  const taskId = route.query.task ? Number(route.query.task) : null;

  if (peerId) {
    let found = conversations.value.find(
      (c) => c.peer_id === peerId && c.task_id === taskId,
    );
    if (!found) {
      try {
        const userInfo = await fetchUserPublic(peerId);

        let taskTitle: string | null = null;
        let taskPrice: number | null = null;
        let taskStatus: string | null = null;
        let taskIcon: string | null = null;
        if (taskId) {
          try {
            const taskInfo = await fetchTask(taskId);
            taskTitle = taskInfo.title;
            taskPrice = taskInfo.price;
            taskStatus = taskInfo.status;
            taskIcon = taskInfo.icon ?? null;
          } catch {
            /* task not found */
          }
        }

        const placeholder: Conversation = {
          peer_id: peerId,
          peer_name: userInfo.display_name,
          peer_avatar: userInfo.avatar_url,
          peer_gender: userInfo.gender ?? null,
          peer_last_active: null,
          task_id: taskId,
          task_title: taskTitle,
          task_price: taskPrice,
          task_status: taskStatus,
          task_icon: taskIcon,
          last_message: null,
          last_message_time: null,
          unread_count: 0,
          blocked_by_me: false,
          blocked_by_them: false,
        };
        conversations.value.unshift(placeholder);
        found = placeholder;
      } catch {
        /* user not found */
      }
    }
    if (found) {
      selectConversation(found);
    }
  } else if (!isMobile.value && conversations.value.length > 0) {
    selectConversation(conversations.value[0]);
  }

  pollTimer = setInterval(async () => {
    await loadConversations();
    if (activeConv.value) {
      const prev = messages.value;
      const latest = await fetchMessages(
        activeConv.value.peer_id,
        activeConv.value.task_id,
      );
      if (
        latest.length !== prev.length ||
        (latest.length > 0 &&
          latest[latest.length - 1].id !== prev[prev.length - 1]?.id)
      ) {
        messages.value = latest;
        await Promise.all([
          markRead(activeConv.value.peer_id, activeConv.value.task_id),
          loadAllAttachments(),
        ]);
        notifStore.pollCount();
        if (activeConv.value) activeConv.value.unread_count = 0;
        await nextTick();
        scrollToBottom();
      }
    }
  }, 5000);
});

onMounted(() => {
  document.addEventListener("click", closeCtxMenu);
});

onUnmounted(() => {
  window.removeEventListener("resize", checkMobile);
  document.removeEventListener("click", closeCtxMenu);
  if (pollTimer) clearInterval(pollTimer);
});
</script>

<template>
  <div class="chat-outer">
    <HomeHeaderBar
      :active-tab="null"
      :app-title="appTitle"
      :is-authenticated="isAuthenticated"
      :display-name="displayName"
      :avatar-url="avatarUrl"
      :gender="avatarGender"
      @publish="router.push('/')"
      @open-my-panel="router.push('/?panel=my')"
      @open-settings="router.push('/settings')"
      @open-reports="router.push('/reports')"
      @open-chat="router.push('/chat')"
      @login="router.push('/login')"
      @logout="auth.logout(); router.push('/login')"
      @update:active-tab="(tab) => router.push(tab === 'workers' ? '/?tab=workers' : '/')"
    />

  <div
    class="chat-page"
    @click="
      handleCopyCode;
      closeCtxMenu();
    "
    @contextmenu.self="closeCtxMenu"
  >
    <!-- 左侧边栏 -->
    <aside
      class="chat-sidebar"
      :class="{ 'sidebar-hidden': activeConv && isMobile }"
    >
      <div class="sidebar-header">
        <h1 class="sidebar-title">消息中心</h1>
        <div class="sidebar-search-inline">
          <Search class="search-icon-inline" :size="14" />
          <input
            v-model="searchQuery"
            type="text"
            placeholder="搜索..."
            class="search-input-inline"
          />
        </div>
      </div>

      <div
        class="contact-list"
        @click="
          closeSwipe();
          closeCtxMenu();
        "
      >
        <div
          v-for="conv in filteredConversations"
          :key="convKey(conv)"
          class="contact-item-wrap"
          :class="{ swiped: isMobile && swipedKey === convKey(conv) }"
          @touchstart.passive="isMobile && onSwipeStart($event, convKey(conv))"
          @touchmove.passive="isMobile && onSwipeMove($event, convKey(conv))"
          @touchend.passive="isMobile && onSwipeEnd()"
          @contextmenu.prevent="
            !isMobile && onContextMenu($event, convKey(conv))
          "
        >
          <div
            class="contact-item"
            :class="{
              active:
                activeConv?.peer_id === conv.peer_id &&
                activeConv?.task_id === conv.task_id,
              blocked: conv.blocked_by_me || conv.blocked_by_them,
            }"
            @click.stop="
              closeSwipe();
              closeCtxMenu();
              selectConversation(conv);
            "
          >
            <div class="contact-avatar-wrap">
              <HomeAvatar
                :avatar-url="conv.peer_avatar"
                :gender="conv.peer_gender"
                size="lg"
                :alt="conv.peer_name"
              />
              <div
                v-if="conv.blocked_by_me || conv.blocked_by_them"
                class="avatar-badge blocked-badge"
              >
                <ShieldAlert :size="10" />
              </div>
              <div
                v-else-if="formatLastSeen(conv.peer_last_active).online"
                class="avatar-badge online-badge"
              ></div>
            </div>
            <div class="contact-info">
              <div class="contact-top-row">
                <span
                  class="contact-name"
                  :class="{
                    'name-blocked': conv.blocked_by_me || conv.blocked_by_them,
                  }"
                  >{{ conv.peer_name }}</span
                >
                <span class="contact-time">{{
                  conv.last_message_time
                    ? formatChatTime(conv.last_message_time)
                    : ""
                }}</span>
              </div>
              <div class="contact-bottom-row">
                <span class="contact-preview">{{
                  conv.last_message || "暂无消息"
                }}</span>
                <span v-if="conv.unread_count > 0" class="unread-badge">{{
                  conv.unread_count > 99 ? "99+" : conv.unread_count
                }}</span>
              </div>
            </div>
          </div>
          <button
            v-if="isMobile"
            class="swipe-delete-btn"
            @click.stop="hideConv(convKey(conv))"
          >
            <Trash2 :size="18" />
          </button>
        </div>

        <div v-if="filteredConversations.length === 0" class="no-contacts">
          <MessageSquare :size="32" />
          <p>暂无聊天记录</p>
        </div>
      </div>
    </aside>

    <!-- 右侧聊天区域 -->
    <main class="chat-main" :class="{ 'main-hidden': !activeConv && isMobile }">
      <!-- 未选中联系人 -->
      <div v-if="!activeConv" class="chat-empty">
        <MessageSquare :size="64" class="empty-icon" />
        <p>从左侧选择一个联系人开始聊天</p>
      </div>

      <!-- 聊天界面 -->
      <template v-else>
        <!-- 顶栏 -->
        <div class="chat-header">
          <div class="header-top">
            <div class="header-left">
              <button v-if="isMobile" class="icon-btn back-btn" @click="goBack">
                <ArrowLeft :size="22" />
              </button>
              <div class="header-avatar-container">
                <HomeAvatar
                  :avatar-url="activeConv.peer_avatar"
                  :gender="activeConv.peer_gender"
                  size="lg"
                  :alt="activeConv.peer_name"
                  class="header-avatar-wrap"
                />
                <span
                  v-if="peerOnlineStatus.online"
                  class="header-online-dot"
                ></span>
              </div>
              <div>
                <h2 class="header-name" :class="{ 'name-blocked': isBlocked }">
                  {{ activeConv.peer_name }}
                </h2>
                <p
                  class="header-last-seen"
                  :class="{ 'last-seen-online': peerOnlineStatus.online }"
                >
                  {{ peerOnlineStatus.text }}
                </p>
              </div>
            </div>
            <div class="header-actions">
              <button
                class="icon-btn"
                title="举报此用户"
                @click="openReportModal"
              >
                <Flag :size="18" />
              </button>
              <button
                class="icon-btn"
                :class="{ 'btn-blocked': activeConv.blocked_by_me }"
                :title="activeConv.blocked_by_me ? '解除拉黑' : '拉黑此用户'"
                @click="handleBlockToggle"
              >
                <ShieldOff :size="18" />
              </button>
              <button class="icon-btn" @click="openAttachmentModal">
                <Paperclip :size="18" />
                <span
                  v-if="attachmentCount.count > 0"
                  class="att-count-badge"
                  >{{ attachmentCount.count }}</span
                >
              </button>
            </div>
          </div>

          <!-- 任务快照 / 来源 -->
          <div
            class="banner-area"
            :class="{ 'banner-collapsed': isBannerCollapsed }"
          >
            <div class="banner-content">
              <!-- 任务快照 -->
              <div
                v-if="activeConv.task_id"
                class="task-snapshot task-snapshot--clickable"
                @click="openTaskDetail"
              >
                <div
                  class="snapshot-icon-wrap"
                  :style="{ background: getTaskIcon(activeConv.task_icon).bg }"
                >
                  <component
                    :is="getTaskIcon(activeConv.task_icon).component"
                    :size="16"
                    :style="{ color: getTaskIcon(activeConv.task_icon).color }"
                  />
                </div>
                <span class="snapshot-badge">快照</span>
                <span class="snapshot-title">{{
                  activeConv.task_title || "未知任务"
                }}</span>
                <div class="snapshot-right">
                  <span class="snapshot-price"
                    >¥{{ activeConv.task_price ?? "—" }}</span
                  >
                  <span
                    class="snapshot-status"
                    :class="snapshotStatusClass(activeConv.task_status)"
                  >
                    {{ snapshotStatusLabel(activeConv.task_status) }}
                  </span>
                </div>
              </div>
              <!-- 来自接单广场 -->
              <div
                v-else
                class="marketplace-badge marketplace-badge--clickable"
                @click="openUserDetail"
              >
                <Compass :size="16" />
                <span>来自接单广场 · 查看对方资料</span>
              </div>
            </div>
            <button
              class="collapse-toggle"
              @click="isBannerCollapsed = !isBannerCollapsed"
            >
              <ChevronUp
                :size="12"
                class="collapse-chevron"
                :class="{ rotated: isBannerCollapsed }"
              />
            </button>
          </div>
        </div>

        <!-- 消息列表 -->
        <div ref="messagesContainer" class="chat-messages">
          <div v-if="loading" class="messages-loading">
            <div class="spinner"></div>
          </div>

          <div v-else-if="messages.length === 0" class="messages-empty">
            <MessageSquare :size="48" class="empty-icon" />
            <p>暂无聊天记录，开始打个招呼吧</p>
          </div>

          <template v-else>
            <div
              v-for="msg in messages"
              :key="msg.id"
              class="message-row"
              :class="{
                'msg-own': msg.sender_id === myId,
                'msg-other': msg.sender_id !== myId,
              }"
            >
              <!-- 对方消息：不放气泡 -->
              <template v-if="msg.sender_id !== myId">
                <div class="msg-other-wrap">
                  <div class="msg-meta-other">
                    <HomeAvatar
                      :avatar-url="activeConv.peer_avatar"
                      :gender="activeConv.peer_gender"
                      size="sm"
                      :alt="activeConv.peer_name"
                      class="msg-avatar-wrap"
                    />
                    <span class="msg-sender">{{ activeConv.peer_name }}</span>
                    <span class="msg-time">{{
                      formatChatTime(msg.created_at)
                    }}</span>
                  </div>
                  <div
                    v-if="!isAttachmentOnly(msg)"
                    class="msg-content-other bubble-other"
                  >
                    <div
                      class="rich-text"
                      v-html="renderRichText(msg.content)"
                    ></div>
                  </div>
                  <!-- 附件预览 -->
                  <div
                    v-if="getMessageAttachments(msg.id).length"
                    class="msg-attachments"
                  >
                    <div
                      v-for="att in getMessageAttachments(msg.id)"
                      :key="att.id"
                      class="att-preview-item"
                    >
                      <a
                        :href="att.file_url"
                        target="_blank"
                        class="att-preview-link"
                      >
                        <img
                          v-if="isImageMime(att.mime_type)"
                          :src="att.file_url"
                          class="att-thumb"
                        />
                        <div v-else class="att-icon-thumb">
                          <component
                            :is="
                              getFileIconComponent(att.mime_type, att.file_name)
                            "
                            :size="24"
                          />
                          <span class="att-ext">{{
                            att.file_name.split(".").pop()?.toUpperCase()
                          }}</span>
                        </div>
                      </a>
                    </div>
                  </div>
                  <div
                    v-else-if="isAttachmentOnly(msg)"
                    class="msg-attachments"
                  >
                    <div
                      class="att-preview-item"
                      @click="showToast('文件不存在', 'warning')"
                    >
                      <div class="att-preview-link att-deleted-link">
                        <div class="att-icon-thumb att-deleted-style">
                          <component
                            :is="
                              getFileIconComponent(
                                '',
                                getAttachmentFileName(msg),
                              )
                            "
                            :size="24"
                          />
                          <span class="att-ext">{{
                            getAttachmentFileName(msg)
                              .split(".")
                              .pop()
                              ?.toUpperCase() || "文件"
                          }}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </template>

              <!-- 己方消息：气泡 -->
              <template v-else>
                <div class="msg-own-wrap">
                  <div class="msg-meta-own">
                    <span class="msg-time">{{
                      formatChatTime(msg.created_at)
                    }}</span>
                    <CheckCheck
                      v-if="msg.is_read"
                      :size="14"
                      class="status-read"
                    />
                    <Check v-else :size="14" class="status-sent" />
                    <span class="msg-sender-me">我</span>
                  </div>
                  <div
                    v-if="!isAttachmentOnly(msg)"
                    class="msg-bubble-own bubble-own"
                  >
                    <div
                      class="rich-text"
                      v-html="renderRichText(msg.content)"
                    ></div>
                  </div>
                  <!-- 附件预览 -->
                  <div
                    v-if="getMessageAttachments(msg.id).length"
                    class="msg-attachments own-attachments"
                  >
                    <div
                      v-for="att in getMessageAttachments(msg.id)"
                      :key="att.id"
                      class="att-preview-item"
                    >
                      <a
                        :href="att.file_url"
                        target="_blank"
                        class="att-preview-link"
                      >
                        <img
                          v-if="isImageMime(att.mime_type)"
                          :src="att.file_url"
                          class="att-thumb"
                        />
                        <div v-else class="att-icon-thumb">
                          <component
                            :is="
                              getFileIconComponent(att.mime_type, att.file_name)
                            "
                            :size="24"
                          />
                          <span class="att-ext">{{
                            att.file_name.split(".").pop()?.toUpperCase()
                          }}</span>
                        </div>
                      </a>
                    </div>
                  </div>
                  <div
                    v-else-if="isAttachmentOnly(msg)"
                    class="msg-attachments own-attachments"
                  >
                    <div
                      class="att-preview-item"
                      @click="showToast('文件不存在', 'warning')"
                    >
                      <div class="att-preview-link att-deleted-link">
                        <div class="att-icon-thumb att-deleted-style">
                          <component
                            :is="
                              getFileIconComponent(
                                '',
                                getAttachmentFileName(msg),
                              )
                            "
                            :size="24"
                          />
                          <span class="att-ext">{{
                            getAttachmentFileName(msg)
                              .split(".")
                              .pop()
                              ?.toUpperCase() || "文件"
                          }}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </template>
            </div>
          </template>
        </div>

        <!-- 输入区域 -->
        <div class="chat-input-area">
          <div v-if="isBlocked" class="blocked-notice">
            <ShieldAlert :size="18" />
            <span>{{ blockReason }}，无法发送消息</span>
          </div>
          <div v-else class="input-wrap">
            <div class="capsule-input">
              <label
                class="file-upload-btn"
                :class="{ disabled: uploadingFile }"
              >
                <Plus :size="20" />
                <input
                  type="file"
                  class="file-input-hidden"
                  multiple
                  @change="handleFileUpload"
                  :disabled="uploadingFile"
                />
              </label>
              <textarea
                ref="textareaRef"
                v-model="inputText"
                placeholder="发送消息..."
                class="msg-textarea"
                @keydown="handleKeyDown"
              ></textarea>
              <button
                class="send-btn"
                :class="{ active: inputText.trim() }"
                :disabled="!inputText.trim() || sending"
                @click="handleSend"
              >
                <ArrowUp :size="20" />
              </button>
            </div>
            <div class="input-hint">
              {{
                isMobile ? "点击发送按钮发送" : "Enter 发送 · Shift+Enter 换行"
              }}
            </div>
          </div>
        </div>
      </template>
    </main>

    <!-- 附件管理弹窗 -->
    <Teleport to="body">
      <Transition name="modal-fade">
        <div
          v-if="showAttachmentModal"
          class="modal-overlay"
          @click.self="showAttachmentModal = false"
        >
          <div class="modal-panel">
            <div class="modal-header">
              <h3>附件管理</h3>
              <span class="modal-count"
                >{{ attachmentCount.count }} / {{ attachmentCount.limit }}</span
              >
              <button class="icon-btn" @click="showAttachmentModal = false">
                <X :size="20" />
              </button>
            </div>
            <div class="modal-body">
              <div v-if="attachments.length === 0" class="modal-empty">
                <Paperclip :size="32" class="empty-icon" />
                <p>暂无附件</p>
              </div>
              <div v-else class="att-list">
                <div v-for="att in attachments" :key="att.id" class="att-item">
                  <div class="att-item-preview">
                    <img
                      v-if="isImageMime(att.mime_type)"
                      :src="att.file_url"
                      class="att-list-thumb"
                    />
                    <div v-else class="att-list-icon">
                      <component
                        :is="getFileIconComponent(att.mime_type, att.file_name)"
                        :size="28"
                      />
                    </div>
                  </div>
                  <div class="att-item-info">
                    <span class="att-item-name">{{ att.file_name }}</span>
                    <span class="att-item-size">{{
                      formatFileSize(att.file_size)
                    }}</span>
                  </div>
                  <div class="att-item-actions">
                    <a :href="att.file_url" target="_blank" class="icon-btn"
                      ><Download :size="16"
                    /></a>
                    <button
                      v-if="att.uploader_id === myId"
                      class="icon-btn danger"
                      @click="handleDeleteAttachment(att)"
                    >
                      <Trash2 :size="16" />
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- 右键菜单（桌面端） -->
    <Teleport to="body">
      <div
        v-if="ctxMenu"
        class="ctx-menu"
        :style="{ top: ctxMenu.y + 'px', left: ctxMenu.x + 'px' }"
        @click.stop
        @contextmenu.prevent.stop
      >
        <button
          class="ctx-menu-item ctx-menu-item--danger"
          @click="hideConv(ctxMenu!.key)"
        >
          <Trash2 :size="14" />
          从列表移除
        </button>
      </div>
    </Teleport>

    <!-- 任务预览弹窗 -->
    <Teleport to="body">
      <Transition name="modal-fade">
        <div
          v-if="showTaskPreview"
          class="modal-overlay"
          @click.self="showTaskPreview = false"
        >
          <div class="modal-panel task-preview-panel">
            <div class="modal-header">
              <div
                class="task-preview-icon"
                :style="{
                  background: getTaskIcon(taskPreview?.icon ?? null).bg,
                }"
              >
                <component
                  :is="getTaskIcon(taskPreview?.icon ?? null).component"
                  :size="16"
                  :style="{
                    color: getTaskIcon(taskPreview?.icon ?? null).color,
                  }"
                />
              </div>
              <h3>{{ taskPreview?.title || "加载中…" }}</h3>
              <button class="icon-btn" @click="showTaskPreview = false">
                <X :size="20" />
              </button>
            </div>
            <div v-if="!taskPreview" class="modal-body task-preview-loading">
              <div class="spinner"></div>
            </div>
            <div v-else class="modal-body task-preview-body">
              <div class="task-preview-meta">
                <span class="task-preview-price">¥{{ taskPreview.price }}</span>
                <span
                  class="task-preview-status"
                  :class="statusMap[taskPreview.status]?.cls"
                  >{{
                    statusMap[taskPreview.status]?.label ?? taskPreview.status
                  }}</span
                >
              </div>
              <div v-if="taskPreview.description" class="task-preview-desc">
                {{ taskPreview.description }}
              </div>
              <div class="task-preview-fields">
                <div v-if="taskPreview.deadline" class="task-preview-field">
                  <span class="field-label">截止时间</span>
                  <span
                    class="field-value"
                    :class="{
                      'field-expired': isExpired(taskPreview.deadline),
                    }"
                  >
                    {{ formatFull(taskPreview.deadline)
                    }}{{ isExpired(taskPreview.deadline) ? "（已过期）" : "" }}
                  </span>
                </div>
                <div v-if="taskPreview.location" class="task-preview-field">
                  <span class="field-label">地点</span>
                  <span class="field-value">{{ taskPreview.location }}</span>
                </div>
                <div class="task-preview-field">
                  <span class="field-label">发布者</span>
                  <span class="field-value">{{
                    taskPreview.publisher_display_name
                  }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- 用户资料弹窗 -->
    <Teleport to="body">
      <Transition name="modal-fade">
        <div
          v-if="showUserDetailModal"
          class="modal-overlay"
          @click.self="showUserDetailModal = false"
        >
          <div class="modal-panel user-detail-panel">
            <div class="modal-header">
              <UserIcon :size="18" class="header-icon-accent" />
              <h3>用户资料</h3>
              <button class="icon-btn" @click="showUserDetailModal = false">
                <X :size="20" />
              </button>
            </div>
            <div class="modal-body user-detail-body">
              <!-- 基本信息 -->
              <div class="user-detail-section user-detail-top-section">
                <div class="user-detail-card">
                  <HomeAvatar
                    :avatar-url="activeConv?.peer_avatar ?? null"
                    :gender="activeConv?.peer_gender ?? null"
                    size="xl"
                    :alt="activeConv?.peer_name ?? ''"
                    class="user-detail-avatar"
                  />
                  <div class="user-detail-info">
                    <h4 class="user-detail-name">
                      {{ activeConv?.peer_name }}
                    </h4>
                    <div class="user-detail-tags">
                      <span class="user-tag gender-tag">
                        {{
                          activeConv?.peer_gender === "male"
                            ? "男"
                            : activeConv?.peer_gender === "female"
                              ? "女"
                              : "未知性别"
                        }}
                      </span>
                      <span
                        class="user-tag online-tag"
                        :class="{ 'online-active': peerOnlineStatus.online }"
                      >
                        {{ peerOnlineStatus.text }}
                      </span>
                    </div>
                    <template v-if="peerWorkerProfile">
                      <div class="user-worker-rating">
                        <HomeStars
                          :value="
                            Math.round(peerWorkerProfile.overall_rating_avg)
                          "
                          size="sm"
                        />
                        <span class="rating-text">
                          {{
                            peerWorkerProfile.overall_rating_count > 0
                              ? `${peerWorkerProfile.overall_rating_avg.toFixed(1)} 分 · ${peerWorkerProfile.overall_rating_count} 评价`
                              : "暂无评分"
                          }}
                        </span>
                      </div>
                    </template>
                  </div>
                </div>

                <template v-if="peerWorkerProfile">
                  <div
                    v-if="peerWorkerProfile.skill_tags.length"
                    class="worker-skills"
                  >
                    <span
                      v-for="tag in peerWorkerProfile.skill_tags"
                      :key="tag.id"
                      class="skill-chip"
                      >{{ tag.name }}</span
                    >
                  </div>

                  <div class="hv-detail-grid">
                    <div class="hv-detail-item">
                      <span class="hv-detail-label">完成任务</span>
                      <span
                        >{{ peerWorkerProfile.worker_completed_count }} 单</span
                      >
                    </div>
                    <div class="hv-detail-item">
                      <span class="hv-detail-label">被拉黑</span>
                      <span>{{ peerWorkerProfile.blocked_by_count }} 次</span>
                    </div>
                    <div
                      v-if="
                        peerWorkerProfile.min_price != null ||
                        peerWorkerProfile.max_price != null
                      "
                      class="hv-detail-item"
                    >
                      <span class="hv-detail-label">报价区间</span>
                      <span
                        >¥{{ peerWorkerProfile.min_price ?? "—" }} ~ ¥{{
                          peerWorkerProfile.max_price ?? "—"
                        }}</span
                      >
                    </div>
                  </div>

                  <p v-if="peerWorkerProfile.bio" class="worker-bio">
                    {{ peerWorkerProfile.bio }}
                  </p>
                </template>
                <p v-else class="user-detail-no-worker">
                  该用户暂未开通接单服务
                </p>
              </div>

              <!-- 历史评价 -->
              <template v-if="peerWorkerProfile">
                <div class="user-detail-section">
                  <h4 class="user-detail-section-title">
                    <Star :size="14" />
                    历史评价
                  </h4>
                  <div v-if="peerWorkerReviews.length" class="user-reviews">
                    <div
                      v-for="r in peerWorkerReviews"
                      :key="r.id"
                      class="user-review-item"
                    >
                      <div class="user-review-header">
                        <HomeStars :value="r.stars" size="sm" />
                        <span class="user-review-meta"
                          >来自 {{ r.reviewer_display_name }} ·
                          {{ formatFull(r.created_at) }}</span
                        >
                      </div>
                      <p v-if="r.comment" class="user-review-comment">
                        {{ r.comment }}
                      </p>
                    </div>
                  </div>
                  <p v-else class="user-detail-hint">暂无历史评价</p>
                </div>
              </template>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- 举报弹窗（复用 HomeReportModal） -->
    <HomeReportModal
      v-model="showReportModal"
      :task-id="activeConv?.task_id ?? null"
      :reported-user-id="activeConv?.peer_id ?? null"
      :reported-user-name="activeConv?.peer_name"
      @success="showToast('举报已提交，请等待管理员审核', 'success')"
      @error="(msg) => showToast(msg, 'error')"
    />

    <AppToast :toast="toast" @dismiss="clearToast" />
  </div>

  </div>
</template>

<style scoped>
/* ── Layout ──────────────────────────────────────────────────────────── */
.chat-outer {
  display: flex;
  flex-direction: column;
  height: 100dvh;
  width: 100%;
  overflow: hidden;
}

.chat-page {
  display: flex;
  flex: 1;
  min-height: 0;
  width: 100%;
  background: var(--c-bg);
  color: var(--c-text);
  overflow: hidden;
}

@keyframes chat-rise {
  from {
    opacity: 0;
    transform: translateY(16px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* ── Sidebar ─────────────────────────────────────────────────────────── */
.chat-sidebar {
  display: flex;
  flex-direction: column;
  width: 320px;
  background: var(--c-surface);
  border-right: 1px solid var(--c-border);
  flex-shrink: 0;
  z-index: 20;
  animation: chat-rise 0.48s cubic-bezier(0.22, 1, 0.36, 1) 0ms both;
}

.sidebar-header {
  padding: 10px 16px;
  border-bottom: 1px solid var(--c-border-light);
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.sidebar-title {
  font-size: var(--text-lg);
  font-weight: 700;
  white-space: nowrap;
  flex-shrink: 0;
  background: linear-gradient(135deg, var(--c-accent), #7c3aed);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.sidebar-search-inline {
  flex: 1;
  min-width: 0;
  position: relative;
  display: flex;
  align-items: center;
}

.search-icon-inline {
  position: absolute;
  left: 10px;
  color: var(--c-text-muted);
  pointer-events: none;
}

.search-input-inline {
  width: 100%;
  padding: 6px 12px 6px 30px;
  background: var(--c-bg);
  border: 1.5px solid var(--c-border);
  border-radius: 999px;
  font-size: var(--text-sm);
  color: var(--c-text);
  outline: none;
  transition: border-color var(--dur-fast) var(--ease),
              box-shadow var(--dur-fast) var(--ease),
              background var(--dur-fast) var(--ease);
}

.search-input-inline::placeholder {
  color: var(--c-text-muted);
}

.search-input-inline:focus {
  border-color: var(--c-accent);
  box-shadow: 0 0 0 3px var(--c-accent-soft);
  background: var(--c-surface);
}

.contact-list {
  flex: 1;
  overflow-y: auto;
}

.contact-item-wrap {
  position: relative;
  overflow: hidden;
  margin: 4px 8px;
  border-radius: 12px;
}

.contact-item-wrap .contact-item {
  margin: 0;
  border-radius: 12px;
}

/* swipe mechanics only on touch devices */
@media (hover: none) and (pointer: coarse) {
  .contact-item-wrap .contact-item {
    transform: translateX(0);
    transition: transform 0.28s cubic-bezier(0.4, 0, 0.2, 1);
  }

  .contact-item-wrap.swiped .contact-item {
    transform: translateX(-72px);
  }

  .swipe-delete-btn {
    position: absolute;
    top: 0;
    right: 0;
    height: 100%;
    width: 72px;
    background: var(--c-danger);
    color: white;
    border: none;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    border-radius: 0 12px 12px 0;
    transform: translateX(100%);
    transition: transform 0.28s cubic-bezier(0.4, 0, 0.2, 1);
  }

  .contact-item-wrap.swiped .swipe-delete-btn {
    transform: translateX(0);
  }

  .swipe-delete-btn:hover {
    background: var(--c-danger-hover, #dc2626);
  }
}

/* ── Desktop context menu ────────────────────────────────────────────── */
.ctx-menu {
  position: fixed;
  z-index: 9000;
  background: var(--c-surface);
  border: 1px solid var(--c-border);
  border-radius: 10px;
  box-shadow: var(--shadow-lg);
  padding: 4px;
  min-width: 140px;
  animation: ctx-in 0.12s ease;
}

@keyframes ctx-in {
  from {
    opacity: 0;
    transform: scale(0.94);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

.ctx-menu-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 7px 12px;
  border: none;
  background: transparent;
  border-radius: 7px;
  font-size: var(--text-sm);
  cursor: pointer;
  color: var(--c-text);
  transition: background var(--dur-fast) var(--ease);
}

.ctx-menu-item:hover {
  background: var(--c-bg);
}

.ctx-menu-item--danger {
  color: var(--c-danger);
}
.ctx-menu-item--danger:hover {
  background: var(--c-danger-light);
}

.contact-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 12px;
  cursor: pointer;
  transition:
    background var(--dur-fast) var(--ease),
    border-color var(--dur-fast) var(--ease);
  border: 1px solid transparent;
}

.contact-item:hover {
  background: var(--c-bg);
}

.contact-item.active {
  background: var(--c-accent-light);
  border-color: var(--c-accent-soft);
  box-shadow: var(--shadow-xs);
}

.contact-avatar-wrap {
  position: relative;
  flex-shrink: 0;
}

.contact-avatar-wrap :deep(img) {
  border: 1px solid var(--c-border);
  box-shadow: var(--shadow-xs);
}

.avatar-badge {
  position: absolute;
  bottom: -2px;
  right: -2px;
  border: 2px solid var(--c-surface);
  border-radius: 50%;
}

.online-badge {
  width: 12px;
  height: 12px;
  background: var(--c-success);
}

.blocked-badge {
  background: var(--c-danger);
  color: white;
  padding: 1px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.contact-info {
  flex: 1;
  min-width: 0;
}

.contact-top-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.contact-name {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--c-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.contact-item.active .contact-name {
  color: #1e3a5f;
}

.name-blocked {
  color: var(--c-danger) !important;
}

.contact-time {
  font-size: var(--text-xs);
  color: var(--c-text-muted);
  flex-shrink: 0;
  margin-left: 8px;
}

.contact-bottom-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.contact-preview {
  font-size: var(--text-xs);
  color: var(--c-text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}

.unread-badge {
  background: var(--c-accent);
  color: white;
  font-size: 10px;
  font-weight: 700;
  min-width: 18px;
  height: 18px;
  border-radius: 9px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 5px;
  flex-shrink: 0;
}

.no-contacts {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 16px;
  color: var(--c-text-muted);
  gap: 8px;
}

/* ── Chat Main ───────────────────────────────────────────────────────── */
.chat-main {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
  background: #f8fafc;
  position: relative;
  animation: chat-rise 0.48s cubic-bezier(0.22, 1, 0.36, 1) 0.08s both;
}

.chat-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--c-text-muted);
  gap: 16px;
}

.empty-icon {
  opacity: 0.15;
}

/* ── Chat Header ─────────────────────────────────────────────────────── */
.chat-header {
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--c-border);
  position: sticky;
  top: 0;
  z-index: 10;
  flex-shrink: 0;
}

.header-top {
  padding: 12px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.back-btn {
  margin-left: -8px;
}

.header-avatar-container {
  position: relative;
  flex-shrink: 0;
}

.header-avatar-wrap :deep(img) {
  border: 1px solid var(--c-border);
}

.header-online-dot {
  position: absolute;
  bottom: 1px;
  right: 1px;
  width: 12px;
  height: 12px;
  background: #22c55e;
  border-radius: 50%;
  border: 2px solid white;
}

.header-name {
  font-size: var(--text-base);
  font-weight: 700;
  color: var(--c-text);
  line-height: 1.2;
}

.header-last-seen {
  font-size: 11px;
  color: var(--c-text-muted);
  margin: 0;
  line-height: 1.3;
}

.last-seen-online {
  color: #22c55e;
  font-weight: 500;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 2px;
  flex-shrink: 0;
}

.btn-blocked {
  color: var(--c-danger) !important;
}

.att-count-badge {
  position: absolute;
  top: -4px;
  right: -4px;
  background: var(--c-accent);
  color: white;
  font-size: 9px;
  font-weight: 700;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* ── Banner / Task Snapshot ──────────────────────────────────────────── */
.banner-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 0 24px;
}

.banner-content {
  width: 100%;
  overflow: hidden;
  max-height: 80px;
  transition:
    max-height 0.28s cubic-bezier(0.4, 0, 0.2, 1),
    opacity 0.22s ease,
    margin-bottom 0.28s ease;
  opacity: 1;
  margin-bottom: 2px;
}

.banner-area.banner-collapsed .banner-content {
  max-height: 0;
  opacity: 0;
  margin-bottom: 0;
}

.collapse-toggle {
  display: flex;
  width: 100%;
  height: 18px;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  background: transparent;
  border: none;
  color: var(--c-text-muted);
  opacity: 0.35;
  transition:
    opacity 0.2s ease,
    height 0.28s cubic-bezier(0.4, 0, 0.2, 1),
    background 0.15s ease;
  border-top: 1px solid var(--c-border-light);
  flex-shrink: 0;
}

.banner-area.banner-collapsed .collapse-toggle {
  height: 10px;
  border-top-color: transparent;
  opacity: 0.25;
}

.collapse-toggle:hover {
  opacity: 0.8;
  background: var(--c-bg);
}

.banner-area.banner-collapsed .collapse-toggle:hover {
  opacity: 0.6;
}

.task-snapshot {
  background: var(--c-surface);
  border: 1px solid var(--c-border);
  border-radius: 12px;
  box-shadow: var(--shadow-xs);
  margin-bottom: 4px;
  padding: 10px;
  display: flex;
  align-items: center;
  gap: 10px;
}

.task-snapshot--clickable {
  cursor: pointer;
  transition:
    border-color var(--dur-fast) var(--ease),
    box-shadow var(--dur-fast) var(--ease);
}

.task-snapshot--clickable:hover {
  border-color: var(--c-accent);
  box-shadow: var(--shadow-sm);
}

.snapshot-icon-wrap {
  padding: 6px;
  border-radius: 8px;
  flex-shrink: 0;
  display: flex;
}

.snapshot-badge {
  font-size: 10px;
  font-weight: 600;
  color: var(--c-accent);
  background: var(--c-accent-light);
  padding: 2px 6px;
  border-radius: 4px;
  border: 1px solid var(--c-accent-soft);
  flex-shrink: 0;
}

.snapshot-title {
  font-size: var(--text-sm);
  font-weight: 700;
  color: var(--c-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  min-width: 0;
}

.snapshot-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  flex-shrink: 0;
  padding-left: 12px;
  border-left: 1px solid var(--c-border-light);
}

.snapshot-price {
  font-size: var(--text-base);
  font-weight: 800;
  color: var(--c-text);
  line-height: 1;
  margin-bottom: 4px;
}

.snapshot-status {
  font-size: 10px;
  font-weight: 600;
  line-height: 1;
}

.status-open {
  color: var(--c-accent);
}
.status-active {
  color: var(--c-warning);
}
.status-done {
  color: var(--c-success);
}
.status-canceled {
  color: var(--c-text-muted);
}

.marketplace-badge {
  background: #eff6ff80;
  border: 1px solid #bfdbfe;
  border-radius: 12px;
  margin-bottom: 4px;
  padding: 8px 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: var(--c-accent);
}

.marketplace-badge span {
  font-size: var(--text-sm);
  font-weight: 500;
}

.marketplace-badge--clickable {
  cursor: pointer;
  transition:
    border-color var(--dur-fast) var(--ease),
    box-shadow var(--dur-fast) var(--ease),
    background var(--dur-fast) var(--ease);
}

.marketplace-badge--clickable:hover {
  border-color: #93c5fd;
  box-shadow: var(--shadow-sm);
  background: #eff6ffcc;
}

.collapse-chevron {
  transition: transform 0.28s cubic-bezier(0.4, 0, 0.2, 1);
}

.collapse-chevron.rotated {
  transform: rotate(180deg);
}

/* ── Messages ────────────────────────────────────────────────────────── */
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

.messages-loading {
  display: flex;
  justify-content: center;
  padding: 48px;
}

.messages-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--c-text-muted);
  gap: 16px;
}

.message-row {
  margin-bottom: 24px;
  animation: msg-in 0.3s var(--ease);
}

@keyframes msg-in {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 对方消息 */
.msg-other-wrap {
  display: flex;
  flex-direction: column;
}

.msg-meta-other {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.msg-avatar-wrap :deep(img) {
  border: 1px solid var(--c-border);
}

.msg-sender {
  font-size: var(--text-xs);
  font-weight: 600;
  color: var(--c-text-secondary);
}

.msg-time {
  font-size: 10px;
  color: var(--c-text-muted);
}

.msg-content-other {
  width: 100%;
  color: var(--c-text);
  line-height: 1.6;
}

/* 己方消息 */
.msg-own {
  display: flex;
  justify-content: flex-end;
}

.msg-own-wrap {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  max-width: 80%;
}

.msg-meta-own {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
}

.status-read {
  color: var(--c-accent);
}

.status-sent {
  color: var(--c-text-muted);
}

.msg-sender-me {
  font-size: var(--text-xs);
  font-weight: 600;
  color: var(--c-text-secondary);
  margin-left: 2px;
}

.msg-bubble-own {
  background: var(--c-accent);
  color: white;
  border-radius: 16px 4px 16px 16px;
  padding: 10px 16px;
  box-shadow: var(--shadow-sm);
  line-height: 1.6;
  border: 1px solid #2563eb80;
}

/* ── Rich Text Overrides ─────────────────────────────────────────────── */
.chat-page :deep(.rich-text) p {
  margin-top: 0.25em;
  margin-bottom: 0.25em;
}

.chat-page :deep(.rich-text) p:first-child {
  margin-top: 0;
}
.chat-page :deep(.rich-text) p:last-child {
  margin-bottom: 0;
}

.chat-page :deep(.rich-text) ul,
.chat-page :deep(.rich-text) ol {
  padding-left: 1.5em;
  margin: 0.25em 0;
}

.chat-page :deep(.rich-text) ul {
  list-style-type: disc;
}
.chat-page :deep(.rich-text) ol {
  list-style-type: decimal;
}

.chat-page :deep(.rich-text) ul ul {
  list-style-type: circle;
}
.chat-page :deep(.rich-text) ul ul ul {
  list-style-type: square;
}

.chat-page :deep(.rich-text) li {
  margin: 0.1em 0;
}

.chat-page :deep(.rich-text) li > ul,
.chat-page :deep(.rich-text) li > ol {
  margin: 0;
}

.chat-page :deep(.rich-text) blockquote {
  border-left: 3px solid var(--c-accent);
  margin: 0.4em 0;
  padding: 0.3em 0.8em;
  background: rgba(0, 0, 0, 0.03);
  border-radius: 0 6px 6px 0;
  color: var(--c-text-secondary);
}

.chat-page :deep(.rich-text) blockquote p {
  margin: 0.15em 0;
}

.chat-page :deep(.rich-text) pre,
.chat-page :deep(.rich-text) pre.hljs-pre {
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

.chat-page :deep(.rich-text) pre code,
.chat-page :deep(.rich-text) pre.hljs-pre code {
  font-family: "Cascadia Code", "Fira Code", "Consolas", monospace;
  background: transparent;
  padding: 0;
  border-radius: 0;
  font-size: inherit;
  color: inherit;
}

.chat-page :deep(.rich-text) code {
  font-family: "Cascadia Code", "Fira Code", "Consolas", monospace;
  background: rgba(0, 0, 0, 0.06);
  padding: 1px 5px;
  border-radius: 4px;
  font-size: 0.85em;
}

.chat-page :deep(.code-lang) {
  position: absolute;
  top: 8px;
  left: 12px;
  font-size: 11px;
  font-weight: 600;
  color: #9ca3af;
  font-family: "Cascadia Code", "Fira Code", "Consolas", monospace;
  user-select: none;
  letter-spacing: 0.03em;
}

.chat-page :deep(.bubble-own .code-lang) {
  color: rgba(255, 255, 255, 0.45);
}

.chat-page :deep(.code-copy-btn) {
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
  transition:
    background 0.15s,
    color 0.15s;
  line-height: 0;
}

.chat-page :deep(.code-copy-btn:hover) {
  background: #e5e7eb;
  color: #111827;
}

.chat-page :deep(.code-copy-btn .icon-check) {
  display: none;
}
.chat-page :deep(.code-copy-btn.copied .icon-copy) {
  display: none;
}
.chat-page :deep(.code-copy-btn.copied .icon-check) {
  display: flex;
  color: #16a34a;
}

.chat-page :deep(.rich-text) table {
  width: 100%;
  border-collapse: collapse;
  margin: 0.4em 0;
  font-size: 0.9em;
}

.chat-page :deep(.rich-text) th,
.chat-page :deep(.rich-text) td {
  padding: 6px 10px;
  text-align: left;
}

.chat-page :deep(.rich-text) th {
  font-weight: 600;
  border-bottom: 2px solid var(--c-text-muted);
}

.chat-page :deep(.rich-text) td {
  border-bottom: 1px solid var(--c-border);
}

.chat-page :deep(.rich-text) tr:last-child td {
  border-bottom: none;
}

.chat-page :deep(.rich-text) hr {
  border: none;
  border-top: 1px solid var(--c-border);
  margin: 0.5em 0;
}

.chat-page :deep(.rich-text) img {
  width: 25vw;
  min-width: 150px;
  max-width: 100%;
  height: auto;
  border-radius: 8px;
  display: block;
  margin: 0 auto;
  box-shadow: var(--shadow-xs);
}

.chat-page :deep(.bubble-other .rich-text > *:not(p:has(img))) {
  margin-left: 2rem;
  max-width: calc(85% - 2rem);
}

.chat-page :deep(.bubble-other .rich-text p:has(img)) {
  display: flex;
  justify-content: center;
  width: 100%;
  margin: 1rem 0;
}

.chat-page :deep(.bubble-own .rich-text) {
  color: white !important;
}
.chat-page :deep(.bubble-own .rich-text) a {
  color: #bfdbfe;
  text-decoration: underline;
}
.chat-page :deep(.bubble-own .rich-text) pre {
  background: rgba(0, 0, 0, 0.25);
  color: #e2e8f0;
  border-color: rgba(255, 255, 255, 0.15);
}
.chat-page :deep(.bubble-own .rich-text) pre code {
  background: transparent;
  color: inherit;
}
.chat-page :deep(.bubble-own .rich-text) code {
  background: rgba(255, 255, 255, 0.2);
  color: white;
}
.chat-page :deep(.bubble-own .code-copy-btn) {
  color: rgba(255, 255, 255, 0.6);
}
.chat-page :deep(.bubble-own .code-copy-btn:hover) {
  background: rgba(255, 255, 255, 0.15);
  color: white;
}
.chat-page :deep(.bubble-own .rich-text) blockquote {
  border-left-color: rgba(255, 255, 255, 0.5);
  background: rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.85);
}
.chat-page :deep(.bubble-own .rich-text) th {
  border-bottom-color: rgba(255, 255, 255, 0.4);
}
.chat-page :deep(.bubble-own .rich-text) td {
  border-bottom-color: rgba(255, 255, 255, 0.15);
}
.chat-page :deep(.bubble-own .katex) {
  color: white;
}
.chat-page :deep(.bubble-own .rich-text p:has(img)) {
  display: flex;
  justify-content: center;
  margin: 0.5rem 0;
}
.chat-page :deep(.bubble-other .rich-text) {
  color: var(--c-text);
  width: 100%;
}
.chat-page :deep(.bubble-other .rich-text) a {
  color: var(--c-accent);
  text-decoration: underline;
}
.chat-page :deep(.latex-error) {
  color: var(--c-danger);
  font-size: var(--text-xs);
  background: var(--c-danger-light);
  padding: 1px 4px;
  border-radius: 4px;
}

/* ── Attachments Preview ─────────────────────────────────────────────── */
.msg-attachments {
  display: flex;
  gap: 8px;
  margin-top: 6px;
  padding-left: 2rem;
  flex-wrap: wrap;
}

.own-attachments {
  padding-left: 0;
  justify-content: flex-end;
}

.att-preview-item {
  width: 72px;
  height: 72px;
  flex-shrink: 0;
}

.att-preview-link {
  display: block;
  width: 100%;
  height: 100%;
  border-radius: 10px;
  overflow: hidden;
  border: 1.5px solid var(--c-text-muted);
  transition:
    box-shadow var(--dur-fast) var(--ease),
    transform var(--dur-fast) var(--ease);
}

.att-preview-link:hover {
  box-shadow: var(--shadow-md);
  transform: scale(1.04);
}

.att-thumb {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.att-icon-thumb {
  width: 100%;
  height: 100%;
  background: var(--c-bg);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  color: var(--c-text-muted);
}

.att-ext {
  font-size: 9px;
  font-weight: 700;
  color: var(--c-text-muted);
  line-height: 1;
  max-width: 56px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.att-deleted-link {
  cursor: pointer;
  opacity: 0.5;
}

.att-deleted-style {
  position: relative;
}

.att-deleted-link:hover {
  opacity: 0.75;
}

/* ── Input Area ──────────────────────────────────────────────────────── */
.chat-input-area {
  background: transparent;
  padding: 0 12px 6px;
  flex-shrink: 0;
  z-index: 10;
}

.blocked-notice {
  background: var(--c-danger-light);
  border: 1px solid var(--c-danger-soft);
  border-radius: var(--radius-full);
  padding: 8px 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: var(--c-danger);
  margin: 4px 0;
}

.blocked-notice span {
  font-size: var(--text-sm);
  font-weight: 500;
}

.input-wrap {
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-width: 800px;
  margin: 0 auto;
}

.capsule-input {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  background: var(--c-bg);
  border: 1.5px solid var(--c-border);
  border-radius: 24px;
  padding: 4px;
  transition: all var(--dur-fast) var(--ease);
  box-shadow: var(--shadow-xs);
}

.capsule-input:focus-within {
  background: var(--c-surface);
  border-color: var(--c-accent);
}

.file-upload-btn {
  width: 38px;
  height: 38px;
  flex-shrink: 0;
  border-radius: 50%;
  background: transparent;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--c-text-secondary);
  cursor: pointer;
  transition:
    background var(--dur-fast) var(--ease),
    color var(--dur-fast) var(--ease);
}

.file-upload-btn:hover {
  background: var(--c-border);
  color: var(--c-text-secondary);
}
.file-upload-btn.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.file-input-hidden {
  display: none;
}

.msg-textarea {
  flex: 1;
  background: transparent;
  border: none;
  outline: none;
  resize: none;
  padding: 9px 8px;
  font-size: 15px;
  color: var(--c-text);
  line-height: 20px;
  height: 38px;
  overflow-y: hidden;
  font-family: inherit;
}

.msg-textarea::placeholder {
  color: var(--c-text-muted);
}

.send-btn {
  width: 38px;
  height: 38px;
  flex-shrink: 0;
  border-radius: 50%;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--dur-fast) var(--ease);
  background: var(--c-border);
  color: var(--c-text-muted);
  cursor: not-allowed;
}

.send-btn.active {
  background: var(--c-accent);
  color: white;
  cursor: pointer;
  box-shadow: var(--shadow-sm);
}

.send-btn.active:hover {
  background: var(--c-accent-hover);
  transform: scale(1.05);
}

.send-btn.active:active {
  transform: scale(0.95);
}

.input-hint {
  font-size: 10px;
  color: var(--c-text-muted);
  text-align: center;
  padding-top: 2px;
}

/* ── Icon Button ─────────────────────────────────────────────────────── */
.icon-btn {
  padding: 8px;
  border-radius: 50%;
  background: transparent;
  border: none;
  color: var(--c-text-muted);
  cursor: pointer;
  transition: all var(--dur-fast) var(--ease);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}

.icon-btn:hover {
  background: var(--c-bg);
  color: var(--c-text);
}

.icon-btn.danger:hover {
  background: var(--c-danger-light);
  color: var(--c-danger);
}

/* ── Modal ───────────────────────────────────────────────────────────── */
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
  background: var(--c-surface);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xl);
  width: min(480px, 92vw);
  max-height: 80vh;
  display: flex;
  flex-direction: column;
}

/* ── Modal Transition ──────────────────────────────────────────────────── */
.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.22s var(--ease);
}

.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}

.modal-fade-enter-active .modal-panel,
.modal-fade-leave-active .modal-panel {
  transition:
    transform 0.22s var(--ease),
    opacity 0.22s var(--ease);
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
  border-bottom: 1px solid var(--c-border);
  display: flex;
  align-items: center;
  gap: 12px;
}

.modal-header h3 {
  font-size: var(--text-lg);
  font-weight: 700;
  flex: 1;
}

.modal-count {
  font-size: var(--text-sm);
  color: var(--c-text-muted);
  font-weight: 500;
}

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
  color: var(--c-text-muted);
  gap: 8px;
}

.att-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.att-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--c-border);
  transition: border-color var(--dur-fast) var(--ease);
}

.att-item:hover {
  border-color: var(--c-accent);
}

.att-item-preview {
  width: 48px;
  height: 48px;
  flex-shrink: 0;
  border-radius: 8px;
  overflow: hidden;
}

.att-list-thumb {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.att-list-icon {
  width: 100%;
  height: 100%;
  background: var(--c-bg);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--c-text-muted);
}

.att-item-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.att-item-name {
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--c-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.att-item-size {
  font-size: var(--text-xs);
  color: var(--c-text-muted);
}

.att-item-actions {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}

/* ── Responsive ──────────────────────────────────────────────────────── */
@media (max-width: 768px) {
  .chat-sidebar {
    width: 100%;
  }

  .sidebar-hidden {
    display: none;
  }

  .main-hidden {
    display: none;
  }

  .chat-main {
    width: 100%;
  }

  .header-top {
    padding: 12px 16px;
  }

  .banner-area {
    padding: 0 16px;
  }

  .chat-messages {
    padding: 16px;
  }

  .msg-own-wrap {
    max-width: 90%;
  }

  .msg-textarea {
    font-size: 16px !important;
  }
}

/* ── Task preview modal ──────────────────────────────────────────────── */
.task-preview-panel {
  width: min(440px, 92vw);
}

.task-preview-icon {
  padding: 6px;
  border-radius: 8px;
  flex-shrink: 0;
  display: flex;
}

.task-preview-loading {
  display: flex;
  justify-content: center;
  padding: 32px;
}

.task-preview-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.task-preview-meta {
  display: flex;
  align-items: center;
  gap: 10px;
}

.task-preview-price {
  font-size: var(--text-xl, 1.25rem);
  font-weight: 700;
  color: var(--c-accent);
}

.task-preview-status {
  font-size: var(--text-sm);
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 99px;
  background: var(--c-bg);
}

.task-preview-desc {
  font-size: var(--text-sm);
  color: var(--c-text-secondary);
  line-height: 1.6;
  white-space: pre-wrap;
}

.task-preview-fields {
  display: flex;
  flex-direction: column;
  gap: 6px;
  border-top: 1px solid var(--c-border);
  padding-top: 10px;
}

.task-preview-field {
  display: flex;
  gap: 8px;
  font-size: var(--text-sm);
}

.field-label {
  color: var(--c-text-muted);
  flex-shrink: 0;
  width: 56px;
}

.field-value {
  color: var(--c-text);
  font-weight: 500;
}

.field-expired {
  color: var(--c-danger);
}

/* ── User Detail Modal ───────────────────────────────────────────────── */
.user-detail-panel {
  width: min(440px, 92vw);
}

.header-icon-accent {
  color: var(--c-accent);
  flex-shrink: 0;
}

.user-detail-body {
  display: flex;
  flex-direction: column;
  padding: 0;
  gap: 0;
}

.user-detail-section {
  padding: 16px 20px;
  border-bottom: 1px solid var(--c-border-light);
}

.user-detail-top-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.user-detail-card {
  display: flex;
  align-items: flex-start;
  gap: 14px;
}

.user-detail-avatar :deep(img) {
  border: 2px solid var(--c-border);
  box-shadow: var(--shadow-sm);
}

.user-detail-info {
  display: flex;
  flex-direction: column;
  gap: 5px;
  flex: 1;
  min-width: 0;
}

.user-detail-name {
  font-size: var(--text-lg);
  font-weight: 700;
  color: var(--c-text);
  margin: 0;
}

.user-detail-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.user-tag {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 99px;
  background: var(--c-bg);
  color: var(--c-text-secondary);
  border: 1px solid var(--c-border);
}

.gender-tag {
  background: #ede9fe;
  color: #7c3aed;
  border-color: #ddd6fe;
}

.online-active {
  background: #dcfce7;
  color: #16a34a;
  border-color: #bbf7d0;
}

.user-worker-rating {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 2px;
}

.rating-text {
  font-size: var(--text-xs);
  color: var(--c-text-muted);
}

.hv-detail-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.hv-detail-item {
  display: flex;
  flex-direction: column;
  gap: 3px;
  font-size: var(--text-sm);
}

.hv-detail-label {
  color: var(--c-text-muted);
  font-size: var(--text-xs);
}

.worker-bio {
  font-size: var(--text-sm);
  color: var(--c-text-secondary);
  line-height: 1.65;
  white-space: pre-wrap;
  margin: 0;
}

.worker-skills {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.skill-chip {
  display: inline-block;
  font-size: var(--text-sm);
  font-weight: 500;
  padding: 4px 12px;
  border-radius: var(--radius-full);
  background: var(--c-accent-light);
  color: var(--c-accent);
}

.user-detail-no-worker {
  color: var(--c-text-muted);
  font-size: var(--text-sm);
  margin: 0;
}

.user-detail-section-title {
  margin: 0 0 10px;
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--c-text-secondary);
  display: flex;
  align-items: center;
  gap: 6px;
}

.user-reviews {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.user-review-item {
  padding: 10px 12px;
  background: var(--c-bg);
  border-radius: var(--radius-md);
}

.user-review-header {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 4px;
}

.user-review-meta {
  color: var(--c-text-muted);
  font-size: var(--text-xs);
}

.user-review-comment {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--c-text-secondary);
  line-height: 1.5;
}

.user-detail-hint {
  color: var(--c-text-muted);
  font-size: var(--text-sm);
  margin: 0;
}
</style>
