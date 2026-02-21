<script setup lang="ts">
import { nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import AppToast from '../components/AppToast.vue'
import { useAppToast } from '../composables/useAppToast'
import { fetchRegistrationStatus, register } from '../api/auth'
import { createAppeal, fetchBanContext } from '../api/moderation'
import type { BanRecord } from '../types/api'
import { useAuthStore } from '../stores/auth'
import { extractError } from '../utils/error'
import { formatBanUntil, formatShort } from '../utils/time'

const router = useRouter()
const auth = useAuthStore()

const appTitle = import.meta.env.VITE_APP_TITLE || '校园任务平台'

const isLogin = ref(true)
const showPassword = ref(false)

const account = ref('')
const password = ref('')
const regName = ref('')
const regAccount = ref('')
const regPassword = ref('')
const confirmPassword = ref('')
const showRegPassword = ref(false)

const { toast, showToast, clearToast } = useAppToast(3000)
const loading = ref(false)

const registrationEnabled = ref(false)
const registrationLoaded = ref(false)

/* ---- Appeal ---- */
const showAppeal = ref(false)
const banUntil = ref<string | null>(null)
const banCount = ref(0)
const banRecords = ref<BanRecord[]>([])
const banContextLoading = ref(false)
const appealReason = ref('')
const appealEvidence = ref('')
const appealLoading = ref(false)
const appealMsg = ref<{ text: string; type: 'success' | 'error' } | null>(null)

function toggleForm() {
  isLogin.value = !isLogin.value
  showPassword.value = false
  showRegPassword.value = false
  clearToast()
}

async function submitLogin() {
  clearToast()
  loading.value = true
  try {
    const res = await auth.login(account.value, password.value)
    if (res.role === 'admin') {
      await router.push('/admin')
      return
    }
    await router.push(res.profile_completed ? '/' : '/complete-profile')
  } catch (error: any) {
    const detail = error?.response?.data?.detail
    if (detail && typeof detail === 'object' && detail.code === 'USER_BANNED') {
      banUntil.value = detail.ban_until || null
      showAppeal.value = true
      loadBanContext()
    } else {
      showToast(extractError(error, '登录失败，请稍后重试'), 'error')
    }
  } finally {
    loading.value = false
  }
}

async function submitRegister() {
  clearToast()

  if (!registrationEnabled.value) return

  if (regPassword.value.length < 6) {
    showToast('密码至少 6 位', 'error')
    return
  }
  if (regPassword.value !== confirmPassword.value) {
    showToast('两次输入的密码不一致', 'error')
    return
  }

  loading.value = true
  try {
    const registerAccount = regAccount.value
    const registerPassword = regPassword.value
    await register({ account: registerAccount, password: registerPassword, name: regName.value })
    const res = await auth.login(registerAccount, registerPassword)
    if (res.role === 'admin') {
      await router.push('/admin')
      return
    }
    await router.push(res.profile_completed ? '/' : '/complete-profile')
  } catch (error: any) {
    showToast(extractError(error, '注册失败，请稍后重试'), 'error')
    loadRegistrationStatus()
  } finally {
    loading.value = false
  }
}

async function loadBanContext() {
  banContextLoading.value = true
  try {
    const ctx = await fetchBanContext({
      account: account.value,
      password: password.value,
    })
    banUntil.value = ctx.ban_until
    banCount.value = ctx.ban_count
    banRecords.value = ctx.records
  } catch {
    /* supplementary */
  } finally {
    banContextLoading.value = false
  }
}

async function submitAppeal() {
  if (!appealReason.value.trim() || !appealEvidence.value.trim()) {
    appealMsg.value = { text: '请填写申诉理由和证据', type: 'error' }
    return
  }
  appealLoading.value = true
  appealMsg.value = null
  try {
    await createAppeal({
      account: account.value,
      password: password.value,
      reason: appealReason.value,
      evidence: appealEvidence.value,
    })
    appealMsg.value = { text: '申诉已提交，请等待管理员审核', type: 'success' }
    appealReason.value = ''
    appealEvidence.value = ''
  } catch (error: any) {
    appealMsg.value = { text: extractError(error, '提交失败'), type: 'error' }
  } finally {
    appealLoading.value = false
  }
}

async function loadRegistrationStatus() {
  try {
    const status = await fetchRegistrationStatus()
    registrationEnabled.value = status.registration_enabled
  } catch {
    registrationEnabled.value = false
  } finally {
    registrationLoaded.value = true
  }
}

onMounted(loadRegistrationStatus)

/* ---- Polygon spinner (canvas) ---- */
const spinnerCanvas = ref<HTMLCanvasElement | null>(null)
let spinnerAnimId = 0

function startSpinner() {
  const canvas = spinnerCanvas.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  if (!ctx) return

  const size = 56
  const dpr = window.devicePixelRatio || 1
  canvas.width = size * dpr
  canvas.height = size * dpr
  ctx.scale(dpr, dpr)

  let rotation = 0
  let points = 3
  let direction = 1

  const outerRadius = 23
  const innerRadiusRatio = 0.75

  function drawStar(cx: number, cy: number, numPoints: number, radius: number, innerRatio: number, rot: number) {
    const innerRadius = radius * innerRatio
    const step = Math.PI / numPoints
    ctx!.beginPath()
    for (let i = 0; i < 2 * Math.ceil(numPoints); i++) {
      const r = (i % 2 === 0) ? radius : innerRadius
      const theta = i * step + rot
      const x = cx + r * Math.cos(theta)
      const y = cy + r * Math.sin(theta)
      if (i === 0) ctx!.moveTo(x, y)
      else ctx!.lineTo(x, y)
    }
    ctx!.closePath()
  }

  function animate() {
    ctx!.clearRect(0, 0, size, size)

    ctx!.fillStyle = '#1c1c1c'
    ctx!.strokeStyle = '#1c1c1c'
    ctx!.lineWidth = 4
    ctx!.lineJoin = 'round'

    const shapeProgress = (points - 3) / 6
    const currentSpeed = 0.01 + 0.11 * Math.pow(shapeProgress, 2)
    rotation += currentSpeed

    drawStar(size / 2, size / 2, points, outerRadius, innerRadiusRatio, rotation - Math.PI / 2)
    ctx!.fill()
    ctx!.stroke()

    points += 0.02 * direction
    if (points >= 9) { points = 9; direction = -1 }
    else if (points <= 3) { points = 3; direction = 1 }

    spinnerAnimId = requestAnimationFrame(animate)
  }

  animate()
}

function stopSpinner() {
  if (spinnerAnimId) {
    cancelAnimationFrame(spinnerAnimId)
    spinnerAnimId = 0
  }
}

watch(loading, (val) => {
  if (val) nextTick(startSpinner)
  else stopSpinner()
})

onUnmounted(() => {
  stopSpinner()
})
</script>

<template>
  <div class="av-page">
    <!-- Background decorations -->
    <div class="av-bg">
      <div class="av-bg__orb av-bg__orb--tl"></div>
      <div class="av-bg__orb av-bg__orb--br"></div>
      <div class="av-bg__orb av-bg__orb--tr"></div>
    </div>

    <!-- Main card -->
    <div class="av-card">
      <!-- Header -->
      <div class="av-header">
        <span class="av-brand">{{ appTitle }}</span>
        <div class="av-header__right">
          <button
            v-if="registrationLoaded && registrationEnabled"
            class="av-toggle"
            @click="toggleForm"
          >
            {{ isLogin ? '注册账号' : '直接登录' }}
          </button>
        </div>
      </div>

      <!-- Title with inline toast -->
      <div class="av-title-wrap">
        <div class="av-title-row" :class="isLogin ? 'av-title-row--active' : 'av-title-row--up'">
          <h1 class="av-title">登录</h1>
          <AppToast :toast="isLogin ? toast : null" inline />
        </div>
        <div class="av-title-row" :class="!isLogin ? 'av-title-row--active' : 'av-title-row--down'">
          <h1 class="av-title">创建账号</h1>
          <AppToast :toast="!isLogin ? toast : null" inline />
        </div>
      </div>

      <!-- Form area -->
      <div
        class="av-form-container"
        :class="isLogin ? 'av-form-container--login' : 'av-form-container--register'"
      >
        <!-- Login form -->
        <form
          class="av-form"
          :class="isLogin ? 'av-form--active' : 'av-form--left'"
          @submit.prevent="submitLogin"
        >
          <div class="av-input-group">
            <i class="fa-solid fa-user av-input-icon"></i>
            <input
              v-model="account"
              type="text"
              placeholder="账号"
              class="av-input"
              required
            />
          </div>
          <div class="av-input-group">
            <i class="fa-solid fa-key av-input-icon"></i>
            <input
              v-model="password"
              :type="showPassword ? 'text' : 'password'"
              placeholder="密码"
              class="av-input av-input--pw"
              required
              @keyup.enter="submitLogin"
            />
            <button
              type="button"
              class="av-eye-btn"
              @click.prevent="showPassword = !showPassword"
            >
              <i :class="showPassword ? 'fa-solid fa-eye-slash' : 'fa-solid fa-eye'"></i>
            </button>
          </div>
        </form>

        <!-- Register form -->
        <form
          class="av-form"
          :class="!isLogin ? 'av-form--active' : 'av-form--right'"
          @submit.prevent="submitRegister"
        >
          <div class="av-input-group">
            <i class="fa-solid fa-id-card av-input-icon"></i>
            <input
              v-model="regName"
              type="text"
              placeholder="请输入真实姓名"
              class="av-input"
              required
            />
          </div>
          <div class="av-input-group">
            <i class="fa-solid fa-user av-input-icon"></i>
            <input
              v-model="regAccount"
              type="text"
              placeholder="设置登录账号"
              class="av-input"
              required
            />
          </div>
          <div class="av-input-group">
            <i class="fa-solid fa-key av-input-icon"></i>
            <input
              v-model="regPassword"
              :type="showRegPassword ? 'text' : 'password'"
              placeholder="设置密码（至少6位）"
              class="av-input av-input--pw"
              minlength="6"
              required
            />
            <button
              type="button"
              class="av-eye-btn"
              @click.prevent="showRegPassword = !showRegPassword"
            >
              <i :class="showRegPassword ? 'fa-solid fa-eye-slash' : 'fa-solid fa-eye'"></i>
            </button>
          </div>
          <div class="av-input-group">
            <i class="fa-solid fa-lock av-input-icon"></i>
            <input
              v-model="confirmPassword"
              type="password"
              placeholder="确认密码"
              class="av-input av-input--pw"
              minlength="6"
              required
              @keyup.enter="submitRegister"
            />
          </div>
        </form>
      </div>

      <!-- Footer -->
      <div class="av-footer">
        <div class="av-footer__text">
          <span class="av-footer__hint">请安全浏览！</span>
          <button class="av-browse-link" @click="router.push('/')">随便看看 →</button>
        </div>
        <button
          class="av-submit-btn"
          :class="{ 'av-submit-btn--loading': loading }"
          :disabled="loading"
          @click="isLogin ? submitLogin() : submitRegister()"
        >
          <canvas ref="spinnerCanvas" class="av-submit-btn__canvas"></canvas>
          <i class="fa-solid fa-arrow-right"></i>
        </button>
      </div>
    </div>

    <!-- Appeal Modal -->
    <Transition name="av-overlay">
      <div v-if="showAppeal" class="av-appeal-overlay" @mousedown.self="showAppeal = false">
        <div class="av-appeal-card">
          <div class="av-appeal-card__inner">
            <div class="av-appeal-header">
              <h3><i class="fa-solid fa-triangle-exclamation" style="color: var(--c-danger);"></i> 账号已被封禁</h3>
              <button class="av-appeal-close" @click="showAppeal = false"><i class="fa-solid fa-xmark"></i></button>
            </div>

            <div class="av-appeal-meta">
              <div class="av-appeal-meta__item">
                <i class="fa-solid fa-clock"></i>
                <span class="av-appeal-meta__label">解封时间</span>
                <span class="av-appeal-meta__value">{{ banUntil ? formatBanUntil(banUntil) : '永久封禁' }}</span>
              </div>
              <div class="av-appeal-meta__item">
                <i class="fa-solid fa-ban"></i>
                <span class="av-appeal-meta__label">累计封禁</span>
                <span class="av-appeal-meta__value">{{ banCount }} 次</span>
              </div>
            </div>

            <div class="av-appeal-section-title">
              <i class="fa-solid fa-file-lines"></i> 封禁原因
            </div>

            <div v-if="banContextLoading" class="av-appeal-loading">
              <span class="av-submit-btn__spinner" style="border-top-color: #1f2937;"></span>
              加载中...
            </div>

            <div v-else-if="banRecords.length === 0" class="av-appeal-empty">
              暂无详细记录
            </div>

            <div v-else class="av-appeal-table-wrap">
              <div class="av-appeal-table-scroll">
                <table class="av-appeal-table">
                  <thead>
                    <tr>
                      <th>来源</th>
                      <th>原因</th>
                      <th>时间</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(rec, i) in banRecords" :key="i">
                      <td>
                        <span v-if="rec.source === 'report'" class="av-badge av-badge--report">用户举报</span>
                        <span v-else class="av-badge av-badge--admin">管理员</span>
                      </td>
                      <td>{{ rec.reason }}</td>
                      <td class="av-appeal-time">{{ formatShort(rec.created_at) }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            <div class="av-appeal-section-title" style="margin-top: 16px;">
              <i class="fa-solid fa-paper-plane"></i> 提交申诉
            </div>
            <div class="av-appeal-form-group">
              <label class="av-appeal-label">申诉理由</label>
              <input v-model="appealReason" class="av-appeal-input" placeholder="请描述你认为封禁不合理的原因（至少5字）" />
            </div>
            <div class="av-appeal-form-group">
              <label class="av-appeal-label">证据说明</label>
              <textarea v-model="appealEvidence" class="av-appeal-input" style="min-height: 80px; resize: vertical;" placeholder="提供相关证据（链接、截图描述等，至少5字）"></textarea>
            </div>
            <button class="av-appeal-btn" style="margin-top: 12px;" :disabled="appealLoading" @click="submitAppeal">
              {{ appealLoading ? '提交中...' : '提交申诉' }}
            </button>

            <Transition name="av-msg">
              <p v-if="appealMsg" class="av-msg" :class="appealMsg.type === 'success' ? 'av-msg--success' : 'av-msg--error'" style="margin-top: 12px;">
                {{ appealMsg.text }}
              </p>
            </Transition>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
/* ---- Page & Background ---- */
.av-page {
  min-height: 100vh;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  font-family: var(--font-sans);
  overflow: hidden;
  background: #f3e7df;
}

.av-bg {
  position: absolute;
  inset: 0;
  pointer-events: none;
  overflow: hidden;
}
.av-bg__orb {
  position: absolute;
  border-radius: 50%;
}
.av-bg__orb--tl {
  top: -15%;
  left: -10%;
  width: 50vw;
  height: 50vw;
  background: rgba(255, 255, 255, 0.6);
  filter: blur(100px);
  opacity: 0.8;
  mix-blend-mode: overlay;
}
.av-bg__orb--br {
  bottom: -10%;
  right: -5%;
  width: 60vw;
  height: 60vw;
  background: linear-gradient(to top left, rgba(240, 144, 80, 0.4), transparent);
  filter: blur(120px);
}
.av-bg__orb--tr {
  top: 20%;
  right: 15%;
  width: 20vw;
  height: 20vw;
  background: rgba(255, 255, 255, 0.5);
  filter: blur(60px);
}

/* ---- Card ---- */
.av-card {
  position: relative;
  z-index: 10;
  width: 100%;
  max-width: 400px;
  background: rgba(255, 255, 255, 0.3);
  backdrop-filter: blur(40px);
  -webkit-backdrop-filter: blur(40px);
  border: 1px solid rgba(255, 255, 255, 0.4);
  box-shadow: 0 20px 60px -15px rgba(0, 0, 0, 0.05);
  border-radius: 40px;
  padding: 32px 36px;
  transition: all 0.7s cubic-bezier(0.4, 0, 0.2, 1);
}

/* ---- Header ---- */
.av-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 36px;
}
.av-brand {
  color: #6b7280;
  font-weight: 500;
  letter-spacing: 0.05em;
  font-size: 13px;
}
.av-header__right {
  min-width: 60px;
  text-align: right;
}
.av-toggle {
  background: none;
  border: none;
  color: #1f2937;
  font-weight: 500;
  font-size: 13px;
  cursor: pointer;
  transition: color 0.2s;
  padding: 0;
}
.av-toggle:hover {
  color: #000;
}

/* ---- Title ---- */
.av-title-wrap {
  position: relative;
  height: 48px;
  margin-bottom: 28px;
}
.av-title-row {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  display: flex;
  align-items: center;
  gap: 12px;
  transition: all 0.7s cubic-bezier(0.4, 0, 0.2, 1);
}
.av-title-row--active {
  opacity: 1;
  transform: translateY(0);
}
.av-title-row--up {
  opacity: 0;
  transform: translateY(-16px);
  pointer-events: none;
}
.av-title-row--down {
  opacity: 0;
  transform: translateY(16px);
  pointer-events: none;
}
.av-title {
  font-size: 32px;
  font-weight: 600;
  color: #111827;
  margin: 0;
  flex-shrink: 0;
}

/* ---- Form Container ---- */
.av-form-container {
  position: relative;
  transition: height 0.7s cubic-bezier(0.4, 0, 0.2, 1);
}
.av-form-container--login {
  height: 120px;
}
.av-form-container--register {
  height: 232px;
}

.av-form {
  position: absolute;
  inset: 0;
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 12px;
  transition: all 0.7s cubic-bezier(0.4, 0, 0.2, 1);
}
.av-form--active {
  transform: translateX(0);
  opacity: 1;
}
.av-form--left {
  transform: translateX(-100%);
  opacity: 0;
  pointer-events: none;
}
.av-form--right {
  transform: translateX(100%);
  opacity: 0;
  pointer-events: none;
}

/* ---- Input ---- */
.av-input-group {
  position: relative;
  display: flex;
  align-items: center;
  background: rgba(255, 255, 255, 0.4);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 9999px;
  padding: 0 20px;
  height: 50px;
  box-shadow: inset 0 2px 10px rgba(255, 255, 255, 0.3);
  transition: background 0.2s;
}
.av-input-group:hover,
.av-input-group:focus-within {
  background: rgba(255, 255, 255, 0.6);
}
.av-input-icon {
  color: #6b7280;
  font-size: 14px;
  margin-right: 12px;
  flex-shrink: 0;
  width: 16px;
  text-align: center;
}
.av-input {
  flex: 1;
  background: transparent;
  border: none;
  outline: none;
  color: #1f2937;
  font-size: 13px;
  font-weight: 500;
  min-width: 0;
}
.av-input::placeholder {
  color: #6b7280;
}
.av-input--pw {
  padding-right: 36px;
}
.av-input--pw::-ms-reveal,
.av-input--pw::-ms-clear,
.av-input--pw::-webkit-contacts-auto-fill-button,
.av-input--pw::-webkit-credentials-auto-fill-button {
  display: none;
  visibility: hidden;
  pointer-events: none;
}
.av-eye-btn {
  position: absolute;
  right: 16px;
  background: none;
  border: none;
  color: #9ca3af;
  cursor: pointer;
  padding: 4px;
  transition: color 0.2s;
  font-size: 14px;
}
.av-eye-btn:hover {
  color: #374151;
}

/* ---- Messages ---- */
.av-msg {
  margin-top: 12px;
  padding: 10px 16px;
  border-radius: 16px;
  font-size: 13px;
  font-weight: 500;
}
.av-msg--error {
  background: rgba(239, 68, 68, 0.12);
  color: #dc2626;
}
.av-msg--success {
  background: rgba(16, 185, 129, 0.12);
  color: #059669;
}

.av-msg-enter-active,
.av-msg-leave-active {
  transition: all 0.3s ease;
}
.av-msg-enter-from,
.av-msg-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

/* ---- Footer ---- */
.av-footer {
  margin-top: 28px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.av-footer__text {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.av-footer__hint {
  font-size: 12px;
  color: #4b5563;
  font-weight: 500;
}
.av-browse-link {
  background: none;
  border: none;
  padding: 0;
  font-size: 12px;
  color: #9ca3af;
  cursor: pointer;
  text-align: left;
  transition: color 0.2s;
}
.av-browse-link:hover {
  color: #6b7280;
  text-decoration: underline;
}

/* ---- Submit Button (organic shape) ---- */
.av-submit-btn {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 64px;
  height: 40px;
  background: #1c1c1c;
  color: #fff;
  border: none;
  border-radius: 24px 12px 24px 12px;
  cursor: pointer;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
  transition: all 0.3s ease;
  overflow: hidden;
  flex-shrink: 0;
}
.av-submit-btn:hover:not(:disabled) {
  border-radius: 16px 20px 16px 20px;
  background: #000;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.25);
}
.av-submit-btn:hover:not(:disabled) i {
  transform: translateX(3px);
}
.av-submit-btn i {
  font-size: 15px;
  transition: transform 0.3s;
  position: relative;
  z-index: 1;
}
.av-submit-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* ---- Loading state: polygon spinner ---- */
.av-submit-btn--loading {
  background: transparent;
  box-shadow: none;
  overflow: visible;
  opacity: 1;
}
.av-submit-btn--loading:hover:not(:disabled) {
  background: transparent;
  box-shadow: none;
}
.av-submit-btn--loading:hover:not(:disabled) i {
  transform: none;
}
.av-submit-btn__canvas {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 56px;
  height: 56px;
  pointer-events: none;
  opacity: 0;
  transition: opacity 0.3s ease;
}
.av-submit-btn--loading .av-submit-btn__canvas {
  opacity: 1;
}

.av-submit-btn__spinner {
  width: 18px;
  height: 18px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: av-spin 0.6s linear infinite;
}
@keyframes av-spin {
  to { transform: rotate(360deg); }
}

/* ---- Overlay transitions ---- */
.av-overlay-enter-active,
.av-overlay-leave-active {
  transition: opacity 0.3s ease;
}
.av-overlay-enter-from,
.av-overlay-leave-to {
  opacity: 0;
}

/* ---- Appeal Modal ---- */
.av-appeal-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  padding: 24px;
}
.av-appeal-card {
  width: 100%;
  max-width: 520px;
  background: rgba(255, 255, 255, 0.6);
  backdrop-filter: blur(40px);
  -webkit-backdrop-filter: blur(40px);
  border: 1px solid rgba(255, 255, 255, 0.5);
  border-radius: 32px;
  box-shadow: 0 20px 60px -15px rgba(0, 0, 0, 0.1);
  max-height: 90vh;
  overflow: hidden;
}
.av-appeal-card__inner {
  padding: 32px 36px;
  max-height: 90vh;
  overflow-y: auto;
}
.av-appeal-card__inner::-webkit-scrollbar {
  width: 6px;
}
.av-appeal-card__inner::-webkit-scrollbar-track {
  background: transparent;
}
.av-appeal-card__inner::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.1);
  border-radius: 10px;
}
.av-appeal-card__inner::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 0, 0, 0.2);
}

