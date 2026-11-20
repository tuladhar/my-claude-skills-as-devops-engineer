#!/bin/sh
# SessionStart hook: print the skill's rules (without the YAML front matter).
# Claude Code adds a SessionStart hook's stdout to Claude's context, so the
# rules apply on every startup, resume, /clear and compaction.
skill="${CLAUDE_PLUGIN_ROOT:-$(dirname "$0")/..}/skills/better-prompt-suggestions/SKILL.md"
[ -f "$skill" ] || exit 0
awk 'NR==1 && /^---$/ {fm=1; next} fm && /^---$/ {fm=0; next} !fm' "$skill"
