<script lang="ts">
import { reactive } from "vue";
import type { AnonCaptchaScene, CaptchaScene } from "../utils/captcha";

interface SlideCaptchaState {
  visible: boolean;
  scene: CaptchaScene | AnonCaptchaScene | null;
  /** 非空时走匿名端点（注册/登录场景） */
  sessionId: string | null;
  resolve: ((token: string | null) => void) | null;
}

export const slideCaptchaState = reactive<SlideCaptchaState>({
  visible: false,
  scene: null,
  sessionId: null,
  resolve: null,
});

export function appSlideCaptcha(scene: CaptchaScene): Promise<string | null> {
  return new Promise((resolve) => {
    if (slideCaptchaState.visible && slideCaptchaState.resolve) {
      slideCaptchaState.resolve(null);
    }
    slideCaptchaState.scene = scene;
    slideCaptchaState.sessionId = null;
    slideCaptchaState.resolve = resolve;
    slideCaptchaState.visible = true;
  });
}

export function appAnonSlideCaptcha(
  scene: AnonCaptchaScene,
  sessionId: string,
): Promise<string | null> {
  return new Promise((resolve) => {
    if (slideCaptchaState.visible && slideCaptchaState.resolve) {
      slideCaptchaState.resolve(null);
    }
    slideCaptchaState.scene = scene;
    slideCaptchaState.sessionId = sessionId;
    slideCaptchaState.resolve = resolve;
    slideCaptchaState.visible = true;
  });
}
</script>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { Slide } from "go-captcha-vue";
import {
  createAnonCaptchaChallenge,
  createCaptchaChallenge,
  verifyAnonCaptchaChallenge,
  verifyCaptchaChallenge,
} from "../api/captcha";

type AnyScene = CaptchaScene | AnonCaptchaScene;

const sceneTitleMap: Record<AnyScene, string> = {
  view_worker_contact: "查看联系方式验证",
  chat_send: "聊天安全验证",
  task_publish: "发布任务验证",
  task_accept: "接取任务验证",
  register: "注册安全验证",
  login: "登录安全验证",
};

const sceneHintMap: Record<AnyScene, string> = {
  view_worker_contact: "为保护隐私，查看联系方式前需要完成验证",
  chat_send: "发送过于频繁，请先验证后继续聊天",
  task_publish: "今日发布任务较多，请完成验证后继续发布",
  task_accept: "今日接取任务较多，请完成验证后继续接取",
  register: "为保障账号安全，注册前请完成验证",
  login: "密码错误次数过多，请先完成验证",
};

const loading = ref(false);
const verifying = ref(false);
const challengeId = ref("");
const errorText = ref("");
const requestVersion = ref(0);
const isShaking = ref(false);

const slideConfig = reactive({
  width: 320,
  height: 200,
  title: "",
  showTheme: false,
  horizontalPadding: 0,
  verticalPadding: 0,
  // scope: false → mousemove 绑定在 document.body，拖出弹窗区域不会中断
  // scope: true  → mousemove 绑定在组件根元素，移出即断（默认值，有 bug）
  scope: false,
});

// overlay padding 16*2 + dialog padding 16*2 + safety = 68px
function computeSlideWidth(): number {
  return Math.min(window.innerWidth - 68, 320);
}

function onResize() {
  if (slideCaptchaState.visible) {
    slideConfig.width = computeSlideWidth();
  }
}

onMounted(() => window.addEventListener("resize", onResize));
onUnmounted(() => window.removeEventListener("resize", onResize));

const slideData = reactive({
  thumbX: 0,
  thumbY: 0,
  thumbWidth: 0,
  thumbHeight: 0,
  image: "",
  thumb: "",
});

const originalWidth = ref(320);
const trajectory: { x: number; t: number }[] = [];
let trajStartTime = 0;

const sceneTitle = computed(() => {
  if (!slideCaptchaState.scene) return "滑块验证";
  return sceneTitleMap[slideCaptchaState.scene];
});

const sceneHint = computed(() => {
  if (!slideCaptchaState.scene) return "";
  return sceneHintMap[slideCaptchaState.scene];
});

function closeWith(token: string | null) {
  // 触发 document.body 上库的 mouseup 监听器（ce/U → X()），清除 scope:false 模式下的全局拖拽事件
  document.body.dispatchEvent(new MouseEvent("mouseup", { bubbles: false }));
  slideCaptchaState.resolve?.(token);
  slideCaptchaState.resolve = null;
  slideCaptchaState.scene = null;
  slideCaptchaState.visible = false;
  challengeId.value = "";
  errorText.value = "";
  slideData.image = "";
  slideData.thumb = "";
}

