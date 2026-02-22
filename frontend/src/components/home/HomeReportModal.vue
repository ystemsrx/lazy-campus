<script setup lang="ts">
import { ref, watch } from 'vue'
import { createReport, uploadReportImage } from '../../api/moderation'
import { extractError } from '../../utils/error'

const props = defineProps<{
  modelValue: boolean
  taskId: number | null
  reportedUserId: number | null
  reportedUserName?: string
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'success'): void
  (e: 'error', message: string): void
}>()

const REPORT_REASONS = [
  { id: 'fake_task',       label: '虚假任务', desc: '任务描述严重不实，与实际情况不符' },
  { id: 'payment_refuse',  label: '拒绝付款', desc: '任务完成后拒绝确认或拒绝支付报酬' },
  { id: 'fraud',           label: '诈骗欺诈', desc: '以虚假理由骗取劳动成果后失联跑路' },
  { id: 'harassment',      label: '骚扰辱骂', desc: '通过站内消息进行骚扰、侮辱或威胁' },
  { id: 'cancel',          label: '恶意取消', desc: '无故反复取消已接受或已发布的任务' },
  { id: 'illegal_request', label: '违规要求', desc: '要求接单者从事违法违规或危险活动' },
  { id: 'privacy',         label: '信息泄露', desc: '恶意获取或传播对方个人隐私信息' },
  { id: 'fake_review',     label: '虚假评价', desc: '无事实依据地给予恶意差评或刷好评' },
  { id: 'impersonation',   label: '冒充身份', desc: '伪造学生证、职务或其他身份进行欺骗' },
  { id: 'other',           label: '其他问题', desc: '以上未涵盖的其他违规行为' },
]

const MAX_IMAGES = 3

type UploadedImage = {
  id: string
  /** 本地预览用的 Object URL（不上传到服务端） */
  previewUrl: string
  /** Canvas 压缩后的 WebP Blob，提交时上传 */
  blob: Blob
}

const selectedReason = ref<string>(REPORT_REASONS[0].id)
const evidence = ref('')
const images = ref<UploadedImage[]>([])
const fileInputRef = ref<HTMLInputElement | null>(null)
const isSubmitting = ref(false)
const isSuccess = ref(false)
const lightboxSrc = ref<string | null>(null)

watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      selectedReason.value = REPORT_REASONS[0].id
      evidence.value = ''
      // 释放旧的 Object URL，防止内存泄漏
      images.value.forEach((img) => URL.revokeObjectURL(img.previewUrl))
      images.value = []
      isSubmitting.value = false
      isSuccess.value = false
      lightboxSrc.value = null
    }
  },
)

function close() {
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

  const remaining = MAX_IMAGES - images.value.length
  const toProcess = files.slice(0, remaining)

  for (const file of toProcess) {
    try {
      const blob = await compressToWebPBlob(file)
      const previewUrl = URL.createObjectURL(blob)
      images.value.push({ id: Math.random().toString(36).slice(2), previewUrl, blob })
    } catch {
      // 单张失败不影响其他张
    }
  }
}

function removeImage(id: string) {
  const img = images.value.find((i) => i.id === id)
  if (img) URL.revokeObjectURL(img.previewUrl)
  images.value = images.value.filter((i) => i.id !== id)
}

