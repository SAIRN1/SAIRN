#!/usr/bin/env python
r"""dispatch_state.py -- what is genuinely open AND unclaimed, right now.

    python tools/dispatch_state.py            # the dispatch list
    python tools/dispatch_state.py --all      # every open row, claimed or not
    python tools/dispatch_state.py --json
    python tools/dispatch_state.py --self-check

Exit 0 / 1 / 2 per tools/checker_kit.py's contract. REPORT ONLY.

── WHY THIS EXISTS, AND IT IS NOT CONVENIENCE ─────────────────────────────
Two sources answer "what should I work on" and neither answers it alone.
`docs/SAIRN-OPEN-WORK-INDEX.md` says what is OPEN; `.claude/claims/*.json` says
what is BEING WORKED. Reading either on its own produces the two failures this
platform keeps paying for:

  registry only   pick something a live session is already three hours into.
  claims only     `sairn_claim.py check` answers about ONE task string you
                  already thought of. It cannot tell you what else exists.

MEASURED ON THE RUN THAT MOTIVATED THIS FILE, 2026-09-16. A five-item queue was
dispatched to this session. FOUR of the five were another session's live or
owned work -- three of them named verbatim in a claim made SIX MINUTES earlier
("G5 suite negative controls tier A continued, G7 contributing factors on
existing records, item 65 backup band artifact") and the fourth owned in the
registry by that same session, which was active at the time. A per-item
`check` would have caught at most one of them, and on the one it did catch it
answered CLEAR.

── THE CLAIM MATCHER IS NOT THE AUTHORITY HERE, DELIBERATELY ──────────────
It is a PHRASE matcher over a hand-typed task string, and its residual false
CLEAR is measured and recorded: the obvious repair cost 74 extra false blocks
over 20,000 sampled cross-session pairs (`04d1c601`) and was rejected. So this
tool does NOT ask it. It joins on the OWNER COLUMN and on the SESSION NAMES in
the claim text, and where those disagree it says so rather than picking one --
a row whose owner is a session with an active claim is REPORTED AS CONTESTED,
not filtered out. **The reader decides; this narrows what they have to read.**

── WHAT IT CANNOT DO ──────────────────────────────────────────────────────
It cannot tell whether a claim's task string and a registry row are the same
WORK -- that judgement is the thing the matcher already fails at, and building
a second guesser here would just move the failure. What it does is put the two
lists side by side for the rows that matter, which is the step nobody was
doing.
"""

import argparse
import io
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))

# ── UTF-8 ON STDOUT, AND I WROTE THIS FILE'S OWN BUG REPORT EARLIER TONIGHT ─
# On Windows, Python encodes stdout with the LOCALE encoding -- cp1252 -- the
# moment stdout is NOT a terminal, which is to say whenever a hook, a CI step
# or another script CAPTURES it. The open-work index carries emoji in row
# titles, so the first real run of this tool died with UnicodeEncodeError
# halfway through a list it had already computed correctly.
#
# THAT IS THE DEFECT I FIXED IN tools/run_semgrep.py HOURS AGO AND THEN
# MEASURED AS UNSWEPT ACROSS 94 OF 138 FILES IN tools/. This file was the 95th
# before it had been committed once. UTF-8 rather than errors='replace',
# deliberately and for the same reason: replacing turns a character into `?` in
# a report whose whole job is to be read accurately.
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from checker_kit import (EXIT_CLEAN, EXIT_FINDING, EXIT_COULD_NOT_RUN,  # noqa: E402
                         finish, read)

INDEX = os.path.join(REPO, 'docs', 'SAIRN-OPEN-WORK-INDEX.md')
CLAIM_DIR = os.path.join(REPO, '.claude', 'claims')
SESSIONS = ('hank', 'cc', 'cody', 'fourth')

# A row is OPEN unless its status opens with one of these. Read from the real
# vocabulary in the file (measured 2026-09-16: CLOSED 121, BUILT 97, FIXED 41,
# MEASURED 14 ...), NOT invented -- and the default is OPEN, so a status nobody
# has seen before is surfaced rather than silently treated as done.
DONE_WORDS = ('CLOSED', 'BUILT', 'FIXED', 'MEASURED', 'RESOLVED', 'DONE',
              'SEEDED', 'PROMOTED', 'RETRACTED', 'SUPERSEDED', 'REVIEWED',
              'RE-DERIVED', 'DERIVED', 'REGRADED', 'WIRED', 'APPLIED',
              'SWEPT', 'AUDITED', 'ANSWERED', 'REGISTERED', 'CORRECTED')
STRIKE = re.compile(r'^\s*~~')


def strip_md(s):
    s = re.sub(r'&[a-z]+;|&#\d+;', ' ', s)
    s = re.sub(r'[*`~]', '', s)
    return re.sub(r'\s+', ' ', s).strip()


