<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, proxyRefs, ref } from 'vue'

import type { AdminCategoriesModel } from '../../composables/admin/useAdminCategories'
import type { Category } from '../../types/api'
import AdminCategoryModal from './AdminCategoryModal.vue'

const props = defineProps<{
  model: AdminCategoriesModel
}>()

const vm = proxyRefs(props.model)

const searchTerm = ref('')

const filteredList = computed(() => {
  if (!searchTerm.value) return vm.categoryList
  const term = searchTerm.value.toLowerCase()
  return vm.categoryList.filter((cat) => {
    const name = (cat.name || '').toLowerCase()
    const desc = (cat.description || '').toLowerCase()
    return name.includes(term) || desc.includes(term)
  })
})

// ======= FLIP 动画引擎 =======

const listRef = ref<HTMLElement | null>(null)
const draggedItemId = ref<number | null>(null)

const origins: Record<string, number> = {}

const dragData = {
  id: null as number | null,
  lastHoverIndex: -1,
  startY: 0,
  startX: 0,
  clone: null as HTMLElement | null,
}

function recordPositions() {
  if (!listRef.value) return
  const children = Array.from(listRef.value.children) as HTMLElement[]
  children.forEach((el) => {
    const id = el.getAttribute('data-id')
    if (id) origins[id] = el.offsetTop
  })
}

function flipAnimate() {
  if (!listRef.value) return
  const children = Array.from(listRef.value.children) as HTMLElement[]

  children.forEach((child) => {
    child.style.transition = 'none'
    child.style.transform = 'none'
  })
  void listRef.value.offsetHeight

  const newPositions = new Map<string, number>()
  children.forEach((child) => {
    const id = child.getAttribute('data-id')
    if (id) newPositions.set(id, child.offsetTop)
  })

  children.forEach((child) => {
    const id = child.getAttribute('data-id')
    if (!id) return
    const oldTop = origins[id]
    const newTop = newPositions.get(id)
    if (oldTop !== undefined && newTop !== undefined) {
      const deltaY = oldTop - newTop
      if (Math.abs(deltaY) > 0.5) {
        child.style.transform = `translateY(${deltaY}px)`
      }
    }
  })
  void listRef.value.offsetHeight

  children.forEach((child) => {
    const id = child.getAttribute('data-id')
    if (!id) return
    const oldTop = origins[id]
    const newTop = newPositions.get(id)
    if (oldTop !== undefined && newTop !== undefined) {
      const deltaY = oldTop - newTop
      if (Math.abs(deltaY) > 0.5) {
        child.style.transition = 'transform 300ms cubic-bezier(0.2, 0.8, 0.2, 1)'
        child.style.transform = 'translateY(0)'
      }
    }
    if (newTop !== undefined) origins[id] = newTop
  })
}

// ======= 自定义 Pointer 拖拽系统 =======

function handlePointerDown(e: PointerEvent, index: number, category: Category) {
  if (searchTerm.value !== '' || e.button !== 0 || draggedItemId.value !== null) return
  e.preventDefault()

  const rowElement = (e.currentTarget as HTMLElement).closest('.av-cat-row') as HTMLElement
  if (!rowElement) return

  const rect = rowElement.getBoundingClientRect()

  const clone = rowElement.cloneNode(true) as HTMLElement
  clone.style.position = 'fixed'
  clone.style.top = `${rect.top}px`
  clone.style.left = `${rect.left}px`
  clone.style.width = `${rect.width}px`
  clone.style.height = `${rect.height}px`
  clone.style.margin = '0'
  clone.style.zIndex = '9999'
  clone.style.pointerEvents = 'none'
  clone.style.backgroundColor = '#ffffff'
  clone.style.boxShadow = '0 25px 50px -12px rgba(0, 0, 0, 0.25), 0 0 0 1px rgba(0,0,0,0.05)'
  clone.style.borderRadius = '12px'
  clone.style.transform = 'scale(1.02) rotate(1deg)'
  clone.style.transition = 'transform 0.15s cubic-bezier(0.2, 0.8, 0.2, 1)'

  document.body.appendChild(clone)
  document.body.style.userSelect = 'none'

  dragData.id = category.id
  dragData.lastHoverIndex = index
  dragData.startY = e.clientY
  dragData.startX = e.clientX
  dragData.clone = clone

  recordPositions()
  draggedItemId.value = category.id

  window.addEventListener('pointermove', handlePointerMove)
  window.addEventListener('pointerup', handlePointerUp)
}

