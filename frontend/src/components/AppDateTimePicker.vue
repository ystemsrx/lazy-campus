<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'

const ITEM_H = 36
const DR = 4

const props = withDefaults(defineProps<{
  modelValue: string
  min?: string
  placeholder?: string
}>(), { placeholder: '选择时间', min: '' })

const emit = defineEmits<{ 'update:modelValue': [value: string] }>()

const isOpen = ref(false)
const activeTab = ref<'date' | 'time'>('date')
const tabDir = ref<'left' | 'right'>('left')
const pickerRef = ref<HTMLElement | null>(null)

const viewYear = ref(new Date().getFullYear())
const viewMonth = ref(new Date().getMonth())
const selDay = ref<number | null>(null)
const selHour = ref(new Date().getHours())
const selMinute = ref(0)

const hourDragY = ref(0)
const minuteDragY = ref(0)
const hDragging = ref(false)
const mDragging = ref(false)
const hSnapping = ref(false)
const mSnapping = ref(false)
let hStartY = 0
let mStartY = 0

function pad(n: number) { return String(n).padStart(2, '0') }
function mod(n: number, m: number) { return ((n % m) + m) % m }
function lerp(a: number, b: number, t: number) { return a + (b - a) * Math.min(Math.max(t, 0), 1) }

function parseVal(s: string): Date | null {
  if (!s) return null
  const d = new Date(s)
  return isNaN(d.getTime()) ? null : d
}

function syncFromModel() {
  const d = parseVal(props.modelValue)
  const base = d || new Date()
  viewYear.value = base.getFullYear()
  viewMonth.value = base.getMonth()
  selDay.value = d ? d.getDate() : null
  selHour.value = base.getHours()
  selMinute.value = base.getMinutes()
  hourDragY.value = 0; minuteDragY.value = 0
}

watch(() => isOpen.value, (v) => { if (v) { syncFromModel(); activeTab.value = 'date' } })

const displayText = computed(() => {
  const d = parseVal(props.modelValue)
  if (!d) return ''
  return `${d.getMonth() + 1}月${d.getDate()}日 ${pad(d.getHours())}:${pad(d.getMinutes())}`
})
const hasValue = computed(() => !!displayText.value)

function setTab(t: 'date' | 'time') {
  if (t === activeTab.value) return
  tabDir.value = t === 'time' ? 'left' : 'right'
  activeTab.value = t
  if (t === 'time') {
    hourDragY.value = 0; minuteDragY.value = 0
    hDragging.value = false; mDragging.value = false
    hSnapping.value = false; mSnapping.value = false
  }
}

// ── Calendar ──
const WKDAYS = ['日', '一', '二', '三', '四', '五', '六']
const monthLabel = computed(() => `${viewYear.value}年${viewMonth.value + 1}月`)
const daysInMonth = computed(() => new Date(viewYear.value, viewMonth.value + 1, 0).getDate())
const firstDow = computed(() => new Date(viewYear.value, viewMonth.value, 1).getDay())
const cells = computed(() => {
  const a: (number | null)[] = []
  for (let i = 0; i < firstDow.value; i++) a.push(null)
  for (let d = 1; d <= daysInMonth.value; d++) a.push(d)
  return a
})
function prevMonth() { viewMonth.value === 0 ? (viewYear.value--, viewMonth.value = 11) : viewMonth.value-- }
function nextMonth() { viewMonth.value === 11 ? (viewYear.value++, viewMonth.value = 0) : viewMonth.value++ }

const minDt = computed(() => props.min ? new Date(props.min) : null)
function dayOff(d: number) { return !!minDt.value && new Date(viewYear.value, viewMonth.value, d, 23, 59, 59) < minDt.value }
function dayToday(d: number) { const n = new Date(); return d === n.getDate() && viewMonth.value === n.getMonth() && viewYear.value === n.getFullYear() }
function daySel(d: number) { const p = parseVal(props.modelValue); return !!p && d === p.getDate() && viewMonth.value === p.getMonth() && viewYear.value === p.getFullYear() }
function pickDay(d: number) { if (dayOff(d)) return; selDay.value = d; doEmit() }

// ── Drum ──
const hourItems = computed(() => Array.from({ length: DR * 2 + 1 }, (_, i) => mod(selHour.value - DR + i, 24)))
const minuteItems = computed(() => Array.from({ length: DR * 2 + 1 }, (_, i) => mod(selMinute.value - DR + i, 60)))

