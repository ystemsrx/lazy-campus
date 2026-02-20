import { onUnmounted, ref } from 'vue'

export type AdminToastType = 'success' | 'error' | 'info'

export interface AdminToast {
  text: string
  type: AdminToastType
}

export function useAdminToast() {
  const toast = ref<AdminToast | null>(null)
  let toastTimer = 0

  function showToast(text: string, type: AdminToastType = 'info') {
    toast.value = { text, type }
    clearTimeout(toastTimer)
    toastTimer = window.setTimeout(() => {
      toast.value = null
    }, 3500)
  }

  function clearToast() {
    toast.value = null
  }

  onUnmounted(() => {
    clearTimeout(toastTimer)
  })

  return {
    toast,
    showToast,
    clearToast,
  }
}

export type AdminToastModel = ReturnType<typeof useAdminToast>
