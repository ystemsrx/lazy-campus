<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import { createReport, fetchMyReports } from '../api/moderation'
import {
  acceptTask,
  confirmTask,
  createReview,
  createTask,
  fetchAcceptedTasks,
  fetchCategories,
  fetchMessages,
  fetchPublishedTasks,
  fetchReviews,
  fetchTasks,
  sendMessage
} from '../api/tasks'
import { fetchMyWorkerProfile, fetchWorkers, updateWorkerProfile } from '../api/users'
import { useAuthStore } from '../stores/auth'
import type { Category, Report, Task, TaskMessage, TaskReview, WorkerProfile } from '../types/api'

const router = useRouter()
const auth = useAuthStore()

const mode = ref<'take' | 'find'>('take')
const loading = ref(false)
const message = ref('')

const categories = ref<Category[]>([])
const tasks = ref<Task[]>([])
const selectedTask = ref<Task | null>(null)
const myPublished = ref<Task[]>([])
const myAccepted = ref<Task[]>([])
const workers = ref<WorkerProfile[]>([])

const taskMessages = ref<TaskMessage[]>([])
const taskReviews = ref<TaskReview[]>([])
const myReports = ref<Report[]>([])

const newTask = ref({
  title: '',
  description: '',
  deadline: '',
  location: '',
  price: 20,
  category_id: null as number | null,
  contact_visibility: 'after_accept' as 'after_accept' | 'internal_only',
  contact_info: ''
})

const workerForm = ref({
  enabled: false,
  skills: '',
  min_price: null as number | null,
  max_price: null as number | null,
  bio: ''
})

const chatContent = ref('')
const reviewForm = ref({
  target_role: 'worker' as 'publisher' | 'worker',
  stars: 5,
  comment: ''
})

const reportForm = ref({
  type: 'report' as 'report' | 'appeal',
  reason: '',
  evidence: ''
})

const me = computed(() => auth.user)
const isParticipant = computed(() => {
  if (!me.value || !selectedTask.value) return false
  return selectedTask.value.publisher_id === me.value.id || selectedTask.value.assignee_id === me.value.id
})

const canAccept = computed(() => {
  if (!selectedTask.value || !me.value) return false
  return selectedTask.value.status === 'open' && selectedTask.value.publisher_id !== me.value.id
})

const canConfirm = computed(() => {
  if (!selectedTask.value || !me.value) return false
  return selectedTask.value.status === 'in_progress' && selectedTask.value.publisher_id === me.value.id
})

const canReview = computed(() => selectedTask.value?.status === 'completed' && isParticipant.value)

async function bootstrap() {
  loading.value = true
  message.value = ''
  try {
    await Promise.all([loadCategories(), loadTasks(), loadWorkers(), loadMyTasks(), loadMyReports(), loadMyWorkerProfile()])
  } catch (error: any) {
    message.value = error?.response?.data?.detail || '加载失败'
  } finally {
    loading.value = false
  }
}

async function loadCategories() {
  categories.value = await fetchCategories()
}

async function loadTasks() {
  tasks.value = await fetchTasks({ status: 'open', sort: 'ranking' })
}

async function loadWorkers() {
  workers.value = await fetchWorkers({})
}

async function loadMyTasks() {
  const [published, accepted] = await Promise.all([fetchPublishedTasks(), fetchAcceptedTasks()])
  myPublished.value = published
  myAccepted.value = accepted
}

async function loadMyWorkerProfile() {
  const p = await fetchMyWorkerProfile()
  workerForm.value = {
    enabled: p.enabled,
    skills: p.skills || '',
    min_price: p.min_price,
    max_price: p.max_price,
    bio: p.bio || ''
  }
}

async function loadMyReports() {
  myReports.value = await fetchMyReports()
}

async function selectTask(task: Task) {
  selectedTask.value = task
  await refreshTaskMeta()
}

async function refreshTaskMeta() {
  if (!selectedTask.value) return
  const taskId = selectedTask.value.id
  try {
    const [messages, reviews] = await Promise.all([fetchMessages(taskId), fetchReviews(taskId)])
    taskMessages.value = messages
    taskReviews.value = reviews
  } catch {
    taskMessages.value = []
    taskReviews.value = await fetchReviews(taskId)
  }
}

