<script setup lang="ts">
import type { Category } from '../../types/api'
import type { WorkerForm } from '../../composables/settings/types'

const props = defineProps<{
  active: boolean
  workerForm: WorkerForm
  categories: Category[]
}>()

const emit = defineEmits<{
  (e: 'toggle-skill-tag', id: number): void
}>()
</script>

<template>
  <div class="sv-tab-pane" :class="{ 'sv-tab-pane--active': active }">
    <div class="sv-section-header sv-section-header--row">
      <div>
        <h2 class="sv-section-title">接单设置</h2>
      </div>
      <div class="sv-toggle-wrap">
        <span class="sv-toggle-label" :class="{ 'sv-toggle-label--active': props.workerForm.enabled }">
          {{ props.workerForm.enabled ? '正在接单' : '暂停接单' }}
        </span>
        <button
          type="button"
          class="sv-toggle"
          :class="{ 'sv-toggle--on': props.workerForm.enabled }"
          @click="props.workerForm.enabled = !props.workerForm.enabled"
        >
          <span class="sv-toggle-thumb" :class="{ 'sv-toggle-thumb--on': props.workerForm.enabled }" />
        </button>
      </div>
    </div>

    <hr class="sv-divider" />

    <div class="sv-section-body">
      <div class="sv-field">
        <label class="sv-label sv-label--row">
          <span>擅长类别（可多选）<span class="sv-required">*</span></span>
          <span v-if="props.workerForm.skill_tag_ids.length === 0" class="sv-count sv-count--warn">请至少选择一个</span>
          <span v-else class="sv-count" :class="{ 'sv-count--warn': props.workerForm.skill_tag_ids.length >= 5 }">
            {{ props.workerForm.skill_tag_ids.length }}/5
          </span>
        </label>
        <div v-if="props.categories.length" class="sv-chip-group">
          <button
            v-for="cat in props.categories"
            :key="cat.id"
            type="button"
            class="sv-chip"
            :class="{ 'sv-chip--selected': props.workerForm.skill_tag_ids.includes(cat.id) }"
            @click="emit('toggle-skill-tag', cat.id)"
          >{{ cat.name }}</button>
        </div>
        <p v-else class="sv-hint" style="margin-top:4px">管理员暂未设置类别</p>
      </div>

      <div class="sv-field">
        <label class="sv-label sv-label--row">
          <span>个人简介 <span class="sv-required">*</span></span>
          <span class="sv-count" :class="{ 'sv-count--warn': props.workerForm.bio.length >= 150 }">
            {{ props.workerForm.bio.length }}/150
          </span>
        </label>
        <textarea
          v-model="props.workerForm.bio"
          class="sv-textarea"
          placeholder="简单介绍一下您的经验、技能和能提供的服务..."
          maxlength="150"
          rows="4"
        />
      </div>

      <div class="sv-grid-2">
        <div class="sv-field">
          <label class="sv-label">手机号码</label>
          <input v-model.trim="props.workerForm.phone" class="sv-input" type="tel" placeholder="请输入联系电话" />
        </div>
        <div class="sv-field">
          <label class="sv-label">微信号</label>
          <input v-model.trim="props.workerForm.wechat" class="sv-input" type="text" placeholder="请输入微信号" />
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped src="./settings-worker-panel.css"></style>
