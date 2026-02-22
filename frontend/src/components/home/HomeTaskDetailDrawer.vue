<script setup lang="ts">
import { computed, nextTick, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import HomeStars from './ui/HomeStars.vue'
import { fetchMessageSnapshot } from '../../api/chat'
import type { Task, TaskMessage, TaskReview, UserReview } from '../../types/api'
import type { ChatMessage } from '../../types/chat'

const chatRouter = useRouter()

type ReviewForm = {
  stars: number
  comment: string
}

const chatSnapshot = ref<ChatMessage[]>([])
const chatSnapshotLoading = ref(false)
const chatHasMore = ref(false)


const props = defineProps<{
  task: Task | null
  isAuthenticated: boolean
  meId: number | null
  isParticipant: boolean
  isPublisher: boolean
  canAccept: boolean
  genderMismatch: boolean
  canConfirm: boolean
  canAbandon: boolean
  canEditTask: boolean
  canDeleteTask: boolean
  deleteBlockedByAssignee: boolean
  taskMessages: TaskMessage[]
  taskReviews: TaskReview[]
  publisherHistoryReviews: UserReview[]
  chatContent: string
  showReviewForm: boolean
  reviewForm: ReviewForm
  myReviewTargetRole: 'worker' | 'publisher' | null
  hasAlreadyReviewed: boolean
  bothSidesReviewed: boolean
  waitingForOtherReview: boolean
  canReview: boolean
  canReport: boolean
  statusOf: (status: string) => { label: string; cls: string }
  genderLabel: (gender: string | null) => { label: string; icon: string; cls: string } | null
  isExpired: (iso: string) => boolean
  formatFull: (iso: string) => string
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'login'): void
  (e: 'accept-task'): void
  (e: 'confirm-task'): void
  (e: 'abandon-task'): void
  (e: 'edit-task'): void
  (e: 'delete-task'): void
  (e: 'update:chatContent', value: string): void
  (e: 'submit-message'): void
  (e: 'update:showReviewForm', value: boolean): void
  (e: 'submit-review'): void
  (e: 'open-report'): void
  (e: 'block-user', userId: number): void
}>()

const task = computed(() => props.task)
const chatContentValue = computed({
  get: () => props.chatContent,
  set: (value: string) => emit('update:chatContent', value),
})

const showReviewFormValue = computed({
  get: () => props.showReviewForm,
  set: (value: boolean) => emit('update:showReviewForm', value),
})

const bottomSheetRef = ref<HTMLElement | null>(null)
const messagesEnd = ref<HTMLDivElement | null>(null)
let sheetDragStartY = 0
let sheetDragStartH = 0
let sheetCanExpand = false
let savedScrollY = 0

watch(
  () => !!props.task,
  (open) => {
    if (open) {
      savedScrollY = window.scrollY
      document.body.style.position = 'fixed'
      document.body.style.top = `-${savedScrollY}px`
      document.body.style.width = '100%'
    } else {
      document.body.style.position = ''
      document.body.style.top = ''
      document.body.style.width = ''
      window.scrollTo(0, savedScrollY)
    }
  },
  { immediate: true },
)

function closeDrawer() {
  emit('close')
}

function resetSheetStyles() {
  const el = bottomSheetRef.value
  if (!el) return
  el.style.maxHeight = ''
  el.style.transform = ''
  el.style.transition = ''
}

function onSheetTouchStart(e: TouchEvent) {
  const el = bottomSheetRef.value
  if (!el) return
  sheetDragStartY = e.touches[0].clientY
  sheetDragStartH = el.getBoundingClientRect().height

  const body = el.querySelector('.hv-drawer__body') as HTMLElement | null
  sheetCanExpand = body ? body.scrollHeight > body.clientHeight + 2 : false

  el.style.transition = 'none'
  document.addEventListener('touchmove', onSheetTouchMove, { passive: false })
  document.addEventListener('touchend', onSheetTouchEnd)
}

