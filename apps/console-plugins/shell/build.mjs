import { mkdirSync, writeFileSync } from 'node:fs'
import * as esbuild from 'esbuild'

mkdirSync('lib', { recursive: true })
writeFileSync('lib/index.js', '/** Host half. The shell only draws in the browser. */\nexport function apply() {}\n')

await esbuild.build({
  entryPoints: ['src/client.tsx'],
  outfile: 'lib/client.js',
  bundle: true,
  format: 'cjs',
  platform: 'browser',
  jsx: 'automatic',
  external: ['react', 'react/jsx-runtime'],
  loader: { '.css': 'text' },
  banner: {
    js: 'window.__ModuleLoader__.load({ id: "@smp/console-shell", factory: (require) => {\nvar module = { exports: {} }; var exports = module.exports;',
  },
  footer: {
    js: 'return module.exports; } });',
  },
})
