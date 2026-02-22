const statusMap: Record<string, { label: string; cls: string }> = {
  open: { label: '待接取', cls: 'status-open' },
  in_progress: { label: '进行中', cls: 'status-active' },
  completed: { label: '已完成', cls: 'status-done' },
  canceled: { label: '已取消', cls: 'status-canceled' },
  under_review: { label: '进行中', cls: 'status-active' },
}

export function snapshotStatusLabel(status: string | null): string {
  if (!status) return '未知'
  return statusMap[status]?.label ?? status
}

export function snapshotStatusClass(status: string | null): string {
  if (!status) return ''
  return statusMap[status]?.cls ?? ''
}

export function getSnapshotStatusMap() {
  return statusMap
}
