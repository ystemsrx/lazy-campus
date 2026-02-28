import { createRouter, createWebHistory } from 'vue-router'

import { useAuthStore } from '../stores/auth'

const publicPaths = ['/', '/login', '/home']

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: () => import('../views/LandingView.vue') },
    { path: '/login', component: () => import('../views/LoginView.vue') },
    { path: '/complete-profile', component: () => import('../views/CompleteProfileView.vue') },
    { path: '/admin', component: () => import('../views/AdminView.vue') },
    { path: '/home', component: () => import('../views/HomeView.vue') },
    { path: '/tasks', component: () => import('../views/TaskManagementView.vue') },
    { path: '/agent-tasks', component: () => import('../views/AgentTasksView.vue') },
    { path: '/agent/:sessionId?', component: () => import('../views/AgentView.vue') },
    { path: '/settings', component: () => import('../views/SettingsView.vue') },
    { path: '/chat', component: () => import('../views/ChatView.vue') },
    { path: '/reports', component: () => import('../views/MyReportsView.vue') },
    {
      path: '/:pathMatch(.*)*',
      name: 'not-found',
      component: () => import('../views/NotFoundView.vue'),
    },
  ]
})

const SESSION_REFRESH_KEY = 'token_refreshed'

router.beforeEach(async (to) => {
  const auth = useAuthStore()

  const needsRefresh = auth.isAuthenticated && !sessionStorage.getItem(SESSION_REFRESH_KEY)
  const needsFetchMe = auth.isAuthenticated && !auth.user && auth.role === 'user'

  if (needsRefresh || needsFetchMe) {
    const tasks: Promise<unknown>[] = []

    if (needsRefresh) {
      sessionStorage.setItem(SESSION_REFRESH_KEY, '1')
      tasks.push(auth.refresh().then(ok => { if (!ok) throw new Error('refresh_failed') }))
    }

    if (needsFetchMe) {
      tasks.push(auth.fetchMe())
    }

    try {
      await Promise.all(tasks)
    } catch {
      auth.logout()
      return '/login'
    }
  }

  if (!auth.isAuthenticated && !publicPaths.includes(to.path) && to.name !== 'not-found') {
    return '/login'
  }

  if ((to.path === '/login' || to.path === '/') && auth.isAuthenticated) {
    return auth.role === 'admin' ? '/admin' : '/home'
  }

  if (auth.role === 'admin' && to.path !== '/admin') {
    return '/admin'
  }

  if (auth.role === 'user' && !auth.profileCompleted && to.path !== '/complete-profile') {
    return '/complete-profile'
  }

  if (auth.role === 'user' && auth.profileCompleted && to.path === '/complete-profile') {
    return '/home'
  }

  return true
})

export default router
