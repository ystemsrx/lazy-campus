export type CaptchaScene = 'view_worker_contact' | 'chat_send' | 'task_publish' | 'task_accept'
export type AnonCaptchaScene = 'register' | 'login'

export type CaptchaRequiredDetail = {
  code: 'CAPTCHA_REQUIRED'
  scene: CaptchaScene | AnonCaptchaScene
  message?: string
}

export class CaptchaCancelledError extends Error {
  constructor() {
    super('CAPTCHA_CANCELLED')
    this.name = 'CaptchaCancelledError'
  }
}

export function parseCaptchaRequiredDetail(error: unknown): CaptchaRequiredDetail | null {
  const detail = (error as any)?.response?.data?.detail
  if (!detail || typeof detail !== 'object') return null
  if (detail.code !== 'CAPTCHA_REQUIRED' || typeof detail.scene !== 'string') return null
  return detail as CaptchaRequiredDetail
}

export async function withCaptchaRetry<T>(
  request: (captchaToken?: string) => Promise<T>,
  requestCaptcha: (scene: CaptchaScene) => Promise<string | null>,
): Promise<T> {
  try {
    return await request()
  } catch (error) {
    const detail = parseCaptchaRequiredDetail(error)
    if (!detail) {
      throw error
    }
    const token = await requestCaptcha(detail.scene)
    if (!token) {
      throw new CaptchaCancelledError()
    }
    return request(token)
  }
}
