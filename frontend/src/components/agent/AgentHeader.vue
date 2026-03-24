<script setup lang="ts">
defineProps<{
  isMobile: boolean;
  logoUrl: string | null;
  title: string;
  statusText: string;
  isRunning: boolean;
  isQueued: boolean;
  isStalled: boolean;
  isError: boolean;
  deliverableCount: number;
}>();

const emit = defineEmits<{
  (e: "back"): void;
  (e: "open-deliverables"): void;
}>();
</script>

<template>
  <div class="agent-header">
    <div class="header-left">
      <button v-if="isMobile" class="icon-btn back-btn" @click="emit('back')">
        <i class="fa-solid fa-arrow-left"></i>
      </button>
      <div class="header-avatar">
        <img v-if="logoUrl" :src="logoUrl" alt="系统 Logo" class="header-avatar-img" />
        <i v-else class="fa-solid fa-robot"></i>
      </div>
      <div>
        <h2 class="header-title">{{ title }}</h2>
        <p
          class="header-status"
          :class="{
            'status-running': isRunning,
            'status-queued': isQueued,
            'status-stalled': isStalled,
            'status-error': isError,
          }"
        >
          {{ statusText }}
        </p>
      </div>
    </div>
    <div class="header-actions">
      <button class="icon-btn" title="交付文件" @click="emit('open-deliverables')">
        <i class="fa-solid fa-paperclip"></i>
        <span v-if="deliverableCount > 0" class="att-count-badge">{{
          deliverableCount
        }}</span>
      </button>
    </div>
  </div>
</template>

<style scoped>
.agent-header {
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--c-border, #e2e8f0);
  padding: 12px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
  z-index: 10;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.back-btn {
  margin-left: -8px;
}

.header-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: linear-gradient(135deg, #3b82f6, #8b5cf6);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 18px;
  flex-shrink: 0;
  overflow: hidden;
}

.header-avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.header-title {
  font-size: var(--text-base, 15px);
  font-weight: 700;
  color: var(--c-text, #1e293b);
  line-height: 1.2;
  margin: 0;
}

.header-status {
  font-size: 11px;
  color: var(--c-text-muted, #94a3b8);
  margin: 2px 0 0;
  line-height: 1.3;
}

.header-status.status-running {
  color: #3b82f6;
  font-weight: 500;
}

.header-status.status-queued {
  color: #d97706;
  font-weight: 500;
}

.header-status.status-stalled {
  color: #b45309;
  font-weight: 600;
}

.header-status.status-error {
  color: #dc2626;
  font-weight: 600;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 2px;
  flex-shrink: 0;
}

.icon-btn {
  padding: 8px;
  border-radius: 50%;
  background: transparent;
  border: none;
  color: var(--c-text-muted, #94a3b8);
  cursor: pointer;
  transition: all 0.15s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  font-size: 16px;
}

.icon-btn:hover {
  background: var(--c-bg, #f1f5f9);
  color: var(--c-text, #1e293b);
}

.att-count-badge {
  position: absolute;
  top: -2px;
  right: -2px;
  background: var(--c-accent, #2563eb);
  color: #fff;
  font-size: 9px;
  font-weight: 700;
  min-width: 16px;
  height: 16px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

@media (max-width: 768px) {
  .agent-header {
    padding: 12px 16px;
  }
}
</style>
