<script setup lang="ts">
import { ClipboardList, Send } from 'lucide-vue-next'

defineProps<{
  modelValue: 'assignee' | 'publisher'
  assigneeTotal: number
  assigneeProgress: number
  publisherTotal: number
  publisherPending: number
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: 'assignee' | 'publisher'): void
}>()
</script>

<template>
  <div class="tm-role-switcher tm-anim-1">
    <button
      class="tm-role-btn"
      :class="{ 'tm-role-btn--active': modelValue === 'assignee' }"
      @click="emit('update:modelValue', 'assignee')"
    >
      <div class="tm-role-btn__icon">
        <ClipboardList :size="20" />
      </div>
      <div class="tm-role-btn__body">
        <span class="tm-role-btn__label">我接取的<span class="tm-role-btn__total">({{ assigneeTotal }})</span></span>
        <span class="tm-role-btn__count">{{ assigneeProgress }} 进行中</span>
      </div>
    </button>

    <button
      class="tm-role-btn"
      :class="{ 'tm-role-btn--active': modelValue === 'publisher' }"
      @click="emit('update:modelValue', 'publisher')"
    >
      <div class="tm-role-btn__icon">
        <Send :size="20" />
      </div>
      <div class="tm-role-btn__body">
        <span class="tm-role-btn__label">我发布的<span class="tm-role-btn__total">({{ publisherTotal }})</span></span>
        <span class="tm-role-btn__count">{{ publisherPending }} 待接取</span>
      </div>
    </button>
  </div>
</template>

<style scoped>
@keyframes tm-rise {
  from {
    opacity: 0;
    transform: translateY(20px);
  }

  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.tm-anim-1 {
  animation: tm-rise 0.5s ease-out 0ms both;
}

.tm-role-switcher {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
  margin-bottom: 24px;
}

.tm-role-btn {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 18px 20px;
  border-radius: 20px;
  border: 2px solid transparent;
  background: #ffffff;
  cursor: pointer;
  transition: all 0.25s var(--ease);
  text-align: left;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.04);
  font-family: var(--font-sans);
  min-width: 0;
  overflow: hidden;
}

.tm-role-btn:hover {
  border-color: var(--c-border);
  box-shadow: 0 4px 18px rgba(0, 0, 0, 0.08);
}

.tm-role-btn--active {
  border-color: var(--c-accent);
  background: var(--c-accent-light);
  box-shadow: 0 4px 18px rgba(0, 0, 0, 0.08);
}

.tm-role-btn__icon {
  width: 46px;
  height: 46px;
  border-radius: 14px;
  background: var(--c-border-light);
  color: var(--c-text-muted);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all 0.25s var(--ease);
}

.tm-role-btn--active .tm-role-btn__icon {
  background: var(--c-accent);
  color: #ffffff;
}

.tm-role-btn__body {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.tm-role-btn__label {
  font-size: 15px;
  font-weight: 700;
  color: var(--c-text);
  display: block;
}

.tm-role-btn__total {
  font-size: 13px;
  font-weight: 500;
  color: var(--c-text-muted);
  margin-left: 3px;
}

.tm-role-btn--active .tm-role-btn__label {
  color: var(--c-accent);
}

.tm-role-btn__count {
  font-size: 12px;
  color: var(--c-text-muted);
  font-weight: 500;
  display: block;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

@media (max-width: 900px) {
  .tm-role-switcher {
    gap: 10px;
  }

  .tm-role-btn {
    padding: 14px 14px;
    gap: 10px;
    border-radius: 16px;
  }

  .tm-role-btn__icon {
    width: 38px;
    height: 38px;
    border-radius: 11px;
  }

  .tm-role-btn__label {
    font-size: 14px;
  }

  .tm-role-btn__count {
    font-size: 11px;
  }
}
</style>
