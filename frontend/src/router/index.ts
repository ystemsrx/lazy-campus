import { createRouter, createWebHistory } from 'vue-router'

import { useAuthStore } from '../stores/auth'

const publicPaths = ['/', '/login']

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', component: () => import('../views/LoginView.vue') },
    { path: '/complete-profile', component: () => import('../views/CompleteProfileView.vue') },
    { path: '/admin', component: () => import('../views/AdminView.vue') },
    { path: '/', component: () => import('../views/HomeView.vue') }
  ]
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()

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