async function submitCreateTask() {
  try {
    await createTask({
      title: newTask.value.title,
      description: newTask.value.description,
      deadline: newTask.value.deadline || null,
      location: newTask.value.location || null,
      price: Number(newTask.value.price),
      category_id: newTask.value.category_id,
      contact_visibility: newTask.value.contact_visibility,
      contact_info: newTask.value.contact_visibility === 'after_accept' ? newTask.value.contact_info || null : null
    })
    message.value = '发布成功'
    newTask.value = {
      title: '',
      description: '',
      deadline: '',
      location: '',
      price: 20,
      category_id: null,
      contact_visibility: 'after_accept',
      contact_info: ''
    }
    await Promise.all([loadTasks(), loadMyTasks()])
  } catch (error: any) {
    message.value = error?.response?.data?.detail || '发布失败'
  }
}

async function submitWorkerProfile() {
  try {
    await updateWorkerProfile({
      enabled: workerForm.value.enabled,
      skills: workerForm.value.skills || null,
      min_price: workerForm.value.min_price,
      max_price: workerForm.value.max_price,
      bio: workerForm.value.bio || null
    })
    message.value = '接委托资料已更新'
    await loadWorkers()
  } catch (error: any) {
    message.value = error?.response?.data?.detail || '保存失败'
  }
}

async function handleAcceptTask() {
  if (!selectedTask.value) return
  try {
    selectedTask.value = await acceptTask(selectedTask.value.id)
    message.value = '已接取该委托'
    await Promise.all([loadTasks(), loadMyTasks(), refreshTaskMeta()])
  } catch (error: any) {
    message.value = error?.response?.data?.detail || '接取失败'
  }
}

async function handleConfirmTask() {
  if (!selectedTask.value) return
  try {
    selectedTask.value = await confirmTask(selectedTask.value.id)
    message.value = '已确认完成'
    await Promise.all([loadTasks(), loadMyTasks(), refreshTaskMeta()])
  } catch (error: any) {
    message.value = error?.response?.data?.detail || '确认失败'
  }
}

async function submitMessage() {
  if (!selectedTask.value || !chatContent.value.trim()) return
  try {
    await sendMessage(selectedTask.value.id, chatContent.value.trim())
    chatContent.value = ''
    await refreshTaskMeta()
  } catch (error: any) {
    message.value = error?.response?.data?.detail || '发送失败'
  }
}

async function submitReview() {
  if (!selectedTask.value) return
  try {
    await createReview(selectedTask.value.id, {
      target_role: reviewForm.value.target_role,
      stars: reviewForm.value.stars,
      comment: reviewForm.value.comment || undefined
    })
    reviewForm.value.comment = ''
    await refreshTaskMeta()
    message.value = '评价已提交'
  } catch (error: any) {
    message.value = error?.response?.data?.detail || '评价失败'
  }
}

async function submitReport() {
  if (!selectedTask.value) return
  try {
    await createReport({
      type: reportForm.value.type,
      task_id: selectedTask.value.id,
      reported_user_id: selectedTask.value.publisher_id,
      reason: reportForm.value.reason,
      evidence: reportForm.value.evidence
    })
    reportForm.value.reason = ''
    reportForm.value.evidence = ''
    await loadMyReports()
    message.value = '举报/申诉已提交，等待管理员审核'
  } catch (error: any) {
    message.value = error?.response?.data?.detail || '提交失败'
  }
}

function logout() {
  auth.logout()
  router.push('/login')
}

watch(selectedTask, async (task) => {
  if (!task || !me.value) return
  if (task.publisher_id === me.value.id) {
    reviewForm.value.target_role = 'worker'
  } else {
    reviewForm.value.target_role = 'publisher'
  }
})

onMounted(async () => {
  await bootstrap()
})
</script>

