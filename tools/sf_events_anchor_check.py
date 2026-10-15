#!/usr/bin/env python
# OWNER: fourth
# written 2026-10-15, batch b22 followup, routed by hover2 b36
"""Enforce the sf_events cell's OWN rule: every quoted anchor in it resolves
EXACTLY ONCE in sairnfreedom.html.

    python tools/sf_events_anchor_check.py
    python tools/sf_events_anchor_check.py --fixtures

Exit 0 clean, 1 findings, 2 COULD NOT RUN.

── WHY THIS EXISTS, AND WHAT IT IS NOT ─────────────────────────────────────
The `sf_events` row of docs/CRITICALITY-TIERS.md carries its citations as
QUOTED STRINGS rather than line numbers, because all seven of its line
citations had rotted by 2026-10-14. The cell states its own acceptance rule in
its own text -- "every quoted anchor in this cell must resolve EXACTLY ONCE in
sairnfreedom.html" -- and until now NOTHING ENFORCED IT. A rule written in prose
inside the thing it governs is a rule that goes quiet the day it is broken.

It went quiet on 2026-10-14. hank b12's F6 rewrote `sfDeleteEvent()` for a real
and correct reason, which moved the text one anchor was quoting; the anchor fell
to ZERO matches and the register went on asserting it. hover2 found it by hand
in b36 and routed it; fourth fixed it in b22. THIS CHECK IS THE THING THAT WOULD
HAVE SAID SO WITHOUT A HUMAN RE-READING THE CELL.

THIS IS NOT cc's ROUTED ANCHOR-ROT TOOL and does not replace it. That one is
general over the whole register (the b20 spec: 8 requirements / 10 arms,
including reporting bare `:NNNN` citations as UNASSESSABLE rather than folding
them into a total). This is one cell and one app file. When the general tool
lands, this should be deleted rather than maintained beside it -- said here so
that deletion is the expected end state and not a judgement call later.

── WHAT IT CANNOT TELL YOU, PRINTED EVERY RUN ──────────────────────────────
A resolving anchor proves the quoted text EXISTS EXACTLY ONCE. It does not
prove the cell's claim ABOUT that text is true. "The delete removes the linked
session by stored id only" is an argument about what the code means, and no
string match establishes it. That half needs the cell read, and the run says so
rather than letting a clean exit stand in for a verdict.

── FAILS CLOSED ────────────────────────────────────────────────────────────
A missing sairnfreedom.html, a missing register, a register with no sf_events
row, or MORE THAN ONE sf_events row is exit 2 COULD NOT RUN -- never exit 0.
"Could not run" is a third state and is never folded into "passed" (PR 1.11).
A cell that uses the `anchor` convention and names ZERO anchors is a FINDING,
not a pass: it would otherwise measure nothing and print a clean line.
"""
import io
import os
import re
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
try:
    from checker_kit import EXIT_CLEAN, EXIT_FINDING, EXIT_COULD_NOT_RUN
except Exception:                                                # noqa: BLE001
    EXIT_CLEAN, EXIT_FINDING, EXIT_COULD_NOT_RUN = 0, 1, 2

CRITERIA_VERSION = '2026-10-15.1'

REGISTER = os.path.join(REPO, 'docs', 'CRITICALITY-TIERS.md')
APP = os.path.join(REPO, 'sairnfreedom.html')
ROW_PREFIX = '| `sf_events` |'

# The register stores these escaped; the app source carries the raw character.
# Table measured from the real row rather than guessed, because an unescape
# that is too eager turns a correct anchor into a phantom miss.
ENTITIES = (
    ('&amp;', '&'), ('&lt;', '<'), ('&gt;', '>'), ('&quot;', '"'),
    ('&rarr;', '→'), ('&larr;', '←'), ('&mdash;', '—'),
    ('&lsquo;', '‘'), ('&rsquo;', '’'),
    ('&ldquo;', '“'), ('&rdquo;', '”'),
)

