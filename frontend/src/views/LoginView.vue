<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { fetchRegistrationStatus } from '../api/auth'
import { createAppeal, fetchBanContext } from '../api/moderation'
import type { BanRecord } from '../types/api'
import { useAuthStore } from '../stores/auth'
import { extractError } from '../utils/error'
import { formatFull, formatShort } from '../utils/time'

const router = useRouter()
const auth = useAuthStore()

const account = ref('')
const password = ref('')
const errorMsg = ref('')
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

async function submit() {
  errorMsg.value = ''
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
      errorMsg.value = extractError(error, '登录失败，请稍后重试')
    }
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
    /* 403 info already shown; context is supplementary */
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

function goRegister() {
  if (!registrationEnabled.value) return
  router.push('/register')
}

onMounted(async () => {
  try {
    const status = await fetchRegistrationStatus()
    registrationEnabled.value = status.registration_enabled
  } catch {
    registrationEnabled.value = false
  } finally {
    registrationLoaded.value = true
  }
})
</script>

<template>
  <div class="lv-page">
    <div class="lv-card card">
      <div class="lv-brand">
        <div class="lv-logo">T</div>
        <h1>校园任务平台</h1>
      </div>
      <p class="lv-subtitle">登录你的账号以继续使用平台服务。</p>

      <form @submit.prevent="submit" class="lv-form">
        <div class="form-group">
          <label class="form-label">账号</label>
          <input v-model="account" class="form-input" placeholder="请输入账号" required />
        </div>
        <div class="form-group">
          <label class="form-label">密码</label>
          <input v-model="password" class="form-input" type="password" placeholder="请输入密码" required />
        </div>

        <button class="btn btn-primary btn-block" type="submit" :disabled="loading">
          <span v-if="loading" class="spinner" style="width: 16px; height: 16px; border-width: 2px;"></span>
          {{ loading ? '登录中...' : '登录' }}
        </button>

        <button class="btn btn-outline btn-block" type="button" :disabled="loading || !registrationEnabled" @click="goRegister">
          {{ registrationLoaded ? (registrationEnabled ? '注册新账号' : '注册已关闭') : '加载中...' }}
        </button>
      </form>

      <Transition name="slide-fade">
        <p v-if="errorMsg" class="lv-error">{{ errorMsg }}</p>
      </Transition>

      <p class="lv-footer">管理员账号从后端配置读取</p>
    </div>

    <!-- Appeal Modal -->
    <Transition name="slide-fade">
      <div v-if="showAppeal" class="lv-appeal-overlay" @mousedown.self="showAppeal = false">
        <div class="lv-appeal-card card">
          <div class="lv-appeal-header">
            <h3><i class="fa-solid fa-triangle-exclamation" style="color: var(--c-danger);"></i> 账号已被封禁</h3>
            <button class="btn btn-ghost btn-sm" @click="showAppeal = false"><i class="fa-solid fa-xmark"></i></button>
          </div>

          <div class="lv-appeal-meta">
            <div class="lv-appeal-meta__item">
              <i class="fa-solid fa-clock"></i>
              <span class="lv-appeal-meta__label">解封时间</span>
              <span class="lv-appeal-meta__value">{{ banUntil ? formatFull(banUntil) : '永久封禁' }}</span>
            </div>
            <div class="lv-appeal-meta__item">
              <i class="fa-solid fa-ban"></i>
              <span class="lv-appeal-meta__label">累计封禁</span>
              <span class="lv-appeal-meta__value">{{ banCount }} 次</span>
            </div>
          </div>

          <div class="lv-appeal-section-title">
            <i class="fa-solid fa-file-lines"></i> 封禁原因
          </div>

          <div v-if="banContextLoading" class="lv-appeal-loading">
            <span class="spinner" style="width: 16px; height: 16px; border-width: 2px;"></span>
            加载中...
          </div>

          <div v-else-if="banRecords.length === 0" class="lv-appeal-empty">
            暂无详细记录
          </div>

          <div v-else class="lv-appeal-table-wrap">
            <table class="lv-appeal-table">
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
                    <span v-if="rec.source === 'report'" class="lv-badge lv-badge--report">
                      用户举报
                    </span>
                    <span v-else class="lv-badge lv-badge--admin">
                      管理员
                    </span>
                  </td>
                  <td>{{ rec.reason }}</td>
                  <td class="lv-appeal-time">{{ formatShort(rec.created_at) }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div class="lv-appeal-section-title" style="margin-top: 16px;">
            <i class="fa-solid fa-paper-plane"></i> 提交申诉
          </div>
          <div class="form-group">
            <label class="form-label">申诉理由</label>
            <input v-model="appealReason" class="form-input" placeholder="请描述你认为封禁不合理的原因（至少5字）" />
          </div>
          <div class="form-group">
            <label class="form-label">证据说明</label>
            <textarea v-model="appealEvidence" class="form-textarea" style="min-height: 64px;" placeholder="提供相关证据（链接、截图描述等，至少5字）"></textarea>
          </div>
          <button class="btn btn-primary btn-block" style="margin-top: 12px;" :disabled="appealLoading" @click="submitAppeal">
            {{ appealLoading ? '提交中...' : '提交申诉' }}
          </button>

          <Transition name="slide-fade">
            <p v-if="appealMsg" class="lv-appeal-msg" :class="appealMsg.type === 'success' ? 'lv-appeal-msg--success' : 'lv-appeal-msg--error'">
              {{ appealMsg.text }}
            </p>
          </Transition>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.lv-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: linear-gradient(145deg, #f8fafc 0%, #eef2ff 50%, #f0f9ff 100%);
}

.lv-card {
  width: 100%;
  max-width: 420px;
  padding: 36px 32px;
  box-shadow: var(--shadow-lg);
  border: 1px solid rgba(226, 232, 240, 0.6);
}

.lv-brand {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 6px;
}

.lv-logo {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-md);
  background: var(--c-accent);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 20px;
  flex-shrink: 0;
}

