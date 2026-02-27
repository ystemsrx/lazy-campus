<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import AppDropdown from '../AppDropdown.vue'
import AppCategoryPicker from '../AppCategoryPicker.vue'
import AppDateTimePicker from '../AppDateTimePicker.vue'
import HomeModal from './ui/HomeModal.vue'
import type { Category } from '../../types/api'
import { TASK_ICON_OPTIONS } from '../../utils/taskIcons'

type TaskEditorForm = {
  title: string
  description: string
  deadline: string
  location: string
  price: number
  category_id: number | null
  contact_visibility: 'after_accept' | 'internal_only'
  contact_info: string
  required_gender: 'male' | 'female' | null
  icon: string
  attachments: string[]
}

const props = defineProps<{
  modelValue: boolean
  mode: 'create' | 'edit'
  form: TaskEditorForm
  categories: Category[]
  nowLocal: () => string
  showAgentAction: boolean
  agentSubmitting?: boolean
  uploadTaskImage: (file: File) => Promise<string>
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'submit'): void
  (e: 'submit-agent'): void
}>()

const title = computed(() => (props.mode === 'create' ? '发布新委托' : '编辑委托'))
const hint = computed(() =>
  props.mode === 'create'
    ? '填写委托信息后发布，其他用户即可在任务大厅看到并接取。'
    : '任务被接取前可随时修改所有信息。',
)
const submitText = computed(() => (props.mode === 'create' ? '发布委托' : '保存修改'))

const categoryOptions = computed(() =>
  props.categories.map((c) => ({ value: c.id, label: c.name })),
)

const GENDER_OPTIONS = [
  { value: null,     label: '不限',   color: '#64748b' },
  { value: 'male',   label: '仅男生', color: '#3b82f6' },
  { value: 'female', label: '仅女生', color: '#ec4899' },
] as const

const genderTrackRef = ref<HTMLElement | null>(null)
const fileInputRef = ref<HTMLInputElement | null>(null)
const uploadingImages = ref(false)
const lightboxSrc = ref<string | null>(null)
const MAX_ATTACHMENTS = 3

const activeGenderIndex = computed(() => {
  const idx = GENDER_OPTIONS.findIndex(o => o.value === props.form.required_gender)
  return idx === -1 ? 0 : idx
})

const canAddAttachments = computed(() => props.form.attachments.length < MAX_ATTACHMENTS)

function triggerAttachmentUpload() {
  if (uploadingImages.value || !canAddAttachments.value) return
  fileInputRef.value?.click()
}

function removeAttachment(index: number) {
  props.form.attachments.splice(index, 1)
}

async function handleAttachmentChange(event: Event) {
  const input = event.target as HTMLInputElement
  if (!input.files) return

  const files = Array.from(input.files)
  input.value = ''

  const remaining = MAX_ATTACHMENTS - props.form.attachments.length
  if (remaining <= 0) return
  const toUpload = files.slice(0, remaining)
  if (!toUpload.length) return

  uploadingImages.value = true
  try {
    for (const file of toUpload) {
      try {
        const url = await props.uploadTaskImage(file)
        if (props.form.attachments.length >= MAX_ATTACHMENTS) break
        if (!props.form.attachments.includes(url)) {
          props.form.attachments.push(url)
        }
      } catch {
        // 单张失败不影响其余图片上传
      }
    }
  } finally {
    uploadingImages.value = false
  }
}

watch(
  () => props.modelValue,
  (open) => {
    if (!open) lightboxSrc.value = null
  },
)
</script>

