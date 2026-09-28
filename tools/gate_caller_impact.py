"""BEFORE YOU NARROW A GATE: who calls it, and will they still get in?

Run:  python tools/gate_caller_impact.py --endpoint legal-deadlines --action add_rule
      python tools/gate_caller_impact.py --endpoint legal-deadlines --action add_rule --action add_holidays
      python tools/gate_caller_impact.py --survey
      python tools/gate_caller_impact.py --json

── WHY THIS EXISTS, AND IT IS A NEAR MISS RATHER THAN A THEORY ─────────────
On 2026-09-27 `add_rule` and `add_holidays` were gated to an owner-or-attorney
session. They had been writable with a LICENCE KEY ALONE -- no employee session
at all -- on the table every computed deadline reads from, so the gate was
correct and overdue.

**And it would have broken seeding on all 48 jurisdictions.**
`tools/load_deadline_seed.py` sent the bearer key and nothing else, so every
write would have answered 401. That was caught by reading the loader before
pushing, which is luck dressed as diligence: nothing asked the question, and the
answer was one file away from being discovered by a failed seed load weeks later.

THE FAILURE MODE IS PARTICULARLY QUIET. A tightened gate does not break the
endpoint -- it breaks a CALLER, somewhere else in the repo, that nobody edited.
The endpoint's own suite goes green. The caller's suite, if it has one, mocks
the transport and goes green too. The break appears the next time somebody runs
a loader by hand.

── WHAT IT DECIDES ─────────────────────────────────────────────────────────
Given an endpoint and the action(s) you are about to gate, it reports EVERY
caller of those actions in this repo and whether each one sends a session
header. `checked / universe` is printed, always, because a caller list that
silently missed a directory is the same defect one level up.

A caller is anything under `tools/ tests/ scripts/ agent/ .github/` that names
the endpoint and sends that action. A caller SENDS A SESSION if it sets an
`X-SD-Auth` header anywhere.

EXIT 1 when a named action has a caller that does not send a session. That is
not automatically a defect -- some callers exist precisely to prove the
unauthenticated path is refused -- which is why the finding says
`ACCOUNT FOR THIS` rather than `BROKEN`, and why `--expect-unauthenticated`
takes the ones you have accounted for, by name, so the list cannot rot into
everybody being exempt.

── WHAT IT CANNOT SEE, so the gap is a decision ────────────────────────────
* A caller that builds the action name dynamically (`{"action": verb}`). The
  literal is the anchor and a computed one is invisible. `--survey` prints the
  files it scanned so a reader can spot an obvious omission.
* A caller OUTSIDE this repo -- a cron in another clone, a curl in somebody's
  notes, a customer integration. This is a repo tool and cannot know about them.
  **That is the largest gap and it is why this reports rather than gates.**
* Whether the session a caller sends carries the RIGHT ROLE. It answers
  "authenticates", not "is authorised"; narrowing owner+attorney out of a
  paralegal caller would pass here and still fail live.
"""
import argparse
import io
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from checker_kit import (EXIT_CLEAN, EXIT_FINDING, EXIT_COULD_NOT_RUN,  # noqa: E402
                         REPO, read)

CRITERIA_VERSION = '2026-09-28.1'

# Where a caller can live. PRINTED with the result, because a scope nobody can
# see is a scope nobody can question.
CALLER_DIRS = ('tools/', 'tests/', 'scripts/', 'agent/', '.github/')
CALLER_EXT = ('.py', '.js', '.mjs', '.cjs', '.yml', '.yaml', '.sh')
SESSION_HEADER_RE = re.compile(r'X-SD-Auth', re.I)


def tracked():
    out = subprocess.run(['git', 'ls-files'], cwd=REPO, capture_output=True,
                         text=True, encoding='utf-8', errors='replace')
    if out.returncode != 0:
        return None
    return [f.strip() for f in out.stdout.split('\n') if f.strip()]


def caller_files(files):
    return [f for f in files
            if f.startswith(CALLER_DIRS) and f.endswith(CALLER_EXT)
            and not f.startswith('archive/')]


# ── argparse USES THE WORD `action` TOO, AND THE FIRST RUN PROVED IT ────────
# `ap.add_argument(..., action='store_true')` matched the keyword-argument shape
# below, so --survey reported 49 "KEY ONLY callers" of an action called
# `store_true` -- every argparse tool in the repo. A report that is mostly noise
# is a report nobody runs, which is the same end state as no report. Two
# narrowings, both stated rather than tuned until the number looked right:
# argparse's own vocabulary is excluded by name, and --survey requires the file
# to address a SAIRN endpoint at all.
ARGPARSE_ACTIONS = frozenset((
    'store', 'store_true', 'store_false', 'store_const', 'append',
    'append_const', 'count', 'help', 'version', 'extend', 'parsers'))
ENDPOINT_RE = re.compile(r'sairn\.vercel\.app|/api/[a-z0-9\-]+')


def action_literals(src):
    """Every action name a file sends as a LITERAL, in either language's shape."""
    names = set()
    for m in re.finditer(r'''["']action["']\s*:\s*["']([a-z0-9_]+)["']''', src):
        names.add(m.group(1))
    for m in re.finditer(r'''\baction\s*=\s*["']([a-z0-9_]+)["']''', src):
        names.add(m.group(1))
    return names - ARGPARSE_ACTIONS


