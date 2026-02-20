<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from "vue";
import AppDropdown from "../AppDropdown.vue";
import HomeAvatar from "./ui/HomeAvatar.vue";
import HomeStars from "./ui/HomeStars.vue";
import type {
  UserReview,
  WorkerContactReveal,
  WorkerProfile,
} from "../../types/api";

const props = defineProps<{
  worker: WorkerProfile | null;
  reviews: UserReview[];
  contactReveal: WorkerContactReveal | null;
  isAuthenticated: boolean;
  revealLoading: boolean;
  formatFull: (iso: string) => string;
}>();

const emit = defineEmits<{
  (e: "close"): void;
  (e: "login"): void;
  (e: "contactAction", value: "view_contact" | "internal_contact"): void;
}>();

const worker = computed(() => props.worker);
const selectedContactAction = ref<string | number | null>(null);
const contactOptions = [
  { value: "view_contact", label: "查看联系方式" },
  { value: "internal_contact", label: "站内联系" },
];

const bottomSheetRef = ref<HTMLElement | null>(null);
let sheetDragStartY = 0;
let sheetDragStartH = 0;
let sheetCanExpand = false;

function closeDrawer() {
  selectedContactAction.value = null;
  emit("close");
}

function resetSheetStyles() {
  const el = bottomSheetRef.value;
  if (!el) return;
  el.style.maxHeight = "";
  el.style.transform = "";
  el.style.transition = "";
}

function onSheetTouchStart(e: TouchEvent) {
  const el = bottomSheetRef.value;
  if (!el) return;
  sheetDragStartY = e.touches[0].clientY;
  sheetDragStartH = el.getBoundingClientRect().height;

  const body = el.querySelector(".hv-drawer__body") as HTMLElement | null;
  sheetCanExpand = body ? body.scrollHeight > body.clientHeight + 2 : false;

  el.style.transition = "none";
  document.addEventListener("touchmove", onSheetTouchMove, { passive: false });
  document.addEventListener("touchend", onSheetTouchEnd);
}

function onSheetTouchMove(e: TouchEvent) {
  const el = bottomSheetRef.value;
  if (!el) return;
  e.preventDefault();
  const deltaY = e.touches[0].clientY - sheetDragStartY;
  const vh = window.innerHeight;

  if (deltaY < 0) {
    const absDelta = Math.abs(deltaY);
    if (sheetCanExpand) {
      const expansion = Math.round(Math.pow(absDelta, 0.75));
      const cap = vh * 0.06;
      el.style.maxHeight = `${sheetDragStartH + Math.min(expansion, cap)}px`;
      el.style.transform = "";
    } else {
      el.style.transform = `translateY(${-Math.round(Math.pow(absDelta, 0.6))}px)`;
    }
  } else {
    el.style.maxHeight = "";
    el.style.transform = `translateY(${deltaY}px)`;
  }
}

function onSheetTouchEnd() {
  document.removeEventListener("touchmove", onSheetTouchMove);
  document.removeEventListener("touchend", onSheetTouchEnd);

  const el = bottomSheetRef.value;
  if (!el) return;

  const match = el.style.transform.match(/translateY\(([^)]+)px\)/);
  const currentTranslateY = match ? parseFloat(match[1]) : 0;
  const vh = window.innerHeight;

  if (currentTranslateY > 120) {
    el.style.transition = "transform 0.35s cubic-bezier(0.32, 0.72, 0, 1)";
    el.style.transform = `translateY(${vh}px)`;
    setTimeout(() => closeDrawer(), 350);
    return;
  }

  el.style.transition =
    "max-height 0.35s cubic-bezier(0.32, 0.72, 0, 1), transform 0.35s cubic-bezier(0.32, 0.72, 0, 1)";
  el.style.maxHeight = `${sheetDragStartH}px`;
  el.style.transform = "translateY(0px)";
  setTimeout(() => {
    el.style.transition = "";
    el.style.transform = "";
    el.style.maxHeight = "";
  }, 350);
}

