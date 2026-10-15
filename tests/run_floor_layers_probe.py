#!/usr/bin/env python
# OWNER: cody
# written 2026-10-15, batch b16, item 2
# REQUIREMENT: the three layers b12 added to the test-file floor in
#   tools/run_all_tests.py must each have an arm that FAILS when the layer is
#   removed. The ratchet must read the pinned floor rather than the last-resort
#   literal; the raise must never lift the floor above the number git actually
#   TRACKS, because an untracked fixture would otherwise push the floor above
#   the real tree and fail the NEXT run for a reason unrelated to the code; and
#   `behind` must sit inside the hook's early-return condition rather than only
#   in a line further down, because a clean tree whose floor has gone stale
#   returns before any line is built.
r"""Arms for the three test-file-floor layers cc measured as UNPROVEN.

    python tests/run_floor_layers_probe.py

Exit 0 every arm passes, 1 an arm FAILED, 3 COULD NOT RUN / UNPROVEN.

── WHY THIS FILE EXISTS, AND IT IS NOT THAT A PROBE WAS WRONG ──────────────
docs/ABLATION-RECORDS.md FINDING 2: cc removed each of the three layers from
tools/run_all_tests.py and ran cody's tests/run_all_tests_floor_probe.py
against each mutant. All three stayed GREEN:

    ratchet                probe exit 0  STILL GREEN -- UNPROVEN
    tracked-intersection   probe exit 0  STILL GREEN -- UNPROVEN
    silence-breaking       probe exit 0  STILL GREEN -- UNPROVEN

That probe predates b12 and tests the shrinking-suite floor, that
MIN_TEST_FILES is defined exactly once, and that both bodies compare against
it. IT WAS NEVER ASKED ABOUT THE RATCHET. So the three layers had no arm
anywhere, and `tests/` is cody's, so cc routed them rather than writing them.

── tracked-intersection IS FIRST BECAUSE IT IS THE URGENT ONE ──────────────
FINDING 2b, and cc had to contaminate the harness to show it: with the
intersection removed, the ratchet counted the floor probe's five UNTRACKED
fixture files and wrote a floor of 812, then 813, against a real 808 -- the
same 807-against-802 shape the layer exists to stop. And cody's probe still
exited 0 ON THE RUN THAT DID IT. The harm lands on the NEXT run, where the
floor now sits above the tree and the probe fails for a reason that has
nothing to do with the code under test.

    So the verdict is not "unarmed". It is UNARMED IN-RUN AND DESTRUCTIVE
    ACROSS RUNS, and arm T2 below is the across-runs half specifically.

── NOTHING HERE WRITES tools/ OR THE REAL FLOOR FILE ───────────────────────
tools/ is cc's. Every arm drives the module's own functions with `_FLOOR_PATH`
pointed at a TEMP file and the tracked-count reader stubbed, then restores both
in a `finally`. The real docs/test-file-floor.json is read ONCE, to assert the
shipped value is sane, and never written -- cc's own harness poisoned that file
and changed a later layer's verdict, which is recorded in FINDING 2b and is the
reason this file touches it not at all.

── ARM S IS STRUCTURAL AND SAYS SO ─────────────────────────────────────────
The silence-breaking layer lives inside a function that calls _run() over every
discovered test file, so driving it behaviourally means running the whole suite
per arm. Arm S therefore asserts the AST SHAPE of the early return -- that
`behind` is inside the `if ... : return 0` test, not merely assigned nearby.
That is weaker than a behavioural drive and is labelled so. It is NOT a string
match: a text anchor on that condition would break on re-wrapping and has
already done so elsewhere in this repo, which is why it is parsed.
"""
import ast
import io
import json
import os
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# ── ONE INJECTION POINT, never set on an ordinary run ─────────────────────
# The ablation points this at a MUTATED COPY of the tool, so each layer's
# removal can be driven without writing tools/ -- which is cc's.
# THE FIRST SPELLING OF THE ABLATION DID NOT ABLATE ANYTHING, and that is
# worth recording here rather than in a log that expires: it shadowed tools/
# with PYTHONPATH, and this file's own `sys.path.insert(0, REPO/tools)` below
# won, so every "mutant" run imported the REAL tool and all three layers
# reported CAUGHT=no against arms that were fine. An ablation harness that
# cannot actually remove the fix reports the arms as broken and the fix as
# unnecessary, in one stroke.
TOOL = os.environ.get('SAIRN_B16_RUN_ALL_TESTS') \
    or os.path.join(REPO, 'tools', 'run_all_tests.py')
