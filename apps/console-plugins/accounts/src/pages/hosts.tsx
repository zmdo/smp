import { useState } from 'react'
import { RouteProvider } from '../../../shared/src/route'
import { CryptoAccountView } from './CryptoAccountView'
import { WalletDetailView } from './WalletDetailView'

export function WalletHost() {
  const [path, setPath] = useState('/accounts/crypto')
  const detail = path.split('?')[0].split('/').filter(Boolean).length > 2
  return (
    <RouteProvider path={path} go={setPath}>
      {detail ? <WalletDetailView /> : <CryptoAccountView />}
    </RouteProvider>
  )
}
