<script setup lang="ts">
import { computed } from 'vue'
import type { Task, Category } from '../../types/api'

const props = defineProps<{
  myAccepted: Task[]
  myPublished: Task[]
  categories: Category[]
}>()

// ---- UTC ISO → local Date ----
function parseUTC(iso: string): Date {
  if (!/Z|[+-]\d{2}:\d{2}$/.test(iso)) return new Date(iso + 'Z')
  return new Date(iso)
}

// ---- Overview tiles ----
const completedCount = computed(() =>
  props.myAccepted.filter(t => t.status === 'completed').length
)
const inProgressCount = computed(() =>
  props.myAccepted.filter(t => t.status === 'in_progress' || t.status === 'open').length
)
const publishedCount = computed(() => props.myPublished.length)

// ---- Week trend (本周任务接取数) ----
// 获取本周周一 00:00:00（本地时区）
function getWeekMonday(): Date {
  const now = new Date()
  const day = now.getDay() // 0=Sun, 1=Mon...6=Sat
  const diff = day === 0 ? -6 : 1 - day
  const mon = new Date(now.getFullYear(), now.getMonth(), now.getDate() + diff)
  mon.setHours(0, 0, 0, 0)
  return mon
}

const weekLabels = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']

function addToWeekCounts(counts: number[], iso: string) {
  const monday = getWeekMonday()
  const date = parseUTC(iso)
  const dayStart = new Date(date.getFullYear(), date.getMonth(), date.getDate())
  const diffDays = Math.round((dayStart.getTime() - monday.getTime()) / 86400000)
  if (diffDays >= 0 && diffDays <= 6) {
    const jsDay = date.getDay()
    const idx = jsDay === 0 ? 6 : jsDay - 1
    counts[idx]++
  }
}

const weekCounts = computed(() => {
  const counts = [0, 0, 0, 0, 0, 0, 0]
  // 接取的任务：用 updated_at 作为接取时间代理
  for (const task of props.myAccepted) {
    addToWeekCounts(counts, task.updated_at)
  }
  // 发布的任务：用 created_at 作为发布时间
  for (const task of props.myPublished) {
    addToWeekCounts(counts, task.created_at)
  }
  return counts
})

const chartMax = computed(() => Math.max(...weekCounts.value, 1))

// SVG 折线图参数
const SVG_W = 560
const SVG_H = 220
const PAD_L = 36
const PAD_R = 20
const PAD_T = 18
const PAD_B = 32

const xStep = computed(() => (SVG_W - PAD_L - PAD_R) / 6)

function chartX(i: number) {
  return PAD_L + i * xStep.value
}

function chartY(v: number) {
  return PAD_T + (1 - v / chartMax.value) * (SVG_H - PAD_T - PAD_B)
}

// 用三次贝塞尔曲线生成平滑折线 path
function smoothPath(counts: number[]): string {
  const pts = counts.map((v, i) => [chartX(i), chartY(v)] as [number, number])
  if (pts.length < 2) return ''
  let d = `M ${pts[0][0]},${pts[0][1]}`
  for (let i = 1; i < pts.length; i++) {
    const [x0, y0] = pts[i - 1]
    const [x1, y1] = pts[i]
    const cpX = (x0 + x1) / 2
    d += ` C ${cpX},${y0} ${cpX},${y1} ${x1},${y1}`
  }
  return d
}

const linePath = computed(() => smoothPath(weekCounts.value))

const areaPath = computed(() => {
  const counts = weekCounts.value
  const pts = counts.map((v, i) => [chartX(i), chartY(v)] as [number, number])
  if (pts.length < 2) return ''
  const bottom = SVG_H - PAD_B
  let d = `M ${pts[0][0]},${bottom} L ${pts[0][0]},${pts[0][1]}`
  for (let i = 1; i < pts.length; i++) {
    const [x0, y0] = pts[i - 1]
    const [x1, y1] = pts[i]
    const cpX = (x0 + x1) / 2
    d += ` C ${cpX},${y0} ${cpX},${y1} ${x1},${y1}`
  }
  d += ` L ${pts[pts.length - 1][0]},${bottom} Z`
  return d
})

// 纵轴刻度
const yTicks = computed(() => {
  const max = chartMax.value
  const step = max <= 4 ? 1 : Math.ceil(max / 4)
  const ticks: number[] = []
  for (let v = 0; v <= max; v += step) ticks.push(v)
  if (ticks[ticks.length - 1] < max) ticks.push(max)
  return ticks
})

// ---- Category stats ----
// 合并发布+接取，按 id 去重
const allMyTasks = computed(() => {
  const map = new Map<number, Task>()
  for (const t of props.myPublished) map.set(t.id, t)
  for (const t of props.myAccepted) map.set(t.id, t)
  return [...map.values()]
})