<template>
  <main class="container" style="padding: 20px 0 40px;">
    <header class="card" style="margin-bottom: 14px; display: flex; justify-content: space-between; align-items: center; gap: 8px; flex-wrap: wrap;">
      <div>
        <h2 style="margin: 0;">校园任务平台</h2>
        <p class="muted" style="margin: 4px 0 0;">你好，{{ auth.displayName }}。可以在“接委托”和“找委托”之间双向切换。</p>
      </div>
      <div class="row" style="width: auto;">
        <button class="btn ghost" @click="mode = 'take'" :style="mode === 'take' ? 'font-weight:700' : ''">接委托</button>
        <button class="btn ghost" @click="mode = 'find'" :style="mode === 'find' ? 'font-weight:700' : ''">找委托人</button>
        <button class="btn secondary" @click="logout">退出</button>
      </div>
    </header>

    <p v-if="message" class="card" style="margin-top: 0; color: #0f172a;">{{ message }}</p>

    <section class="grid-2" style="align-items: start;">
      <article class="card">
        <h3 style="margin-top: 0;">发布委托</h3>
        <div style="display: grid; gap: 8px;">
          <input v-model="newTask.title" class="input" placeholder="标题" />
          <textarea v-model="newTask.description" class="textarea" placeholder="描述与详细要求"></textarea>
          <div class="row">
            <input v-model="newTask.location" class="input" placeholder="地点" />
            <input v-model.number="newTask.price" class="input" type="number" min="1" placeholder="价格" />
          </div>
          <div class="row">
            <input v-model="newTask.deadline" class="input" type="datetime-local" />
            <select v-model.number="newTask.category_id" class="select">
              <option :value="null">选择类目</option>
              <option v-for="c in categories" :key="c.id" :value="c.id">{{ c.name }}</option>
            </select>
          </div>
          <div class="row">
            <select v-model="newTask.contact_visibility" class="select">
              <option value="after_accept">接取后可见联系方式</option>
              <option value="internal_only">永不展示，只站内聊</option>
            </select>
            <input
              v-model="newTask.contact_info"
              class="input"
              :disabled="newTask.contact_visibility === 'internal_only'"
              placeholder="联系方式"
            />
          </div>
          <button class="btn" @click="submitCreateTask">发布委托</button>
        </div>
      </article>

      <article class="card">
        <h3 style="margin-top: 0;">接单者资料设置</h3>
        <div style="display: grid; gap: 8px;">
          <label class="row" style="align-items: center;">
            <input v-model="workerForm.enabled" type="checkbox" />
            <span>开启接委托（出现在接单者列表）</span>
          </label>
          <input v-model="workerForm.skills" class="input" placeholder="擅长类型（如：高数、前端、跑腿）" />
          <div class="row">
            <input v-model.number="workerForm.min_price" class="input" type="number" placeholder="最低价" />
            <input v-model.number="workerForm.max_price" class="input" type="number" placeholder="最高价" />
          </div>
          <textarea v-model="workerForm.bio" class="textarea" placeholder="个人简介"></textarea>
          <button class="btn" @click="submitWorkerProfile">保存接单资料</button>
        </div>
      </article>
    </section>

    <section v-if="mode === 'take'" class="grid-2" style="margin-top: 14px; align-items: start;">
      <article class="card">
        <h3 style="margin-top: 0;">可接任务</h3>
        <div style="display: grid; gap: 8px; max-height: 580px; overflow: auto;">
          <button
            v-for="task in tasks"
            :key="task.id"
            class="btn ghost"
            style="text-align: left;"
            @click="selectTask(task)"
          >
            <div style="font-weight: 700;">{{ task.title }}（¥{{ task.price }}）</div>
            <div class="muted">发布者：{{ task.publisher_display_name }} ｜ 状态：{{ task.status }}</div>
          </button>
          <p v-if="tasks.length === 0" class="muted">暂无可接任务。</p>
        </div>
      </article>

      <article class="card" v-if="selectedTask">
        <h3 style="margin-top: 0;">任务详情</h3>
        <p><b>{{ selectedTask.title }}</b></p>
        <p class="muted">{{ selectedTask.description }}</p>
        <p class="muted">地点：{{ selectedTask.location || '未填写' }} ｜ 截止：{{ selectedTask.deadline || '未设置' }}</p>
        <p class="muted">联系方式：{{ selectedTask.contact_info || '仅参与者可见或站内沟通' }}</p>

        <div class="row" style="margin-bottom: 12px;">
          <button v-if="canAccept" class="btn" @click="handleAcceptTask">接取任务</button>
          <button v-if="canConfirm" class="btn secondary" @click="handleConfirmTask">确认完成</button>
        </div>

        <section class="card" style="padding: 12px; margin-bottom: 10px;">
          <h4 style="margin: 0 0 8px;">站内消息</h4>
          <div v-if="isParticipant" style="display: grid; gap: 6px; max-height: 180px; overflow: auto; margin-bottom: 8px;">
            <div v-for="m in taskMessages" :key="m.id" class="muted">
              <b>{{ m.sender_display_name }}</b>：{{ m.content }}
            </div>
          </div>
          <p v-else class="muted">仅参与者可见聊天内容。</p>
          <div v-if="isParticipant" class="row">
            <input v-model="chatContent" class="input" placeholder="输入消息" />
            <button class="btn" @click="submitMessage">发送</button>
          </div>
        </section>

        <section class="card" style="padding: 12px; margin-bottom: 10px;">
          <h4 style="margin: 0 0 8px;">双向互评</h4>
          <div style="display: grid; gap: 6px; margin-bottom: 8px;">
            <div v-for="r in taskReviews" :key="r.id" class="muted">
              {{ r.target_role }}: {{ r.stars }}星 {{ r.comment ? `- ${r.comment}` : '' }}
            </div>
            <p v-if="taskReviews.length === 0" class="muted">暂无评价</p>
          </div>
          <div v-if="canReview" class="row" style="align-items: flex-start;">
            <select v-model="reviewForm.target_role" class="select" style="max-width: 130px;">
              <option value="publisher">评价发布者</option>
              <option value="worker">评价接单者</option>
            </select>
            <input v-model.number="reviewForm.stars" class="input" type="number" min="1" max="5" style="max-width: 100px;" />
            <input v-model="reviewForm.comment" class="input" placeholder="可选评价文字" />
            <button class="btn" @click="submitReview">提交评价</button>
          </div>
        </section>

        <section class="card" style="padding: 12px;">
          <h4 style="margin: 0 0 8px;">举报/申诉</h4>
          <div class="row">
            <select v-model="reportForm.type" class="select" style="max-width: 120px;">
              <option value="report">举报</option>
              <option value="appeal">申诉</option>
            </select>
            <input v-model="reportForm.reason" class="input" placeholder="问题描述（必填）" />
          </div>
          <textarea v-model="reportForm.evidence" class="textarea" placeholder="证据说明（链接、截图信息等）"></textarea>
          <button class="btn" @click="submitReport">提交</button>
        </section>
      </article>

      <article v-else class="card">
        <p class="muted">从左侧选择一个任务查看详情。</p>
      </article>
    </section>

    <section v-if="mode === 'find'" class="grid-2" style="margin-top: 14px; align-items: start;">
      <article class="card">
        <h3 style="margin-top: 0;">接单者列表</h3>
        <div style="display: grid; gap: 8px; max-height: 580px; overflow: auto;">
          <div v-for="w in workers" :key="w.user_id" class="card" style="padding: 10px;">
            <div style="display: flex; justify-content: space-between;">
              <b>{{ w.display_name }}</b>
              <span class="badge">{{ w.worker_rating_avg }}分 / {{ w.worker_rating_count }}评</span>
            </div>
            <p class="muted">擅长：{{ w.skills || '未填写' }}</p>
            <p class="muted">价格范围：{{ w.min_price ?? '-' }} ~ {{ w.max_price ?? '-' }}</p>
            <p class="muted">被拉黑次数：{{ w.blocked_by_count }}</p>
            <p class="muted" style="margin-bottom: 0;">简介：{{ w.bio || '无' }}</p>
          </div>
          <p v-if="workers.length === 0" class="muted">暂无开放接单者。</p>
        </div>
      </article>

      <article class="card">
        <h3 style="margin-top: 0;">我的任务记录</h3>
        <h4>我发布的</h4>
        <div style="display: grid; gap: 6px; max-height: 220px; overflow: auto;">
          <div v-for="t in myPublished" :key="t.id" class="muted">#{{ t.id }} {{ t.title }} - {{ t.status }}</div>
          <p v-if="myPublished.length === 0" class="muted">暂无</p>
        </div>

        <h4>我接取的</h4>
        <div style="display: grid; gap: 6px; max-height: 220px; overflow: auto;">
          <div v-for="t in myAccepted" :key="t.id" class="muted">#{{ t.id }} {{ t.title }} - {{ t.status }}</div>
          <p v-if="myAccepted.length === 0" class="muted">暂无</p>
        </div>

        <h4>我的举报/申诉</h4>
        <div style="display: grid; gap: 6px; max-height: 140px; overflow: auto;">
          <div v-for="r in myReports" :key="r.id" class="muted">#{{ r.id }} {{ r.type }} - {{ r.status }}</div>
          <p v-if="myReports.length === 0" class="muted">暂无</p>
        </div>
      </article>
    </section>

    <section v-if="loading" class="card" style="margin-top: 14px;">加载中...</section>
  </main>
</template>
