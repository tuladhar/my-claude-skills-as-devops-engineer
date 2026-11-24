export type CopyKind =
  | 'reply'
  | 'code'
  | 'next'
  | 'shell'
  | 'table'
  | 'url'
  | 'path'
  | 'inline'

export type CopyItem = { kind: CopyKind; label: string; text: string }

declare module 'claude-code' {
  interface PluginState {
    'smart-copy': { items: Shaped<CopyItem[]>; isOpen: boolean }
  }
}
