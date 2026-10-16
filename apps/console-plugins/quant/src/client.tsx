import type { ReactNode } from 'react'
import { QuantOverviewView } from './pages/QuantOverviewView'
import { MarketView } from './pages/MarketView'
import { ExchangeView } from './pages/ExchangeView'
import { QuantStrategyView } from './pages/QuantStrategyView'

interface Slots {
  inject(name: string, register: () => () => void): void
  register(options: object, component: (props: { renderSlot?: unknown }) => ReactNode): () => void
}

export const inject = ['slots']

export function apply(ctx: { slots: Slots }): void {
  ctx.slots.inject('console.page', () => ctx.slots.register({
    name: 'console.page',
    key: 'quant-overview',
  }, QuantOverviewView))
  ctx.slots.inject('console.page', () => ctx.slots.register({
    name: 'console.page',
    key: 'quant-markets',
  }, MarketView))
  ctx.slots.inject('console.page', () => ctx.slots.register({
    name: 'console.page',
    key: 'quant-exchanges',
  }, ExchangeView))
  ctx.slots.inject('console.page', () => ctx.slots.register({
    name: 'console.page',
    key: 'quant-strategies',
  }, QuantStrategyView))
}
