#!/bin/sh
# SessionStart hook: print the skill's rules (without the YAML front matter).
# Claude Code adds a SessionStart hook's stdout to Claude's context, so the
# rules apply on every startup, resume, /clear and compaction.
skill="${CLAUDE_PLUGIN_ROOT:-$(dirname "$0")/..}/skills/better-prompt-suggestions/SKILL.md"
[ -f "$skill" ] || exit 0
awk 'NR==1 && /^---$/ {fm=1; next} fm && /^---$/ {fm=0; next} !fm' "$skill"

# Claude Code hides its grey suggestion near usage limits and after many turns
# without the user. CLAUDE_CODE_ENABLE_PROMPT_SUGGESTION=true keeps it on.
# It must be set before Claude Code starts, so a plugin can't set it; ask
# Claude to tell the user once instead.
case "$CLAUDE_CODE_ENABLE_PROMPT_SUGGESTION" in
  1|true|TRUE|True) ;;
  *) cat <<'TIP'

## Setup tip (mention once)

`CLAUDE_CODE_ENABLE_PROMPT_SUGGESTION` is not set, so Claude Code hides its grey suggestion when the user nears a usage limit or after many turns without them. In your first reply this session, add one short line telling the user they can keep suggestions on by adding `"CLAUDE_CODE_ENABLE_PROMPT_SUGGESTION": "true"` to the `env` section of `~/.claude/settings.json` and restarting Claude Code, and offer to do it. Don't repeat it later in the session.
TIP
  ;;
esac
