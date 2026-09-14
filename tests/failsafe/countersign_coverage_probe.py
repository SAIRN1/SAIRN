"""The COUNTERSIGN half of the witnessing lock is untested by every suite.

Run: python tests/failsafe/countersign_coverage_probe.py     (report only, exit 0)

── WHAT THIS IS ─────────────────────────────────────────────────────────────
The independent review of item 83, run rather than read. It does not review
the two failsafe suites by reading them; it BREAKS THE LOCK, one refusal at a
time, and asks which suite notices.

── THE FINDING, MEASURED 2026-09-14 ────────────────────────────────────────
Every refusal on `api/sv-witness.js`'s `countersign` action can be deleted and
ALL THREE suites stay green -- `tests/failsafe/witness_atomicity.js` (14),
`tests/failsafe/witness_recovery.js` (14) and `api/sv-witness.test.js` (38).
Sixty-six arms over a DEA-relevant lock, and none of them enters that handler.

The sharpest one is SAME_PERSON. The lock's own comment at that line reads:

    A COUNTERSIGNATURE BY THE AUTHOR IS NOT A COUNTERSIGNATURE. This is the
    entire content of "two person", and without it the setting is a second
    click by the same hand.

That check can be removed and nothing on this platform goes red.

── WHY IT WAS MISSED, WHICH IS NOT AN OVERSIGHT ────────────────────────────
Item 83 asked two questions -- is the transition ATOMIC, and does the RECOVERY
work -- and answered both well, about `requireWitness()`. `requireWitness()` is
the SPEND path: the last gate before an irreversible write. `countersign` is a
different entry point on the same lock, reached over HTTP by a second person,
and nothing framed it as in scope. Pass three's own commit says so plainly --
*"the lock has TWO expiry checks (requireWitness and the HTTP confirm path).
These arms drive the first."* That disclosure was accurate; what nobody had
done was MEASURE what the second one costs.

── REPORT ONLY, AND EXIT 0, DELIBERATELY ───────────────────────────────────
This measures COVERAGE, not a defect in shipped behaviour: the lock is correct
today and every refusal is present. Failing a suite over it would block pushes
on somebody else's missing test. It is registered report-only so the runner
says it on every sweep until a countersign suite exists -- and the moment one
does, the MISSED list shrinks and this file says so without being edited.

── WHAT IT CANNOT SEE ──────────────────────────────────────────────────────
A mutation this cannot express. The list is hand-written, each anchor is
COUNTED rather than merely found, and an anchor that stops matching is REPORTED
as could-not-test rather than silently skipped -- a mutation that plants
nothing and is read as covered would be the same lie in the other direction.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

REPO = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True).stdout.strip()
LOCK = os.path.join('api', 'sv-witness.js')
SUITES = [os.path.join('tests', 'failsafe', 'witness_atomicity.js'),
          os.path.join('tests', 'failsafe', 'witness_recovery.js'),
          os.path.join('api', 'sv-witness.test.js')]

# Each entry: (what the mutation destroys, anchor, replacement).
MUTATIONS = [
    ('SAME_PERSON -- the author may countersign their own record',
     '      if (row.witness_employee_id === caller.employee_id) {',
     '      if (false) {'),
    ('ALREADY_COUNTERSIGNED -- a record may be countersigned twice',
     '      if (row.countersign_employee_id) {',
     '      if (false) {'),
    ('ALREADY_SPENT on the countersign path -- a spent token may be countersigned',
     "      if (row.spent_at) { res.status(409).json({ error: { code: 'ALREADY_SPENT'",
     "      if (false) { res.status(409).json({ error: { code: 'ALREADY_SPENT'"),
    ('EXPIRED on the countersign path -- an expired token may be countersigned',
     "      if (new Date(row.expires_at).getTime() <= Date.now()) {\n"
     "        res.status(409).json({ error: { code: 'EXPIRED',",
     "      if (false) {\n"
     "        res.status(409).json({ error: { code: 'EXPIRED',"),
    ('the countersign expiry BOUNDARY -- <= loosened to <',
     "      if (new Date(row.expires_at).getTime() <= Date.now()) {\n"
     "        res.status(409).json({ error: { code: 'EXPIRED',",
     "      if (new Date(row.expires_at).getTime() < Date.now()) {\n"
     "        res.status(409).json({ error: { code: 'EXPIRED',"),
    # NOT a countersign-only gap, and it is listed here because it was found by
    # the same pass. The recovery suite tests the window at TTL-1 and TTL+1 --
    # both sides of the boundary, neither ON it -- and `<=` and `<` agree
    # everywhere except at exactly expires_at. So the WINDOW LENGTH is proven
    # and the COMPARISON OPERATOR is not. One millisecond, in the fail-safe
    # direction, and one arm closes it.
    ('the SPEND-path expiry boundary -- <= loosened to <',
     '  if (new Date(row.expires_at).getTime() <= Date.now()) {\n'
     '    return { status: 409, body: { error: { code: \'WITNESS_EXPIRED\',',
     '  if (new Date(row.expires_at).getTime() < Date.now()) {\n'
     '    return { status: 409, body: { error: { code: \'WITNESS_EXPIRED\','),
]

# The control. If this one is not caught, the harness is broken and every
# MISSED below means nothing -- a probe that cannot detect a caught mutation
# reports total absence of coverage against any codebase at all.
CONTROL = ('requireWitness expiry disabled -- THE CONTROL, must be CAUGHT',
           '  if (new Date(row.expires_at).getTime() <= Date.now()) {\n'
           '    return { status: 409, body: { error: { code: \'WITNESS_EXPIRED\',',
           '  if (false) {\n'
           '    return { status: 409, body: { error: { code: \'WITNESS_EXPIRED\',')


def main():
    wt = tempfile.mkdtemp(prefix='sv-countersign-')
    shutil.rmtree(wt, ignore_errors=True)
    add = subprocess.run(['git', '-C', REPO, 'worktree', 'add', '-q', '--detach', wt, 'HEAD'],
                         capture_output=True, text=True)
    if add.returncode != 0:
        print('COULD NOT CHECK: no worktree -- nothing was measured. '
              'ZERO FINDINGS HERE IS NOT A CLEAN SWEEP.')
        print(add.stderr.strip()[:300])
        return 2
    try:
        for rel in [LOCK] + SUITES:
            shutil.copyfile(os.path.join(REPO, rel), os.path.join(wt, rel))
        orig = io.open(os.path.join(wt, LOCK), encoding='utf-8', newline='').read()

        def run(suite):
            r = subprocess.run(['node', os.path.join(wt, suite)], cwd=wt,
                               capture_output=True, text=True)
            return r.returncode

        baseline = [(os.path.basename(s), run(s)) for s in SUITES]
        if any(rc != 0 for _, rc in baseline):
            print('COULD NOT CHECK: a suite is RED before any mutation, so '
                  '"caught" would be meaningless.')
            for nm, rc in baseline:
                print('    %-28s exit %d' % (nm, rc))
            return 2

        def apply_and_run(anchor, repl):
            n = orig.count(anchor)
            if n != 1:
                return None, n
            io.open(os.path.join(wt, LOCK), 'w', encoding='utf-8',
                    newline='').write(orig.replace(anchor, repl, 1))
            try:
                return [nm for nm, rc in
                        [(os.path.basename(s), run(s)) for s in SUITES]
                        if rc != 0], n
            finally:
                io.open(os.path.join(wt, LOCK), 'w', encoding='utf-8',
                        newline='').write(orig)

        clabel, canchor, crepl = CONTROL
        caught_by, cn = apply_and_run(canchor, crepl)
        control_ok = bool(caught_by)

        rows, unreadable = [], []
        for label, anchor, repl in MUTATIONS:
            got, n = apply_and_run(anchor, repl)
            if got is None:
                unreadable.append((label, n))
                continue
            rows.append({'what': label, 'caught_by': got})
    finally:
        shutil.rmtree(wt, ignore_errors=True)
        subprocess.run(['git', '-C', REPO, 'worktree', 'prune'], capture_output=True)

    missed = [r for r in rows if not r['caught_by']]
    if '--json' in sys.argv:
        print(json.dumps({'control_caught': control_ok, 'rows': rows,
                          'unreadable': unreadable}, indent=1))
        return 0

    print('WITNESSING-LOCK MUTATION COVERAGE -- report only, nothing was changed')
    print('  suites asked : %s' % ', '.join(os.path.basename(s) for s in SUITES))
    print('  CONTROL (%s) : %s'
          % ('caught' if control_ok else 'NOT CAUGHT',
             ', '.join(caught_by or ['nothing'])))
    if not control_ok:
        print('')
        print('  THE CONTROL DID NOT BITE, SO EVERY LINE BELOW IS MEANINGLESS.')
        print('  A harness that cannot detect a caught mutation reports total')
        print('  absence of coverage against any codebase at all. Fix this first.')
        return 2
    print('')
    for r in rows:
        print('  %-9s %s' % ('CAUGHT' if r['caught_by'] else 'MISSED', r['what']))
    if unreadable:
        print('')
        print('  COULD NOT TEST -- the anchor no longer matches exactly once.')
        print('  Reported rather than skipped: a mutation that plants nothing')
        print('  and is read as covered is the same lie in the other direction.')
        for label, n in unreadable:
            print('    %d match(es): %s' % (n, label))
    print('')
    print('  %d of %d mutations are caught by NOTHING on this platform.'
          % (len(missed), len(rows)))
    print('  The lock is CORRECT today -- every refusal is present. What is')
    print('  missing is anything that would notice if one were removed, and the')
    print('  countersign action is where "two person" actually lives.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