def is_open(status):
    st = strip_md(status).upper()
    if not st:
        return True
    for w in DONE_WORDS:
        if st.startswith(w):
            return False
    return True


def owners_of(cell):
    """Session names named in the owner column. A row can name several."""
    low = strip_md(cell).lower()
    return sorted(s for s in SESSIONS
                  if re.search(r'(?<![a-z])' + s + r'(?![a-z])', low))


def live_claims():
    """[(session, task, age_hours)] for every ACTIVE claim. (list, problem).

    ── IMPORTED, NOT RE-IMPLEMENTED (2026-09-16) ───────────────────────────
    This read `.claude/claims/*.json` out of the WORKING TREE and called
    anything with `status == 'active'` live. `sairn_claim.py` answers the same
    question two ways differently, and both differences were visible in this
    tool's own output:

      * IT READS origin/main, not the working tree. A claim another session
        pushed is only a fact once it is there, and a claim this clone has
        written and not pushed is invisible to everyone else -- so a local read
        over-reports here and under-reports them. `sairn_claim.read_origin_
        claims()` uses `git show`, which cannot write, deliberately: the
        `git checkout origin/main -- .claude/claims` it replaced STAGED a
        revert of a claim this clone had already committed (PR 1.4).
      * IT APPLIES THE 4-HOUR EXPIRY. `is_active()` requires the claim to be
        inside STALE_HOURS. Measured on 2026-09-16: this panel listed a
        74.4-hour-old `fourth` claim as ACTIVE while `sairn_claim.py list`
        did not show it at all. Two tools, one claim record, two answers, and
        the one a session reads before starting work was the looser of them.

    THAT DIVERGENCE IS WHAT THE DORMANT `import subprocess` AT THE TOP OF THIS
    FILE WAS FOR. It was left behind by a pass that started making this read
    the same way and did not finish; nothing in this module ever called it. The
    resolution is to call the owner rather than to grow a second reader --
    the same decision `report_only_checks.py` records about the push gate:
    "THE PUSH GATE IS IMPORTED, NOT COPIED", after a fix reached one copy and
    not the other. So the import is gone and sairn_claim owns the subprocess
    calls.
    """
    if not os.path.isdir(CLAIM_DIR):
        return None, 'no claims directory at ' + CLAIM_DIR
    try:
        import sairn_claim
    except Exception as exc:                                     # noqa: BLE001
        # PR 1.11. A check that depends on another tool fails CLOSED when it is
        # absent, and says which tool. Returning an empty list here would print
        # "0 active claims" -- the exact sentence that sends a session into work
        # somebody else is already doing.
        return None, ('sairn_claim.py could not be imported (%s), so the claim '
                      'half of this report did not run' % exc)
    try:
        claims = sairn_claim.load_all(from_origin=True)
    except Exception as exc:                                     # noqa: BLE001
        return None, 'sairn_claim.load_all failed: %s' % exc
    out = []
    for c in claims:
        if not sairn_claim.is_active(c):
            continue
        age = (sairn_claim.now() - float(c.get('claimed_at_epoch') or 0)) / 3600.0
        out.append((c.get('session') or os.path.basename(c.get('_file', ''))[:-5],
                    '%s: %s' % (c.get('subject', ''), c.get('task', '')),
                    age))
    return out, ''


def rows():
    """[(app, item, status, owner)] for every table row with 7 columns."""
    try:
        src = read(INDEX)
    except OSError as exc:
        return None, str(exc)
    out = []
    for ln in src.split('\n'):
        if not ln.startswith('|'):
            continue
        c = ln.split('|')
        if len(c) < 8:
            continue
        if c[1].strip() == 'App' or set(c[2].strip()) <= set('- :'):
            continue
        out.append((strip_md(c[1]), c[2].strip(), c[3].strip(), c[4].strip()))
    return out, ''


