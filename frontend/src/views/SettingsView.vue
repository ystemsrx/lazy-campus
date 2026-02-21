<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { extractError } from '../utils/error'
import HomeAvatar from '../components/home/ui/HomeAvatar.vue'
import HomeHeaderBar from '../components/home/HomeHeaderBar.vue'
import AppToast from '../components/AppToast.vue'
import { useAppToast } from '../composables/useAppToast'
import { fetchCategories } from '../api/tasks'
import { updateProfile, updateWorkerProfile, uploadAvatar, fetchMyWorkerProfile } from '../api/users'
import type { Category } from '../types/api'

const router = useRouter()
const auth = useAuthStore()
const { toast, showToast, clearToast } = useAppToast()

const appTitle = import.meta.env.VITE_APP_TITLE || '校园任务平台'

function logout() {
  auth.logout()
  router.push('/login')
}

const me = computed(() => auth.user)
const loading = ref(true)
const categories = ref<Category[]>([])
const activeTab = ref<'profile' | 'worker'>('profile')
const avatarUploading = ref(false)

const profileForm = ref({
  email: '',
  nickname: '',
  gender: '' as 'male' | 'female' | '',
})

const workerForm = ref({
  enabled: false,
  skill_tag_ids: [] as number[],
  bio: '',
  phone: '',
  wechat: '',
})

// ── 滑动指示器 ──
const tabRefs = ref<(HTMLElement | null)[]>([null, null])
const indicatorStyle = ref<Record<string, string | number>>({ opacity: 0 })

function updateIndicator() {
  const idx = activeTab.value === 'profile' ? 0 : 1
  const el = tabRefs.value[idx]
  if (el) {
    indicatorStyle.value = {
      opacity: 1,
      width: el.offsetWidth + 'px',
      height: el.offsetHeight + 'px',
      transform: `translate(${el.offsetLeft}px, ${el.offsetTop}px)`,
    }
  }
}

watch(activeTab, async () => {
  await nextTick()
  updateIndicator()
})

// ── 自动保存：防抖 500ms，saving 从变化起持续到 API 实际返回 ──
const saveStatus = ref<'idle' | 'saving' | 'saved'>('idle')
const isDataLoaded = ref(false)

// 用独立变量而非对象引用，更简洁可靠
let profileDebounce: ReturnType<typeof setTimeout> | null = null
let workerDebounce: ReturnType<typeof setTimeout> | null = null
let savedResetTimer: ReturnType<typeof setTimeout> | null = null

watch(profileForm, () => {
  if (!isDataLoaded.value) return
  if (!profileForm.value.email || !profileForm.value.gender) return
  // 立即显示保存中；重置防抖，上一次等待直接作废
  saveStatus.value = 'saving'
  if (profileDebounce) clearTimeout(profileDebounce)
  profileDebounce = setTimeout(doSaveProfile, 500)
}, { deep: true })

watch(workerForm, () => {
  if (!isDataLoaded.value) return
  saveStatus.value = 'saving'
  if (workerDebounce) clearTimeout(workerDebounce)
  workerDebounce = setTimeout(doSaveWorker, 500)
}, { deep: true })

async function doSaveProfile() {
  // 若防抖期间又有新变化，新的 watch 会取消本次调用并重新调度
  try {
    const updated = await updateProfile({
      email: profileForm.value.email,
      gender: profileForm.value.gender as 'male' | 'female',
      nickname: profileForm.value.nickname || undefined,
    })
    auth.user = updated
    auth.displayName = updated.nickname || updated.name
    localStorage.setItem('display_name', auth.displayName)
    // 以实际 API 返回时间为准，保存完成才标记 saved
    markSaved()
  } catch (err: any) {
    saveStatus.value = 'idle'
    showToast(extractError(err, '保存失败'), 'error')
  }
}

async function doSaveWorker() {
  try {
    await updateWorkerProfile({
      enabled: workerForm.value.enabled,
      skill_tag_ids: workerForm.value.skill_tag_ids,
      min_price: null,
      max_price: null,
      bio: workerForm.value.bio || null,
      phone: workerForm.value.phone || null,
      wechat: workerForm.value.wechat || null,
    })
    markSaved()
  } catch (err: any) {
    saveStatus.value = 'idle'
    showToast(extractError(err, '保存失败'), 'error')
  }
}

