---
name: better-prompt-suggestions
description: End every reply with a numbered "Suggested next:" list of up to 3 exact things the user could type next, best first, so Claude Code's grey prompt suggestion (accepted with Tab) offers the best one and the user can pick another by typing its number. The plugin's SessionStart hook loads these rules into every session; run the skill by hand to re-apply them mid-session.
disable-model-invocation: true
---

# Better prompt suggestions

After you reply, Claude Code may show a grey suggestion in the prompt box that the user accepts with Tab. It guesses that suggestion from the end of the conversation. Make the guess easy: finish every reply with the exact text the user would most likely type next. When there are other sensible next steps, number them so the user can pick one by typing its number.

## The rule

End every reply with this block, with nothing after it:

Suggested next:
[1] `<exact text to type>`
[2] `<exact text to type>`
[3] `<exact text to type>`

- **[1] is the best one.** It is the action you would recommend.
- **Only list real options.** Use 1 to 3 items. When there is only one sensible next step, give only [1].
- **Each item is verbatim and complete.** It must work if typed exactly as shown: real paths, names, flags and values from this conversation, no `<placeholders>`, no `...`.
- **One line per item.** Chain shell steps with `&&` instead of using several lines.
- **No explanations in the list.** Only the text in backticks after each number.
- **No secrets.** Never put tokens, passwords or keys in it.

## Choosing the actions

Go down this list to choose [1], then fill [2] and [3] with the next best real alternatives:

1. **Something only the user can do.** A command they must run themselves goes as `! <command>` (for example an interactive login, a command needing their shell or `sudo`). A Claude Code command goes as is, for example `/mcp`, `/login`, `/plugin install x`.
2. **An answer to a question you just asked.** Give the answer they most likely want, for example `yes, include the clipboard hook` or `go`. If you offered options, the one you recommended is [1] and the others follow.
3. **The natural follow-up to finished work.** For example `run the tests`, `commit and open a PR`, `deploy it to staging`.
4. **Nothing obvious.** Give the most useful next request about the current task, in the user's own short style.

Write items the way the user writes: short, plain, lowercase is fine.

## When the user replies with a number

If the user's whole message is just a number such as `2` (or `[2]`), it means "do item [2] from your last Suggested next list". Do it. If that item is something only the user can run (a `! <command>` or a `/command`), you can't run it for them: say so in one line and show it again as [1] so they can Tab it.

## Examples

A fix the user must run:

> The server is registered only for the subfolder. Register it for your user account instead, then reconnect it.
>
> Suggested next:
> [1] `! claude mcp remove iximiuz-labs -s local && claude mcp add --scope user --transport http iximiuz-labs https://labs.iximiuz.com/mcp`
> [2] `/mcp`

A question with a recommended answer:

> Should I build the skill-only version and open the PR?
>
> Suggested next:
> [1] `yes, build it and open the PR`
> [2] `include the clipboard hook too`

Finished work with one obvious step:

> All 42 tests pass and the branch is pushed.
>
> Suggested next:
> [1] `open a PR`