# ── ROWS WHOSE LEADING WORD DISAGREES WITH THE REST OF THE CELL ─────────────
# `is_open()` reads the FIRST word of the status and defaults to OPEN. That is
# the right default -- an unknown status is surfaced rather than assumed done --
# and it means a row whose work landed stays OPEN until somebody edits the word.
#
# THE COST IS MEASURED, NOT ASSUMED. On 2026-09-16, of 173 open rows, TWO of the
# first four spot-checked were already finished: `master_plan.py gate 4 counts
# fault probes in PYTHON ONLY` (fault_probes() carries FAULT_PROBE_JS and the
# document prints sairnbiz ... 2) and `run_snapshot_freshness_probe.py arms 2c
# and 4a RED` (re-run: 0 arms failed). A third had already been closed under a
# different title. A dispatch list that sends a session at finished work is the
# failure the list exists to prevent, one level up.
#
# ── SO WHY THIS IS A REVIEW LIST AND NOT A VERDICT ──────────────────────────
# MEASURED BOTH WAYS. A done word ANYWHERE in the status fires on 89 of 173 --
# useless. Restricted to the first four tokens it fires on 45, and reading those
# 45 is what settles it: the same shape covers
#
#   CONFIRMED AND CLOSED      really done
#   TRACED AND CLOSED         really done
#   HALF CLOSED               explicitly not
#   CODE CLOSED               done in code, migration never run
#   OPEN BUILT AND PROVEN     the row says OPEN in its own first word
#   FOUND AND FIXED           and this one is on a row another session is
#                             CURRENTLY working because the test is still RED
#
# There is no rule separating those without reading the sentence, and a tool
# that guessed would close real work. So this prints the shortlist and refuses
# the verdict, which is the same decision dispatch_state already makes about
# matching a claim to a row.
#
# ── AND THE STANDING MECHANISM, ANSWERED RATHER THAN DEFERRED ───────────────
# An auto-flip on merge is NOT buildable here and the blocker is concrete: a
# commit cannot name the row it closes, because ROWS HAVE NO IDs. Adding them is
# a change to 523 rows and a convention every session has to follow, which is
# Michael's call and not a tool's. Until then the honest mechanism is this list
# plus the convention the list makes visible: THE FIRST WORD OF A STATUS IS THE
# VERDICT, and everything qualifying it comes after.
LEADING_TOKENS = 4


