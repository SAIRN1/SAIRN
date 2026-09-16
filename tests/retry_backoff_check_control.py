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

    print('\n%d failure(s)' % len(FAILS))
    return 1 if FAILS else 0


if __name__ == '__main__':
    sys.exit(main())
