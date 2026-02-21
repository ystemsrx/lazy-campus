import { nextTick, onMounted, onUnmounted, ref, watch, type Ref } from 'vue'

import type { SettingsTab } from './types'

export function useSettingsTabs(activeTab: Ref<SettingsTab>) {
  const tabRefs = ref<(HTMLElement | null)[]>([null, null])
  const indicatorStyle = ref<Record<string, string | number>>({ opacity: 0 })

  function updateIndicator() {
    const idx = activeTab.value === 'profile' ? 0 : 1
    const el = tabRefs.value[idx]
    if (!el) return

    indicatorStyle.value = {
      opacity: 1,
      width: `${el.offsetWidth}px`,
      height: `${el.offsetHeight}px`,
      transform: `translate(${el.offsetLeft}px, ${el.offsetTop}px)`,
    }
  }

  watch(activeTab, async () => {
    await nextTick()
    updateIndicator()
  })

  onMounted(() => {
    window.addEventListener('resize', updateIndicator)
  })

  onUnmounted(() => {
    window.removeEventListener('resize', updateIndicator)
  })

  function setTabRef(index: 0 | 1, el: HTMLElement | null) {
    tabRefs.value[index] = el
  }

  return {
    indicatorStyle,
    updateIndicator,
    setTabRef,
  }
}
