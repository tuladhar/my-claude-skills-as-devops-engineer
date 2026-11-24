import { expect, test } from 'claude-code/testing'

import { extract } from './register'

const REPLY = [
  'I wrote the runbook command into a script:',
  '`/tmp/renew-cert.sh`',
  '',
  '| Check | Result |',
  '|---|---|',
  '| AWS | ok |',
  '',
  'See https://github.com/o/r/pull/17.',
  '',
  '```sh',
  'kubectl get secret ca.example.com -n istio-system',
  '```',
  '',
  'Suggested next:',
  '[1] `! bash /tmp/renew-cert.sh`',
  '[2] `/permissions`',
].join('\n')

test('extract finds every kind, suggestions first', async () => {
  const got = extract(REPLY)
  const kinds = got.map(i => `${i.kind}:${i.text.split('\n')[0]}`)

  expect(kinds).toEqual([
    'shell:bash /tmp/renew-cert.sh',
    'next:/permissions',
    'code:kubectl get secret ca.example.com -n istio-system',
    'table:| Check | Result |',
    'url:https://github.com/o/r/pull/17',
    'path:/tmp/renew-cert.sh',
  ])
  expect(got[3]?.label).toBe('Check | Result (1 rows)')
})
