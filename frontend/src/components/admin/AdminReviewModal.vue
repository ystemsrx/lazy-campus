<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { Report } from '../../types/api'

const BAN_TYPE_OPTIONS = [
  { id: 'publish', label: '禁止发布', icon: 'fa-solid fa-pen-to-square' },
  { id: 'accept', label: '禁止接单', icon: 'fa-solid fa-handshake' },
  { id: 'contact', label: '禁止联系', icon: 'fa-solid fa-comment-slash' },
  { id: 'login', label: '封禁登录', icon: 'fa-solid fa-lock' },
]

const DURATION_OPTIONS = [
  { value: -1, label: '自动' },
  { value: 1, label: '1 天' },
  { value: 3, label: '3 天' },
  { value: 7, label: '7 天' },
  { value: 15, label: '15 天' },
  { value: 30, label: '30 天' },
  { value: 0, label: '永久' },
]

const AUTO_BAN_DAYS = [1, 3, 7]

const props = defineProps<{
  show: boolean
  submitting: boolean
  target?: Report | null
  // 直接传入时使用（无 Report 对象场景）
  title?: string
  targetName?: string
  banCount?: number
  preselectedTypes?: string[]
  confirmLabel?: string
}>()

const emit = defineEmits<{
  close: []
  confirm: [payload: { ban_types: string[]; ban_days: number | null; admin_notes: string }]
}>()

const selectedTypes = ref<string[]>([])
const selectedDuration = ref(-1)
const banReason = ref('')

watch(() => props.show, (val) => {
  if (val) {
    selectedTypes.value = props.preselectedTypes?.length
      ? [...props.preselectedTypes]
      : ['login']
    selectedDuration.value = -1
    banReason.value = ''
  }
})

function toggleType(id: string) {
  const idx = selectedTypes.value.indexOf(id)
  if (idx >= 0) {
    selectedTypes.value.splice(idx, 1)
  } else {
    selectedTypes.value.push(id)
  }
}

const resolvedBanCount = computed(() =>
  props.target?.reported_user_ban_count ?? props.banCount ?? 0,
)

const autoDays = computed(() =>
  AUTO_BAN_DAYS[Math.min(resolvedBanCount.value, AUTO_BAN_DAYS.length - 1)],
)

const nextBanCount = computed(() => resolvedBanCount.value + 1)

const displayDuration = computed(() => {
  if (selectedDuration.value === -1) return `${autoDays.value} 天（自动，第 ${nextBanCount.value} 次封禁）`
  if (selectedDuration.value === 0) return '永久'
  return `${selectedDuration.value} 天`
})

const hasSelection = computed(() => selectedTypes.value.length > 0)

const resolvedTargetName = computed(() =>
  props.targetName
  || props.target?.reported_user_nickname
  || props.target?.reported_user_name
  || props.target?.reported_user_account
  || '该用户',
)

const resolvedTitle = computed(() => props.title ?? '通过举报')
const resolvedConfirmLabel = computed(() => props.confirmLabel ?? '确认通过并处罚')

function onConfirm() {
  if (!hasSelection.value) return
  emit('confirm', {
    ban_types: [...selectedTypes.value],
    ban_days: selectedDuration.value === -1 ? null : selectedDuration.value,
    admin_notes: banReason.value,
  })
}
</script>

