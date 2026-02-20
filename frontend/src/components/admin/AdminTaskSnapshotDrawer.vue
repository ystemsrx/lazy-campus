<script setup lang="ts">
import type { TaskSnapshot } from '../../composables/admin/useAdminReports'
import { formatShort } from '../../utils/time'

defineProps<{
  show: boolean
  loading: boolean
  snapshot: TaskSnapshot | null
  taskStatusMap: Record<string, string>
}>()

defineEmits<{
  close: []
}>()
</script>

<template>
  <Teleport to="body">
    <Transition name="av-drawer">
      <div v-if="show" class="av-snapshot-overlay" @mousedown.self="$emit('close')">
        <div class="av-snapshot-drawer">
          <div class="av-snapshot-drawer__header">
            <h3>任务快照</h3>
            <button class="btn btn-ghost btn-sm" @click="$emit('close')">
              <i class="fa-solid fa-xmark"></i>
            </button>
          </div>

          <div v-if="loading" class="av-snapshot-drawer__loading">
            <div class="spinner"></div>
          </div>

          <div v-else-if="snapshot" class="av-snapshot-drawer__body">
            <div class="av-snap-section">
              <h4 class="av-snap-title">{{ snapshot.title }}</h4>
              <div class="av-snap-meta">
                <span
                  class="badge"
                  :class="{
                    'badge-green': snapshot.status === 'completed',
                    'badge-amber': snapshot.status === 'in_progress' || snapshot.status === 'under_review',
                    'badge-red': snapshot.status === 'canceled',
                    'badge-default': snapshot.status === 'open',
                  }"
                >
                  {{ taskStatusMap[snapshot.status] || snapshot.status }}
                </span>
                <span>¥{{ snapshot.price }}</span>
                <span v-if="snapshot.location"><i class="fa-solid fa-location-dot"></i> {{ snapshot.location }}</span>
              </div>
              <p class="av-snap-desc">{{ snapshot.description }}</p>
              <div class="av-snap-users">
                <div class="av-snap-user-row">
                  <span class="av-snap-user-label">发布者</span>
                  <span>{{ snapshot.publisher_display_name }}</span>
                </div>
                <div class="av-snap-user-row">
                  <span class="av-snap-user-label">接单者</span>
                  <span>{{ snapshot.assignee_display_name || '—' }}</span>
                </div>
                <div v-if="snapshot.deadline" class="av-snap-user-row">
                  <span class="av-snap-user-label">截止时间</span>
                  <span>{{ formatShort(snapshot.deadline) }}</span>
                </div>
              </div>
            </div>

            <div class="av-snap-section">
              <h4 class="av-snap-subtitle"><i class="fa-regular fa-comment-dots"></i> 聊天记录 ({{ snapshot.messages.length }})</h4>
              <div v-if="snapshot.messages.length" class="av-snap-chat">
                <div v-for="(msg, idx) in snapshot.messages" :key="idx" class="av-snap-msg">
                  <div class="av-snap-msg__head">
                    <span class="av-snap-msg__sender">{{ msg.sender_display_name }}</span>
                    <span class="av-snap-msg__time">{{ formatShort(msg.created_at) }}</span>
                  </div>
                  <div class="av-snap-msg__text">{{ msg.content }}</div>
                </div>
              </div>
              <p v-else class="av-snap-empty">暂无聊天记录</p>
            </div>

            <div class="av-snap-section">
              <h4 class="av-snap-subtitle"><i class="fa-regular fa-star-half-stroke"></i> 互评 ({{ snapshot.reviews.length }})</h4>
              <div v-if="snapshot.reviews.length" class="av-snap-reviews">
                <div v-for="(rev, idx) in snapshot.reviews" :key="idx" class="av-snap-review">
                  <div class="av-snap-review__head">
                    <span class="badge badge-default">{{ rev.target_role === 'worker' ? '评价接单者' : '评价发布者' }}</span>
                    <span class="av-snap-review__stars">
                      <i
                        v-for="star in 5"
                        :key="star"
                        :class="star <= rev.stars ? 'fa-solid fa-star' : 'fa-regular fa-star'"
                        class="av-review-star"
                      ></i>
                    </span>
                  </div>
                  <p class="av-snap-review__by">{{ rev.reviewer_display_name }} · {{ formatShort(rev.created_at) }}</p>
                  <p v-if="rev.comment" class="av-snap-review__comment">{{ rev.comment }}</p>
                </div>
              </div>
              <p v-else class="av-snap-empty">暂无评价</p>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.av-snapshot-overlay {
  position: fixed;
  inset: 0;
  z-index: 2000;
  display: flex;
  justify-content: flex-end;
  background: rgba(0, 0, 0, 0.3);
  backdrop-filter: blur(2px);
}

