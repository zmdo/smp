import type { ReactNode } from 'react'
import { WalletHost } from './pages/hosts'
import { CardAccountView } from './pages/CardAccountView'

interface Slots {
  inject(name: string, register: () => () => void): void
  register(options: object, component: (props: { renderSlot?: unknown }) => ReactNode): () => void
}

export const inject = ['slots']

export function apply(ctx: { slots: Slots }): void {
  ctx.slots.inject('console.page', () => ctx.slots.register({
    name: 'console.page',
    key: 'wallet',
  }, WalletHost))
  ctx.slots.inject('console.page', () => ctx.slots.register({
    name: 'console.page',
    key: 'cards',
  }, CardAccountView))
}