function markSaved() {
  saveStatus.value = 'saved'
  if (savedResetTimer) clearTimeout(savedResetTimer)
  savedResetTimer = setTimeout(() => { saveStatus.value = 'idle' }, 2000)
}

onMounted(async () => {
  window.addEventListener('resize', updateIndicator)

  try {
    const [cats, workerProfile] = await Promise.all([
      fetchCategories(),
      fetchMyWorkerProfile(),
    ])
    categories.value = cats
    workerForm.value = {
      enabled: workerProfile.enabled,
      skill_tag_ids: workerProfile.skill_tags.map((t: { id: number }) => t.id),
      bio: workerProfile.bio || '',
      phone: workerProfile.phone || '',
      wechat: workerProfile.wechat || '',
    }
  } catch (err: any) {
    showToast(extractError(err, '加载失败'), 'error')
  }

  if (me.value) {
    profileForm.value.email = me.value.email || ''
    profileForm.value.nickname = me.value.nickname || ''
    profileForm.value.gender = (me.value.gender as 'male' | 'female') || ''
  }

  loading.value = false

  // 等内容渲染完毕再初始化指示器 & 允许自动保存
  await nextTick()
  updateIndicator()
  isDataLoaded.value = true
})

onUnmounted(() => {
  window.removeEventListener('resize', updateIndicator)
  if (profileDebounce) clearTimeout(profileDebounce)
  if (workerDebounce) clearTimeout(workerDebounce)
  if (savedResetTimer) clearTimeout(savedResetTimer)
})

function toggleSkillTag(id: number) {
  const ids = workerForm.value.skill_tag_ids
  const idx = ids.indexOf(id)
  if (idx >= 0) {
    ids.splice(idx, 1)
  } else if (ids.length < 5) {
    ids.push(id)
  }
}

async function handleAvatarUpload(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  avatarUploading.value = true
  try {
    const updated = await uploadAvatar(file)
    auth.user = updated
    showToast('头像已更新', 'success')
  } catch (err: any) {
    showToast(extractError(err, '头像上传失败'), 'error')
  } finally {
    avatarUploading.value = false
    input.value = ''
  }
}
</script>