# ONLY spans the cell explicitly introduces with the word `anchor`. The cell
# also carries ordinary prose in backticks -- `eventRefusals()`,
# `liquorServiceCheck()`, `sc_auth` -- which are function and row NAMES written
# with empty parentheses while the source writes them with arguments. Those
# count ZERO in the app and are NOT anchors. Treating every backticked span as
# an anchor would report three false positives on this one cell, which is the
# first thing the general tool will have to get right too.
ANCHOR_RE = re.compile(r'anchor\s+`([^`]+)`')


def unescape(s):
    for a, b in ENTITIES:
        s = s.replace(a, b)
    return s


def anchors(cell):
    """-> [anchor text], in document order, markdown entities resolved."""
    return [unescape(m.group(1)) for m in ANCHOR_RE.finditer(cell)]


def check(cell, app_src):
    """-> [finding string]. Empty means every anchor resolved exactly once."""
    found = anchors(cell)
    if not found:
        return ['NO ANCHOR: the cell names no `anchor `...`` span at all, so '
                'this check would pass by measuring nothing. Either the cell '
                'stopped using the convention or the convention changed '
                'spelling -- both need a human, neither is a pass.']
    out = []
    for i, a in enumerate(found, 1):
        n = app_src.count(a)
        if n == 1:
            continue
        if n == 0:
            out.append('ROTTED: anchor %d of %d resolves ZERO times. The cell '
                       'asserts text that is no longer in the app. Re-anchor '
                       'it on the code that replaced it; do not delete the '
                       'claim. Anchor: %r' % (i, len(found), a))
        else:
            out.append('AMBIGUOUS: anchor %d of %d resolves %d times, so it '
                       'does not identify a site and a later reader cannot '
                       'tell which one the cell means. Lengthen it until it '
                       'is unique. Anchor: %r' % (i, len(found), n, a))
    return out


# ── THE CRITERIA LOCK: synthetic fixtures, driven BEFORE the real data ──────
# Locked against hand-built strings rather than against the live register, so
# the check cannot be "proved" by the very file it is meant to judge. Arm 2 is
# the REAL pre-fix anchor text: it is the failing-first arm, and it must be a
# FINDING or this tool would have slept through the drift it was written for.
PRE_FIX_ANCHOR = ('if(ev && ev.sessionId) st(K_SESSIONS, '
                  'getSessions().filter(')
POST_FIX_ANCHOR = ('var after = before.filter(function(s){ return '
                   's.id!==ev.sessionId; });')

FIXTURE_APP = (
    'function sfDeleteEvent(id){\n'
    '  var removedSessions = 0;\n'
    '  if (ev && ev.sessionId) {\n'
    '    var before = getSessions();\n'
    '    ' + POST_FIX_ANCHOR + '\n'
    '    removedSessions = before.length - after.length;\n'
    '  }\n'
    '}\n'
    'function eventRefusals(e){ return []; }\n'
)


