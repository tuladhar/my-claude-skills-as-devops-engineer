#!/usr/bin/env python3
"""Reorder items in an Omarchy menu, safely and reversibly.

Omarchy merges ~/.config/omarchy/extensions/omarchy-menu.jsonc into the stock
menu by id. An override keeps the stock item's position, so items can't be
moved by overriding them. This helper hides the stock items of one submenu
("when": "false") and re-adds copies in the wanted order, read from the live
stock menu every time. Everything it writes sits between marker comments, so
it can always be found, rebuilt (sync) or removed (reset) without touching
anything else in the file.

Commands:
  show  [MENU]           stock order, current order, and status (read-only)
  set   MENU ITEM...     write a new order (items by their last id part, e.g. lock)
  reset MENU | --all     remove the managed block(s), back to the default order
  sync  [--all] [MENU]   rebuild managed block(s) from the live stock menu
  check                  exit 1 if a managed block is out of date with the stock menu
  list                   list the menus this helper manages

MENU is a menu id such as "system", or "root" for the top-level menu.
"""

import json
import os
import re
import shutil
import sys
import tempfile

OMARCHY_PATH = os.environ.get("OMARCHY_PATH") or "/usr/share/omarchy"
STOCK_FILE = os.path.join(OMARCHY_PATH, "default/omarchy/omarchy-menu.jsonc")
USER_FILE = os.path.expanduser("~/.config/omarchy/extensions/omarchy-menu.jsonc")
BACKUP_FILE = USER_FILE + ".bak-menu-order"
HOOK_FILE = os.path.expanduser("~/.config/omarchy/hooks/post-update.d/omarchy-menu-order")
ID_INFIX = "order-"

BEGIN = "  // >>> omarchy-menu-order: {menu} (managed block, change it with /omarchy-menu-order)"
ORDER = "  // order: {order}"
END = "  // <<< omarchy-menu-order: {menu}"
BEGIN_RE = re.compile(r"^\s*// >>> omarchy-menu-order: (\S+)")
ORDER_RE = re.compile(r"^\s*// order: (.*)$")
END_RE = re.compile(r"^\s*// <<< omarchy-menu-order: (\S+)")


class Fail(Exception):
    pass


# --- Reading menus, the same way Omarchy's MenuModel.js does -----------------

def strip_jsonc(raw):
    """Mirror MenuModel.stripJsonc: drop full-line // comments and trailing commas."""
    text = re.sub(r"^\s*//[^\n]*(\n|$)", "", raw, flags=re.M)
    return re.sub(r",(\s*[}\]])", r"\1", text)


