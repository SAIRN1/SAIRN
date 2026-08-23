"""nav_panel_check.py -- panel <-> sidebar reconciliation (Guardian checks 16-18).

REWRITTEN 2026-08-23. The previous version hardcoded StoneDesk's conventions:
sidebar buttons had to carry class="sb-btn", and nav calls had to be sbNav('x').
SAIRNlaw uses class="sb" and nav('x') -- both perfectly valid, neither matched --
so a Guardian pass got RESULT:FAIL listing all 20 SAIRNlaw panels as having no
sidebar button, when the real reconciliation is an exact 20/20. Same false-alarm
class as vercel_config_check.py's buildCommand-glob bug found the same day, and
the same class this file's own removed comment already admitted to once before.

The fix is to stop hardcoding either convention and derive the pair from the
file: a sidebar nav button is a <button> that carries BOTH id="sb-X" AND an
onclick calling whichever nav function that file actually defines. That is what
makes it a nav button in either app, so it needs no per-app configuration.

Duplicate-ID detection is now scoped to STATIC markup (outside <script>), because
counting id="..." across the whole source also counts ids inside JS strings that
build markup. sairnlaw.html's tr-explain-result is written once, then replaced by
outerHTML in one of two mutually exclusive branches -- three source occurrences,
never two live nodes. Those are reported separately as informational, not FAIL.

Usage: python tools/nav_panel_check.py path/to/app.html
"""
import sys, re
from collections import Counter

# StoneDesk-specific allowances. Harmless for other apps (they subtract ids that
# do not exist there); documented rather than silently applied everywhere.
PAGE_SYSTEM_IDS = {'doc-scan', 'check-register', 'field-quote'}
NO_SIDEBAR_BUTTON_OK = {'client'}


def resolve_panel(arg, panel_ids):
    """Map a nav argument onto a real panel id, whatever prefix either uses.

    Four live conventions, all correct, none guessable in advance:
        nav('trust')            -> id="panel-trust"        (SAIRNlaw)
        sbNav('slabs')          -> id="panel-slabs"        (StoneDesk)
        svNav('panel-soap')     -> id="panel-soap"         (SAIRNvet, arg carries the prefix)
        scpNav('design')        -> id="scp-panel-design"   (SAIRNscape, app-specific prefix)

    Matching on any of these rather than one hardcoded shape is the whole
    point; the previous versions of this script each assumed one and reported
    every other app's panels as unreachable."""
    if arg in panel_ids:
        return arg
    for pid in panel_ids:
        if pid.endswith('-' + arg) or pid == arg:
            return pid
        if arg.endswith('-' + pid) or arg.startswith('panel-') and arg[len('panel-'):] == pid:
            return pid
    return None


def detect_panels(html):
    """Every panel div, and the prefix its ids use.

    Also derived rather than assumed: most apps use id="panel-x", but
    SAIRNscape and SAIRNcash mark panels with class="panel" and a bare id.
    Hardcoding the panel- prefix reported both as having ZERO panels, which
    then made every one of their nav buttons look dead."""
    prefixed = set(re.findall(r'id="panel-([a-zA-Z0-9_-]+)"', html))
    # UNION, not either/or. SAIRNvet uses BOTH conventions in one file: 81
    # panels as id="panel-x", and dashboard/billing/reports/settings as bare
    # id="x" on class="panel". Returning early on the prefixed set reported
    # those four nav buttons as pointing at nothing -- four "dead button"
    # findings against buttons that work.
    # Which class token marks a panel in THIS file? Also derived. Candidates
    # are tokens equal to 'panel' or ending in '-panel', and the winner is
    # simply the most common one:
    #
    #   StoneDesk    panel (62)  vs  q-tab-panel (6)   -> panel
    #   SAIRNscape   scp-panel (11)                    -> scp-panel
    #
    # Neither a substring match nor an exact-'panel' match works for both. A
    # \bpanel\b regex swept in StoneDesk's 6 tab sub-panels (biztab-*, dim-*)
    # and reported them unreachable; requiring the exact token 'panel' instead
    # dropped ALL of SAIRNscape's panels and turned its FAIL into a vacuous
    # PASS -- which is the worse of the two errors, so it is worth deriving
    # rather than picking a side.
    tag_tokens = []
    for tag in re.findall(r'<div\b[^>]*>', html):
        m_cls = re.search(r'class="([^"]*)"', tag)
        if not m_cls:
            continue
        toks = [t for t in m_cls.group(1).split() if t == 'panel' or t.endswith('-panel')]
        if toks:
            tag_tokens.append((toks, tag))
    counts = Counter(t for toks, _ in tag_tokens for t in toks)
    panel_token = counts.most_common(1)[0][0] if counts else 'panel'

    bare = set()
    for toks, tag in tag_tokens:
        if panel_token not in toks:
            continue
        m = re.search(r'id="([a-zA-Z0-9_-]+)"', tag)
        if m:
            name = m.group(1)
            bare.add(name[len('panel-'):] if name.startswith('panel-') else name)
    both = prefixed | bare
    return sorted(both), 'panel-' if prefixed else ''