watch(
  () => selectedContactAction.value,
  (value) => {
    if (value === "view_contact" || value === "internal_contact") {
      emit("contactAction", value);
      selectedContactAction.value = null;
    }
  },
);

watch(
  () => props.worker?.user_id,
  () => {
    resetSheetStyles();
    selectedContactAction.value = null;
  },
);

onUnmounted(() => {
  document.removeEventListener("touchmove", onSheetTouchMove);
  document.removeEventListener("touchend", onSheetTouchEnd);
});
</script>

<template>
  <Teleport to="body">
    <Transition name="drawer">
      <div
        v-if="worker"
        class="hv-drawer-overlay hv-worker-detail-overlay"
        @click.self="closeDrawer"
      >
        <div ref="bottomSheetRef" class="hv-drawer hv-worker-detail-drawer">
          <div class="hv-sheet-handle" @touchstart.passive="onSheetTouchStart">
            <div class="hv-sheet-handle__bar"></div>
          </div>

          <div class="hv-drawer__header">
            <h3>接单者详情</h3>
            <button
              class="btn btn-ghost btn-sm"
              aria-label="关闭"
              @click="closeDrawer"
            >
              <i class="fa-solid fa-xmark"></i>
            </button>
          </div>

          <div class="hv-drawer__body">
            <div class="hv-drawer__section">
              <div class="hv-worker-top">
                <HomeAvatar
                  size="xl"
                  :avatar-url="worker.avatar_url"
                  :gender="worker.gender"
                  alt="worker avatar"
                />
                <div class="hv-worker-top__info">
                  <h3>{{ worker.display_name }}</h3>
                  <div class="hv-worker-top__rating">
                    <HomeStars :value="Math.round(worker.overall_rating_avg)" />
                    <span>
                      {{
                        worker.overall_rating_count > 0
                          ? `${worker.overall_rating_avg.toFixed(1)} 分 · ${worker.overall_rating_count} 评价`
                          : "暂无评分"
                      }}
                    </span>
                  </div>
                </div>
              </div>

              <div v-if="worker.skill_tags.length" class="hv-worker-skill-tags">
                <span v-for="tag in worker.skill_tags" :key="tag.id" class="hv-worker-skill-tag">{{ tag.name }}</span>
              </div>

              <div class="hv-detail-grid">
                <div class="hv-detail-item">
                  <span class="hv-detail-label">价格区间</span>
                  <span
                    >{{ worker.min_price ?? "-" }} ~
                    {{ worker.max_price ?? "-" }} 元</span
                  >
                </div>
                <div class="hv-detail-item">
                  <span class="hv-detail-label">完成任务</span>
                  <span>{{ worker.worker_completed_count }} 单</span>
                </div>
                <div class="hv-detail-item">
                  <span class="hv-detail-label">被拉黑</span>
                  <span>{{ worker.blocked_by_count }} 次</span>
                </div>
              </div>

              <p v-if="worker.bio" class="hv-worker-bio">{{ worker.bio }}</p>
            </div>

            <div class="hv-drawer__section">
              <h4 class="hv-drawer__subtitle">
                <i class="fa-regular fa-star"></i> 历史评价
              </h4>
              <div v-if="reviews.length" class="hv-reviews">
                <div v-for="r in reviews" :key="r.id" class="hv-review">
                  <div class="hv-review__header">
                    <HomeStars size="sm" :value="r.stars" />
                    <span class="hv-review-meta"
                      >来自 {{ r.reviewer_display_name }} ·
                      {{ formatFull(r.created_at) }}</span
                    >
                  </div>
                  <p v-if="r.comment" class="hv-review__comment">
                    {{ r.comment }}
                  </p>
                </div>
              </div>
              <p v-else class="hv-section-hint">该接单者暂无历史评价</p>
            </div>

            <div v-if="contactReveal" class="hv-drawer__section">
              <h4 class="hv-drawer__subtitle">
                <i class="fa-solid fa-address-book"></i> 联系方式
              </h4>
              <div class="hv-contact-card">
                <div class="hv-contact-row">
                  <span>手机号</span>
                  <strong>{{ contactReveal.phone || "未填写" }}</strong>
                </div>
                <div class="hv-contact-row">
                  <span>微信号</span>
                  <strong>{{ contactReveal.wechat || "未填写" }}</strong>
                </div>
                <p class="hv-section-hint">
                  本次查看时间：{{ formatFull(contactReveal.viewed_at) }}
                </p>
              </div>
            </div>
          </div>

          <div class="hv-worker-footer">
            <AppDropdown
              v-model="selectedContactAction"
              :options="contactOptions"
              placement="top"
              width="100%"
              min-width="220px"
            >
              <template #trigger="{ toggle }">
                <button
                  class="btn btn-primary hv-contact-btn"
                  :disabled="revealLoading"
                  @click="toggle"
                >
                  <i class="fa-regular fa-comment-dots"></i>
                  {{ revealLoading ? "处理中..." : "联系 TA" }}
                </button>
              </template>
            </AppDropdown>
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
}