def parse_menu(raw, path):
    text = strip_jsonc(raw)
    if not text.strip():
        return {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise Fail(f"{path} is not valid menu JSONC ({e}). Fix it by hand first; nothing was changed.")
    if not isinstance(data, dict):
        raise Fail(f"{path} is not a menu object; nothing was changed.")
    if isinstance(data.get("items"), dict):
        data = data["items"]
    return {k: v for k, v in data.items() if isinstance(v, dict)}


def parent_of(item_id, entry):
    if "parent" in entry:
        return entry["parent"]
    return item_id.rsplit(".", 1)[0] if "." in item_id else "root"


def leaf(item_id):
    return item_id.rsplit(".", 1)[-1]


def read_stock():
    if not os.path.isfile(STOCK_FILE):
        raise Fail(f"Stock menu not found at {STOCK_FILE}. Is this an Omarchy system?")
    with open(STOCK_FILE, encoding="utf-8") as f:
        return parse_menu(f.read(), STOCK_FILE)


def read_user_text():
    if not os.path.isfile(USER_FILE):
        return "{\n}\n"
    with open(USER_FILE, encoding="utf-8") as f:
        return f.read()


# --- Managed blocks ------------------------------------------------------------

def find_blocks(text):
    """Return {menu: (start_line, end_line, order_list)} for every managed block."""
    lines = text.split("\n")
    blocks, open_menu, start, order = {}, None, None, []
    for i, line in enumerate(lines):
        m = BEGIN_RE.match(line)
        if m:
            if open_menu:
                raise Fail(f"Managed block for '{open_menu}' is not closed in {USER_FILE}.")
            open_menu, start, order = m.group(1), i, []
            continue
        m = ORDER_RE.match(line)
        if m and open_menu:
            order = [s.strip() for s in m.group(1).split(",") if s.strip()]
            continue
        m = END_RE.match(line)
        if m:
            if m.group(1) != open_menu:
                raise Fail(f"Managed block markers don't match in {USER_FILE}.")
            blocks[open_menu] = (start, i, order)
            open_menu = None
    if open_menu:
        raise Fail(f"Managed block for '{open_menu}' is not closed in {USER_FILE}.")
    return blocks


def without_blocks(text, menus):
    blocks = find_blocks(text)
    lines = text.split("\n")
    drop = set()
    for menu in menus:
        if menu in blocks:
            s, e, _ = blocks[menu]
            drop.update(range(s, e + 1))
            if s > 0 and not lines[s - 1].strip():
                drop.add(s - 1)
    return "\n".join(l for i, l in enumerate(lines) if i not in drop)


def movable_items(stock, menu):
    """Stock items directly under MENU, in stock order, with what blocks moving them."""
    children = [i for i, e in stock.items() if parent_of(i, e) == menu]
    has_children = {parent_of(i, e) for i, e in stock.items()}
    out = []
    for item_id in children:
        e = stock[item_id]
        reason = None
        if item_id in has_children:
            reason = "it is a submenu with its own items"
        elif e.get("provider"):
            reason = "its rows are generated at runtime"
        elif not (e.get("action") or e.get("target")):
            reason = "it has no action"
        out.append((item_id, reason))
    return out


def build_block(stock, menu, order):
    items = movable_items(stock, menu)
    by_leaf = {leaf(i): i for i, r in items if r is None}
    final = [l for l in order if l in by_leaf]
    final += [l for l in by_leaf if l not in final]  # new stock items keep their place at the end
    lines = [BEGIN.format(menu=menu), ORDER.format(order=", ".join(final))]
    for l in by_leaf:  # hide stock rows, in stock order
        lines.append(f'  {json.dumps(by_leaf[l])}: {{"when":"false","aliases":[]}},')
    for l in final:  # re-add copies, in the wanted order
        entry = dict(stock[by_leaf[l]])
        entry["parent"] = menu
        new_id = f"{menu}.{ID_INFIX}{l}" if menu != "root" else f"{ID_INFIX}{l}"
        lines.append(f"  {json.dumps(new_id)}: {json.dumps(entry, ensure_ascii=False, separators=(',', ':'))},")
    lines.append(END.format(menu=menu))
    return "\n".join(lines), final


def insert_block(text, block):
    idx = text.rstrip().rfind("}")
    if idx < 0:
        raise Fail(f"Could not find the closing }} of {USER_FILE}; nothing was changed.")
    lines = text[:idx].rstrip().split("\n")
    # The last real entry needs a trailing comma before our block (comment lines don't count).
    last = next((n for n in range(len(lines) - 1, -1, -1)
                 if lines[n].strip() and not lines[n].lstrip().startswith("//")), None)
    if last is None:
        raise Fail(f"Could not read {USER_FILE}; nothing was changed.")
    if lines[last].rstrip().endswith("{"):
        sep = "\n"
    else:
        if not lines[last].rstrip().endswith(","):
            lines[last] = lines[last].rstrip() + ","
        sep = "\n\n"
    return "\n".join(lines) + sep + block + "\n" + text[idx:]


def foreign_overrides(text, stock, menu):
    """Stock ids of MENU that the user overrides outside any managed block."""
    user = parse_menu(without_blocks(text, find_blocks(text).keys()), USER_FILE)
    ids = {i for i, _ in movable_items(stock, menu)}
    return sorted(i for i in user if i in ids)


def own_items(text, stock, menu):
    """Items the user added to MENU themselves (outside managed blocks)."""
    user = parse_menu(without_blocks(text, find_blocks(text).keys()), USER_FILE)
    return [i for i, e in user.items() if i not in stock and parent_of(i, e) == menu]


def write_user(new_text):
    parse_menu(new_text, USER_FILE + " (new version)")  # must still load in Omarchy, or we don't write
    os.makedirs(os.path.dirname(USER_FILE), exist_ok=True)
    if os.path.isfile(USER_FILE):
        shutil.copy2(USER_FILE, BACKUP_FILE)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(USER_FILE), prefix=".omarchy-menu.")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(new_text)
    if os.path.isfile(USER_FILE):
        shutil.copymode(USER_FILE, tmp)
    os.replace(tmp, USER_FILE)