.lv-brand h1 {
  font-size: var(--text-2xl);
  margin: 0;
}

.lv-subtitle {
  color: var(--c-text-muted);
  font-size: var(--text-sm);
  margin: 0 0 24px;
}

.lv-form {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.lv-error {
  margin: 14px 0 0;
  padding: 10px 14px;
  background: var(--c-danger-light);
  color: var(--c-danger);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
}

.lv-footer {
  margin: 20px 0 0;
  color: var(--c-text-muted);
  font-size: var(--text-xs);
  text-align: center;
}

/* ---- Appeal Modal ---- */
.lv-appeal-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.35);
  backdrop-filter: blur(2px);
  padding: 24px;
}

.lv-appeal-card {
  width: 100%;
  max-width: 560px;
  padding: 28px 24px;
  box-shadow: var(--shadow-xl);
  max-height: 90vh;
  overflow-y: auto;
}

.lv-appeal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
.lv-appeal-header h3 {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  margin: 0;
}

.lv-appeal-meta {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}
.lv-appeal-meta__item {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--c-danger-light, #fef2f2);
  border-radius: var(--radius-md);
  padding: 10px 14px;
  font-size: var(--text-sm);
}
.lv-appeal-meta__item i {
  color: var(--c-danger, #ef4444);
  font-size: 13px;
}
.lv-appeal-meta__label {
  color: var(--c-text-muted);
  white-space: nowrap;
}
.lv-appeal-meta__value {
  font-weight: 600;
  color: var(--c-text);
}

.lv-appeal-section-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 10px;
  color: var(--c-text);
}
.lv-appeal-section-title i {
  font-size: 13px;
  color: var(--c-text-muted);
}

.lv-appeal-loading {
  display: flex;
  align-items: center;
  gap: 8px;
  justify-content: center;
  padding: 16px;
  color: var(--c-text-muted);
  font-size: var(--text-sm);
}

.lv-appeal-empty {
  text-align: center;
  padding: 16px;
  color: var(--c-text-muted);
  font-size: var(--text-sm);
}

.lv-appeal-table-wrap {
  border: 1px solid var(--c-border, #e2e8f0);
  border-radius: var(--radius-md);
  overflow: auto;
  max-height: 200px;
  margin-bottom: 4px;
}
.lv-appeal-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--text-sm);
}
.lv-appeal-table th {
  background: var(--c-bg-muted, #f8fafc);
  padding: 8px 12px;
  text-align: left;
  font-weight: 600;
  color: var(--c-text-muted);
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.3px;
  border-bottom: 1px solid var(--c-border, #e2e8f0);
  position: sticky;
  top: 0;
  z-index: 1;
}
.lv-appeal-table td {
  padding: 10px 12px;
  border-bottom: 1px solid var(--c-border-light, #f1f5f9);
  vertical-align: top;
}
.lv-appeal-table tr:last-child td {
  border-bottom: none;
}

.lv-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 600;
  white-space: nowrap;
}
.lv-badge--report {
  background: #fef3c7;
  color: #92400e;
}
.lv-badge--admin {
  background: #fee2e2;
  color: #991b1b;
}

.lv-appeal-time {
  white-space: nowrap;
  color: var(--c-text-muted);
  font-size: 12px;
}

.lv-appeal-msg {
  margin: 12px 0 0;
  padding: 10px 14px;
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
}
.lv-appeal-msg--success {
  background: var(--c-success-light, #f0fdf4);
  color: var(--c-success, #16a34a);
}
.lv-appeal-msg--error {
  background: var(--c-danger-light, #fef2f2);
  color: var(--c-danger, #ef4444);
}
</style>
