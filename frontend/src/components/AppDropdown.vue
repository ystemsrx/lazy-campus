<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'

export interface DropdownOption {
  value: string | number | null
  label: string
  disabled?: boolean
}

const props = withDefaults(defineProps<{
  modelValue: string | number | null | undefined
  options: DropdownOption[]
  placeholder?: string
  minWidth?: string
  width?: string
  placement?: 'top' | 'bottom'
}>(), {
  placeholder: '请选择',
  minWidth: '120px',
  width: '100%',
  placement: 'bottom',
})

const emit = defineEmits<{
  'update:modelValue': [value: string | number | null]
}>()

const isOpen = ref(false)
const dropdownRef = ref<HTMLElement | null>(null)

const selectedLabel = computed(() => {
  const found = props.options.find(o => o.value === props.modelValue)
  return found ? found.label : props.placeholder
})

const hasValue = computed(() => {
  return props.modelValue !== null && props.modelValue !== undefined && props.modelValue !== ''
})

function toggle() {
  isOpen.value = !isOpen.value
}

function select(opt: DropdownOption) {
  if (opt.disabled) return
  emit('update:modelValue', opt.value)
  isOpen.value = false
}

function onClickOutside(e: MouseEvent) {
  if (dropdownRef.value && !dropdownRef.value.contains(e.target as Node)) {
    isOpen.value = false
  }
}

onMounted(() => document.addEventListener('mousedown', onClickOutside))
onUnmounted(() => document.removeEventListener('mousedown', onClickOutside))
</script>

<template>
  <div
    ref="dropdownRef"
    class="app-dropdown"
    :class="{ 'app-dropdown--open': isOpen, 'app-dropdown--top': placement === 'top' }"
    :style="{ width: props.width, minWidth: props.minWidth }"
  >
    <slot name="trigger" :toggle="toggle" :is-open="isOpen">
      <button type="button" class="app-dropdown__trigger" @click="toggle">
        <span class="app-dropdown__label" :class="{ 'app-dropdown__label--placeholder': !hasValue }">
          {{ selectedLabel }}
        </span>
        <span class="app-dropdown__chevron">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M3 5L7 9L11 5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </span>
      </button>
    </slot>

    <Transition :name="placement === 'top' ? 'app-dropdown-up' : 'app-dropdown'">
      <div v-if="isOpen" class="app-dropdown__menu">
        <button
          v-for="opt in options"
          :key="String(opt.value)"
          type="button"
          class="app-dropdown__item"
          :class="{ 'app-dropdown__item--active': opt.value === modelValue, 'app-dropdown__item--disabled': opt.disabled }"
          :disabled="opt.disabled"
          @click="select(opt)"
        >
          <span>{{ opt.label }}</span>
          <svg
            v-if="opt.value === modelValue"
            width="13"
            height="13"
            viewBox="0 0 13 13"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            class="app-dropdown__check"
          >
            <path d="M2 6.5L5.2 10L11 3" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </button>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.app-dropdown {
  position: relative;
  display: inline-block;
  min-width: 0;
}

/* ── 触发按钮 ── */
.app-dropdown__trigger {
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
  min-width: 0;
  overflow: hidden;
}

@media (hover: hover) {
  .app-dropdown__trigger:hover {
    background: #f8fafc;
    box-shadow: var(--shadow-md);
  }
}

.app-dropdown--open .app-dropdown__trigger {
  background: #f8fafc;
  box-shadow: 0 0 0 2.5px var(--c-accent-soft), var(--shadow-md);
}

/* ── 标签 ── */
.app-dropdown__label {
  flex: 1;
  text-align: left;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--c-text);
}
.app-dropdown__label--placeholder {
  color: var(--c-text-muted);
}

/* ── 箭头图标 ── */
.app-dropdown__chevron {
  display: flex;
  align-items: center;
  color: var(--c-text-muted);
  transition: transform var(--dur-normal) var(--ease);
  flex-shrink: 0;
}
.app-dropdown--open .app-dropdown__chevron {
  transform: rotate(180deg);
}

/* ── 弹出菜单 ── */
.app-dropdown__menu {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  min-width: 100%;
  background: #ffffff;
  border: none;
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xl);
  z-index: 1000;
  overflow: hidden;
  padding: 5px;
  transform-origin: top center;
}

.app-dropdown--top .app-dropdown__menu {
  top: auto;
  bottom: calc(100% + 6px);
  transform-origin: bottom center;
}

/* ── 选项 ── */
.app-dropdown__item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  width: 100%;
  padding: 8px 11px;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--c-text);
  font-size: var(--text-base);
  font-family: var(--font-sans);
  cursor: pointer;
  text-align: left;
  white-space: nowrap;
  transition: background var(--dur-fast) var(--ease), color var(--dur-fast) var(--ease);
}

@media (hover: hover) {
  .app-dropdown__item:hover {
    background: var(--c-accent-light);
    color: var(--c-accent);
  }
}

.app-dropdown__item--active {
  background: var(--c-accent-light);
  color: var(--c-accent);
  font-weight: 500;
}

.app-dropdown__item--disabled {
  color: #94a3b8;
  cursor: not-allowed;
}

@media (hover: hover) {
  .app-dropdown__item--disabled:hover {
    background: transparent;
    color: #94a3b8;
  }
}

.app-dropdown__check {
  color: var(--c-accent);
  flex-shrink: 0;
}

/* ── 进出场动画（向下） ── */
.app-dropdown-enter-active {
  transition:
    opacity var(--dur-normal) var(--ease),
    transform var(--dur-normal) var(--ease);
}
.app-dropdown-leave-active {
  transition:
    opacity 180ms var(--ease),
    transform 180ms var(--ease);
}
.app-dropdown-enter-from {
  opacity: 0;
  transform: scaleY(0.88) translateY(-6px);
}
.app-dropdown-leave-to {
  opacity: 0;
  transform: scaleY(0.94) translateY(-3px);
}

/* ── 进出场动画（向上） ── */
.app-dropdown-up-enter-active {
  transition:
    opacity var(--dur-normal) var(--ease),
    transform var(--dur-normal) var(--ease);
}
.app-dropdown-up-leave-active {
  transition:
    opacity 180ms var(--ease),
    transform 180ms var(--ease);
}
.app-dropdown-up-enter-from {
  opacity: 0;
  transform: scaleY(0.88) translateY(6px);
}
.app-dropdown-up-leave-to {
  opacity: 0;
  transform: scaleY(0.94) translateY(3px);
}
</style>
