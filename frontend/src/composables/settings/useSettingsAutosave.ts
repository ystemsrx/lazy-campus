import { onUnmounted, ref, watch, type Ref } from 'vue'

import type { ProfileForm, SettingsSaveStatus, WorkerForm } from './types'

interface UseSettingsAutosaveOptions {
  profileForm: Ref<ProfileForm>
  workerForm: Ref<WorkerForm>
  isDataLoaded: Ref<boolean>
  saveProfile: () => Promise<void>
  saveWorker: () => Promise<void>
  onError: (error: unknown) => void
}

export function useSettingsAutosave(options: UseSettingsAutosaveOptions) {
  const saveStatus = ref<SettingsSaveStatus>('idle')

  let profileDebounce: ReturnType<typeof setTimeout> | null = null
  let workerDebounce: ReturnType<typeof setTimeout> | null = null
  let savedResetTimer: ReturnType<typeof setTimeout> | null = null

  function markSaved() {
    saveStatus.value = 'saved'
    if (savedResetTimer) clearTimeout(savedResetTimer)
    savedResetTimer = setTimeout(() => {
      saveStatus.value = 'idle'
    }, 2000)
  }

  async function doSaveProfile() {
    try {
      await options.saveProfile()
      markSaved()
    } catch (error) {
      saveStatus.value = 'idle'
      options.onError(error)
    }
  }

  async function doSaveWorker() {
    try {
      await options.saveWorker()
      markSaved()
    } catch (error) {
      saveStatus.value = 'idle'
      options.onError(error)
    }
  }

  watch(
    options.profileForm,
    () => {
      if (!options.isDataLoaded.value) return
      if (!options.profileForm.value.email || !options.profileForm.value.gender) return

      saveStatus.value = 'saving'
      if (profileDebounce) clearTimeout(profileDebounce)
      profileDebounce = setTimeout(doSaveProfile, 500)
    },
    { deep: true },
  )

  watch(
    options.workerForm,
    () => {
      if (!options.isDataLoaded.value) return

      saveStatus.value = 'saving'
      if (workerDebounce) clearTimeout(workerDebounce)
      workerDebounce = setTimeout(doSaveWorker, 500)
    },
    { deep: true },
  )

  onUnmounted(() => {
    if (profileDebounce) clearTimeout(profileDebounce)
    if (workerDebounce) clearTimeout(workerDebounce)
    if (savedResetTimer) clearTimeout(savedResetTimer)
  })

  return {
    saveStatus,
  }
}
