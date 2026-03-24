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
  payment_qr_url: string | null
  is_banned: boolean
  ban_until: string | null
  ban_publish: boolean
  ban_accept: boolean
  ban_contact: boolean
  agent_usage_remaining: number
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
  is_pinned: boolean
  is_urgent: boolean
  admin_note: string | null
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
  publisher_payment_qr_url: string | null
  icon: string | null
  attachments: TaskAttachment[]
  created_at: string
  updated_at: string
}

export interface TaskAttachment {
  id: number
  file_name: string
  file_url: string
}

export interface Category {
  id: number
  name: string
  description: string | null
  sort_order: number
  ai_agent_enabled: boolean
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
  email: string | null
  gender: 'male' | 'female' | null
  display_name: string
  avatar_url: string | null
  role: UserRole
  is_active: boolean
  is_banned: boolean
  ban_reason: string | null
  ban_count: number
  ban_until: string | null
  ban_publish: boolean
  ban_accept: boolean
  ban_contact: boolean
  agent_usage_remaining: number
  blocked_by_count: number
  worker_enabled: boolean
  worker_skill_count: number
  publisher_rating_avg: number
  publisher_rating_count: number
  worker_rating_avg: number
  worker_rating_count: number
  published_task_count: number
  accepted_task_count: number
  completed_task_count: number
  report_received_count: number
  publish_count_24h: number
  accept_count_24h: number
  last_active: string | null
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
  task_title: string | null
  reporter_id: number
  reporter_name: string | null
  reporter_nickname: string | null
  reporter_account: string | null
  reported_user_id: number | null
  reported_user_name: string | null
  reported_user_nickname: string | null
  reported_user_account: string | null
  reported_user_ban_count: number | null
  reporter_avatar_url: string | null
  reporter_gender: 'male' | 'female' | null
  reported_user_avatar_url: string | null
  reported_user_gender: 'male' | 'female' | null
  reason: string
  evidence: string
  images: string[]
  status: 'pending' | 'approved' | 'rejected'
  admin_id: number | null
  admin_notes: string | null
  ban_penalty: string | null
  is_admin_ban: boolean
  created_at: string
}

export type NotificationType = 'task_expired' | 'chat_message' | 'task_accepted' | 'report_reviewed' | 'task_completed' | 'task_abandoned' | 'task_canceled' | 'punishment' | 'admin_notice' | 'admin_task_notice' | 'admin_warning' | 'admin_success' | 'admin_info' | 'admin_announcement' | 'newcomer_reward'
export type DismissType = 'read' | 'action' | 'source' | 'persistent'

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

export interface AdminTrendPoint {
  date: string
  new_users: number
  new_tasks: number
  new_reports: number
  new_messages: number
}

export interface AdminRiskUser {
  user_id: number
  display_name: string
  ban_count: number
  blocked_by_count: number
  report_received_count: number
}

export interface AdminDashboardData {
  total_users: number
  active_users_24h: number
  new_users_7d: number
  active_workers: number
  total_tasks: number
  open_tasks: number
  in_progress_tasks: number
  under_review_tasks: number
  completed_tasks: number
  canceled_tasks: number
  overdue_open_tasks: number
  pinned_tasks: number
  urgent_tasks: number
  avg_task_price: number
  pending_reports: number
  approved_reports_7d: number
  rejected_reports_7d: number
  chat_messages_24h: number
  completion_rate: number
  registration_enabled: boolean
  trends: AdminTrendPoint[]
  top_risk_users: AdminRiskUser[]
}

export interface AdminTaskItem {
  id: number
  title: string
  status: TaskStatus
  price: number
  category_id: number | null
  category_name: string | null
  publisher_id: number
  publisher_display_name: string
  assignee_id: number | null
  assignee_display_name: string | null
  is_pinned: boolean
  is_urgent: boolean
  is_deleted: boolean
  demote_level: number
  deadline: string | null
  created_at: string
  updated_at: string
  report_count: number
}

export interface AdminTaskListResponse {
  total: number
  page: number
  page_size: number
  items: AdminTaskItem[]
}

