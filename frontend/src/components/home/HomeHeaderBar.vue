<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import HomeAvatar from './ui/HomeAvatar.vue'

const props = defineProps<{
  appTitle: string
  activeTab: 'hall' | 'workers' | null
  isAuthenticated: boolean
  displayName: string
  avatarUrl?: string | null
  gender?: 'male' | 'female' | null
}>()

const emit = defineEmits<{
  (e: 'update:activeTab', value: 'hall' | 'workers' | null): void
  (e: 'publish'): void
  (e: 'openMyPanel'): void
  (e: 'openSettings'): void
  (e: 'openReports'): void
  (e: 'login'): void
  (e: 'logout'): void
}>()

const showUserMenu = ref(false)
const userMenuRef = ref<HTMLElement | null>(null)

function onClickOutside(e: MouseEvent) {
  if (userMenuRef.value && !userMenuRef.value.contains(e.target as Node)) {
    showUserMenu.value = false
  }
}

function onOpenMyPanel() {
  showUserMenu.value = false
  emit('openMyPanel')
}

function onOpenSettings() {
  showUserMenu.value = false
  emit('openSettings')
}

function onOpenReports() {
  showUserMenu.value = false
  emit('openReports')
}

function onLogout() {
  showUserMenu.value = false
  emit('logout')
}

onMounted(() => {
  document.addEventListener('mousedown', onClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('mousedown', onClickOutside)
})
</script>

<template>
  <header class="hv-header">
    <div class="hv-header__brand">
      <div class="hv-logo">T</div>
      <span class="hv-header__title">{{ appTitle }}</span>
    </div>

    <nav class="hv-tabs">
      <button
        class="hv-tab"
        :class="{ 'hv-tab--active': activeTab === 'hall' }"
        @click="emit('update:activeTab', 'hall')"
      >
        <i class="fa-solid fa-clipboard-list"></i> 任务大厅
      </button>
      <button
        class="hv-tab"
        :class="{ 'hv-tab--active': activeTab === 'workers' }"
        @click="emit('update:activeTab', 'workers')"
      >
        <i class="fa-solid fa-user-group"></i> 接单广场
      </button>
    </nav>

    <div class="hv-header__right">
      <template v-if="isAuthenticated">
        <button class="btn btn-primary btn-sm hv-publish-btn" @click="emit('publish')">
          <i class="fa-solid fa-plus"></i> 发布
        </button>

        <div ref="userMenuRef" class="hv-user-menu-wrap">
          <button class="hv-user-trigger" @click="showUserMenu = !showUserMenu">
            <HomeAvatar :avatar-url="avatarUrl" :gender="gender" />
            <span class="hv-header__name">{{ displayName }}</span>
            <i
              class="fa-solid fa-chevron-down hv-user-trigger__arrow"
              :class="{ 'hv-user-trigger__arrow--open': showUserMenu }"
            ></i>
          </button>

          <Transition name="app-dropdown">
            <div v-if="showUserMenu" class="hv-user-dropdown">
              <button class="hv-user-dropdown__item" @click="onOpenMyPanel">
                <i class="fa-solid fa-list-check"></i> 任务
              </button>
              <button class="hv-user-dropdown__item" @click="onOpenSettings">
                <i class="fa-solid fa-gear"></i> 设置
              </button>
              <button class="hv-user-dropdown__item" @click="onOpenReports">
                <i class="fa-solid fa-flag"></i> 我的举报
              </button>
              <div class="hv-user-dropdown__divider"></div>
              <button class="hv-user-dropdown__item hv-user-dropdown__item--danger" @click="onLogout">
                <i class="fa-solid fa-right-from-bracket"></i> 退出登录
              </button>
            </div>
          </Transition>
        </div>
      </template>

      <template v-else>
        <button class="btn btn-primary btn-sm" @click="emit('login')">
          <i class="fa-solid fa-right-to-bracket"></i> 登录
        </button>
      </template>
    </div>
  </header>
</template>

<style scoped>
.hv-header {
  position: sticky;
  top: 0;
  z-index: 40;
  display: flex;
  align-items: center;
  padding: 0 24px;
  height: 60px;
  background: rgba(255, 255, 255, 0.82);
  backdrop-filter: blur(14px);
  border-bottom: 1px solid var(--c-border);
}

.hv-header__brand {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.hv-logo {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-sm);
  background: var(--c-accent);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 16px;
}

.hv-header__title {
  font-weight: 700;
  font-size: var(--text-lg);
  color: var(--c-text);
}

.hv-header__right {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}

.hv-header__name {
  font-size: var(--text-sm);
  color: var(--c-text-secondary);
}

.hv-publish-btn {
  border-radius: var(--radius-full);
  padding: 6px 18px;
}

.hv-user-menu-wrap {
  position: relative;
}

.hv-user-trigger {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 8px 4px 4px;
  background: transparent;
  border: none;
  border-radius: var(--radius-full);
  transition: background var(--dur-fast) var(--ease);
}

@media (hover: hover) {
  .hv-user-trigger:hover {
    background: var(--c-border-light);
  }
}

.hv-user-trigger__arrow {
  font-size: 10px;
  color: var(--c-text-muted);
  transition: transform var(--dur-normal) var(--ease);
}

.hv-user-trigger__arrow--open {
  transform: rotate(180deg);
}

.hv-user-dropdown {
  position: absolute;
  top: calc(100% + 6px);
  right: 0;
  min-width: 180px;
  background: #ffffff;
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xl);
  z-index: 1000;
  padding: 5px;
  transform-origin: top right;
}