def cmd_stale_review(argv=None):
    rs, err = rows()
    if rs is None:
        print('COULD NOT READ %s: %s -- nothing was reviewed. NOT a pass.'
              % (INDEX, err))
        return 2
    open_rows = [r for r in rs if is_open(r[2])]
    hits = []
    for app, item, status, owner in open_rows:
        st = strip_md(status).upper()
        toks = re.findall(r'[A-Z-]+', st)[:LEADING_TOKENS]
        for i, t in enumerate(toks):
            if i > 0 and t in DONE_WORDS:
                hits.append((app, strip_md(item), ' '.join(toks), strip_md(owner)))
                break
    print('STATUS-WORD REVIEW -- rows whose leading phrase disagrees with itself')
    print('  %d row(s), %d open, %d to review' % (len(rs), len(open_rows), len(hits)))
    print('  A done word ANYWHERE fires on far more and is useless; the first %d'
          % LEADING_TOKENS)
    print('  tokens is the tightest band that still contains the real ones.')
    print('')
    for app, item, lead, owner in hits:
        print('  %-13s %-58s' % (app[:13], item[:58]))
        print('      status opens: %-34s owner: %s' % (lead[:34], owner[:26] or '-'))
    print('')
    print('  THIS IS A SHORTLIST AND NOT A VERDICT. The same shape covers')
    print('  "CONFIRMED AND CLOSED" (done), "HALF CLOSED" (explicitly not),')
    print('  "CODE CLOSED" (done in code, migration never run) and "FOUND AND')
    print('  FIXED" on a row another session is working right now because the')
    print('  test is still RED. No rule separates those without reading the')
    print('  sentence, and a tool that guessed would close real work.')
    print('')
    print('  THE CONVENTION THIS MAKES VISIBLE: the FIRST word of a status is')
    print('  the verdict; everything qualifying it comes after. An auto-flip on')
    print('  merge is not buildable until rows carry IDs a commit can name.')
    return 1 if hits else 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--self-check', action='store_true')
    ap.add_argument('--stale-review', action='store_true', dest='stale',
                    help='rows whose leading status phrase disagrees with itself')
    args = ap.parse_args(argv)

    if args.stale:
        return cmd_stale_review()

    if args.self_check:
        bad = self_check()
        print('\n%d case(s) wrong' % len(bad))
        return EXIT_CLEAN if not bad else EXIT_FINDING

    bad = self_check(verbose=False)
    if bad:
        print('COULD NOT RUN -- the open/closed rule failed its own fixtures, '
              'so nothing was classified:')
        for label, got, want in bad:
            print('  %r -> %s, expected %s' % (label, got, want))
        return EXIT_COULD_NOT_RUN

    claims, cproblem = live_claims()
    rs, rproblem = rows()
    could_not_run = [p for p in (cproblem, rproblem) if p]
    if rs is None or claims is None:
        print('COULD NOT RUN: ' + '; '.join(could_not_run))
        return EXIT_COULD_NOT_RUN

    busy = {}
    for sess, task, age in claims:
        busy.setdefault(sess, []).append((task, age))

    open_rows = [r for r in rs if is_open(r[2]) and not STRIKE.match(r[1])]
    contested, michael, unclaimed, unowned = [], [], [], []
    for app, item, status, owner in open_rows:
        os_ = owners_of(owner)
        low = strip_md(owner).lower()
        if any(s in busy for s in os_):
            contested.append((app, item, owner, [s for s in os_ if s in busy]))
        elif 'michael' in low:
            michael.append((app, item, owner))
        elif os_:
            unclaimed.append((app, item, owner))
        else:
            unowned.append((app, item, owner))

    if args.json:
        print(json.dumps({'open': len(open_rows), 'contested': contested,
                          'michael': michael, 'unclaimed': unclaimed,
                          'unowned': unowned,
                          'claims': [(s, t, round(a, 2)) for s, t, a in claims]},
                         indent=1))
        return finish([], could_not_run, quiet=True)

    print('DISPATCH STATE -- %d open row(s) of %d, %d active claim(s)'
          % (len(open_rows), len(rs), len(claims)))
    print('')
    print('ACTIVE CLAIMS, which is the half a per-item `check` cannot show you:')
    for sess, task, age in sorted(claims, key=lambda x: x[2]):
        print('  %-7s %4.1fh  %s' % (sess, age, task[:96]))
    print('')
    print('CONTESTED -- open, and owned by a session that is working RIGHT NOW '
          '(%d).' % len(contested))
    print('  Not a verdict that it IS the same work; the owner column and a '
          'live claim')
    print('  simply point at the same session, and that is worth reading before '
          'starting.')
    for app, item, owner, who in contested[:20]:
        print('  ! %-13s %-62s -> %s' % (app[:13], strip_md(item)[:62], ','.join(who)))
    if len(contested) > 20:
        print('    ... and %d more' % (len(contested) - 20))
    print('')
    print("MICHAEL'S (%d) -- open and waiting on a decision or an action only he "
          'can take.' % len(michael))
    for app, item, _o in michael[:12]:
        print('    %-13s %s' % (app[:13], strip_md(item)[:66]))
    if len(michael) > 12:
        print('    ... and %d more' % (len(michael) - 12))
    print('')
    print('OPEN, OWNED, AND THAT OWNER IS NOT CURRENTLY WORKING (%d) -- the real '
          'dispatch list.' % len(unclaimed))
    for app, item, owner in unclaimed[:25]:
        print('    %-13s %-58s owner: %s'
              % (app[:13], strip_md(item)[:58], strip_md(owner)[:22]))
    if len(unclaimed) > 25:
        print('    ... and %d more' % (len(unclaimed) - 25))
    print('')
    print('OPEN AND UNOWNED (%d) -- nobody named at all.' % len(unowned))
    for app, item, _o in unowned[:25]:
        print('    %-13s %s' % (app[:13], strip_md(item)[:66]))
    if len(unowned) > 25:
        print('    ... and %d more' % (len(unowned) - 25))
    print('')
    print('THIS DOES NOT DECIDE WHETHER A CLAIM AND A ROW ARE THE SAME WORK.')
    print('That judgement is exactly what the phrase matcher already fails at --')
    print('its residual false CLEAR is measured, and the obvious repair cost 74')
    print('extra false blocks over 20,000 sampled pairs and was rejected. A')
    print('second guesser here would move the failure, not remove it. What this')
    print('does is put the two lists side by side, which nobody was doing.')
    return finish([], could_not_run)


FIXTURES = [
    ('**CLOSED 2026-09-15 (Cody)**', False),
    ('**BUILT 2026-09-14 (Fourth)**', False),
    ('**FIXED 2026-09-15 (Hank)**', False),
    ('**MEASURED 2026-09-14 (CC)**', False),
    ('**RE-DERIVED 2026-09-15 (Fourth)**', False),
    ('Open &mdash; needs a call', True),
    ('**Blocked 2026-08-27**', True),
    ('**SCOPED 2026-09-15 (Hank)**, nothing built', True),
    ('**PHASE 1 DONE**, PHASE 2 PENDING', True),
    ('', True),
    ('**SOMETHING NOBODY HAS USED BEFORE**', True),
]


def self_check(verbose=True):
    bad = []
    for status, want in FIXTURES:
        got = is_open(status)
        if verbose:
            print('    %-46s open=%-5s %s'
                  % (strip_md(status)[:46] or '(empty)', got,
                     'ok' if got == want else 'EXPECTED %s' % want))
        if got != want:
            bad.append((status, got, want))
    # THE DEFAULT MUST BE OPEN. A status vocabulary this file has never seen is
    # surfaced, never silently treated as done -- the reverse would make a new
    # word hide a row for ever.
    if is_open('**QUUXED 2026-01-01**') is not True:
        bad.append(('unknown status defaults to open', False, True))
    return bad


if __name__ == '__main__':
    sys.exit(main())