.hv-drawer__section {
  padding: 20px 24px;
  border-bottom: 1px solid var(--c-border-light);
}

.hv-worker-top {
  display: flex;
  align-items: center;
  gap: 14px;
}

.hv-worker-top__info h3 {
  margin: 0 0 4px;
}

.hv-worker-top__rating {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--c-text-muted);
  font-size: var(--text-sm);
}

.hv-worker-skill-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 12px;
}

.hv-worker-skill-tag {
  display: inline-block;
  padding: 4px 12px;
  border-radius: var(--radius-full);
  background: var(--c-accent-light);
  color: var(--c-accent);
  font-size: var(--text-sm);
  font-weight: 500;
}

.hv-detail-grid {
  margin-top: 14px;
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

.hv-worker-bio {
  margin: 12px 0 0;
  font-size: var(--text-sm);
  color: var(--c-text-secondary);
  line-height: 1.65;
}

.hv-drawer__subtitle {
  margin: 0 0 12px;
  font-size: var(--text-base);
  color: var(--c-text-secondary);
  display: flex;
  align-items: center;
  gap: 7px;
}

.hv-reviews {
  display: flex;
  flex-direction: column;
  gap: 10px;
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
  flex-wrap: wrap;
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

.hv-section-hint {
  color: var(--c-text-muted);
  font-size: var(--text-sm);
  margin: 0;
}

.hv-contact-card {
  padding: 10px 12px;
  background: var(--c-border-light);
  border-radius: var(--radius-md);
}

.hv-contact-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  font-size: var(--text-sm);
  margin-bottom: 6px;
}

.hv-contact-row strong {
  color: var(--c-accent);
}

.hv-worker-footer {
  border-top: 1px solid var(--c-border);
  padding: 12px 16px;
  background: var(--c-surface);
  position: sticky;
  bottom: 0;
}

.hv-contact-btn {
  width: 100%;
  border-radius: var(--radius-full);
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
  .hv-worker-detail-overlay {
    flex-direction: column;
    justify-content: flex-end;
    align-items: stretch;
  }

  .hv-worker-detail-drawer {
    width: 100% !important;
    height: auto !important;
    max-height: 92vh;
    border-radius: 16px 16px 0 0;
    box-shadow:
      0 80px 0 0 var(--c-surface),
      0 -4px 20px rgba(0, 0, 0, 0.1);
    overflow: hidden;
  }

  .hv-drawer__header .btn-ghost {
    display: none;
  }

  .hv-sheet-handle {
    display: flex;
  }

  .hv-detail-grid {
    grid-template-columns: 1fr;
  }

  .drawer-enter-from .hv-worker-detail-drawer,
  .drawer-leave-to .hv-worker-detail-drawer {
    transform: translateY(100%);
  }
}
</style>