function drumStyle(idx: number, dragY: number, dragging: boolean): Record<string, string> {
  const dist = Math.abs((idx - DR) + dragY / ITEM_H)
  const t = Math.min(dist / 2.5, 1)
  return {
    fontSize: `${lerp(21, 13, t)}px`,
    fontWeight: dist < 0.45 ? '700' : dist < 1.2 ? '600' : '400',
    opacity: `${lerp(1, 0.25, t)}`,
    color: dist < 0.45 ? 'var(--c-accent)' : dist < 1.4 ? 'var(--c-text-secondary)' : 'var(--c-text-muted)',
    transition: dragging ? 'none' : 'all 0.28s cubic-bezier(0.16, 1, 0.3, 1)',
  }
}

const drumHourCss = computed(() => ({
  transform: `translateY(${hourDragY.value}px)`,
  transition: hDragging.value ? 'none' : 'transform 0.3s cubic-bezier(0.16, 1, 0.3, 1)',
}))
const drumMinuteCss = computed(() => ({
  transform: `translateY(${minuteDragY.value}px)`,
  transition: mDragging.value ? 'none' : 'transform 0.3s cubic-bezier(0.16, 1, 0.3, 1)',
}))

function doEmit() {
  if (selDay.value == null) return
  emit('update:modelValue',
    `${viewYear.value}-${pad(viewMonth.value + 1)}-${pad(selDay.value)}T${pad(selHour.value)}:${pad(selMinute.value)}`)
}

/**
 * Animated shift: instantly update the value while setting a visual offset,
 * then smoothly animate the offset back to 0. Edge items that change are
 * hidden behind the fade gradients, so the switch is visually seamless.
 */
function animatedShiftH(d: number) {
  if (!d || hSnapping.value) return
  hDragging.value = true
  selHour.value = mod(selHour.value + d, 24)
  hourDragY.value = d * ITEM_H
  doEmit()
  nextTick(() => {
    void document.body.offsetHeight
    hDragging.value = false
    hourDragY.value = 0
  })
}
function animatedShiftM(d: number) {
  if (!d || mSnapping.value) return
  mDragging.value = true
  selMinute.value = mod(selMinute.value + d, 60)
  minuteDragY.value = d * ITEM_H
  doEmit()
  nextTick(() => {
    void document.body.offsetHeight
    mDragging.value = false
    minuteDragY.value = 0
  })
}

// ── Wheel (desktop) ──
function onHWheel(e: WheelEvent) {
  e.preventDefault()
  animatedShiftH(e.deltaY > 0 ? 1 : -1)
}
function onMWheel(e: WheelEvent) {
  e.preventDefault()
  animatedShiftM(e.deltaY > 0 ? 1 : -1)
}

// ── Touch drag: hour ──
function onHTouchStart(e: TouchEvent) {
  if (hSnapping.value) return
  hStartY = e.touches[0].clientY; hourDragY.value = 0; hDragging.value = true
}
function onHTouchMove(e: TouchEvent) {
  if (!hDragging.value) return
  hourDragY.value = e.touches[0].clientY - hStartY
  while (hourDragY.value > ITEM_H) {
    selHour.value = mod(selHour.value - 1, 24)
    hStartY += ITEM_H; hourDragY.value -= ITEM_H
  }
  while (hourDragY.value < -ITEM_H) {
    selHour.value = mod(selHour.value + 1, 24)
    hStartY -= ITEM_H; hourDragY.value += ITEM_H
  }
}
function onHTouchEnd() {
  if (!hDragging.value) return
  const steps = -Math.round(hourDragY.value / ITEM_H)
  const remainder = hourDragY.value + steps * ITEM_H
  selHour.value = mod(selHour.value + steps, 24)
  hourDragY.value = remainder
  doEmit()
  hSnapping.value = true
  nextTick(() => {
    void document.body.offsetHeight
    hDragging.value = false
    hourDragY.value = 0
    setTimeout(() => { hSnapping.value = false }, 320)
  })
}

