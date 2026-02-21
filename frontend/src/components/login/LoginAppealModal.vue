<script setup lang="ts">
import { ref, watch } from 'vue'

import { createAppeal, fetchBanContext } from '../../api/moderation'
import type { BanRecord } from '../../types/api'
import { extractError } from '../../utils/error'
import { formatBanUntil, formatShort } from '../../utils/time'

const props = defineProps<{
  modelValue: boolean
  account: string
  password: string
  initialBanUntil: string | null
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
}>()

const banUntil = ref<string | null>(null)
const banCount = ref(0)
const banRecords = ref<BanRecord[]>([])
const banContextLoading = ref(false)
const appealReason = ref('')
const appealEvidence = ref('')
const appealLoading = ref(false)
const appealMsg = ref<{ text: string; type: 'success' | 'error' } | null>(null)

function closeModal() {
  emit('update:modelValue', false)
}

async function loadBanContext() {
  banContextLoading.value = true
  try {
    const ctx = await fetchBanContext({
      account: props.account,
      password: props.password,
    })
    banUntil.value = ctx.ban_until
    banCount.value = ctx.ban_count
    banRecords.value = ctx.records
  } catch {
    /* supplementary */
  } finally {
    banContextLoading.value = false
  }
}

async function submitAppeal() {
  if (!appealReason.value.trim() || !appealEvidence.value.trim()) {
    appealMsg.value = { text: '请填写申诉理由和证据', type: 'error' }
    return
  }

  appealLoading.value = true
  appealMsg.value = null
  try {
    await createAppeal({
      account: props.account,
      password: props.password,
      reason: appealReason.value,
      evidence: appealEvidence.value,
    })
    appealMsg.value = { text: '申诉已提交，请等待管理员审核', type: 'success' }
    appealReason.value = ''
    appealEvidence.value = ''
  } catch (error: any) {
    appealMsg.value = { text: extractError(error, '提交失败'), type: 'error' }
  } finally {
    appealLoading.value = false
  }
}

watch(
  () => props.modelValue,
  (visible) => {
    if (!visible) return
    banUntil.value = props.initialBanUntil
    loadBanContext()
  }
)

watch(
  () => props.initialBanUntil,
  (value) => {
    if (props.modelValue) {
      banUntil.value = value
      loadBanContext()
    }
  }
)
</script>

