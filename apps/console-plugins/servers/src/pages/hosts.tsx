import { useState } from 'react'
import { RouteProvider } from '../../../shared/src/route'
import { ServerDetailView } from './ServerDetailView'
import { ServerFormView } from './ServerFormView'
import { ServerListView } from './ServerListView'
import { ServerTerminalView } from './ServerTerminalView'

function serverKind(path: string): 'list' | 'form' | 'detail' | 'terminal' {
  const pathname = path.split('?')[0]
  if (pathname === '/servers' || pathname === '/servers/') return 'list'
  if (pathname === '/servers/new' || pathname.endsWith('/edit')) return 'form'
  if (pathname.endsWith('/terminal')) return 'terminal'
  return 'detail'
}

export function ServerHost() {
  const [path, setPath] = useState('/servers')
  const kind = serverKind(path)
  return (
    <RouteProvider path={path} go={setPath}>
      {kind === 'list' && <ServerListView />}
      {kind === 'form' && <ServerFormView />}
      {kind === 'detail' && <ServerDetailView />}
      {kind === 'terminal' && <ServerTerminalView />}
    </RouteProvider>
  )
}
