<script setup lang="ts">
import { computed } from 'vue'
import { Star, User as UserIcon, X } from 'lucide-vue-next'

import HomeAvatar from '../home/ui/HomeAvatar.vue'
import HomeStars from '../home/ui/HomeStars.vue'
import type { UserReview, WorkerProfile } from '../../types/api'
import type { Conversation } from '../../types/chat'
import { formatFull } from '../../utils/time'

const props = defineProps<{
  modelValue: boolean
  conversation: Conversation | null
  peerOnlineStatus: { online: boolean; text: string }
  peerWorkerProfile: WorkerProfile | null
  peerWorkerReviews: UserReview[]
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
}>()

const peerGenderLabel = computed(() => {
  if (props.conversation?.peer_gender === 'male') return '男'
  if (props.conversation?.peer_gender === 'female') return '女'
  return '未知性别'
})

function closeModal() {
  emit('update:modelValue', false)
}
</script>

<template>
  <Teleport to="body">
    <Transition name="modal-fade">
      <div v-if="modelValue" class="modal-overlay" @click.self="closeModal">
        <div class="modal-panel user-detail-panel">
          <div class="modal-header">
            <UserIcon :size="18" class="header-icon-accent" />
            <h3>用户资料</h3>
            <button class="icon-btn" @click="closeModal">
              <X :size="20" />
            </button>
          </div>

          <div class="modal-body user-detail-body">
            <div class="user-detail-section user-detail-top-section">
              <div class="user-detail-card">
                <HomeAvatar
                  :avatar-url="conversation?.peer_avatar ?? null"
                  :gender="conversation?.peer_gender ?? null"
                  size="xl"
                  :alt="conversation?.peer_name ?? ''"
                  class="user-detail-avatar"
                />

                <div class="user-detail-info">
                  <h4 class="user-detail-name">{{ conversation?.peer_name }}</h4>

                  <div class="user-detail-tags">
                    <span class="user-tag gender-tag">{{ peerGenderLabel }}</span>

                    <span class="user-tag online-tag" :class="{ 'online-active': peerOnlineStatus.online }">
                      {{ peerOnlineStatus.text }}
                    </span>
                  </div>

                  <template v-if="peerWorkerProfile">
                    <div class="user-worker-rating">
                      <HomeStars :value="Math.round(peerWorkerProfile.overall_rating_avg)" size="sm" />
                      <span class="rating-text">
                        {{
                          peerWorkerProfile.overall_rating_count > 0
                            ? `${peerWorkerProfile.overall_rating_avg.toFixed(1)} 分 · ${peerWorkerProfile.overall_rating_count} 评价`
                            : '暂无评分'
                        }}
                      </span>
                    </div>
                  </template>
                </div>
              </div>

              <template v-if="peerWorkerProfile">
                <div v-if="peerWorkerProfile.skill_tags.length" class="worker-skills">
                  <span v-for="tag in peerWorkerProfile.skill_tags" :key="tag.id" class="skill-chip">
                    {{ tag.name }}
                  </span>
                </div>

                <div class="hv-detail-grid">
                  <div class="hv-detail-item">
                    <span class="hv-detail-label">完成任务</span>
                    <span>{{ peerWorkerProfile.worker_completed_count }} 单</span>
                  </div>

                  <div class="hv-detail-item">
                    <span class="hv-detail-label">被拉黑</span>
                    <span>{{ peerWorkerProfile.blocked_by_count }} 次</span>
                  </div>

                  <div
                    v-if="peerWorkerProfile.min_price != null || peerWorkerProfile.max_price != null"
                    class="hv-detail-item"
                  >
                    <span class="hv-detail-label">报价区间</span>
                    <span>¥{{ peerWorkerProfile.min_price ?? '—' }} ~ ¥{{ peerWorkerProfile.max_price ?? '—' }}</span>
                  </div>
                </div>

                <p v-if="peerWorkerProfile.bio" class="worker-bio">
                  {{ peerWorkerProfile.bio }}
                </p>
              </template>

              <p v-else class="user-detail-no-worker">该用户暂未开通接单服务</p>
            </div>

            <template v-if="peerWorkerProfile">
              <div class="user-detail-section">
                <h4 class="user-detail-section-title">
                  <Star :size="14" />
                  历史评价
                </h4>

                <div v-if="peerWorkerReviews.length" class="user-reviews">
                  <div v-for="review in peerWorkerReviews" :key="review.id" class="user-review-item">
                    <div class="user-review-header">
                      <HomeStars :value="review.stars" size="sm" />
                      <span class="user-review-meta">
                        来自 {{ review.reviewer_display_name }} · {{ formatFull(review.created_at) }}
                      </span>
                    </div>
                    <p v-if="review.comment" class="user-review-comment">{{ review.comment }}</p>
                  </div>
                </div>

                <p v-else class="user-detail-hint">暂无历史评价</p>
              </div>
            </template>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.icon-btn {
  padding: 8px;
  border-radius: 50%;
  background: transparent;
  border: none;
  color: var(--c-text-muted);
  cursor: pointer;
  transition: all var(--dur-fast) var(--ease);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}

