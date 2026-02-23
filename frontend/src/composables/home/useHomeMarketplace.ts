import { computed, ref } from 'vue'
import { fetchAcceptedTasks, fetchCategories, fetchPublishedTasks, fetchTasks } from '../../api/tasks'
import { fetchWorkers } from '../../api/users'
import type { Category, Task, WorkerProfile } from '../../types/api'
import type { HomeTaskSort, HomeWorkerSort } from './model'
import { sortTasksByMode, sortWorkersByMode } from './ranking'

interface UseHomeMarketplaceOptions {
  isAuthenticated: () => boolean
  onBootstrapError: (error: unknown) => void
}

export function useHomeMarketplace(options: UseHomeMarketplaceOptions) {
  const taskSort = ref<HomeTaskSort>('ranking')
  const workerSort = ref<HomeWorkerSort>('ranking')
  const searchQuery = ref('')
  const workerSearchQuery = ref('')
  const selectedCategory = ref<number | null>(null)
  const selectedWorkerCategory = ref<number | null>(null)

  const loading = ref(false)
  const categories = ref<Category[]>([])
  const allTasks = ref<Task[]>([])
  const myPublished = ref<Task[]>([])
  const myAccepted = ref<Task[]>([])
  const allWorkers = ref<WorkerProfile[]>([])
  const totalWorkerCount = ref(0)

  const totalTaskCount = computed(() => categories.value.reduce((sum, category) => sum + category.task_count, 0))

  const tasks = computed(() => {
    let result = [...allTasks.value]

    if (searchQuery.value.trim()) {
      const keyword = searchQuery.value.trim().toLowerCase()
      result = result.filter(
        (task) =>
          task.title.toLowerCase().includes(keyword) ||
          task.description.toLowerCase().includes(keyword) ||
          (task.location && task.location.toLowerCase().includes(keyword)),
      )
    }

    if (selectedCategory.value !== null) {
      result = result.filter((task) => task.category_id === selectedCategory.value)
    }

    return sortTasksByMode(result, taskSort.value)
  })

  const workers = computed(() => {
    let result = [...allWorkers.value]

    if (workerSearchQuery.value.trim()) {
      const keyword = workerSearchQuery.value.trim().toLowerCase()
      result = result.filter(
        (worker) =>
          worker.display_name.toLowerCase().includes(keyword) ||
          (worker.bio && worker.bio.toLowerCase().includes(keyword)) ||
          worker.skill_tags.some((tag) => tag.name.toLowerCase().includes(keyword)),
      )
    }

    if (selectedWorkerCategory.value !== null) {
      const categoryId = selectedWorkerCategory.value
      result = result.filter((worker) => worker.skill_tags.some((tag) => tag.id === categoryId))
    }

    return sortWorkersByMode(result, workerSort.value)
  })

  function categoryName(id: number | null) {
    if (!id) return null
    return categories.value.find((category) => category.id === id)?.name ?? null
  }

  async function loadCategories() {
    categories.value = await fetchCategories()
  }

  async function loadTasks() {
    allTasks.value = await fetchTasks({ status: 'open' })
  }

  async function loadWorkers() {
    allWorkers.value = await fetchWorkers({})
    totalWorkerCount.value = allWorkers.value.length
  }

  async function loadMyTasks() {
    const [published, accepted] = await Promise.all([fetchPublishedTasks(), fetchAcceptedTasks()])
    myPublished.value = published
    myAccepted.value = accepted
  }

  async function bootstrap() {
    loading.value = true
    try {
      const loads = [loadCategories(), loadTasks(), loadWorkers()]
      if (options.isAuthenticated()) {
        loads.push(loadMyTasks())
      }
      await Promise.all(loads)
    } catch (error) {
      options.onBootstrapError(error)
    } finally {
      loading.value = false
    }
  }

  return {
    taskSort,
    workerSort,
    searchQuery,
    workerSearchQuery,
    selectedCategory,
    selectedWorkerCategory,
    loading,
    categories,
    allTasks,
    myPublished,
    myAccepted,
    allWorkers,
    totalWorkerCount,
    totalTaskCount,
    tasks,
    workers,
    categoryName,
    loadCategories,
    loadTasks,
    loadWorkers,
    loadMyTasks,
    bootstrap,
  }
}
