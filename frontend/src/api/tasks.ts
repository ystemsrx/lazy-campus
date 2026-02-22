import api from './client'
import type { Category, Task, TaskMessage, TaskReview } from '../types/api'

export async function fetchCategories() {
  const { data } = await api.get<Category[]>('/tasks/categories')
  return data
}

export async function fetchTasks(params: Record<string, string | number | undefined>) {
  const { data } = await api.get<Task[]>('/tasks', { params })
  return data
}

export async function createTask(payload: {
  title: string
  description: string
  deadline: string | null
  location: string | null
  price: number
  category_id: number | null
  contact_visibility: 'after_accept' | 'internal_only'
  contact_info: string | null
  required_gender: 'male' | 'female' | null
  icon?: string | null
}) {
  const { data } = await api.post<Task>('/tasks', payload)
  return data
}

export async function acceptTask(taskId: number) {
  const { data } = await api.post<Task>(`/tasks/${taskId}/accept`)
  return data
}

export async function confirmTask(taskId: number) {
  const { data } = await api.post<Task>(`/tasks/${taskId}/confirm-complete`)
  return data
}

export async function abandonTask(taskId: number) {
  const { data } = await api.post<Task>(`/tasks/${taskId}/abandon`)
  return data
}

export async function fetchPublishedTasks() {
  const { data } = await api.get<Task[]>('/tasks/me/published')
  return data
}

export async function fetchAcceptedTasks() {
  const { data } = await api.get<Task[]>('/tasks/me/accepted')
  return data
}

export async function fetchMessages(taskId: number) {
  const { data } = await api.get<TaskMessage[]>(`/tasks/${taskId}/messages`)
  return data
}

export async function sendMessage(taskId: number, content: string) {
  const { data } = await api.post<TaskMessage>(`/tasks/${taskId}/messages`, { content })
  return data
}

export async function fetchReviews(taskId: number) {
  const { data } = await api.get<TaskReview[]>(`/tasks/${taskId}/reviews`)
  return data
}

export async function createReview(
  taskId: number,
  payload: { stars: number; comment?: string; target_role: 'publisher' | 'worker' }
) {
  const { data } = await api.post<TaskReview>(`/tasks/${taskId}/reviews`, payload)
  return data
}

export async function updateTask(
  taskId: number,
  payload: {
    title?: string
    description?: string
    deadline?: string | null
    location?: string | null
    price?: number
    category_id?: number | null
    contact_visibility?: 'after_accept' | 'internal_only'
    contact_info?: string | null
    required_gender?: 'male' | 'female' | null
    icon?: string | null
  }
) {
  const { data } = await api.put<Task>(`/tasks/${taskId}`, payload)
  return data
}

export async function deleteTask(taskId: number) {
  await api.delete(`/tasks/${taskId}`)
}

export async function createCategory(payload: { name: string; description?: string; sort_order?: number }) {
  const { data } = await api.post<Category>('/tasks/categories', payload)
  return data
}

export async function updateCategory(id: number, payload: { name: string; description?: string; sort_order?: number }) {
  const { data } = await api.put<Category>(`/tasks/categories/${id}`, payload)
  return data
}

export async function deleteCategory(id: number) {
  await api.delete(`/tasks/categories/${id}`)
}