function handleCancel() {
  if (verifying.value) return;
  closeWith(null);
}

function handleOverlay(event: MouseEvent) {
  if (event.target === event.currentTarget) {
    handleCancel();
  }
}

async function loadChallenge() {
  if (!slideCaptchaState.visible || !slideCaptchaState.scene) return;
  const version = ++requestVersion.value;
  // 同步清空轨迹，避免 await 期间残留 move 事件污染数据
  trajectory.length = 0;
  trajStartTime = 0;
  loading.value = true;
  errorText.value = "";
  try {
    const scene = slideCaptchaState.scene;
    const sessionId = slideCaptchaState.sessionId;
    const challenge = sessionId
      ? await createAnonCaptchaChallenge(sessionId, scene as AnonCaptchaScene)
      : await createCaptchaChallenge(scene as CaptchaScene);
    if (version !== requestVersion.value) return;
    challengeId.value = challenge.challenge_id;
    originalWidth.value = challenge.width;
    trajectory.length = 0;
    trajStartTime = 0;
    const displayWidth = computeSlideWidth();
    const ratio = displayWidth / challenge.width;
    slideConfig.width = displayWidth;
    slideConfig.height = Math.round(challenge.height * ratio);
    slideData.thumbX = 0;
    slideData.thumbY = Math.round(challenge.thumb_y * ratio);
    slideData.thumbWidth = Math.round(challenge.thumb_width * ratio);
    slideData.thumbHeight = Math.round(challenge.thumb_height * ratio);
    slideData.image = challenge.image;
    slideData.thumb = challenge.thumb;
  } catch (error: any) {
    if (version !== requestVersion.value) return;
    errorText.value =
      error?.response?.data?.detail || "验证码加载失败，请刷新重试";
  } finally {
    if (version === requestVersion.value) {
      loading.value = false;
    }
  }
}

function handleRefresh() {
  if (verifying.value) return;
  trajectory.length = 0;
  trajStartTime = 0;
  void loadChallenge();
}

const slideEvents = {
  refresh() {
    handleRefresh();
  },
  close() {
    handleCancel();
  },
  move(x: number, _y: number) {
    // 弹窗已关闭时忽略，防止 document.body 上的残留监听器写入脏数据
    if (!slideCaptchaState.visible) return;
    const now = Date.now();
    if (!trajStartTime) trajStartTime = now;
    trajectory.push({ x, t: now - trajStartTime });
  },
  async confirm(point: { x: number; y: number }, reset: () => void) {
    if (verifying.value || !challengeId.value) return;
    verifying.value = true;
    errorText.value = "";
    try {
      const scale = originalWidth.value / slideConfig.width;
      const scaledX = Math.round(point.x * scale);
      const scaledY = Math.round(point.y * scale);
      const scaledTrajectory = trajectory.map((p) => ({
        x: Math.round(p.x * scale),
        t: p.t,
      }));
      const sessionId = slideCaptchaState.sessionId;
      const result = sessionId
        ? await verifyAnonCaptchaChallenge(
            sessionId,
            challengeId.value,
            scaledX,
            scaledY,
            scaledTrajectory,
          )
        : await verifyCaptchaChallenge(
            challengeId.value,
            scaledX,
            scaledY,
            scaledTrajectory,
          );
      closeWith(result.captcha_token);
    } catch (error: any) {
      errorText.value = error?.response?.data?.detail || "验证失败，请重试";
      isShaking.value = true;
      setTimeout(() => {
        isShaking.value = false;
      }, 550);
      reset();
      await loadChallenge();
    } finally {
      verifying.value = false;
    }
  },
};

watch(
  () => slideCaptchaState.visible,
  (visible) => {
    if (visible) {
      slideConfig.width = computeSlideWidth();
      void loadChallenge();
    }
  },
);
</script>