function handlePointerMove(e: PointerEvent) {
  if (!dragData.clone || !listRef.value) return

  const deltaY = e.clientY - dragData.startY
  const deltaX = e.clientX - dragData.startX

  dragData.clone.style.transition = 'none'
  dragData.clone.style.transform = `translate(${deltaX}px, ${deltaY}px) scale(1.02) rotate(1deg)`

  const elements = Array.from(listRef.value.children) as HTMLElement[]
  let hoverIndex = -1

  const containerRect = listRef.value.getBoundingClientRect()
  const mouseLocalY = e.clientY - containerRect.top + listRef.value.scrollTop

  elements.forEach((el, idx) => {
    const top = el.offsetTop
    const bottom = top + el.offsetHeight
    if (mouseLocalY >= top && mouseLocalY <= bottom) {
      hoverIndex = idx
    }
  })

  if (hoverIndex !== -1 && hoverIndex !== dragData.lastHoverIndex) {
    const indexSpan = dragData.clone.querySelector('.av-cat-order-num')
    if (indexSpan) indexSpan.textContent = String(hoverIndex + 1)

    elements.forEach((el) => {
      const id = el.getAttribute('data-id')
      if (id) origins[id] = el.offsetTop
    })

    dragData.lastHoverIndex = hoverIndex

    const list = [...vm.categoryList]
    const currentIdx = list.findIndex(c => c && c.id === dragData.id)
    if (currentIdx === -1 || currentIdx === hoverIndex) return

    const [item] = list.splice(currentIdx, 1)
    if (!item) return
    list.splice(hoverIndex, 0, item)
    vm.categoryList = list

    nextTick(() => flipAnimate())
  }
}

function handlePointerUp() {
  const { clone, id } = dragData

  window.removeEventListener('pointermove', handlePointerMove)
  window.removeEventListener('pointerup', handlePointerUp)
  document.body.style.userSelect = ''

  if (clone && id && listRef.value) {
    const targetSlot = listRef.value.querySelector(`[data-id="${id}"]`) as HTMLElement

    if (targetSlot) {
      const containerRect = listRef.value.getBoundingClientRect()
      const finalTop = containerRect.top + targetSlot.offsetTop - listRef.value.scrollTop
      const finalLeft = containerRect.left + targetSlot.offsetLeft

      const startX = parseFloat(clone.style.left)
      const startY = parseFloat(clone.style.top)

      const targetTranslateX = finalLeft - startX
      const targetTranslateY = finalTop - startY

      clone.style.transition = 'all 250ms cubic-bezier(0.2, 0.8, 0.2, 1)'
      clone.style.transform = `translate(${targetTranslateX}px, ${targetTranslateY}px) scale(1) rotate(0deg)`
      clone.style.boxShadow = 'inset 0 -1px 0 0 #f3f4f6'

      setTimeout(() => {
        if (clone.parentNode) clone.remove()
        draggedItemId.value = null

        // 取拖拽后当前列表的 id 顺序，传给 saveSortOrder 做 API 批量更新
        const orderedIds = vm.categoryList.map(c => c.id)
        vm.saveSortOrder(orderedIds)
      }, 250)
    } else {
      clone.remove()
      draggedItemId.value = null
    }
  } else {
    draggedItemId.value = null
  }

  dragData.id = null
  dragData.lastHoverIndex = -1
  dragData.startY = 0
  dragData.startX = 0
  dragData.clone = null
}

onBeforeUnmount(() => {
  window.removeEventListener('pointermove', handlePointerMove)
  window.removeEventListener('pointerup', handlePointerUp)
  if (dragData.clone?.parentNode) dragData.clone.remove()
})
</script>