FLOOR_DOC = os.path.join(REPO, 'docs', 'test-file-floor.json')

fails = []
unproven = []


def ok(name):
    print('  ok   ' + name)


def bad(name, detail=''):
    fails.append(name)
    print('  FAIL ' + name + ('\n         ' + str(detail)[:420] if detail else ''))


def cannot(name, why):
    unproven.append(name)
    print('  UNPROVEN ' + name + '\n         ' + str(why)[:400])


def could_not_run(why):
    print('COULD NOT RUN: %s Nothing was verified.' % why)
    sys.exit(3)


if not os.path.isfile(TOOL):
    could_not_run('%s does not exist.' % TOOL)
# tools/ stays on the path for the tool's OWN sibling imports; the module under
# test is loaded from TOOL by path, so an injected copy really is the one
# driven rather than being shadowed by this insert.
sys.path.insert(0, os.path.join(REPO, 'tools'))
try:
    import importlib.util
    _spec = importlib.util.spec_from_file_location('run_all_tests_under_test',
                                                   TOOL)
    R = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(R)
except Exception as exc:                                        # noqa: BLE001
    could_not_run('%s would not import (%s).' % (TOOL, exc))

for fn in ('_read_floor', 'raise_floor', '_tracked_test_files'):
    if not hasattr(R, fn):
        could_not_run('tools/run_all_tests.py no longer exposes %s(), so these '
                      'arms cannot drive the layers through their own '
                      'functions.' % fn)

print('the three test-file-floor layers -- criteria 2026-10-15.1')
print('subject: tools/run_all_tests.py (READ and DRIVEN, never written)')
print('fixtures: a temp floor file per arm; the real '
      'docs/test-file-floor.json is never written\n')


class floor_fixture(object):
    """Point the module's floor path at a temp file holding `value`.

    PER ARM, and restored in a finally. cc's own harness restored the TOOL and
    left the FLOOR FILE poisoned, which changed a later layer's verdict between
    runs -- FINDING 2b. An ablation that leaves its subject's state behind has
    contaminated every measurement after it.
    """

    def __init__(self, value):
        self.value = value

    def __enter__(self):
        self.dir = tempfile.mkdtemp(prefix='floor-layers-')
        self.path = os.path.join(self.dir, 'test-file-floor.json')
        io.open(self.path, 'w', encoding='utf-8', newline='\n').write(
            json.dumps({'floor': self.value, 'how': 'fixture'}, indent=2) + '\n')
        self.saved = R._FLOOR_PATH
        R._FLOOR_PATH = self.path
        return self

    def read_back(self):
        return json.loads(io.open(self.path, encoding='utf-8').read())['floor']

    def __exit__(self, *exc):
        R._FLOOR_PATH = self.saved
        try:
            os.unlink(self.path)
            os.rmdir(self.dir)
        except OSError:
            pass
        return False


LIT = getattr(R, '_MIN_TEST_FILES_FLOOR', None)
if not isinstance(LIT, int):
    could_not_run('_MIN_TEST_FILES_FLOOR is not an int, so "above the '
                  'last-resort literal" has no meaning here.')

# ── T. THE TRACKED INTERSECTION -- THE URGENT ONE ──────────────────────────
print('T. tracked-intersection: the floor may never rise above what git TRACKS')
TRACKED = LIT + 10
INFLATED = TRACKED + 5          # as if five untracked fixtures were counted

