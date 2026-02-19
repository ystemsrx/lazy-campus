<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import {
  banUser,
  fetchAdminDashboard,
  fetchAdminReports,
  fetchRegistrationSetting,
  reviewReport,
  updateRegistrationSetting
} from '../api/moderation'
import { useAuthStore } from '../stores/auth'
import type { Report } from '../types/api'

const auth = useAuthStore()
const router = useRouter()

const dashboard = ref<Record<string, any>>({})
const reports = ref<Report[]>([])
const banUserId = ref<number | null>(null)
const banReason = ref('')
const message = ref('')
const registrationEnabled = ref(true)
const savingRegistration = ref(false)

async function loadData() {
  try {
    const [d, r, rs] = await Promise.all([fetchAdminDashboard(), fetchAdminReports(), fetchRegistrationSetting()])
    dashboard.value = d
    reports.value = r
    registrationEnabled.value = rs.registration_enabled
  } catch (error: any) {
    message.value = error?.response?.data?.detail || '加载失败'
  }
}

async function handleReview(report: Report, status: 'approved' | 'rejected') {
  try {
    await reviewReport(report.id, { status, admin_notes: status === 'approved' ? '审核通过' : '审核驳回' })
    await loadData()
  } catch (error: any) {
    message.value = error?.response?.data?.detail || '审核失败'
  }
}

async function handleBan(banned: boolean) {
  if (!banUserId.value) return
  try {
    await banUser(banUserId.value, { banned, reason: banReason.value || undefined })
    message.value = banned ? '用户已封禁' : '用户已解封'
  } catch (error: any) {
    message.value = error?.response?.data?.detail || '操作失败'
  }
}

async function handleToggleRegistration() {
  savingRegistration.value = true
  message.value = ''
  try {
    const nextValue = !registrationEnabled.value
    const data = await updateRegistrationSetting({ registration_enabled: nextValue })
    registrationEnabled.value = data.registration_enabled
    dashboard.value.registration_enabled = data.registration_enabled
    message.value = data.registration_enabled ? '已开启用户注册' : '已关闭用户注册'
  } catch (error: any) {
    message.value = error?.response?.data?.detail || '更新注册开关失败'
  } finally {
    savingRegistration.value = false
  }
}

function logout() {
  auth.logout()
  router.push('/login')
}

onMounted(async () => {
  await loadData()
})
</script>

<template>
  <main class="container" style="padding: 20px 0 40px;">
    <header class="card" style="margin-bottom: 14px; display: flex; justify-content: space-between; align-items: center;">
      <div>
        <h2 style="margin: 0;">管理员控制台</h2>
        <p class="muted" style="margin: 4px 0 0;">内容审核、风控处置、用户封禁、数据看板</p>
      </div>
      <button class="btn secondary" @click="logout">退出</button>
    </header>

    <p v-if="message" class="card" style="margin-top: 0;">{{ message }}</p>

    <section class="grid-2" style="align-items: start;">
      <article class="card">
        <h3 style="margin-top: 0;">数据看板</h3>
        <div class="muted">总用户：{{ dashboard.total_users }}</div>
        <div class="muted">开放接单者：{{ dashboard.active_workers }}</div>
        <div class="muted">总任务：{{ dashboard.total_tasks }}</div>
        <div class="muted">已完成任务：{{ dashboard.completed_tasks }}</div>
        <div class="muted">待处理举报：{{ dashboard.pending_reports }}</div>
        <div class="muted">完成率：{{ dashboard.completion_rate }}</div>
        <div class="muted">注册开关：{{ registrationEnabled ? '开启' : '关闭' }}</div>
        <button class="btn ghost" style="margin-top: 8px;" :disabled="savingRegistration" @click="handleToggleRegistration">
          {{ savingRegistration ? '保存中...' : (registrationEnabled ? '关闭注册' : '开启注册') }}
        </button>
      </article>

      <article class="card">
        <h3 style="margin-top: 0;">用户封禁</h3>
        <div class="row">
          <input v-model.number="banUserId" type="number" class="input" placeholder="用户ID" />
          <input v-model="banReason" class="input" placeholder="原因（可选）" />
        </div>
        <div class="row" style="margin-top: 8px;">
          <button class="btn" @click="handleBan(true)">封禁</button>
          <button class="btn ghost" @click="handleBan(false)">解封</button>
        </div>
      </article>
    </section>

    <section class="card" style="margin-top: 14px;">
      <h3 style="margin-top: 0;">举报/申诉审核</h3>
      <div style="display: grid; gap: 8px; max-height: 560px; overflow: auto;">
        <div v-for="report in reports" :key="report.id" class="card" style="padding: 10px;">
          <div style="display: flex; justify-content: space-between;">
            <b>#{{ report.id }} {{ report.type }}</b>
            <span class="badge">{{ report.status }}</span>
          </div>
          <p class="muted">任务ID：{{ report.task_id || '-' }} ｜ 被举报用户：{{ report.reported_user_id || '-' }}</p>
          <p class="muted">原因：{{ report.reason }}</p>
          <p class="muted">证据：{{ report.evidence }}</p>
          <div class="row" v-if="report.status === 'pending'">
            <button class="btn" @click="handleReview(report, 'approved')">通过</button>
            <button class="btn ghost" @click="handleReview(report, 'rejected')">驳回</button>
          </div>
        </div>
        <p v-if="reports.length === 0" class="muted">暂无数据</p>
      </div>
    </section>
  </main>
</template>
