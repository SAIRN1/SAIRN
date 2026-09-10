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
# Every entry is a KNOWN, RECORDED finding that is suppressed on purpose, and
# each one is PRINTED on every run rather than silently subtracted -- the same
# rule tools/reachability_exemptions.json holds itself to. An entry that stops
# matching anything is dead weight; an entry nobody can see is a hidden defect.
NO_SIDEBAR_BUTTON_OK = {
    'client': 'StoneDesk: reached from the client list, not the sidebar',
    # Found 2026-09-10 by the first run of this tool that could see `page-`
    # containers at all. It is REAL and it is already recorded: sairnmechanical
    # names it in its own source -- "page-sairnbiz-connector, which has NO nav
    # item and no showPage() caller anywhere -- an unreachable panel, reported
    # separately and deliberately not deleted here" -- and its three buttons
    # were wired anyway so the defect cannot ship the day somebody adds the
    # missing nav row. Suppressed so a standing, known finding does not fire on
    # every push and teach people to ignore this checker; DELETE THIS LINE the
    # moment the connector is either wired or removed.
    'sairnbiz-connector': 'SAIRNmechanical: quarantined dormant panel, '
                          'recorded in the app source and the open-work index',
}


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
        # camelCase suffix: SAIRNcash's showPage('home') switches id="homePage".
        # A fifth live convention, and the reason this function derives rather
        # than assumes -- each one of them is somebody's perfectly ordinary
        # naming choice, and every version of this file that picked a side
        # reported a working app as broken.
        if pid == arg + 'Page' or pid == arg + 'Panel':
            return pid
    return None


