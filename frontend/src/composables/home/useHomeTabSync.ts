import { ref, watch } from 'vue'
import type { Router, RouteLocationNormalizedLoaded } from 'vue-router'
import { normalizeHomeTab, type HomeTab } from './model'

export function useHomeTabSync(route: RouteLocationNormalizedLoaded, router: Router) {
  const activeTab = ref<HomeTab>(normalizeHomeTab(route.query.tab))

  function syncTabQuery(tab: HomeTab) {
    const nextQuery = { ...route.query }
    if (tab === 'workers') {
      nextQuery.tab = 'workers'
    } else {
      delete nextQuery.tab
    }

    const currentTabQuery = route.query.tab === 'workers' ? 'workers' : undefined
    const nextTabQuery = tab === 'workers' ? 'workers' : undefined
    if (currentTabQuery === nextTabQuery) return

    router.replace({ query: nextQuery })
  }

  watch(
    () => route.query.tab,
    (newValue) => {
      const nextTab = normalizeHomeTab(newValue)
      if (activeTab.value !== nextTab) {
        activeTab.value = nextTab
      }
    },
  )

  watch(activeTab, (tab) => {
    syncTabQuery(tab)
  })

  return {
    activeTab,
  }
}
