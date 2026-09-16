"""The negative control for tools/retry_backoff_check.py.

    python tests/retry_backoff_check_control.py

The tool reports ZERO retry loops across 322 source units. That is the most
suspicious possible result for a retry checker: a tool that found nothing looks
exactly like a tool that CAN find nothing. So this plants real retry loops into
REAL platform source and asserts the tool reports each one.

── MUTATED IN MEMORY, NOT ON DISK, AND THAT IS DELIBERATE ──────────────────
Every arm below reads a real tracked file, applies its mutation to the STRING,
and calls analyse() on the result. Nothing is written and nothing is restored,
so there is no window in which a tracked file is modified.

That is not squeamishness. On 2026-09-14 two probes on this platform ran in the
same second, each snapshotted a file the other had already mutated, and the
second restore reported byte-identical success over the first one's damage. A
probe that never writes cannot participate in that. The cost is that this does
not exercise the file-reading half of the tool -- `sources()` -- and arm 0 below
covers that separately by asserting the real sweep actually reaches real files.
"""
# REQUIREMENT: a retry policy actually backs off rather than retrying immediately, so a
#   failing dependency is not hammered by its own client
#
import io
import os
import subprocess
import sys

CONTROLS_FOR = ['tools/retry_backoff_check.py']

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))

import retry_backoff_check as R                                  # noqa: E402

FAILS = []


def arm(label, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + label
          + ('' if cond else '\n         ' + str(detail)[:400]))
    if not cond:
        FAILS.append(label)


def shapes(src):
    found, _unb = R.analyse(R.blank_noise(src))
    return found


# A real retry: the same url, no delay, no breaker. This is the shape the tool
# exists to find and the shape the platform currently does not contain.
PLANT_RETRY = '''
async function plantedRetry(url, headers) {
  let n = 3;
  while (n--) {
    const r = await fetch(url, { headers });
    if (r.ok) return r;
  }
  return null;
}
'''

PLANT_RETRY_WITH_BACKOFF = '''
async function plantedBackoff(url, headers) {
  let n = 3;
  while (n--) {
    const r = await fetch(url, { headers });
    if (r.ok) return r;
    await new Promise(function (res) { setTimeout(res, 250); });
  }
  return null;
}
'''


