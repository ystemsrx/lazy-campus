<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { fetchRegistrationStatus } from '../api/auth'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()

const account = ref('')
const password = ref('')
const errorMsg = ref('')
const loading = ref(false)
const registrationEnabled = ref(false)
const registrationLoaded = ref(false)

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
    errorMsg.value = error?.response?.data?.detail || '登录失败，请稍后重试'
  } finally {
    loading.value = false
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
</style>
