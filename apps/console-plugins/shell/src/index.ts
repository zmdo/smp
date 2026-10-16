/**
 * Host half. Without a console session the browser gets /login, a page of its
 * own, and the console frame is not loaded. A live smp_session may open the
 * frame and the connection behind 军师. The launch token stays inside this
 * process and is never sent to the browser.
 */
import { spawnSync } from 'node:child_process'
import { clearDshCookieHeaders, dshAuthCookieNames, indexGate, smpSessionValue, tokenExchangeUrl } from './gate.ts'
import { LOGIN_PAGE } from './login-page.ts'

interface IndexRequest {
  method?: string
  url?: string
  headers: { cookie?: string | string[] }
}

interface IndexResponse {
  setHeader?(name: string, value: string | readonly string[]): void
  writeHead(status: number, headers?: Record<string, string>): unknown
  end(body?: string): unknown
}

interface Admission {
  rejection?: number
}

interface ConnectionService {
  authorizeIndex(request: IndexRequest, response: IndexResponse): boolean
  authenticatedUrl(baseUrl: string): string
  admit(request: IndexRequest): Admission
}

interface HostCtx {
  connection: ConnectionService
  webServer: {
    register(route: {
      kind: 'exact'
      path: string
      handler: (request: IndexRequest, response: IndexResponse) => void | Promise<void>
    }): () => void
  }
  effect(run: () => (() => void)): void
}

export const inject = ['connection', 'webServer']

const AUTH_URL = process.env.SMP_AUTH_URL ?? 'http://web-api:8000/api/auth/me'
const CACHE_MS = 15_000
const sessionCache = new Map<string, { ok: boolean; expires: number }>()

const CHECK = `
let raw = ''
process.stdin.setEncoding('utf8')
process.stdin.on('data', chunk => { raw += chunk })
process.stdin.on('end', () => {
  const body = JSON.parse(raw)
  fetch(body.url, { headers: { cookie: body.cookie } })
    .then(response => response.json())
    .then(me => {
      process.stdout.write(me.authenticated === true ? '1' : '0')
    })
    .catch(() => { process.stdout.write('0') })
})
`

function header(request: IndexRequest, name: 'cookie'): string {
  const value = request.headers[name]
  return Array.isArray(value) ? value.join('; ') : value ?? ''
}

function consoleAuthenticated(cookieHeader: string): boolean {
  const session = smpSessionValue(cookieHeader)
  if (session === undefined) return false
  const now = Date.now()
  const cached = sessionCache.get(session)
  if (cached !== undefined && cached.expires > now) return cached.ok
  const result = spawnSync(process.execPath, ['--input-type=module', '-e', CHECK], {
    input: JSON.stringify({ url: AUTH_URL, cookie: cookieHeader }),
    encoding: 'utf8',
    timeout: 4000,
  })
  const ok = result.stdout.trim() === '1'
  if (ok) sessionCache.set(session, { ok: true, expires: now + CACHE_MS })
  return ok
}

function launchToken(connection: ConnectionService): string | undefined {
  return new URL(connection.authenticatedUrl('http://127.0.0.1/')).searchParams.get('token') ?? undefined
}

function expirePageConnection(response: IndexResponse, cookieHeader: string): void {
  const clearing = clearDshCookieHeaders(dshAuthCookieNames(cookieHeader))
  if (clearing.length > 0) response.setHeader?.('set-cookie', clearing)
}

export function apply(ctx: HostCtx): void {
  ctx.effect(() => ctx.webServer.register({
    kind: 'exact',
    path: '/login',
    handler: (request, response) => {
      if (request.method !== 'GET' && request.method !== 'HEAD') {
        response.writeHead(405, { allow: 'GET, HEAD' })
        response.end()
        return
      }
      const cookieHeader = header(request, 'cookie')
      if (consoleAuthenticated(cookieHeader)) {
        response.writeHead(303, { location: '/', 'cache-control': 'no-store' })
        response.end()
        return
      }
      expirePageConnection(response, cookieHeader)
      response.writeHead(200, { 'content-type': 'text/html; charset=utf-8', 'cache-control': 'no-store' })
      response.end(request.method === 'HEAD' ? undefined : LOGIN_PAGE)
    },
  }))

  const connection = ctx.connection
  const original = connection.authorizeIndex.bind(connection)
  connection.authorizeIndex = (request, response) => {
    const cookieHeader = header(request, 'cookie')
    const gate = indexGate(consoleAuthenticated(cookieHeader), !('rejection' in connection.admit(request)))
    if (gate === 'login') {
      expirePageConnection(response, cookieHeader)
      response.writeHead(303, { location: '/login', 'cache-control': 'no-store' })
      response.end()
      return false
    }
    if (gate === 'app') return original(request, response)
    const token = launchToken(connection)
    if (token === undefined || request.method !== 'GET') return original(request, response)
    return original({
      method: request.method,
      url: tokenExchangeUrl(request.url ?? '/', token),
      headers: request.headers,
    }, response)
  }
}
