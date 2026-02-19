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
const message = ref('')
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
  message.value = ''

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
    await register({
      account: account.value,
      password: password.value,
      name: name.value
    })
    message.value = '注册成功，请返回登录'
  } catch (error: any) {
    errorMsg.value = error?.response?.data?.detail || '注册失败，请稍后重试'
    await loadRegistrationStatus()
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await loadRegistrationStatus()
})
</script>

<template>
  <main class="container" style="padding-top: 9vh;">
    <section class="card" style="max-width: 460px; margin: 0 auto;">
      <h1 style="margin-top: 0;">用户注册</h1>
      <p class="muted" style="margin-bottom: 12px;">管理员可在后台开启或关闭注册。</p>
      <form @submit.prevent="submit">
        <div style="margin-bottom: 10px;">
          <input v-model="account" class="input" placeholder="账号" required />
        </div>
        <div style="margin-bottom: 10px;">
          <input v-model="name" class="input" placeholder="姓名" required />
        </div>
        <div style="margin-bottom: 10px;">
          <input v-model="password" class="input" type="password" minlength="6" placeholder="密码（至少6位）" required />
        </div>
        <div style="margin-bottom: 10px;">
          <input v-model="confirmPassword" class="input" type="password" minlength="6" placeholder="确认密码" required />
        </div>
        <button class="btn" type="submit" :disabled="loading || !registrationEnabled" style="width: 100%;">
          {{ loading ? '提交中...' : '注册' }}
        </button>
        <button class="btn ghost" type="button" style="width: 100%; margin-top: 8px;" @click="router.push('/login')">
          返回登录
        </button>
      </form>
      <p v-if="message" style="color: #047857; margin-bottom: 0;">{{ message }}</p>
      <p v-if="errorMsg" style="color: #b91c1c; margin-bottom: 0;">{{ errorMsg }}</p>
      <p class="muted" style="margin-top: 14px;">
        当前注册状态：{{ registrationEnabled ? '开启' : '关闭' }}
      </p>
    </section>
  </main>
</template>