.av-appeal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}
.av-appeal-header h3 {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 18px;
  font-weight: 600;
  color: #111827;
  margin: 0;
}
.av-appeal-close {
  background: none;
  border: none;
  color: #6b7280;
  font-size: 18px;
  cursor: pointer;
  padding: 4px;
  transition: color 0.2s;
}
.av-appeal-close:hover {
  color: #1f2937;
}

.av-appeal-meta {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
}
.av-appeal-meta__item {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(254, 242, 242, 0.6);
  border: 1px solid rgba(254, 226, 226, 0.5);
  border-radius: 16px;
  padding: 12px 16px;
  font-size: 13px;
}
.av-appeal-meta__item i {
  color: #ef4444;
  font-size: 14px;
}
.av-appeal-meta__label {
  color: #6b7280;
  white-space: nowrap;
}
.av-appeal-meta__value {
  font-weight: 600;
  color: #111827;
}

.av-appeal-section-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 12px;
  color: #111827;
}
.av-appeal-section-title i {
  font-size: 14px;
  color: #6b7280;
}

.av-appeal-loading {
  display: flex;
  align-items: center;
  gap: 8px;
  justify-content: center;
  padding: 24px;
  color: #6b7280;
  font-size: 13px;
  font-weight: 500;
}
.av-appeal-empty {
  text-align: center;
  padding: 24px;
  color: #6b7280;
  font-size: 13px;
  background: rgba(255, 255, 255, 0.4);
  border-radius: 16px;
  border: 1px dashed rgba(255, 255, 255, 0.5);
  margin-bottom: 16px;
}

