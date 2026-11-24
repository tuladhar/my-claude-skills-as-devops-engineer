import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { CopyItem, CopyKind } from '../types'

// Hotkeys in order: 0 is the whole reply, then 1-9, then letters (q closes).
const KEYS = '123456789abcdefghijklmnoprstuvwxyz'
const items = atom({ plugin: 'smart-copy', key: 'items' } as const, [], {
  shape: 'items-1',
})
const isOpen = atom({ plugin: 'smart-copy', key: 'isOpen' } as const, false)

const TAG: Record<CopyKind, string> = {
  reply: 'reply',
  next: 'next',
  shell: 'shell',
  code: 'code',
  table: 'table',
  url: 'url',
  path: 'path',
  inline: 'code',
}

const firstLine = (text: string) => text.split('\n').find(l => l.trim()) ?? ''

/** Pulls the copyable pieces out of one reply, most useful first. */
export function extract(reply: string): CopyItem[] {
  const out: CopyItem[] = []
  const seen = new Set<string>()
  const add = (kind: CopyKind, text: string, label = firstLine(text)) => {
    const t = text.replace(/\s+$/, '')
    if (t.length < 2 || seen.has(t)) return
    seen.add(t)
    out.push({ kind, label: label.trim(), text: t })
  }

  // Fenced code blocks, taken out so nothing else matches inside them.
  const code: string[] = []
  const prose = reply.replace(/```[^\n]*\n([\s\S]*?)```/g, (_, body: string) => {
    code.push(body)
    return '\n'
  })

  // "Suggested next" items: [n] `text`. A leading "! " means a shell command.
  const nextLine = /^\s*\[\d+\]\s+`(.+)`\s*$/
  const lines = prose.split('\n')
  for (const l of lines) {
    const m = nextLine.exec(l)
    if (!m) continue
    const text = m[1] ?? ''
    if (text.startsWith('! ')) add('shell', text.slice(2))
    else add('next', text)
  }

  for (const body of code) add('code', body)

  // Markdown tables: runs of lines starting with "|".
  let table: string[] = []
  const flush = () => {
    if (table.length >= 2) {
      const head = (table[0] ?? '').split('|').map(c => c.trim()).filter(Boolean)
      add('table', table.join('\n'), `${head.join(' | ')} (${table.length - 2} rows)`)
    }
    table = []
  }
  for (const l of lines) {
    if (/^\s*\|/.test(l)) table.push(l.trim())
    else flush()
  }
  flush()

  const rest = lines.filter(l => !nextLine.test(l)).join('\n')

  for (const m of rest.matchAll(/https?:\/\/[^\s<>()\[\]`"']+/g)) {
    add('url', m[0].replace(/[.,;:!?]+$/, ''))
  }

  // Inline code spans: paths first, then anything command-like.
  const spans = [...rest.matchAll(/`([^`\n]+)`/g)].map(m => (m[1] ?? '').trim())
  for (const s of spans) {
    if (/^(~|\.{0,2})\/\S+$/.test(s)) add('path', s)
  }
  for (const s of spans) {
    if (s.length >= 4) add('inline', s)
  }

  return out
}

/** The text of the last reply: every assistant message since the last prompt. */
async function lastReply($: EngineInterface) {
  const found = await $.session.messages({ last: 80 })
  if ('deny' in found) return ''
  const parts: string[] = []
  for (let i = found.length - 1; i >= 0; i--) {
    const m = found[i]
    if (!m) continue
    if (m.role === 'assistant') {
      if (m.text.trim()) parts.unshift(m.text)
      continue
    }
    // A user message that only carries tool results is mid-reply.
    if (m.toolResults && m.toolResults.length > 0) continue
    // The prompt before the reply ends it; ones after it (this command) are skipped.
    if (parts.length > 0) break
  }
  return parts.join('\n\n')
}

const stripNext = (reply: string) =>
  reply.replace(/\n*Suggested next:\s*\n(\s*\[\d+\].*\n?)+\s*$/, '').trimEnd()

export const register: Register = on => {
  // The band's id, learned the first time it is drawn; focus needs it.
  let bandId: string | undefined

  on('session.start', async ($, e, next) => {
    await $.command.register({
      name: 'smart-copy',
      description:
        'Copy a code block, command, table, URL or path from the last reply (/smart-copy [key])',
    })
    return next(e)
  })

  // Typing a new prompt puts the picker away.
  on('prompt.submit', async ($, e, next) => {
    await update($, isOpen, () => false)
    return next(e)
  })

  on('command.run', { command: 'smart-copy' }, async ($, e) => {
    const reply = await lastReply($)
    if (!reply) return { text: 'smart-copy: no reply to copy from yet.' }

    const list: CopyItem[] = [
      { kind: 'reply', label: 'Whole reply', text: stripNext(reply) },
      ...extract(reply).slice(0, KEYS.length),
    ]
    await update($, items, () => list)

    const key = e.args.trim().toLowerCase()
    if (key) {
      const at = key === '0' ? 0 : KEYS.indexOf(key) + 1
      const item = at >= 0 && key.length === 1 ? list[at] : undefined
      if (!item) return { text: `smart-copy: no item "${key}". Run /smart-copy to see them.` }
      const done = await $.ui.copy({ text: item.text })
      return {
        text: done.isCopied
          ? `Copied ${TAG[item.kind]}: ${item.label}`
          : `smart-copy: copy failed (${done.reason}).`,
      }
    }

    await update($, isOpen, () => true)
    // Hand the band the keyboard so a bare key copies at once.
    for (let i = 0; i < 20 && bandId === undefined; i++) await $.clock.sleep(25)
    if (bandId !== undefined) {
      void $.ui.focus({ requestId: bandId, key: list.length > 1 ? 'item:1' : 'item:0' })
    }
    return {}
  })

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    bandId = e.requestId
    if (e.props.hasSurvey || !(await read($, isOpen))) return next(e)

    const { Box, Text, Button } = $.ui.resolve(e)
    const list = await read($, items)
    const width = Math.max(20, e.props.bodyColumns - 16)
    const cut = (s: string) => (s.length > width ? `${s.slice(0, width - 1)}…` : s)
    const close = () => update($, isOpen, () => false)

    const copy = async (item: CopyItem, surface: typeof e.surface) => {
      const done = await $.ui.copy({ text: item.text, surface })
      $.ui.toast(
        done.isCopied ? `Copied ${TAG[item.kind]}: ${cut(item.label)}` : `Copy failed: ${done.reason}`,
      )
      if (done.isCopied) await close()
    }

    return (
      <Box flexDirection="column">
        <Text>
          <Text bold>Copy from the last reply</Text>
          <Text dimColor> · press a key · q to close</Text>
        </Text>
        {list.map((item, i) => (
          <Button
            key={`item:${i}`}
            hotkey={i === 0 ? '0' : KEYS[i - 1]}
            plain
            onPress={press => copy(item, press.surface)}
          >
            {cut(item.label)} <Text dimColor>{TAG[item.kind]}</Text>
          </Button>
        ))}
        <Button key="close" hotkey="q" plain dimColor role="dismiss" onPress={close}>
          Close
        </Button>
      </Box>
    )
  })
}