<template>
  <HomeModal :model-value="props.modelValue" :title="title" @update:model-value="emit('update:modelValue', $event)">
    <p class="hv-hint hv-hint--spaced">{{ hint }}</p>
    <form class="hv-form" @submit.prevent="emit('submit')">
      <div class="form-group">
        <label class="form-label">标题<span class="required-star">*</span></label>
        <input v-model="form.title" class="form-input" placeholder="简要描述你需要完成的事项" required />
      </div>

      <div class="form-group">
        <label class="form-label">任务图标</label>
        <div class="hv-icon-picker-wrap">
          <div class="hv-icon-picker">
            <button
              v-for="opt in TASK_ICON_OPTIONS"
              :key="opt.name"
              type="button"
              class="hv-icon-picker__item"
              :class="{ 'hv-icon-picker__item--active': form.icon === opt.name }"
              @click="form.icon = opt.name"
              :title="opt.label"
            >
              <div class="hv-icon-picker__circle" :style="{ backgroundColor: opt.bg, color: opt.color }">
                <component :is="opt.component" :size="20" />
              </div>
            </button>
          </div>
        </div>
      </div>

      <div class="form-group">
        <label class="form-label">详细描述<span class="required-star">*</span></label>
        <textarea
          v-model="form.description"
          class="form-textarea hv-description-textarea"
          placeholder="详细说明需求、要求和注意事项"
        ></textarea>
      </div>

      <div class="form-row">
        <div class="form-group">
          <label class="form-label">地点</label>
          <input v-model="form.location" class="form-input" placeholder="任务执行地点（选填）" />
        </div>
        <div class="form-group">
          <label class="form-label">价格 (¥)<span class="required-star">*</span></label>
          <input v-model.number="form.price" class="form-input" type="number" min="1" placeholder="报酬金额" />
        </div>
      </div>

      <div class="form-row hv-row-fixed">
        <div class="form-group">
          <label class="form-label">截止时间</label>
          <AppDateTimePicker v-model="form.deadline" :min="nowLocal()" placeholder="选择截止时间" />
        </div>
        <div class="form-group">
          <label class="form-label">所属类目<span class="required-star">*</span></label>
          <AppCategoryPicker v-model="form.category_id" :options="categoryOptions" placeholder="选择类目" />
        </div>
      </div>

      <div class="form-row hv-row-fixed">
        <div class="form-group">
          <label class="form-label">联系方式可见性<span class="required-star">*</span></label>
          <AppDropdown
            v-model="form.contact_visibility"
            :options="[
              { value: 'after_accept', label: '接取后可见联系方式' },
              { value: 'internal_only', label: '仅站内沟通' },
            ]"
          />
        </div>
        <div class="form-group">
          <label class="form-label">联系方式<span v-if="form.contact_visibility === 'after_accept'" class="required-star">*</span></label>
          <input
            v-model="form.contact_info"
            class="form-input"
            :disabled="form.contact_visibility === 'internal_only'"
            placeholder="微信/手机号等（选填）"
          />
        </div>
      </div>

      <div class="form-group">
        <label class="form-label">接单者性别要求</label>
        <div ref="genderTrackRef" class="gender-toggle">
          <div
            class="gender-toggle__slider"
            :style="{
              left: `calc(4px + ${activeGenderIndex} * (100% - 8px) / 3)`,
              width: 'calc((100% - 8px) / 3)',
            }"
          />
          <button
            v-for="(opt, i) in GENDER_OPTIONS"
            :key="String(opt.value)"
            type="button"
            class="gender-toggle__option"
            :class="{ 'gender-toggle__option--active': activeGenderIndex === i }"
            :style="activeGenderIndex === i ? { color: opt.color } : {}"
            @click="form.required_gender = opt.value as 'male' | 'female' | null"
          >
            {{ opt.label }}
          </button>
        </div>
      </div>

      <div class="form-group">
        <label class="form-label">附件图片<span class="hv-upload-hint">最多 {{ MAX_ATTACHMENTS }} 张</span></label>
        <div class="hv-attachment-grid">
          <div v-for="(url, idx) in form.attachments" :key="`${url}-${idx}`" class="hv-attachment-cell">
            <img :src="url" class="hv-attachment-thumb" alt="附件图片" @click="lightboxSrc = url" />
            <button type="button" class="hv-attachment-remove" aria-label="删除图片" @click.stop="removeAttachment(idx)">
              <i class="fa-solid fa-xmark"></i>
            </button>
          </div>
          <button
            v-if="canAddAttachments"
            type="button"
            class="hv-attachment-add"
            :disabled="uploadingImages"
            @click="triggerAttachmentUpload"
          >
            <i :class="uploadingImages ? 'fa-solid fa-circle-notch fa-spin' : 'fa-solid fa-image'"></i>
            <span>{{ uploadingImages ? '上传中…' : '上传图片' }}</span>
          </button>
        </div>
        <input
          ref="fileInputRef"
          type="file"
          accept="image/*"
          multiple
          class="hv-file-input"
          @change="handleAttachmentChange"
        />
      </div>

      <div class="hv-submit-row">
        <button
          v-if="props.mode === 'create' && props.showAgentAction"
          class="btn btn-outline hv-ai-btn"
          type="button"
          :disabled="props.agentSubmitting || uploadingImages"
          @click="emit('submit-agent')"
        >
          <i class="fa-solid fa-robot"></i>
          AI 代理
        </button>
        <button class="btn btn-primary hv-submit-btn" type="submit" :disabled="uploadingImages">{{ submitText }}</button>
      </div>
    </form>
  </HomeModal>

  <Transition name="drawer-lightbox">
    <div v-if="lightboxSrc" class="hv-image-lightbox" @click="lightboxSrc = null">
      <img :src="lightboxSrc" class="hv-image-lightbox__img" alt="附件预览" />
    </div>
  </Transition>
