<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { Megaphone, Pin } from "lucide-vue-next";

import ChatRichTextRenderer from "./chat/ChatRichTextRenderer.vue";
import HomeModal from "./home/ui/HomeModal.vue";
import { useAuthStore } from "../stores/auth";
import { useNotificationStore } from "../stores/notifications";
import { formatFull } from "../utils/time";

const route = useRoute();
const authStore = useAuthStore();
const notifStore = useNotificationStore();

const checkedUserId = ref<number | null>(null);
const checkingAuto = ref(false);

const activeAnnouncement = computed(() => notifStore.activeAnnouncement);

const canAutoCheck = computed(
  () =>
    authStore.isAuthenticated &&
    authStore.role === "user" &&
    authStore.profileCompleted &&
    route.path !== "/login" &&
    route.path !== "/complete-profile",
);

async function checkAutoAnnouncement() {
  if (!canAutoCheck.value || checkingAuto.value) return;
  const uid = authStore.user?.id ?? null;
  if (!uid || checkedUserId.value === uid) return;

  checkingAuto.value = true;
  try {
    await notifStore.load();
    const unreadAnnouncement = notifStore.notifications.find(
      (item) => item.type === "admin_announcement" && !item.is_read,
    );
    if (unreadAnnouncement) {
      notifStore.openAnnouncement(unreadAnnouncement, { markRead: true });
    }
    checkedUserId.value = uid;
  } finally {
    checkingAuto.value = false;
  }
}

function closeAnnouncement() {
  notifStore.closeAnnouncement();
}

watch(
  () => [canAutoCheck.value, authStore.user?.id] as const,
  ([enabled]) => {
    if (!enabled) return;
    checkAutoAnnouncement().catch(() => {});
  },
  { immediate: true },
);

watch(
  () => authStore.isAuthenticated,
  (authed) => {
    if (authed) return;
    checkedUserId.value = null;
    notifStore.closeAnnouncement();
  },
);

watch(
  () => authStore.user?.id,
  (next, prev) => {
    if (next === prev) return;
    checkedUserId.value = null;
  },
);

onMounted(() => {
  checkAutoAnnouncement().catch(() => {});
});
</script>

<template>
  <HomeModal
    :model-value="Boolean(activeAnnouncement)"
    title="公告"
    width="min(760px, 94vw)"
    body-class="announce__body"
    @update:model-value="
      (val) => {
        if (!val) closeAnnouncement();
      }
    "
  >
    <template #header>
      <div class="announce__head">
        <div class="announce__head-left">
          <span class="announce__icon">
            <Megaphone :size="16" />
          </span>
          <div class="announce__title-wrap">
            <div class="announce__title-line">
              <h3 class="announce__title">
                {{ activeAnnouncement?.title || "平台公告" }}
              </h3>
              <span
                v-if="activeAnnouncement?.dismiss_type === 'persistent'"
                class="announce__pin-tag"
              >
                <Pin :size="12" />
                置顶
              </span>
            </div>
            <p v-if="activeAnnouncement" class="announce__meta">
              发布时间：{{ formatFull(activeAnnouncement.created_at) }}
            </p>
          </div>
        </div>
      </div>
    </template>

    <div v-if="activeAnnouncement" class="announce__content">
      <div class="announce__content-rich">
        <ChatRichTextRenderer
          :content="activeAnnouncement.description || '暂无公告正文。'"
        />
      </div>

      <div class="announce__foot">
        <p
          v-if="activeAnnouncement.dismiss_type === 'persistent'"
          class="announce__tip"
        >
          该公告已置顶，你仍可在右上角通知中心再次查看。
        </p>
        <button
          class="btn btn-primary announce__ack-btn"
          @click="closeAnnouncement"
        >
          我知道了
        </button>
      </div>
    </div>
  </HomeModal>
</template>

<style scoped>
.announce__head {
  display: flex;
  align-items: center;
  gap: 10px;
}

.announce__head-left {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 10px;
}

.announce__icon {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  background: rgba(124, 58, 237, 0.12);
  color: #7c3aed;
  display: grid;
  place-items: center;
  flex-shrink: 0;
}

.announce__title-wrap {
  min-width: 0;
}

.announce__title-line {
  display: flex;
  align-items: center;
  gap: 8px;
}

.announce__title {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  color: #1f2937;
  line-height: 1.25;
}

.announce__meta {
  margin: 3px 0 0;
  font-size: 12px;
  color: #6b7280;
}

.announce__pin-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
  color: #7c3aed;
  background: rgba(124, 58, 237, 0.12);
  border: 1px solid rgba(124, 58, 237, 0.22);
  flex-shrink: 0;
  line-height: 1.2;
}

.announce__content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.announce__content-rich {
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  background: #fff;
  padding: 14px 16px;
  max-height: 56vh;
  overflow: auto;
}

.announce__content-rich :deep(.rich-text) {
  font-size: 14px;
  line-height: 1.7;
  color: #1f2937;
}

.announce__content-rich :deep(.rich-text p) {
  margin: 0 0 10px;
}

.announce__content-rich :deep(.rich-text p:last-child) {
  margin-bottom: 0;
}

.announce__content-rich :deep(.rich-text ul),
.announce__content-rich :deep(.rich-text ol) {
  margin: 8px 0 10px;
  padding-left: 20px;
}

.announce__content-rich :deep(.rich-text blockquote) {
  margin: 10px 0;
  padding: 8px 12px;
  border-left: 3px solid #a78bfa;
  background: #f5f3ff;
  color: #5b21b6;
  border-radius: 0 10px 10px 0;
}

.announce__content-rich :deep(.rich-text pre) {
  margin: 10px 0;
  border-radius: 12px;
  background: #0f172a;
}

.announce__content-rich :deep(.rich-text code) {
  font-family:
    "JetBrains Mono", "Fira Code", ui-monospace, SFMono-Regular, Menlo,
    Consolas, monospace;
}

.announce__content-rich :deep(.rich-text a) {
  color: #2563eb;
}

.announce__content-rich :deep(.rich-text img) {
  display: block;
  width: 40%;
  max-width: 40%;
  height: auto;
  margin: 10px auto;
  border-radius: 10px;
}

.announce__foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.announce__tip {
  margin: 0;
  font-size: 12px;
  color: #6b7280;
}

.announce__ack-btn {
  min-width: 112px;
}

@media (max-width: 640px) {
  .announce__content-rich {
    max-height: 48vh;
  }

  .announce__foot {
    flex-direction: column;
    align-items: stretch;
  }

  .announce__ack-btn {
    width: 100%;
  }
}
</style>
