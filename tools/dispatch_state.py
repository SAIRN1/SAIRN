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
import subprocess
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
    """[(session, task, age_hours)] for every ACTIVE claim. (list, problem)."""
    if not os.path.isdir(CLAIM_DIR):
        return None, 'no claims directory at ' + CLAIM_DIR
    import time
    out = []
    for fn in sorted(os.listdir(CLAIM_DIR)):
        if not fn.endswith('.json'):
            continue
        try:
            d = json.load(io.open(os.path.join(CLAIM_DIR, fn), encoding='utf-8'))
        except (OSError, ValueError) as exc:
            return None, '%s: %s' % (fn, exc)
        for c in d.get('claims', []):
            if c.get('status') != 'active':
                continue
            age = (time.time() - float(c.get('claimed_at_epoch') or 0)) / 3600.0
            out.append((d.get('session') or fn[:-5],
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


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--self-check', action='store_true')
    args = ap.parse_args(argv)

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