def scan(endpoint, actions, expect_unauth, survey):
    files = tracked()
    if files is None:
        return None, ['`git ls-files` failed, so the caller universe is unknown. '
                      'A caller list built from a failed enumeration is worse '
                      'than none.']
    cands = caller_files(files)
    if not cands:
        return None, ['no candidate caller files found under %s -- that is a '
                      'broken invocation, not a repo with no callers'
                      % ', '.join(CALLER_DIRS)]

    unreadable, rows, scanned = [], [], 0
    for f in cands:
        try:
            src = read(os.path.join(REPO, f))
        except (IOError, OSError) as e:
            unreadable.append('%s could not be read (%s) -- NOT scanned, so a '
                              'caller in it would be MISSING from this answer'
                              % (f, e))
            continue
        scanned += 1
        if endpoint and endpoint not in src:
            continue
        # In survey mode there is no endpoint filter, so the file must at least
        # address a SAIRN endpoint -- otherwise every argparse tool in the repo
        # is a "caller". See ARGPARSE_ACTIONS.
        if not endpoint and not ENDPOINT_RE.search(src):
            continue
        sends = action_literals(src)
        hit = sorted(sends & set(actions)) if actions else sorted(sends)
        if not hit:
            continue
        rows.append({'file': f, 'actions': hit,
                     'sends_session': bool(SESSION_HEADER_RE.search(src)),
                     'accounted': f in expect_unauth})
    return {'scanned': scanned, 'universe': len(cands), 'rows': rows,
            'survey': survey}, unreadable


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--endpoint', default='',
                    help='endpoint name as it appears in a caller, e.g. legal-deadlines')
    ap.add_argument('--action', action='append', default=[],
                    help='action being gated (repeatable)')
    ap.add_argument('--expect-unauthenticated', action='append', default=[],
                    help='a caller that SHOULD send no session, by path -- e.g. a '
                         'probe that proves the refusal. Named, never a blanket skip.')
    ap.add_argument('--survey', action='store_true',
                    help='no action filter: list every action any caller sends')
    ap.add_argument('--json', action='store_true')
    args = ap.parse_args(argv)

    if not args.action and not args.survey:
        print('COULD NOT RUN: name the action(s) you are about to gate with '
              '--action, or pass --survey.\nA caller-impact report with no gate '
              'in mind is a directory listing.')
        return EXIT_COULD_NOT_RUN

    result, unreadable = scan(args.endpoint, args.action,
                              set(args.expect_unauthenticated), args.survey)
    if result is None:
        print('COULD NOT RUN:')
        for u in unreadable:
            print('  ? %s' % u)
        return EXIT_COULD_NOT_RUN

    findings = []
    for r in result['rows']:
        if not r['sends_session'] and not r['accounted']:
            findings.append('%s calls %s with a licence key and NO session -- '
                            'ACCOUNT FOR THIS: either it must sign in, or it is '
                            'a probe that proves the refusal and belongs in '
                            '--expect-unauthenticated by name'
                            % (r['file'], ', '.join(r['actions'])))

    print('GATE CALLER IMPACT -- who calls this, and will they still get in')
    print('  criteria          : %s' % CRITERIA_VERSION)
    print('  endpoint          : %s' % (args.endpoint or '(any)'))
    print('  actions           : %s' % (', '.join(args.action) or '(survey)'))
    print('  CHECKED / UNIVERSE: %d / %d candidate caller files'
          % (result['scanned'], result['universe']))
    print('  caller scope      : %s' % ', '.join(CALLER_DIRS))
    print('  A CALLER OUTSIDE THIS REPO IS INVISIBLE HERE -- a cron in another')
    print('  clone, a curl in somebody\'s notes, a customer integration. That is')
    print('  the largest gap and is why this reports rather than gates.')
    print()
    if not result['rows']:
        print('  no caller in this repo sends %s to %s.'
              % (', '.join(args.action) or 'any action', args.endpoint or 'any endpoint'))
    for r in sorted(result['rows'], key=lambda x: x['file']):
        mark = 'SESSION' if r['sends_session'] else ('ACCOUNTED' if r['accounted'] else 'KEY ONLY')
        print('  %-10s %-52s %s' % (mark, r['file'], ', '.join(r['actions'])))

    if args.json:
        print(json.dumps({'criteria': CRITERIA_VERSION, 'endpoint': args.endpoint,
                          'actions': args.action, 'checked': result['scanned'],
                          'universe': result['universe'], 'rows': result['rows'],
                          'findings': findings, 'could_not_run': unreadable}, indent=2))

    if unreadable:
        print('\nCOULD NOT RUN (%d) -- this is NOT a pass:' % len(unreadable))
        for u in unreadable:
            print('  ? %s' % u)
        return EXIT_COULD_NOT_RUN
    if findings:
        print('\nUNACCOUNTED CALLERS (%d):' % len(findings))
        for f in findings:
            print('  ! %s' % f)
        return EXIT_FINDING
    print('\nEVERY caller of these actions either sends a session or is named as '
          'deliberately unauthenticated.')
    return EXIT_CLEAN


if __name__ == '__main__':
    sys.exit(main())