def detect_nav_fn(html, panel_ids):
    """Which nav function does this file actually use?

    Derived, never hardcoded. Three real conventions exist in this repo and a
    fourth is only a matter of time:

        StoneDesk  <button class="sb-btn"    id="sb-x" onclick="sbNav('x')">
        SAIRNlaw   <button class="sb"        id="sb-x" onclick="nav('x')">
        SAIRNvet   <button class="sidebar-btn"         onclick="svNav('panel-x')">

    Note SAIRNvet has no id at all and passes the panel- prefix inside the
    argument. Every previous version of this script assumed one shape and
    reported the other apps as broken.

    Scoring is by how many of a candidate's string-literal arguments actually
    name a real panel -- NOT by call count. Call count picks toggleNav /
    closeNav / isMobileNav, which are sidebar-chrome helpers that merely end in
    "Nav" and are called constantly; that mistake reported 9 of 12 apps as
    fully unreachable. A function whose arguments are panel names is the nav
    function, whatever it happens to be called."""
    # Candidates are NOT filtered by name. Restricting to names containing
    # "nav" looked safe and was wrong twice over: it cannot match the bare name
    # "nav" (SAIRNlaw resolved to closeNav, all 20 panels reported unreachable),
    # and SAIRNcode's nav function is called showPanel() with no "nav" in it at
    # all (37 panels reported unreachable). Five conventions across twelve apps
    # is enough evidence that the name is not a reliable signal.
    #
    # The reliable signal is behavioural: whichever function is called from an
    # onclick with a string argument that names a real panel IS the nav
    # function, regardless of what anyone called it.
    candidates = set(re.findall(r'onclick="([A-Za-z_$][A-Za-z0-9_$]*)\(\s*[\'"]', html))
    if not candidates:
        return 'nav'

    def score(name):
        return sum(1 for a in nav_call_re(name).findall(html) if resolve_panel(a, panel_ids))

    best = max(candidates, key=lambda n: (score(n), len(nav_call_re(n).findall(html))))
    return best if score(best) else 'nav'


def nav_call_re(fn):
    """Match fn('x') but never a call whose name merely ENDS with fn -- without
    the lookbehind, sbNav('x') also matches a bare nav( pattern and inflates
    every count in a StoneDesk-shaped file."""
    return re.compile(r"(?<![A-Za-z0-9_$])" + fn + r"\('([a-zA-Z0-9_-]+)'\)")


