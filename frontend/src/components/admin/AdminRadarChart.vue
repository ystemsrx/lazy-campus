<script setup lang="ts">
import { computed } from 'vue'

import type { AdminUserRadarMetrics } from '../../types/api'

const props = withDefaults(defineProps<{
  metrics: AdminUserRadarMetrics
  size?: number
}>(), {
  size: 260,
})

const labels = [
  { key: 'reliability', label: '信誉' },
  { key: 'activity', label: '活跃' },
  { key: 'cooperation', label: '协作' },
  { key: 'safety', label: '安全' },
  { key: 'growth', label: '成长' },
] as const

const center = computed(() => props.size / 2)
const radius = computed(() => (props.size / 2) * 0.72)

function polar(index: number, r: number) {
  const angle = ((Math.PI * 2) / labels.length) * index - Math.PI / 2
  return {
    x: center.value + Math.cos(angle) * r,
    y: center.value + Math.sin(angle) * r,
  }
}

const rings = [0.2, 0.4, 0.6, 0.8, 1]

const polygonPoints = computed(() => {
  return labels
    .map((item, idx) => {
      const value = props.metrics[item.key] ?? 0
      const p = polar(idx, radius.value * (value / 100))
      return `${p.x},${p.y}`
    })
    .join(' ')
})
</script>

<template>
  <div class="arc-wrap">
    <svg :width="size" :height="size" :viewBox="`0 0 ${size} ${size}`" class="arc-svg">
      <g>
        <polygon
          v-for="ring in rings"
          :key="ring"
          :points="labels.map((_, idx) => { const p = polar(idx, radius * ring); return `${p.x},${p.y}` }).join(' ')"
          class="arc-grid"
        />
      </g>
      <g>
        <line
          v-for="(_, idx) in labels"
          :key="`axis-${idx}`"
          :x1="center"
          :y1="center"
          :x2="polar(idx, radius).x"
          :y2="polar(idx, radius).y"
          class="arc-axis"
        />
      </g>
      <polygon :points="polygonPoints" class="arc-area" />
      <polyline :points="polygonPoints" class="arc-line" />

      <g>
        <circle
          v-for="(item, idx) in labels"
          :key="`dot-${item.key}`"
          :cx="polar(idx, radius * ((metrics[item.key] || 0) / 100)).x"
          :cy="polar(idx, radius * ((metrics[item.key] || 0) / 100)).y"
          r="3.4"
          class="arc-dot"
        />
      </g>
    </svg>

    <div
      v-for="(item, idx) in labels"
      :key="item.key"
      class="arc-label"
      :style="{ left: `${polar(idx, radius * 1.12).x}px`, top: `${polar(idx, radius * 1.12).y}px` }"
    >
      <span>{{ item.label }}</span>
      <strong>{{ metrics[item.key] || 0 }}</strong>
    </div>
  </div>
</template>

<style scoped>
.arc-wrap {
  position: relative;
  width: fit-content;
  margin: 0 auto;
}

.arc-svg {
  display: block;
}

.arc-grid {
  fill: none;
  stroke: #dbe6f3;
  stroke-width: 1;
}

.arc-axis {
  stroke: #e4edf7;
  stroke-width: 1;
}

.arc-area {
  fill: rgba(29, 78, 216, 0.18);
}

.arc-line {
  fill: none;
  stroke: #1d4ed8;
  stroke-width: 2;
}

.arc-dot {
  fill: #1d4ed8;
  stroke: #fff;
  stroke-width: 1.5;
}

.arc-label {
  position: absolute;
  transform: translate(-50%, -50%);
  pointer-events: none;
  text-align: center;
  line-height: 1.1;
}

.arc-label span {
  font-size: 11px;
  color: #5e7188;
  display: block;
}

.arc-label strong {
  font-size: 12px;
  color: #0f172a;
}
</style>