.av-appeal-table-wrap {
  background: rgba(255, 255, 255, 0.4);
  border: 1px solid rgba(255, 255, 255, 0.5);
  border-radius: 16px;
  overflow: hidden;
  margin-bottom: 16px;
}
.av-appeal-table-scroll {
  max-height: 200px;
  overflow-y: auto;
}
.av-appeal-table-scroll::-webkit-scrollbar {
  width: 5px;
}
.av-appeal-table-scroll::-webkit-scrollbar-track {
  background: transparent;
}
.av-appeal-table-scroll::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.1);
  border-radius: 10px;
}
.av-appeal-table-scroll::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 0, 0, 0.18);
}
.av-appeal-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.av-appeal-table th {
  background: #f0e8e2;
  padding: 10px 16px;
  text-align: left;
  font-weight: 600;
  color: #4b5563;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
  position: sticky;
  top: 0;
  z-index: 1;
}
.av-appeal-table td {
  padding: 12px 16px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.04);
  color: #374151;
  vertical-align: top;
}
.av-appeal-table tr:last-child td {
  border-bottom: none;
}

.av-badge {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;
  white-space: nowrap;
}
.av-badge--report {
  background: rgba(254, 243, 199, 0.8);
  color: #92400e;
}
.av-badge--admin {
  background: rgba(254, 226, 226, 0.8);
  color: #991b1b;
}
.av-appeal-time {
  white-space: nowrap;
  color: #6b7280;
  font-size: 12px;
}

