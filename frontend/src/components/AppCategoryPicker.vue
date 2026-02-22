<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

export interface CategoryOption {
  value: number | null
  label: string
}

const props = withDefaults(defineProps<{
  modelValue: number | null
  options: CategoryOption[]
  placeholder?: string
}>(), {
  placeholder: '选择类目',
})

const emit = defineEmits<{
  'update:modelValue': [value: number | null]
}>()

const isOpen = ref(false)
const pickerRef = ref<HTMLElement | null>(null)

function toggle() {
  isOpen.value = !isOpen.value
}

function select(opt: CategoryOption) {
  emit('update:modelValue', opt.value)
  isOpen.value = false
}

function selectedLabel(): string {
  const found = props.options.find(o => o.value === props.modelValue)
  return found ? found.label : props.placeholder
}

function onClickOutside(e: MouseEvent) {
  if (pickerRef.value && !pickerRef.value.contains(e.target as Node)) {
    isOpen.value = false
  }
}

onMounted(() => document.addEventListener('mousedown', onClickOutside))
onUnmounted(() => document.removeEventListener('mousedown', onClickOutside))
</script>

<template>
  <div ref="pickerRef" class="acp" :class="{ 'acp--open': isOpen }">
    <button type="button" class="acp__trigger" @click="toggle">
      <span class="acp__label" :class="{ 'acp__label--placeholder': modelValue === null }">
        {{ selectedLabel() }}
      </span>
      <span class="acp__chevron">
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
          <path d="M3 5L7 9L11 5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </span>
    </button>

    <Transition name="acp-pop">
      <div v-if="isOpen" class="acp__panel">
        <div class="acp__grid">
          <button
            v-for="opt in options"
            :key="String(opt.value)"
            type="button"
            class="acp__item"
            :class="{ 'acp__item--active': opt.value === modelValue }"
            @click="select(opt)"
          >
            {{ opt.label }}
          </button>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.acp {
  position: relative;
  display: inline-block;
  width: 100%;
}

.acp__trigger {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  width: 100%;
  padding: 9px 13px;
  background: #ffffff;
  border: none;
  border-radius: var(--radius-md);
  color: var(--c-text);
  font-size: var(--text-base);
  font-family: var(--font-sans);
  cursor: pointer;
  transition:
    background var(--dur-fast) var(--ease),
    box-shadow var(--dur-fast) var(--ease);
  box-shadow: var(--shadow-sm);
  user-select: none;
  white-space: nowrap;
}

@media (hover: hover) {
  .acp__trigger:hover {
    background: #f8fafc;
    box-shadow: var(--shadow-md);
  }
}

.acp--open .acp__trigger {
  background: #f8fafc;
  box-shadow: 0 0 0 2.5px var(--c-accent-soft), var(--shadow-md);
}

.acp__label {
  flex: 1;
  text-align: left;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--c-text);
}

.acp__label--placeholder {
  color: var(--c-text-muted);
}

.acp__chevron {
  display: flex;
  align-items: center;
  color: var(--c-text-muted);
  transition: transform var(--dur-normal) var(--ease);
  flex-shrink: 0;
}

.acp--open .acp__chevron {
  transform: rotate(180deg);
}

.acp__panel {
  position: absolute;
  top: calc(100% + 8px);
  left: 50%;
  transform: translateX(-50%);
  min-width: 280px;
  width: max-content;
  max-width: 360px;
  background: #ffffff;
  border-radius: 16px;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.12), 0 2px 8px rgba(0, 0, 0, 0.06);
  z-index: 1000;
  padding: 12px;
  transform-origin: top center;
}

.acp__grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.acp__item {
  padding: 9px 14px;
  border-radius: 999px;
  border: 1px solid var(--c-border);
  background: var(--c-surface);
  color: var(--c-text-secondary);
  font-size: var(--text-sm);
  font-family: var(--font-sans);
  cursor: pointer;
  text-align: center;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}

@media (hover: hover) {
  .acp__item:hover {
    border-color: var(--c-accent);
    color: var(--c-accent);
    background: var(--c-accent-light);
  }
}

.acp__item--active {
  background: var(--c-accent);
  border-color: var(--c-accent);
  color: #ffffff;
  font-weight: 500;
}

@media (hover: hover) {
  .acp__item--active:hover {
    background: var(--c-accent-hover);
    border-color: var(--c-accent-hover);
    color: #ffffff;
  }
}

/* Transition */
.acp-pop-enter-active {
  transition: opacity 0.28s ease, transform 0.32s cubic-bezier(0.16, 1, 0.3, 1);
}

.acp-pop-leave-active {
  transition: opacity 0.18s ease, transform 0.18s cubic-bezier(0.4, 0, 1, 1);
}

.acp-pop-enter-from {
  opacity: 0;
  transform: translateX(-50%) scale(0.88) translateY(-8px);
}

.acp-pop-leave-to {
  opacity: 0;
  transform: translateX(-50%) scale(0.94) translateY(-4px);
}

.acp-pop-enter-active .acp__item {
  animation: acp-item-in 0.3s cubic-bezier(0.16, 1, 0.3, 1) both;
}

@keyframes acp-item-in {
  from {
    opacity: 0;
    transform: translateY(6px) scale(0.95);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}
</style>