# --- Update hook ---------------------------------------------------------------

def sync_hook(text):
    want = bool(find_blocks(text))
    if want and not os.path.isfile(HOOK_FILE):
        os.makedirs(os.path.dirname(HOOK_FILE), exist_ok=True)
        script = os.path.realpath(__file__)
        with open(HOOK_FILE, "w") as f:
            f.write("#!/bin/bash\n"
                    "# Installed by the omarchy-menu-order Claude skill.\n"
                    "# After each Omarchy update, rebuild reordered menus from the new stock menu.\n"
                    f'H="{script}"\n'
                    '[ -f "$H" ] && command -v python3 >/dev/null && python3 "$H" sync --all --quiet || true\n')
        os.chmod(HOOK_FILE, 0o755)
        return "installed"
    if not want and os.path.isfile(HOOK_FILE):
        os.remove(HOOK_FILE)
        return "removed"
    return None


# --- Commands ------------------------------------------------------------------

def effective_order(stock, text, menu):
    user = parse_menu(text, USER_FILE)
    merged, order = {}, []
    for src in (stock, user):
        for i, e in src.items():
            if i not in merged:
                order.append(i)
            merged[i] = {**merged.get(i, {}), **e}
    rows = []
    for i in order:
        e = merged[i]
        if parent_of(i, e) != menu or e.get("when") == "false":
            continue
        rows.append((i, e.get("label", i), e.get("when", "")))
    return rows


def cmd_show(menu):
    stock, text = read_stock(), read_user_text()
    items = movable_items(stock, menu)
    if not items:
        raise Fail(f"No menu '{menu}' in the stock menu. Run 'list-menus' to see the menu ids.")
    blocks = find_blocks(text)
    print(f"Menu: {menu}")
    print("Stock order:")
    for i, reason in items:
        note = f"  (can't move: {reason})" if reason else ""
        when = f"  [shown only when: {stock[i]['when']}]" if stock[i].get("when") else ""
        print(f"  {leaf(i):<14} {stock[i].get('label', i)}{when}{note}")
    print("Current order (what the menu shows, conditional rows included):")
    for i, label, when in effective_order(stock, text, menu):
        print(f"  {leaf(i).removeprefix(ID_INFIX):<14} {label}" + ("  [conditional]" if when else ""))
    if menu in blocks:
        block, _ = build_block(stock, menu, blocks[menu][2])
        s, e, _ = blocks[menu]
        current = "\n".join(text.split("\n")[s:e + 1])
        print("Status: reordered by this skill" + ("" if current == block else " -- OUT OF DATE with the stock menu, run sync"))
    else:
        print("Status: default order (not managed by this skill)")
    clash = foreign_overrides(text, stock, menu)
    if clash:
        print("CONFLICT - stock items overridden elsewhere in your menu file (set will refuse until they're removed):")
        for i in clash:
            print(f"  {i}")
    own = own_items(text, stock, menu)
    if own:
        print("Your own items in this menu (left alone; they show before the reordered stock items):")
        for i in own:
            print(f"  {i}")