</template>

<style scoped>
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

.hv-submit-btn {
  margin-top: 4px;
  flex: 1;
}

.hv-submit-row {
  margin-top: 4px;
  display: flex;
  gap: 8px;
}

.hv-ai-btn {
  min-width: 120px;
}

.hv-description-textarea {
  min-height: 80px;
}

.hv-upload-hint {
  margin-left: 6px;
  color: var(--c-text-muted);
  font-size: var(--text-xs);
  font-weight: 400;
}

.required-star {
  color: #ef4444;
  margin-left: 2px;
  font-weight: 600;
}

.hv-row-fixed {
  grid-template-columns: 1fr 1fr !important;
}

.hv-row-fixed > .form-group {
  min-width: 0;
}

@media (max-width: 768px) {
  .hv-row-fixed {
    grid-template-columns: 1fr 1fr !important;
  }
}

.hv-icon-picker-wrap {
  max-height: 166px;
  overflow-y: auto;
  padding-right: 2px;
}

.hv-icon-picker-wrap::-webkit-scrollbar {
  width: 4px;
}

.hv-icon-picker-wrap::-webkit-scrollbar-thumb {
  background: var(--c-border);
  border-radius: 2px;
}

.hv-icon-picker {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.hv-icon-picker__item {
  border: 2px solid transparent;
  border-radius: 14px;
  padding: 3px;
  background: none;
  cursor: pointer;
  transition: all 0.2s;
}

@media (hover: hover) {
  .hv-icon-picker__item:not(.hv-icon-picker__item--active):hover {
    border-color: var(--c-border);
  }
}

.hv-icon-picker__item--active {
  border-color: var(--c-accent);
}

.hv-icon-picker__circle {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.hv-attachment-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.hv-attachment-cell {
  position: relative;
  aspect-ratio: 1;
}

.hv-attachment-thumb {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 10px;
  border: 1px solid var(--c-border);
  background: var(--c-border-light);
  cursor: zoom-in;
}

.hv-attachment-remove {
  position: absolute;
  top: -8px;
  right: -8px;
  width: 22px;
  height: 22px;
  border-radius: 999px;
  border: none;
  background: #ef4444;
  color: #fff;
  font-size: 11px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.2);
}

.hv-attachment-add {
  aspect-ratio: 1;
  border-radius: 10px;
  border: 2px dashed var(--c-border);
  background: transparent;
  color: var(--c-text-muted);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  cursor: pointer;
  font-size: var(--text-xs);
}

.hv-attachment-add:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.hv-file-input {
  display: none;
}

/* ── Gender Toggle ── */
.gender-toggle {
  position: relative;
  display: flex;
  background: #f1f5f9;
  border-radius: 999px;
  padding: 4px;
  gap: 0;
}

.gender-toggle__slider {
  position: absolute;
  top: 4px;
  bottom: 4px;
  border-radius: 999px;
  background: #ffffff;
  transition: left 0.32s cubic-bezier(0.16, 1, 0.3, 1);
  box-shadow: 0 1px 6px rgba(0, 0, 0, 0.1);
  pointer-events: none;
  z-index: 0;
}

.gender-toggle__option {
  flex: 1;
  position: relative;
  z-index: 1;
  padding: 8px 0;
  border: none;
  background: transparent;
  color: var(--c-text-muted);
  font-size: var(--text-sm);
  font-family: var(--font-sans);
  font-weight: 500;
  cursor: pointer;
  transition: color 0.25s ease;
  text-align: center;
  user-select: none;
  border-radius: 999px;
}

.gender-toggle__option--active {
  font-weight: 600;
}

.hv-image-lightbox {
  position: fixed;
  inset: 0;
  z-index: 200;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  cursor: zoom-out;
}

.hv-image-lightbox__img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  border-radius: 12px;
  box-shadow: 0 8px 40px rgba(0, 0, 0, 0.45);
}

.drawer-lightbox-enter-active,
.drawer-lightbox-leave-active {
  transition: opacity 0.2s ease;
}

.drawer-lightbox-enter-from,
.drawer-lightbox-leave-to {
  opacity: 0;
}
</style>
