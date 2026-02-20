const FIELD_NAMES: Record<string, string> = {
  reason: '问题描述',
  evidence: '证据说明',
  title: '标题',
  description: '描述',
  price: '价格',
  content: '内容',
  nickname: '昵称',
  email: '邮箱',
  password: '密码',
  account: '账号',
  name: '姓名',
}

export function extractError(error: any, fallback = '操作失败'): string {
  const detail = error?.response?.data?.detail
  if (!detail) return fallback

  if (typeof detail === 'string') {
    if (detail.startsWith('Third-party auth')) return '请检查账号、密码'
    return detail
  }

  if (Array.isArray(detail)) {
    const msgs = detail.map((e: any) => {
      const field = e.loc?.[e.loc.length - 1]
      const label = (field && FIELD_NAMES[field]) || field || '字段'
      const type: string = e.type || ''
      if (type === 'string_too_short') return `${label}至少 ${e.ctx?.min_length ?? ''} 个字符`
      if (type === 'string_too_long') return `${label}最多 ${e.ctx?.max_length ?? ''} 个字符`
      if (type === 'missing') return `请填写${label}`
      if (type === 'value_error') return `${label}格式不正确`
      return `${label}不符合要求`
    })
    return msgs.join('；')
  }

  if (typeof detail === 'object' && detail.code === 'USER_BANNED') return '账号已被封禁'

  return fallback
}