.av-snapshot-drawer {
  width: 520px;
  max-width: 100vw;
  height: 100vh;
  background: #fff;
  box-shadow: -8px 0 30px rgba(0, 0, 0, 0.12);
  display: flex;
  flex-direction: column;
  animation: av-slide-in 0.25s var(--ease, cubic-bezier(0.16, 1, 0.3, 1));
}

@keyframes av-slide-in {
  from {
    transform: translateX(100%);
  }
}

.av-snapshot-drawer__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 24px;
  border-bottom: 1px solid var(--c-border);
  flex-shrink: 0;
}

.av-snapshot-drawer__header h3 {
  margin: 0;
  font-size: 16px;
}

.av-snapshot-drawer__loading {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 200px;
  padding: 20px 24px;
}

.av-snapshot-drawer__body {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
}

.av-snap-section {
  margin-bottom: 24px;
}

.av-snap-section:last-child {
  margin-bottom: 0;
}

.av-snap-title {
  font-size: 16px;
  font-weight: 600;
  margin: 0 0 8px;
}

.av-snap-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: var(--text-sm);
  color: var(--c-text-secondary);
  margin-bottom: 10px;
}

.av-snap-desc {
  font-size: var(--text-sm);
  color: var(--c-text-secondary);
  line-height: 1.6;
  margin: 0 0 12px;
  white-space: pre-wrap;
}

.av-snap-users {
  background: var(--c-bg-secondary, #f8fafc);
  border-radius: var(--radius-md);
  padding: 10px 14px;
}

.av-snap-user-row {
  display: flex;
  gap: 12px;
  font-size: var(--text-sm);
  padding: 3px 0;
}

.av-snap-user-label {
  color: var(--c-text-muted);
  min-width: 56px;
  flex-shrink: 0;
}

.av-snap-subtitle {
  font-size: 14px;
  font-weight: 600;
  margin: 0 0 10px;
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--c-text);
}

.av-snap-chat {
  max-height: 360px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px;
  background: var(--c-bg-secondary, #f8fafc);
  border-radius: var(--radius-md);
}

.av-snap-msg__head {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 2px;
}

.av-snap-msg__sender {
  font-size: 12px;
  font-weight: 600;
  color: var(--c-text);
}

.av-snap-msg__time {
  font-size: 11px;
  color: var(--c-text-muted);
}

.av-snap-msg__text {
  font-size: var(--text-sm);
  color: var(--c-text-secondary);
  line-height: 1.5;
  word-break: break-word;
  padding: 6px 10px;
  background: #fff;
  border-radius: var(--radius-sm);
  display: inline-block;
}

.av-snap-reviews {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.av-snap-review {
  background: var(--c-bg-secondary, #f8fafc);
  border-radius: var(--radius-md);
  padding: 10px 14px;
}

.av-snap-review__head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.av-snap-review__stars {
  display: flex;
  gap: 1px;
}

.av-review-star {
  color: #f59e0b;
  font-size: 12px;
}

.av-snap-review__by {
  font-size: 12px;
  color: var(--c-text-muted);
  margin: 0 0 4px;
}

.av-snap-review__comment {
  font-size: var(--text-sm);
  color: var(--c-text-secondary);
  margin: 0;
  line-height: 1.5;
}

.av-snap-empty {
  color: var(--c-text-muted);
  font-size: var(--text-sm);
  text-align: center;
  padding: 16px 0;
}

.av-drawer-enter-active {
  transition: opacity 0.25s var(--ease);
}

.av-drawer-leave-active {
  transition: opacity 0.2s var(--ease);
}

.av-drawer-enter-from,
.av-drawer-leave-to {
  opacity: 0;
}
</style>