<template>
  <AppToast :toast="toast" @dismiss="clearToast" />

  <div class="sv-page">
    <div class="sv-bg-gradient" />

    <HomeHeaderBar
      :active-tab="null"
      :app-title="appTitle"
      :is-authenticated="auth.isAuthenticated"
      :display-name="auth.displayName"
      :avatar-url="me?.avatar_url"
      :gender="me?.gender ?? null"
      @publish="router.push('/')"
      @open-my-panel="router.push('/tasks')"
      @open-settings="router.push('/settings')"
      @open-reports="router.push('/')"
      @login="router.push('/login')"
      @logout="logout"
      @update:active-tab="(t) => router.push({ path: '/', query: t === 'workers' ? { tab: 'workers' } : {} })"
    />

    <div class="sv-container">

      <!-- 顶部标题：始终立即显示，挂载时有入场动画 -->
      <header class="sv-header">
        <h1 class="sv-title">账号设置</h1>
        <p class="sv-subtitle">管理您的个人信息与接单首选项</p>
      </header>

      <div class="sv-layout">

        <!-- ══ 骨架屏（加载中）══ -->
        <template v-if="loading">
          <!-- 导航骨架 -->
          <div class="sv-nav-skel">
            <div class="sv-skel sv-skel--nav-btn" />
            <div class="sv-skel sv-skel--nav-btn" />
          </div>

          <!-- 面板骨架 -->
          <div class="sv-panel sv-panel-skel">
            <div class="sv-skel-section">
              <!-- 标题行 -->
              <div class="sv-skel sv-skel--title" />
              <div class="sv-skel sv-skel--subtitle" />
            </div>
            <div class="sv-skel sv-skel--divider" />
            <!-- 头像区 -->
            <div class="sv-skel-avatar-row">
              <div class="sv-skel sv-skel--avatar" />
              <div class="sv-skel-avatar-lines">
                <div class="sv-skel sv-skel--line-md" />
                <div class="sv-skel sv-skel--line-sm" />
              </div>
            </div>
            <!-- 字段骨架 -->
            <div class="sv-skel-grid">
              <div v-for="i in 4" :key="i" class="sv-skel-field">
                <div class="sv-skel sv-skel--label" />
                <div class="sv-skel sv-skel--input" />
              </div>
            </div>
          </div>
        </template>

        <!-- ══ 实际内容（加载完成后，带分步入场动画）══ -->
        <template v-else>
          <!-- 导航：入场动画 anim-1（进入设置页时） -->
          <nav class="sv-nav sv-anim-1">
            <div class="sv-nav-indicator" :style="indicatorStyle" />

            <button
              :ref="(el) => (tabRefs[0] = el as HTMLElement | null)"
              class="sv-nav-btn"
              :class="{ 'sv-nav-btn--active': activeTab === 'profile' }"
              @click="activeTab = 'profile'"
            >
              <svg width="18" height="18" viewBox="0 0 20 20" fill="none">
                <path d="M10 10a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm0 2c-4.418 0-8 2.015-8 4.5V18h16v-1.5c0-2.485-3.582-4.5-8-4.5Z" fill="currentColor"/>
              </svg>
              个人资料
            </button>

            <button
              :ref="(el) => (tabRefs[1] = el as HTMLElement | null)"
              class="sv-nav-btn"
              :class="{ 'sv-nav-btn--active': activeTab === 'worker' }"
              @click="activeTab = 'worker'"
            >
              <svg width="18" height="18" viewBox="0 0 20 20" fill="none">
                <path d="M7 3a2 2 0 0 0-2 2v1H3a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1V7a1 1 0 0 0-1-1h-2V5a2 2 0 0 0-2-2H7Zm0 2h6v1H7V5Zm-4 3h14v8H3V8Z" fill="currentColor"/>
              </svg>
              接单设置
            </button>
          </nav>

          <!-- 面板：入场动画 anim-2（进入设置页时，延迟 120ms） -->
          <main class="sv-panel sv-anim-2">
            <form @submit.prevent>

              <!-- Tab 内容叠放，切换时仅做 opacity+translateY 过渡，无分步入场 -->
              <div class="sv-tab-grid">

                <!-- 个人资料 Tab -->
                <div class="sv-tab-pane" :class="{ 'sv-tab-pane--active': activeTab === 'profile' }">
                  <div class="sv-section-header">
                    <h2 class="sv-section-title">个人资料</h2>
                    <p class="sv-section-desc">更新您的头像和基本个人信息。</p>
                  </div>

                  <hr class="sv-divider" />

                  <!-- 头像 -->
                  <div class="sv-avatar-row">
                    <div class="sv-avatar-wrap">
                      <HomeAvatar size="xl" :avatar-url="me?.avatar_url" :gender="me?.gender ?? null" alt="avatar" />
                      <label class="sv-avatar-overlay" :class="{ 'sv-avatar-overlay--show': avatarUploading }">
                        <svg v-if="!avatarUploading" width="22" height="22" viewBox="0 0 24 24" fill="none">
                          <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" stroke="white" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
                          <circle cx="12" cy="13" r="4" stroke="white" stroke-width="1.8"/>
                        </svg>
                        <div v-else class="sv-spinner sv-spinner--sm sv-spinner--white" />
                        <input type="file" accept="image/*" hidden :disabled="avatarUploading" @change="handleAvatarUpload" />
                      </label>
                    </div>
                    <div class="sv-avatar-info">
                      <label class="sv-upload-btn">
                        {{ avatarUploading ? '上传中...' : '更改头像' }}
                        <input type="file" accept="image/*" hidden :disabled="avatarUploading" @change="handleAvatarUpload" />
                      </label>
                      <p class="sv-hint">支持 JPG、GIF 或 PNG 格式，最大 10MB</p>
                    </div>
                  </div>

                  <div class="sv-grid-2">
                    <div class="sv-field">
                      <label class="sv-label">姓名</label>
                      <div class="sv-input-wrap">
                        <input class="sv-input sv-input--disabled" :value="me?.name" disabled />
                        <svg class="sv-input-icon" width="15" height="15" viewBox="0 0 20 20" fill="none">
                          <circle cx="10" cy="10" r="8" stroke="currentColor" stroke-width="1.8"/>
                          <path d="M10 9v5M10 7v.5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
                        </svg>
                      </div>
                      <p class="sv-hint">姓名不可修改</p>
                    </div>

                    <div class="sv-field">
                      <label class="sv-label sv-label--row">
                        <span>昵称</span>
                        <span class="sv-count" :class="{ 'sv-count--warn': profileForm.nickname.length >= 8 }">
                          {{ profileForm.nickname.length }}/8
                        </span>
                      </label>
                      <input v-model="profileForm.nickname" class="sv-input" type="text" placeholder="请输入您的昵称" maxlength="8" />
                    </div>

                    <div class="sv-field sv-field--full">
                      <label class="sv-label">电子邮箱 <span class="sv-required">*</span></label>
                      <input v-model.trim="profileForm.email" class="sv-input" type="email" placeholder="you@example.com" required />
                    </div>

                    <div class="sv-field sv-field--full">
                      <label class="sv-label">性别 <span class="sv-required">*</span></label>
                      <div class="sv-gender-group">
                        <label v-for="g in ['male', 'female'] as const" :key="g" class="sv-gender-option">
                          <input v-model="profileForm.gender" type="radio" name="sv-gender" :value="g" class="sv-radio-hidden" />
                          <div class="sv-gender-card" :class="{ 'sv-gender-card--active': profileForm.gender === g }">
                            {{ g === 'male' ? '男' : '女' }}
                          </div>
                        </label>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- 接单设置 Tab -->
                <div class="sv-tab-pane" :class="{ 'sv-tab-pane--active': activeTab === 'worker' }">
                  <div class="sv-section-header sv-section-header--row">
                    <div>
                      <h2 class="sv-section-title">接单设置</h2>
                    </div>
                    <div class="sv-toggle-wrap">
                      <span class="sv-toggle-label" :class="{ 'sv-toggle-label--active': workerForm.enabled }">
                        {{ workerForm.enabled ? '正在接单' : '暂停接单' }}
                      </span>
                      <button
                        type="button"
                        class="sv-toggle"
                        :class="{ 'sv-toggle--on': workerForm.enabled }"
                        @click="workerForm.enabled = !workerForm.enabled"
                      >
                        <span class="sv-toggle-thumb" :class="{ 'sv-toggle-thumb--on': workerForm.enabled }" />
                      </button>
                    </div>
                  </div>

                  <hr class="sv-divider" />

                  <div class="sv-section-body">
                    <div class="sv-field">
                      <label class="sv-label sv-label--row">
                        <span>擅长类别（可多选）<span class="sv-required">*</span></span>
                        <span v-if="workerForm.skill_tag_ids.length === 0" class="sv-count sv-count--warn">请至少选择一个</span>
                        <span v-else class="sv-count" :class="{ 'sv-count--warn': workerForm.skill_tag_ids.length >= 5 }">
                          {{ workerForm.skill_tag_ids.length }}/5
                        </span>
                      </label>
                      <div v-if="categories.length" class="sv-chip-group">
                        <button
                          v-for="cat in categories"
                          :key="cat.id"
                          type="button"
                          class="sv-chip"
                          :class="{ 'sv-chip--selected': workerForm.skill_tag_ids.includes(cat.id) }"
                          @click="toggleSkillTag(cat.id)"
                        >{{ cat.name }}</button>
                      </div>
                      <p v-else class="sv-hint" style="margin-top:4px">管理员暂未设置类别</p>
                    </div>

                    <div class="sv-field">
                      <label class="sv-label sv-label--row">
                        <span>个人简介 <span class="sv-required">*</span></span>
                        <span class="sv-count" :class="{ 'sv-count--warn': workerForm.bio.length >= 150 }">
                          {{ workerForm.bio.length }}/150
                        </span>
                      </label>
                      <textarea
                        v-model="workerForm.bio"
                        class="sv-textarea"
                        placeholder="简单介绍一下您的经验、技能和能提供的服务..."
                        maxlength="150"
                        rows="4"
                      />
                    </div>

                    <div class="sv-grid-2">
                      <div class="sv-field">
                        <label class="sv-label">手机号码</label>
                        <input v-model.trim="workerForm.phone" class="sv-input" type="tel" placeholder="请输入联系电话" />
                      </div>
                      <div class="sv-field">
                        <label class="sv-label">微信号</label>
                        <input v-model.trim="workerForm.wechat" class="sv-input" type="text" placeholder="请输入微信号" />
                      </div>
                    </div>
                  </div>
                </div>

              </div>

              <!-- 底部保存状态（无按钮，以实际 API 返回时间为准） -->
              <div class="sv-status-bar">
                <div class="sv-status-wrap">
                  <div class="sv-status-item" :class="{ 'sv-status-item--visible': saveStatus === 'saving' }">
                    <div class="sv-spinner sv-spinner--sm" />
                  </div>
                  <div class="sv-status-item sv-status-item--saved" :class="{ 'sv-status-item--visible': saveStatus === 'saved' }">
                    <svg width="17" height="17" viewBox="0 0 18 18" fill="none">
                      <path d="M2 9l5 5L16 3" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                    <span>已保存</span>
                  </div>
                </div>
              </div>

            </form>
          </main>
        </template>

      </div>
    </div>
  </div>
