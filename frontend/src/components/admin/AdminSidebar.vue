<script setup lang="ts">
import { computed, ref, watch, onMounted, nextTick } from 'vue'

export type AdminTabKey =
  | 'dashboard'
  | 'reports'
  | 'users'
  | 'tasks'
  | 'chats'
  | 'notifications'
  | 'categories'
  | 'agents'
  | 'newcomer-rewards'
  | 'logs'

interface TabItem {
  key: AdminTabKey
  label: string
  icon: string
  hint: string
}

const props = defineProps<{
  activeTab: AdminTabKey
  mobileOpen: boolean
}>()

const emit = defineEmits<{
  'tab-change': [key: AdminTabKey]
  'close-mobile': []
  logout: []
}>()

const appTitle = import.meta.env.VITE_APP_TITLE as string || '校园任务平台'
const logoFile = import.meta.env.VITE_APP_LOGO as string | undefined
const logoUrl = computed(() => logoFile ? `/logos/${logoFile}` : null)

const tabs: TabItem[] = [
  { key: 'dashboard', label: '运营看板', icon: 'fa-solid fa-chart-line', hint: '数据概览' },
  { key: 'reports', label: '举报审核', icon: 'fa-solid fa-flag', hint: '举报/申诉' },
  { key: 'users', label: '用户管理', icon: 'fa-solid fa-users-gear', hint: '画像与风控' },
  { key: 'tasks', label: '任务处置', icon: 'fa-solid fa-list-check', hint: '删除/置顶/加急' },
  { key: 'chats', label: '聊天审计', icon: 'fa-solid fa-comments', hint: '全量会话' },
  { key: 'notifications', label: '通知公告', icon: 'fa-solid fa-bullhorn', hint: '运营触达' },
  { key: 'categories', label: '类别管理', icon: 'fa-solid fa-tags', hint: '分类体系' },
  { key: 'agents', label: '代理管理', icon: 'fa-solid fa-robot', hint: 'AI 配额与审计' },
  { key: 'newcomer-rewards', label: '奖励配置', icon: 'fa-solid fa-gift', hint: '规则与发放' },
  { key: 'logs', label: '操作日志', icon: 'fa-solid fa-clock-rotate-left', hint: '审计留痕' },
]

function chooseTab(key: AdminTabKey) {
  emit('tab-change', key)
  emit('close-mobile')
}

function onOverlayClick() {
  emit('close-mobile')
}

const navRef = ref<HTMLElement | null>(null)
const itemRefs = ref<(HTMLButtonElement | null)[]>([])
const sliderStyle = ref<Record<string, string>>({ top: '0px', height: '44px', opacity: '0' })
const sliderReady = ref(false)

const activeIndex = computed(() => tabs.findIndex(t => t.key === props.activeTab))

function updateSlider(animate = true) {
  nextTick(() => {
    const nav = navRef.value
    const el = itemRefs.value[activeIndex.value]
    if (!nav || !el) return
    const navRect = nav.getBoundingClientRect()
    const itemRect = el.getBoundingClientRect()
    if (!animate) {
      sliderReady.value = false
      sliderStyle.value = {
        top: `${itemRect.top - navRect.top + nav.scrollTop}px`,
        height: `${itemRect.height}px`,
        opacity: '1',
      }
      // 双层 rAF：第一帧让浏览器绘制无动画的正确位置，第二帧再开启 transition
      // 单层 rAF 可能在同一渲染批次中执行，导致 sliderReady 翻转时位置变化仍带动画
      requestAnimationFrame(() => {
        requestAnimationFrame(() => { sliderReady.value = true })
      })
    } else {
      sliderStyle.value = {
        top: `${itemRect.top - navRect.top + nav.scrollTop}px`,
        height: `${itemRect.height}px`,
        opacity: '1',
      }
    }
  })
}

watch(() => props.activeTab, () => updateSlider(true))
onMounted(() => updateSlider(false))
</script>

<template>
  <Teleport to="body">
    <Transition name="as-overlay">
      <div v-if="props.mobileOpen" class="as-mobile-overlay" @click.self="onOverlayClick" />
    </Transition>
  </Teleport>

  <aside class="as-shell" :class="{ 'as-shell--mobile-open': props.mobileOpen }">
    <div class="as-brand">
      <div class="as-logo">
        <img v-if="logoUrl" :src="logoUrl" class="as-logo__img" alt="Logo" />
        <i v-else class="fa-solid fa-graduation-cap"></i>
      </div>
      <div class="as-brand-info">
        <span class="as-brand-name">{{ appTitle }}</span>
        <span class="as-brand-sub">管理控制台</span>
      </div>
      <button class="as-mobile-close" @click="$emit('close-mobile')">
        <i class="fa-solid fa-xmark"></i>
      </button>
    </div>

    <nav class="as-nav" ref="navRef">
      <div class="as-nav__label">主菜单</div>
      <div class="as-nav__slider" :class="{ 'as-nav__slider--ready': sliderReady }" :style="sliderStyle" aria-hidden="true" />
      <button
        v-for="(tab, idx) in tabs"
        :key="tab.key"
        :ref="(el) => { itemRefs[idx] = el as HTMLButtonElement }"
        class="as-item"
        :class="{ 'as-item--active': props.activeTab === tab.key }"
        @click="chooseTab(tab.key)"
      >
        <i :class="tab.icon" class="as-item__icon"></i>
        <span class="as-item__label">{{ tab.label }}</span>
      </button>
    </nav>

    <div class="as-foot">
      <div class="as-foot__avatar">
        <i class="fa-solid fa-user-shield"></i>
      </div>
      <span class="as-foot__name">管理员</span>
      <button class="as-logout" @click="$emit('logout')">
        <i class="fa-solid fa-right-from-bracket"></i>
      </button>
    </div>
  </aside>