.av-appeal-form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 12px;
}
.av-appeal-label {
  font-size: 13px;
  font-weight: 500;
  color: #374151;
  margin-left: 4px;
}
.av-appeal-input {
  width: 100%;
  background: rgba(255, 255, 255, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.4);
  border-radius: 16px;
  padding: 12px 16px;
  color: #1f2937;
  font-size: 13px;
  font-family: inherit;
  outline: none;
  transition: all 0.2s;
  box-shadow: inset 0 2px 8px rgba(0, 0, 0, 0.02);
}
.av-appeal-input::placeholder {
  color: #9ca3af;
}
.av-appeal-input:hover,
.av-appeal-input:focus {
  background: rgba(255, 255, 255, 0.7);
  border-color: rgba(255, 255, 255, 0.6);
}

.av-appeal-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  height: 44px;
  background: #1c1c1c;
  color: #fff;
  border: none;
  border-radius: 16px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
}
.av-appeal-btn:hover:not(:disabled) {
  background: #000;
  transform: translateY(-1px);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.2);
}
.av-appeal-btn:active:not(:disabled) {
  transform: translateY(0);
}
.av-appeal-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* ---- Responsive ---- */
@media (max-width: 480px) {
  .av-card {
    border-radius: 28px;
    padding: 24px 24px;
  }
  .av-title {
    font-size: 28px;
  }
}
</style>