function onSheetTouchMove(e: TouchEvent) {
  const el = bottomSheetRef.value
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

  const el = bottomSheetRef.value
  if (!el) return

  const match = el.style.transform.match(/translateY\(([^)]+)px\)/)
  const currentTranslateY = match ? parseFloat(match[1]) : 0
  const vh = window.innerHeight

  if (currentTranslateY > 120) {
    el.style.transition = 'transform 0.35s cubic-bezier(0.32, 0.72, 0, 1)'
    el.style.transform = `translateY(${vh}px)`
    setTimeout(() => closeDrawer(), 350)
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

function scrollMessagesToBottom() {
  nextTick(() => {
    messagesEnd.value?.scrollIntoView({ behavior: 'smooth' })
  })
}

watch(
  () => props.taskMessages.length,
  () => scrollMessagesToBottom(),
)

watch(
  () => props.task?.id,
  async (newId) => {
    if (newId != null) {
      resetSheetStyles()
      await loadChatSnapshot()
    }
    scrollMessagesToBottom()
  },
)

async function loadChatSnapshot() {
  const t = props.task
  if (!t || !props.isParticipant || !props.meId) return
  const peerId = t.publisher_id === props.meId ? t.assignee_id : t.publisher_id
  if (!peerId) return
  chatSnapshotLoading.value = true
  try {
    chatSnapshot.value = await fetchMessageSnapshot(peerId, t.id)
    chatHasMore.value = chatSnapshot.value.length >= 10
  } catch { chatSnapshot.value = [] }
  chatSnapshotLoading.value = false
}

function openFullChat() {
  const t = props.task
  if (!t || !props.meId) return
  const peerId = t.publisher_id === props.meId ? t.assignee_id : t.publisher_id
  if (!peerId) return
  chatRouter.push({ path: '/chat', query: { peer: String(peerId), task: String(t.id) } })
}

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
    <Transition name="drawer">
      <div v-if="task" class="hv-drawer-overlay hv-task-detail-overlay" @click.self="closeDrawer">
        <div ref="bottomSheetRef" class="hv-drawer hv-task-detail-drawer">
          <div class="hv-sheet-handle" @touchstart.passive="onSheetTouchStart">
            <div class="hv-sheet-handle__bar"></div>
          </div>

          <div class="hv-drawer__header">
            <h3>任务详情</h3>
            <button class="btn btn-ghost btn-sm" aria-label="关闭" @click="closeDrawer"><i class="fa-solid fa-xmark"></i></button>
          </div>

          <div class="hv-drawer__body">
            <div class="hv-drawer__section">
              <div class="hv-detail-top">
                <span class="badge" :class="statusOf(task.status).cls">{{ statusOf(task.status).label }}</span>
                <span v-if="task.required_gender && genderLabel(task.required_gender)" class="badge" :class="genderLabel(task.required_gender)!.cls">
                  <i :class="genderLabel(task.required_gender)!.icon" class="hv-gender-icon"></i>{{ genderLabel(task.required_gender)!.label }}
                </span>
                <span class="hv-price">¥{{ task.price }}</span>
              </div>

              <h3 class="hv-detail-title">{{ task.title }}</h3>
              <p class="hv-detail-description">{{ task.description }}</p>

              <div class="hv-detail-grid">
                <div class="hv-detail-item">
                  <span class="hv-detail-label">发布者</span>
                  <span>
                    {{ task.publisher_display_name }}
                    <span v-if="task.publisher_rating_count > 0" class="hv-task-card__pub-rating hv-pub-rating-inline">
                      <i class="fa-solid fa-star hv-task-card__star"></i>
                      <span class="hv-task-card__rating-score">{{ task.publisher_rating_avg.toFixed(1) }}</span>
                      <span class="hv-task-card__rating-count">({{ task.publisher_rating_count }}条评价)</span>
                    </span>
                  </span>
                </div>

                <div class="hv-detail-item">
                  <span class="hv-detail-label">地点</span>
                  <span>{{ task.location || '未填写' }}</span>
                </div>

                <div class="hv-detail-item">
                  <span class="hv-detail-label">任务数</span>
                  <span>{{ task.publisher_task_count }} 个</span>
                </div>

                <div class="hv-detail-item">
                  <span class="hv-detail-label">被拉黑</span>
                  <span>{{ task.publisher_blocked_by_count }} 次</span>
                </div>

                <div class="hv-detail-item">
                  <span class="hv-detail-label">截止</span>
                  <span v-if="task.deadline" :class="{ 'hv-meta--expired': isExpired(task.deadline) }">
                    {{ formatFull(task.deadline) }}
                    <span v-if="isExpired(task.deadline)" class="badge badge-red hv-expired-badge">已过期</span>
                  </span>
                  <span v-else>未设置</span>
                </div>

                <div class="hv-detail-item">
                  <span class="hv-detail-label">联系方式</span>
                  <span>{{ task.contact_info || '仅站内沟通' }}</span>
                </div>
              </div>

              <div v-if="!isAuthenticated && task.status === 'open'" class="hv-drawer__actions">
                <button class="btn btn-primary" @click="emit('login')"><i class="fa-solid fa-right-to-bracket"></i> 登录后接取任务</button>
              </div>

              <div v-else-if="canAccept || canConfirm || canAbandon || isPublisher || genderMismatch" class="hv-drawer__actions">
                <button v-if="canAccept" class="btn btn-primary" @click="emit('accept-task')"><i class="fa-solid fa-hand-pointer"></i> 接取此任务</button>
                <button v-if="canConfirm" class="btn btn-success" @click="emit('confirm-task')"><i class="fa-solid fa-circle-check"></i> 确认完成</button>
                <button v-if="canAbandon" class="btn btn-danger btn-sm" @click="emit('abandon-task')"><i class="fa-solid fa-person-running"></i> 放弃接取</button>
                <button v-if="canEditTask" class="btn btn-outline btn-sm" @click="emit('edit-task')"><i class="fa-solid fa-pen-to-square"></i> 编辑</button>
                <button v-if="canDeleteTask" class="btn btn-danger btn-sm" @click="emit('delete-task')"><i class="fa-solid fa-trash"></i> 删除任务</button>
                <span v-if="deleteBlockedByAssignee" class="hv-delete-hint"><i class="fa-solid fa-lock"></i> 任务已被接取，接单者放弃后方可删除</span>
                <span v-if="genderMismatch" class="hv-delete-hint">
                  <i class="fa-solid fa-ban"></i>
                  该任务限{{ task.required_gender === 'male' ? '男生' : '女生' }}接取，您不满足要求
                </span>
              </div>
            </div>

            <div class="hv-drawer__section">
              <h4 class="hv-drawer__subtitle"><i class="fa-regular fa-comment-dots"></i> 站内消息</h4>
              <div v-if="isParticipant" class="hv-chat">
                <div class="hv-chat__messages">
                  <div v-if="chatSnapshotLoading" class="hv-chat-empty">加载中...</div>
                  <template v-else>
                    <div v-if="chatHasMore" class="hv-chat-more-hint">
                      <span>仅显示最近 10 条，</span>
                      <button class="hv-chat-more-link" @click="openFullChat">查看全部消息</button>
                    </div>
                    <div v-for="m in chatSnapshot" :key="m.id" class="hv-chat__msg" :class="{ 'hv-chat__msg--mine': meId !== null && m.sender_id === meId }">
                      <span class="hv-chat__sender">{{ m.sender_id === meId ? '我' : task?.publisher_display_name }}</span>
                      <span class="hv-chat__text">{{ m.content }}</span>
                    </div>
                    <p v-if="chatSnapshot.length === 0" class="hv-chat-empty">暂无消息</p>
                  </template>
                  <div ref="messagesEnd"></div>
                </div>
                <div class="hv-chat-snapshot-footer">
                  <button class="btn btn-outline btn-sm" @click="openFullChat">
                    <i class="fa-solid fa-arrow-up-right-from-square"></i> 进入聊天页面发送消息
                  </button>
                </div>
              </div>
              <p v-else class="hv-section-hint">仅任务参与者可查看和发送消息。</p>
            </div>

            <div v-if="task.status === 'open'" class="hv-drawer__section">
              <h4 class="hv-drawer__subtitle"><i class="fa-regular fa-star"></i> 历史评价</h4>
              <div class="hv-reviews">
                <div v-for="r in publisherHistoryReviews" :key="r.id" class="hv-review">
                  <div class="hv-review__header">
                    <HomeStars size="sm" :value="r.stars" />
                    <span class="hv-review-meta">来自 {{ r.reviewer_display_name }}</span>
                  </div>
                  <p v-if="r.comment" class="hv-review__comment">{{ r.comment }}</p>
                </div>
                <p v-if="publisherHistoryReviews.length === 0" class="hv-section-hint">该发布者暂无历史评价</p>
              </div>
            </div>

            <div v-else-if="task.status === 'in_progress' || task.status === 'under_review'" class="hv-drawer__section">
              <h4 class="hv-drawer__subtitle"><i class="fa-regular fa-star-half-stroke"></i> 双向互评</h4>
              <div class="hv-reviewed-hint hv-reviewed-hint--waiting">
                <i class="fa-solid fa-clock"></i> 任务完成后可评价
              </div>
            </div>

            <div v-else-if="task.status === 'completed'" class="hv-drawer__section">
              <h4 class="hv-drawer__subtitle"><i class="fa-regular fa-star-half-stroke"></i> 双向互评</h4>
              <div class="hv-reviews">
                <div v-for="r in taskReviews" :key="r.id" class="hv-review">
                  <div class="hv-review__header">
                    <span class="badge badge-default">{{ r.target_role === 'worker' ? '评价接单者' : '评价发布者' }}</span>
                    <HomeStars size="sm" :value="r.stars" />
                    <span v-if="meId !== null && r.reviewer_id === meId" class="hv-review__mine">我的评价</span>
                  </div>
                  <p v-if="r.comment" class="hv-review__comment">{{ r.comment }}</p>
                </div>
                <p v-if="taskReviews.length === 0 && !canReview" class="hv-section-hint">暂无评价</p>
              </div>

              <div v-if="waitingForOtherReview" class="hv-reviewed-hint hv-reviewed-hint--waiting">
                <i class="fa-solid fa-hourglass-half"></i> 您已评价，等待对方评价后双方评价互相可见
              </div>
              <div v-else-if="isParticipant && hasAlreadyReviewed && bothSidesReviewed" class="hv-reviewed-hint">
                <i class="fa-solid fa-circle-check"></i> 互评已完成
              </div>

              <div v-if="canReview && !showReviewFormValue" class="hv-review-form-trigger">
                <button class="btn btn-primary btn-sm" @click="showReviewFormValue = true"><i class="fa-solid fa-pen-to-square"></i> 立即评价</button>
              </div>

              <div v-if="canReview && showReviewFormValue" class="hv-review-form">
                <div class="hv-review-form__top">
                  <span class="badge badge-default">{{ myReviewTargetRole === 'worker' ? '评价接单者' : '评价发布者' }}</span>
                  <div class="hv-star-input">
                    <button
                      v-for="n in 5"
                      :key="n"
                      type="button"
                      class="hv-star-btn"
                      :class="{ active: n <= reviewForm.stars }"
                      @click="reviewForm.stars = n"
                    >
                      <i :class="n <= reviewForm.stars ? 'fa-solid fa-star' : 'fa-regular fa-star'"></i>
                    </button>
                  </div>
                </div>
                <div class="hv-review-form__action">
                  <input v-model="reviewForm.comment" class="form-input" placeholder="评价内容（选填）" />
                  <button class="btn btn-primary btn-sm" @click="emit('submit-review')">提交</button>
                </div>
              </div>
            </div>

            <div v-if="canReport || (isAuthenticated && meId !== null && (!isPublisher || (isPublisher && task.assignee_id)))" class="hv-drawer__section hv-report-section">
              <button v-if="canReport" class="btn btn-report-trigger" @click="emit('open-report')">
                <i class="fa-solid fa-flag"></i>
                举报对方
              </button>
              <button v-if="isAuthenticated && !isPublisher && meId !== null" class="btn btn-block-trigger" @click="emit('block-user', task.publisher_id)">
                <i class="fa-solid fa-ban"></i>
                拉黑发布者
              </button>
              <button v-if="isAuthenticated && isPublisher && task.assignee_id" class="btn btn-block-trigger" @click="emit('block-user', task.assignee_id as number)">
                <i class="fa-solid fa-ban"></i>
                拉黑接单者
              </button>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.hv-drawer-overlay {
  position: fixed;
  inset: 0;
  z-index: 100;
  background: rgba(15, 23, 42, 0.35);
  display: flex;
  justify-content: flex-end;
}

.hv-drawer {
  width: min(540px, 92vw);
  height: 100vh;
  background: var(--c-surface);
  display: flex;
  flex-direction: column;
  box-shadow: -4px 0 24px rgba(0, 0, 0, 0.12);
}

.hv-drawer__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  border-bottom: 1px solid var(--c-border);
  flex-shrink: 0;
}