def cmd_set(menu, wanted):
    stock, text = read_stock(), read_user_text()
    items = movable_items(stock, menu)
    if not items:
        raise Fail(f"No menu '{menu}' in the stock menu.")
    movable = {leaf(i): r for i, r in items}
    for w in wanted:
        if w not in movable:
            raise Fail(f"'{w}' is not an item of '{menu}'. Items: {', '.join(movable)}")
        if movable[w]:
            raise Fail(f"'{w}' can't be moved: {movable[w]}.")
    if len(set(wanted)) != len(wanted):
        raise Fail("An item is listed twice.")
    clash = foreign_overrides(text, stock, menu)
    if clash:
        raise Fail("These stock items are already overridden elsewhere in your menu file: "
                   + ", ".join(clash)
                   + ". They would fight with the new order. Remove them (or let Claude do it after you agree), then run again.")
    block, final = build_block(stock, menu, wanted)
    new_text = insert_block(without_blocks(text, [menu]), block)
    write_user(new_text)
    hook = sync_hook(new_text)
    print(f"New order for {menu}: {', '.join(final)}")
    print(f"Backup of the previous file: {BACKUP_FILE}")
    if hook:
        print(f"Update hook {hook}: {HOOK_FILE}")


def cmd_reset(menus):
    text = read_user_text()
    blocks = find_blocks(text)
    if menus == ["--all"]:
        menus = list(blocks)
    missing = [m for m in menus if m not in blocks]
    if missing and not [m for m in menus if m in blocks]:
        print(f"Nothing to reset: {', '.join(missing)} is not reordered by this skill.")
        return
    new_text = without_blocks(text, menus)
    write_user(new_text)
    hook = sync_hook(new_text)
    print(f"Back to the default order: {', '.join(m for m in menus if m in blocks)}")
    print(f"Backup of the previous file: {BACKUP_FILE}")
    if hook:
        print(f"Update hook {hook}: {HOOK_FILE}")


def cmd_sync(menus, quiet=False):
    stock, text = read_stock(), read_user_text()
    blocks = find_blocks(text)
    if menus == ["--all"]:
        menus = list(blocks)
    new_text, changed = text, []
    for menu in menus:
        if menu not in blocks:
            continue
        s, e, order = find_blocks(new_text)[menu]
        block, _ = build_block(stock, menu, order)
        lines = new_text.split("\n")
        if "\n".join(lines[s:e + 1]) != block:
            new_text = "\n".join(lines[:s] + block.split("\n") + lines[e + 1:])
            changed.append(menu)
    if changed:
        write_user(new_text)
    sync_hook(new_text)
    if not quiet or changed:
        print("Updated from the stock menu: " + ", ".join(changed) if changed else "Everything is up to date.")


def cmd_check():
    stock, text = read_stock(), read_user_text()
    stale = []
    for menu, (s, e, order) in find_blocks(text).items():
        block, _ = build_block(stock, menu, order)
        if "\n".join(text.split("\n")[s:e + 1]) != block:
            stale.append(menu)
    if stale:
        print("Out of date: " + ", ".join(stale))
        sys.exit(1)
    print("Everything is up to date.")


def cmd_list():
    blocks = find_blocks(read_user_text())
    print("Reordered by this skill: " + (", ".join(f"{m} ({', '.join(o)})" for m, (_, _, o) in blocks.items()) or "none"))
    print(f"Update hook: {'installed' if os.path.isfile(HOOK_FILE) else 'not installed'}")


def cmd_list_menus():
    stock = read_stock()
    parents = {}
    for i, e in stock.items():
        parents.setdefault(parent_of(i, e), []).append(leaf(i))
    for p, kids in parents.items():
        if p:
            label = stock.get(p, {}).get("label", "Top level" if p == "root" else p)
            print(f"  {p:<28} {label}: {', '.join(kids)}")


def main(argv):
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(__doc__.strip())
        return
    cmd, args = argv[0], argv[1:]
    quiet = "--quiet" in args
    args = [a for a in args if a != "--quiet"]
    if cmd == "show":
        cmd_show(args[0] if args else "system")
    elif cmd == "set":
        if len(args) < 2:
            raise Fail("Usage: set MENU ITEM [ITEM...]")
        cmd_set(args[0], args[1:])
    elif cmd == "reset":
        cmd_reset(args or ["system"])
    elif cmd == "sync":
        cmd_sync(["--all"] if not args or args == ["--all"] else args, quiet)
    elif cmd == "check":
        cmd_check()
    elif cmd == "list":
        cmd_list()
    elif cmd == "list-menus":
        cmd_list_menus()
    else:
        raise Fail(f"Unknown command '{cmd}'. Run with --help.")


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except Fail as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)
