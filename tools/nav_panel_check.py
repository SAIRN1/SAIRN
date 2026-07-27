import sys, re
from collections import Counter

if __name__ == '__main__':
    path = sys.argv[1]
    with open(path, encoding='utf-8', errors='replace') as f:
        html = f.read()

    fails = []

    # All ids in the document, for duplicate detection.
    all_ids = re.findall(r'\bid="([^"]+)"', html)
    dupes = sorted([i for i, c in Counter(all_ids).items() if c > 1])
    if dupes:
        fails.append(f"DUPLICATE_IDS:{dupes}")

    # Every panel-X div.
    panel_ids = sorted(set(re.findall(r'id="panel-([a-zA-Z0-9_-]+)"', html)))
    print(f"PANEL_COUNT:{len(panel_ids)}")

    # Every sidebar nav button: <button class="sb-btn" ... id="sb-X" ... onclick="sbNav('X')">.
    # Scope strictly to class="sb-btn" tags -- other unrelated chrome (collapse toggle,
    # search box, etc.) also happens to use "sb-" prefixed ids and is not a nav button.
    sb_buttons = re.findall(r'<button[^>]*class="sb-btn[^"]*"[^>]*>', html)
    sb_ids = set()
    nav_targets_from_buttons = set()
    for btn in sb_buttons:
        m_id = re.search(r'id="sb-([a-zA-Z0-9_-]+)"', btn)
        m_nav = re.search(r"sbNav\('([a-zA-Z0-9_-]+)'\)", btn)
        if m_id:
            sb_ids.add(m_id.group(1))
        if m_nav:
            nav_targets_from_buttons.add(m_nav.group(1))
    nav_targets = set(re.findall(r"sbNav\('([a-zA-Z0-9_-]+)'\)", html))

    # Check 17: every sbNav('X') call site has a matching panel-X div.
    orphan_nav_targets = sorted(nav_targets - set(panel_ids))
    if orphan_nav_targets:
        fails.append(f"NAV_TARGETS_WITH_NO_PANEL:{orphan_nav_targets}")

    # Check 16: every panel has a sidebar button (sb-X) wired to it, EXCEPT a small
    # known set that are intentionally reached another way (not sidebar nav items).
    NO_SIDEBAR_BUTTON_OK = {'client'}  # reached via quote flow, not a direct sb- nav button today
    panels_without_sb_button = sorted(p for p in panel_ids if p not in sb_ids and p not in NO_SIDEBAR_BUTTON_OK)
    if panels_without_sb_button:
        fails.append(f"PANELS_WITH_NO_SIDEBAR_BUTTON:{panels_without_sb_button}")

    # sb-X buttons whose id has no matching panel at all (dead nav button).
    sb_ids_without_panel = sorted(sb_ids - set(panel_ids))
    if sb_ids_without_panel:
        fails.append(f"SIDEBAR_BUTTONS_WITH_NO_PANEL:{sb_ids_without_panel}")

    for f in fails:
        print(f"FAIL:{f}")

    if fails:
        print("RESULT:FAIL")
        sys.exit(1)
    else:
        print("RESULT:PASS")
        sys.exit(0)
