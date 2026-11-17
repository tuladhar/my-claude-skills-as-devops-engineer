---
name: step-by-step
description: Explain a topic using chunking with a check for understanding (scaffolding) - one basic sentence per mini step, waiting for the user to reply "understood" before continuing.
disable-model-invocation: true
argument-hint: "[topic to explain]"
---

# Step-by-step explanation (chunking + check for understanding)

Explain the topic the user names (or, if none is given, the thing currently being worked on in this conversation) using this format.

## Rules

1. **One mini step per message.** Each message contains exactly ONE basic sentence that carries ONE new idea.
   - Format: `**Mini step N:** <one plain sentence>.`
   - Use plain words. Introduce a technical term only after explaining the idea, e.g. "...adds an entry to their DNS (called a CNAME)."
   - Use the real names and values from the user's actual task, not abstract placeholders.
2. **Then stop and wait.** End every message with: `Reply **"understood"** for mini step N+1.`
   Do not continue until the user replies "understood" (typos such as "undestood" count).
3. **Build in order.** Each step builds on the previous one. Start from what already exists and works, move to the goal, then to the obstacle, then to each piece of the solution, and finish with how to verify it.
4. **Questions interrupt the flow.** If the user asks a question instead of saying "understood", answer only that question, in a few short lines (a small numbered list is fine), then ask for "understood" before resuming at the next mini step.
5. **If the user says they didn't understand**, restart smaller: split the idea into even simpler mini steps. Never repeat the same wording.
6. **Final step.** Mark it `**Mini step N (the last one):**`. After the user confirms it, give a short numbered checklist of what is left to actually do, with who does each item.

## Don't

- Don't use tables, headings or code blocks inside the mini steps.
- Don't preview upcoming steps or add a "why this matters" paragraph.
- Don't put more than one sentence in a mini step (the "Reply understood" line doesn't count).
