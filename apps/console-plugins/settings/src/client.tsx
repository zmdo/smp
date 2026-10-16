import type { ReactNode } from 'react'
import { AccountView } from './pages/AccountView'
import { McpSettingsView } from './pages/McpSettingsView'

interface Slots {
  inject(name: string, register: () => () => void): void
  register(options: object, component: (props: { renderSlot?: unknown }) => ReactNode): () => void
}

export const inject = ['slots']

export function apply(ctx: { slots: Slots }): void {
  ctx.slots.inject('console.page', () => ctx.slots.register({
    name: 'console.page',
    key: 'settings',
  }, AccountView))
  ctx.slots.inject('console.page', () => ctx.slots.register({
    name: 'console.page',
    key: 'mcp',
  }, McpSettingsView))
}
