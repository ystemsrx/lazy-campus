import { createRouter, createWebHistory } from 'vue-router'

import { useAuthStore } from '../stores/auth'

const publicPaths = ['/', '/login']

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', component: () => import('../views/LoginView.vue') },
    { path: '/complete-profile', component: () => import('../views/CompleteProfileView.vue') },
    { path: '/admin', component: () => import('../views/AdminView.vue') },
    { path: '/tasks', component: () => import('../views/TaskManagementView.vue') },
    { path: '/settings', component: () => import('../views/SettingsView.vue') },
    { path: '/', component: () => import('../views/HomeView.vue') }
  ]
})

const SESSION_REFRESH_KEY = 'token_refreshed'

router.beforeEach(async (to) => {
  const auth = useAuthStore()

  // 每次新的浏览器会话（sessionStorage 随 tab 关闭而清空）刷新一次 token
  // 实现滑动窗口：只要在 30 天内有过访问，就自动续期
  if (auth.isAuthenticated && !sessionStorage.getItem(SESSION_REFRESH_KEY)) {
    sessionStorage.setItem(SESSION_REFRESH_KEY, '1')
    const ok = await auth.refresh()
    if (!ok) return '/login'
  }

  if (!auth.isAuthenticated && !publicPaths.includes(to.path)) {
    return '/login'
  }

  if (auth.isAuthenticated && !auth.user && auth.role === 'user') {
    try {
      await auth.fetchMe()
    } catch {
      auth.logout()
      return '/login'
    }
  }

  if (to.path === '/login' && auth.isAuthenticated) {
    return auth.role === 'admin' ? '/admin' : '/'
  }

  if (auth.role === 'admin' && to.path !== '/admin') {
    return '/admin'
  }

  if (auth.role === 'user' && !auth.profileCompleted && to.path !== '/complete-profile') {
    return '/complete-profile'
  }

  if (auth.role === 'user' && auth.profileCompleted && to.path === '/complete-profile') {
    return '/'
  }

  return true
})

export default router
