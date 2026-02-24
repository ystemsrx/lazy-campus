<script setup lang="ts">
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import { Ban, CheckCircle2, ClipboardList, Clock } from 'lucide-vue-next'

const props = defineProps<{
  activeRole: 'assignee' | 'publisher'
  modelValue: 'pending' | 'progress' | 'completed' | 'canceled'
  publisherPending: number
  canceledCount: number
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: 'pending' | 'progress' | 'completed' | 'canceled'): void
}>()

const ASSIGNEE_TABS = [
  { value: 'progress' as const, label: '进行中', icon: Clock,         color: '#3b82f6' },
  { value: 'completed' as const, label: '已完成', icon: CheckCircle2, color: '#22c55e' },
]

const PUBLISHER_TABS = [
  { value: 'pending'   as const, label: '待接取', icon: ClipboardList, color: '#f59e0b' },
  { value: 'progress'  as const, label: '进行中', icon: Clock,         color: '#3b82f6' },
  { value: 'completed' as const, label: '已完成', icon: CheckCircle2,  color: '#22c55e' },
  { value: 'canceled'  as const, label: '已取消', icon: Ban,           color: '#94a3b8' },
]

const tabs = computed(() => props.activeRole === 'assignee' ? ASSIGNEE_TABS : PUBLISHER_TABS)
const activeIndex = computed(() => {
  const idx = tabs.value.findIndex(t => t.value === props.modelValue)
  return idx === -1 ? 0 : idx
})
const activeColor = computed(() => tabs.value[activeIndex.value]?.color ?? '#3b82f6')

const containerRef = ref<HTMLElement | null>(null)
const btnRefs = ref<(HTMLElement | null)[]>([])
const isAnimating = ref(false)
const sliderStyle = ref<Record<string, string>>({
  left: '4px',
  top: '4px',
  width: '0px',
  height: '0px',
  backgroundColor: '#3b82f6',
})

function updateSlider(animate = true) {
  const container = containerRef.value
  const btn = btnRefs.value[activeIndex.value]
  if (!container || !btn) return
  const cr = container.getBoundingClientRect()
  const br = btn.getBoundingClientRect()
  isAnimating.value = animate
  sliderStyle.value = {
    left: `${br.left - cr.left}px`,
    top: `${br.top - cr.top}px`,
    width: `${br.width}px`,
    height: `${br.height}px`,
    backgroundColor: activeColor.value,
  }
}

watch(() => props.modelValue, async () => {
  await nextTick()
  updateSlider(true)
})

watch(() => props.activeRole, async () => {
  await nextTick()
  updateSlider(false)
})

onMounted(async () => {
  await nextTick()
  updateSlider(false)
  requestAnimationFrame(() => { isAnimating.value = true })
})
</script>

<template>
  <div
    ref="containerRef"
    class="tm-status-tabs tm-anim-2"
    :class="{ 'tm-has-four': tabs.length === 4 }"
  >
    <div
      class="tm-status-slider"
      :class="{ 'tm-status-slider--animated': isAnimating }"
      :style="sliderStyle"
    />

    <button
      v-for="(tab, i) in tabs"
      :key="tab.value"
      :ref="(el) => { btnRefs[i] = el as HTMLElement | null }"
      class="tm-status-tab"
      :class="{ 'tm-status-tab--active': modelValue === tab.value }"
      @click="emit('update:modelValue', tab.value)"
    >
      <component :is="tab.icon" :size="15" />
      <span>{{ tab.label }}</span>
      <span v-if="tab.value === 'pending' && publisherPending" class="tm-tab-badge">
        {{ publisherPending > 99 ? '99+' : publisherPending }}
      </span>
      <span v-if="tab.value === 'canceled' && canceledCount" class="tm-tab-badge tm-tab-badge--muted">
        {{ canceledCount > 99 ? '99+' : canceledCount }}
      </span>
    </button>
  </div>
</template>

<style scoped>
@keyframes tm-rise {
  from { opacity: 0; transform: translateY(20px); }
  to   { opacity: 1; transform: translateY(0); }
}

.tm-anim-2 {
  animation: tm-rise 0.5s ease-out 0.12s both;
}

.tm-status-tabs {
  position: relative;
  display: flex;
  background: #f1f5f9;
  border-radius: 14px;
  padding: 4px;
  gap: 0;
  margin-bottom: 24px;
  overflow: visible;
}

.tm-status-slider {
  position: absolute;
  border-radius: 11px;
  pointer-events: none;
  z-index: 0;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.18);
}

.tm-status-slider--animated {
  transition:
    left            0.32s cubic-bezier(0.16, 1, 0.3, 1),
    top             0.32s cubic-bezier(0.16, 1, 0.3, 1),
    width           0.32s cubic-bezier(0.16, 1, 0.3, 1),
    height          0.32s cubic-bezier(0.16, 1, 0.3, 1),
    background-color 0.32s ease;
}

.tm-status-tab {
  flex: 1;
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 10px 12px;
  border: none;
  background: transparent;
  color: var(--c-text-muted);
  font-size: 13px;
  font-weight: 600;
  font-family: var(--font-sans);
  cursor: pointer;
  transition: color 0.25s ease;
  border-radius: 11px;
  white-space: nowrap;
}

.tm-status-tab--active {
  color: #ffffff;
}

.tm-tab-badge {
  position: absolute;
  top: -6px;
  right: -4px;
  min-width: 18px;
  height: 18px;
  padding: 0 4px;
  border-radius: 9px;
  background: #ef4444;
  color: #ffffff;
  font-size: 10px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
  border: 2px solid #f1f5f9;
  pointer-events: none;
  z-index: 2;
}

.tm-tab-badge--muted {
  background: #94a3b8;
}

/* 移动端 publisher 四选项改为 2×2 */
@media (max-width: 900px) {
  .tm-status-tabs.tm-has-four {
    flex-wrap: wrap;
  }

  .tm-status-tabs.tm-has-four .tm-status-tab {
    flex: 0 0 50%;
    box-sizing: border-box;
  }
}
</style>
