import { useSyncExternalStore } from 'react'
import { api } from './api'

export interface Me {
  authenticated: boolean
  username: string | null
  password_is_default: boolean
  totp_enabled: boolean
}

export interface LoginResult {
  ok: boolean
  totp_required: boolean
}

interface AuthSnap {
  checked: boolean
  authenticated: boolean
  username: string | null
  passwordIsDefault: boolean
  totpEnabled: boolean
}

let snap: AuthSnap = {
  checked: false,
  authenticated: false,
  username: null,
  passwordIsDefault: false,
  totpEnabled: false,
}
const listeners = new Set<() => void>()

function publish(next: AuthSnap): void {
  snap = next
  for (const listener of listeners) listener()
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener)
  return () => { listeners.delete(listener) }
}

export async function refreshAuth(): Promise<void> {
  try {
    const me = await api<Me>('/api/auth/me')
    publish({
      checked: true,
      authenticated: me.authenticated,
      username: me.username,
      passwordIsDefault: me.password_is_default,
      totpEnabled: me.totp_enabled,
    })
  } catch {
    publish({ checked: true, authenticated: false, username: null, passwordIsDefault: false, totpEnabled: false })
  }
}

export async function login(username: string, password: string, totpCode?: string): Promise<LoginResult> {
  const body: Record<string, string> = { username, password }
  if (totpCode !== undefined) body.totp_code = totpCode
  const result = await api<LoginResult>('/api/auth/login', { method: 'POST', body: JSON.stringify(body) })
  if (result.ok) await refreshAuth()
  return result
}

export async function logout(): Promise<void> {
  await api('/api/auth/logout', { method: 'POST' })
  publish({ ...snap, authenticated: false, username: null, totpEnabled: false })
}

export function useAuth() {
  const current = useSyncExternalStore(subscribe, () => snap)
  return { ...current, refresh: refreshAuth, login, logout }
}
