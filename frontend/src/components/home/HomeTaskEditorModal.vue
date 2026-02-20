<script setup lang="ts">
import { computed } from 'vue'
import AppDropdown from '../AppDropdown.vue'
import HomeModal from './ui/HomeModal.vue'
import type { Category } from '../../types/api'

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
}

const props = defineProps<{
  modelValue: boolean
  mode: 'create' | 'edit'
  form: TaskEditorForm
  categories: Category[]
  nowLocal: () => string
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'submit'): void
}>()

const title = computed(() => (props.mode === 'create' ? '发布新委托' : '编辑委托'))
const hint = computed(() =>
  props.mode === 'create'
    ? '填写委托信息后发布，其他用户即可在任务大厅看到并接取。'
    : '任务被接取前可随时修改所有信息。',
)
const submitText = computed(() => (props.mode === 'create' ? '发布委托' : '保存修改'))

const categoryOptions = computed(() => [
  { value: null, label: '选择类目' },
  ...props.categories.map((c) => ({ value: c.id, label: c.name })),
])
</script>

<template>
  <HomeModal :model-value="props.modelValue" :title="title" @update:model-value="emit('update:modelValue', $event)">
    <p class="hv-hint hv-hint--spaced">{{ hint }}</p>
    <form class="hv-form" @submit.prevent="emit('submit')">
      <div class="form-group">
        <label class="form-label">标题</label>
        <input v-model="form.title" class="form-input" placeholder="简要描述你需要完成的事项" required />
      </div>

      <div class="form-group">
        <label class="form-label">详细描述</label>
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
          <label class="form-label">价格 (¥)</label>
          <input v-model.number="form.price" class="form-input" type="number" min="1" placeholder="报酬金额" />
        </div>
      </div>

      <div class="form-row">
        <div class="form-group">
          <label class="form-label">截止时间</label>
          <input v-model="form.deadline" class="form-input" type="datetime-local" :min="nowLocal()" />
        </div>
        <div class="form-group">
          <label class="form-label">所属类目</label>
          <AppDropdown v-model="form.category_id" :options="categoryOptions" placeholder="选择类目" />
        </div>
      </div>

      <div class="form-row">
        <div class="form-group">
          <label class="form-label">联系方式可见性</label>
          <AppDropdown
            v-model="form.contact_visibility"
            :options="[
              { value: 'after_accept', label: '接取后可见联系方式' },
              { value: 'internal_only', label: '仅站内沟通' },
            ]"
          />
        </div>
        <div class="form-group">
          <label class="form-label">联系方式</label>
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
        <AppDropdown
          v-model="form.required_gender"
          :options="[
            { value: null, label: '不限性别' },
            { value: 'male', label: '仅限男生' },
            { value: 'female', label: '仅限女生' },
          ]"
          placeholder="不限性别"
        />
      </div>

      <button class="btn btn-primary btn-block hv-submit-btn" type="submit">{{ submitText }}</button>
    </form>
  </HomeModal>
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
}

.hv-description-textarea {
  min-height: 80px;
}
</style>
