<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()

const email = ref('')
const gender = ref<'male' | 'female' | 'other'>('male')
const nickname = ref('')
const loading = ref(false)
const errorMsg = ref('')

async function submit() {
  errorMsg.value = ''
  loading.value = true
  try {
    await auth.completeProfile({
      email: email.value,
      gender: gender.value,
      nickname: nickname.value
    })
    await router.push('/')
  } catch (error: any) {
    errorMsg.value = error?.response?.data?.detail || '保存失败'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="container" style="padding-top: 8vh;">
    <section class="card" style="max-width: 520px; margin: 0 auto;">
      <h2 style="margin-top: 0;">首次登录请补全资料</h2>
      <p class="muted">必须设置邮箱、性别、昵称。设置昵称后对外显示昵称而非真实姓名。</p>

      <form @submit.prevent="submit">
        <div style="margin-bottom: 10px;">
          <input v-model="email" type="email" class="input" placeholder="邮箱" required />
        </div>
        <div style="margin-bottom: 10px;">
          <select v-model="gender" class="select" required>
            <option value="male">男</option>
            <option value="female">女</option>
            <option value="other">其他</option>
          </select>
        </div>
        <div style="margin-bottom: 10px;">
          <input v-model="nickname" class="input" placeholder="昵称" required />
        </div>
        <button class="btn" :disabled="loading" style="width: 100%;">
          {{ loading ? '提交中...' : '提交资料' }}
        </button>
      </form>
      <p v-if="errorMsg" style="color: #b91c1c; margin-bottom: 0;">{{ errorMsg }}</p>
    </section>
  </main>
</template>