async function submit() {
  if (!props.taskId || !props.reportedUserId || isSubmitting.value) return
  isSubmitting.value = true
  try {
    // 1. 并发上传所有图片，获取服务端 URL
    const imageUrls = await Promise.all(
      images.value.map((img) => uploadReportImage(img.blob)),
    )

    // 2. 提交举报
    const reasonObj = REPORT_REASONS.find((r) => r.id === selectedReason.value)
    const reasonText = reasonObj ? reasonObj.label : selectedReason.value
    await createReport({
      task_id: props.taskId,
      reported_user_id: props.reportedUserId,
      reason: reasonText,
      evidence: evidence.value.trim(),
      images: imageUrls,
    })
    isSuccess.value = true
    emit('success')
    setTimeout(() => close(), 2200)
  } catch (error: unknown) {
    emit('error', extractError(error, '提交举报失败'))
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <Teleport to="body">
    <Transition name="hrm-overlay">
      <div v-if="modelValue" class="hrm-overlay" @click.self="close">
        <div class="hrm-modal" role="dialog" aria-modal="true">

          <!-- Success State -->
          <div v-if="isSuccess" class="hrm-success">
            <div class="hrm-success__icon">
              <i class="fa-solid fa-circle-check" />
            </div>
            <h3 class="hrm-success__title">举报已提交</h3>
            <p class="hrm-success__desc">
              感谢您的反馈，平台将尽快核实处理。<br />
              共同维护健康的校园环境。
            </p>
          </div>

          <!-- Form State -->
          <template v-else>
            <!-- Header -->
            <div class="hrm-header">
              <h2 class="hrm-header__title">
                <i class="fa-solid fa-flag hrm-flag-icon" />
                提交举报
              </h2>
              <button class="hrm-close-btn" aria-label="关闭" @click="close">
                <i class="fa-solid fa-xmark" />
              </button>
            </div>

            <!-- Body -->
            <div class="hrm-body">
              <!-- Target info -->
              <div v-if="reportedUserName" class="hrm-target">
                <span class="hrm-target__label">举报对象</span>
                <span class="hrm-target__name">{{ reportedUserName }}</span>
              </div>

              <!-- Reason tags -->
              <div class="hrm-section">
                <label class="hrm-label">举报原因</label>
                <div class="hrm-reasons">
                  <button
                    v-for="r in REPORT_REASONS"
                    :key="r.id"
                    type="button"
                    class="hrm-reason-tag"
                    :class="{ 'hrm-reason-tag--active': selectedReason === r.id }"
                    :title="r.desc"
                    @click="selectedReason = r.id"
                  >
                    {{ r.label }}
                  </button>
                </div>
                <p v-if="selectedReason" class="hrm-reason-desc">
                  {{ REPORT_REASONS.find((r) => r.id === selectedReason)?.desc }}
                </p>
              </div>

              <!-- Evidence -->
              <div class="hrm-section">
                <label class="hrm-label">
                  补充说明
                  <span class="hrm-label__optional">选填</span>
                </label>
                <textarea
                  v-model="evidence"
                  class="hrm-textarea"
                  maxlength="500"
                  placeholder="可补充具体情况、聊天截图描述、发生时间等，帮助我们更快核实..."
                />
                <span class="hrm-char-count">{{ evidence.length }}/500</span>
              </div>

              <!-- Image upload -->
              <div class="hrm-section">
                <label class="hrm-label">
                  上传截图
                  <span class="hrm-label__optional">最多 {{ MAX_IMAGES }} 张</span>
                </label>
                <div class="hrm-img-grid">
                  <div
                    v-for="img in images"
                    :key="img.id"
                    class="hrm-img-cell"
                  >
                    <img
                      :src="img.previewUrl"
                      class="hrm-img-thumb"
                      alt="截图"
                      @click="lightboxSrc = img.previewUrl"
                    />
                    <button
                      type="button"
                      class="hrm-img-remove"
                      aria-label="删除"
                      @click.stop="removeImage(img.id)"
                    >
                      <i class="fa-solid fa-xmark" />
                    </button>
                  </div>
                  <button
                    v-if="images.length < MAX_IMAGES"
                    type="button"
                    class="hrm-img-add"
                    @click="triggerFileInput"
                  >
                    <i class="fa-solid fa-cloud-arrow-up hrm-img-add__icon" />
                    <span>上传图片</span>
                  </button>
                </div>
                <input
                  ref="fileInputRef"
                  type="file"
                  accept="image/*"
                  multiple
                  class="hrm-file-input"
                  @change="handleFileChange"
                />
                <div class="hrm-notice">
                  <i class="fa-solid fa-circle-info hrm-notice__icon" />
                  <span>支持 JPG、PNG 等格式，截图包含完整违规场景将帮助我们更快处理。</span>
                </div>
              </div>

              <!-- Notice -->
              <div class="hrm-notice">
                <i class="fa-solid fa-circle-info hrm-notice__icon" />
                <span>恶意举报将影响您的账号信誉，请如实填写。</span>
              </div>
            </div>

            <!-- Footer -->
            <div class="hrm-footer">
              <button class="hrm-btn hrm-btn--cancel" @click="close">取消</button>
              <button
                class="hrm-btn hrm-btn--submit"
                :disabled="isSubmitting"
                @click="submit"
              >
                <template v-if="isSubmitting">
                  <i class="fa-solid fa-circle-notch fa-spin" />
                  提交中…
                </template>
                <template v-else>确认举报</template>
              </button>
            </div>
          </template>

        </div>
      </div>
    </Transition>

    <!-- Lightbox -->
    <Transition name="hrm-overlay">
      <div v-if="lightboxSrc" class="hrm-lightbox" @click="lightboxSrc = null">
        <img :src="lightboxSrc" class="hrm-lightbox__img" alt="截图预览" />
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
/* ── Overlay ── */
.hrm-overlay {
  position: fixed;
  inset: 0;
  z-index: 300;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  background: rgba(15, 23, 42, 0.45);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
}

/* ── Modal card ── */
.hrm-modal {
  position: relative;
  width: 100%;
  max-width: 520px;
  background: var(--c-surface);
  border-radius: 24px;
  box-shadow: 0 24px 64px rgba(0, 0, 0, 0.18), 0 4px 16px rgba(0, 0, 0, 0.08);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  max-height: calc(100dvh - 48px);
}

/* ── Header ── */
.hrm-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid var(--c-border-light);
  flex-shrink: 0;
}

.hrm-header__title {
  margin: 0;
  font-size: var(--text-base);
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
}

.hrm-flag-icon {
  color: #ef4444;
  font-size: 16px;
}

.hrm-close-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: none;
  background: transparent;
  border-radius: 50%;
  color: var(--c-text-muted);
  font-size: 16px;
  cursor: pointer;
  transition: background var(--dur-fast) var(--ease), color var(--dur-fast) var(--ease);
  flex-shrink: 0;
}