<template>
  <Transition name="av-overlay">
    <div v-if="modelValue" class="av-appeal-overlay" @mousedown.self="closeModal">
      <div class="av-appeal-card">
        <div class="av-appeal-card__inner">
          <div class="av-appeal-header">
            <h3><i class="fa-solid fa-triangle-exclamation" style="color: var(--c-danger);"></i> 账号已被封禁</h3>
            <button class="av-appeal-close" @click="closeModal"><i class="fa-solid fa-xmark"></i></button>
          </div>

          <div class="av-appeal-meta">
            <div class="av-appeal-meta__item">
              <i class="fa-solid fa-clock"></i>
              <span class="av-appeal-meta__label">解封时间</span>
              <span class="av-appeal-meta__value">{{ banUntil ? formatBanUntil(banUntil) : '永久封禁' }}</span>
            </div>
            <div class="av-appeal-meta__item">
              <i class="fa-solid fa-ban"></i>
              <span class="av-appeal-meta__label">累计封禁</span>
              <span class="av-appeal-meta__value">{{ banCount }} 次</span>
            </div>
          </div>

          <div class="av-appeal-section-title">
            <i class="fa-solid fa-file-lines"></i> 封禁原因
          </div>

          <div v-if="banContextLoading" class="av-appeal-loading">
            <span class="av-appeal-spinner"></span>
            加载中...
          </div>

          <div v-else-if="banRecords.length === 0" class="av-appeal-empty">
            暂无详细记录
          </div>

          <div v-else class="av-appeal-table-wrap">
            <div class="av-appeal-table-scroll">
              <table class="av-appeal-table">
                <thead>
                  <tr>
                    <th>来源</th>
                    <th>原因</th>
                    <th>时间</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(rec, i) in banRecords" :key="i">
                    <td>
                      <span v-if="rec.source === 'report'" class="av-badge av-badge--report">用户举报</span>
                      <span v-else class="av-badge av-badge--admin">管理员</span>
                    </td>
                    <td>{{ rec.reason }}</td>
                    <td class="av-appeal-time">{{ formatShort(rec.created_at) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <div class="av-appeal-section-title" style="margin-top: 16px;">
            <i class="fa-solid fa-paper-plane"></i> 提交申诉
          </div>
          <div class="av-appeal-form-group">
            <label class="av-appeal-label">申诉理由</label>
            <input v-model="appealReason" class="av-appeal-input" placeholder="请描述你认为封禁不合理的原因（至少5字）" />
          </div>
          <div class="av-appeal-form-group">
            <label class="av-appeal-label">证据说明</label>
            <textarea v-model="appealEvidence" class="av-appeal-input" style="min-height: 80px; resize: vertical;" placeholder="提供相关证据（链接、截图描述等，至少5字）"></textarea>
          </div>
          <button class="av-appeal-btn" style="margin-top: 12px;" :disabled="appealLoading" @click="submitAppeal">
            {{ appealLoading ? '提交中...' : '提交申诉' }}
          </button>

          <Transition name="av-msg">
            <p v-if="appealMsg" class="av-msg" :class="appealMsg.type === 'success' ? 'av-msg--success' : 'av-msg--error'" style="margin-top: 12px;">
              {{ appealMsg.text }}
            </p>
          </Transition>
        </div>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.av-msg {
  margin-top: 12px;
  padding: 10px 16px;
  border-radius: 16px;
  font-size: 13px;
  font-weight: 500;
}
.av-msg--error {
  background: rgba(239, 68, 68, 0.12);
  color: #dc2626;
}
.av-msg--success {
  background: rgba(16, 185, 129, 0.12);
  color: #059669;
}

.av-msg-enter-active,
.av-msg-leave-active {
  transition: all 0.3s ease;
}
.av-msg-enter-from,
.av-msg-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

.av-overlay-enter-active,
.av-overlay-leave-active {
  transition: opacity 0.3s ease;
}
.av-overlay-enter-from,
.av-overlay-leave-to {
  opacity: 0;
}

.av-appeal-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  padding: 24px;
}
.av-appeal-card {
  width: 100%;
  max-width: 520px;
  background: rgba(255, 255, 255, 0.6);
  backdrop-filter: blur(40px);
  -webkit-backdrop-filter: blur(40px);
  border: 1px solid rgba(255, 255, 255, 0.5);
  border-radius: 32px;
  box-shadow: 0 20px 60px -15px rgba(0, 0, 0, 0.1);
  max-height: 90vh;
  overflow: hidden;
}
.av-appeal-card__inner {
  padding: 32px 36px;
  max-height: 90vh;
  overflow-y: auto;
}
.av-appeal-card__inner::-webkit-scrollbar {
  width: 6px;
}
.av-appeal-card__inner::-webkit-scrollbar-track {
  background: transparent;
}
.av-appeal-card__inner::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.1);
  border-radius: 10px;
}
.av-appeal-card__inner::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 0, 0, 0.2);
}

.av-appeal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}
.av-appeal-header h3 {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 18px;
  font-weight: 600;
  color: #111827;
  margin: 0;
}
.av-appeal-close {
  background: none;
  border: none;
  color: #6b7280;
  font-size: 18px;
  cursor: pointer;
  padding: 4px;
  transition: color 0.2s;
}
.av-appeal-close:hover {
  color: #1f2937;
}