<template>
  <section class="av-section">
    <!-- 操作栏：搜索 + 统计 + 添加 -->
    <div class="av-cat-toolbar">
      <div class="av-cat-search">
        <i class="fa-solid fa-magnifying-glass av-cat-search__icon"></i>
        <input
          v-model="searchTerm"
          type="text"
          class="av-cat-search__input"
          placeholder="搜索类别名称或描述..."
        />
        <button v-if="searchTerm" class="av-cat-search__clear" @click="searchTerm = ''">
          <i class="fa-solid fa-xmark"></i>
        </button>
      </div>
      <div class="av-cat-toolbar__right">
        <span class="av-cat-count">共 {{ vm.categoryList.length }} 个类别</span>
        <button class="btn btn-primary btn-sm av-cat-add-btn" @click="vm.openCategoryModal(null)">
          <i class="fa-solid fa-plus"></i>
          新建类别
        </button>
      </div>
    </div>

    <p class="av-cat-hint">类别同时用于任务分类和接单者擅长领域</p>

    <!-- 加载中 -->
    <div v-if="vm.categoryLoading" class="av-cat-loading">
      <div class="spinner"></div>
    </div>

    <!-- 空状态 -->
    <div v-else-if="filteredList.length === 0" class="av-cat-empty">
      <i class="fa-solid fa-tags av-cat-empty__icon"></i>
      <template v-if="searchTerm">
        <p class="av-cat-empty__title">未找到任何类别</p>
        <p class="av-cat-empty__sub">尝试调整搜索词或新建一个类别</p>
      </template>
      <template v-else>
        <p class="av-cat-empty__title">暂无类别</p>
        <p class="av-cat-empty__sub">点击上方按钮添加第一个类别</p>
      </template>
    </div>

    <!-- 类别列表 -->
    <div v-else class="av-cat-table">
      <!-- 表头 -->
      <div class="av-cat-thead">
        <div class="av-cat-col av-cat-col--order">排序</div>
        <div class="av-cat-col av-cat-col--name">类别名称</div>
        <div class="av-cat-col av-cat-col--desc">描述说明</div>
        <div class="av-cat-col av-cat-col--stats">统计</div>
        <div class="av-cat-col av-cat-col--actions">操作</div>
      </div>

      <!-- 列表体 -->
      <div ref="listRef" class="av-cat-tbody">
        <div
          v-for="(category, index) in filteredList"
          :key="category.id"
          :data-id="category.id"
          :class="[
            'av-cat-row',
            draggedItemId === category.id ? 'av-cat-row--slot' : 'av-cat-row--normal',
          ]"
        >
          <!-- 拖拽手柄 + 排序序号 -->
          <div class="av-cat-col av-cat-col--order">
            <div
              :class="['av-cat-grip', { 'av-cat-grip--disabled': searchTerm !== '' }]"
              :style="{ touchAction: 'none' }"
              title="按住拖动排序"
              @pointerdown="handlePointerDown($event, index, category)"
            >
              <i class="fa-solid fa-grip-vertical"></i>
            </div>
            <span class="av-cat-order-num">{{ index + 1 }}</span>
          </div>

          <!-- 名称 -->
          <div class="av-cat-col av-cat-col--name">
            <span class="av-cat-name-text">{{ category.name }}</span>
          </div>

          <!-- 描述 -->
          <div class="av-cat-col av-cat-col--desc">
            <span v-if="category.description" class="av-cat-desc-text">{{ category.description }}</span>
            <span v-else class="av-cat-no-desc">暂无描述</span>
          </div>

          <!-- 统计 -->
          <div class="av-cat-col av-cat-col--stats">
            <span class="badge badge-blue">{{ category.task_count }} 个任务</span>
            <span class="badge badge-green">{{ category.worker_count }} 位接单者</span>
          </div>

          <!-- 操作 -->
          <div class="av-cat-col av-cat-col--actions">
            <button class="av-cat-action" title="编辑" @click="vm.openCategoryModal(category)">
              <i class="fa-solid fa-pen"></i>
            </button>
            <button
              class="av-cat-action"
              :class="category.task_count > 0 ? 'av-cat-action--disabled' : 'av-cat-action--danger'"
              :disabled="category.task_count > 0"
              :title="category.task_count > 0 ? `该类别下有 ${category.task_count} 个任务，无法删除` : '删除'"
              @click="vm.handleDeleteCategory(category)"
            >
              <i class="fa-solid fa-trash"></i>
            </button>
          </div>
        </div>
      </div>
    </div>
  </section>

  <AdminCategoryModal
    :show="vm.showCategoryModal"
    :is-editing="Boolean(vm.editingCategory)"
    :name="vm.categoryForm.name"
    :description="vm.categoryForm.description"
    :submitting="vm.categorySubmitting"
    @update:name="vm.categoryForm.name = $event"
    @update:description="vm.categoryForm.description = $event"
    @close="vm.closeCategoryModal"
    @confirm="vm.submitCategory"
  />
