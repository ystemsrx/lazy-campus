import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { completeProfile as apiCompleteProfile, getMe, login as apiLogin, refreshToken as apiRefreshToken } from '../api/auth'
import type { UserMe, UserRole } from '../types/api'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('access_token'))
  const role = ref<UserRole | null>((localStorage.getItem('role') as UserRole | null) || null)
  const profileCompleted = ref(localStorage.getItem('profile_completed') === 'true')
  const user = ref<UserMe | null>(null)
  const displayName = ref(localStorage.getItem('display_name') || '')

  const isAuthenticated = computed(() => Boolean(token.value))

  async function _applyLoginResponse(res: Awaited<ReturnType<typeof apiLogin>>) {
    token.value = res.token.access_token
    role.value = res.role
    profileCompleted.value = res.profile_completed
    displayName.value = res.display_name
    localStorage.setItem('access_token', res.token.access_token)
    localStorage.setItem('role', res.role)
    localStorage.setItem('profile_completed', String(res.profile_completed))
    localStorage.setItem('display_name', res.display_name)
    if (res.role === 'user') {
      await fetchMe()
    }
    return res
  }

  async function login(account: string, password: string) {
    const res = await apiLogin({ account, password })
    return _applyLoginResponse(res)
  }

  async function loginWithCaptcha(account: string, password: string, captchaToken: string, sessionId: string) {
    const res = await apiLogin({ account, password, captcha_token: captchaToken, session_id: sessionId })
    return _applyLoginResponse(res)
  }

  async function fetchMe() {
    if (!token.value || role.value !== 'user') return null
    user.value = await getMe()
    displayName.value = user.value.nickname || user.value.name
    localStorage.setItem('display_name', displayName.value)
    return user.value
  }

  async function completeProfile(payload: { email: string; gender: 'male' | 'female'; nickname: string | null }) {
    const data = await apiCompleteProfile(payload)
    user.value = data
    profileCompleted.value = true
    displayName.value = data.nickname || data.name
    localStorage.setItem('profile_completed', 'true')
    localStorage.setItem('display_name', displayName.value)
    return data
  }

  async function refresh() {
    if (!token.value) return false
    try {
      const res = await apiRefreshToken()
      token.value = res.access_token
      localStorage.setItem('access_token', res.access_token)
      return true
    } catch {
      logout()
      return false
    }
  }

  function logout() {
    token.value = null
    role.value = null
    user.value = null
    profileCompleted.value = false
    displayName.value = ''
    localStorage.removeItem('access_token')
    localStorage.removeItem('role')
    localStorage.removeItem('profile_completed')
    localStorage.removeItem('display_name')
  }

  return {
    token,
    role,
    user,
    displayName,
    isAuthenticated,
    profileCompleted,
    login,
    loginWithCaptcha,
    fetchMe,
    completeProfile,
    refresh,
    logout
  }
})
