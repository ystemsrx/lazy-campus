<script setup lang="ts">
import { proxyRefs } from 'vue'

import type { AdminCategoriesModel } from '../../composables/admin/useAdminCategories'
import AdminCategoryModal from './AdminCategoryModal.vue'

const props = defineProps<{
  model: AdminCategoriesModel
}>()

const vm = proxyRefs(props.model)
</script>

<template>
  <section class="av-section">
    <div class="av-users-header">
      <h2>类别管理</h2>
      <span class="av-users-total">共 {{ vm.categoryList.length }} 个</span>
      <button class="btn btn-primary btn-sm av-add-btn" @click="vm.openCategoryModal(null)">
        <i class="fa-solid fa-plus"></i>
        添加类别
      </button>
    </div>
    <p class="av-category-hint">类别同时用于任务分类和接单者擅长领域</p>

    <div v-if="vm.categoryLoading" class="av-users-loading">
      <div class="spinner"></div>
    </div>

    <div v-else-if="vm.categoryList.length === 0" class="av-empty">
      <i class="fa-solid fa-tags av-empty__icon"></i>
      暂无类别，点击上方按钮添加
    </div>

    <div v-else class="av-category-grid">
      <div v-for="category in vm.categoryList" :key="category.id" class="card av-category-card">
        <div class="av-category-card__main">
          <h4 class="av-category-card__name">{{ category.name }}</h4>
          <p v-if="category.description" class="av-category-card__desc">{{ category.description }}</p>
          <div class="av-category-card__stats">
            <span class="badge badge-blue">{{ category.task_count }} 个任务</span>
            <span class="badge badge-green">{{ category.worker_count }} 位接单者</span>
            <span class="av-category-card__order">排序: {{ category.sort_order }}</span>
          </div>
        </div>
        <div class="av-category-card__actions">
          <button class="av-action-btn" title="编辑" @click="vm.openCategoryModal(category)">
            <i class="fa-solid fa-pen"></i>
          </button>
          <button
            class="av-action-btn av-action-btn--danger"
            title="删除"
            @click="vm.handleDeleteCategory(category)"
          >
            <i class="fa-solid fa-trash"></i>
          </button>
        </div>
      </div>
    </div>
  </section>

  <AdminCategoryModal
    :show="vm.showCategoryModal"
    :is-editing="Boolean(vm.editingCategory)"
    :name="vm.categoryForm.name"
    :description="vm.categoryForm.description"
    :sort-order="vm.categoryForm.sort_order"
    :submitting="vm.categorySubmitting"
    @update:name="vm.categoryForm.name = $event"
    @update:description="vm.categoryForm.description = $event"
    @update:sort-order="vm.categoryForm.sort_order = $event"
    @close="vm.closeCategoryModal"
    @confirm="vm.submitCategory"
  />
</template>

<style scoped>
.av-section {
  padding: 0;
}

.av-users-header {
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 16px;
}

.av-users-total {
  font-size: var(--text-sm);
  color: #94a3b8;
  font-weight: 500;
}

.av-add-btn {
  margin-left: auto;
  border-radius: var(--radius-md);
}

.av-category-hint {
  color: #94a3b8;
  font-size: var(--text-sm);
  margin: -8px 0 20px;
}

.av-users-loading {
  display: flex;
  justify-content: center;
  padding: 48px 0;
}

.av-empty {
  text-align: center;
  color: #94a3b8;
  padding: 60px 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.av-empty__icon {
  font-size: 40px;
  display: block;
  margin-bottom: 8px;
  color: #cbd5e1;
}

.av-category-grid {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-width: 720px;
}

.av-category-card {
  display: flex;
  align-items: center;
  gap: 16px;
  border-radius: var(--radius-2xl) !important;
  border: 1px solid rgba(226, 232, 240, 0.6) !important;
  box-shadow: var(--shadow-card) !important;
  transition: box-shadow 200ms var(--ease);
}

.av-category-card:hover {
  box-shadow: var(--shadow-card-hover) !important;
}

.av-category-card__main {
  flex: 1;
  min-width: 0;
}

.av-category-card__name {
  margin: 0 0 2px;
  font-size: var(--text-base);
}

.av-category-card__desc {
  margin: 0 0 6px;
  font-size: var(--text-sm);
  color: #94a3b8;
}

.av-category-card__stats {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.av-category-card__order {
  font-size: var(--text-xs);
  color: #94a3b8;
}

.av-category-card__actions {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}

.av-action-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: none;
  border-radius: var(--radius-md);
  background: transparent;
  font-size: 14px;
  transition: all 200ms var(--ease);
  color: #94a3b8;
}

.av-action-btn:hover {
  color: var(--c-accent);
  background: rgba(59, 130, 246, 0.06);
}

.av-action-btn--danger:hover {
  color: #ef4444;
  background: rgba(239, 68, 68, 0.06);
}
</style>