// ── Touch drag: minute ──
function onMTouchStart(e: TouchEvent) {
  if (mSnapping.value) return
  mStartY = e.touches[0].clientY; minuteDragY.value = 0; mDragging.value = true
}
function onMTouchMove(e: TouchEvent) {
  if (!mDragging.value) return
  minuteDragY.value = e.touches[0].clientY - mStartY
  while (minuteDragY.value > ITEM_H) {
    selMinute.value = mod(selMinute.value - 1, 60)
    mStartY += ITEM_H; minuteDragY.value -= ITEM_H
  }
  while (minuteDragY.value < -ITEM_H) {
    selMinute.value = mod(selMinute.value + 1, 60)
    mStartY -= ITEM_H; minuteDragY.value += ITEM_H
  }
}
function onMTouchEnd() {
  if (!mDragging.value) return
  const steps = -Math.round(minuteDragY.value / ITEM_H)
  const remainder = minuteDragY.value + steps * ITEM_H
  selMinute.value = mod(selMinute.value + steps, 60)
  minuteDragY.value = remainder
  doEmit()
  mSnapping.value = true
  nextTick(() => {
    void document.body.offsetHeight
    mDragging.value = false
    minuteDragY.value = 0
    setTimeout(() => { mSnapping.value = false }, 320)
  })
}

function clearValue() { selDay.value = null; emit('update:modelValue', '') }
function toggle() { isOpen.value = !isOpen.value }

function onClickOutside(e: MouseEvent) {
  if (pickerRef.value && !pickerRef.value.contains(e.target as Node)) isOpen.value = false
}
onMounted(() => document.addEventListener('mousedown', onClickOutside))
onUnmounted(() => document.removeEventListener('mousedown', onClickOutside))
</script>

<template>
  <div ref="pickerRef" class="adtp" :class="{ 'adtp--open': isOpen }">
    <button type="button" class="adtp__trigger" @click="toggle">
      <span class="adtp__label" :class="{ 'adtp__label--ph': !hasValue }">{{ hasValue ? displayText : placeholder }}</span>
      <button v-if="hasValue" type="button" class="adtp__clear" @click.stop="clearValue" aria-label="清除">
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none"><path d="M2 2L10 10M10 2L2 10" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
      </button>
      <span v-else class="adtp__chevron">
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M3 5L7 9L11 5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>
      </span>
    </button>

    <Transition name="adtp-pop">
      <div v-if="isOpen" class="adtp__panel">
        <div class="adtp__tabs">
          <div class="adtp__tab-bg" :class="{ 'adtp__tab-bg--right': activeTab === 'time' }" />
          <button type="button" class="adtp__tab" :class="{ 'adtp__tab--active': activeTab === 'date' }" @click="setTab('date')">
            <svg width="13" height="13" viewBox="0 0 13 13" fill="none"><rect x="1" y="2" width="11" height="10" rx="2" stroke="currentColor" stroke-width="1.2"/><path d="M1 6h11" stroke="currentColor" stroke-width="1.2"/><path d="M4 1v2M9 1v2" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/></svg>
            日期
          </button>
          <button type="button" class="adtp__tab" :class="{ 'adtp__tab--active': activeTab === 'time' }" @click="setTab('time')">
            <svg width="13" height="13" viewBox="0 0 13 13" fill="none"><circle cx="6.5" cy="6.5" r="5" stroke="currentColor" stroke-width="1.2"/><path d="M6.5 4V6.5l1.5 1.5" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/></svg>
            时间
          </button>
        </div>

        <div class="adtp__content">
          <Transition :name="`tab-${tabDir}`" mode="out-in">
            <!-- Date -->
            <div v-if="activeTab === 'date'" key="date" class="adtp__pane adtp__date-pane">
              <div class="adtp__nav">
                <button type="button" class="adtp__nav-btn" @click="prevMonth"><svg width="12" height="12" viewBox="0 0 12 12" fill="none"><path d="M8 2L4 6L8 10" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg></button>
                <span class="adtp__nav-label">{{ monthLabel }}</span>
                <button type="button" class="adtp__nav-btn" @click="nextMonth"><svg width="12" height="12" viewBox="0 0 12 12" fill="none"><path d="M4 2L8 6L4 10" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg></button>
              </div>
              <div class="adtp__wkrow"><span v-for="w in WKDAYS" :key="w" class="adtp__wk">{{ w }}</span></div>
              <div class="adtp__days">
                <template v-for="(day, i) in cells" :key="i">
                  <span v-if="day === null" class="adtp__day-blank" />
                  <button v-else type="button" class="adtp__day"
                    :class="{ 'adtp__day--sel': daySel(day), 'adtp__day--today': dayToday(day) && !daySel(day), 'adtp__day--off': dayOff(day) }"
                    :disabled="dayOff(day)" @click="pickDay(day)">{{ day }}</button>
                </template>
              </div>
            </div>

            <!-- Time -->
            <div v-else key="time" class="adtp__pane adtp__time-pane">
              <div class="drum-head"><span>时</span><span>分</span></div>
              <div class="drum-wrap">
                <div class="drum-band" />
                <div class="drum-fade drum-fade--t" />
                <div class="drum-fade drum-fade--b" />
                <div class="drum-cols">
                  <div class="drum-col"
                    @wheel="onHWheel"
                    @touchstart="onHTouchStart" @touchmove.prevent="onHTouchMove" @touchend="onHTouchEnd">
                    <div class="drum-inner" :style="drumHourCss">
                      <div v-for="(h, i) in hourItems" :key="i" class="drum-cell"
                        :style="drumStyle(i, hourDragY, hDragging)"
                        @click="animatedShiftH(i - DR)">{{ pad(h) }}</div>
                    </div>
                  </div>
                  <div class="drum-col"
                    @wheel="onMWheel"
                    @touchstart="onMTouchStart" @touchmove.prevent="onMTouchMove" @touchend="onMTouchEnd">
                    <div class="drum-inner" :style="drumMinuteCss">
                      <div v-for="(m, i) in minuteItems" :key="i" class="drum-cell"
                        :style="drumStyle(i, minuteDragY, mDragging)"
                        @click="animatedShiftM(i - DR)">{{ pad(m) }}</div>
                    </div>
                  </div>
                </div>
              </div>
              <p v-if="selDay === null" class="drum-hint">请先在「日期」选项卡选择日期</p>
            </div>
          </Transition>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.adtp { position: relative; display: inline-block; width: 100%; }

