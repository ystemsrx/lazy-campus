<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()
</script>

<template>
  <main class="nf-page">
    <div class="nf-card">
      <p class="nf-code">404</p>
      <h1 class="nf-title">页面不存在</h1>
      <p class="nf-desc">当前地址没有对应页面。</p>
      <div class="nf-actions">
        <button class="nf-btn nf-btn--primary" @click="router.push('/home')">进入任务大厅</button>
        <button class="nf-btn" @click="router.push('/login')">前往登录</button>
      </div>
    </div>
  </main>
</template>

<style scoped>
.nf-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 24px;
  background: linear-gradient(180deg, #f8fafc 0%, #eef2ff 100%);
}

.nf-card {
  width: min(520px, 100%);
  border: 1px solid #dbeafe;
  border-radius: 20px;
  padding: 28px;
  background: #fff;
  box-shadow: 0 20px 45px rgba(15, 23, 42, 0.08);
  text-align: center;
}

.nf-code {
  margin: 0;
  font-size: 56px;
  line-height: 1;
  font-weight: 800;
  color: #1d4ed8;
}

.nf-title {
  margin: 10px 0 6px;
  font-size: 28px;
  color: #0f172a;
}

.nf-desc {
  margin: 0;
  color: #475569;
}

.nf-actions {
  margin-top: 20px;
  display: flex;
  justify-content: center;
  gap: 10px;
  flex-wrap: wrap;
}

.nf-btn {
  border: 1px solid #cbd5e1;
  background: #fff;
  color: #0f172a;
  border-radius: 10px;
  padding: 10px 14px;
  font-weight: 600;
  cursor: pointer;
}

.nf-btn--primary {
  border-color: #1d4ed8;
  background: #1d4ed8;
  color: #fff;
}
</style>