.hv-drawer__header h3 {
  margin: 0;
}

.hv-drawer__body {
  flex: 1;
  overflow-y: auto;
  padding: 0;
}

.hv-drawer__section {
  padding: 20px 24px;
  border-bottom: 1px solid var(--c-border-light);
}

.hv-drawer__section:last-child {
  border-bottom: none;
}

.hv-drawer__subtitle {
  margin: 0 0 12px;
  font-size: var(--text-base);
  color: var(--c-text-secondary);
  display: flex;
  align-items: center;
  gap: 7px;
}

.hv-drawer__actions {
  display: flex;
  gap: 10px;
  margin-top: 16px;
}

.hv-detail-top {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
  flex-wrap: wrap;
}

.hv-gender-icon {
  margin-right: 3px;
}

.hv-price {
  font-size: var(--text-2xl);
  font-weight: 700;
  color: var(--c-accent);
}

.hv-detail-title {
  margin-bottom: 8px;
}

.hv-detail-description {
  color: var(--c-text-secondary);
  line-height: 1.7;
  margin-bottom: 12px;
}

.hv-detail-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.hv-detail-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: var(--text-sm);
}

.hv-detail-label {
  color: var(--c-text-muted);
  font-size: var(--text-xs);
}

.hv-task-card__pub-rating {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: var(--text-xs);
  margin-top: 1px;
}

