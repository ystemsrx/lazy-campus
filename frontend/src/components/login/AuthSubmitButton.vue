<script setup lang="ts">
import { nextTick, onUnmounted, ref, watch } from 'vue'

const props = defineProps<{
  loading: boolean
}>()

const emit = defineEmits<{
  (e: 'click'): void
}>()

const spinnerCanvas = ref<HTMLCanvasElement | null>(null)
let spinnerAnimId = 0

function startSpinner() {
  const canvas = spinnerCanvas.value
  if (!canvas) return
  const ctx = canvas.getContext('2d') as CanvasRenderingContext2D
  if (!ctx) return

  const size = 56
  const dpr = window.devicePixelRatio || 1
  canvas.width = size * dpr
  canvas.height = size * dpr
  ctx.scale(dpr, dpr)

  let rotation = 0
  let points = 3
  let direction = 1

  const outerRadius = 23
  const innerRadiusRatio = 0.75

  function drawStar(cx: number, cy: number, numPoints: number, radius: number, innerRatio: number, rot: number) {
    const innerRadius = radius * innerRatio
    const step = Math.PI / numPoints
    ctx.beginPath()
    for (let i = 0; i < 2 * Math.ceil(numPoints); i++) {
      const r = i % 2 === 0 ? radius : innerRadius
      const theta = i * step + rot
      const x = cx + r * Math.cos(theta)
      const y = cy + r * Math.sin(theta)
      if (i === 0) ctx.moveTo(x, y)
      else ctx.lineTo(x, y)
    }
    ctx.closePath()
  }

  function animate() {
    ctx.clearRect(0, 0, size, size)

    ctx.fillStyle = '#1c1c1c'
    ctx.strokeStyle = '#1c1c1c'
    ctx.lineWidth = 4
    ctx.lineJoin = 'round'

    const shapeProgress = (points - 3) / 6
    const currentSpeed = 0.01 + 0.11 * Math.pow(shapeProgress, 2)
    rotation += currentSpeed

    drawStar(size / 2, size / 2, points, outerRadius, innerRadiusRatio, rotation - Math.PI / 2)
    ctx.fill()
    ctx.stroke()

    points += 0.02 * direction
    if (points >= 9) {
      points = 9
      direction = -1
    } else if (points <= 3) {
      points = 3
      direction = 1
    }

    spinnerAnimId = requestAnimationFrame(animate)
  }

  animate()
}

function stopSpinner() {
  if (spinnerAnimId) {
    cancelAnimationFrame(spinnerAnimId)
    spinnerAnimId = 0
  }
}

watch(
  () => props.loading,
  (loading) => {
    if (loading) nextTick(startSpinner)
    else stopSpinner()
  }
)

onUnmounted(() => {
  stopSpinner()
})
</script>

<template>
  <button
    class="av-submit-btn"
    :class="{ 'av-submit-btn--loading': loading }"
    :disabled="loading"
    @click="emit('click')"
  >
    <canvas ref="spinnerCanvas" class="av-submit-btn__canvas"></canvas>
    <i class="fa-solid fa-arrow-right"></i>
  </button>
</template>

<style scoped>
.av-submit-btn {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 64px;
  height: 40px;
  background: #1c1c1c;
  color: #fff;
  border: none;
  border-radius: 24px 12px 24px 12px;
  cursor: pointer;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
  transition: all 0.3s ease;
  overflow: hidden;
  flex-shrink: 0;
}
.av-submit-btn:hover:not(:disabled) {
  border-radius: 16px 20px 16px 20px;
  background: #000;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.25);
}
.av-submit-btn:hover:not(:disabled) i {
  transform: translateX(3px);
}
.av-submit-btn i {
  font-size: 15px;
  transition: transform 0.3s;
  position: relative;
  z-index: 1;
}
.av-submit-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.av-submit-btn--loading {
  background: transparent;
  box-shadow: none;
  overflow: visible;
  opacity: 1;
}
.av-submit-btn--loading:hover:not(:disabled) {
  background: transparent;
  box-shadow: none;
}
.av-submit-btn--loading:hover:not(:disabled) i {
  transform: none;
}
.av-submit-btn__canvas {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 56px;
  height: 56px;
  pointer-events: none;
  opacity: 0;
  transition: opacity 0.3s ease;
}
.av-submit-btn--loading .av-submit-btn__canvas {
  opacity: 1;
}
</style>