const categoryStats = computed(() => {
  const counts = new Map<number | null, number>()
  for (const t of allMyTasks.value) {
    counts.set(t.category_id, (counts.get(t.category_id) ?? 0) + 1)
  }
  const result: { name: string; count: number; color: string }[] = []
  const palette = ['#3b82f6', '#22c55e', '#a855f7', '#f97316', '#06b6d4', '#ec4899']

  let colorIdx = 0
  // 先处理有分类的
  for (const cat of props.categories) {
    const count = counts.get(cat.id) ?? 0
    if (count === 0) continue
    result.push({ name: cat.name, count, color: palette[colorIdx % palette.length] })
    colorIdx++
  }
  // 无分类
  const nocat = counts.get(null) ?? 0
  if (nocat > 0) {
    result.push({ name: '未分类', count: nocat, color: palette[colorIdx % palette.length] })
  }

  return result.sort((a, b) => b.count - a.count)
})

const catMax = computed(() => Math.max(...categoryStats.value.map(c => c.count), 1))

// 今天是本周第几天（0=周一...6=周日）
const todayWeekIdx = computed(() => {
  const day = new Date().getDay()
  return day === 0 ? 6 : day - 1
})
</script>

<template>
  <div class="hs-root">
    <div class="hs-layout">
    <div class="hs-left">
    <!-- ① 顶部三磁贴 -->
    <div class="hs-tiles">
      <div class="hs-tile">
        <span class="hs-tile__num hs-tile__num--blue">{{ completedCount }}</span>
        <span class="hs-tile__label">已完成</span>
      </div>
      <div class="hs-tile">
        <span class="hs-tile__num hs-tile__num--orange">{{ inProgressCount }}</span>
        <span class="hs-tile__label">进行中</span>
      </div>
      <div class="hs-tile">
        <span class="hs-tile__num hs-tile__num--green">{{ publishedCount }}</span>
        <span class="hs-tile__label">已发布</span>
      </div>
    </div>

    <!-- ② 折线图：本周任务趋势 -->
    <div class="hs-card hs-card--trend">
      <h3 class="hs-card__title">本周趋势</h3>
      <p class="hs-card__sub">发布任务按发布时间计，接取任务按接取时间计</p>
      <div class="hs-chart-wrap">
        <svg
          :viewBox="`0 0 ${SVG_W} ${SVG_H}`"
          class="hs-chart"
          aria-label="本周任务接取折线图"
        >
          <!-- 网格线 -->
          <line
            v-for="tick in yTicks"
            :key="tick"
            :x1="PAD_L"
            :y1="chartY(tick)"
            :x2="SVG_W - PAD_R"
            :y2="chartY(tick)"
            class="hs-chart__grid"
          />

          <!-- 面积填充 -->
          <path :d="areaPath" class="hs-chart__area" />

          <!-- 折线（平滑贝塞尔曲线） -->
          <path :d="linePath" class="hs-chart__line" />

          <!-- 数据点 + tooltip -->
          <g v-for="(v, i) in weekCounts" :key="i">
            <!-- 高亮今天 -->
            <circle
              v-if="i === todayWeekIdx"
              :cx="chartX(i)"
              :cy="chartY(v)"
              r="7"
              class="hs-chart__dot-halo"
            />
            <circle
              :cx="chartX(i)"
              :cy="chartY(v)"
              r="4"
              :class="['hs-chart__dot', { 'hs-chart__dot--today': i === todayWeekIdx }]"
            />
            <!-- 数值标签（非零时显示） -->
            <text
              v-if="v > 0"
              :x="chartX(i)"
              :y="chartY(v) - 10"
              class="hs-chart__val"
              text-anchor="middle"
            >{{ v }}</text>
          </g>

          <!-- 纵轴刻度标签 -->
          <text
            v-for="tick in yTicks"
            :key="'y' + tick"
            :x="PAD_L - 6"
            :y="chartY(tick) + 4"
            class="hs-chart__axis-label"
            text-anchor="end"
          >{{ tick }}</text>

          <!-- 横轴标签 -->
          <text
            v-for="(label, i) in weekLabels"
            :key="'x' + i"
            :x="chartX(i)"
            :y="SVG_H - 6"
            class="hs-chart__axis-label"
            :class="{ 'hs-chart__axis-label--today': i === todayWeekIdx }"
            text-anchor="middle"
          >{{ label }}</text>
        </svg>
      </div>
    </div>

    </div>
    <div class="hs-right">
    <!-- ③ 分类统计 -->
    <div class="hs-card hs-card--cat">
      <h3 class="hs-card__title">分类统计</h3>
      <div v-if="categoryStats.length" class="hs-cat-list">
        <div v-for="cat in categoryStats" :key="cat.name" class="hs-cat-item">
          <div class="hs-cat-item__header">
            <span class="hs-cat-item__name">{{ cat.name }}</span>
            <span class="hs-cat-item__count">{{ cat.count }}个任务</span>
          </div>
          <div class="hs-cat-bar-bg">
            <div
              class="hs-cat-bar-fill"
              :style="{
                width: (cat.count / catMax * 100) + '%',
                background: cat.color,
              }"
            ></div>
          </div>
        </div>
      </div>
      <p v-else class="hs-empty">暂无任务数据</p>
    </div>
    </div>
    </div>
  </div>
</template>

<style scoped>
.hs-root {
  padding: 28px 32px;
}