.hv-pub-rating-inline {
  margin-left: 6px;
}

.hv-task-card__star {
  color: #f5a623;
  font-size: 11px;
}

.hv-task-card__rating-score {
  font-weight: 600;
  color: var(--c-text);
}

.hv-task-card__rating-count {
  color: var(--c-text-muted);
}

.hv-chat__messages {
  max-height: 220px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 10px;
  padding: 4px 0;
}

.hv-chat__msg {
  display: flex;
  flex-direction: column;
  gap: 2px;
  max-width: 85%;
}

.hv-chat__msg--mine {
  align-self: flex-end;
  align-items: flex-end;
}

.hv-chat__sender {
  font-size: var(--text-xs);
  color: var(--c-text-muted);
}

.hv-chat__text {
  display: inline-block;
  padding: 8px 12px;
  border-radius: var(--radius-md);
  background: var(--c-border-light);
  font-size: var(--text-sm);
  line-height: 1.5;
  word-break: break-word;
}

.hv-chat__msg--mine .hv-chat__text {
  background: var(--c-accent);
  color: #fff;
}

.hv-chat__input {
  display: flex;
  gap: 8px;
}

.hv-chat-empty,
.hv-section-hint {
  color: var(--c-text-muted);
  font-size: var(--text-sm);
}

