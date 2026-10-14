#!/usr/bin/env python
# OWNER: cc
# written 2026-10-13, batch b7, queue item 3
"""Does `save_reviews()` still LOSE A WRITER when two land at once on Windows?

    python tests/run_save_reviews_retry_probe.py
    python tests/run_save_reviews_retry_probe.py --iterations 400

Exit 0 all arms pass, 1 an arm failed, 2 COULD NOT RUN.

THE DEFECT, routed by cody in docs/2026-10-13-cody-b6-routed-to-cc.md PART 1.
`tools/tier_a_review_gate.py:save_reviews()` writes a `mkstemp` temp file and
then `os.replace(tmp, REVIEWS)`. On POSIX that is `rename(2)` and a concurrent
rename onto the same destination is safe. ON WINDOWS `os.replace` is
`MoveFileEx(MOVEFILE_REPLACE_EXISTING)` and fails `ERROR_ACCESS_DENIED`
(`WinError 5`) while the destination is held open -- INCLUDING by another
`MoveFileEx` in flight on the same target. cody measured 305 of 400 iterations
raising, and called it what it is: not a flake, the normal case on this
platform.

SAFETY HELD AND LIVENESS DID NOT, which is why nothing looked wrong for as
long as the arm existed. No reader ever saw half a file. What fails is that one
of two concurrent writers ERRORS INSTEAD OF COMPLETING -- and `--open`,
`--discharge` and `--reseat-shas` all end in `save_reviews`, so two sessions
landing together means one caller did its work and its record was never
written.

── FAILING-FIRST, AND MEASURED IN THAT ORDER ───────────────────────────────
Arm 1 was driven against UNPATCHED `save_reviews` before the retry existed and
FAILED, with the raw log in this batch's scratchpad. That is the only sequence
in which a green arm means anything here: the race is probabilistic, so an arm
written after the fix could be passing because the race never fired.

    unpatched, 2 writers + tight reader, 400 saves : 335 PermissionError
    patched,   2 writers + tight reader, 400 saves : 3   -- DISCLOSED, arm 1c
    patched,   2 writers, 400 saves                : 0   -- arm 1

THE TWO PATCHED NUMBERS ARE BOTH REPORTED AND THAT IS DELIBERATE. A reader
reopening the destination in a tight loop holds it open far more of the time
than any real caller, and it can starve a BOUNDED retry -- so the second
number is disclosed with a ceiling rather than asserted to zero. One combined
figure here would be the fabricated half of a two-number result (convention 2).

── ARMS, AND WHY EACH IS SEPARATE ──────────────────────────────────────────
1. THE RACE COMPLETES. Two writers, N saves each, zero `PermissionError`
   escaping. This is the routed defect and the only arm that needs the race.
2. SAFETY IS STILL INTACT. The file parses as ONE JSON document after every
   single save. A retry that fixed liveness by widening the write window would
   pass arm 1 and break the property the atomic write exists for.
3. EXHAUSTION RE-RAISES. With `os.replace` stubbed to fail forever, the call
   RAISES rather than returning quietly. A retry that gives up silently turns a
   lost record into a silent one, which is worse than the defect.
4. A NON-PermissionError IS NOT RETRIED. `OSError(ENOSPC)` escapes on the
   FIRST attempt -- retrying a full disk twenty times then raising is strictly
   worse than raising once, and `except OSError` is how that gets written.

── WHAT THIS PROBE CANNOT SEE ──────────────────────────────────────────────
  * POSIX. The retry branch is unreachable there, so this platform cannot show
    that no behaviour changed on another -- stated, not assumed away. The
    arm-4 shape is what would catch an `except` that caught something else.
  * the read-modify-write race. Two concurrent `--open` calls can still LOSE a
    record because both read before either writes. Untouched here, and
    arm 12 of `tests/run_tier_a_review_gate_probe.py` still expects `1`.
  * THE REAL `docs/tier-a-reviews.json` IS NEVER WRITTEN. `REVIEWS` is pointed
    at a throwaway file for the whole run and the path is printed.
"""
import io
import json
import os
import shutil
import sys
import tempfile
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
TOOLS = os.path.join(REPO, 'tools')
SUBJECT = os.path.join(TOOLS, 'tier_a_review_gate.py')

