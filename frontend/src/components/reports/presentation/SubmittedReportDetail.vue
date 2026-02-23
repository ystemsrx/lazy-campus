<script setup lang="ts">
import HomeAvatar from '../../home/ui/HomeAvatar.vue'
import type { Report } from '../../../types/api'

defineProps<{
  report: Report
  displayName: string
  typeLabel: string
  createdAtText: string
}>()

const emit = defineEmits<{
  back: []
  'preview-image': [src: string]
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

    <div
      v-if="report.status === 'pending'"
      class="mr-status-banner mr-status-banner--pending"
    >
      <i class="fa-solid fa-clock" />
      <div>
        <div class="mr-status-banner__title">平台正在核实中</div>
        <div class="mr-status-banner__message">
          我们已收到您的反馈，正在调查处理。一般情况下，处理结果将在
          24-48 小时内反馈给您，请耐心等待。
        </div>
      </div>
    </div>

    <div
      v-else-if="report.status === 'approved'"
      class="mr-status-banner mr-status-banner--approved"
    >
      <i class="fa-solid fa-circle-check" />
      <div class="mr-status-banner__body">
        <div class="mr-status-banner__title">
          {{ report.type === 'report' ? '举报已通过' : '申诉已通过' }}
        </div>
        <div class="mr-status-banner__message">
          <template v-if="report.type === 'report'">
            经核实，举报成立，平台已对违规方采取相应措施。
          </template>
          <template v-else>
            您的申诉已被管理员审核通过，账号封禁已解除，您现在可以正常使用平台所有功能。
          </template>
        </div>
        <div v-if="report.type === 'report'" class="mr-penalty-box">
          <div class="mr-penalty-box__row">
            <i class="fa-solid fa-gavel" />
            <span>{{ report.ban_penalty || '已对违规方执行处罚' }}</span>
          </div>
          <div v-if="report.admin_notes" class="mr-penalty-box__reason">
            处罚理由：{{ report.admin_notes }}
          </div>
        </div>
      </div>
    </div>

    <div
      v-else-if="report.status === 'rejected'"
      class="mr-status-banner mr-status-banner--rejected"
    >
      <i class="fa-solid fa-circle-xmark" />
      <div>
        <div class="mr-status-banner__title">
          {{ report.type === 'report' ? '举报未通过' : '申诉未通过' }}
        </div>
        <div class="mr-status-banner__message">
          <template v-if="report.type === 'report'">
            抱歉，根据您提供的证据及平台核实，暂未发现明显违规行为。建议补充更多有效证据后重新提交。
          </template>
          <template v-else>
            抱歉，经管理员审核，您的申诉暂未获得通过。如有异议，请确认材料后重新提交申诉。
          </template>
        </div>
      </div>
    </div>

    <div
      v-if="report.status === 'rejected' && report.admin_notes"
      class="mr-admin-notes"
    >
      <div class="mr-admin-notes__header">
        <i class="fa-solid fa-comment-dots" />
        <span>管理员说明</span>
      </div>
      <div class="mr-admin-notes__body">{{ report.admin_notes }}</div>
    </div>

    <div class="mr-info-card">
      <h3 class="mr-info-card__title">
        {{ report.type === 'report' ? '我提交的举报' : '我提交的申诉' }}
      </h3>

      <div class="mr-info-target">
        <HomeAvatar
          class="mr-info-target__avatar-img"
          :avatar-url="report.type === 'appeal' ? report.reporter_avatar_url : report.reported_user_avatar_url"
          :gender="report.type === 'appeal' ? (report.reporter_gender ?? null) : (report.reported_user_gender ?? null)"
          size="lg"
          :alt="report.type === 'report' ? '被举报人头像' : '申诉人头像'"
        />
        <div>
          <div class="mr-info-target__label">
            {{ report.type === 'report' ? '被举报人' : '申诉账号' }}
          </div>
          <div class="mr-info-target__name">{{ displayName }}</div>
        </div>
      </div>

      <div class="mr-info-fields">
        <div>
          <div class="mr-info-field__label">
            {{ report.type === 'report' ? '举报事由' : '申诉事由' }}
          </div>
          <div class="mr-info-field__value">{{ report.reason }}</div>
        </div>

        <div v-if="report.evidence">
          <div class="mr-info-field__label">
            {{ report.type === 'report' ? '补充说明' : '申诉材料 / 说明' }}
          </div>
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
          <span class="mr-info-meta__label">类型</span>
          <span class="mr-badge" :class="report.type === 'report' ? 'mr-badge--report' : 'mr-badge--appeal'">
            {{ typeLabel }}
          </span>
        </div>
        <div v-if="report.task_id" class="mr-info-meta__item">
          <span class="mr-info-meta__label">关联任务</span>
          <span class="mr-info-meta__value">#{{ report.task_id }}</span>
        </div>
        <div class="mr-info-meta__item">
          <span class="mr-info-meta__label">提交时间</span>
          <span class="mr-info-meta__value">{{ createdAtText }}</span>
        </div>
      </div>
    </div>
  </div>
</template>
