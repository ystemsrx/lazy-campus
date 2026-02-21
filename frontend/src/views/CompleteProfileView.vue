<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'

import AppToast from '../components/AppToast.vue'
import { useAppToast } from '../composables/useAppToast'
import { useAuthStore } from '../stores/auth'
import { extractError } from '../utils/error'

const router = useRouter()
const auth = useAuthStore()

const logoFile = import.meta.env.VITE_APP_LOGO as string | undefined
const logoUrl = computed(() =>
  logoFile ? `/logos/${logoFile}` : null,
)

const email = ref('')
const gender = ref<'male' | 'female'>('male')
const nickname = ref('')
const loading = ref(false)

const { toast, showToast } = useAppToast()

async function submit() {
  loading.value = true
  try {
    await auth.completeProfile({ email: email.value, gender: gender.value, nickname: nickname.value || null })
    await router.push('/')
  } catch (error: any) {
    showToast(extractError(error, '保存失败'), 'error')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="cp-page">
    <!-- 动态背景装饰 -->
    <div class="cp-blob cp-blob--tl"></div>
    <div class="cp-blob cp-blob--br"></div>


    <div class="cp-container">
      <!-- 卡片主体 -->
      <div class="cp-card">

        <!-- 头部 Logo 与标题 -->
        <div class="cp-header">
          <div class="cp-brand-row">
            <div class="cp-logo-wrap">
              <img v-if="logoUrl" :src="logoUrl" class="cp-logo-img" alt="Logo" />
              <div v-else class="cp-logo-icon">
                <i class="fa-solid fa-handshake"></i>
              </div>
            </div>
            <span class="cp-welcome">欢迎使用</span>
            <AppToast :toast="toast" inline />
          </div>
          <p class="cp-desc">首次登录请设置以下信息。昵称设置后将用于对外显示，以保护你的真实姓名。</p>
        </div>

        <form @submit.prevent="submit" class="cp-form">

          <!-- 邮箱输入框 -->
          <div class="cp-field">
            <label class="cp-label">邮箱<span class="cp-required">*</span></label>
            <div class="cp-input-wrap" :class="{ 'cp-input-wrap--focused': false }">
              <svg class="cp-input-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <rect width="20" height="16" x="2" y="4" rx="2"/>
                <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/>
              </svg>
              <input
                v-model="email"
                type="email"
                class="cp-input"
                placeholder="请输入常用邮箱"
                required
              />
            </div>
          </div>

          <!-- 性别选择 (滑动分段控制器) -->
          <div class="cp-field">
            <label class="cp-label">性别<span class="cp-required">*</span></label>
            <div class="cp-gender-seg">
              <!-- 滑动背景块 -->
              <div class="cp-gender-pill" :class="{ 'cp-gender-pill--right': gender === 'female' }"></div>
              <button
                type="button"
                class="cp-gender-btn"
                :class="{ 'cp-gender-btn--male': gender === 'male' }"
                @click="gender = 'male'"
              >男</button>
              <button
                type="button"
                class="cp-gender-btn"
                :class="{ 'cp-gender-btn--female': gender === 'female' }"
                @click="gender = 'female'"
              >女</button>
            </div>
          </div>

          <!-- 昵称输入框 -->
          <div class="cp-field">
            <label class="cp-label">昵称</label>
            <div class="cp-input-wrap">
              <svg class="cp-input-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="8" r="4"/>
                <path d="M20 21a8 8 0 1 0-16 0"/>
              </svg>
              <input
                v-model="nickname"
                type="text"
                class="cp-input"
                placeholder="请设置一个昵称"
              />
            </div>
          </div>

          <!-- 提交按钮 -->
          <div class="cp-submit-wrap">
            <button
              type="submit"
              :disabled="loading"
              class="cp-submit-btn"
            >
              <!-- 光泽动画 -->
              <span class="cp-shimmer"></span>
              <span class="cp-btn-inner">
                <template v-if="loading">
                  <svg class="cp-spinner" viewBox="0 0 24 24" fill="none">
                    <circle class="cp-spinner-track" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                    <path class="cp-spinner-arc" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
                  </svg>
                  提交中...
                </template>
                <template v-else>
                  完成设置
                  <svg class="cp-arrow-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M5 12h14"/><path d="m12 5 7 7-7 7"/>
                  </svg>
                </template>
              </span>
            </button>
          </div>

        </form>
      </div>

    </div>
  </div>
</template>

<style scoped>
/* ───── 页面底层 ───── */
.cp-page {
  min-height: 100vh;
  background: #f4f7fb;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  position: relative;
  overflow: hidden;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

/* ───── 背景光晕 ───── */
.cp-blob {
  position: absolute;
  width: 40%;
  height: 40%;
  border-radius: 50%;
  filter: blur(80px);
  mix-blend-mode: multiply;
  animation: blob 7s infinite;
}
.cp-blob--tl {
  top: -10%;
  left: -10%;
  background: rgba(96, 165, 250, 0.2);
}
.cp-blob--br {
  bottom: -10%;
  right: -10%;
  background: rgba(129, 140, 248, 0.18);
  animation-delay: 2s;
}
@keyframes blob {
  0%   { transform: translate(0, 0) scale(1); }
  33%  { transform: translate(30px, -50px) scale(1.1); }
  66%  { transform: translate(-20px, 20px) scale(0.9); }
  100% { transform: translate(0, 0) scale(1); }
}

/* ───── 内容容器 ───── */
.cp-container {
  max-width: 420px;
  width: 100%;
  position: relative;
  z-index: 10;
}

/* ───── 卡片 ───── */
.cp-card {
  background: rgba(255, 255, 255, 0.82);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-radius: 2rem;
  box-shadow: 0 20px 40px -15px rgba(0, 0, 0, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.9);
  padding: 40px;
}

/* ───── 头部 ───── */
.cp-header {
  margin-bottom: 24px;
}
.cp-brand-row {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 14px;
}

/* Logo 区域 */
.cp-logo-wrap {
  width: 56px;
  height: 56px;
  border-radius: 16px;
  flex-shrink: 0;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}
.cp-logo-img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}
.cp-logo-icon {
  width: 100%;
  height: 100%;
  background: linear-gradient(135deg, #2563eb 0%, #818cf8 100%);
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 8px 20px -4px rgba(37, 99, 235, 0.35);
}
.cp-logo-icon i {
  color: #fff;
  font-size: 22px;
}

.cp-welcome {
  font-size: 22px;
  font-weight: 700;
  color: #1e293b;
  letter-spacing: -0.02em;
}
.cp-desc {
  font-size: 13px;
  color: #6b7280;
  margin: 0;
  line-height: 1.7;
}

/* ───── 表单 ───── */
.cp-form {
  display: flex;
  flex-direction: column;
  gap: 22px;
}
.cp-field {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.cp-label {
  font-size: 13px;
  font-weight: 500;
  color: #374151;
  margin-left: 4px;
}
.cp-required {
  color: #ef4444;
  margin-left: 3px;
}

/* 输入框 */
.cp-input-wrap {
  position: relative;
  display: flex;
  align-items: center;
}
.cp-input-icon {
  position: absolute;
  left: 16px;
  color: #9ca3af;
  pointer-events: none;
  transition: color 0.2s;
  flex-shrink: 0;
}
.cp-input-wrap:focus-within .cp-input-icon {
  color: #3b82f6;
}
.cp-input {
  width: 100%;
  padding: 14px 16px 14px 44px;
  background: rgba(249, 250, 251, 0.6);
  border: 1.5px solid #f3f4f6;
  border-radius: 16px;
  font-size: 14px;
  color: #1f2937;
  outline: none;
  transition: all 0.25s ease;
  box-sizing: border-box;
}
.cp-input::placeholder {
  color: #9ca3af;
}
.cp-input:focus {
  background: #ffffff;
  border-color: #3b82f6;
  box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.10);
}

/* 性别分段控制器 */
.cp-gender-seg {
  position: relative;
  display: flex;
  padding: 6px;
  background: rgba(243, 244, 246, 0.8);
  border-radius: 16px;
}
.cp-gender-pill {
  position: absolute;
  top: 6px;
  bottom: 6px;
  left: 6px;
  width: calc(50% - 9px);
  background: #ffffff;
  border-radius: 12px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.08);
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  z-index: 0;
}
.cp-gender-pill--right {
  transform: translateX(calc(100% + 6px));
}
.cp-gender-btn {
  position: relative;
  z-index: 1;
  flex: 1;
  padding: 12px 0;
  background: none;
  border: none;
  font-size: 14px;
  font-weight: 600;
  color: #6b7280;
  cursor: pointer;
  transition: color 0.2s ease;
  border-radius: 10px;
}
.cp-gender-btn--male {
  color: #2563eb;
}
.cp-gender-btn--female {
  color: #ec4899;
}

/* 提交按钮区域 */
.cp-submit-wrap {
  padding-top: 8px;
}
.cp-submit-btn {
  width: 100%;
  position: relative;
  overflow: hidden;
  background: #2563eb;
  color: #ffffff;
  border: none;
  border-radius: 16px;
  padding: 16px 24px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  box-shadow: 0 8px 20px -6px rgba(37, 99, 235, 0.4);
  transition: background 0.2s, box-shadow 0.2s, transform 0.1s;
  display: flex;
  align-items: center;
  justify-content: center;
}
.cp-submit-btn:hover:not(:disabled) {
  background: #1d4ed8;
  box-shadow: 0 12px 25px -6px rgba(37, 99, 235, 0.5);
}
.cp-submit-btn:active:not(:disabled) {
  transform: scale(0.98);
}
.cp-submit-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

/* 光泽动画 */
.cp-shimmer {
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.22), transparent);
  transform: translateX(-100%);
  pointer-events: none;
}
.cp-submit-btn:hover:not(:disabled) .cp-shimmer {
  animation: shimmer 1.5s infinite;
}
@keyframes shimmer {
  100% { transform: translateX(100%); }
}

.cp-btn-inner {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 箭头动画 */
.cp-arrow-icon {
  transition: transform 0.2s ease;
}
.cp-submit-btn:hover:not(:disabled) .cp-arrow-icon {
  transform: translateX(3px);
}

/* 加载 spinner */
.cp-spinner {
  width: 18px;
  height: 18px;
  animation: spin 0.8s linear infinite;
}
.cp-spinner-track { opacity: 0.25; }
.cp-spinner-arc { opacity: 0.75; }
@keyframes spin {
  to { transform: rotate(360deg); }
}

</style>