_saved_tracked = R._tracked_test_files
try:
    R._tracked_test_files = lambda paths=None: (TRACKED, '')
    with floor_fixture(LIT + 1) as fx:
        got, note = R.raise_floor(INFLATED)
        on_disk = fx.read_back()
        # T1 -- IN-RUN: the value the raise reports and writes is the TRACKED
        # count, not the inflated working-tree count.
        if got == TRACKED and on_disk == TRACKED:
            ok('T1 the raise is CLAMPED to the tracked count: asked for %d with '
               '%d tracked, wrote %d' % (INFLATED, TRACKED, on_disk))
        else:
            bad('T1 the raise must be CLAMPED to the tracked count',
                'asked for %d with %d tracked -> returned %r, file holds %r. '
                'An untracked fixture can push the floor above the real tree, '
                'which is FINDING 2b exactly: cc measured 812 then 813 against '
                'a real 808. note=%r' % (INFLATED, TRACKED, got, on_disk, note))
        # T2 -- ACROSS RUNS, which is the half that makes this destructive
        # rather than merely unarmed. Whatever the raise did, a SUBSEQUENT read
        # must not hand back a floor above the tracked tree, because the next
        # run compares its discovered count against it and fails for a reason
        # that has nothing to do with the code under test.
        later, _n = R._read_floor()
        if later <= TRACKED:
            ok('T2 ACROSS RUNS: a later read of the floor is %d, still <= the '
               '%d files git tracks, so the next run cannot fail against a '
               'floor above its own tree' % (later, TRACKED))
        else:
            bad('T2 ACROSS RUNS the floor must not be left above the tracked '
                'tree',
                'a later _read_floor() returned %d with only %d tracked. THIS '
                'IS THE DESTRUCTIVE HALF: the run that does it still exits 0, '
                'and the NEXT run reports "discovered (%d) >= MIN_TEST_FILES '
                '(%d)" and fails for an unrelated reason.'
                % (later, TRACKED, TRACKED, later))

    # T3 -- THE PAIRED POSITIVE. Clamping must not mean "never rises": a
    # genuine rise within the tracked count has to land, or T1 is satisfied by
    # a ratchet that is simply broken.
    with floor_fixture(LIT + 1) as fx2:
        want = TRACKED - 3
        got2, _n2 = R.raise_floor(want)
        if got2 == want and fx2.read_back() == want:
            ok('T3 PAIRED POSITIVE: a rise WITHIN the tracked count still '
               'lands (%d) -- the clamp is not a ratchet that never moves'
               % want)
        else:
            bad('T3 a rise within the tracked count must still land',
                'asked %d with %d tracked -> %r, file %r'
                % (want, TRACKED, got2, fx2.read_back()))

    # T4 -- FAIL CLOSED. If the tracked count cannot be measured the floor must
    # NOT be raised from the working-tree count alone (PR 1.11: could-not-run
    # is a third state, never folded into a pass).
    R._tracked_test_files = lambda paths=None: (None, 'stubbed as unmeasurable')
    with floor_fixture(LIT + 1) as fx3:
        got3, note3 = R.raise_floor(INFLATED)
        if got3 is None and fx3.read_back() == LIT + 1 and 'NOT ratcheted' in (note3 or ''):
            ok('T4 FAIL CLOSED: with the tracked count UNMEASURABLE the floor '
               'is not raised at all, and the reason is stated')
        else:
            bad('T4 an unmeasurable tracked count must not raise the floor',
                'returned %r, file holds %r, note=%r'
                % (got3, fx3.read_back(), note3))
finally:
    R._tracked_test_files = _saved_tracked

# ── R. THE RATCHET ─────────────────────────────────────────────────────────
print('\nR. ratchet: the floor is READ from the pin, not the hardcoded literal')
with floor_fixture(LIT + 7) as fx:
    got, note = R._read_floor()
    if got == LIT + 7:
        ok('R1 a pinned floor ABOVE the literal is the one used (%d, not the '
           'last-resort %d)' % (got, LIT))
    else:
        bad('R1 the pinned floor must be the one used',
            'pin said %d, literal is %d, _read_floor() returned %d. If this is '
            'the literal, the ratchet layer is gone and the floor is back to a '
            'hand-maintained number -- which sat at 370 against a real 802.'
            % (LIT + 7, LIT, got))

