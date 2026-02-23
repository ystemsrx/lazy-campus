<script setup lang="ts">
import { nextTick, onUnmounted, ref, watch } from 'vue'
import type { TaskSnapshot } from '../../composables/admin/useAdminReports'
import { formatShort } from '../../utils/time'

const props = defineProps<{
  show: boolean
  loading: boolean
  snapshot: TaskSnapshot | null
  taskStatusMap: Record<string, string>
}>()

const emit = defineEmits<{
  close: []
}>()

const chatRef = ref<HTMLElement | null>(null)
const sheetRef = ref<HTMLElement | null>(null)

let sheetDragStartY = 0
let sheetDragStartH = 0
let sheetCanExpand = false
let savedScrollY = 0

function scrollChatToBottom() {
  const el = chatRef.value
  if (el) el.scrollTop = el.scrollHeight
}

function resetSheetStyles() {
  const el = sheetRef.value
  if (!el) return
  el.style.maxHeight = ''
  el.style.transform = ''
  el.style.transition = ''
}

function onSheetTouchStart(e: TouchEvent) {
  const el = sheetRef.value
  if (!el) return
  sheetDragStartY = e.touches[0].clientY
  sheetDragStartH = el.getBoundingClientRect().height
  const body = el.querySelector('.av-snapshot-drawer__body') as HTMLElement | null
  sheetCanExpand = body ? body.scrollHeight > body.clientHeight + 2 : false
  el.style.transition = 'none'
  document.addEventListener('touchmove', onSheetTouchMove, { passive: false })
  document.addEventListener('touchend', onSheetTouchEnd)
}

function onSheetTouchMove(e: TouchEvent) {
  const el = sheetRef.value
  if (!el) return
  e.preventDefault()
  const deltaY = e.touches[0].clientY - sheetDragStartY
  const vh = window.innerHeight

  if (deltaY < 0) {
    const absDelta = Math.abs(deltaY)
    if (sheetCanExpand) {
      const expansion = Math.round(Math.pow(absDelta, 0.75))
      const cap = vh * 0.06
      el.style.maxHeight = `${sheetDragStartH + Math.min(expansion, cap)}px`
      el.style.transform = ''
    } else {
      el.style.transform = `translateY(${-Math.round(Math.pow(absDelta, 0.6))}px)`
    }
  } else {
    el.style.maxHeight = ''
    el.style.transform = `translateY(${deltaY}px)`
  }
}

function onSheetTouchEnd() {
  document.removeEventListener('touchmove', onSheetTouchMove)
  document.removeEventListener('touchend', onSheetTouchEnd)

  const el = sheetRef.value
  if (!el) return

  const match = el.style.transform.match(/translateY\(([^)]+)px\)/)
  const currentTranslateY = match ? parseFloat(match[1]) : 0
  const vh = window.innerHeight

  if (currentTranslateY > 120) {
    el.style.transition = 'transform 0.35s cubic-bezier(0.32, 0.72, 0, 1)'
    el.style.transform = `translateY(${vh}px)`
    setTimeout(() => emit('close'), 350)
    return
  }

  el.style.transition =
    'max-height 0.35s cubic-bezier(0.32, 0.72, 0, 1), transform 0.35s cubic-bezier(0.32, 0.72, 0, 1)'
  el.style.maxHeight = `${sheetDragStartH}px`
  el.style.transform = 'translateY(0px)'
  setTimeout(() => {
    el.style.transition = ''
    el.style.transform = ''
    el.style.maxHeight = ''
  }, 350)
}

watch(
  () => props.snapshot,
  async (snap) => {
    if (snap && snap.messages.length) {
      await nextTick()
      scrollChatToBottom()
    }
  },
)

watch(
  () => props.show,
  (open) => {
    if (open) {
      savedScrollY = window.scrollY
      document.body.style.position = 'fixed'
      document.body.style.top = `-${savedScrollY}px`
      document.body.style.width = '100%'
      resetSheetStyles()
    } else {
      document.body.style.position = ''
      document.body.style.top = ''
      document.body.style.width = ''
      window.scrollTo(0, savedScrollY)
    }
  },
  { immediate: true },
)

onUnmounted(() => {
  document.removeEventListener('touchmove', onSheetTouchMove)
  document.removeEventListener('touchend', onSheetTouchEnd)
  document.body.style.position = ''
  document.body.style.top = ''
  document.body.style.width = ''
})
</script>

