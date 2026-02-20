<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

import { useAuthStore } from '../stores/auth'
import { extractError } from '../utils/error'

const router = useRouter()
const auth = useAuthStore()

const email = ref('')
const gender = ref<'male' | 'female'>('male')
const nickname = ref('')
const loading = ref(false)
const errorMsg = ref('')

async function submit() {
  errorMsg.value = ''
  loading.value = true
  try {
    await auth.completeProfile({ email: email.value, gender: gender.value, nickname: nickname.value })
    await router.push('/')
  } catch (error: any) {
    errorMsg.value = extractError(error, '保存失败')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="cp-page">
    <div class="cp-card card">
      <div class="cp-brand">
        <div class="cp-logo">T</div>
        <h1>完善个人资料</h1>
      </div>
      <p class="cp-subtitle">首次登录请设置以下信息。昵称设置后将用于对外显示，保护你的真实姓名。</p>

      <form @submit.prevent="submit" class="cp-form">
        <div class="form-group">
          <label class="form-label">邮箱</label>
          <input v-model="email" type="email" class="form-input" placeholder="请输入常用邮箱" required />
        </div>

        <div class="form-group">
          <label class="form-label">性别</label>
          <div class="cp-gender-group">
            <label v-for="opt in ([
              { value: 'male', label: '男' },
              { value: 'female', label: '女' },
            ] as const)" :key="opt.value" class="cp-gender-opt" :class="{ 'cp-gender-opt--active': gender === opt.value }">
              <input type="radio" v-model="gender" :value="opt.value" style="display: none;" />
              {{ opt.label }}
            </label>
          </div>
        </div>

        <div class="form-group">
          <label class="form-label">昵称</label>
          <input v-model="nickname" class="form-input" placeholder="请设置一个昵称" required />
        </div>

        <button class="btn btn-primary btn-block" :disabled="loading" type="submit">
          <span v-if="loading" class="spinner" style="width: 16px; height: 16px; border-width: 2px;"></span>
          {{ loading ? '提交中...' : '完成设置' }}
        </button>
      </form>

      <Transition name="slide-fade">
        <p v-if="errorMsg" class="cp-error">{{ errorMsg }}</p>
      </Transition>
    </div>
  </div>
</template>

<style scoped>
.cp-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: linear-gradient(145deg, #f8fafc 0%, #eef2ff 50%, #f0f9ff 100%);
}

.cp-card {
  width: 100%;
  max-width: 460px;
  padding: 36px 32px;
  box-shadow: var(--shadow-lg);
  border: 1px solid rgba(226, 232, 240, 0.6);
}

.cp-brand {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 6px;
}

.cp-logo {
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

.cp-brand h1 {
  font-size: var(--text-2xl);
  margin: 0;
}

.cp-subtitle {
  color: var(--c-text-muted);
  font-size: var(--text-sm);
  margin: 0 0 24px;
  line-height: 1.6;
}

.cp-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.cp-gender-group {
  display: flex;
  gap: 8px;
}

.cp-gender-opt {
  flex: 1;
  padding: 9px 0;
  text-align: center;
  border: 1.5px solid var(--c-border);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--c-text-secondary);
  cursor: pointer;
  transition: all var(--dur-fast) var(--ease);
}

.cp-gender-opt:hover {
  border-color: var(--c-accent);
  color: var(--c-accent);
}

.cp-gender-opt--active {
  background: var(--c-accent-light);
  border-color: var(--c-accent);
  color: var(--c-accent);
}

.cp-error {
  margin: 14px 0 0;
  padding: 10px 14px;
  background: var(--c-danger-light);
  color: var(--c-danger);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
}
</style>
