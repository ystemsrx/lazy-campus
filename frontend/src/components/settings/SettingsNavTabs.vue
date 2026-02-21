<script setup lang="ts">
import type { SettingsTab } from '../../composables/settings/types'

const props = defineProps<{
  modelValue: SettingsTab
  indicatorStyle: Record<string, string | number>
  setTabRef: (index: 0 | 1, el: HTMLElement | null) => void
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: SettingsTab): void
}>()
</script>

<template>
  <nav class="sv-nav">
    <div class="sv-nav-indicator" :style="props.indicatorStyle" />

    <button
      :ref="(el) => props.setTabRef(0, el as HTMLElement | null)"
      class="sv-nav-btn"
      :class="{ 'sv-nav-btn--active': props.modelValue === 'profile' }"
      @click="emit('update:modelValue', 'profile')"
    >
      <svg width="18" height="18" viewBox="0 0 20 20" fill="none">
        <path d="M10 10a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm0 2c-4.418 0-8 2.015-8 4.5V18h16v-1.5c0-2.485-3.582-4.5-8-4.5Z" fill="currentColor"/>
      </svg>
      个人资料
    </button>

    <button
      :ref="(el) => props.setTabRef(1, el as HTMLElement | null)"
      class="sv-nav-btn"
      :class="{ 'sv-nav-btn--active': props.modelValue === 'worker' }"
      @click="emit('update:modelValue', 'worker')"
    >
      <svg width="18" height="18" viewBox="0 0 20 20" fill="none">
        <path d="M7 3a2 2 0 0 0-2 2v1H3a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1V7a1 1 0 0 0-1-1h-2V5a2 2 0 0 0-2-2H7Zm0 2h6v1H7V5Zm-4 3h14v8H3V8Z" fill="currentColor"/>
      </svg>
      接单设置
    </button>
  </nav>
</template>

<style scoped src="./settings-nav-tabs.css"></style>
