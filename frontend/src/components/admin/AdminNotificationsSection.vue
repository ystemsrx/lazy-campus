<script setup lang="ts">
import { proxyRefs } from 'vue'

import type { AdminNotificationsModel } from '../../composables/admin/useAdminNotifications'
import AppDropdown from '../AppDropdown.vue'

const props = defineProps<{
  model: AdminNotificationsModel
}>()

const vm = proxyRefs(props.model)

const targetOptions = [
  { value: 'all', label: '全体用户' },
  { value: 'active', label: '近3天活跃用户' },
  { value: 'banned', label: '受限用户' },
  { value: 'custom', label: '指定用户ID' },
]

const dismissOptions = [
  { value: 'read', label: '可读后关闭' },
  { value: 'action', label: '待操作提醒' },
  { value: 'persistent', label: '持久提醒' },
]
</script>

<template>
  <section class="av-noti">
    <div class="av-noti__head">
      <h2>通知推送中心</h2>
      <p>运营活动、风控提醒、人工触达统一入口</p>
    </div>

    <div class="card av-noti__panel">
      <div class="form-row">
        <label class="form-group">
          <span class="form-label">通知标题</span>
          <input v-model="vm.title" class="form-input" maxlength="200" placeholder="例如：平台公告 / 风险提醒" />
        </label>
        <label class="form-group">
          <span class="form-label">推送范围</span>
          <AppDropdown v-model="vm.targetMode" :options="targetOptions" width="100%" min-width="100%" />
        </label>
      </div>

      <label class="form-group">
        <span class="form-label">通知内容</span>
        <textarea v-model="vm.description" class="form-textarea" maxlength="2000" placeholder="输入具体通知内容..." />
      </label>

      <div class="form-row">
        <label class="form-group">
          <span class="form-label">关闭方式</span>
          <AppDropdown v-model="vm.dismissType" :options="dismissOptions" width="100%" min-width="100%" />
        </label>
        <label v-if="vm.targetMode === 'custom'" class="form-group">
          <span class="form-label">用户 ID 列表</span>
          <input v-model="vm.customUserIds" class="form-input" placeholder="例如：12, 18, 120" />
        </label>
      </div>

      <div class="av-noti__foot">
        <button class="btn btn-primary" :disabled="vm.sending" @click="vm.send">
          <i class="fa-solid fa-paper-plane"></i>
          {{ vm.sending ? '推送中...' : '发送通知' }}
        </button>
        <span v-if="vm.lastSentCount > 0" class="av-noti__result">
          最近一次成功发送：{{ vm.lastSentCount }} 人
        </span>
      </div>
    </div>
  </section>
</template>

<style scoped>
.av-noti {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.av-noti__head h2 {
  margin: 0;
}

.av-noti__head p {
  margin: 4px 0 0;
  color: #94a3b8;
  font-size: 13px;
}

.av-noti__panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
  border: 1px solid rgba(226, 232, 240, 0.6);
  border-radius: var(--radius-2xl);
  background: rgba(255, 255, 255, 0.8);
  box-shadow: var(--shadow-card);
  padding: 28px;
}

.av-noti__foot {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  padding-top: 8px;
}

.av-noti__foot .btn {
  border-radius: var(--radius-md);
  padding: 10px 24px;
}

.av-noti__result {
  color: var(--c-accent);
  font-size: 13px;
  font-weight: 600;
}
</style>