.hv-user-dropdown__item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 9px 14px;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--c-text);
  font-size: var(--text-base);
  font-family: var(--font-sans);
  cursor: pointer;
  text-align: left;
  transition: background var(--dur-fast) var(--ease), color var(--dur-fast) var(--ease);
}

.hv-user-dropdown__item i {
  width: 16px;
  text-align: center;
  color: var(--c-text-muted);
}

@media (hover: hover) {
  .hv-user-dropdown__item:hover {
    background: var(--c-accent-light);
    color: var(--c-accent);
  }

  .hv-user-dropdown__item:hover i {
    color: var(--c-accent);
  }

  .hv-user-dropdown__item--danger:hover {
    background: var(--c-danger-light);
    color: var(--c-danger);
  }

  .hv-user-dropdown__item--danger:hover i {
    color: var(--c-danger);
  }
}

.hv-user-dropdown__divider {
  height: 1px;
  background: var(--c-border-light);
  margin: 4px 8px;
}

.hv-tabs {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  gap: 4px;
}

.hv-tab {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 20px;
  border: none;
  background: transparent;
  color: var(--c-text-muted);
  font-size: var(--text-sm);
  font-weight: 500;
  border-radius: var(--radius-sm);
  transition: color var(--dur-fast) var(--ease), background var(--dur-fast) var(--ease);
}

@media (hover: hover) {
  .hv-tab:hover {
    color: var(--c-text);
    background: var(--c-border-light);
  }
}

.hv-tab--active {
  color: var(--c-accent);
  background: var(--c-accent-light);
}

.app-dropdown-enter-active {
  transition: opacity var(--dur-normal) var(--ease), transform var(--dur-normal) var(--ease);
}

.app-dropdown-leave-active {
  transition: opacity 180ms var(--ease), transform 180ms var(--ease);
}

.app-dropdown-enter-from {
  opacity: 0;
  transform: scaleY(0.88) translateY(-6px);
}

.app-dropdown-leave-to {
  opacity: 0;
  transform: scaleY(0.94) translateY(-3px);
}

@media (max-width: 900px) {
  .hv-header {
    padding: 0 14px;
  }

  .hv-header__title {
    display: none;
  }

  .hv-header__name {
    display: none;
  }

  .hv-tabs {
    position: static;
    transform: none;
  }
}
</style>