</template>

<style scoped>
/* ════════════════════════════════════
   页面基础
   ════════════════════════════════════ */
.sv-page {
  min-height: 100vh;
  background: #f8fafc;
  position: relative;
  z-index: 0;
  font-family: var(--font-sans);
}

.sv-bg-gradient {
  position: absolute;
  inset: 0;
  z-index: -1;
  background: linear-gradient(135deg, rgba(238,242,255,0.8) 0%, #ffffff 50%, rgba(253,242,248,0.8) 100%);
  pointer-events: none;
}

.sv-container {
  max-width: 1000px;
  margin: 0 auto;
  padding: 32px 24px 48px;
  position: relative;
  z-index: 1;
}

/* ════════════════════════════════════
   顶部标题（挂载时立即入场）
   ════════════════════════════════════ */
.sv-header {
  margin-bottom: 40px;
  animation: sv-rise 0.55s ease-out 0ms both;
}


.sv-title {
  font-size: 28px;
  font-weight: 700;
  color: #18181b;
  letter-spacing: -0.5px;
  line-height: 1.2;
}

.sv-subtitle {
  font-size: var(--text-base);
  color: #64748b;
  margin-top: 8px;
}

/* ════════════════════════════════════
   布局
   ════════════════════════════════════ */
.sv-layout {
  display: flex;
  gap: 32px;
  align-items: flex-start;
}

/* ════════════════════════════════════
   分步入场动画（仅进入页面时触发）
   ════════════════════════════════════ */
@keyframes sv-rise {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 导航：0ms 延迟 */
.sv-anim-1 {
  animation: sv-rise 0.5s ease-out 0ms both;
}

/* 面板：120ms 延迟，营造先后感 */
.sv-anim-2 {
  animation: sv-rise 0.5s ease-out 0.12s both;
}

/* ════════════════════════════════════
   骨架屏 + 流光效果
   ════════════════════════════════════ */
@keyframes sv-shimmer {
  0%   { background-position: -500px 0; }
  100% { background-position: 500px 0; }
}

.sv-skel {
  border-radius: var(--radius-md);
  background: linear-gradient(
    90deg,
    #f1f5f9 0%,
    #e8edf5 40%,
    #dde4ee 50%,
    #e8edf5 60%,
    #f1f5f9 100%
  );
  background-size: 500px 100%;
  animation: sv-shimmer 1.5s ease-in-out infinite;
}

/* 导航骨架 */
.sv-nav-skel {
  display: flex;
  flex-direction: column;
  gap: 4px;
  width: 220px;
  flex-shrink: 0;
}

.sv-skel--nav-btn {
  height: 46px;
  border-radius: 12px;
}

/* 面板骨架 */
.sv-panel-skel {
  padding: 40px;
}

.sv-skel-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 0;
}

.sv-skel--title {
  height: 22px;
  width: 120px;
}

.sv-skel--subtitle {
  height: 14px;
  width: 200px;
}

.sv-skel--divider {
  height: 1px;
  background: #f1f5f9;
  margin: 28px 0;
  animation: none;
}

.sv-skel-avatar-row {
  display: flex;
  align-items: center;
  gap: 24px;
  margin-bottom: 32px;
}

.sv-skel--avatar {
  width: 72px;
  height: 72px;
  border-radius: 50%;
  flex-shrink: 0;
}

.sv-skel-avatar-lines {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.sv-skel--line-md {
  height: 32px;
  width: 110px;
  border-radius: var(--radius-md);
}

.sv-skel--line-sm {
  height: 14px;
  width: 160px;
}

.sv-skel-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px 24px;
}

.sv-skel-field {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.sv-skel--label {
  height: 14px;
  width: 60px;
}

.sv-skel--input {
  height: 40px;
}

/* ════════════════════════════════════
   左侧导航（桌面端）
   ════════════════════════════════════ */
.sv-nav {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 4px;
  width: 220px;
  flex-shrink: 0;
}

/* 白色滑块指示器，transition all 300ms ease-out 与 demo.jsx 一致 */
.sv-nav-indicator {
  position: absolute;
  left: 0;
  top: 0;
  background: #ffffff;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
  outline: 1px solid rgba(226,232,240,0.8);
  transition: all 300ms ease-out;
  z-index: 0;
  pointer-events: none;
}

.sv-nav-btn {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  border-radius: 12px;
  border: none;
  background: transparent;
  /* 非激活：slate-500，与 demo.jsx text-slate-500 一致 */
  color: #64748b;
  font-size: var(--text-base);
  font-weight: 500;
  font-family: var(--font-sans);
  cursor: pointer;
  /* 仅过渡颜色，不过渡背景（背景由指示器完成） */
  transition: color 200ms ease;
  white-space: nowrap;
  text-align: left;
}

/* 激活：zinc-900，与 demo.jsx text-zinc-900 一致 */
.sv-nav-btn--active {
  color: #18181b;
}

/* hover 非激活：slate-200/50 背景 + zinc-900 文字，与 demo.jsx 完全一致 */
@media (hover: hover) {
  .sv-nav-btn:not(.sv-nav-btn--active):hover {
    background: rgba(203,213,225,0.5);
    color: #18181b;
  }
}

/* ════════════════════════════════════
   右侧面板
   ════════════════════════════════════ */
.sv-panel {
  flex: 1;
  background: #ffffff;
  border-radius: 20px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
  border: 1px solid rgba(226,232,240,0.6);
  padding: 40px;
  min-width: 0;
}

/* ════════════════════════════════════
   Tab 叠放容器（切换时无分步入场，仅 opacity+translateY）
   ════════════════════════════════════ */
/* 容器仅作定位父元素，高度由激活面板（relative）撑开 */
.sv-tab-grid {
  position: relative;
}

/* 非激活面板：绝对定位脱离文档流，不贡献高度 */
.sv-tab-pane {
  position: absolute;
  inset: 0;
  width: 100%;
  opacity: 0;
  transform: translateY(16px);
  pointer-events: none;
  z-index: 0;
  transition: opacity 500ms ease-in-out, transform 500ms ease-in-out;
}

/* 激活面板：回到常规流，撑起容器真实高度 */
.sv-tab-pane--active {
  position: relative;
  opacity: 1;
  transform: translateY(0);
  pointer-events: auto;
  z-index: 1;
}

/* ════════════════════════════════════
   Section 头部
   ════════════════════════════════════ */
.sv-section-header { margin-bottom: 0; }

.sv-section-header--row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.sv-section-title {
  font-size: var(--text-xl);
  font-weight: 600;
  color: #18181b;
}

.sv-section-desc {
  font-size: var(--text-sm);
  color: #94a3b8;
  margin-top: 4px;
}

.sv-divider {
  border: none;
  border-top: 1px solid #f1f5f9;
  margin: 28px 0;
}

/* ════════════════════════════════════
   头像
   ════════════════════════════════════ */
.sv-avatar-row {
  display: flex;
  align-items: center;
  gap: 24px;
  margin-bottom: 32px;
}

.sv-avatar-wrap {
  position: relative;
  flex-shrink: 0;
  cursor: pointer;
}

.sv-avatar-overlay {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  background: rgba(24,24,27,0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity var(--dur-fast) var(--ease);
  cursor: pointer;
}

.sv-avatar-wrap:hover .sv-avatar-overlay,
.sv-avatar-overlay--show {
  opacity: 1;
}

.sv-avatar-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.sv-upload-btn {
  display: inline-block;
  align-self: flex-start;
  padding: 8px 16px;
  background: #ffffff;
  border: 1px solid var(--c-border);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-weight: 500;
  color: #3f3f46;
  font-family: var(--font-sans);
  cursor: pointer;
  transition: background var(--dur-fast) var(--ease);
}

@media (hover: hover) {
  .sv-upload-btn:hover { background: #f8fafc; }
}

/* ════════════════════════════════════
   表单
   ════════════════════════════════════ */
.sv-grid-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px 24px;
}

.sv-section-body {
  display: flex;
  flex-direction: column;
  gap: 24px;
  margin-top: 28px;
}

.sv-field {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.sv-field--full { grid-column: 1 / -1; }

.sv-label {
  font-size: var(--text-sm);
  font-weight: 500;
  color: #3f3f46;
}

.sv-label--row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.sv-required { color: var(--c-danger); }

.sv-count {
  font-size: var(--text-xs);
  color: #94a3b8;
  font-weight: 400;
}

.sv-count--warn {
  color: var(--c-danger);
  font-weight: 500;
}

.sv-input-wrap { position: relative; }

.sv-input {
  width: 100%;
  padding: 10px 16px;
  background: #ffffff;
  border: 1px solid var(--c-border);
  border-radius: var(--radius-md);
  color: #18181b;
  font-size: var(--text-base);
  font-family: var(--font-sans);
  outline: none;
  transition: border-color var(--dur-fast) var(--ease), box-shadow var(--dur-fast) var(--ease);
}

.sv-input:focus {
  border-color: #94a3b8;
  box-shadow: 0 0 0 3px rgba(148,163,184,0.15);
}

.sv-input--disabled {
  background: #f8fafc;
  color: #94a3b8;
  cursor: not-allowed;
  padding-right: 40px;
}

.sv-input-icon {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  color: #94a3b8;
  pointer-events: none;
}

.sv-textarea {
  width: 100%;
  padding: 12px 16px;
  background: #ffffff;
  border: 1px solid var(--c-border);
  border-radius: var(--radius-lg);
  color: #18181b;
  font-size: var(--text-base);
  font-family: var(--font-sans);
  outline: none;
  resize: none;
  line-height: 1.6;
  transition: border-color var(--dur-fast) var(--ease), box-shadow var(--dur-fast) var(--ease);
}

.sv-textarea:focus {
  border-color: #94a3b8;
  box-shadow: 0 0 0 3px rgba(148,163,184,0.15);
}

/* ════════════════════════════════════
   性别选择
   ════════════════════════════════════ */
.sv-gender-group {
  display: flex;
  gap: 12px;
}

.sv-gender-option { cursor: pointer; }

.sv-radio-hidden {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
}

.sv-gender-card {
  padding: 10px 24px;
  border-radius: var(--radius-md);
  border: 1px solid var(--c-border);
  font-size: var(--text-sm);
  font-weight: 500;
  color: #64748b;
  cursor: pointer;
  transition: all var(--dur-fast) var(--ease);
}

@media (hover: hover) {
  .sv-gender-card:hover { background: #f8fafc; }
}

.sv-gender-card--active {
  border-color: #18181b;
  background: #f8fafc;
  color: #18181b;
}

/* ════════════════════════════════════
   接单开关
   ════════════════════════════════════ */
.sv-toggle-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.sv-toggle-label {
  font-size: var(--text-sm);
  font-weight: 500;
  color: #94a3b8;
  transition: color var(--dur-fast) var(--ease);
}

.sv-toggle-label--active { color: #18181b; }

.sv-toggle {
  position: relative;
  display: inline-flex;
  align-items: center;
  width: 48px;
  height: 28px;
  flex-shrink: 0;
  cursor: pointer;
  border-radius: 9999px;
  border: 2px solid transparent;
  background: #e2e8f0;
  transition: background 200ms ease-in-out;
  outline: none;
}

.sv-toggle:focus-visible {
  box-shadow: 0 0 0 3px rgba(24,24,27,0.15);
}

.sv-toggle--on { background: #18181b; }

.sv-toggle-thumb {
  pointer-events: none;
  display: inline-block;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: #ffffff;
  box-shadow: 0 1px 3px rgba(0,0,0,0.2);
  transform: translateX(0);
  transition: transform 200ms ease-in-out;
}

.sv-toggle-thumb--on { transform: translateX(20px); }

/* ════════════════════════════════════
   技能标签
   ════════════════════════════════════ */
.sv-chip-group {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.sv-chip {
  display: inline-flex;
  align-items: center;
  padding: 8px 18px;
  border-radius: 9999px;
  border: 1px solid var(--c-border);
  background: #ffffff;
  color: #64748b;
  font-size: var(--text-sm);
  font-weight: 500;
  font-family: var(--font-sans);
  cursor: pointer;
  transition: all 200ms ease;
}

@media (hover: hover) {
  .sv-chip:not(.sv-chip--selected):hover {
    border-color: #94a3b8;
    background: #f8fafc;
  }
}

.sv-chip--selected {
  background: #18181b;
  border-color: #18181b;
  color: #ffffff;
  box-shadow: var(--shadow-xs);
}

/* ════════════════════════════════════
   底部保存状态（无按钮，以 API 返回时间为准）
   ════════════════════════════════════ */
.sv-status-bar {
  margin-top: 40px;
  padding-top: 24px;
  border-top: 1px solid #f1f5f9;
  display: flex;
  justify-content: flex-end;
  align-items: center;
  height: 32px;
}

.sv-status-wrap {
  position: relative;
  width: 96px;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: flex-end;
}

.sv-status-item {
  position: absolute;
  right: 0;
  display: flex;
  align-items: center;
  gap: 6px;
  opacity: 0;
  transform: translateY(-10px) scale(0.95);
  transition: opacity 500ms cubic-bezier(0.4,0,0.2,1), transform 500ms cubic-bezier(0.4,0,0.2,1);
  pointer-events: none;
}

.sv-status-item--visible {
  opacity: 1;
  transform: translateY(0) scale(1);
}

.sv-status-item--saved {
  color: #10b981;
  font-size: var(--text-sm);
  font-weight: 500;
  letter-spacing: 0.01em;
  transform: translateY(10px) scale(0.95);
}

.sv-status-item--saved.sv-status-item--visible {
  transform: translateY(0) scale(1);
}

/* ════════════════════════════════════
   提示文字 & 转圈
   ════════════════════════════════════ */
.sv-hint {
  font-size: var(--text-xs);
  color: #94a3b8;
}

.sv-spinner {
  width: 24px;
  height: 24px;
  border: 2.5px solid rgba(148,163,184,0.3);
  border-top-color: #94a3b8;
  border-radius: 50%;
  animation: sv-spin 0.7s linear infinite;
  flex-shrink: 0;
}

.sv-spinner--sm {
  width: 18px;
  height: 18px;
  border-width: 2px;
}

.sv-spinner--white {
  border-color: rgba(255,255,255,0.35);
  border-top-color: #ffffff;
}

@keyframes sv-spin {
  to { transform: rotate(360deg); }
}

/* ════════════════════════════════════
   移动端：分节控制器（Segmented Control）
   两个选项视觉上属于同一组，样式完全统一
   ════════════════════════════════════ */
@media (max-width: 768px) {
  .sv-container { padding: 24px 16px; }

  .sv-layout {
    flex-direction: column;
    gap: 16px;
  }

  /* 骨架导航也用同等宽度 */
  .sv-nav-skel {
    width: 100%;
    flex-direction: row;
    display: flex;
    gap: 4px;
    background: rgba(0,0,0,0.06);
    border-radius: 9999px;
    padding: 3px;
  }

  .sv-skel--nav-btn {
    flex: 1;
    height: 36px;
    border-radius: 9999px;
  }

  /* 真实导航：pill 容器 + segmented 激活样式 */
  .sv-nav {
    width: 100%;
    flex-direction: row;
    /* 共享背景容器，让两个选项看起来属于同一选择器 */
    background: rgba(0,0,0,0.06);
    border-radius: 9999px;
    padding: 3px;
    gap: 2px;
    overflow: visible;
  }

  /* 移动端指示器：全圆角 pill，与容器匹配；滑动逻辑与桌面端完全相同 */
  .sv-nav-indicator {
    border-radius: 9999px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.12);
  }

  .sv-nav-btn {
    flex: 1;
    justify-content: center;
    border-radius: 9999px;
    padding: 8px 12px;
    font-size: var(--text-sm);
    color: #64748b;
    transition: color 200ms ease;
  }

  /* 激活态只改文字颜色，白色背景由滑块指示器负责 */
  .sv-nav-btn--active {
    color: #18181b;
  }

  .sv-panel { padding: 24px 20px; }

  .sv-panel-skel { padding: 24px 20px; }

  .sv-skel-grid { grid-template-columns: 1fr; }
}
</style>