.hrm-close-btn:hover {
  background: var(--c-border-light);
  color: var(--c-text);
}

/* ── Body ── */
.hrm-body {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* ── Target ── */
.hrm-target {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  background: var(--c-border-light);
  border-radius: 10px;
  font-size: var(--text-sm);
}

.hrm-target__label {
  color: var(--c-text-muted);
  flex-shrink: 0;
}

.hrm-target__name {
  font-weight: 500;
  color: var(--c-text);
}

/* ── Section ── */
.hrm-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.hrm-label {
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--c-text);
  display: flex;
  align-items: center;
  gap: 6px;
}

.hrm-label__optional {
  font-size: var(--text-xs);
  font-weight: 400;
  color: var(--c-text-muted);
}

/* ── Reason tags ── */
.hrm-reasons {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.hrm-reason-tag {
  padding: 6px 14px;
  border-radius: 999px;
  border: 1px solid var(--c-border);
  background: var(--c-surface);
  color: var(--c-text-secondary);
  font-size: var(--text-sm);
  cursor: pointer;
  transition: all var(--dur-fast) var(--ease);
  line-height: 1.4;
}


.hrm-reason-tag--active {
  background: var(--c-text);
  border-color: var(--c-text);
  color: var(--c-surface);
}

.hrm-reason-desc {
  margin: 0;
  font-size: var(--text-xs);
  color: var(--c-text-muted);
  line-height: 1.6;
  padding: 0 2px;
}

/* ── Textarea ── */
.hrm-textarea {
  width: 100%;
  height: 100px;
  padding: 12px 14px;
  background: var(--c-border-light);
  border: 1px solid var(--c-border);
  border-radius: 12px;
  font-size: var(--text-sm);
  color: var(--c-text);
  resize: none;
  font-family: inherit;
  line-height: 1.6;
  transition: border-color var(--dur-fast) var(--ease), box-shadow var(--dur-fast) var(--ease);
  box-sizing: border-box;
}

.hrm-textarea::placeholder {
  color: var(--c-text-muted);
}

.hrm-textarea:focus {
  outline: none;
  border-color: var(--c-text-muted);
  box-shadow: 0 0 0 3px rgba(0, 0, 0, 0.06);
}

.hrm-char-count {
  font-size: var(--text-xs);
  color: var(--c-text-muted);
  text-align: right;
  margin-top: -6px;
}

/* ── Notice ── */
.hrm-notice {
  display: flex;
  align-items: flex-start;
  gap: 7px;
  font-size: var(--text-xs);
  color: var(--c-text-muted);
  line-height: 1.6;
}

.hrm-notice__icon {
  flex-shrink: 0;
  margin-top: 2px;
  font-size: 12px;
  color: var(--c-text-muted);
}

/* ── Footer ── */
.hrm-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  padding: 16px 24px;
  border-top: 1px solid var(--c-border-light);
  background: var(--c-border-light);
  flex-shrink: 0;
}