def main():
    # 0. THE SWEEP REALLY REACHES REAL FILES. Every arm below tests analyse();
    #    none of them would notice sources() returning an empty list, and an
    #    empty universe is the other way to report zero retries.
    srcs, bad = R.sources()
    names = [s[0] for s in srcs]
    arm('the sweep reaches real api/ files', 'api/audit-checkpoint.js' in names,
        names[:5])
    arm('...and real app HTML script blocks',
        any(n.startswith('stonedesk.html:') for n in names), names[:5])
    arm('...and nothing was unreadable', not bad, bad)
    arm('...and every unit brace-balances, so none was silently half-scanned',
        not [n for n, s in srcs if R.analyse(R.blank_noise(s))[1]],
        [n for n, s in srcs if R.analyse(R.blank_noise(s))[1]][:5])

    # 0b. THE 2026-09-16 MERGE, GUARDED. Two changes came in from
    #     tools/retry_policy_audit.py and both revert silently: a recursive
    #     walk can go back to two listdir calls, and a vocabulary entry can be
    #     dropped while every other arm keeps passing. Arm 0 above would not
    #     notice either -- it only asks whether the sweep reaches ANY api file.
    arm('the api/ walk is RECURSIVE -- api/agent/ is scanned',
        any(n.startswith('api/agent/') for n in names),
        'api/agent/poll.js holds an outbound fetch inside a while loop and was '
        'invisible to this tool until 2026-09-16')
    for sub in ('api/sairncash/', 'api/sairndental/', 'api/_resources/'):
        arm('...and so is ' + sub, any(n.startswith(sub) for n in names), sub)
    lib = [n for n in names if n.startswith('api/_lib/')]
    arm('...and api/_lib is scanned EXACTLY ONCE -- the old explicit block plus '
        'the walk would double every finding in it',
        len(lib) == len(set(lib)), sorted(set(x for x in lib if lib.count(x) > 1)))

    pats = [pat.pattern for pat in R.OUTBOUND]
    arm('an AI/agent call is an OUTBOUND call -- callClaude is in the vocabulary',
        any('callClaude' in x for x in pats), pats)
    arm('...and dispatchAgent', any('dispatchAgent' in x for x in pats), pats)
    arm('...and the four TRANSPORT patterns survived, so the merge ADDED rather '
        'than replaced',
        all(any(k in x for x in pats)
            for k in ('fetch', 'XMLHttpRequest', 'sairnHttp', 'from')), pats)

    # 1. PLANTED INTO REAL SOURCE, the tool must report it.
    for real in ('api/audit-checkpoint.js', 'api/_lib/courtlistener.js',
                 'api/sv-witness.js'):
        src = io.open(os.path.join(REPO, real), encoding='utf-8',
                      errors='replace').read()
        clean = [f for f in shapes(src) if f['shape'] == 'RETRY']
        arm('%s has no retry as it stands' % real, not clean, clean)

        got = [f for f in shapes(src + PLANT_RETRY) if f['shape'] == 'RETRY']
        arm('...and a retry planted into it IS reported',
            len(got) == 1 and not got[0]['delay'] and not got[0]['breaker'], got)

    # 2. THE OTHER DIRECTION. A planted retry that DOES back off must not be
    #    reported as bare -- without this, arm 1 is satisfied by a tool that
    #    calls every loop a finding.
    src = io.open(os.path.join(REPO, 'api', 'audit-checkpoint.js'),
                  encoding='utf-8', errors='replace').read()
    got = [f for f in shapes(src + PLANT_RETRY_WITH_BACKOFF)
           if f['shape'] == 'RETRY']
    arm('a planted retry WITH a delay is seen as a retry that backs off',
        len(got) == 1 and got[0]['delay'] is True, got)

    # 3. AND THE ITERATION IT ALREADY CONTAINS IS STILL NOT A FINDING while the
    #    planted retry is. Both answers, in one file, at the same time -- which
    #    is the only thing that says the tool DISCRIMINATES rather than leans.
    both = shapes(src + PLANT_RETRY)
    arm('the file\'s real pagination still reads ITERATION alongside it',
        any(f['shape'] == 'ITERATION' for f in both)
        and any(f['shape'] == 'RETRY' for f in both),
        [(f['line'], f['shape']) for f in both])

    # 4. THE BREAKER COUNT IS A MEASUREMENT, NOT A CONSTANT. If this ever stops
    #    returning a list, the headline finding is being asserted rather than read.
    imp = R.breaker_importers()
    arm('breaker_importers() returns a list (0 today, and that is the finding)',
        isinstance(imp, list), imp)

    # 5. THE BLIND LOCK REFUSES WHEN THE CRITERIA ARE BROKEN.
    real_fn = R.varies_across_iterations
    R.varies_across_iterations = lambda h, b, a: True    # everything is iteration
    try:
        rc = R.run_fixtures()
    finally:
        R.varies_across_iterations = real_fn
    arm('criteria stubbed to "always iteration" makes --fixtures REFUSE',
        rc == 2, 'exit %r' % rc)
    arm('...and the unmodified criteria pass their own lock',
        R.run_fixtures() == 0)

    # 6. THE "Report only." CLAIM, ADDED 2026-09-16 BY A FIRST ARTICLE
    #    INSPECTION (item 47), by Hank, on a tool written by another session.
    #    It is the THIRD tool in a row inspected that day to state REPORT ONLY
    #    in its own header and check it nowhere -- after Fourth's three-tool
    #    sweep found the same thing, and after tools/dispatch_state.py the same
    #    hour. The exit-code contract is already covered by arm 5 above
    #    (a broken blind lock REFUSES with 2), so this is the half that had
    #    nothing, not a second finding about the same gap.
    #
    #    REPORT ONLY means it never MUTATES -- not that it never exits 1, which
    #    a report-only check registered with by_exit is expected to do. So the
    #    arms ask about mutation, from two structurally different directions:
    #    the SOURCE (no writer is written down) and a RUN (nothing moved).
    import ast as _ast
    _SUBJECT = os.path.join(REPO, 'tools', 'retry_backoff_check.py')
    _src = io.open(_SUBJECT, encoding='utf-8').read()
    _writes = []
    for _n in _ast.walk(_ast.parse(_src)):
        if not (isinstance(_n, _ast.Call) and (
                (isinstance(_n.func, _ast.Name) and _n.func.id == 'open')
                or (isinstance(_n.func, _ast.Attribute)
                    and _n.func.attr == 'open'))):
            continue
        # The MODE argument only. Scanning every string argument flags
        # `errors='replace'` -- an 'a' in a careful read -- which is how the
        # first version of this same predicate produced four false hits on
        # this very file.
        _m = _n.args[1] if len(_n.args) > 1 else None
        for _k in _n.keywords:
            if _k.arg == 'mode':
                _m = _k.value
        if (isinstance(_m, _ast.Constant) and isinstance(_m.value, str)
                and any(c in _m.value for c in 'wax+')):
            _writes.append(_ast.dump(_n)[:100])
    arm('6 REPORT ONLY: no write-mode open() anywhere in the source', not _writes,
        _writes[:2])
    for _w in ('json.dump(', 'shutil.', 'os.remove', 'os.rename', 'os.makedirs',
               'os.mkdir', 'subprocess.run', 'subprocess.call'):
        arm('6 ...and no %s' % _w, _w not in _src, _w)

    def _tree():
        return subprocess.run(
            ['git', 'status', '--porcelain'], cwd=REPO, capture_output=True,
            text=True, encoding='utf-8', errors='replace').stdout

    # ONE RUN, not one per subcommand. The full sweep reads every app HTML and
    # takes real time; three of them turned this control into a two-minute
    # file, and a control nobody will wait for is a control that gets skipped.
    # The source arms above cover the other entry points -- a writer cannot be
    # present on one code path and absent from the file.
    _before = _tree()
    subprocess.run([sys.executable, _SUBJECT], cwd=REPO, capture_output=True,
                   text=True, encoding='utf-8', errors='replace',
                   env=dict(os.environ, PYTHONIOENCODING='utf-8'))
    # IF THIS ARM IS RED, CHECK WHETHER YOU EDITED THE TREE WHILE IT RAN.
    # It compares `git status --porcelain` across a sweep that takes minutes, so
    # ANY change to the working tree in that window -- your own commit, a
    # regenerated document -- is a true observation and a false accusation. It
    # went red exactly once for that reason on 2026-09-16 and green on a quiet
    # tree immediately after. Recorded here so the next reader does not chase it.
    arm('6 ...and a real run leaves the WHOLE WORKING TREE unchanged',
        _tree() == _before,
        'the tool mutated the repo -- OR the tree was edited while this ran')

    # 7. THE OTHER TWO THIRDS OF THE EXIT CONTRACT, added by the same First
    #    Article Inspection. The header states "Exit 0 clean, 1 finding, 2
    #    could-not-run"; arm 5 above covered the 2 and NOTHING covered the 0 or
    #    the 1. Every arm in this file works at the analyse() layer, so main()
    #    -- the function whose return value IS the contract -- had never been
    #    called.
    #
    #    DRIVEN THROUGH THE REAL main() WITH sources() STUBBED, not through a
    #    subprocess. The real sweep reads every app HTML and takes minutes; a
    #    control that slow is one that gets skipped. Stubbing the source list is
    #    the seam that makes the exit contract testable in milliseconds, and it
    #    is the SAME main(), so the mapping from findings to exit code is the
    #    real one.
    _real_sources = R.sources
    _real_importers = R.breaker_importers
    CLEAN_UNIT = ('fixture_clean.js',
                  'async function f(u){ const r = await fetch(u); return r; }\n')
    BARE_RETRY = ('fixture_bare.js',
                  'async function f(u, h) {\n'
                  '  let n = 3;\n'
                  '  while (n--) {\n'
                  '    const r = await fetch(u, { headers: h });\n'
                  '    if (r.ok) return r;\n'
                  '  }\n'
                  '  return null;\n'
                  '}\n')
    # UNCLEAR is produced when the outbound call inside a loop has NO arguments,
    # so the tool cannot tell what is being called again. Its own header says
    # "Where it cannot tell, it says UNCLEAR and that is not a pass" -- and that
    # branch was reachable and exercised by nothing.
    UNCLEAR_UNIT = ('fixture_unclear.js',
                    'async function f() {\n'
                    '  let n = 3;\n'
                    '  while (n--) {\n'
                    '    const r = await fetch();\n'
                    '    if (r) return r;\n'
                    '  }\n'
                    '}\n')
    import contextlib

    def _rc(argv=None):
        """main()'s exit code, with its report swallowed."""
        with contextlib.redirect_stdout(io.StringIO()):
            return R.main(argv or [])

    try:
        # EXIT 0 needs the BREAKER stubbed as well, and that is itself worth
        # recording: on the real repo today `breaker_importers()` returns an
        # empty list and main() adds "the only breaker on the platform cannot
        # fire" to its findings. So this tool CANNOT exit 0 against the live
        # tree, by design, and an arm that did not stub it would have been
        # asserting the platform's state rather than the tool's contract.
        R.breaker_importers = lambda: ['api/fixture-importer.js']
        R.sources = lambda: ([CLEAN_UNIT], [])
        arm('7 EXIT 0: no bare retry, nothing UNCLEAR and a breaker with an '
            'importer exits CLEAN', _rc() == 0)
        R.sources = lambda: ([BARE_RETRY], [])
        arm('7 EXIT 1: a bare retry -- a loop, an outbound call, no delay and '
            'no breaker -- is a FINDING', _rc() == 1)
        arm('7 ...and --json returns the SAME code on the same input',
            _rc(['--json']) == _rc([]))

        # THE UNCLEAR PATH, which nothing exercised before this inspection.
        R.sources = lambda: ([UNCLEAR_UNIT], [])
        _found, _ = R.analyse(R.blank_noise(UNCLEAR_UNIT[1]))
        arm('7 UNCLEAR: an outbound call with NO arguments inside a loop reads '
            'UNCLEAR, because the tool cannot tell what is called again',
            [f['shape'] for f in _found] == ['UNCLEAR'],
            [(f['line'], f['shape']) for f in _found])
        arm('7 ...and UNCLEAR IS NOT A PASS -- it is COULD NOT RUN (2), not a '
            'finding and not clean', _rc() == 2)
        arm('7 ...and --json agrees about THAT too, which it did not before '
            'this inspection: it had its own rule and called UNCLEAR a finding',
            _rc(['--json']) == 2)

        # THE HEADLINE FINDING MUST REACH A MACHINE-READABLE CALLER. The json
        # path never looked at breaker_importers(), so on the real repo it
        # exited 0 while the text run did not -- the tool's own headline
        # invisible to anything wired to --json.
        R.breaker_importers = lambda: []
        R.sources = lambda: ([CLEAN_UNIT], [])
        arm('7 A PLATFORM WITH NO BREAKER IMPORTER IS A FINDING IN BOTH MODES',
            (_rc(), _rc(['--json'])) == (1, 1),
            (_rc(), _rc(['--json'])))

        R.breaker_importers = lambda: ['api/fixture-importer.js']
        R.sources = lambda: ([], [])
        arm('7 EXIT 2: an empty source universe is COULD NOT RUN, not a clean '
            'sweep over nothing', _rc() == 2)
    finally:
        R.sources = _real_sources
        R.breaker_importers = _real_importers

    print('\n%d failure(s)' % len(FAILS))
    return 1 if FAILS else 0


if __name__ == '__main__':
    sys.exit(main())
