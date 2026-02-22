import {
  File as FileIcon,
  FileArchive,
  FileCode,
  FileImage,
  FileSpreadsheet,
  FileText,
  Film,
  Music,
} from 'lucide-vue-next'

import type { ChatAttachment, ChatMessage } from '../../types/chat'

export const ATTACHMENT_MSG_PREFIX = '📎 [附件]'

export function getFileIconComponent(mime: string, name: string) {
  const ext = name.split('.').pop()?.toLowerCase() || ''

  if (
    mime.startsWith('image/') ||
    ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'svg', 'ico', 'tiff', 'avif'].includes(ext)
  ) {
    return FileImage
  }

  if (
    mime.startsWith('video/') ||
    ['mp4', 'mov', 'avi', 'mkv', 'webm', 'flv', 'wmv', 'm4v', 'ogv', 'ts'].includes(ext)
  ) {
    return Film
  }

  if (
    mime.startsWith('audio/') ||
    ['mp3', 'wav', 'ogg', 'flac', 'aac', 'm4a', 'opus', 'wma', 'aiff'].includes(ext)
  ) {
    return Music
  }

  if (['pdf'].includes(ext)) return FileText
  if (['doc', 'docx', 'odt', 'rtf'].includes(ext)) return FileText
  if (['xls', 'xlsx', 'csv', 'ods'].includes(ext)) return FileSpreadsheet
  if (['ppt', 'pptx', 'odp'].includes(ext)) return FileText

  if (['zip', 'rar', '7z', 'tar', 'gz', 'bz2', 'xz', 'zst'].includes(ext)) {
    return FileArchive
  }

  if (
    [
      'js',
      'ts',
      'py',
      'java',
      'c',
      'cpp',
      'h',
      'go',
      'rs',
      'rb',
      'php',
      'html',
      'css',
      'json',
      'xml',
      'yaml',
      'yml',
      'sh',
      'bat',
      'sql',
      'vue',
      'jsx',
      'tsx',
      'swift',
      'kt',
    ].includes(ext)
  ) {
    return FileCode
  }

  return FileIcon
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export function isImageMime(mime: string): boolean {
  return mime.startsWith('image/')
}

export function isAttachmentOnly(msg: ChatMessage): boolean {
  return msg.content.startsWith(ATTACHMENT_MSG_PREFIX)
}

export function getAttachmentFileName(msg: ChatMessage): string {
  return msg.content.replace(ATTACHMENT_MSG_PREFIX, '').trim()
}

export function getMessageAttachments(attachments: ChatAttachment[], msgId: number): ChatAttachment[] {
  return attachments.filter((att) => att.message_id === msgId)
}
