<script setup lang="ts">
import { ref, watch } from 'vue'

import AppToast from '../AppToast.vue'
import { createAppeal, createAuthenticatedAppeal, fetchBanContext, fetchMyBanContext, uploadAppealImage } from '../../api/moderation'
import { useAppToast } from '../../composables/useAppToast'
import type { BanRecord } from '../../types/api'
import { extractError } from '../../utils/error'
import { formatBanUntil, formatShort } from '../../utils/time'

const props = withDefaults(defineProps<{
  modelValue: boolean
  account?: string
  password?: string
  initialBanUntil?: string | null
  authenticated?: boolean
}>(), {
  account: '',
  password: '',
  initialBanUntil: null,
  authenticated: false,
})

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'submitted'): void
}>()

const REASON_MAX = 20
const EVIDENCE_MAX = 200
const MAX_IMAGES = 3

type UploadedImage = {
  id: string
  previewUrl: string
  blob: Blob
}

const banUntil = ref<string | null>(null)
const banCount = ref(0)
const banRecords = ref<BanRecord[]>([])
const banContextLoading = ref(false)
const appealReason = ref('')
const appealEvidence = ref('')
const appealImages = ref<UploadedImage[]>([])
const fileInputRef = ref<HTMLInputElement | null>(null)
const lightboxSrc = ref<string | null>(null)
const appealLoading = ref(false)
const { toast, showToast, clearToast } = useAppToast(3500)

function closeModal() {
  emit('update:modelValue', false)
}

function triggerFileInput() {
  fileInputRef.value?.click()
}

async function compressToWebPBlob(file: File): Promise<Blob> {
  return new Promise((resolve, reject) => {
    const img = new Image()
    const objectUrl = URL.createObjectURL(file)
    img.onload = () => {
      URL.revokeObjectURL(objectUrl)
      const canvas = document.createElement('canvas')
      canvas.width = img.naturalWidth
      canvas.height = img.naturalHeight
      const ctx = canvas.getContext('2d')!
      ctx.drawImage(img, 0, 0)
      canvas.toBlob(
        (blob) => {
          if (blob) resolve(blob)
          else reject(new Error('WebP 转换失败'))
        },
        'image/webp',
        0.8,
      )
    }
    img.onerror = () => {
      URL.revokeObjectURL(objectUrl)
      reject(new Error('图片加载失败'))
    }
    img.src = objectUrl
  })
}

async function handleFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  if (!input.files) return
  const files = Array.from(input.files)
  input.value = ''
  const remaining = MAX_IMAGES - appealImages.value.length
  for (const file of files.slice(0, remaining)) {
    try {
      const blob = await compressToWebPBlob(file)
      const previewUrl = URL.createObjectURL(blob)
      appealImages.value.push({ id: Math.random().toString(36).slice(2), previewUrl, blob })
    } catch { /* 单张失败不影响其他 */ }
  }
}

function removeImage(id: string) {
  const img = appealImages.value.find((i) => i.id === id)
  if (img) URL.revokeObjectURL(img.previewUrl)
  appealImages.value = appealImages.value.filter((i) => i.id !== id)
}

async function loadBanContext() {
  banContextLoading.value = true
  try {
    const ctx = props.authenticated
      ? await fetchMyBanContext()
      : await fetchBanContext({ account: props.account, password: props.password })
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
    showToast('请填写申诉理由和证据', 'error')
    return
  }

  appealLoading.value = true
  clearToast()
  try {
    const imageUrls = await Promise.all(
      appealImages.value.map((img) => uploadAppealImage(img.blob)),
    )
    if (props.authenticated) {
      await createAuthenticatedAppeal({
        reason: appealReason.value,
        evidence: appealEvidence.value,
        images: imageUrls,
      })
    } else {
      await createAppeal({
        account: props.account,
        password: props.password,
        reason: appealReason.value,
        evidence: appealEvidence.value,
        images: imageUrls,
      })
    }
    showToast('申诉已提交，请等待管理员审核', 'success')
    appealReason.value = ''
    appealEvidence.value = ''
    appealImages.value.forEach((img) => URL.revokeObjectURL(img.previewUrl))
    appealImages.value = []
    emit('submitted')
  } catch (error: any) {
    showToast(extractError(error, '提交失败'), 'error')
  } finally {
    appealLoading.value = false
  }
}