if __name__ == '__main__':
    path = sys.argv[1]
    with open(path, encoding='utf-8', errors='replace') as f:
        html = f.read()

    fails = []

    panel_ids, panel_prefix = detect_panels(html)
    nav_fn = detect_nav_fn(html, panel_ids)
    call_re = nav_call_re(nav_fn)
    print(f"DETECTED_NAV_FN:{nav_fn}")
    print(f"DETECTED_PANEL_PREFIX:{panel_prefix or '(none, bare ids on class=panel)'}")

    # ── duplicate ids, static markup only ────────────────────────────────────
    static = re.sub(r'<script\b.*?</script>', '', html, flags=re.S | re.I)
    static_ids = re.findall(r'\bid="([^"]+)"', static)
    dupes = sorted([i for i, c in Counter(static_ids).items() if c > 1])
    print(f"STATIC_IDS:{len(static_ids)}")
    if dupes:
        fails.append(f"DUPLICATE_IDS:{dupes}")

    script_only = Counter(re.findall(r'\bid="([^"]+)"', html))
    for i in static_ids:
        script_only[i] -= 1
    js_repeat = sorted([i for i, c in script_only.items() if c > 1])
    if js_repeat:
        print(f"INFO:IDS_EMITTED_MORE_THAN_ONCE_FROM_JS:{js_repeat}"
              f" (not a duplicate unless two are live at once -- verify by reading)")

    # ── panels (detected above, before nav-fn scoring needed them) ───────────
    print(f"PANEL_COUNT:{len(panel_ids)}")

    # ── sidebar nav buttons ──────────────────────────────────────────────────
    # A nav button is a <button> whose onclick calls the nav function. An
    # id="sb-X" is checked when present but NOT required -- SAIRNvet's buttons
    # carry no id, and demanding one reported all 81 of its panels unreachable.
    # The nav argument may or may not already carry the panel- prefix
    # (nav('trust') vs svNav('panel-trust')), so both are normalised to a bare
    # panel key before anything is compared.
    buttons_with_nav, sb_id_pairs, wired, unresolved = 0, [], set(), set()
    for btn in re.findall(r'<button\b[^>]*>', html):
        m_nav = call_re.search(btn)
        if not m_nav:
            continue
        buttons_with_nav += 1
        raw = m_nav.group(1)
        target = resolve_panel(raw, panel_ids)
        if target:
            wired.add(target)
        else:
            unresolved.add(raw)
        m_id = re.search(r'id="sb-([a-zA-Z0-9_-]+)"', btn)
        if m_id and target:
            sb_id_pairs.append((m_id.group(1), target))
    sb_ids = {i for i, _ in sb_id_pairs}
    print(f"SIDEBAR_NAV_BUTTONS:{buttons_with_nav}")
    print(f"SIDEBAR_BUTTONS_CARRYING_AN_ID:{len(sb_ids)}")

    # Only meaningful where ids exist; a mismatch means the button is labelled
    # for one panel and actually navigates to another.
    mismatched = sorted(f'{i}->{t}' for i, t in sb_id_pairs
                        if resolve_panel(i, panel_ids) != t)
    if mismatched:
        fails.append(f"SB_BUTTON_ID_DOES_NOT_MATCH_ITS_NAV_TARGET:{mismatched}")

    # Check 17: every nav('X') call site resolves to a real panel div.
    #
    # Scoped to onclick= attributes ONLY -- real wiring. Scanning the whole
    # file also matches the function name inside PROSE: SAIRNcode has a comment
    # reading `Every button's onclick is exactly showPanel('name')`, which was
    # duly reported as a nav target with no panel. Stripping comments first is
    # the obvious alternative and the wrong one; a naive comment regex blanks
    # strings and URLs too, which is the documented cause of 58 phantom
    # findings in sairn_dead_button_audit.py. Narrowing the scan is safer than
    # widening the parse.
    onclick_targets = set()
    for attr in re.findall(r'onclick="([^"]*)"', html):
        onclick_targets.update(call_re.findall(attr))
    orphan = sorted(a for a in onclick_targets
                    if not resolve_panel(a, panel_ids) and a not in PAGE_SYSTEM_IDS)
    if orphan:
        fails.append(f"NAV_TARGETS_WITH_NO_PANEL:{orphan}")

    # Check 16: every panel is reachable -- some nav button navigates to it.
    # Reachability is what matters; whether the button also carries a matching
    # id is a separate, weaker signal already reported above.
    #
    # SUB-CONTAINERS are excluded: SAIRNvet has 40 ids like panel-soap-table
    # sitting INSIDE panel-soap, rendered by their parent and never a nav
    # destination (confirmed: zero svNav calls target any of them). Counting
    # them produced 40 "unreachable panel" findings that were all wrong. A
    # panel whose id is <parent>-<suffix> where <parent> is itself a panel is
    # a child of it, not an orphan.
    def is_sub_container(pid):
        return any(pid != other and pid.startswith(other + '-') for other in panel_ids)

    subs = sorted(p for p in panel_ids if p not in wired and is_sub_container(p))
    no_button = sorted(p for p in panel_ids
                       if p not in wired and p not in NO_SIDEBAR_BUTTON_OK and not is_sub_container(p))
    if subs:
        print(f"INFO:SUB_CONTAINERS_NOT_NAV_TARGETS:{len(subs)} "
              f"(e.g. {subs[:3]}) -- nested inside a parent panel, not orphans")
    if no_button:
        fails.append(f"PANELS_WITH_NO_NAV_BUTTON:{no_button}")

    # A nav button pointing at no panel at all (dead nav button).
    dead = sorted(unresolved - PAGE_SYSTEM_IDS)
    if dead:
        fails.append(f"NAV_BUTTONS_WITH_NO_PANEL:{dead}")

    if not panel_ids:
        print("INFO:NO_PANELS_FOUND -- this app may use a different container "
              "convention entirely (e.g. showPage/class=page). Reconciliation "
              "is vacuous here; confirm by hand before reading PASS as coverage.")

    for f in fails:
        print(f"FAIL:{f}")

    print("RESULT:FAIL" if fails else "RESULT:PASS")
    sys.exit(1 if fails else 0)