/* 两列 grid 布局：左列自适应，右列固定 320px */
.hs-layout {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 24px;
  /* 默认 align-items: stretch，两列等高 */
}

.hs-left {
  display: flex;
  flex-direction: column;
  gap: 20px;
  min-width: 0;
}

.hs-right {
  min-width: 0;
  display: flex;
  flex-direction: column;
}

/* 分类统计卡片撑满右列高度，内容可滚动 */
.hs-card--cat {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.hs-card--cat .hs-cat-list {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
}

.hs-card--cat .hs-cat-list::-webkit-scrollbar { width: 4px; }
.hs-card--cat .hs-cat-list::-webkit-scrollbar-thumb { background: transparent; border-radius: 2px; }
.hs-card--cat .hs-cat-list:hover::-webkit-scrollbar-thumb { background: var(--c-border); }

/* ---- 入场动画 ---- */
@keyframes hs-fade-up {
  from {
    opacity: 0;
    transform: translateY(22px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* ---- 磁贴 ---- */
.hs-tiles {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.hs-tile {
  background: var(--c-surface);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-sm);
  padding: 28px 24px 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  animation: hs-fade-up 0.48s cubic-bezier(0.22, 1, 0.36, 1) both;
}

.hs-tiles > .hs-tile:nth-child(1) { animation-delay: 0ms; }
.hs-tiles > .hs-tile:nth-child(2) { animation-delay: 90ms; }
.hs-tiles > .hs-tile:nth-child(3) { animation-delay: 180ms; }

.hs-tile__num {
  font-size: 52px;
  font-weight: 800;
  line-height: 1;
  letter-spacing: -1px;
}

.hs-tile__num--blue   { color: #3b82f6; }
.hs-tile__num--orange { color: #f97316; }
.hs-tile__num--green  { color: #22c55e; }

.hs-tile__label {
  font-size: var(--text-sm);
  color: var(--c-text-muted);
  font-weight: 500;
}

/* ---- 卡片 ---- */
.hs-card {
  background: var(--c-surface);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-sm);
  padding: 24px 28px;
  animation: hs-fade-up 0.48s cubic-bezier(0.22, 1, 0.36, 1) both;
}

.hs-card--trend { animation-delay: 270ms; }
.hs-card--cat   { animation-delay: 360ms; }

.hs-card__title {
  font-size: var(--text-lg);
  font-weight: 700;
  color: var(--c-text);
  margin-bottom: 2px;
}

.hs-card__sub {
  font-size: var(--text-xs);
  color: var(--c-text-muted);
  margin-bottom: 20px;
}

/* ---- 折线图 ---- */
.hs-chart-wrap {
  width: 100%;
  height: 220px;
  overflow-x: auto;
  flex-shrink: 0;
}

.hs-chart {
  width: 100%;
  height: 100%;
  display: block;
  overflow: hidden;
}

.hs-chart__grid {
  stroke: #f1f5f9;
  stroke-width: 1;
}

.hs-chart__area {
  fill: url(#areaGrad);
  fill: rgba(59, 130, 246, 0.08);
}

.hs-chart__line {
  fill: none;
  stroke: #3b82f6;
  stroke-width: 2.5;
  stroke-linejoin: round;
  stroke-linecap: round;
}

.hs-chart__dot {
  fill: #ffffff;
  stroke: #3b82f6;
  stroke-width: 2.5;
}

.hs-chart__dot--today {
  fill: #3b82f6;
  stroke: #3b82f6;
}

.hs-chart__dot-halo {
  fill: rgba(59, 130, 246, 0.15);
  stroke: none;
}

.hs-chart__val {
  font-size: 11px;
  font-weight: 700;
  fill: #3b82f6;
  font-family: var(--font-sans);
}

.hs-chart__axis-label {
  font-size: 11px;
  fill: #94a3b8;
  font-family: var(--font-sans);
}

.hs-chart__axis-label--today {
  fill: #3b82f6;
  font-weight: 700;
}

/* ---- 分类统计 ---- */
.hs-cat-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.hs-cat-item__header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 8px;
}

.hs-cat-item__name {
  font-size: var(--text-base);
  font-weight: 500;
  color: var(--c-text);
}

.hs-cat-item__count {
  font-size: var(--text-sm);
  color: var(--c-text-muted);
}

.hs-cat-bar-bg {
  height: 10px;
  background: #f1f5f9;
  border-radius: var(--radius-full);
  overflow: hidden;
}

.hs-cat-bar-fill {
  height: 100%;
  border-radius: var(--radius-full);
  transition: width 0.6s var(--ease);
}

.hs-empty {
  color: var(--c-text-muted);
  font-size: var(--text-sm);
  padding: 16px 0;
}

/* ---- 响应式 ---- */
@media (max-width: 900px) {
  .hs-layout {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 600px) {
  .hs-root {
    padding: 16px;
  }

  .hs-left {
    gap: 14px;
  }

  .hs-tile {
    padding: 20px 12px 16px;
    gap: 6px;
  }

  .hs-tile__num {
    font-size: 38px;
  }

  .hs-card {
    padding: 18px 16px;
  }
}
</style>
