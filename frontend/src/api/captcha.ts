import api from './client'
import type { AnonCaptchaScene, CaptchaScene } from '../utils/captcha'

export interface CaptchaChallenge {
  challenge_id: string
  scene: CaptchaScene
  width: number
  height: number
  thumb_y: number
  thumb_width: number
  thumb_height: number
  image: string
  thumb: string
  expires_at: string
}

export interface CaptchaVerifyResult {
  scene: CaptchaScene
  captcha_token: string
}

export async function createCaptchaChallenge(scene: CaptchaScene) {
  const { data } = await api.post<CaptchaChallenge>('/captcha/challenges', { scene })
  return data
}

export interface TrajectoryPoint {
  x: number
  t: number
}

export async function verifyCaptchaChallenge(
  challengeId: string,
  x: number,
  y: number,
  trajectory: TrajectoryPoint[],
) {
  const { data } = await api.post<CaptchaVerifyResult>('/captcha/challenges/verify', {
    challenge_id: challengeId,
    x,
    y,
    trajectory,
  })
  return data
}

// ── 匿名端点（注册 / 登录，无需登录态）──────────────────────────

export interface AnonCaptchaChallenge {
  challenge_id: string
  scene: AnonCaptchaScene
  width: number
  height: number
  thumb_y: number
  thumb_width: number
  thumb_height: number
  image: string
  thumb: string
  expires_at: string
}

export interface AnonCaptchaVerifyResult {
  scene: AnonCaptchaScene
  captcha_token: string
}

export async function createAnonCaptchaChallenge(sessionId: string, scene: AnonCaptchaScene) {
  const { data } = await api.post<AnonCaptchaChallenge>('/captcha/anon/challenges', {
    session_id: sessionId,
    scene,
  })
  return data
}

export async function verifyAnonCaptchaChallenge(
  sessionId: string,
  challengeId: string,
  x: number,
  y: number,
  trajectory: TrajectoryPoint[],
) {
  const { data } = await api.post<AnonCaptchaVerifyResult>('/captcha/anon/challenges/verify', {
    session_id: sessionId,
    challenge_id: challengeId,
    x,
    y,
    trajectory,
  })
  return data
}
