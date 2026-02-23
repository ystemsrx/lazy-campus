export type UserRole = 'user' | 'admin'
export type TaskStatus = 'open' | 'in_progress' | 'completed' | 'canceled' | 'under_review'
export type ContactVisibility = 'after_accept' | 'internal_only'

export interface LoginPayload {
  account: string
  password: string
  captcha_token?: string
  session_id?: string
}

export interface RegisterPayload {
  account: string
  password: string
  name: string
  captcha_token: string
  session_id: string
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
  gender: 'male' | 'female' | null
  avatar_url: string | null
  is_banned: boolean
  ban_until: string | null
  role: UserRole
  created_at: string
}

export interface SkillTag {
  id: number
  name: string
}

export interface WorkerProfile {
  user_id: number
  enabled: boolean
  skill_tags: SkillTag[]
  min_price: number | null
  max_price: number | null
  bio: string | null
  has_contact: boolean
  phone: string | null
  wechat: string | null
  show_contact: boolean
  display_name: string
  avatar_url: string | null
  gender: Gender | null
  worker_rating_avg: number
  worker_rating_count: number
  overall_rating_avg: number
  overall_rating_count: number
  worker_completed_count: number
  blocked_by_count: number
}

export interface WorkerContactReveal {
  phone: string | null
  wechat: string | null
  viewed_at: string
}

export type Gender = 'male' | 'female'

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
  required_gender: Gender | null
  publisher_display_name: string
  assignee_display_name: string | null
  publisher_rating_avg: number
  publisher_rating_count: number
  publisher_completed_count: number
  publisher_blocked_by_count: number
  publisher_task_count: number
  icon: string | null
  created_at: string
  updated_at: string
}

export interface Category {
  id: number
  name: string
  description: string | null
  sort_order: number
  task_count: number
  worker_count: number
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

export interface UserReview {
  id: number
  stars: number
  comment: string | null
  reviewer_display_name: string
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
  ban_until: string | null
  created_at: string
}

export interface AdminUserListResponse {
  total: number
  page: number
  page_size: number
  items: AdminUserItem[]
}

export interface BanRecord {
  source: 'report' | 'admin'
  reason: string
  created_at: string
}

export interface BanContext {
  ban_until: string | null
  ban_count: number
  records: BanRecord[]
}

export interface Report {
  id: number
  type: 'report' | 'appeal'
  task_id: number | null
  reporter_id: number
  reporter_name: string | null
  reporter_nickname: string | null
  reporter_account: string | null
  reported_user_id: number | null
  reported_user_name: string | null
  reported_user_nickname: string | null
  reported_user_account: string | null
  reported_user_ban_count: number | null
  reason: string
  evidence: string
  images: string[]
  status: 'pending' | 'approved' | 'rejected'
  admin_id: number | null
  admin_notes: string | null
  created_at: string
}

export type NotificationType = 'task_expired' | 'chat_message' | 'task_accepted' | 'report_reviewed' | 'task_completed' | 'task_abandoned'
export type DismissType = 'read' | 'action' | 'source'

export interface AppNotification {
  id: number
  type: NotificationType
  title: string
  description: string | null
  related_task_id: number | null
  related_report_id: number | null
  related_user_id: number | null
  dismiss_type: DismissType
  is_read: boolean
  created_at: string
}

export interface BlacklistItem {
  blocked_user_id: number
  blocked_display_name: string
  blocked_avatar_url: string | null
  reason: string | null
  created_at: string
}