.adtp__trigger {
  display: flex; align-items: center; justify-content: space-between; gap: 8px;
  width: 100%; padding: 9px 13px; background: #fff; border: none;
  border-radius: var(--radius-md); color: var(--c-text); font-size: var(--text-base);
  font-family: var(--font-sans); cursor: pointer; box-shadow: var(--shadow-sm);
  user-select: none; white-space: nowrap; min-width: 0;
  transition: background var(--dur-fast) var(--ease), box-shadow var(--dur-fast) var(--ease);
}
@media (hover: hover) { .adtp__trigger:hover { background: #f8fafc; box-shadow: var(--shadow-md); } }
.adtp--open .adtp__trigger { background: #f8fafc; box-shadow: 0 0 0 2.5px var(--c-accent-soft), var(--shadow-md); }
.adtp__label { flex: 1; text-align: left; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--c-text); }
.adtp__label--ph { color: var(--c-text-muted); }
.adtp__chevron { display: flex; align-items: center; color: var(--c-text-muted); transition: transform var(--dur-normal) var(--ease); flex-shrink: 0; }
.adtp--open .adtp__chevron { transform: rotate(180deg); }
.adtp__clear {
  display: flex; align-items: center; justify-content: center; width: 18px; height: 18px;
  border: none; background: var(--c-border); border-radius: 50%; color: var(--c-text-muted);
  cursor: pointer; flex-shrink: 0; padding: 0; transition: background 0.15s, color 0.15s;
}
@media (hover: hover) { .adtp__clear:hover { background: var(--c-text-muted); color: #fff; } }

.adtp__panel {
  position: absolute; bottom: calc(100% + 8px); left: 0; width: 268px;
  background: #fff; border-radius: 16px;
  box-shadow: 0 -4px 16px rgba(0,0,0,0.06), 0 12px 40px rgba(0,0,0,0.12);
  z-index: 1000; overflow: hidden;
}

/* Tabs */
.adtp__tabs {
  position: relative; display: flex; gap: 6px; padding: 8px 10px;
  border-bottom: 1px solid var(--c-border-light);
}
.adtp__tab-bg {
  position: absolute; top: 8px; bottom: 8px; left: 10px;
  width: calc(50% - 13px); background: var(--c-accent-light);
  border-radius: 10px; z-index: 0;
  transition: left 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}
.adtp__tab-bg--right { left: calc(50% + 3px); }
.adtp__tab {
  flex: 1; position: relative; z-index: 1;
  display: flex; align-items: center; justify-content: center; gap: 5px;
  padding: 8px 0; border: none; background: transparent; border-radius: 10px;
  font-size: var(--text-sm); font-family: var(--font-sans); font-weight: 500;
  color: var(--c-text-muted); cursor: pointer; transition: color 0.25s ease;
}
.adtp__tab--active { color: var(--c-accent); }

/* Content */
.adtp__content { height: 218px; overflow: hidden; }
.adtp__pane { height: 100%; }

/* Tab slide transitions */
.tab-left-enter-active, .tab-right-enter-active {
  transition: transform 0.22s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.18s ease;
}
.tab-left-leave-active, .tab-right-leave-active {
  transition: transform 0.12s ease, opacity 0.1s ease;
}
.tab-left-enter-from { opacity: 0; transform: translateX(20px); }
.tab-left-leave-to   { opacity: 0; transform: translateX(-20px); }
.tab-right-enter-from { opacity: 0; transform: translateX(-20px); }
.tab-right-leave-to   { opacity: 0; transform: translateX(20px); }

/* Date */
.adtp__date-pane { padding: 10px 14px 6px; overflow-y: auto; }
.adtp__nav { display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px; }
.adtp__nav-btn {
  width: 28px; height: 28px; border: none; background: transparent; border-radius: 8px;
  display: flex; align-items: center; justify-content: center; cursor: pointer;
  color: var(--c-text-muted); transition: background 0.15s, color 0.15s;
}
@media (hover: hover) { .adtp__nav-btn:hover { background: var(--c-border-light); color: var(--c-text); } }
.adtp__nav-label { font-size: var(--text-sm); font-weight: 600; color: var(--c-text); }
.adtp__wkrow { display: grid; grid-template-columns: repeat(7, 1fr); }
.adtp__wk { text-align: center; font-size: var(--text-xs); color: var(--c-text-muted); padding: 3px 0; font-weight: 500; }
.adtp__days { display: grid; grid-template-columns: repeat(7, 1fr); gap: 2px; }
.adtp__day-blank { height: 28px; }
.adtp__day {
  height: 28px; border: none; background: transparent; border-radius: 8px;
  font-size: var(--text-sm); font-family: var(--font-sans); color: var(--c-text);
  cursor: pointer; display: flex; align-items: center; justify-content: center;
  transition: background 0.12s, color 0.12s;
}
@media (hover: hover) { .adtp__day:hover:not(:disabled) { background: var(--c-border-light); } }
.adtp__day--today { font-weight: 700; color: var(--c-accent); }
.adtp__day--sel { background: var(--c-accent) !important; color: #fff !important; font-weight: 600; }
.adtp__day--off { color: var(--c-text-muted); opacity: 0.35; cursor: not-allowed; }

/* Time drum */
.adtp__time-pane { display: flex; flex-direction: column; padding: 6px 0 4px; }
.drum-head { flex-shrink: 0; display: flex; padding: 0 14px; height: 22px; align-items: center; }
.drum-head span { flex: 1; text-align: center; font-size: var(--text-sm); color: var(--c-text-muted); font-weight: 500; }
.drum-wrap { flex: 1; position: relative; overflow: hidden; min-height: 0; }
.drum-band {
  position: absolute; top: 50%; transform: translateY(-50%);
  left: 12px; right: 12px; height: 36px;
  background: var(--c-accent-light); border-radius: 10px;
  pointer-events: none; z-index: 0;
}
.drum-fade { position: absolute; left: 0; right: 0; height: 38%; pointer-events: none; z-index: 2; }
.drum-fade--t { top: 0; background: linear-gradient(to bottom, #fff 10%, transparent); }
.drum-fade--b { bottom: 0; background: linear-gradient(to top, #fff 10%, transparent); }
.drum-cols { display: flex; height: 100%; position: relative; z-index: 1; }
.drum-col {
  flex: 1; height: 100%; display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  overflow: hidden; touch-action: none; cursor: ns-resize;
}
.drum-inner { display: flex; flex-direction: column; align-items: center; width: 100%; }
.drum-cell {
  height: 36px; width: 100%; display: flex; align-items: center; justify-content: center;
  font-family: var(--font-sans); font-variant-numeric: tabular-nums; user-select: none; cursor: pointer;
}
.drum-hint {
  text-align: center; font-size: var(--text-xs); color: var(--c-text-muted);
  margin: 2px 14px 0; flex-shrink: 0; line-height: 1.5;
}

/* Panel pop */
.adtp-pop-enter-active { transition: opacity 0.24s ease, transform 0.28s cubic-bezier(0.16, 1, 0.3, 1); }
.adtp-pop-leave-active { transition: opacity 0.15s ease, transform 0.15s ease; }
.adtp-pop-enter-from { opacity: 0; transform: scale(0.93) translateY(8px); }
.adtp-pop-leave-to   { opacity: 0; transform: scale(0.96) translateY(4px); }
</style>
