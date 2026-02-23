import type { ContactVisibility, Gender, TaskStatus } from '../../types/api'

export type HomeTab = 'hall' | 'workers'

export type HomeTaskSort =
  | 'ranking'
  | 'newest'
  | 'deadline_asc'
  | 'publisher_rating'
  | 'publisher_completed'
  | 'price_desc'

export type HomeWorkerSort = 'ranking' | 'worker_rating' | 'worker_completed'

export interface HomeTaskEditorForm {
  title: string
  description: string
  deadline: string
  location: string
  price: number
  category_id: number | null
  contact_visibility: ContactVisibility
  contact_info: string
  required_gender: Gender | null
  icon: string
}

export interface HomeReviewForm {
  stars: number
  comment: string
}

export const HOME_TASK_SORT_OPTIONS: Array<{ value: HomeTaskSort; label: string }> = [
  { value: 'ranking', label: '综合排序' },
  { value: 'newest', label: '最新发布' },
  { value: 'deadline_asc', label: '截止时间最近' },
  { value: 'publisher_rating', label: '发布人评分最高' },
  { value: 'publisher_completed', label: '发布人完成数最多' },
  { value: 'price_desc', label: '价格最高' },
]

export const HOME_WORKER_SORT_OPTIONS: Array<{ value: HomeWorkerSort; label: string }> = [
  { value: 'ranking', label: '综合排序' },
  { value: 'worker_rating', label: '评分最高' },
  { value: 'worker_completed', label: '完成任务最多' },
]

const HOME_STATUS_MAP: Record<TaskStatus, { label: string; cls: string }> = {
  open: { label: '待接取', cls: 'badge-blue' },
  in_progress: { label: '进行中', cls: 'badge-amber' },
  completed: { label: '已完成', cls: 'badge-green' },
  canceled: { label: '已取消', cls: 'badge-default' },
  under_review: { label: '审核中', cls: 'badge-red' },
}

const HOME_GENDER_MAP: Record<Gender, { label: string; icon: string; cls: string }> = {
  male: { label: '限男生', icon: 'fa-solid fa-mars', cls: 'badge-blue' },
  female: { label: '限女生', icon: 'fa-solid fa-venus', cls: 'badge-pink' },
}

export function normalizeHomeTab(value: unknown): HomeTab {
  return value === 'workers' ? 'workers' : 'hall'
}

export function statusOf(status: string) {
  return HOME_STATUS_MAP[status as TaskStatus] || { label: status, cls: 'badge-default' }
}

export function genderLabel(gender: string | null) {
  if (gender !== 'male' && gender !== 'female') return null
  return HOME_GENDER_MAP[gender]
}

export function createTaskEditorForm(): HomeTaskEditorForm {
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

export function createReviewForm(): HomeReviewForm {
  return {
    stars: 5,
    comment: '',
  }
}
