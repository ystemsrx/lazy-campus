export type SettingsTab = 'profile' | 'worker'
export type SettingsSaveStatus = 'idle' | 'saving' | 'saved'

export interface ProfileForm {
  email: string
  nickname: string
  gender: 'male' | 'female' | ''
}

export interface WorkerForm {
  enabled: boolean
  skill_tag_ids: number[]
  bio: string
  phone: string
  wechat: string
}

export function createProfileForm(): ProfileForm {
  return {
    email: '',
    nickname: '',
    gender: '',
  }
}

export function createWorkerForm(): WorkerForm {
  return {
    enabled: false,
    skill_tag_ids: [],
    bio: '',
    phone: '',
    wechat: '',
  }
}
