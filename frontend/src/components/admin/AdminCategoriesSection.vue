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
  color: var(--c-text-muted);
  font-weight: 500;
}

.av-add-btn {
  margin-left: auto;
}

.av-category-hint {
  color: var(--c-text-muted);
  font-size: var(--text-sm);
  margin: -8px 0 16px;
}

.av-users-loading {
  display: flex;
  justify-content: center;
  padding: 40px 0;
}

.av-empty {
  text-align: center;
  color: var(--c-text-muted);
  padding: 48px 20px;
}

.av-empty__icon {
  font-size: 36px;
  display: block;
  margin-bottom: 12px;
  color: var(--c-border);
}

.av-category-grid {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-width: 700px;
}

.av-category-card {
  display: flex;
  align-items: center;
  gap: 16px;
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
  color: var(--c-text-muted);
}

.av-category-card__stats {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.av-category-card__order {
  font-size: var(--text-xs);
  color: var(--c-text-muted);
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
  border-radius: var(--radius-sm);
  background: transparent;
  font-size: 14px;
  transition: all var(--dur-fast) var(--ease);
  color: var(--c-text-muted);
}

.av-action-btn:hover {
  color: var(--c-accent);
  background: var(--c-accent-light);
}

.av-action-btn--danger:hover {
  color: var(--c-danger);
  background: var(--c-danger-light);
}
</style>
