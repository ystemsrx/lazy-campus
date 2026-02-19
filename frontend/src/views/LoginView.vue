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
  <main class="container" style="padding-top: 9vh;">
    <section class="card" style="max-width: 460px; margin: 0 auto;">
      <h1 style="margin-top: 0;">校园任务平台</h1>
      <p class="muted">登录策略：本地数据库优先，失败后回退第三方认证并自动同步账号。</p>
      <form @submit.prevent="submit">
        <div style="margin-bottom: 10px;">
          <input v-model="account" class="input" placeholder="账号" required />
        </div>
        <div style="margin-bottom: 10px;">
          <input v-model="password" class="input" type="password" placeholder="密码" required />
        </div>
        <button class="btn" type="submit" :disabled="loading" style="width: 100%;">
          {{ loading ? '登录中...' : '登录' }}
        </button>
        <button
          class="btn secondary"
          type="button"
          style="width: 100%; margin-top: 8px;"
          :disabled="loading || !registrationEnabled"
          @click="goRegister"
        >
          {{ registrationLoaded ? (registrationEnabled ? '去注册' : '注册已关闭') : '注册状态加载中...' }}
        </button>
      </form>
      <p v-if="errorMsg" style="color: #b91c1c; margin-bottom: 0;">{{ errorMsg }}</p>
      <p class="muted" style="margin-top: 14px;">
        管理员账号从后端 .env 配置读取。
      </p>
    </section>
  </main>
</template>