.hv-chat-empty {
  text-align: center;
  padding: 16px 0;
}

.hv-chat-more-hint {
  text-align: center;
  padding: 6px 0 10px;
  font-size: var(--text-xs);
  color: var(--c-text-muted);
}

.hv-chat-more-link {
  background: none;
  border: none;
  color: var(--c-accent);
  font-size: var(--text-xs);
  cursor: pointer;
  padding: 0;
  text-decoration: underline;
}

.hv-chat-snapshot-footer {
  margin-top: 10px;
  display: flex;
  justify-content: center;
}

.hv-reviews {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 14px;
}

.hv-review {
  padding: 10px 14px;
  background: var(--c-border-light);
  border-radius: var(--radius-md);
}

.hv-review__header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.hv-review-meta {
  color: var(--c-text-muted);
  font-size: var(--text-xs);
}

.hv-review__comment {
  margin: 6px 0 0;
  font-size: var(--text-sm);
  color: var(--c-text-secondary);
}

.hv-review__mine {
  font-size: var(--text-xs);
  color: var(--c-accent);
  margin-left: auto;
}

.hv-review-form-trigger {
  margin-top: 10px;
}

.hv-review-form {
  padding: 12px 14px;
  background: var(--c-border-light);
  border-radius: var(--radius-md);
}