</template>

<style scoped>
.av-section {
  padding: 0;
}

/* ======== 操作栏 ======== */

.av-cat-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 16px;
  margin-bottom: 12px;
}

.av-cat-search {
  position: relative;
  width: 320px;
  max-width: 100%;
}

.av-cat-search__icon {
  position: absolute;
  left: 14px;
  top: 50%;
  transform: translateY(-50%);
  color: #94a3b8;
  font-size: 14px;
  pointer-events: none;
}

.av-cat-search__input {
  width: 100%;
  padding: 10px 36px 10px 40px;
  border: 1px solid rgba(226, 232, 240, 0.8);
  border-radius: 12px;
  background: #fff;
  font-size: 14px;
  color: var(--c-text);
  outline: none;
  transition: border-color 200ms ease, box-shadow 200ms ease;
}

.av-cat-search__input::placeholder {
  color: #94a3b8;
}

.av-cat-search__input:focus {
  border-color: var(--c-accent);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.12);
}

.av-cat-search__clear {
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  width: 24px;
  height: 24px;
  border: none;
  background: transparent;
  color: #94a3b8;
  font-size: 12px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: color 150ms, background 150ms;
}

.av-cat-search__clear:hover {
  color: #64748b;
  background: rgba(100, 116, 139, 0.08);
}

.av-cat-toolbar__right {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-left: auto;
}

.av-cat-count {
  font-size: 13px;
  color: #64748b;
  font-weight: 500;
  background: rgba(241, 245, 249, 0.8);
  padding: 6px 14px;
  border-radius: 999px;
  white-space: nowrap;
}

.av-cat-add-btn {
  border-radius: 12px !important;
  gap: 8px;
  white-space: nowrap;
  transition: all 200ms ease !important;
}

.av-cat-add-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.25);
}

.av-cat-hint {
  color: #94a3b8;
  font-size: 13px;
  margin: 0 0 20px;
}

/* ======== 加载 & 空状态 ======== */

.av-cat-loading {
  display: flex;
  justify-content: center;
  padding: 48px 0;
}

.av-cat-empty {
  text-align: center;
  color: #94a3b8;
  padding: 60px 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.av-cat-empty__icon {
  font-size: 48px;
  display: block;
  margin-bottom: 12px;
  color: #cbd5e1;
}

.av-cat-empty__title {
  font-size: 16px;
  font-weight: 600;
  color: var(--c-text);
  margin: 0;
}

.av-cat-empty__sub {
  font-size: 13px;
  color: #94a3b8;
  margin: 4px 0 0;
}

/* ======== 表格容器 ======== */

.av-cat-table {
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04), 0 1px 2px rgba(0, 0, 0, 0.02);
  border: 1px solid rgba(241, 245, 249, 0.8);
  overflow: hidden;
}

/* ======== 表头 ======== */

.av-cat-thead {
  display: none;
}

@media (min-width: 640px) {
  .av-cat-thead {
    display: grid;
    grid-template-columns: 80px 1.2fr 2fr 1fr 100px;
    gap: 16px;
    padding: 14px 24px;
    border-bottom: 1px solid rgba(241, 245, 249, 0.8);
    background: rgba(248, 250, 252, 0.5);
  }
}

