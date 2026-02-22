<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { fetchBlacklist, unblockUser } from '../../api/moderation'
import type { BlacklistItem } from '../../types/api'
import { formatFull } from '../../utils/time'
import HomeAvatar from '../home/ui/HomeAvatar.vue'

const props = defineProps<{
  active: boolean
}>()

const emit = defineEmits<{
  (e: 'toast', message: string, type: 'success' | 'error' | 'info'): void
}>()

const items = ref<BlacklistItem[]>([])
const loading = ref(false)
const removing = ref<number | null>(null)

async function load() {
  loading.value = true
  try {
    items.value = await fetchBlacklist()
  } catch {
    emit('toast', '加载黑名单失败', 'error')
  } finally {
    loading.value = false
  }
}

async function handleUnblock(userId: number) {
  removing.value = userId
  try {
    await unblockUser(userId)
    items.value = items.value.filter((i) => i.blocked_user_id !== userId)
    emit('toast', '已取消拉黑', 'success')
  } catch {
    emit('toast', '操作失败', 'error')
  } finally {
    removing.value = null
  }
}

onMounted(() => {
  load()
})
</script>

<template>
  <div class="sv-tab-pane" :class="{ 'sv-tab-pane--active': active }">
    <div class="sv-section-header">
      <h2 class="sv-section-title">黑名单</h2>
      <p class="sv-section-desc">管理被你拉黑的用户，拉黑后双方将无法看到对方的任务和接单信息</p>
    </div>

    <div class="sv-blacklist-divider" />

    <div v-if="loading" class="sv-blacklist-loading">
      <div v-for="i in 3" :key="i" class="sv-blacklist-skel">
        <div class="sv-skel sv-skel--avatar-sm" />
        <div class="sv-skel-lines">
          <div class="sv-skel sv-skel--line-md" />
          <div class="sv-skel sv-skel--line-sm" />
        </div>
      </div>
    </div>

    <div v-else-if="items.length === 0" class="sv-blacklist-empty">
      <i class="fa-regular fa-face-smile"></i>
      <p>黑名单为空</p>
    </div>

    <div v-else class="sv-blacklist-list">
      <div v-for="item in items" :key="item.blocked_user_id" class="sv-blacklist-item">
        <HomeAvatar
          size="md"
          :avatar-url="item.blocked_avatar_url"
          :gender="null"
          alt="avatar"
        />
        <div class="sv-blacklist-item__info">
          <span class="sv-blacklist-item__name">{{ item.blocked_display_name }}</span>
          <span class="sv-blacklist-item__meta">
            {{ formatFull(item.created_at) }} 拉黑
            <template v-if="item.reason"> · {{ item.reason }}</template>
          </span>
        </div>
        <button
          class="btn btn-outline btn-sm sv-blacklist-item__btn"
          :disabled="removing === item.blocked_user_id"
          @click="handleUnblock(item.blocked_user_id)"
        >
          {{ removing === item.blocked_user_id ? '处理中...' : '取消拉黑' }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.sv-tab-pane {
  position: absolute;
  inset: 0;
  width: 100%;
  opacity: 0;
  transform: translateY(16px);
  pointer-events: none;
  z-index: 0;
  transition: opacity 500ms ease-in-out, transform 500ms ease-in-out;
}

.sv-tab-pane--active {
  position: relative;
  opacity: 1;
  transform: translateY(0);
  pointer-events: auto;
  z-index: 1;
}

.sv-section-header {
  margin-bottom: 0;
}

.sv-section-title {
  font-size: var(--text-xl);
  font-weight: 700;
  margin: 0 0 4px;
}

.sv-section-desc {
  color: var(--c-text-muted);
  font-size: var(--text-sm);
  margin: 0;
}

.sv-blacklist-divider {
  height: 1px;
  background: var(--c-border-light);
  margin: 16px 0;
}

.sv-blacklist-loading {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.sv-blacklist-skel {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 0;
}

.sv-skel {
  background: var(--c-border-light);
  border-radius: var(--radius-md);
  animation: skel-pulse 1.5s ease-in-out infinite;
}

.sv-skel--avatar-sm {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  flex-shrink: 0;
}

.sv-skel-lines {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.sv-skel--line-md {
  height: 14px;
  width: 120px;
}

.sv-skel--line-sm {
  height: 12px;
  width: 180px;
}

@keyframes skel-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.sv-blacklist-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 48px 0;
  color: var(--c-text-muted);
  font-size: var(--text-sm);
}

.sv-blacklist-empty i {
  font-size: 32px;
  opacity: 0.5;
}

.sv-blacklist-empty p {
  margin: 0;
}

.sv-blacklist-list {
  display: flex;
  flex-direction: column;
}

.sv-blacklist-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px solid var(--c-border-light);
}

.sv-blacklist-item:last-child {
  border-bottom: none;
}

.sv-blacklist-item__info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.sv-blacklist-item__name {
  font-weight: 600;
  font-size: var(--text-sm);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sv-blacklist-item__meta {
  color: var(--c-text-muted);
  font-size: var(--text-xs);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sv-blacklist-item__btn {
  flex-shrink: 0;
  border-color: #fca5a5;
  color: #ef4444;
}

.sv-blacklist-item__btn:hover:not(:disabled) {
  background: #fff1f2;
}
</style>
