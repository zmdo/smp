import type { ReactNode } from 'react'
import { ServerHost } from './pages/hosts'
import { KeyListView } from './pages/KeyListView'

interface Slots {
  inject(name: string, register: () => () => void): void
  register(options: object, component: (props: { renderSlot?: unknown }) => ReactNode): () => void
}

export const inject = ['slots']

export function apply(ctx: { slots: Slots }): void {
  ctx.slots.inject('console.page', () => ctx.slots.register({
    name: 'console.page',
    key: 'servers',
  }, ServerHost))
  ctx.slots.inject('console.page', () => ctx.slots.register({
    name: 'console.page',
    key: 'keys',
  }, KeyListView))
}