export interface AdminChatConversationItem {
  user_a_id: number
  user_a_display_name: string
  user_a_avatar_url: string | null
  user_a_gender: 'male' | 'female' | null
  user_b_id: number
  user_b_display_name: string
  user_b_avatar_url: string | null
  user_b_gender: 'male' | 'female' | null
  task_id: number | null
  task_title: string | null
  task_price: number | null
  task_status: string | null
  message_count: number
  last_message: string | null
  last_message_time: string | null
}

export interface AdminChatConversationListResponse {
  total: number
  page: number
  page_size: number
  items: AdminChatConversationItem[]
}

export interface AdminChatMessage {
  id: number
  sender_id: number
  sender_display_name: string
  sender_avatar_url: string | null
  sender_gender: 'male' | 'female' | null
  receiver_id: number
  receiver_display_name: string
  task_id: number | null
  content: string
  is_read: boolean
  blocked: boolean
  created_at: string
}

export interface AdminTaskChatConversationItem {
  task_id: number
  task_title: string
  task_price: number | null
  task_status: string | null
  publisher_id: number
  publisher_display_name: string
  publisher_avatar_url: string | null
  publisher_gender: 'male' | 'female' | null
  session_assignee_id: number | null
  session_assignee_display_name: string | null
  session_assignee_avatar_url: string | null
  session_assignee_gender: 'male' | 'female' | null
  message_count: number
  last_message: string | null
  last_message_time: string | null
}

export interface AdminTaskChatConversationListResponse {
  total: number
  page: number
  page_size: number
  items: AdminTaskChatConversationItem[]
}

export interface AdminTaskChatMessage {
  id: number
  task_id: number
  sender_id: number
  sender_display_name: string
  sender_avatar_url: string | null
  sender_gender: 'male' | 'female' | null
  session_assignee_id: number | null
  content: string
  created_at: string
}

export interface AdminChatAttachment {
  id: number
  message_id: number | null
  file_name: string
  file_url: string
  file_size: number
  mime_type: string
}

export interface AdminPushNotificationResult {
  sent_count: number
  target_user_ids: number[]
}

export interface AdminSentNotification {
  title: string
  description: string | null
  type: string
  dismiss_type: string
  remaining_count: number
  read_count: number
  sent_at: string
}

export interface AdminMiniUser {
  id: number
  account: string
  display_name: string
  avatar_url: string | null
}

export interface AdminUserTaskBrief {
  id: number
  title: string
  status: TaskStatus
  price: number
  created_at: string
  updated_at: string
}

export interface AdminUserReportBrief {
  id: number
  type: 'report' | 'appeal'
  status: 'pending' | 'approved' | 'rejected'
  reason: string
  created_at: string
}

export interface AdminUserRadarMetrics {
  reliability: number
  activity: number
  cooperation: number
  safety: number
  growth: number
}

export interface AdminUserProfile {
  id: number
  account: string
  name: string
  nickname: string | null
  email: string | null
  gender: 'male' | 'female' | null
  display_name: string
  avatar_url: string | null
  id_number: string | null
  role: UserRole
  is_active: boolean
  is_banned: boolean
  ban_reason: string | null
  ban_count: number
  ban_until: string | null
  ban_publish: boolean
  ban_accept: boolean
  ban_contact: boolean
  agent_usage_remaining: number
  blocked_by_count: number
  last_active: string | null
  created_at: string
  worker_enabled: boolean
  worker_bio: string | null
  worker_min_price: number | null
  worker_max_price: number | null
  worker_phone: string | null
  worker_wechat: string | null
  worker_show_contact: boolean
  worker_skill_ids: number[]
  worker_skill_names: string[]
  blocked_users: AdminMiniUser[]
  published_task_count: number
  accepted_task_count: number
  completed_published_count: number
  completed_accepted_count: number
  report_submitted_count: number
  report_received_count: number
  pending_report_received_count: number
  appeal_count: number
  chat_message_count: number
  publisher_rating_avg: number
  publisher_rating_count: number
  worker_rating_avg: number
  worker_rating_count: number
  abandon_count_24h: number
  cancel_count_24h: number
  publish_count_24h: number
  accept_count_24h: number
  radar: AdminUserRadarMetrics
  recent_tasks: AdminUserTaskBrief[]
  recent_reports: AdminUserReportBrief[]
}

