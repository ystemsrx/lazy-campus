export interface ChatMessage {
  id: number
  sender_id: number
  receiver_id: number
  task_id: number | null
  content: string
  is_read: boolean
  blocked: boolean
  created_at: string
}

export interface Conversation {
  peer_id: number
  peer_name: string
  peer_avatar: string | null
  peer_gender: 'male' | 'female' | null
  peer_last_active: string | null
  task_id: number | null
  task_title: string | null
  task_price: number | null
  task_status: string | null
  task_icon: string | null
  task_is_deleted: boolean
  last_message: string | null
  last_message_time: string | null
  unread_count: number
  blocked_by_me: boolean
  blocked_by_them: boolean
  peer_ban_contact: boolean
}

export interface ChatAttachment {
  id: number
  uploader_id: number
  peer_id: number
  task_id: number | null
  message_id: number | null
  file_name: string
  file_url: string
  file_size: number
  mime_type: string
  created_at: string
}

export interface AttachmentCount {
  count: number
  limit: number
}