.hrm-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 10px 20px;
  border-radius: 12px;
  font-size: var(--text-sm);
  font-weight: 500;
  cursor: pointer;
  border: none;
  transition: all var(--dur-fast) var(--ease);
  line-height: 1;
}

.hrm-btn--cancel {
  background: transparent;
  color: var(--c-text-secondary);
}

.hrm-btn--cancel:hover {
  background: var(--c-border);
}

.hrm-btn--submit {
  background: var(--c-text);
  color: var(--c-surface);
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.12);
}

.hrm-btn--submit:hover:not(:disabled) {
  opacity: 0.88;
}

.hrm-btn--submit:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

/* ── Success State ── */
.hrm-success {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 52px 36px;
  text-align: center;
  gap: 14px;
}

.hrm-success__icon {
  width: 64px;
  height: 64px;
  background: #f0fdf4;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  color: #22c55e;
  margin-bottom: 4px;
}

.hrm-success__title {
  margin: 0;
  font-size: var(--text-xl);
  font-weight: 600;
  color: var(--c-text);
}

.hrm-success__desc {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--c-text-muted);
  line-height: 1.8;
}

/* ── Transitions ── */
.hrm-overlay-enter-active {
  transition: opacity 0.25s ease;
}

.hrm-overlay-leave-active {
  transition: opacity 0.2s ease;
}

.hrm-overlay-enter-from,
.hrm-overlay-leave-to {
  opacity: 0;
}

.hrm-overlay-enter-active .hrm-modal {
  transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.25s ease;
}

.hrm-overlay-leave-active .hrm-modal {
  transition: transform 0.2s ease, opacity 0.2s ease;
}

.hrm-overlay-enter-from .hrm-modal {
  transform: translateY(24px) scale(0.96);
  opacity: 0;
}

.hrm-overlay-leave-to .hrm-modal {
  transform: translateY(12px) scale(0.97);
  opacity: 0;
}

/* ── Image upload ── */
.hrm-img-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}

.hrm-img-cell {
  position: relative;
  aspect-ratio: 1;
}

.hrm-img-thumb {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 10px;
  border: 1px solid var(--c-border);
  background: var(--c-border-light);
  display: block;
  cursor: zoom-in;
}

.hrm-img-remove {
  position: absolute;
  top: -8px;
  right: -8px;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  border: none;
  background: #ef4444;
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 1px 4px rgba(0,0,0,0.2);
  z-index: 1;
}

.hrm-img-add {
  aspect-ratio: 1;
  border-radius: 10px;
  border: 2px dashed var(--c-border);
  background: transparent;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  cursor: pointer;
  color: var(--c-text-muted);
  font-size: var(--text-xs);
  transition: border-color var(--dur-fast) var(--ease);
}

.hrm-img-add:hover {
  border-color: var(--c-text-muted);
}

.hrm-img-add__icon {
  font-size: 22px;
}

.hrm-file-input {
  display: none;
}

/* ── Lightbox ── */
.hrm-lightbox {
  position: fixed;
  inset: 0;
  z-index: 500;
  background: rgba(0, 0, 0, 0.85);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  cursor: zoom-out;
  backdrop-filter: blur(4px);
}

.hrm-lightbox__img {
  max-width: 100%;
  max-height: 100%;
  border-radius: 12px;
  box-shadow: 0 8px 40px rgba(0,0,0,0.5);
  object-fit: contain;
}

/* ── Mobile ── */
@media (max-width: 600px) {
  .hrm-overlay {
    align-items: flex-end;
    padding: 0;
  }

  .hrm-modal {
    max-width: 100%;
    border-radius: 20px 20px 0 0;
    max-height: 92dvh;
  }

  .hrm-overlay-enter-from .hrm-modal {
    transform: translateY(100%);
    opacity: 1;
  }

  .hrm-overlay-leave-to .hrm-modal {
    transform: translateY(100%);
    opacity: 1;
  }
}
</style>
