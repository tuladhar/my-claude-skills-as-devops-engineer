---
name: better-prompt-suggestions
description: End every reply with the single best next thing the user would type, alone on the last line, so Claude Code's grey prompt suggestion (accepted with Tab) offers it. The plugin's SessionStart hook loads these rules into every session; run the skill by hand to re-apply them mid-session.
disable-model-invocation: true
---

# Better prompt suggestions

After you reply, Claude Code may show a grey suggestion in the prompt box that the user accepts with Tab. It guesses that suggestion from the end of the conversation. Make the guess easy: finish every reply with the exact text the user would most likely type next.

## The rule

End every reply with one final line in this form, with nothing after it:

**Next:** `<exact text to type>`

- **Exactly one action.** Pick the best one. No lists, no "or".
- **Verbatim and complete.** It must work if typed exactly as shown: real paths, names, flags and values from this conversation, no `<placeholders>`, no `...`.
- **One line.** Chain shell steps with `&&` instead of using several lines.
- **No secrets.** Never put tokens, passwords or keys in it.

## Choosing the action

Go down this list and use the first that fits:

1. **Something only the user can do.** A command they must run themselves goes as `! <command>` (for example an interactive login, a command needing their shell or `sudo`). A Claude Code command goes as is, for example `/mcp`, `/login`, `/plugin install x`.
2. **An answer to a question you just asked.** Give the answer they most likely want, for example `yes, include the clipboard hook` or `go`. If you offered options, use the one you recommended.
3. **The natural follow-up to finished work.** For example `run the tests`, `commit and open a PR`, `deploy it to staging`.
4. **Nothing obvious.** Give the most useful next request about the current task, in the user's own short style.

Write it the way the user writes: short, plain, lowercase is fine.

## Examples

A fix the user must run:

> The server is registered only for the subfolder. Register it for your user account instead, then reconnect it.
>
> **Next:** `! claude mcp remove iximiuz-labs -s local && claude mcp add --scope user --transport http iximiuz-labs https://labs.iximiuz.com/mcp`

A question with a recommended answer:

> Should I build the skill-only version and open the PR?
>
> **Next:** `yes, build it and open the PR`

Finished work:

> All 42 tests pass and the branch is pushed.
>
> **Next:** `open a PR`
