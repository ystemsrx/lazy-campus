<script setup lang="ts">
import type { Report } from '../../../types/api'

defineProps<{
  report: Report
  selected: boolean
  activePenalty: boolean
  dateText: string
}>()

const emit = defineEmits<{
  select: []
}>()
</script>

<template>
  <div
    class="mr-card mr-card--penalty"
    :class="{ 'mr-card--selected': selected }"
    @click="emit('select')"
  >
    <div class="mr-card__top">
      <span class="mr-card__id">处罚 #{{ report.id }}</span>
      <span
        class="mr-badge"
        :class="activePenalty ? 'mr-badge--active-penalty' : 'mr-badge--approved'"
      >
        <i :class="activePenalty ? 'fa-solid fa-circle-dot' : 'fa-solid fa-gavel'" />
        {{ activePenalty ? '处罚中' : '已结束' }}
      </span>
    </div>
    <div class="mr-card__body">
      <div class="mr-card__penalty-icon">
        <i class="fa-solid fa-triangle-exclamation" />
      </div>
      <div class="mr-card__info">
        <div class="mr-card__target">
          {{ report.ban_penalty || '账号限制' }}
        </div>
        <div class="mr-card__reason">举报事由：{{ report.reason }}</div>
      </div>
    </div>
    <div class="mr-card__footer">
      <span class="mr-card__date">{{ dateText }}</span>
      <span class="mr-card__action">
        查看详情 <i class="fa-solid fa-chevron-right" />
      </span>
    </div>
  </div>
</template>
