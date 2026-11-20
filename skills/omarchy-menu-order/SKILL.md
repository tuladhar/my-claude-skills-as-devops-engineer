---
name: omarchy-menu-order
description: Reorder items in an Omarchy menu (the System menu by default), or put a menu back to its default order. Use for requests like "move Lock to the top", "put Logout under Reboot", "move lock behind screensaver", "reset the system menu order", or /omarchy-menu-order. Works live from the machine's own Omarchy menu, so it stays correct across Omarchy updates.
argument-hint: "[what to move, e.g. 'lock to the top' | reset | status]"
---

# Reorder an Omarchy menu

The user wants to change the order of items in an Omarchy menu (Super + Esc opens the System menu), or undo that. Do the work yourself with the helper below. Don't hand the user commands to run or files to edit.

## How it works (know this, don't lecture it)

- Omarchy builds its menu from the stock file `/usr/share/omarchy/default/omarchy/omarchy-menu.jsonc` (owned by the omarchy package, overwritten on every update) merged with the user's file `~/.config/omarchy/extensions/omarchy-menu.jsonc`. The menu reloads the user's file on save, so no restart is needed.
- Overriding a stock item by id keeps its original position, so items can't be moved that way. The helper hides the stock items of one menu (`"when":"false"`) and adds copies back in the wanted order. It copies them from the **live stock file on this machine**, so icons, commands and conditions are always the current ones.
- Everything the helper writes sits between `// >>> omarchy-menu-order: <menu>` and `// <<< omarchy-menu-order: <menu>` marker comments. It never touches anything else in the file. Before every write, it validates the result with the same parsing rules Omarchy uses and keeps a backup at `~/.config/omarchy/extensions/omarchy-menu.jsonc.bak-menu-order`.
- While any menu is reordered, the helper keeps a post-update hook at `~/.config/omarchy/hooks/post-update.d/omarchy-menu-order`. After each `omarchy update`, the hook rebuilds the reordered menus from the new stock file. When nothing is reordered any more, the helper removes the hook again.

## The helper

`scripts/menu_order.py` next to this file (the base directory is shown when the skill loads). Run it with `python3`.

| Command | What it does |
|---|---|
| `show [MENU]` | Read-only: stock order, current order, status, conflicts. MENU defaults to `system`. |
| `set MENU ITEM...` | Write a new order. ITEMs are the short names from `show` (e.g. `lock`). Items you leave out keep their stock order after the ones you list. |
| `reset MENU` / `reset --all` | Remove the managed block, back to the default order. |
| `sync [--all]` | Rebuild from the live stock menu (the update hook runs this). |
| `check` | Exit 1 if a reordered menu is out of date with the stock menu. |
| `list` | Which menus are reordered, and whether the hook is installed. |
| `list-menus` | Every menu id and its items, e.g. `system`, `root` (top level), `trigger`. |

## Steps

1. **Preflight.** If `/usr/share/omarchy` (or `$OMARCHY_PATH`) doesn't exist, this isn't an Omarchy machine: say so and stop. If `python3` is missing, say it's needed and suggest `omarchy pkg add python`. Don't install it yourself.
2. **Look first.** Run `show <menu>`. With no menu named, use `system`. If the user names a menu you can't place, run `list-menus` and pick the matching one, or ask.
3. **Work out the full order** from what the user said and the current order from `show`.
   - Read directions the way the menu looks on screen: "top" is first. "Behind", "after" and "below" mean the next row down, and "before" and "above" mean the next row up.
   - If the request could reasonably mean two different orders, pick the most natural reading, and say in one line which one you picked. It's one command to change.
   - "Reset", "default", "undo", "turn it off" or "put it back" mean `reset`. No request at all, or "status", means: show the current order and stop.
4. **Conflicts.** If `show` lists a CONFLICT (the user already overrides some of this menu's stock items by hand), `set` will refuse. Show the user the conflicting lines from their file, and explain that they'd fight with the new order. Remove them only after the user says yes. They may also need to remove hand-made copies (listed under "Your own items") that would otherwise show up twice. Then run `set`.
5. **Apply.** Run `set <menu> <items in the new order>`.
6. **Report briefly.** Show the new order as a short numbered list. Mention, once, that the menu has already updated (Super + Esc to see it) and that `/omarchy-menu-order reset` puts it back. Also mention the update hook the first time it gets installed.

## Safety: stop and say so instead of doing it

This skill only **reorders existing menu items**. If a request needs any of the following, explain why in a sentence or two, and don't do it:

- Editing anything under `/usr/share/omarchy/`, or using `sudo`/`pkexec`. It's never needed for this.
- Changing what an item does: its command, its `when` condition, or adding a new item with a command. Those run as the user from a menu, so they're a separate, deliberate change, not part of reordering.
- Moving a submenu or a runtime-generated item (`show` marks them "can't move"). A copy would lose its children or its rows.
- Writing the menu file by hand when the helper refuses. Fix what it complains about instead, with the user's agreement.
- Running `omarchy refresh` or restoring the backup over newer changes without asking.
- Triggering a menu item to "test" it (Lock, Logout, Reboot and Shutdown act immediately). Use `show` to verify instead.

If the helper reports an error, show the message in plain words and stop. Don't work around it.
