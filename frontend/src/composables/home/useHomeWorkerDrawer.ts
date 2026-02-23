import { ref, type ComputedRef } from 'vue'
import type { Router } from 'vue-router'
import { appConfirm } from '../../components/AppConfirm.vue'
import { blockUser } from '../../api/moderation'
import { fetchUserReviews, fetchWorkerDetail, revealWorkerContact } from '../../api/users'
import type { UserReview, WorkerContactReveal, WorkerProfile } from '../../types/api'
import type { AppToastNotifier } from '../useAppToast'
import type { CaptchaScene } from '../../utils/captcha'
import { extractError } from '../../utils/error'

interface UseHomeWorkerDrawerOptions {
  isAuthenticated: ComputedRef<boolean>
  router: Router
  showToast: AppToastNotifier
  loadTasks: () => Promise<void>
  loadWorkers: () => Promise<void>
  requestCaptcha: (scene: CaptchaScene) => Promise<string | null>
}

export function useHomeWorkerDrawer(options: UseHomeWorkerDrawerOptions) {
  const selectedWorker = ref<WorkerProfile | null>(null)
  const workerHistoryReviews = ref<UserReview[]>([])
  const workerContactReveal = ref<WorkerContactReveal | null>(null)
  const workerContactLoading = ref(false)

  async function openWorkerDrawer(worker: WorkerProfile) {
    workerContactReveal.value = null
    workerContactLoading.value = false
    try {
      const [detail, reviews] = await Promise.all([
        fetchWorkerDetail(worker.user_id),
        fetchUserReviews(worker.user_id, 'worker'),
      ])
      selectedWorker.value = detail
      workerHistoryReviews.value = reviews
    } catch (error) {
      options.showToast(extractError(error, '加载接单者详情失败'), 'error')
    }
  }

  function closeWorkerDrawer() {
    selectedWorker.value = null
    workerHistoryReviews.value = []
    workerContactReveal.value = null
    workerContactLoading.value = false
  }

  async function handleWorkerContactAction(action: 'view_contact' | 'internal_contact') {
    if (!selectedWorker.value) return

    if (action === 'internal_contact') {
      if (!options.isAuthenticated.value) {
        options.showToast('请先登录后再使用站内联系', 'info')
        options.router.push('/login')
        return
      }
      const workerId = selectedWorker.value.user_id
      closeWorkerDrawer()
      options.router.push({ path: '/chat', query: { peer: String(workerId) } })
      return
    }

    if (!options.isAuthenticated.value) {
      options.showToast('请先登录后再查看联系方式', 'info')
      options.router.push('/login')
      return
    }

    workerContactLoading.value = true
    try {
      const captchaToken = await options.requestCaptcha('view_worker_contact')
      if (!captchaToken) return

      const reveal = await revealWorkerContact(selectedWorker.value.user_id, captchaToken)
      workerContactReveal.value = reveal
      if (!reveal.phone && !reveal.wechat) {
        options.showToast('该接单者暂未填写手机号或微信号', 'info')
      } else {
        options.showToast('联系方式已展示', 'success')
      }
    } catch (error) {
      options.showToast(extractError(error, '查看联系方式失败'), 'error')
    } finally {
      workerContactLoading.value = false
    }
  }

  async function handleBlockWorkerUser(userId: number) {
    const yes = await appConfirm({
      title: '确认拉黑',
      message: '拉黑后双方将无法看到对方的任务和接单信息。确认拉黑？',
      confirmText: '拉黑',
      type: 'danger',
    })
    if (!yes) return
    try {
      await blockUser({ blocked_user_id: userId })
      closeWorkerDrawer()
      options.showToast('已拉黑该用户', 'success')
      await Promise.all([options.loadTasks(), options.loadWorkers()])
    } catch (error) {
      options.showToast(extractError(error, '拉黑失败'), 'error')
    }
  }

  return {
    selectedWorker,
    workerHistoryReviews,
    workerContactReveal,
    workerContactLoading,
    openWorkerDrawer,
    closeWorkerDrawer,
    handleWorkerContactAction,
    handleBlockWorkerUser,
  }
}