watch(
  () => props.modelValue,
  (visible) => {
    if (!visible) {
      appealImages.value.forEach((img) => URL.revokeObjectURL(img.previewUrl))
      appealImages.value = []
      lightboxSrc.value = null
      return
    }
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
        <div class="av-appeal-header">
          <h3><i class="fa-solid fa-triangle-exclamation" style="color: var(--c-danger);"></i> {{ authenticated ? '账号功能受限' : '账号已被封禁' }}</h3>
          <button class="av-appeal-close" @click="closeModal"><i class="fa-solid fa-xmark"></i></button>
        </div>
        <div class="av-appeal-card__inner">
          <div class="av-appeal-meta">
            <div class="av-appeal-meta__item">
              <div class="av-appeal-meta__top">
                <i class="fa-solid fa-clock"></i>
                <span class="av-appeal-meta__label">解封时间</span>
              </div>
              <span class="av-appeal-meta__value">{{ banUntil ? formatBanUntil(banUntil) : '永久封禁' }}</span>
            </div>
            <div class="av-appeal-meta__item">
              <div class="av-appeal-meta__top">
                <i class="fa-solid fa-ban"></i>
                <span class="av-appeal-meta__label">累计封禁</span>
              </div>
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
            <div class="av-appeal-label-row">
              <label class="av-appeal-label">申诉理由 <span class="av-required">*</span></label>
              <span class="av-charcount" :class="{ 'av-charcount--limit': appealReason.length >= REASON_MAX }">{{ appealReason.length }}/{{ REASON_MAX }}</span>
            </div>
            <input v-model="appealReason" class="av-appeal-input" :maxlength="REASON_MAX" placeholder="请描述你认为封禁不合理的原因" />
          </div>
          <div class="av-appeal-form-group">
            <div class="av-appeal-label-row">
              <label class="av-appeal-label">证据说明 <span class="av-required">*</span></label>
              <span class="av-charcount" :class="{ 'av-charcount--limit': appealEvidence.length >= EVIDENCE_MAX }">{{ appealEvidence.length }}/{{ EVIDENCE_MAX }}</span>
            </div>
            <textarea v-model="appealEvidence" class="av-appeal-input" style="min-height: 80px; resize: vertical;" :maxlength="EVIDENCE_MAX" placeholder="提供相关证据（链接、截图描述等）"></textarea>
          </div>
          <div class="av-appeal-form-group">
            <div class="av-appeal-label-row">
              <label class="av-appeal-label">上传截图</label>
              <span class="av-charcount">最多 {{ MAX_IMAGES }} 张</span>
            </div>
            <div class="av-img-grid">
              <div v-for="img in appealImages" :key="img.id" class="av-img-cell">
                <img :src="img.previewUrl" class="av-img-thumb" alt="截图" @click="lightboxSrc = img.previewUrl" />
                <button type="button" class="av-img-remove" @click.stop="removeImage(img.id)">
                  <i class="fa-solid fa-xmark"></i>
                </button>
              </div>
              <button v-if="appealImages.length < MAX_IMAGES" type="button" class="av-img-add" @click="triggerFileInput">
                <i class="fa-solid fa-cloud-arrow-up av-img-add__icon"></i>
                <span>上传图片</span>
              </button>
            </div>
            <input ref="fileInputRef" type="file" accept="image/*" multiple class="av-file-input" @change="handleFileChange" />
          </div>

          <button class="av-appeal-btn" style="margin-top: 12px;" :disabled="appealLoading" @click="submitAppeal">
            {{ appealLoading ? '提交中...' : '提交申诉' }}
          </button>

        </div>
      </div>
    </div>
  </Transition>

  <div class="av-toast-layer">
    <AppToast :toast="toast" @dismiss="clearToast" />
  </div>

  <Transition name="av-overlay">
    <div v-if="lightboxSrc" class="av-lightbox" @click="lightboxSrc = null">
      <img :src="lightboxSrc" class="av-lightbox__img" alt="截图预览" />
    </div>
  </Transition>
</template>

<style scoped>
.av-toast-layer :deep(.app-toast--fixed) {
  z-index: 1200;
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
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.av-appeal-card__inner {
  padding: 0 36px 32px;
  flex: 1;
  overflow-y: auto;
  min-height: 0;
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
  padding: 24px 36px 16px;
  flex-shrink: 0;
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
  padding-top: 8px;
}
.av-appeal-meta__item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
  background: rgba(254, 242, 242, 0.6);
  border: 1px solid rgba(254, 226, 226, 0.5);
  border-radius: 16px;
  padding: 12px 16px;
  font-size: 13px;
}
.av-appeal-meta__top {
  display: flex;
  align-items: center;
  gap: 6px;
}
.av-appeal-meta__item i {
  color: #ef4444;
  font-size: 13px;
}
.av-appeal-meta__label {
  color: #6b7280;
  white-space: nowrap;
  font-size: 12px;
}
.av-appeal-meta__value {
  display: block;
  width: 100%;
  font-weight: 600;
  color: #111827;
  font-size: 14px;
  word-break: break-all;
  text-align: center;
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
.av-appeal-label-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: 0 4px;
}
.av-appeal-label {
  font-size: 13px;
  font-weight: 500;
  color: #374151;
}
.av-required {
  color: #ef4444;
  font-weight: 600;
}
.av-charcount {
  font-size: 11px;
  color: #374151;
  font-variant-numeric: tabular-nums;
  transition: color 0.2s;
}
.av-charcount--limit {
  color: #ef4444;
  font-weight: 600;
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

.av-img-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}
.av-img-cell {
  position: relative;
  aspect-ratio: 1;
}
.av-img-thumb {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 10px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  display: block;
  cursor: zoom-in;
}
.av-img-remove {
  position: absolute;
  top: -7px;
  right: -7px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  border: none;
  background: #ef4444;
  color: #fff;
  font-size: 10px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.2);
  z-index: 1;
}
.av-img-add {
  aspect-ratio: 1;
  border-radius: 10px;
  border: 2px dashed rgba(0, 0, 0, 0.15);
  background: transparent;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 5px;
  cursor: pointer;
  color: #9ca3af;
  font-size: 11px;
  transition: border-color 0.2s;
}
.av-img-add:hover {
  border-color: rgba(0, 0, 0, 0.3);
}
.av-img-add__icon {
  font-size: 20px;
}
.av-file-input {
  display: none;
}
.av-lightbox {
  position: fixed;
  inset: 0;
  z-index: 1100;
  background: rgba(0, 0, 0, 0.85);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  cursor: zoom-out;
  backdrop-filter: blur(4px);
  -webkit-backdrop-filter: blur(4px);
}
.av-lightbox__img {
  max-width: 100%;
  max-height: 100%;
  border-radius: 12px;
  box-shadow: 0 8px 40px rgba(0, 0, 0, 0.5);
  object-fit: contain;
}

@media (max-width: 400px) {
  .av-appeal-overlay {
    padding: 12px;
  }
  .av-appeal-card {
    border-radius: 24px;
  }
  .av-appeal-header {
    padding: 18px 18px 12px;
  }
  .av-appeal-card__inner {
    padding: 0 18px 20px;
  }
  .av-appeal-header h3 {
    font-size: 15px;
  }
  .av-appeal-meta {
    gap: 8px;
  }
  .av-appeal-meta__item {
    padding: 10px 12px;
    border-radius: 12px;
  }
  .av-appeal-meta__value {
    font-size: 13px;
  }
  .av-appeal-table {
    font-size: 11px;
  }
  .av-appeal-table th {
    padding: 8px 10px;
    font-size: 10px;
  }
  .av-appeal-table td {
    padding: 8px 10px;
  }
  .av-badge {
    padding: 3px 7px;
    font-size: 10px;
  }
  .av-appeal-time {
    font-size: 10px;
  }
  .av-appeal-section-title {
    font-size: 13px;
  }
  .av-appeal-input {
    font-size: 12px;
    padding: 10px 14px;
  }
  .av-appeal-btn {
    font-size: 13px;
    height: 40px;
  }
}

@keyframes av-spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