# R2 -- THE REFUSAL DIRECTION. A pin BELOW the literal must not lower the
# floor, and must say so: a ratchet that can be edited downward is not one.
with floor_fixture(max(1, LIT - 50)) as fx:
    got, note = R._read_floor()
    if got == LIT and note:
        ok('R2 a pin BELOW the literal is REFUSED and the floor stays at %d, '
           'with the reason stated' % LIT)
    else:
        bad('R2 a pin below the literal must be refused with a reason',
            'returned %d note=%r' % (got, note))

# R3 -- the module constant and the file must AGREE on the shipped tree. This
# is the one arm that reads the real pin, and it only reads it.
#
# IT IS ABOUT THE SHIPPED TOOL, SO IT IS NOT APPLICABLE TO AN INJECTED COPY,
# and that distinction was paid for: a copy computes its own `_FLOOR_PATH`
# relative to its own location, so it cannot find docs/test-file-floor.json,
# falls back to the literal, and R3 FAILED on an unmutated copy -- which made
# the whole ablation refuse to start with "the baseline copy is not green".
# An arm that cannot hold under the harness its own ablation needs is reported
# as NOT APPLICABLE rather than as a failure or, worse, quietly dropped.
SHIPPED_TOOL = os.path.join(REPO, 'tools', 'run_all_tests.py')
if os.path.abspath(TOOL) != os.path.abspath(SHIPPED_TOOL):
    print('  --   R3 NOT APPLICABLE: the tool under test is an injected copy '
          '(%s), whose _FLOOR_PATH cannot resolve docs/test-file-floor.json. '
          'Neither a pass nor a failure.' % os.path.basename(
              os.path.dirname(TOOL)))
elif True:
  try:
    shipped = json.loads(io.open(FLOOR_DOC, encoding='utf-8').read())['floor']
  except Exception as exc:                                        # noqa: BLE001
    cannot('R3 the shipped pin agrees with the module constant',
           'docs/test-file-floor.json could not be read (%s), so agreement '
           'could not be checked. Not a pass.' % exc)
  else:
    if R.MIN_TEST_FILES == shipped:
        ok('R3 MIN_TEST_FILES (%d) is the SHIPPED pin, so the constant really '
           'comes from the ratchet rather than the literal' % shipped)
    elif shipped < LIT and R.MIN_TEST_FILES == LIT:
        ok('R3 the shipped pin (%d) is below the literal and the constant is '
           'correctly the literal (%d)' % (shipped, LIT))
    else:
        bad('R3 MIN_TEST_FILES must come from the shipped pin',
            'constant=%d pin=%d literal=%d'
            % (R.MIN_TEST_FILES, shipped, LIT))

# R4 -- THE ARM THAT ACTUALLY CATCHES THE RATCHET LAYER, and R1 does not.
# Driven and recorded: the ratchet layer is the single line
# `MIN_TEST_FILES = _read_floor()[0]`. Removing it to
# `MIN_TEST_FILES = _MIN_TEST_FILES_FLOOR` leaves _read_floor() COMPLETELY
# INTACT, so R1 -- which calls _read_floor() directly -- stayed green against
# that mutant and the first ablation run reported "ratchet NOT CAUGHT".
# R1 is still worth having (it pins the function's own two directions), but
# the LAYER is the WIRING, and only an arm on the module CONSTANT can see
# wiring. MIN_TEST_FILES is computed at import time, so this reads it as
# imported and compares it against what the module's own floor path holds.
if os.path.isfile(R._FLOOR_PATH):
    try:
        _pin = json.loads(io.open(R._FLOOR_PATH, encoding='utf-8').read())['floor']
    except Exception as exc:                                    # noqa: BLE001
        cannot('R4 MIN_TEST_FILES is WIRED to the floor file',
               '%s could not be read (%s), so the wiring could not be '
               'checked. Not a pass.' % (R._FLOOR_PATH, exc))
    else:
        want = _pin if _pin >= LIT else LIT
        if R.MIN_TEST_FILES == want:
            ok('R4 MIN_TEST_FILES is WIRED to the floor file: constant %d == '
               'the pin at %s (%d). This is the arm that catches the ratchet '
               'layer being removed; R1 does not, because removing the wiring '
               'leaves _read_floor() intact'
               % (R.MIN_TEST_FILES, os.path.basename(R._FLOOR_PATH), _pin))
        else:
            bad('R4 MIN_TEST_FILES must be WIRED to the floor file, not to the '
                'last-resort literal',
                'constant=%d pin=%d literal=%d expected=%d. If the constant is '
                'the literal while the pin is higher, the ratchet layer is '
                'gone and the floor is a hand-maintained number again -- which '
                'sat at 370 against a real 802.'
                % (R.MIN_TEST_FILES, _pin, LIT, want))
