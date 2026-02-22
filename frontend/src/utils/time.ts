/**
 * 时间工具：后端统一保存 UTC，前端统一转为用户本地时区显示。
 *
 * 后端返回的 ISO 字符串是 naive UTC（无 Z 后缀），JavaScript 会错误地
 * 将其当成本地时间解析。此模块所有函数都先将其标记为 UTC 再处理。
 */

export function parseUTC(iso: string): Date {
  if (!/Z|[+-]\d{2}:\d{2}$/.test(iso)) {
    return new Date(iso + 'Z')
  }
  return new Date(iso)
}

/** MM-DD HH:mm（本地时区） */
export function formatShort(iso: string): string {
  const d = parseUTC(iso)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

/** YYYY-MM-DD HH:mm（本地时区） */
export function formatFull(iso: string): string {
  const d = parseUTC(iso)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

/** 解封时间：当天只显示时间，否则只显示日期 */
export function formatBanUntil(iso: string): string {
  const d = parseUTC(iso)
  const now = new Date()
  const pad = (n: number) => String(n).padStart(2, '0')
  if (
    d.getFullYear() === now.getFullYear() &&
    d.getMonth() === now.getMonth() &&
    d.getDate() === now.getDate()
  ) {
    return `今天 ${pad(d.getHours())}:${pad(d.getMinutes())}`
  }
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

/** 判断 UTC 截止时间是否已过期 */
export function isExpired(iso: string | null | undefined): boolean {
  if (!iso) return false
  return parseUTC(iso) < new Date()
}

/** 将后端 UTC ISO 转为 <input type="datetime-local"> 需要的本地时间值 */
export function utcToLocal(iso: string): string {
  const d = parseUTC(iso)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

/** 将 <input type="datetime-local"> 的本地时间值转为 UTC ISO（发送给后端） */
export function localToUTC(localStr: string): string {
  return new Date(localStr).toISOString()
}

/** 当前本地时间的 datetime-local 值（用于 min 属性） */
export function nowLocal(): string {
  const now = new Date()
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}T${pad(now.getHours())}:${pad(now.getMinutes())}`
}

/** 相对时间（"刚刚"、"3 分钟前"、"2 小时前"等） */
export function formatRelativeTime(iso: string): string {
  const d = parseUTC(iso)
  const now = new Date()
  const diffMs = now.getTime() - d.getTime()
  const diffMin = Math.floor(diffMs / 60000)
  const diffHour = Math.floor(diffMs / 3600000)
  const diffDay = Math.floor(diffMs / 86400000)

  if (diffMin < 1) return '刚刚'
  if (diffMin < 60) return `${diffMin} 分钟前`
  if (diffHour < 24) return `${diffHour} 小时前`
  if (diffDay < 7) return `${diffDay} 天前`
  if (diffDay < 30) return `${Math.floor(diffDay / 7)} 周前`
  return formatShort(iso)
}

/** 聊天列表 & 消息时间：今天只显示时间，昨天显示"昨天"，近 7 天显示"X天前"，更久显示日期 */
export function formatChatTime(iso: string): string {
  const d = parseUTC(iso)
  const now = new Date()
  const pad = (n: number) => String(n).padStart(2, '0')

  const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const msgDay = new Date(d.getFullYear(), d.getMonth(), d.getDate())
  const diffDays = Math.floor((todayStart.getTime() - msgDay.getTime()) / 86400000)

  if (diffDays === 0) return `${pad(d.getHours())}:${pad(d.getMinutes())}`
  if (diffDays === 1) return '昨天'
  if (diffDays < 7) return `${diffDays}天前`
  return `${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

/** Telegram 风格最后在线状态 */
export function formatLastSeen(iso: string | null | undefined): { online: boolean; text: string } {
  if (!iso) return { online: false, text: '从未上线' }
  const d = parseUTC(iso)
  const now = new Date()
  const diffMs = now.getTime() - d.getTime()
  const diffSec = Math.floor(diffMs / 1000)
  const diffMin = Math.floor(diffMs / 60000)
  const diffHour = Math.floor(diffMs / 3600000)

  if (diffSec < 45) return { online: true, text: '在线' }
  if (diffMin < 3) return { online: false, text: '刚刚在线' }
  if (diffMin < 60) return { online: false, text: `${diffMin} 分钟前在线` }
  if (diffHour < 24) return { online: false, text: `${diffHour} 小时前在线` }
  return { online: false, text: '最近上线' }
}
