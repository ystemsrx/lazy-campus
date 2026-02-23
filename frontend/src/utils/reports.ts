import type { Report } from '../types/api'
import { formatFull } from './time'

export function reportDisplayName(report: Report): string {
  if (report.type === 'appeal') {
    return report.reporter_nickname || report.reporter_name || report.reporter_account || '未知'
  }
  return report.reported_user_nickname || report.reported_user_name || report.reported_user_account || '未知用户'
}

export function reportTypeLabel(type: Report['type']): string {
  return type === 'report' ? '举报' : '申诉'
}

export function reportStatusLabel(status: Report['status']): string {
  if (status === 'pending') return '待审核'
  if (status === 'approved') return '已通过'
  return '已驳回'
}

export function reportStatusIcon(status: Report['status']): string {
  if (status === 'pending') return 'fa-solid fa-clock'
  if (status === 'approved') return 'fa-solid fa-shield-halved'
  return 'fa-solid fa-circle-xmark'
}

export function reportDateOnly(iso: string): string {
  return formatFull(iso).split(' ')[0]
}