def run_fixtures():
    bad = []

    def arm(label, got, want):
        ok = got == want
        if not ok:
            bad.append(label)
        print('  %-4s %-72s' % ('ok' if ok else 'FAIL', label))

    print('SF_EVENTS ANCHOR CHECK -- criteria lock %s' % CRITERIA_VERSION)

    arm('an anchor present exactly once is CLEAN',
        check('anchor `' + POST_FIX_ANCHOR + '`', FIXTURE_APP), [])

    # FAILING-FIRST, and it is the real drift: the pre-fix text is absent from
    # the post-fix app, so the check must go red on the register as it stood
    # before b22. If this arm ever passes, the tool has stopped testing.
    f = check('anchor `' + PRE_FIX_ANCHOR.replace('&', '&amp;') + '`',
              FIXTURE_APP)
    arm('THE REAL PRE-FIX ANCHOR IS A FINDING (failing-first)', len(f), 1)
    arm('...and the finding says ROTTED', f and f[0].startswith('ROTTED'), True)

    arm('an anchor resolving TWICE is a finding',
        len(check('anchor `function sfDeleteEvent(id){`',
                  FIXTURE_APP + FIXTURE_APP)), 1)
    arm('...and that finding says AMBIGUOUS',
        check('anchor `function sfDeleteEvent(id){`',
              FIXTURE_APP + FIXTURE_APP)[0].startswith('AMBIGUOUS'), True)

    arm('NO anchor at all is a FINDING, not a pass',
        len(check('a cell with `backticks` but no anchor keyword',
                  FIXTURE_APP)), 1)
    arm('...and that finding says NO ANCHOR',
        check('a cell with `backticks` but no anchor keyword',
              FIXTURE_APP)[0].startswith('NO ANCHOR'), True)

    # The entity half, in BOTH directions. The register escapes & as &amp;;
    # an anchor that is correct in the app must not be reported rotted because
    # of the escaping, and the unescape must not invent a match either.
    arm('an &amp;-escaped anchor matches the raw app text',
        check('anchor `if (ev &amp;&amp; ev.sessionId) {`', FIXTURE_APP), [])
    arm('unescaping does NOT invent a match for absent text',
        len(check('anchor `if (zz &amp;&amp; zz.nope) {`', FIXTURE_APP)), 1)

    # The false-positive class this tool must NOT produce: prose spans.
    arm('a prose span with empty parens is IGNORED, not a finding',
        check('`eventRefusals()` runs first; anchor `'
              + POST_FIX_ANCHOR + '`', FIXTURE_APP), [])

    print('  %d/%d arms classify correctly'
          % (10 - len(bad), 10))
    if bad:
        print('  CRITERIA BROKEN: ' + '; '.join(bad))
        return EXIT_FINDING
    return EXIT_CLEAN


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    lock = run_fixtures()
    if lock != EXIT_CLEAN:
        print()
        print('REFUSING TO JUDGE REAL DATA ON BROKEN CRITERIA.')
        return EXIT_COULD_NOT_RUN
    if '--fixtures' in argv:
        return EXIT_CLEAN

    print()
    print('SF_EVENTS ANCHOR CHECK -- criteria %s' % CRITERIA_VERSION)

    for path, what in ((REGISTER, 'the register'), (APP, 'the app')):
        if not os.path.isfile(path):
            print('  COULD NOT RUN: %s is missing (%s). This check depends on '
                  'it, so it did NOT run -- which is not a pass.'
                  % (os.path.relpath(path, REPO), what))
            return EXIT_COULD_NOT_RUN

    rows = [(i + 1, l) for i, l in
            enumerate(io.open(REGISTER, encoding='utf-8').read().split('\n'))
            if l.startswith(ROW_PREFIX)]
    if len(rows) != 1:
        print('  COULD NOT RUN: expected exactly ONE row starting %r, found '
              '%d. Judging the wrong row is worse than not judging one.'
              % (ROW_PREFIX, len(rows)))
        return EXIT_COULD_NOT_RUN

    lineno, cell = rows[0]
    app_src = io.open(APP, encoding='utf-8').read()
    found = anchors(cell)
    findings = check(cell, app_src)

    print('  docs/CRITICALITY-TIERS.md:%d -- %d anchor(s), %d char cell'
          % (lineno, len(found), len(cell)))
    for i, a in enumerate(found, 1):
        n = app_src.count(a)
        print('  %-5s anchor %d  count=%d  %s'
              % ('ok' if n == 1 else 'MISS', i, n, a[:84]))

    print()
    if findings:
        print('%d FINDING(S):' % len(findings))
        for f in findings:
            print('  ! %s' % f)
        return EXIT_FINDING

    print('CLEAN: every quoted anchor in the sf_events cell resolves EXACTLY '
          'ONCE in sairnfreedom.html.')
    print('LIMIT, not folded into that pass: this proves the quoted TEXT '
          'exists and is unique. It does NOT prove the cell\'s claim ABOUT '
          'that text -- "the delete removes the linked session by stored id '
          'only" is an argument about meaning, and no string match establishes '
          'it. That half needs the cell read.')
    return EXIT_CLEAN


if __name__ == '__main__':
    sys.exit(main())
