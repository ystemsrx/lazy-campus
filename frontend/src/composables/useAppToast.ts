import { onUnmounted, ref } from 'vue'

export type AppToastType = 'info' | 'warning' | 'error' | 'success'

export interface AppToastMessage {
  text: string
  type: AppToastType
}

export type AppToastNotifier = (text: string, type?: AppToastType) => void

export function useAppToast(defaultDuration = 3500) {
  const toast = ref<AppToastMessage | null>(null)
  let timer = 0

  function showToast(text: string, type: AppToastType = 'info', duration = defaultDuration) {
    clearTimeout(timer)
    toast.value = { text, type }
    if (duration > 0) {
      timer = window.setTimeout(() => { toast.value = null }, duration)
    }
  }

  function clearToast() {
    clearTimeout(timer)
    toast.value = null
  }

  onUnmounted(() => { clearTimeout(timer) })

  return { toast, showToast, clearToast }
}
