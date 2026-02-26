import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'

import { fetchAgentAvailability, startTaskAgent } from '../api/agent'
import { createTask, fetchCategories } from '../api/tasks'
import { appSlideCaptcha } from '../components/AppSlideCaptcha.vue'
import { useAuthStore } from '../stores/auth'
import type { AgentAvailability, Category } from '../types/api'
import { CaptchaCancelledError, withCaptchaRetry } from '../utils/captcha'
import { extractError } from '../utils/error'
import { localToUTC } from '../utils/time'

export type QuickTaskEditorForm = {
  title: string
  description: string
  deadline: string
  location: string
  price: number
  category_id: number | null
  contact_visibility: 'after_accept' | 'internal_only'
  contact_info: string
  required_gender: 'male' | 'female' | null
  icon: string
}

function createTaskEditorForm(): QuickTaskEditorForm {
  return {
    title: '',
    description: '',
    deadline: '',
    location: '',
    price: 20,
    category_id: null,
    contact_visibility: 'after_accept',
    contact_info: '',
    required_gender: null,
    icon: 'Hexagon',
  }
}

export function useQuickTaskPublish(options: {
  showToast: (text: string, type?: 'info' | 'warning' | 'error' | 'success') => void
}) {
  const router = useRouter()
  const auth = useAuthStore()

  const showCreateModal = ref(false)
  const publishCategories = ref<Category[]>([])
  const newTask = ref<QuickTaskEditorForm>(createTaskEditorForm())
  const createWithAgentSubmitting = ref(false)
  const agentAvailability = ref<AgentAvailability | null>(null)
  const bootstrapped = ref(false)
  const loadingBootstrap = ref(false)

  const createCategorySupportsAgent = computed(() => {
    if (!newTask.value.category_id) return false
    return publishCategories.value.some(
      (category) => category.id === newTask.value.category_id && category.ai_agent_enabled,
    )
  })

  const canCreateWithAgent = computed(() => {
    if (!auth.isAuthenticated) return false
    if (!agentAvailability.value?.agent_enabled) return false
    if ((agentAvailability.value.remaining_count ?? 0) <= 0) return false
    return createCategorySupportsAgent.value
  })

  async function bootstrap() {
    if (bootstrapped.value || loadingBootstrap.value) return
    loadingBootstrap.value = true
    try {
      const [cats, availability] = await Promise.all([
        fetchCategories(),
        fetchAgentAvailability().catch(() => null),
      ])
      publishCategories.value = cats
      agentAvailability.value = availability
      bootstrapped.value = true
    } catch (error) {
      options.showToast(extractError(error, '加载发布配置失败'), 'error')
    } finally {
      loadingBootstrap.value = false
    }
  }

  async function openPublishModal() {
    if (!auth.isAuthenticated) {
      router.push('/login')
      return
    }
    await bootstrap()
    showCreateModal.value = true
  }

  async function submitPublishTask(mode: 'normal' | 'agent' = 'normal') {
    if (mode === 'agent' && !canCreateWithAgent.value) {
      options.showToast('当前任务不满足 AI 代理开启条件', 'error')
      return
    }
    if (mode === 'agent') createWithAgentSubmitting.value = true

    try {
      const created = await withCaptchaRetry(
        (captchaToken) =>
          createTask({
            title: newTask.value.title,
            description: newTask.value.description,
            deadline: newTask.value.deadline ? localToUTC(newTask.value.deadline) : null,
            location: newTask.value.location || null,
            price: Number(newTask.value.price),
            category_id: newTask.value.category_id,
            contact_visibility: newTask.value.contact_visibility,
            contact_info:
              newTask.value.contact_visibility === 'after_accept'
                ? newTask.value.contact_info || null
                : null,
            required_gender: newTask.value.required_gender,
            icon: newTask.value.icon,
            captcha_token: captchaToken ?? null,
          }),
        appSlideCaptcha,
      )

      let startedSessionId: string | null = null
      if (mode === 'agent') {
        try {
          const started = await startTaskAgent(created.id)
          startedSessionId = started.session_id
          agentAvailability.value = await fetchAgentAvailability().catch(() => agentAvailability.value)
        } catch (error) {
          options.showToast(extractError(error, '委托已发布，但启动 AI 代理失败'), 'error')
        }
      }

      options.showToast(mode === 'agent' ? '委托已发布，正在启动 AI 代理' : '委托发布成功', 'success')
      newTask.value = createTaskEditorForm()
      showCreateModal.value = false

      if (startedSessionId) {
        router.push(`/agent/${startedSessionId}`)
      }
    } catch (error) {
      if (error instanceof CaptchaCancelledError) return
      options.showToast(extractError(error, '发布失败'), 'error')
    } finally {
      createWithAgentSubmitting.value = false
    }
  }

  return {
    showCreateModal,
    newTask,
    publishCategories,
    canCreateWithAgent,
    createWithAgentSubmitting,
    openPublishModal,
    submitPublishTask,
  }
}