<template>
  <Teleport to="body">
    <Transition name="captcha-fade">
      <div
        v-if="slideCaptchaState.visible"
        class="asc-overlay"
        @mousedown="handleOverlay"
      >
        <div class="asc-dialog">
          <div class="asc-header">
            <div>
              <h3>{{ sceneTitle }}</h3>
              <p>{{ sceneHint }}</p>
            </div>
            <div class="asc-header-actions">
              <button
                class="asc-icon-btn"
                aria-label="刷新"
                @click="handleRefresh"
              >
                <i class="fa-solid fa-rotate-right"></i>
              </button>
              <button
                class="asc-icon-btn"
                aria-label="关闭"
                @click="handleCancel"
              >
                <i class="fa-solid fa-xmark"></i>
              </button>
            </div>
          </div>

          <div class="asc-body" :class="{ 'asc-shake': isShaking }">
            <Slide
              :data="slideData"
              :events="slideEvents"
              :config="slideConfig"
            />
            <Transition name="captcha-fade">
              <div v-if="loading || verifying" class="asc-loading-overlay">
                <div class="asc-spinner" />
                <span>{{ verifying ? "正在验证…" : "加载中…" }}</span>
              </div>
            </Transition>
            <Transition name="captcha-fade">
              <div v-if="errorText" class="asc-error-toast">
                <i class="fa-solid fa-circle-exclamation"></i> {{ errorText }}
              </div>
            </Transition>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.asc-overlay {
  position: fixed;
  inset: 0;
  z-index: 10000;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(15, 23, 42, 0.42);
  backdrop-filter: blur(2px);
  padding: 16px;
}

.asc-dialog {
  width: min(100%, 420px);
  border-radius: 16px;
  background: #fff;
  box-shadow: 0 18px 52px rgba(15, 23, 42, 0.28);
  padding: 16px;
}

.asc-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 12px;
}

.asc-header h3 {
  margin: 0;
  font-size: 16px;
  color: var(--c-text);
}

.asc-header p {
  margin: 4px 0 0;
  font-size: 13px;
  color: var(--c-text-secondary);
}

.asc-header-actions {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}

.asc-icon-btn {
  width: 32px;
  height: 32px;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 50%;
  background: transparent;
  font-size: 14px;
  color: var(--c-text-secondary, #888);
  cursor: pointer;
  transition:
    background 0.15s,
    color 0.15s;
}

.asc-icon-btn:hover {
  background: var(--c-surface-hover, #f1f5f9);
  color: var(--c-text, #1e293b);
}

.asc-body {
  display: flex;
  flex-direction: column;
  align-items: center;
  position: relative;
}

/* --- 覆盖层 loading spinner --- */
.asc-loading-overlay {
  position: absolute;
  inset: 0;
  z-index: 20;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(2px);
  border-radius: 8px;
  pointer-events: none;
}

.asc-loading-overlay span {
  font-size: 13px;
  color: var(--c-text-secondary, #666);
}

.asc-spinner {
  width: 30px;
  height: 30px;
  border: 3px solid rgba(62, 124, 255, 0.2);
  border-top-color: #3e7cff;
  border-radius: 50%;
  animation: asc-spin 0.7s linear infinite;
}

@keyframes asc-spin {
  to {
    transform: rotate(360deg);
  }
}

/* --- 出错 toast --- */
.asc-error-toast {
  position: absolute;
  bottom: 60px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 25;
  background: rgba(239, 68, 68, 0.92);
  color: #fff;
  font-size: 13px;
  padding: 6px 14px;
  border-radius: 6px;
  white-space: nowrap;
  pointer-events: none;
  box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3);
}

.captcha-fade-enter-active,
.captcha-fade-leave-active {
  transition: opacity 0.2s ease;
}

.captcha-fade-enter-from,
.captcha-fade-leave-to {
  opacity: 0;
}

@media (max-width: 480px) {
  .asc-dialog {
    width: 100%;
    padding: 14px;
  }
}

/* 出错摇晃动画 */
@keyframes asc-shake {
  0%,
  100% {
    transform: translateX(0);
  }
  15% {
    transform: translateX(-7px);
  }
  30% {
    transform: translateX(7px);
  }
  45% {
    transform: translateX(-5px);
  }
  60% {
    transform: translateX(5px);
  }
  75% {
    transform: translateX(-3px);
  }
  90% {
    transform: translateX(2px);
  }
}

.asc-shake {
  animation: asc-shake 0.5s ease-out;
}

/* --- 去掉 go-captcha 内部 header、loading、边框 --- */
:deep(.gc-header) {
  display: none !important;
}

:deep(.gc-loading) {
  display: none !important;
}

:deep(.gc-wrapper) {
  border: none !important;
  box-shadow: none !important;
  background: transparent !important;
}

:deep(.gc-body) {
  border-radius: 8px !important;
  overflow: hidden;
  margin-top: 0 !important;
}

/* --- 滑块改为圆形 --- */
:deep(.gc-drag-block) {
  width: 40px !important;
  height: 40px !important;
  border-radius: 50% !important;
  margin-top: -20px !important;
}

:deep(.gc-drag-line) {
  height: 4px !important;
  margin-top: -2px !important;
  border-radius: 2px !important;
}
</style>