.hv-review-form__top {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}

.hv-review-form__action {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}

.hv-star-input {
  display: flex;
  gap: 2px;
}

.hv-star-btn {
  border: none;
  background: transparent;
  font-size: 22px;
  color: var(--c-border);
  padding: 0 2px;
  transition: color var(--dur-fast) var(--ease), transform var(--dur-fast) var(--ease);
}

.hv-star-btn.active {
  color: #f59e0b;
}

@media (hover: hover) {
  .hv-star-btn:hover {
    transform: scale(1.2);
  }
}

.hv-reviewed-hint {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: var(--text-sm);
  color: var(--c-success);
  padding: 8px 0;
}

.hv-reviewed-hint--waiting {
  color: var(--c-text-muted);
}

.hv-report-section {
  display: flex;
  justify-content: flex-start;
  gap: 10px;
  flex-wrap: wrap;
}

.btn-report-trigger,
.btn-block-trigger {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 16px;
  border-radius: var(--radius-md);
  border: 1px solid #fca5a5;
  background: #fff1f2;
  color: #ef4444;
  font-size: var(--text-sm);
  cursor: pointer;
}

.btn-block-trigger:hover {
  background: #fee2e2;
}

.hv-delete-hint {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: var(--text-xs);
  color: var(--c-text-muted);
}

.hv-meta--expired {
  color: var(--c-danger) !important;
}

.hv-expired-badge {
  font-size: 10px;
  padding: 1px 5px;
  vertical-align: middle;
  margin-left: 3px;
}

.badge-pink {
  background: #fce7f3;
  color: #be185d;
}

.hv-sheet-handle {
  display: none;
  justify-content: center;
  padding: 10px 0 2px;
  cursor: grab;
  touch-action: none;
  flex-shrink: 0;
}

.hv-sheet-handle__bar {
  width: 36px;
  height: 4px;
  border-radius: 2px;
  background: var(--c-border);
  transition: background var(--dur-fast) var(--ease);
}

.hv-sheet-handle:active .hv-sheet-handle__bar {
  background: var(--c-text-muted);
}

.drawer-enter-active {
  transition: all var(--dur-slow) var(--ease);
}

.drawer-leave-active {
  transition: all var(--dur-normal) var(--ease);
}

.drawer-enter-active .hv-drawer {
  transition: transform var(--dur-slow) var(--ease);
}

.drawer-leave-active .hv-drawer {
  transition: transform var(--dur-normal) var(--ease);
}

.drawer-enter-from,
.drawer-leave-to {
  opacity: 0;
}

.drawer-enter-from .hv-drawer,
.drawer-leave-to .hv-drawer {
  transform: translateX(100%);
}

@media (max-width: 900px) {
  .hv-task-detail-overlay {
    flex-direction: column;
    justify-content: flex-end;
    align-items: stretch;
  }

  .hv-task-detail-drawer {
    width: 100% !important;
    height: auto !important;
    max-height: 92vh;
    border-radius: 16px 16px 0 0;
    box-shadow: 0 80px 0 0 var(--c-surface), 0 -4px 20px rgba(0, 0, 0, 0.1);
    overflow: hidden;
  }

  .hv-drawer__header .btn-ghost {
    display: none;
  }

  .hv-sheet-handle {
    display: flex;
  }

  .drawer-enter-from .hv-task-detail-drawer,
  .drawer-leave-to .hv-task-detail-drawer {
    transform: translateY(100%);
  }
}
</style>