else:
    cannot('R4 MIN_TEST_FILES is WIRED to the floor file',
           'the module under test resolves its floor path to %s, which does '
           'not exist, so the constant cannot be compared against a pin. An '
           'injected copy needs a docs/test-file-floor.json beside its own '
           'tools/ directory for this arm to mean anything.' % R._FLOOR_PATH)

# ── S. SILENCE-BREAKING -- STRUCTURAL, AND LABELLED AS SUCH ────────────────
print('\nS. silence-breaking: `behind` is INSIDE the early-return condition')
try:
    tree = ast.parse(io.open(TOOL, encoding='utf-8').read())
except SyntaxError as exc:
    cannot('S1 `behind` is part of the early-return condition',
           'tools/run_all_tests.py would not parse (%s).' % exc)
else:
    # PARSED, NOT GREPPED. A text anchor on that condition breaks the moment
    # somebody re-wraps the line, and this repo has already recorded arms that
    # silently stopped testing anything for exactly that reason.
    hits = []
    for fnode in ast.walk(tree):
        if not isinstance(fnode, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        assigns_behind = any(
            isinstance(n, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == 'behind'
                    for t in n.targets)
            for n in ast.walk(fnode))
        if not assigns_behind:
            continue
        for node in ast.walk(fnode):
            if not isinstance(node, ast.If):
                continue
            body = node.body
            bare_return = (len(body) == 1 and isinstance(body[0], ast.Return)
                           and isinstance(body[0].value, ast.Constant)
                           and body[0].value.value == 0)
            if not bare_return:
                continue
            names = {n.id for n in ast.walk(node.test)
                     if isinstance(n, ast.Name)}
            hits.append((fnode.name, node.lineno, 'behind' in names,
                         sorted(names)))
    if not hits:
        cannot('S1 `behind` is part of the early-return condition',
               'no `if ...: return 0` was found inside a function that assigns '
               '`behind`, so the shape this arm reads has moved. Re-read the '
               'function rather than trusting this arm -- it is UNPROVEN, not '
               'a pass.')
    else:
        guarded = [h for h in hits if h[2]]
        if guarded:
            ok('S1 STRUCTURAL: the early `return 0` in %s() at line %d tests '
               '`behind` (condition names: %s). A clean tree whose floor has '
               'gone stale therefore cannot return before any line is built'
               % (guarded[0][0], guarded[0][1], ', '.join(guarded[0][3])))
            print('       NOTE: structural, not behavioural -- the enclosing '
                  'function runs the whole suite, so driving it per arm is not '
                  'practical. Read as "the layer is present", not "the layer '
                  'works".')
        else:
            bad('S1 STRUCTURAL: `behind` must be inside the early-return '
                'condition, not only assigned near it',
                'found %d bare `return 0` guard(s) in a function assigning '
                '`behind`, none naming it: %r. Appending `behind` to the '
                'output lines alone makes it unreachable on exactly the run '
                'where it matters.' % (len(hits), hits))

print('')
if unproven:
    print('%d UNPROVEN: %s' % (len(unproven), '; '.join(unproven)))
if fails:
    print('%d failure(s)' % len(fails))
    for f in fails:
        print('  - ' + f)
    sys.exit(1)
if unproven:
    sys.exit(3)
print('ok  all three floor layers are armed')
sys.exit(0)
