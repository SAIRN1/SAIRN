"""ABLATION: remove one guard at a time and ask whether ANYTHING notices.

Run:  python tools/guard_ablation.py              # every role gate in sd-data.js
      python tools/guard_ablation.py --limit 5    # first N, for a quick look
      python tools/guard_ablation.py --json OUT   # machine-readable report

ITEM 98 -- ABLATION, AND HOW IT DIFFERS FROM MUTATION TESTING
--------------------------------------------------------------
Mutation testing asks: *does a test catch this defect?* Ablation asks a
different and blunter question borrowed from ML practice: *if I remove this
component entirely, does the measured outcome change at all?* A component whose
removal changes nothing is not automatically wrong -- but it is definitely not
EARNING anything measurable, and you cannot claim it contributes.

The distinction is not academic here. On 2026-09-15 a three-layer peel of
SAIRNcare's pharmacy-review gate found that its innermost role check is
UNREACHABLE BY CONSTRUCTION -- an outer gate has already refused every role it
names by the time it runs. `tests/sairncare/test-alf-phase3.js` had an assertion
literally called *"med_aide CANNOT accept a pharmacy order"* which passed on a
DIFFERENT gate entirely. Mutation testing on that guard reports "not caught" and
points at the test suite. Ablation reports "removing it changes nothing" and
points at the ARCHITECTURE, which is where the answer actually was.

WHAT THIS ABLATES
-----------------
Every role gate in `api/sd-data.js` of the exact shape

    if (!SOMETHING_ROLES[session.role]) {

replaced one at a time with `if (false) {` -- the guard stops refusing anybody.
The set is DERIVED by scanning the file, never listed, so a gate added tomorrow
is ablated tomorrow.

Then every suite that exercises `api/sd-data.js` is run against it.

THREE OUTCOMES, AND THE THIRD IS NEVER FOLDED INTO THE FIRST
--------------------------------------------------------------
  LOAD-BEARING  at least one suite goes red. The guard is individually
                necessary and something proves it. The first suite to notice is
                named, so the claim is auditable.
  SILENT        every suite stays green. This means ONE OF TWO THINGS and this
                tool CANNOT TELL THEM APART:
                  (a) redundant -- another guard refuses the same request, so
                      behaviour is unchanged (the pharmacy case), or
                  (b) untested -- behaviour genuinely changed and nobody looks.
                (a) is fine and (b) is a hole. Reporting them as one number
                would be the fabrication this platform keeps paying for, so
                SILENT is reported as a QUESTION, never as a verdict.
  COULD-NOT-RUN the baseline was not green, or the anchor did not match exactly
                once. Never counted as either of the above.

WHY SHORT-CIRCUIT IS SAFE HERE
-------------------------------
LOAD-BEARING is an existential claim -- "at least one suite notices" -- so the
first red suite settles it and the rest are not run. SILENT is a universal
claim, so it pays the full sweep every time. The asymmetry is deliberate: the
expensive path is the one whose answer must be complete.

THIS IS A REPORTING TOOL, NOT A GATE. It does not belong in the push gate: a
SILENT result is a question for a person, and a number nobody can act on gets
driven to zero by the cheapest available route, which for a checker is
switching it off.
"""
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

REPO = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True).stdout.strip()
SUBJECT = os.path.join('api', 'sd-data.js')
# `[ \t]*` AND NOT `\s*`, AND THE DIFFERENCE COST A GATE. `\s` includes the
# newline, so with re.M the `^` could match at a BLANK line and `(\s*)` would
# then eat that line's newline plus the next line's indentation -- producing an
# anchor that spans two lines and can never equal any single line. It happened
# exactly once in 38 gates (EMPLOYEE_PROFILE_MANAGE_ROLES, the one preceded by a
# blank line) and was reported as COULD-NOT-RUN rather than silently skipped,
# which is the only reason it was visible at all.
GATE = re.compile(r'^([ \t]*)if \(!(\w+_ROLES)\[session\.role\]\) \{$', re.M)


def fail(msg):
    print('COULD NOT RUN: ' + msg)
    print('Nothing was ablated. This is exit 2, not a pass.')
    sys.exit(2)


def suites():
    """Every tracked test that loads api/sd-data.js. Derived, not listed."""
    r = subprocess.run(['git', '-C', REPO, 'ls-files', 'tests/', 'api/'],
                       capture_output=True, text=True)
    if r.returncode != 0:
        fail('git ls-files failed')
    out = []
    for p in r.stdout.splitlines():
        if not p.endswith('.js'):
            continue
        if not (p.startswith('tests/') or p.endswith('.test.js')):
            continue
        try:
            body = io.open(os.path.join(REPO, p), encoding='utf-8',
                           errors='replace').read()
        except OSError:
            continue
        if 'sd-data.js' in body:
            out.append(p)
    return sorted(out)