.av-appeal-meta {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
}
.av-appeal-meta__item {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(254, 242, 242, 0.6);
  border: 1px solid rgba(254, 226, 226, 0.5);
  border-radius: 16px;
  padding: 12px 16px;
  font-size: 13px;
}
.av-appeal-meta__item i {
  color: #ef4444;
  font-size: 14px;
}
.av-appeal-meta__label {
  color: #6b7280;
  white-space: nowrap;
}
.av-appeal-meta__value {
  font-weight: 600;
  color: #111827;
}

.av-appeal-section-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 12px;
  color: #111827;
}
.av-appeal-section-title i {
  font-size: 14px;
  color: #6b7280;
}

.av-appeal-loading {
  display: flex;
  align-items: center;
  gap: 8px;
  justify-content: center;
  padding: 24px;
  color: #6b7280;
  font-size: 13px;
  font-weight: 500;
}
.av-appeal-spinner {
  width: 18px;
  height: 18px;
  border: 2px solid rgba(31, 41, 55, 0.2);
  border-top-color: #1f2937;
  border-radius: 50%;
  animation: av-spin 0.6s linear infinite;
}

.av-appeal-empty {
  text-align: center;
  padding: 24px;
  color: #6b7280;
  font-size: 13px;
  background: rgba(255, 255, 255, 0.4);
  border-radius: 16px;
  border: 1px dashed rgba(255, 255, 255, 0.5);
  margin-bottom: 16px;
}

.av-appeal-table-wrap {
  background: rgba(255, 255, 255, 0.4);
  border: 1px solid rgba(255, 255, 255, 0.5);
  border-radius: 16px;
  overflow: hidden;
  margin-bottom: 16px;
}
.av-appeal-table-scroll {
  max-height: 200px;
  overflow-y: auto;
}
.av-appeal-table-scroll::-webkit-scrollbar {
  width: 5px;
}
.av-appeal-table-scroll::-webkit-scrollbar-track {
  background: transparent;
}
.av-appeal-table-scroll::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.1);
  border-radius: 10px;
}
.av-appeal-table-scroll::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 0, 0, 0.18);
}
.av-appeal-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.av-appeal-table th {
  background: #f0e8e2;
  padding: 10px 16px;
  text-align: left;
  font-weight: 600;
  color: #4b5563;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
  position: sticky;
  top: 0;
  z-index: 1;
}
.av-appeal-table td {
  padding: 12px 16px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.04);
  color: #374151;
  vertical-align: top;
}
.av-appeal-table tr:last-child td {
  border-bottom: none;
}

.av-badge {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;
  white-space: nowrap;
}
.av-badge--report {
  background: rgba(254, 243, 199, 0.8);
  color: #92400e;
}
.av-badge--admin {
  background: rgba(254, 226, 226, 0.8);
  color: #991b1b;
}
.av-appeal-time {
  white-space: nowrap;
  color: #6b7280;
  font-size: 12px;
}

.av-appeal-form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 12px;
}
.av-appeal-label {
  font-size: 13px;
  font-weight: 500;
  color: #374151;
  margin-left: 4px;
}
.av-appeal-input {
  width: 100%;
  background: rgba(255, 255, 255, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.4);
  border-radius: 16px;
  padding: 12px 16px;
  color: #1f2937;
  font-size: 13px;
  font-family: inherit;
  outline: none;
  transition: all 0.2s;
  box-shadow: inset 0 2px 8px rgba(0, 0, 0, 0.02);
}
.av-appeal-input::placeholder {
  color: #9ca3af;
}
.av-appeal-input:hover,
.av-appeal-input:focus {
  background: rgba(255, 255, 255, 0.7);
  border-color: rgba(255, 255, 255, 0.6);
}

.av-appeal-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  height: 44px;
  background: #1c1c1c;
  color: #fff;
  border: none;
  border-radius: 16px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
}
.av-appeal-btn:hover:not(:disabled) {
  background: #000;
  transform: translateY(-1px);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.2);
}
.av-appeal-btn:active:not(:disabled) {
  transform: translateY(0);
}
.av-appeal-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

@keyframes av-spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