def detect_panels(html):
    """Every panel div, and the prefix its ids use.

    Also derived rather than assumed: most apps use id="panel-x", but
    SAIRNscape and SAIRNcash mark panels with class="panel" and a bare id.
    Hardcoding the panel- prefix reported both as having ZERO panels, which
    then made every one of their nav buttons look dead."""
    # ── `page-` IS THE FIFTH HARDCODED ASSUMPTION, REMOVED 2026-09-10 ───────
    # SAIRNmechanical marks its containers id="page-x" on class="page" and
    # navigates with showPage('x') -- 17 real pages, 24 call sites. This file
    # matched only `panel`, found ZERO containers, and printed **RESULT:PASS**.
    # That is the dangerous direction of the same bug this file has now
    # corrected five times: the class, the id, the nav-function name and the
    # element all failed LOUD, reporting a working app as broken. This one
    # failed SILENT, reporting an app it had not looked at as clean -- and the
    # report-only registry then counted it as a passing checker.
    #
    # It matters beyond the count: `page-sairnbiz-connector` is an unreachable
    # container that sairnmechanical's own source calls out by name, and this
    # tool is the thing meant to find that class. It could not see the panel
    # system at all.
    prefixed = set(re.findall(r'id="panel-([a-zA-Z0-9_-]+)"', html))
    # ADOPTED ONLY IF THE APP NAVIGATES TO THEM. Taking every `page-` id was
    # the first attempt and it broke three apps at once, because `page` marks
    # two different things: a nav-switched panel (SAIRNmechanical) and an app
    # SHELL container (SAIRNcash's homePage/appPage, StoneDesk's doc-scan /
    # check-register / field-quote page system, which this file already keeps
    # an allowance list for). Counting shells as panels reported StoneDesk's
    # `field-quote` and SAIRNcash's `homePage` as unreachable -- two working
    # apps, exactly the false-alarm class this file exists to have stopped
    # making. So the test is behavioural rather than nominal: a container is a
    # panel if something CALLS it by name. Two or more, so one incidental
    # string cannot adopt a whole convention.
    # THE CONVENTION IS ADOPTED, NOT THE ADDRESSED MEMBERS. The first version
    # took only the ids something calls by name, and that is self-defeating:
    # an UNREACHABLE container is by definition one nothing calls, so filtering
    # to addressed ids guarantees the tool can never report the finding it
    # exists for. It made SAIRNmechanical pass with 16 panels by dropping the
    # seventeenth -- `page-sairnbiz-connector`, the one that is actually
    # unreachable and that the app's own source names.
    #
    # So the ≥2 test decides whether THIS FILE navigates by `page-` at all, and
    # if it does, every `page-` container is in scope.
    page_ids = set(re.findall(r'id="page-([a-zA-Z0-9_-]+)"', html))
    addressed = {n for n in page_ids
                 if re.search(r'\w+\(\s*[\'"]%s[\'"]' % re.escape(n), html)}
    if len(addressed) >= 2:
        prefixed |= page_ids
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
        # `page` is here alongside `panel` for SAIRNcash, whose two containers
        # are class="page" with id="homePage"/"appPage" and showPage('home').
        # It is safe here and was NOT safe in the id branch, and the difference
        # is worth stating: an id prefix is a naming habit, but a CLASS token
        # is what the app's own CSS and its showPage() both key on, so a
        # class="page" element really is one of the things being switched.
        toks = [t for t in m_cls.group(1).split()
                if t in ('panel', 'page') or t.endswith(('-panel', '-page'))]
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
            for p in ('panel-', 'page-'):
                if name.startswith(p):
                    name = name[len(p):]
                    break
            bare.add(name)
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
    # ── TRAILING ARGUMENTS, added 2026-09-10 ────────────────────────────────
    # This required the closing paren IMMEDIATELY after the quoted argument, so
    # a nav function that takes anything else was invisible. `stonedesk-hr.html`
    # navigates with `showPage('dashboard', this)` from fifteen
    # `<div class="sidebar-item">` controls, and this tool saw ZERO of them:
    # it fell back to the default `nav`, matched nothing, and reported all
    # fifteen pages unreachable on an app whose sidebar works.
    #
    # It surfaced only because adopting the `page-` convention made those
    # containers visible at all -- before that the file had 0 panels and
    # reported a vacuous PASS, so the defect was invisible behind another one.
    # That is the sixth hardcoded assumption in this file and the second found
    # in a day.
    return re.compile(r"(?<![A-Za-z0-9_$])" + fn +
                      r"\(\s*'([a-zA-Z0-9_-]+)'\s*(?:,[^)]*)?\)")


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

    # ── sidebar nav controls ─────────────────────────────────────────────────
    # A nav control is ANY element whose onclick calls the nav function. An
    # id="sb-X" is checked when present but NOT required -- SAIRNvet's buttons
    # carry no id, and demanding one reported all 81 of its panels unreachable.
    # The nav argument may or may not already carry the panel- prefix
    # (nav('trust') vs svNav('panel-trust')), so both are normalised to a bare
    # panel key before anything is compared.
    #
    # ── THE ELEMENT IS DERIVED TOO, AS OF 2026-09-09 ────────────────────────
    # This scanned `<button>` only, and that is the FOURTH instance of this
    # file's own recurring bug -- it has already stopped hardcoding the class
    # (`sb-btn`), the id (`sb-X`) and the function name, each time after
    # reporting a whole working app as unreachable. The element was the last
    # hardcoded assumption left.
    #
    # FOUND ON ITS FIRST REAL RUN, 2026-09-09, in the report-only promotion
    # pass: sairnfreedom.html came back RESULT:FAIL with all 26 panels listed
    # as having no nav button and SIDEBAR_NAV_BUTTONS:0, because its sidebar is
    #     <div class="nitem" id="nav-members" onclick="sfNav('members')">
    # Every panel is wired. Promoted blocking as it stood, it would have
    # refused every SAIRNfreedom push while the app was fine -- which is
    # exactly why the promotion path is report-only first.
    #
    # ACCEPTED WIDENING, STATED RATHER THAN QUIET: this counts a nav call on
    # any element anywhere in the file, including one inside a panel (a "back
    # to dashboard" link) and one inside a JS template string. So a panel
    # reachable ONLY from deep inside another panel now counts as wired. That
    # looseness already existed for <button> -- nothing ever checked that the
    # button was in the sidebar -- so this widens the element set, not the
    # rule. The tag breakdown is printed so a reader can see what matched
    # instead of taking the count on trust.
    #
    # The output key changed from SIDEBAR_NAV_BUTTONS to SIDEBAR_NAV_CONTROLS
    # because a key named BUTTONS counting <div>s is the quiet kind of wrong
    # this file keeps correcting itself about.
    controls_with_nav, sb_id_pairs, wired, unresolved = 0, [], set(), set()
    tags = Counter()
    # THE TAG PATTERN IS TIGHT FOR A MEASURED REASON, not a guessed one. The
    # first version was `<([a-zA-Z][\w-]*)\b[^>]*>` and it matched the JS
    # comparison `if(days<TRIAL_DAYS)return true;` as an opening tag, then ran
    # `[^>]*` across a dozen lines until it found a `>`, swallowing a real nav
    # call and counting a phantom control on sairnvet and sairnlegacy.
    #   * an HTML tag name cannot contain `_`, so [a-zA-Z0-9-] excludes it;
    #   * the name must be followed by whitespace, `/` or `>`;
    #   * a tag body cannot contain `<` or span a newline here.
    # Checked both patterns over all 22 app files: the tight one loses exactly
    # those two phantoms and NOT ONE real control anywhere. That comparison is
    # the evidence -- a tightening nobody measures is how a false alarm becomes
    # a silent miss.
    for m_el in re.finditer(r'<([a-zA-Z][a-zA-Z0-9-]*)(?=[\s/>])[^<>\n]*>', html):
        el = m_el.group(0)
        m_nav = call_re.search(el)
        if not m_nav:
            continue
        controls_with_nav += 1
        tags[m_el.group(1).lower()] += 1
        raw = m_nav.group(1)
        target = resolve_panel(raw, panel_ids)
        if target:
            wired.add(target)
        else:
            unresolved.add(raw)
        m_id = re.search(r'id="sb-([a-zA-Z0-9_-]+)"', el)
        if m_id and target:
            sb_id_pairs.append((m_id.group(1), target))
    sb_ids = {i for i, _ in sb_id_pairs}
    print(f"SIDEBAR_NAV_CONTROLS:{controls_with_nav}")
    print(f"NAV_CONTROL_TAGS:{dict(sorted(tags.items()))}")
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
    # PAGE_SYSTEM_IDS is subtracted from BOTH sides as of 2026-09-10. It was
    # only ever taken off `unresolved` (a nav call with no panel), which was
    # enough while `page-` containers were invisible to this tool. Adopting the
    # `page-` convention brought StoneDesk's page SYSTEM into the panel set,
    # and `field-quote` -- one of the three ids this allowance exists for --
    # came back as an unreachable panel on a working app. The allowance means
    # "not a sidebar panel", which is a statement about both directions.
    unreached = [p for p in sorted(panel_ids)
                 if p not in wired and not is_sub_container(p)]
    suppressed = [p for p in unreached if p in NO_SIDEBAR_BUTTON_OK]
    no_button = [p for p in unreached
                 if p not in NO_SIDEBAR_BUTTON_OK and p not in PAGE_SYSTEM_IDS]
    for p in suppressed:
        print("SUPPRESSED:%s -- %s" % (p, NO_SIDEBAR_BUTTON_OK[p]))
    if subs:
        print(f"INFO:SUB_CONTAINERS_NOT_NAV_TARGETS:{len(subs)} "
              f"(e.g. {subs[:3]}) -- nested inside a parent panel, not orphans")
    if no_button:
        fails.append(f"PANELS_WITH_NO_NAV_BUTTON:{no_button}")

    # A nav button pointing at no panel at all (dead nav button).
    dead = sorted(unresolved - PAGE_SYSTEM_IDS)
    if dead:
        fails.append(f"NAV_BUTTONS_WITH_NO_PANEL:{dead}")

    # ── "COULD NOT TELL" IS NOT A PASS -- EXIT 3, added 2026-09-10 ──────────
    # This printed the INFO line below and then RESULT:PASS, exit 0. A caller
    # reads the exit code, so a file whose panel system this tool did not
    # recognise counted as a clean check -- and once it was wired into the
    # report-only registry, as a passing checker.
    #
    # THE DISTINCTION IS DERIVED, NOT ASSUMED, because most of the 0-container
    # files are legitimately single-purpose pages (the booking form, the
    # complaint form, the intake page) with nothing to reconcile, and marking
    # those SKIPPED every push is the notice nobody reads. So: a file with no
    # containers AND no nav function taking panel-shaped arguments has genuinely
    # nothing to check and still passes. A file where a nav system CLEARLY
    # EXISTS -- a nav function called with two or more distinct string
    # arguments -- and no container matched is a checker failure, not a clean
    # app, and says so.
    #
    # Exit 3 is the same "a precondition is not a pass" code check4_probe and
    # run_all_tests.py already use, and the same rule as the SQL preflight's
    # fail-closed and --require-live's exit 2.
    if not panel_ids:
        print("INFO:NO_PANELS_FOUND -- this app may use a different container "
              "convention entirely. Reconciliation is vacuous here; confirm by "
              "hand before reading PASS as coverage.")
        # THE SIGNAL IS INDEPENDENT OF nav_fn DETECTION, deliberately. Keying
        # it on `unresolved` was the first attempt and it could not fire: when
        # the container convention is unrecognised, detect_nav_fn scores every
        # candidate at zero and falls back to `nav`, so nothing resolves and
        # nothing is unresolved either. The two failures are the same failure.
        # So: does ANY function get called with two or more distinct string
        # literals from an element handler? That is a panel system, whatever it
        # is called and whatever its containers look like.
        handlers = Counter()
        for m in re.finditer(r'on\w+="\s*(\w+)\(\s*[\'"]([a-zA-Z0-9_-]+)[\'"]',
                             html):
            handlers[m.group(1)] += 1
        top = handlers.most_common(1)
        if top and top[0][1] >= 2:
            print("SKIPPED: a nav system exists here -- %s() is called from %d "
                  "element handlers with string arguments -- and NO container "
                  "convention matched, so nothing was reconciled. This is the "
                  "checker failing to recognise the app, not the app being "
                  "clean." % (top[0][0], top[0][1]))
            sys.exit(3)

    for f in fails:
        print(f"FAIL:{f}")

    print("RESULT:FAIL" if fails else "RESULT:PASS")
    sys.exit(1 if fails else 0)