def run(wt, suite, timeout=60):
    try:
        r = subprocess.run(['node', os.path.join(wt, suite)], cwd=wt,
                           capture_output=True, text=True, timeout=timeout)
        return r.returncode
    except subprocess.TimeoutExpired:
        return 124


def main(argv):
    limit = None
    if '--limit' in argv:
        limit = int(argv[argv.index('--limit') + 1])
    jsonout = argv[argv.index('--json') + 1] if '--json' in argv else None

    src = io.open(os.path.join(REPO, SUBJECT), encoding='utf-8',
                  newline='').read()
    gates = [(m.group(0), m.group(2),
              src[:m.start()].count('\n') + 1) for m in GATE.finditer(src)]
    if not gates:
        fail('no `if (!X_ROLES[session.role]) {` sites found in %s -- the shape '
             'this tool ablates has changed, so it is refusing rather than '
             'reporting zero' % SUBJECT)

    S = suites()
    if not S:
        fail('no suite loads api/sd-data.js -- nothing could observe an ablation')

    # ── THE SUBJECT IS FINGERPRINTED, AND THAT IS NOT DECORATION ───────────
    # A full sweep takes tens of minutes. The FIRST real run of this tool was
    # overlapped by an unrelated edit to api/sd-data.js, and every line number
    # in its report was silently off by one by the time anybody read it -- the
    # report was internally consistent, externally wrong, and nothing said so.
    # That is the eighth cross-domain discipline exactly: nothing announces the
    # day a check stops describing its subject. The hash is printed here and
    # RE-CHECKED at the end, so a stale report says it is stale.
    digest = hashlib.sha256(src.encode('utf-8')).hexdigest()[:12]
    print('GUARD ABLATION -- item 98\n')
    print('  subject : %s' % SUBJECT.replace(os.sep, '/'))
    print('  sha256  : %s  (line numbers below are relative to THIS content)'
          % digest)
    print('  gates   : %d  (derived by scanning, not listed)' % len(gates))
    print('  suites  : %d  (every tracked test that loads the subject)\n' % len(S))

    wt = tempfile.mkdtemp(prefix='sairn-abl-')
    shutil.rmtree(wt, ignore_errors=True)
    add = subprocess.run(['git', '-C', REPO, 'worktree', 'add', '-q',
                          '--detach', wt, 'HEAD'], capture_output=True, text=True)
    if add.returncode != 0:
        fail('could not create a worktree: ' + add.stderr.strip()[:200])

    results = []
    try:
        # ── EVERY MODIFIED TRACKED FILE COMES ACROSS, NOT JUST THE SUBJECT ──
        # The first version copied only the subject and the suites. A run
        # overlapping uncommitted work then put a sd-data.js that `require`s a
        # NEW lib into a worktree that did not have that lib, and 48 of 93
        # suites went red on the baseline -- reported honestly and loudly, but
        # the run was worthless. Copying the subject without its dependencies
        # is not "reading the working tree", it is reading half of it.
        dirty = subprocess.run(
            ['git', '-C', REPO, 'diff', '--name-only', 'HEAD'],
            capture_output=True, text=True).stdout.split()
        for rel in sorted(set([SUBJECT] + list(S) + dirty)):
            srcp = os.path.join(REPO, rel)
            dstp = os.path.join(wt, rel)
            if not os.path.isfile(srcp):
                continue
            d = os.path.dirname(dstp)
            if d and not os.path.isdir(d):
                os.makedirs(d)
            shutil.copyfile(srcp, dstp)
        # Untracked-but-required files are NOT copied and cannot be: the tool
        # does not know which untracked file is a dependency and which is
        # somebody's scratch. The baseline guard below is what catches that.

        # ── BASELINE. A suite that is already red cannot report an ablation,
        #    and counting it as "did not notice" would be a lie in the safe
        #    direction. Those are dropped by name, loudly.
        green, broken = [], []
        for s in S:
            (green if run(wt, s) == 0 else broken).append(s)
        if broken:
            print('  %d suite(s) are NOT GREEN on the shipped tree and are '
                  'EXCLUDED -- they could not observe anything:' % len(broken))
            for s in broken[:10]:
                print('      ' + s)
            if len(broken) > 10:
                print('      ... and %d more' % (len(broken) - 10))
            print()
        if not green:
            fail('every suite is red on the shipped tree -- no observer')
        # ── A COLLAPSED OBSERVER SET IS A FINDING, NOT A SMALLER RUN ────────
        # With most suites excluded, almost every gate comes back SILENT and the
        # report reads like a platform-wide coverage hole when the real cause is
        # that the worktree is broken. That is a false finding dressed as a
        # measurement, which is worse than no run. One third is a judgement, and
        # it is stated rather than tuned: the observed failure was 48 of 93.
        if len(broken) * 3 > len(S):
            fail('%d of %d suites are red on the shipped tree. The observer set '
                 'has collapsed, so a SILENT verdict would say more about this '
                 'worktree than about any guard. Fix the baseline first -- the '
                 'usual cause is an uncommitted dependency the worktree does '
                 'not have.' % (len(broken), len(S)))
        print('  observing suites: %d\n' % len(green))

        # ── ABLATION IS BY LINE NUMBER, NOT BY STRING REPLACE ──────────────
        # The first version did `src.replace(anchor, ..., 1)` and reported
        # COULD-NOT-RUN for every gate whose text is not unique.
        # `if (!CRM_MANAGEMENT_ROLES[session.role]) {` appears at FOUR sites, so
        # four real gates became four non-answers -- and `replace(..., 1)` would
        # silently have hit the first one four times if the count had not been
        # checked. A line index cannot be ambiguous. The line is re-read from
        # the split source and asserted to still match the pattern before it is
        # touched, so a stale index refuses instead of damaging a random line.
        lines = src.split('\n')
        todo = gates[:limit] if limit else gates
        for i, (anchor, name, line) in enumerate(todo, 1):
            idx = line - 1
            if idx >= len(lines) or lines[idx] != anchor:
                print('  ?      %-38s :%-6d COULD-NOT-RUN (line no longer '
                      'matches the gate pattern)' % (name, line))
                results.append({'role_table': name, 'line': line,
                                'verdict': 'COULD-NOT-RUN', 'noticed_by': None})
                continue
            mutated = list(lines)
            mutated[idx] = anchor.split('if (')[0] + 'if (false) {'
            io.open(os.path.join(wt, SUBJECT), 'w', encoding='utf-8',
                    newline='').write('\n'.join(mutated))
            noticed = None
            for s in green:
                if run(wt, s) != 0:
                    noticed = s
                    break
            io.open(os.path.join(wt, SUBJECT), 'w', encoding='utf-8',
                    newline='').write(src)
            if noticed:
                print('  ok     %-38s :%-6d LOAD-BEARING   caught by %s'
                      % (name, line, os.path.basename(noticed)))
                results.append({'role_table': name, 'line': line,
                                'verdict': 'LOAD-BEARING', 'noticed_by': noticed})
            else:
                print('  ?      %-38s :%-6d SILENT         %d suites, none '
                      'noticed' % (name, line, len(green)))
                results.append({'role_table': name, 'line': line,
                                'verdict': 'SILENT', 'noticed_by': None})
            sys.stdout.flush()

        # The restore is itself checked -- a silent restore failure would leave
        # every later ablation running against an already-broken subject.
        after = io.open(os.path.join(wt, SUBJECT), encoding='utf-8',
                        newline='').read()
        if after != src:
            fail('the subject was not restored after the last ablation -- '
                 'results after that point are not trustworthy')
    finally:
        shutil.rmtree(wt, ignore_errors=True)
        subprocess.run(['git', '-C', REPO, 'worktree', 'prune'],
                       capture_output=True)

    # ── DID THE SUBJECT MOVE UNDER US? ─────────────────────────────────────
    # Re-read the WORKING TREE, not the snapshot. If it changed during the run
    # the verdicts still stand -- they were measured against a real file -- but
    # the LINE NUMBERS no longer point at the gates they name, and the role
    # table name is the only durable identifier left. Saying so is the whole
    # difference between a stale report and a wrong one.
    now = io.open(os.path.join(REPO, SUBJECT), encoding='utf-8',
                  newline='').read()
    stale = hashlib.sha256(now.encode('utf-8')).hexdigest()[:12] != digest
    if stale:
        print('')
        print('  !! %s CHANGED DURING THIS RUN.' % SUBJECT.replace(os.sep, '/'))
        print('     The verdicts are valid for sha256 %s; the LINE NUMBERS are' % digest)
        print('     not valid for the file on disk now. Use the role-table names,')
        print('     or re-run against a quiet tree.')

    lb = [r for r in results if r['verdict'] == 'LOAD-BEARING']
    si = [r for r in results if r['verdict'] == 'SILENT']
    cn = [r for r in results if r['verdict'] == 'COULD-NOT-RUN']
    print('\n  LOAD-BEARING  %d' % len(lb))
    print('  SILENT        %d   <- redundant OR untested; this tool cannot tell'
          % len(si))
    print('  COULD-NOT-RUN %d   <- never counted as either' % len(cn))
    if si:
        print('\n  Each SILENT gate is a QUESTION, not a verdict. For each, ask:')
        print('  does removing it change BEHAVIOUR? If yes it is untested; if no')
        print('  it is redundant, and that should be written down where it sits.')
        for r in si:
            print('      %s  %s:%d' % (r['role_table'], SUBJECT.replace(os.sep, '/'),
                                       r['line']))
    if jsonout:
        io.open(jsonout, 'w', encoding='utf-8').write(
            json.dumps({'subject': SUBJECT.replace(os.sep, '/'),
                        'results': results}, indent=1))
        print('\n  wrote ' + jsonout)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
