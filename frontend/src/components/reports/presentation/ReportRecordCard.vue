<script setup lang="ts">
import HomeAvatar from '../../home/ui/HomeAvatar.vue'
import type { Report } from '../../../types/api'

defineProps<{
  report: Report
  selected: boolean
  statusLabel: string
  statusIcon: string
  typeLabel: string
  displayName: string
  dateText: string
}>()

const emit = defineEmits<{
  select: []
}>()
</script>

<template>
  <div
    class="mr-card"
    :class="{ 'mr-card--selected': selected }"
    @click="emit('select')"
  >
    <div class="mr-card__top">
      <span class="mr-card__id">单号 #{{ report.id }}</span>
      <span
        class="mr-badge"
        :class="{
          'mr-badge--pending': report.status === 'pending',
          'mr-badge--approved': report.status === 'approved',
          'mr-badge--rejected': report.status === 'rejected',
        }"
      >
        <i :class="statusIcon" />
        {{ statusLabel }}
      </span>
    </div>

    <div class="mr-card__body">
      <HomeAvatar
        class="mr-card__avatar-img"
        :avatar-url="report.type === 'appeal' ? report.reporter_avatar_url : report.reported_user_avatar_url"
        :gender="report.type === 'appeal' ? (report.reporter_gender ?? null) : (report.reported_user_gender ?? null)"
        size="lg"
        alt="被举报人头像"
      />
      <div class="mr-card__info">
        <div class="mr-card__target">{{ typeLabel }}：{{ displayName }}</div>
        <div class="mr-card__reason">{{ report.reason }}</div>
      </div>
    </div>

    <div class="mr-card__footer">
      <span class="mr-card__date">提交于 {{ dateText }}</span>
      <span class="mr-card__action">
        查看详情 <i class="fa-solid fa-chevron-right" />
      </span>
    </div>
  </div>
</template>
