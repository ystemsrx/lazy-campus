<script setup lang="ts">
import { computed } from 'vue'
import AppDropdown from '../AppDropdown.vue'
import HomeDrawer from './ui/HomeDrawer.vue'
import HomeAvatar from './ui/HomeAvatar.vue'
import type { UserMe } from '../../types/api'

type ProfileForm = {
  nickname: string
  gender: 'male' | 'female' | ''
}

type WorkerForm = {
  enabled: boolean
  skills: string
  min_price: number | null
  max_price: number | null
  bio: string
}

const props = defineProps<{
  modelValue: boolean
  settingsTab: 'profile' | 'worker'
  me: UserMe | null
  avatarUploading: boolean
  profileForm: ProfileForm
  workerForm: WorkerForm
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'update:settingsTab', value: 'profile' | 'worker'): void
  (e: 'submitProfile'): void
  (e: 'submitWorker'): void
  (e: 'avatarUpload', event: Event): void
}>()

const settingsTabValue = computed({
  get: () => props.settingsTab,
  set: (value: 'profile' | 'worker') => emit('update:settingsTab', value),
})
</script>

<template>
  <HomeDrawer :model-value="modelValue" title="设置" @update:model-value="emit('update:modelValue', $event)">
    <div class="hv-settings-tabs">
      <button class="hv-pill" :class="{ 'hv-pill--active': settingsTabValue === 'profile' }" @click="settingsTabValue = 'profile'">
        <i class="fa-solid fa-user"></i> 个人资料
      </button>
      <button class="hv-pill" :class="{ 'hv-pill--active': settingsTabValue === 'worker' }" @click="settingsTabValue = 'worker'">
        <i class="fa-solid fa-id-card"></i> 接单设置
      </button>
    </div>

    <div v-if="settingsTabValue === 'profile'" class="hv-drawer__section">
      <div class="hv-avatar-section">
        <HomeAvatar size="xl" :avatar-url="me?.avatar_url" :gender="me?.gender ?? null" alt="avatar" />
        <div class="hv-avatar-actions">
          <label class="btn btn-outline btn-sm hv-avatar-upload-btn">
            <i class="fa-solid fa-camera"></i>
            {{ avatarUploading ? '上传中...' : '更换头像' }}
            <input type="file" accept="image/*" hidden :disabled="avatarUploading" @change="emit('avatarUpload', $event)" />
          </label>
          <span class="hv-hint">支持 JPG/PNG，最大 10MB</span>
        </div>
      </div>

      <form class="hv-form" @submit.prevent="emit('submitProfile')">
        <div class="form-group">
          <label class="form-label">姓名</label>
          <input class="form-input" :value="me?.name" disabled />
          <span class="form-hint">姓名不可修改</span>
        </div>

        <div class="form-group">
          <label class="form-label">昵称</label>
          <input v-model="profileForm.nickname" class="form-input" placeholder="输入昵称" required />
        </div>

        <div class="form-group">
          <label class="form-label">性别</label>
          <AppDropdown
            v-model="profileForm.gender"
            :options="[
              { value: 'male', label: '男' },
              { value: 'female', label: '女' },
            ]"
            placeholder="选择性别"
          />
        </div>

        <button class="btn btn-primary btn-block" type="submit">保存资料</button>
      </form>
    </div>

    <div v-if="settingsTabValue === 'worker'" class="hv-drawer__section">
      <p class="hv-hint hv-hint--spaced">开启后你将出现在接单广场，其他用户可以查看你的资料。</p>
      <form class="hv-form" @submit.prevent="emit('submitWorker')">
        <label class="hv-switch-row">
          <input v-model="workerForm.enabled" type="checkbox" class="hv-switch" />
          <span>开启接单（对外展示）</span>
        </label>

        <div class="form-group">
          <label class="form-label">擅长类型</label>
          <input v-model="workerForm.skills" class="form-input" placeholder="如：高数、前端开发、跑腿取件" />
        </div>

        <div class="form-row">
          <div class="form-group">
            <label class="form-label">最低价 (¥)</label>
            <input v-model.number="workerForm.min_price" class="form-input" type="number" placeholder="最低接单价格" />
          </div>
          <div class="form-group">
            <label class="form-label">最高价 (¥)</label>
            <input v-model.number="workerForm.max_price" class="form-input" type="number" placeholder="最高接单价格" />
          </div>
        </div>

        <div class="form-group">
          <label class="form-label">个人简介</label>
          <textarea v-model="workerForm.bio" class="form-textarea" placeholder="介绍一下自己的能力和服务"></textarea>
        </div>

        <button class="btn btn-primary btn-block" type="submit">保存接单资料</button>
      </form>
    </div>
  </HomeDrawer>
</template>

<style scoped>
.hv-settings-tabs {
  display: flex;
  gap: 6px;
  padding: 16px 24px;
  border-bottom: 1px solid var(--c-border-light);
}

.hv-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 18px;
  border: 1.5px solid var(--c-border);
  border-radius: var(--radius-full);
  background: transparent;
  color: var(--c-text-secondary);
  font-size: var(--text-sm);
  font-weight: 500;
  transition: all var(--dur-fast) var(--ease);
}

.hv-pill:hover {
  border-color: var(--c-text-muted);
}

.hv-pill--active {
  background: var(--c-primary);
  color: var(--c-text-inverse);
  border-color: transparent;
}

.hv-drawer__section {
  padding: 20px 24px;
  border-bottom: 1px solid var(--c-border-light);
}

.hv-avatar-section {
  display: flex;
  align-items: center;
  gap: 20px;
  padding-bottom: 20px;
  border-bottom: 1px solid var(--c-border-light);
}

.hv-avatar-actions {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.hv-avatar-upload-btn {
  cursor: pointer;
}

.hv-form {
  display: flex;
  flex-direction: column;
  gap: 14px;
  margin-top: 16px;
}

.hv-hint {
  color: var(--c-text-muted);
  font-size: var(--text-sm);
  margin: 0;
}

.hv-hint--spaced {
  margin-bottom: 12px;
}

.hv-switch-row {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  font-size: var(--text-base);
}

.hv-switch {
  appearance: none;
  width: 40px;
  height: 22px;
  border-radius: 11px;
  background: var(--c-border);
  position: relative;
  cursor: pointer;
  transition: background var(--dur-fast) var(--ease);
  flex-shrink: 0;
}

.hv-switch::after {
  content: '';
  position: absolute;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #fff;
  top: 2px;
  left: 2px;
  transition: transform var(--dur-fast) var(--ease);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.15);
}

.hv-switch:checked {
  background: var(--c-accent);
}

.hv-switch:checked::after {
  transform: translateX(18px);
}
</style>