<template>
  <Teleport to="body">
    <Transition name="av-drawer">
      <div v-if="show" class="av-snapshot-overlay" @mousedown.self="$emit('close')">
        <div ref="sheetRef" class="av-snapshot-drawer">
          <div class="av-snap-sheet-handle" @touchstart.passive="onSheetTouchStart">
            <div class="av-snap-sheet-handle__bar"></div>
          </div>
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
                <span v-if="snapshot.is_deleted" class="badge badge-red">
                  <i class="fa-solid fa-trash"></i> 已删除
                </span>
                <span
                  v-if="!snapshot.is_deleted"
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
              <div v-if="snapshot.messages.length" class="av-snap-chat-legend">
                <span class="av-snap-legend-item av-snap-legend-item--publisher">
                  <i class="fa-solid fa-circle"></i> 发布者
                </span>
                <span class="av-snap-legend-item av-snap-legend-item--assignee">
                  <i class="fa-solid fa-circle"></i> 接单者
                </span>
              </div>
              <div v-if="snapshot.messages.length" class="av-snap-chat">
                <div ref="chatRef" class="av-snap-chat__scroll">
                <div v-for="(msg, idx) in snapshot.messages" :key="idx" class="av-snap-msg">
                  <div class="av-snap-msg__head">
                    <span
                      class="av-snap-msg__sender"
                      :class="{
                        'av-snap-msg__sender--publisher': msg.sender_display_name === snapshot.publisher_display_name,
                        'av-snap-msg__sender--assignee': msg.sender_display_name === snapshot.assignee_display_name,
                      }"
                    >{{ msg.sender_display_name }}</span>
                    <span class="av-snap-msg__time">{{ formatShort(msg.created_at) }}</span>
                  </div>
                  <div class="av-snap-msg__text">{{ msg.content }}</div>
                </div>
                </div><!-- /av-snap-chat__scroll -->
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
  background: rgba(15, 23, 42, 0.35);
}

.av-snapshot-drawer {
  width: 520px;
  max-width: 100vw;
  height: 100vh;
  background: #f8fafc;
  box-shadow: -8px 0 30px rgba(0, 0, 0, 0.08);
  display: flex;
  flex-direction: column;
  will-change: transform;
}

.av-snap-sheet-handle {
  display: none;
  justify-content: center;
  padding: 10px 0 2px;
  cursor: grab;
  touch-action: none;
  flex-shrink: 0;
}

.av-snap-sheet-handle__bar {
  width: 36px;
  height: 4px;
  border-radius: 2px;
  background: var(--c-border);
  transition: background var(--dur-fast, 0.15s) var(--ease);
}

.av-snap-sheet-handle:active .av-snap-sheet-handle__bar {
  background: var(--c-text-muted);
}

.av-snapshot-drawer__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid var(--c-border);
  flex-shrink: 0;
  background: var(--c-surface);
}

.av-snapshot-drawer__header h3 {
  margin: 0;
  font-size: 17px;
  font-weight: 700;
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
  background: #fff;
  border: 1px solid rgba(226, 232, 240, 0.6);
  border-radius: var(--radius-lg);
  padding: 12px 16px;
  box-shadow: var(--shadow-xs);
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
  background: #fff;
  border: 1px solid rgba(226, 232, 240, 0.6);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-card);
  overflow: hidden;
}

.av-snap-chat__scroll {
  max-height: 360px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 14px;
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

.av-snap-msg__sender--publisher {
  color: var(--c-accent, #6366f1);
}

.av-snap-msg__sender--assignee {
  color: #ef4444;
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
  background: #fff;
  border: 1px solid rgba(226, 232, 240, 0.6);
  border-radius: var(--radius-lg);
  padding: 12px 16px;
  box-shadow: var(--shadow-xs);
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

.av-snap-chat-legend {
  display: flex;
  gap: 14px;
  margin-bottom: 8px;
  font-size: 12px;
}

.av-snap-legend-item {
  display: flex;
  align-items: center;
  gap: 4px;
  color: var(--c-text-muted);
}

.av-snap-legend-item i {
  font-size: 8px;
}

.av-snap-legend-item--publisher i {
  color: var(--c-accent, #6366f1);
}

.av-snap-legend-item--assignee i {
  color: #ef4444;
}

.av-drawer-enter-active {
  transition: opacity 0.3s var(--ease);
}

.av-drawer-enter-active .av-snapshot-drawer {
  transition: transform 0.3s var(--ease);
}

.av-drawer-leave-active {
  transition: opacity 0.2s var(--ease);
}

.av-drawer-leave-active .av-snapshot-drawer {
  transition: transform 0.2s var(--ease);
}

.av-drawer-enter-from,
.av-drawer-leave-to {
  opacity: 0;
}

.av-drawer-enter-from .av-snapshot-drawer,
.av-drawer-leave-to .av-snapshot-drawer {
  transform: translateX(100%);
}

@media (max-width: 900px) {
  .av-snapshot-overlay {
    flex-direction: column;
    justify-content: flex-end;
    align-items: stretch;
  }

  .av-snapshot-drawer {
    width: 100% !important;
    height: auto !important;
    max-height: 92vh;
    border-radius: 16px 16px 0 0;
    box-shadow: 0 80px 0 0 #f8fafc, 0 -4px 20px rgba(0, 0, 0, 0.1);
    overflow: hidden;
  }

  .av-snapshot-drawer__header .btn-ghost {
    display: none;
  }

  .av-snap-sheet-handle {
    display: flex;
  }

  .av-drawer-enter-from .av-snapshot-drawer,
  .av-drawer-leave-to .av-snapshot-drawer {
    transform: translateY(100%);
  }
}
</style>