.av-cat-thead .av-cat-col {
  font-size: 12px;
  font-weight: 600;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.av-cat-thead .av-cat-col--order {
  text-align: center;
}

.av-cat-thead .av-cat-col--actions {
  text-align: right;
}

/* ======== 列表体 ======== */

.av-cat-tbody {
  position: relative;
  width: 100%;
  background: #fff;
}

/* ======== 列表行 ======== */

.av-cat-row {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 16px 20px;
  align-items: flex-start;
  background: #fff;
  transition: background-color 200ms ease;
  box-shadow: inset 0 -1px 0 0 rgba(241, 245, 249, 0.8);
}

@media (min-width: 640px) {
  .av-cat-row {
    display: grid;
    grid-template-columns: 80px 1.2fr 2fr 1fr 100px;
    gap: 16px;
    padding: 16px 24px;
    align-items: center;
  }
}

.av-cat-row:last-child {
  box-shadow: none;
}

.av-cat-row--normal {
  opacity: 1;
  z-index: 10;
}

.av-cat-row--normal:hover {
  background: rgba(248, 250, 252, 0.8);
}

.av-cat-row--slot {
  background: rgba(219, 234, 254, 0.3);
  box-shadow: inset 0 0 0 2px #93c5fd;
  border-radius: 12px;
  z-index: 0;
}

.av-cat-row--slot > * {
  opacity: 0;
}

/* ---- 排序列 ---- */

.av-cat-col--order {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.av-cat-grip {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 6px;
  border-radius: 8px;
  color: #94a3b8;
  cursor: grab;
  transition: color 200ms ease, background 200ms ease;
}

.av-cat-grip:active {
  cursor: grabbing;
}

.av-cat-grip:hover {
  color: var(--c-accent);
  background: rgba(59, 130, 246, 0.08);
}

.av-cat-grip--disabled {
  color: #cbd5e1;
  cursor: default;
}

.av-cat-grip--disabled:hover {
  color: #cbd5e1;
  background: transparent;
}

.av-cat-order-num {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 20px;
  font-size: 13px;
  font-weight: 500;
  color: #94a3b8;
}

/* ---- 名称列 ---- */

.av-cat-name-text {
  font-size: 14px;
  font-weight: 600;
  color: var(--c-text);
}

/* ---- 描述列 ---- */

.av-cat-desc-text {
  font-size: 13px;
  color: #64748b;
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.av-cat-no-desc {
  font-size: 13px;
  color: #cbd5e1;
  font-style: italic;
}

/* ---- 统计列 ---- */

.av-cat-col--stats {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

/* ---- 操作列 ---- */

.av-cat-col--actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 4px;
}

/* ======== 操作按钮 ======== */

.av-cat-action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border: none;
  border-radius: 8px;
  background: transparent;
  font-size: 14px;
  color: #94a3b8;
  cursor: pointer;
  transition: all 200ms ease;
}

.av-cat-action:hover {
  color: var(--c-accent);
  background: rgba(59, 130, 246, 0.06);
}

.av-cat-action--danger:hover {
  color: #ef4444;
  background: rgba(239, 68, 68, 0.06);
}

.av-cat-action--disabled,
.av-cat-action--disabled:hover {
  opacity: 0.3;
  cursor: not-allowed;
  color: #94a3b8;
  background: transparent;
}

/* ======== 响应式 ======== */

@media (max-width: 639px) {
  .av-cat-toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .av-cat-search {
    width: 100%;
  }

  .av-cat-toolbar__right {
    margin-left: 0;
    justify-content: space-between;
  }

  .av-cat-col--order {
    order: 3;
    width: 100%;
    justify-content: flex-start;
    margin-top: 8px;
    padding-top: 8px;
    border-top: 1px solid rgba(241, 245, 249, 0.8);
  }

  .av-cat-col--actions {
    justify-content: flex-start;
  }
}
</style>