<template>
  <Teleport to="body">
  <Transition name="fade">
    <div v-if="show" class="arv-overlay" @click.self="$emit('close')">
      <div class="arv-modal" @click.stop>
        <div class="arv-header">
          <h3>{{ resolvedTitle }}</h3>
          <button class="btn btn-ghost btn-sm" @click="$emit('close')">
            <i class="fa-solid fa-xmark"></i>
          </button>
        </div>

        <div class="arv-body">
          <p class="arv-target-line">
            对「<strong>{{ resolvedTargetName }}</strong>」执行处罚
          </p>

          <div class="arv-section">
            <label class="arv-section-label">封禁类型（可多选）</label>
            <div class="arv-type-grid">
              <button
                v-for="opt in BAN_TYPE_OPTIONS"
                :key="opt.id"
                class="arv-type-chip"
                :class="{
                  'arv-type-chip--active': selectedTypes.includes(opt.id),
                  'arv-type-chip--login': opt.id === 'login' && selectedTypes.includes(opt.id),
                }"
                @click="toggleType(opt.id)"
              >
                <i :class="opt.icon" class="arv-type-chip__icon"></i>
                <span>{{ opt.label }}</span>
              </button>
            </div>
          </div>

          <div class="arv-section">
            <label class="arv-section-label">封禁时长</label>
            <div class="arv-dur-row">
              <button
                v-for="opt in DURATION_OPTIONS"
                :key="opt.value"
                class="arv-dur-btn"
                :class="{
                  'arv-dur-btn--active': selectedDuration === opt.value,
                  'arv-dur-btn--permanent': opt.value === 0 && selectedDuration === 0,
                }"
                @click="selectedDuration = opt.value"
              >
                {{ opt.label }}
              </button>
            </div>
            <div class="arv-dur-preview">
              <i class="fa-regular fa-clock"></i>
              封禁时长：{{ displayDuration }}
            </div>
          </div>

          <div class="arv-section">
            <label class="arv-section-label">封禁理由（选填）</label>
            <input
              v-model="banReason"
              class="form-input"
              placeholder="输入封禁理由，留空则显示 违反社区规则"
              @keyup.enter="onConfirm"
            />
          </div>
        </div>

        <div class="arv-footer">
          <button class="btn btn-outline btn-sm" @click="$emit('close')">取消</button>
          <button
            class="btn btn-warning btn-sm"
            :disabled="submitting || !hasSelection"
            @click="onConfirm"
          >
            {{ submitting ? '处理中…' : resolvedConfirmLabel }}
          </button>
        </div>
      </div>
    </div>
  </Transition>
  </Teleport>
</template>

<style scoped>
.arv-overlay {
  position: fixed;
  inset: 0;
  z-index: 100;
  background: rgba(15, 23, 42, 0.2);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.arv-modal {
  background: var(--c-surface);
  border-radius: var(--radius-2xl);
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.1);
  width: min(520px, 100%);
  overflow: hidden;
  animation: arv-slide-up 0.3s var(--ease);
}

@keyframes arv-slide-up {
  from {
    opacity: 0;
    transform: translateY(20px) scale(0.97);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.arv-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid rgba(241, 245, 249, 0.8);
}

.arv-header h3 {
  margin: 0;
  font-size: 17px;
  font-weight: 700;
}

.arv-body {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 18px;
  max-height: 70vh;
  overflow-y: auto;
}

.arv-target-line {
  margin: 0;
  color: var(--c-text-secondary);
  font-size: var(--text-sm);
}

.arv-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.arv-section-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--c-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.arv-type-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.arv-type-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 9px 16px;
  border: 1.5px solid rgba(226, 232, 240, 0.8);
  border-radius: var(--radius-lg);
  background: var(--c-surface);
  color: var(--c-text-secondary);
  font-size: 13px;
  font-weight: 500;
  font-family: var(--font-sans);
  cursor: pointer;
  transition: all 200ms var(--ease);
  user-select: none;
}

@media (hover: hover) {
  .arv-type-chip:not(.arv-type-chip--active):hover {
    border-color: #cbd5e1;
    background: #f1f5f9;
    color: #475569;
  }
}

.arv-type-chip--active {
  border-color: var(--c-accent);
  background: var(--c-accent-light);
  color: var(--c-accent);
  cursor: pointer;
}

.arv-type-chip--login {
  border-color: var(--c-danger);
  background: var(--c-danger-light);
  color: var(--c-danger);
}

.arv-type-chip__icon {
  font-size: 12px;
  width: 14px;
  text-align: center;
}

.arv-dur-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.arv-dur-btn {
  padding: 7px 14px;
  border: 1.5px solid rgba(226, 232, 240, 0.8);
  border-radius: var(--radius-md);
  background: var(--c-surface);
  color: var(--c-text-secondary);
  font-size: 12px;
  font-weight: 500;
  font-family: var(--font-sans);
  cursor: pointer;
  transition: all 200ms var(--ease);
}

@media (hover: hover) {
  .arv-dur-btn:not(.arv-dur-btn--active):not(.arv-dur-btn--permanent):hover {
    border-color: #cbd5e1;
    background: #f1f5f9;
    color: #475569;
  }
}

.arv-dur-btn--active {
  border-color: var(--c-accent);
  background: var(--c-accent);
  color: #fff;
  cursor: pointer;
}

.arv-dur-btn--permanent {
  border-color: var(--c-danger);
  background: var(--c-danger);
  color: #fff;
  cursor: pointer;
}

.arv-dur-preview {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--c-text-muted);
  padding: 4px 0;
}

.arv-dur-preview i {
  font-size: 11px;
}

.arv-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 16px 24px;
  border-top: 1px solid rgba(241, 245, 249, 0.8);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity var(--dur-fast) var(--ease);
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
