import api from './client'
import type {
  NewcomerRewardLogList,
  NewcomerRewardManualGrantResult,
  NewcomerRewardRuleItem,
  NewcomerRewardRuleList,
} from '../types/api'

export async function fetchNewcomerRewardRules(params: { page?: number; page_size?: number } = {}) {
  const { data } = await api.get<NewcomerRewardRuleList>('/admin/newcomer-rewards/rules', { params })
  return data
}

export async function createNewcomerRewardRule(payload: {
  reward_type: string
  reward_detail: string
  start_time?: string | null
  end_time?: string | null
}) {
  const { data } = await api.post<NewcomerRewardRuleItem>('/admin/newcomer-rewards/rules', payload)
  return data
}

export async function updateNewcomerRewardRule(ruleId: number, payload: {
  reward_type?: string
  reward_detail?: string
  enabled?: boolean
  start_time?: string | null
  end_time?: string | null
}) {
  const { data } = await api.put<NewcomerRewardRuleItem>(`/admin/newcomer-rewards/rules/${ruleId}`, payload)
  return data
}

export async function deleteNewcomerRewardRule(ruleId: number) {
  await api.delete(`/admin/newcomer-rewards/rules/${ruleId}`)
}

export async function toggleNewcomerRewardRule(ruleId: number) {
  const { data } = await api.patch<NewcomerRewardRuleItem>(`/admin/newcomer-rewards/rules/${ruleId}/toggle`)
  return data
}

export async function fetchNewcomerRewardLogs(params: {
  page?: number
  page_size?: number
  reward_type?: string
  status?: string
  q?: string
} = {}) {
  const { data } = await api.get<NewcomerRewardLogList>('/admin/newcomer-rewards/logs', { params })
  return data
}

export async function grantNewcomerRewardToUsers(payload: {
  rule_id?: number
  reward_type?: string
  reward_detail?: string
  user_ids: number[]
}) {
  const { data } = await api.post<NewcomerRewardManualGrantResult>('/admin/newcomer-rewards/grant', payload)
  return data
}
