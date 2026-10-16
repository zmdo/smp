import { createContext, useContext, type MouseEvent, type ReactNode } from 'react'

const PathContext = createContext('/servers')
const GoContext = createContext<(to: string) => void>(() => {})

export function RouteProvider(props: { path: string; go: (to: string) => void; children: ReactNode }) {
  return (
    <PathContext.Provider value={props.path}>
      <GoContext.Provider value={props.go}>{props.children}</GoContext.Provider>
    </PathContext.Provider>
  )
}

export function useNavigate(): (to: string) => void {
  return useContext(GoContext)
}

export function useParams(): { id: string } {
  const parts = useContext(PathContext).split('?')[0].split('/').filter(Boolean)
  if (parts[0] === 'servers' && parts[1] !== undefined && parts[1] !== 'new') return { id: decodeURIComponent(parts[1]) }
  if (parts[0] === 'accounts' && parts[2] !== undefined) return { id: decodeURIComponent(parts[2]) }
  return { id: '' }
}

export function useSearchParams(): [URLSearchParams] {
  const path = useContext(PathContext)
  return [new URLSearchParams(path.split('?')[1] ?? '')]
}

export function Link(props: {
  to: string
  className?: string
  title?: string
  children: ReactNode
  onClick?: (event: MouseEvent<HTMLAnchorElement>) => void
}) {
  const go = useContext(GoContext)
  return (
    <a
      href={props.to}
      className={props.className}
      title={props.title}
      onClick={(event) => {
        props.onClick?.(event)
        if (event.defaultPrevented) return
        event.preventDefault()
        go(props.to)
      }}
    >
      {props.children}
    </a>
  )
}