export interface AdminBlacklistItem {
  blocked_user_id: number
  blocked_display_name: string
  blocked_name?: string
  blocked_account: string
  blocked_avatar_url: string | null
  reason: string | null
  created_at: string
}

export interface AdminActionLogItem {
  id: number
  admin_identifier: string
  action: string
  target_type: string
  target_id: string
  detail: string | null
  created_at: string
}

export interface AdminActionLogListResponse {
  total: number
  page: number
  page_size: number
  items: AdminActionLogItem[]
  distinct_actions: string[]
}

export interface AgentAvailability {
  agent_enabled: boolean
  remaining_count: number
  max_interactions: number
  max_files: number
  max_file_size_mb: number
}

export interface AgentAttachment {
  name: string
  stored_name: string
  workspace_path: string
  size: number
}

export interface AgentMessage {
  id: number
  role: 'user' | 'assistant' | 'tool' | 'tool_call' | 'system'
  content: string | null
  tool_name: string | null
  tool_arguments: string | null
  tool_call_id: string | null
  attachments: AgentAttachment[]
  created_at: string
}

export interface AgentDeliverable {
  name: string
  size: number
  updated_at: string
}

export interface AgentSessionStart {
  session_id: string
  task_id: number
  task_title: string
  task_status: string
  status: string
  last_error: string | null
  interaction_count: number
  max_interactions: number
  remaining_count: number
  can_send: boolean
  queue_waiting: boolean
  queue_ahead_users: number
  last_activity_at: string
  created_at: string
  updated_at: string
}

export interface AgentSessionDetail extends AgentSessionStart {
  deliverables: AgentDeliverable[]
}

export interface AgentSendResult {
  queued: boolean
  queue_ahead_users: number
  interaction_count: number
  max_interactions: number
}

export interface AgentCancelResult {
  canceled: boolean
  mode: 'none' | 'queued' | 'running'
  removed_message_id: number | null
  restored_content: string | null
  restored_attachments: AgentAttachment[]
}

export interface AgentMySessionItem {
  session_id: string
  task_id: number
  task_title: string
  task_status: string
  status: string
  last_error: string | null
  interaction_count: number
  max_interactions: number
  can_send: boolean
  last_activity_at: string
  created_at: string
  updated_at: string
}

export interface AgentMySessionList {
  total: number
  page: number
  page_size: number
  items: AgentMySessionItem[]
}

export interface AgentAdminConfig {
  agent_enabled: boolean
}

export interface AgentAdminSessionItem {
  session_id: string
  task_id: number
  task_title: string
  user_id: number
  user_display_name: string
  status: string
  interaction_count: number
  max_interactions: number
  has_container: boolean
  last_activity_at: string
  created_at: string
  updated_at: string
}

export interface AgentAdminSessionList {
  total: number
  page: number
  page_size: number
  items: AgentAdminSessionItem[]
}

export interface NewcomerRewardRuleItem {
  id: number
  reward_type: string
  reward_detail: string
  enabled: boolean
  start_time: string | null
  end_time: string | null
  created_at: string
  updated_at: string
}

export interface NewcomerRewardRuleList {
  items: NewcomerRewardRuleItem[]
  total: number
}

export interface NewcomerRewardLogItem {
  id: number
  user_id: number
  user_display_name: string
  user_account: string
  rule_id: number
  reward_type: string
  reward_detail: string
  status: string
  fail_reason: string | null
  created_at: string
}

export interface NewcomerRewardLogList {
  items: NewcomerRewardLogItem[]
  total: number
}

export interface NewcomerRewardManualGrantResult {
  requested_count: number
  processed_count: number
  success_count: number
  failed_count: number
  missing_user_ids: number[]
}
