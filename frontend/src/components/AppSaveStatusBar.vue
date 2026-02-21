<script setup lang="ts">
withDefaults(
  defineProps<{
    status: 'idle' | 'saving' | 'saved'
    savedText?: string
  }>(),
  {
    savedText: '已保存',
  },
)
</script>

<template>
  <div class="asb-bar">
    <div class="asb-wrap">
      <div class="asb-item" :class="{ 'asb-item--visible': status === 'saving' }">
        <div class="asb-spinner asb-spinner--sm" />
      </div>
      <div class="asb-item asb-item--saved" :class="{ 'asb-item--visible': status === 'saved' }">
        <svg width="17" height="17" viewBox="0 0 18 18" fill="none">
          <path d="M2 9l5 5L16 3" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        <span>{{ savedText }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped src="./app-save-status-bar.css"></style>