</template>

<style scoped>
.as-mobile-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.2);
  z-index: 69;
  backdrop-filter: blur(4px);
  -webkit-backdrop-filter: blur(4px);
}

.as-shell {
  flex-shrink: 0;
  width: 260px;
  height: 100vh;
  padding: 0;
  border-right: 1px solid rgba(226, 232, 240, 0.5);
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  display: flex;
  flex-direction: column;
  z-index: 70;
  box-shadow: 4px 0 24px rgba(0, 0, 0, 0.02);
}

.as-brand {
  height: 72px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 22px;
  border-bottom: 1px solid rgba(226, 232, 240, 0.6);
}

.as-logo {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
  color: #fff;
  font-size: 14px;
  display: grid;
  place-items: center;
  box-shadow: 0 8px 20px rgba(59, 130, 246, 0.25);
  flex-shrink: 0;
  overflow: hidden;
}

.as-logo__img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.as-brand-info {
  display: flex;
  flex-direction: column;
  gap: 1px;
  flex: 1;
  min-width: 0;
}

.as-brand-name {
  font-weight: 700;
  font-size: 14px;
  color: var(--c-text);
  letter-spacing: -0.01em;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.as-brand-sub {
  font-size: 11px;
  color: #94a3b8;
}

.as-mobile-close {
  display: none;
  margin-left: auto;
  border: none;
  background: transparent;
  color: #94a3b8;
  font-size: 16px;
  padding: 4px;
}

.as-mobile-close:hover {
  color: #64748b;
}

.as-nav {
  flex: 1;
  overflow-y: auto;
  padding: 20px 14px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  position: relative;
}

.as-nav__slider {
  position: absolute;
  left: 14px;
  right: 14px;
  border-radius: 14px;
  background: rgba(59, 130, 246, 0.07);
  pointer-events: none;
  z-index: 0;
}

.as-nav__slider--ready {
  transition:
    top 280ms cubic-bezier(0.4, 0, 0.2, 1),
    height 280ms cubic-bezier(0.4, 0, 0.2, 1),
    opacity 180ms ease;
}

.as-nav__label {
  font-size: 11px;
  font-weight: 600;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  padding: 0 10px;
  margin-bottom: 10px;
}

.as-item {
  position: relative;
  z-index: 1;
  border: none;
  background: transparent;
  border-radius: 14px;
  padding: 11px 12px;
  text-align: left;
  display: flex;
  align-items: center;
  gap: 12px;
  transition: color 200ms var(--ease);
}

.as-item__icon {
  width: 20px;
  text-align: center;
  font-size: 14px;
  color: #94a3b8;
  flex-shrink: 0;
  transition: color 200ms var(--ease);
}

.as-item__label {
  font-weight: 500;
  font-size: 13.5px;
  color: #64748b;
  transition: color 200ms var(--ease);
}

@media (hover: hover) {
  .as-item:not(.as-item--active):hover {
    background: rgba(241, 245, 249, 0.8);
  }

  .as-item:not(.as-item--active):hover .as-item__icon {
    color: #64748b;
  }

  .as-item:not(.as-item--active):hover .as-item__label {
    color: #334155;
  }
}

.as-item--active {
  background: transparent;
}

.as-item--active .as-item__icon {
  color: var(--c-accent);
}

.as-item--active .as-item__label {
  color: var(--c-accent);
  font-weight: 600;
}

.as-foot {
  margin: 0 10px 10px;
  padding: 10px 12px;
  background: #f8fafc;
  border-radius: 16px;
  display: flex;
  align-items: center;
  gap: 10px;
}

.as-foot__avatar {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: #fff;
  border: 1px solid #e2e8f0;
  display: grid;
  place-items: center;
  color: #64748b;
  font-size: 13px;
  flex-shrink: 0;
}

.as-foot__name {
  flex: 1;
  font-size: 13px;
  font-weight: 600;
  color: var(--c-text);
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.as-logout {
  width: 32px;
  height: 32px;
  border: none;
  background: transparent;
  color: #94a3b8;
  border-radius: var(--radius-sm);
  display: grid;
  place-items: center;
  font-size: 14px;
  flex-shrink: 0;
  transition: color 200ms var(--ease), background 200ms var(--ease);
}

.as-logout:hover {
  color: #ef4444;
  background: rgba(239, 68, 68, 0.06);
}

@media (max-width: 1024px) {
  .as-shell {
    position: fixed;
    left: 0;
    top: 0;
    transform: translateX(-100%);
    transition: transform 0.3s var(--ease);
    background: rgba(255, 255, 255, 0.95);
  }

  .as-shell--mobile-open {
    transform: translateX(0);
    box-shadow: 16px 0 44px rgba(2, 8, 23, 0.12);
  }

  .as-mobile-close {
    display: block;
  }
}

.as-overlay-enter-active,
.as-overlay-leave-active {
  transition: opacity 0.22s var(--ease);
}

.as-overlay-enter-from,
.as-overlay-leave-to {
  opacity: 0;
}
</style>
