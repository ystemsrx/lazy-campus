import api from './client'
import type { LoginPayload, LoginResponse, RegisterPayload, RegisterResponse, RegistrationStatus, UserMe } from '../types/api'

export async function login(payload: LoginPayload): Promise<LoginResponse> {
  const { data } = await api.post<LoginResponse>('/auth/login', payload)
  return data
}

export async function register(payload: RegisterPayload): Promise<RegisterResponse> {
  const { data } = await api.post<RegisterResponse>('/auth/register', payload)
  return data
}

export async function fetchRegistrationStatus(): Promise<RegistrationStatus> {
  const { data } = await api.get<RegistrationStatus>('/auth/registration-status')
  return data
}

export async function getMe(): Promise<UserMe> {
  const { data } = await api.get<UserMe>('/users/me')
  return data
}

export async function completeProfile(payload: { email: string; gender: 'male' | 'female'; nickname: string }): Promise<UserMe> {
  const { data } = await api.post<UserMe>('/users/me/complete-profile', payload)
  return data
}
