<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { fetchRegistrationStatus, register } from '../api/auth'

const router = useRouter()

const account = ref('')
const name = ref('')
const password = ref('')
const confirmPassword = ref('')
const loading = ref(false)
const registrationEnabled = ref(false)
const successMsg = ref('')
const errorMsg = ref('')

async function loadRegistrationStatus() {
  try {
    const status = await fetchRegistrationStatus()
    registrationEnabled.value = status.registration_enabled
  } catch {
    registrationEnabled.value = false
  }
}

async function submit() {
  errorMsg.value = ''
  successMsg.value = ''

  if (!registrationEnabled.value) {
    errorMsg.value = '当前已关闭注册，请联系管理员'
    return
  }

  if (password.value !== confirmPassword.value) {
    errorMsg.value = '两次输入的密码不一致'
    return
  }

  loading.value = true
  try {
    await register({ account: account.value, password: password.value, name: name.value })
    successMsg.value = '注册成功！即将跳转到登录页面...'
    setTimeout(() => router.push('/login'), 1500)
  } catch (error: any) {
    errorMsg.value = error?.response?.data?.detail || '注册失败，请稍后重试'
    await loadRegistrationStatus()
  } finally {
    loading.value = false
  }
}

onMounted(loadRegistrationStatus)
</script>

<template>
  <div class="rv-page">
    <div class="rv-card card">
      <div class="rv-brand">
        <div class="rv-logo">T</div>
        <h1>用户注册</h1>
      </div>
      <p class="rv-subtitle">
        创建账号加入校园任务平台。
        <span class="badge" :class="registrationEnabled ? 'badge-green' : 'badge-red'" style="margin-left: 4px;">
          {{ registrationEnabled ? '注册开放' : '注册关闭' }}
        </span>
      </p>

      <form @submit.prevent="submit" class="rv-form">
        <div class="form-group">
          <label class="form-label">账号</label>
          <input v-model="account" class="form-input" placeholder="请设置登录账号" required />
        </div>
        <div class="form-group">
          <label class="form-label">姓名</label>
          <input v-model="name" class="form-input" placeholder="请输入真实姓名" required />
        </div>
        <div class="form-group">
          <label class="form-label">密码</label>
          <input v-model="password" class="form-input" type="password" minlength="6" placeholder="至少 6 位" required />
        </div>
        <div class="form-group">
          <label class="form-label">确认密码</label>
          <input v-model="confirmPassword" class="form-input" type="password" minlength="6" placeholder="再次输入密码" required />
        </div>

        <button class="btn btn-primary btn-block" type="submit" :disabled="loading || !registrationEnabled">
          <span v-if="loading" class="spinner" style="width: 16px; height: 16px; border-width: 2px;"></span>
          {{ loading ? '提交中...' : '注册' }}
        </button>

        <button class="btn btn-ghost btn-block" type="button" @click="router.push('/login')">
          返回登录
        </button>
      </form>

      <Transition name="slide-fade">
        <p v-if="successMsg" class="rv-success">{{ successMsg }}</p>
      </Transition>
      <Transition name="slide-fade">
        <p v-if="errorMsg" class="rv-error">{{ errorMsg }}</p>
      </Transition>
    </div>
  </div>
</template>

<style scoped>
.rv-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: linear-gradient(145deg, #f8fafc 0%, #eef2ff 50%, #f0f9ff 100%);
}

.rv-card {
  width: 100%;
  max-width: 420px;
  padding: 36px 32px;
  box-shadow: var(--shadow-lg);
  border: 1px solid rgba(226, 232, 240, 0.6);
}

.rv-brand {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 6px;
}

.rv-logo {
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

.rv-brand h1 {
  font-size: var(--text-2xl);
  margin: 0;
}

.rv-subtitle {
  color: var(--c-text-muted);
  font-size: var(--text-sm);
  margin: 0 0 24px;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
}

.rv-form {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.rv-success {
  margin: 14px 0 0;
  padding: 10px 14px;
  background: var(--c-success-light);
  color: var(--c-success);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
}

.rv-error {
  margin: 14px 0 0;
  padding: 10px 14px;
  background: var(--c-danger-light);
  color: var(--c-danger);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
}
</style>
