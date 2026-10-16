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

interface AuthBucket {
  snap: AuthSnap
  listeners: Set<() => void>
}

const AUTH_KEY = '__SMP_CONSOLE_AUTH__'

function bucket(): AuthBucket {
  const host = globalThis as typeof globalThis & { [AUTH_KEY]?: AuthBucket }
  if (host[AUTH_KEY] === undefined) {
    host[AUTH_KEY] = {
      snap: {
        checked: false,
        authenticated: false,
        username: null,
        passwordIsDefault: false,
        totpEnabled: false,
      },
      listeners: new Set(),
    }
  }
  return host[AUTH_KEY]
}

function publish(next: AuthSnap): void {
  const store = bucket()
  store.snap = next
  for (const listener of store.listeners) listener()
}

function subscribe(listener: () => void): () => void {
  const store = bucket()
  store.listeners.add(listener)
  return () => { store.listeners.delete(listener) }
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
  publish({ ...bucket().snap, authenticated: false, username: null, totpEnabled: false })
}

export function useAuth() {
  const current = useSyncExternalStore(subscribe, () => bucket().snap)
  return { ...current, refresh: refreshAuth, login, logout }
}