.icon-btn:hover {
  background: var(--c-bg);
  color: var(--c-text);
}

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  backdrop-filter: blur(4px);
}

.modal-panel {
  background: var(--c-surface);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xl);
  width: min(480px, 92vw);
  max-height: 80vh;
  display: flex;
  flex-direction: column;
}

.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.22s var(--ease);
}

.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}

.modal-fade-enter-active .modal-panel,
.modal-fade-leave-active .modal-panel {
  transition:
    transform 0.22s var(--ease),
    opacity 0.22s var(--ease);
}

.modal-fade-enter-from .modal-panel {
  transform: scale(0.95) translateY(10px);
  opacity: 0;
}

.modal-fade-leave-to .modal-panel {
  transform: scale(0.96) translateY(6px);
  opacity: 0;
}

.modal-header {
  padding: 16px 20px;
  border-bottom: 1px solid var(--c-border);
  display: flex;
  align-items: center;
  gap: 12px;
}

.modal-header h3 {
  font-size: var(--text-lg);
  font-weight: 700;
  flex: 1;
}

.modal-body {
  padding: 16px 20px;
  overflow-y: auto;
  flex: 1;
}

.user-detail-panel {
  width: min(440px, 92vw);
}

.header-icon-accent {
  color: var(--c-accent);
  flex-shrink: 0;
}

.user-detail-body {
  display: flex;
  flex-direction: column;
  padding: 0;
  gap: 0;
}

.user-detail-section {
  padding: 16px 20px;
  border-bottom: 1px solid var(--c-border-light);
}

.user-detail-section:last-child {
  border-bottom: none;
}

.user-detail-top-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.user-detail-card {
  display: flex;
  align-items: flex-start;
  gap: 14px;
}

.user-detail-avatar :deep(img) {
  border: 2px solid var(--c-border);
  box-shadow: var(--shadow-sm);
}

.user-detail-info {
  display: flex;
  flex-direction: column;
  gap: 5px;
  flex: 1;
  min-width: 0;
}

.user-detail-name {
  font-size: var(--text-lg);
  font-weight: 700;
  color: var(--c-text);
  margin: 0;
}

.user-detail-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.user-tag {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 99px;
  background: var(--c-bg);
  color: var(--c-text-secondary);
  border: 1px solid var(--c-border);
}

.gender-tag {
  background: #ede9fe;
  color: #7c3aed;
  border-color: #ddd6fe;
}

.online-active {
  background: #dcfce7;
  color: #16a34a;
  border-color: #bbf7d0;
}

.user-worker-rating {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 2px;
}

.rating-text {
  font-size: var(--text-xs);
  color: var(--c-text-muted);
}

.hv-detail-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.hv-detail-item {
  display: flex;
  flex-direction: column;
  gap: 3px;
  font-size: var(--text-sm);
}

.hv-detail-label {
  color: var(--c-text-muted);
  font-size: var(--text-xs);
}

.worker-bio {
  font-size: var(--text-sm);
  color: var(--c-text-secondary);
  line-height: 1.65;
  white-space: pre-wrap;
  margin: 0;
}

.worker-skills {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.skill-chip {
  display: inline-block;
  font-size: var(--text-sm);
  font-weight: 500;
  padding: 4px 12px;
  border-radius: var(--radius-full);
  background: var(--c-accent-light);
  color: var(--c-accent);
}

.user-detail-no-worker {
  color: var(--c-text-muted);
  font-size: var(--text-sm);
  margin: 0;
}

.user-detail-section-title {
  margin: 0 0 10px;
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--c-text-secondary);
  display: flex;
  align-items: center;
  gap: 6px;
}

.user-reviews {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.user-review-item {
  padding: 10px 12px;
  background: var(--c-bg);
  border-radius: var(--radius-md);
}

.user-review-header {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 4px;
}

.user-review-meta {
  color: var(--c-text-muted);
  font-size: var(--text-xs);
}

.user-review-comment {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--c-text-secondary);
  line-height: 1.5;
}

.user-detail-hint {
  color: var(--c-text-muted);
  font-size: var(--text-sm);
  margin: 0;
}
</style>
