<script setup lang="ts">
import type { Report } from '../../../types/api'

defineProps<{
  report: Report
  createdAtText: string
  isActivePenalty: boolean
  hasPendingAppeal: boolean
  hasAnyBan: boolean
}>()

const emit = defineEmits<{
  back: []
  'preview-image': [src: string]
  'open-appeal': []
}>()
</script>

<template>
  <div class="mr-detail-content">
    <div class="mr-detail-back-bar">
      <button class="mr-detail-back-btn" @click="emit('back')">
        <i class="fa-solid fa-arrow-left" />
        返回列表
      </button>
    </div>

    <div class="mr-status-banner mr-status-banner--approved">
      <i class="fa-solid fa-gavel" />
      <div class="mr-status-banner__body">
        <div class="mr-status-banner__title">你收到了平台处罚</div>
        <div class="mr-status-banner__message">
          <template v-if="report.is_admin_ban">
            经平台管理员核查，对你的账号执行了以下处罚。如有异议，可提交申诉。
          </template>
          <template v-else>
            因其他用户的举报，经平台核实后对你的账号执行了以下处罚。如有异议，可提交申诉。
          </template>
        </div>
        <div class="mr-penalty-box">
          <div class="mr-penalty-box__row">
            <i class="fa-solid fa-ban" />
            <span>{{ report.ban_penalty || '已对你的账号执行处罚' }}</span>
          </div>
          <div v-if="report.admin_notes" class="mr-penalty-box__reason">
            处罚理由：{{ report.admin_notes }}
          </div>
        </div>
      </div>
    </div>

    <div class="mr-info-card">
      <h3 class="mr-info-card__title">处罚详情</h3>

      <div v-if="!report.is_admin_ban" class="mr-info-fields">
        <div>
          <div class="mr-info-field__label">举报事由</div>
          <div class="mr-info-field__value">{{ report.reason }}</div>
        </div>
        <div v-if="report.evidence">
          <div class="mr-info-field__label">补充说明</div>
          <div class="mr-info-field__evidence">{{ report.evidence }}</div>
        </div>
        <div v-if="report.images?.length">
          <div class="mr-info-field__label">截图证据</div>
          <div class="mr-evidence-imgs">
            <img
              v-for="(src, index) in report.images"
              :key="index"
              :src="src"
              class="mr-evidence-img"
              alt="证据截图"
              @click="emit('preview-image', src)"
            />
          </div>
        </div>
      </div>

      <div class="mr-info-meta">
        <div class="mr-info-meta__item">
          <span class="mr-info-meta__label">处罚时间</span>
          <span class="mr-info-meta__value">{{ createdAtText }}</span>
        </div>
      </div>
    </div>

    <div v-if="isActivePenalty" class="mr-appeal-bar">
      <button
        v-if="hasPendingAppeal"
        class="mr-appeal-btn mr-appeal-btn--disabled"
        disabled
      >
        <i class="fa-solid fa-hourglass-half" />
        已有待处理的申诉
      </button>
      <button
        v-else-if="hasAnyBan"
        class="mr-appeal-btn"
        @click="emit('open-appeal')"
      >
        <i class="fa-solid fa-paper-plane" />
        对此提交申诉
      </button>
    </div>
  </div>
</template>
