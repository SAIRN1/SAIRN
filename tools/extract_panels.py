"""
Reliably extracts the panel/section list from any SAIRN app's single-file HTML.

Built because a real risk was found in this session (STONEDESK-SESSION80-
HANDOFF.md): generating a panel list from memory of "a long night's changes"
is exactly the kind of unverified claim sairn-guardian-v2's Check 0b and
sairn-master-orientation's rule #1 both warn about. This reads the real
markup instead.

Per sairn-master-orientation rule #9 ("scanners built for one app need
portability verification before trusting on another"), this does NOT assume
every app uses the same convention. Checked directly against 5 real app
files before writing this:

  - id="panel-X"  -- the dominant convention (stonedesk.html, sairnbiz.html,
    sairnvet.html, sairndesign.html, sairnlaw.html all use it).
  - id="page-X"   -- a documented SECONDARY system that coexists with
    panel-X in stonedesk.html (see tools/nav_panel_check.py's PAGE_SYSTEM_IDS
    comment) -- a small, separate set of ids shown/hidden by a different
    JS function, not panel-X/showPanel().
  - id="tab-X" / id="view-X" -- sairncash.html uses NEITHER panel- nor
    page- at all. A tool that only looked for "panel-" would have silently
    reported "0 panels" on this file, which reads as "this app has no
    panels" instead of "this app uses a different convention" -- exactly
    the false-negative shape rule #9 warns about. Detected and reported
    explicitly instead of silently missed.

Usage: python tools/extract_panels.py <file.html>
"""
import sys
import re
from collections import Counter


def extract_ids_by_prefix(html, prefix):
    pattern = r'\bid="' + re.escape(prefix) + r'([a-zA-Z0-9_-]+)"'
    return sorted(set(re.findall(pattern, html)))


def find_owning_div_class(html, full_id):
    """Best-effort: look at the <div ...> tag that declares this id and
    report its class attribute, if any, for extra context. Returns None if
    the id isn't on a <div> or has no class attribute -- this is a nicety,
    not something callers should treat as authoritative."""
    m = re.search(r'<div\b([^>]*\bid="' + re.escape(full_id) + r'"[^>]*)>', html)
    if not m:
        return None
    tag_attrs = m.group(1)
    cls = re.search(r'class="([^"]*)"', tag_attrs)
    return cls.group(1) if cls else None


CONVENTIONS = ['panel-', 'page-', 'tab-', 'view-']


def main():
    if len(sys.argv) < 2:
        print("Usage: python tools/extract_panels.py <file.html>")
        sys.exit(2)
    path = sys.argv[1]
    with open(path, encoding='utf-8', errors='replace') as f:
        html = f.read()

    all_ids = re.findall(r'\bid="([^"]+)"', html)
    dupes = sorted(i for i, c in Counter(all_ids).items() if c > 1)

    found_any = False
    print(f"FILE:{path}")
    for prefix in CONVENTIONS:
        names = extract_ids_by_prefix(html, prefix)
        if not names:
            continue
        found_any = True
        print(f"CONVENTION:{prefix}X  COUNT:{len(names)}")
        for name in names:
            full_id = prefix + name
            cls = find_owning_div_class(html, full_id)
            cls_note = f"  class={cls!r}" if cls else ""
            print(f"  {full_id}{cls_note}")

    if not found_any:
        print("WARNING: no ids matched any known convention "
              f"({', '.join(c + 'X' for c in CONVENTIONS)}). "
              "This does NOT mean the app has no panels -- it means this "
              "tool doesn't recognize its convention yet. Do not report "
              "\"0 panels\" as a real finding; inspect the file's actual "
              "nav/section markup and extend CONVENTIONS above.")

    if dupes:
        print(f"DUPLICATE_IDS_IN_FILE:{dupes}")

    print("RESULT:PASS" if found_any else "RESULT:UNKNOWN_CONVENTION")
    sys.exit(0 if found_any else 1)


if __name__ == '__main__':
    main()