if not os.path.isfile(SUBJECT):
    print('COULD NOT RUN: %s is absent, so NOTHING WAS TESTED.' % SUBJECT)
    sys.exit(2)

sys.path.insert(0, TOOLS)
try:
    import tier_a_review_gate as gate
except Exception as exc:                                         # noqa: BLE001
    print('COULD NOT RUN: tier_a_review_gate would not import (%s).' % exc)
    sys.exit(2)

ITER = 200
if '--iterations' in sys.argv:
    ITER = int(sys.argv[sys.argv.index('--iterations') + 1])

arms = []
tmp = tempfile.mkdtemp(prefix='srr-probe-')
real_reviews = gate.REVIEWS
print('save_reviews retry probe')
print('  subject        : tools/tier_a_review_gate.py save_reviews()')
print('  throwaway file : %s' % os.path.join(tmp, 'tier-a-reviews.json'))
print('  the REAL docs/tier-a-reviews.json is NOT written by this run')
print('  iterations     : %d per thread, 2 threads' % ITER)
print('')

try:
    gate.REVIEWS = os.path.join(tmp, 'tier-a-reviews.json')

    def payload(tag, n):
        return {'records': [{'id': '%s-%d' % (tag, i), 'resource': 'x',
                             'note': 'padding so the file is not trivial'}
                            for i in range(n)]}

    # ── THE RACE, RUN TWICE, AND THE TWO RUNS ARE NOT THE SAME QUESTION ────
    # PHASE A is the routed defect: two concurrent WRITERS, which is what
    # `--open` and `--discharge` from two sessions actually looks like.
    # PHASE B adds a reader in a TIGHT LOOP, which holds the destination open
    # far more of the time than any real caller does. It is kept because it is
    # the only way to drive the safety property -- and its liveness number is
    # DISCLOSED rather than asserted to zero, because a pathological reader can
    # starve a bounded retry and pretending otherwise would be the fabricated
    # half of a two-number result (convention 2).
    def race(with_reader):
        errors = []
        unparseable = []
        stop = threading.Event()
        done = []

        def writer(tag, size):
            for _i in range(ITER):
                try:
                    gate.save_reviews(payload(tag, size))
                except Exception as exc:                         # noqa: BLE001
                    errors.append('%s: %r' % (tag, exc))
            done.append(tag)
            if len(done) == 2:
                stop.set()

        def reader():
            # It must see the old file or the new one -- never two JSON
            # documents concatenated, which is the corruption the atomic write
            # exists to stop.
            while not stop.is_set():
                try:
                    with io.open(gate.REVIEWS, encoding='utf-8') as fh:
                        json.loads(fh.read())
                except ValueError as exc:
                    unparseable.append(repr(exc))
                except OSError:
                    pass        # a replace in flight; not the property at test

        # Different sizes, because the corruption cody measured in 2026-09-21
        # came from a SHORT write leaving the tail of a LONG one behind.
        threads = [threading.Thread(target=writer, args=('a', 40)),
                   threading.Thread(target=writer, args=('b', 400))]
        if with_reader:
            threads.append(threading.Thread(target=reader))
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        perm = [e for e in errors if 'PermissionError' in e
                or 'WinError 5' in e]
        return perm, [e for e in errors if e not in perm], unparseable

    gate.save_reviews(payload('seed', 3))
    perm_a, other_a, _ = race(with_reader=False)
    perm_b, other_b, unparseable = race(with_reader=True)
    print('  PHASE A  2 writers            : %d PermissionError in %d saves'
          % (len(perm_a), ITER * 2))
    print('  PHASE B  2 writers + 1 tight reader : %d PermissionError in %d '
          'saves  (DISCLOSED, see arm 1c)' % (len(perm_b), ITER * 2))
    print('')

    arms.append(('ARM 1 (the routed defect): %d concurrent saves by two '
                 'writers and NOT ONE lost to PermissionError' % (ITER * 2),
                 len(perm_a), 0))
    arms.append(('ARM 1b: no OTHER exception escaped either',
                 (other_a, other_b), ([], [])))
    # The honest version of the second phase: a bound, with the unpatched
    # measurement beside it, rather than a zero that is not true.
    arms.append(('ARM 1c (DISCLOSED, not zero): under a reader holding the '
                 'destination open in a tight loop, losses stay under 5%% of '
                 'saves -- unpatched the SAME phase measured 335/400 (84%%), '
                 'log in this batch\'s scratchpad. A bounded retry CAN be '
                 'starved by a pathological reader and this says so rather '
                 'than asserting a zero that is not true.',
                 len(perm_b) <= max(1, (ITER * 2) // 20), True))
    arms.append(('ARM 2 (safety, which held before the fix and must still): a '
                 'racing reader never saw a half-written or doubled file',
                 unparseable, []))
    arms.append(('ARM 2b: the file parses as ONE document at the end',
                 isinstance(json.load(io.open(gate.REVIEWS,
                                              encoding='utf-8')), dict), True))

    # ── ARM 3: exhaustion RE-RAISES ─────────────────────────────────────────
    keep = os.replace
    calls = []
    try:
        def always_denied(src, dst):
            calls.append(src)
            raise PermissionError(13, 'stubbed WinError 5', dst)
        os.replace = always_denied
        raised = None
        try:
            gate.save_reviews(payload('exhaust', 2))
        except PermissionError as exc:
            raised = exc
        except Exception as exc:                                 # noqa: BLE001
            raised = exc
    finally:
        os.replace = keep
    arms.append(('ARM 3: a replace that fails FOREVER raises PermissionError '
                 'rather than returning quietly -- a silent give-up turns a '
                 'lost record into an invisible one',
                 isinstance(raised, PermissionError), True))
    arms.append(('ARM 3b: it retried more than once before giving up (a cap, '
                 'not a single attempt)', len(calls) > 1, True))
    arms.append(('ARM 3c: and the cap is BOUNDED -- an unbounded retry turns a '
                 'deadlock into a hang (PR 1.12)', len(calls) < 1000, True))
    leftover = [n for n in os.listdir(tmp) if '.tmp-' in n]
    arms.append(('ARM 3d: the temp file was cleaned up even though the write '
                 'failed, so docs/ does not fill with orphans', leftover, []))

    # ── ARM 4: a non-PermissionError is NOT retried ─────────────────────────
    keep = os.replace
    calls = []
    try:
        def no_space(src, dst):
            calls.append(src)
            raise OSError(28, 'No space left on device', dst)
        os.replace = no_space
        raised = None
        try:
            gate.save_reviews(payload('enospc', 2))
        except Exception as exc:                                 # noqa: BLE001
            raised = exc
    finally:
        os.replace = keep
    arms.append(('ARM 4: OSError(ENOSPC) escapes on the FIRST attempt -- '
                 '`except OSError` would retry a full disk twenty times and '
                 'then raise anyway',
                 (len(calls), isinstance(raised, OSError),
                  isinstance(raised, PermissionError)), (1, True, False)))
finally:
    gate.REVIEWS = real_reviews
    shutil.rmtree(tmp, ignore_errors=True)

passed = 0
for name, got, want in arms:
    ok = got == want
    passed += ok
    print('  %-4s %s' % ('PASS' if ok else 'FAIL', name))
    if not ok:
        print('       wanted %r' % (want,))
        print('       got    %r' % (got,))
print('save_reviews retry probe: %d/%d arm(s) pass' % (passed, len(arms)))
sys.exit(0 if passed == len(arms) else 1)
