export type UserRole = 'user' | 'admin'
export type TaskStatus = 'open' | 'in_progress' | 'completed' | 'canceled' | 'under_review'
export type ContactVisibility = 'after_accept' | 'internal_only'

export interface LoginPayload {
  account: string
  password: string
}

export interface RegisterPayload {
  account: string
  password: string
  name: string
}

export interface LoginResponse {
  token: { access_token: string; token_type: string }
  role: UserRole
  profile_completed: boolean
  user_id: number | null
  display_name: string
}

export interface RegisterResponse {
  user_id: number
  account: string
}

export interface RegistrationStatus {
  registration_enabled: boolean
}

export interface UserMe {
  id: number
  account: string
  name: string
  nickname: string | null
  email: string | null
  gender: 'male' | 'female' | 'other' | null
  avatar_url: string | null
  is_banned: boolean
  role: UserRole
  created_at: string
}

export interface WorkerProfile {
  user_id: number
  enabled: boolean
  skills: string | null
  min_price: number | null
  max_price: number | null
  bio: string | null
  display_name: string
  avatar_url: string | null
  worker_rating_avg: number
  worker_rating_count: number
  blocked_by_count: number
}

export interface Task {
  id: number
  title: string
  description: string
  deadline: string | null
  location: string | null
  price: number
  status: TaskStatus
  category_id: number | null
  publisher_id: number
  assignee_id: number | null
  contact_visibility: ContactVisibility
  contact_info: string | null
  publisher_display_name: string
  assignee_display_name: string | null
  created_at: string
}

export interface Category {
  id: number
  name: string
  description: string | null
  sort_order: number
}

export interface TaskMessage {
  id: number
  task_id: number
  sender_id: number
  sender_display_name: string
  content: string
  created_at: string
}

export interface TaskReview {
  id: number
  task_id: number
  reviewer_id: number
  reviewee_id: number
  target_role: 'publisher' | 'worker'
  stars: number
  comment: string | null
  created_at: string
}

export interface AdminUserItem {
  id: number
  account: string
  name: string
  nickname: string | null
  display_name: string
  avatar_url: string | null
  role: UserRole
  is_banned: boolean
  ban_reason: string | null
  ban_count: number
  created_at: string
}

export interface AdminUserListResponse {
  total: number
  page: number
  page_size: number
  items: AdminUserItem[]
}

export interface Report {
  id: number
  type: 'report' | 'appeal'
  task_id: number | null
  reporter_id: number
  reported_user_id: number | null
  reason: string
  evidence: string
  status: 'pending' | 'approved' | 'rejected'
  admin_id: number | null
  admin_notes: string | null
  created_at: string
}
