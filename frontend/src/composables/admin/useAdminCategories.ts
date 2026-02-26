import { ref } from 'vue'

import { createCategory, deleteCategory, fetchCategories, updateCategory } from '../../api/tasks'
import { appConfirm } from '../../components/AppConfirm.vue'
import type { Category } from '../../types/api'
import { extractError } from '../../utils/error'
import type { AppToastNotifier } from '../useAppToast'

interface CategoryForm {
  name: string
  description: string
  sort_order: number
  ai_agent_enabled: boolean
}

export function useAdminCategories(showToast: AppToastNotifier) {
  const categoryList = ref<Category[]>([])
  const categoryLoading = ref(false)
  const showCategoryModal = ref(false)
  const editingCategory = ref<Category | null>(null)
  const categoryForm = ref<CategoryForm>({ name: '', description: '', sort_order: 0, ai_agent_enabled: false })
  const categorySubmitting = ref(false)

  async function loadCategories() {
    categoryLoading.value = true
    try {
      categoryList.value = await fetchCategories()
    } catch (error: unknown) {
      showToast(extractError(error, '加载类别失败'), 'error')
    } finally {
      categoryLoading.value = false
    }
  }

  function openCategoryModal(category: Category | null) {
    editingCategory.value = category
    categoryForm.value = category
      ? {
          name: category.name,
          description: category.description || '',
          sort_order: category.sort_order,
          ai_agent_enabled: category.ai_agent_enabled,
        }
      : {
          name: '',
          description: '',
          sort_order: categoryList.value.length + 1,
          ai_agent_enabled: false,
        }
    showCategoryModal.value = true
  }

  function closeCategoryModal() {
    showCategoryModal.value = false
  }

  async function submitCategory() {
    if (!categoryForm.value.name.trim()) {
      showToast('请输入类别名称', 'error')
      return
    }
    categorySubmitting.value = true
    try {
      const payload = {
        name: categoryForm.value.name.trim(),
        description: categoryForm.value.description.trim() || undefined,
        sort_order: categoryForm.value.sort_order,
        ai_agent_enabled: categoryForm.value.ai_agent_enabled,
      }
      if (editingCategory.value) {
        await updateCategory(editingCategory.value.id, payload)
        showToast('类别已更新', 'success')
      } else {
        await createCategory(payload)
        showToast('类别已添加', 'success')
      }
      showCategoryModal.value = false
      await loadCategories()
    } catch (error: unknown) {
      showToast(extractError(error, '保存失败'), 'error')
    } finally {
      categorySubmitting.value = false
    }
  }

  async function saveSortOrder(orderedIds: number[]) {
    // orderedIds 是拖拽后的 id 排列顺序（原始顺序，sort_order 字段尚未改写）
    const snapshot = categoryList.value.slice()
    const idToCategory = new Map(snapshot.map(c => [c.id, c]))

    try {
      await Promise.all(
        orderedIds.map((id, i) => {
          const cat = idToCategory.get(id)
          if (!cat) return Promise.resolve()
          return updateCategory(id, {
            name: cat.name,
            description: cat.description || undefined,
            sort_order: i + 1,
            ai_agent_enabled: cat.ai_agent_enabled,
          })
        }),
      )
      // 本地同步新顺序，避免重新请求
      categoryList.value = orderedIds
        .map(id => idToCategory.get(id))
        .filter((c): c is Category => !!c)
        .map((cat, i) => ({ ...cat, sort_order: i + 1 }))
      showToast('排序已保存', 'success')
    } catch (error: unknown) {
      showToast(extractError(error, '保存排序失败'), 'error')
      await loadCategories()
    }
  }

  async function handleDeleteCategory(category: Category) {
    const warnings: string[] = []
    if (category.task_count > 0) {
      warnings.push(`${category.task_count} 个任务`)
    }
    if (category.worker_count > 0) {
      warnings.push(`${category.worker_count} 位接单者`)
    }
    const extra = warnings.length ? `\n当前有 ${warnings.join('、')} 使用此类别。` : ''
    const yes = await appConfirm({
      title: '确认删除',
      message: `确定删除类别「${category.name}」？${extra}`,
      confirmText: '删除',
      type: 'danger',
    })
    if (!yes) {
      return
    }

    try {
      await deleteCategory(category.id)
      showToast('类别已删除', 'success')
      await loadCategories()
    } catch (error: unknown) {
      showToast(extractError(error, '删除失败'), 'error')
    }
  }

  return {
    categoryList,
    categoryLoading,
    showCategoryModal,
    editingCategory,
    categoryForm,
    categorySubmitting,
    loadCategories,
    openCategoryModal,
    closeCategoryModal,
    submitCategory,
    saveSortOrder,
    handleDeleteCategory,
  }
}

export type AdminCategoriesModel = ReturnType<typeof useAdminCategories>
