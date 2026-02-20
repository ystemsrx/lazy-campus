<script setup lang="ts">
defineProps<{
  show: boolean
  isEditing: boolean
  name: string
  description: string
  sortOrder: number
  submitting: boolean
}>()

const emit = defineEmits<{
  close: []
  confirm: []
  'update:name': [value: string]
  'update:description': [value: string]
  'update:sort-order': [value: number]
}>()

function updateName(event: Event) {
  const target = event.target as HTMLInputElement
  emit('update:name', target.value)
}

function updateDescription(event: Event) {
  const target = event.target as HTMLInputElement
  emit('update:description', target.value)
}

function updateSortOrder(event: Event) {
  const target = event.target as HTMLInputElement
  emit('update:sort-order', Number(target.value))
}
</script>

<template>
  <Transition name="fade">
    <div v-if="show" class="av-modal-overlay" @click.self="$emit('close')">
      <div class="av-modal">
        <div class="av-modal__header">
          <h3>{{ isEditing ? '编辑类别' : '添加类别' }}</h3>
          <button class="btn btn-ghost btn-sm" @click="$emit('close')">
            <i class="fa-solid fa-xmark"></i>
          </button>
        </div>
        <div class="av-modal__body">
          <div class="form-group">
            <label class="form-label">名称</label>
            <input
              :value="name"
              class="form-input"
              placeholder="输入类别名称"
              @input="updateName"
              @keyup.enter="$emit('confirm')"
            />
          </div>
          <div class="form-group">
            <label class="form-label">描述（选填）</label>
            <input
              :value="description"
              class="form-input"
              placeholder="输入类别描述"
              @input="updateDescription"
            />
          </div>
          <div class="form-group">
            <label class="form-label">排序（越小越靠前）</label>
            <input
              :value="sortOrder"
              class="form-input"
              type="number"
              @input="updateSortOrder"
            />
          </div>
        </div>
        <div class="av-modal__footer">
          <button class="btn btn-outline btn-sm" @click="$emit('close')">取消</button>
          <button class="btn btn-primary btn-sm" :disabled="submitting" @click="$emit('confirm')">
            {{ submitting ? '保存中…' : '保存' }}
          </button>
        </div>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.av-modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 100;
  background: rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.av-modal {
  background: var(--c-surface);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xl);
  width: min(440px, 100%);
  overflow: hidden;
}

.av-modal__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid var(--c-border-light);
}

.av-modal__header h3 {
  margin: 0;
}

.av-modal__body {
  padding: 20px;
}

.av-modal__footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 12px 20px;
  border-top: 1px solid var(--c-border-light);
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
