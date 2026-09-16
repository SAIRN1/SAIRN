#!/usr/bin/env python
"""tests/run_dispatch_state_probe.py -- controls for tools/dispatch_state.py.

THE WAY THIS TOOL FAILS DANGEROUSLY IS BY SHOWING TOO SHORT A LIST. A row it
wrongly classifies as CLOSED, or wrongly attributes to a busy session, simply
stops appearing -- and an empty dispatch list looks identical to a finished
platform. So the arms are weighted toward the OPEN direction: an unknown status
must default to open, a strikethrough title must not hide a row that is still
open underneath, and the classifier must be shown to move when its input moves.

Exit 0 all arms passed, 1 otherwise.
"""

import hashlib
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, 'tools'))
SUBJECT = os.path.join(REPO, 'tools', 'dispatch_state.py')

FAILS, PASSES = [], [0]


def ok(label, cond, detail=''):
    if cond:
        PASSES[0] += 1
        print('    ok   %s' % label)
    else:
        FAILS.append(label)
        print('    FAIL %s' % label)
        if detail:
            print('         %s' % str(detail)[:400])


import dispatch_state as D   # noqa: E402


# THE WORKING TREE AS IT WAS BEFORE THIS FILE RAN THE SUBJECT EVEN ONCE.
# Captured here rather than in section F, and that is not tidiness: the first
# version took its "before" inside section F, by which point sections C, D and
# E had already run the tool four times. A sabotage that made the tool CREATE A
# FILE was therefore present in both snapshots and the arm reported clean --
# found 2026-09-16 by running that sabotage, not by reading the arm.
def _tree_state():
    return subprocess.run(['git', 'status', '--porcelain'], cwd=REPO,
                          capture_output=True, text=True, encoding='utf-8',
                          errors='replace').stdout


TREE_AT_START = _tree_state()


print('\nA. open vs closed, and the direction the default leans')
ok('the fixture table passes', not D.self_check(verbose=False))
ok('EVERY done-word closes a row',
   all(not D.is_open('**%s 2026-01-01 (x)**' % w) for w in D.DONE_WORDS),
   [w for w in D.DONE_WORDS if D.is_open('**%s 2026-01-01 (x)**' % w)])
# THE ARM THAT MATTERS MOST. A vocabulary this file has not seen must surface
# the row, never hide it -- the reverse would let one new status word retire a
# row silently and for ever.
for unknown in ('QUUXED', 'PARKED', 'DEFERRED', 'HELD', 'PENDING', 'WONTFIX'):
    ok('an unseen status %r defaults to OPEN' % unknown,
       D.is_open('**%s 2026-01-01**' % unknown))
ok('a done-word only counts at the START -- "not CLOSED" stays open',
   D.is_open('not CLOSED yet, see below'))


print('\nB. owner parsing')
ok('a single owner is found', D.owners_of('Hank') == ['hank'])
ok('two owners are both found',
   D.owners_of('CC (fixed) / **Fourth** (the five stale claims)') == ['cc', 'fourth'])
ok('Michael is not a session', D.owners_of('**Michael** to run the migration') == [])
ok('a word merely CONTAINING a session name does not match',
   D.owners_of('unassigned, blocked, ccache') == [],
   D.owners_of('unassigned, blocked, ccache'))
ok('an em-dash owner cell yields nobody', D.owners_of('&mdash;') == [])


print('\nC. the live inputs are real, and an absent one is COULD NOT RUN')
claims, cp = D.live_claims()
ok('claims parse', claims is not None, cp)
ok('...and there is at least one active claim to join against',
   claims and len(claims) >= 1, claims)
rs, rp = D.rows()
ok('the index parses', rs is not None, rp)
ok('...into a realistic number of rows', rs and len(rs) > 400, len(rs or []))
ok('every row has an app, an item and a status',
   all(len(r) == 4 for r in (rs or [])))

TMP = tempfile.mkdtemp(prefix='ds_')
try:
    src = io.open(SUBJECT, encoding='utf-8').read()
    ANCHOR = "CLAIM_DIR = os.path.join(REPO, '.claude', 'claims')"
    ok('the claims-path anchor is present', src.count(ANCHOR) == 1,
       'anchor stale -- the could-not-run arm below tests NOTHING')
    broken = os.path.join(TMP, 'broken.py')
    io.open(broken, 'w', encoding='utf-8').write(
        src.replace(ANCHOR, "CLAIM_DIR = os.path.join(REPO, '.claude', 'NOPE')"))
    r = subprocess.run([sys.executable, broken], capture_output=True, text=True,
                       encoding='utf-8', errors='replace', cwd=REPO,
                       env=dict(os.environ, PYTHONPATH=os.path.join(REPO, 'tools')))
    ok('AN ABSENT CLAIMS DIRECTORY IS COULD NOT RUN (2), not an empty claim list',
       r.returncode == 2, 'exit %s\n%s' % (r.returncode, r.stdout[-300:]))
    ok('...and it says so rather than reporting everything unclaimed',
       'COULD NOT RUN' in r.stdout, r.stdout[:200])
finally:
    shutil.rmtree(TMP, ignore_errors=True)
    ok('the scratch directory is gone', not os.path.isdir(TMP))


print('\nD. the report itself')
r = subprocess.run([sys.executable, SUBJECT], capture_output=True, text=True,
                   encoding='utf-8', errors='replace', cwd=REPO)
ok('it runs to completion', r.returncode in (0, 1, 2), r.stderr[-400:])
# IT DIED HERE ON ITS FIRST REAL RUN. The index carries emoji in row titles and
# Windows encodes captured stdout as cp1252, so the tool computed the right
# answer and then raised UnicodeEncodeError printing it -- the exact defect
# fixed in tools/run_semgrep.py hours earlier and measured as unswept across 94
# of 138 files in tools/. This arm is why it cannot come back silently.
ok('NO UnicodeEncodeError when stdout is CAPTURED, which is every hook and CI '
   'step', 'UnicodeEncodeError' not in (r.stderr or ''), r.stderr[-300:])
for section in ('ACTIVE CLAIMS', 'CONTESTED', "MICHAEL'S",
                'OPEN AND UNOWNED', 'DOES NOT DECIDE'):
    ok('the report carries the %r section' % section, section in r.stdout)
ok('it states its own limit rather than implying a verdict',
   'same work' in r.stdout and 'second guesser' in r.stdout, r.stdout[-400:])
rj = subprocess.run([sys.executable, SUBJECT, '--json'], capture_output=True,
                    text=True, encoding='utf-8', errors='replace', cwd=REPO)
import json
body = json.loads(rj.stdout[rj.stdout.index('{'):])
ok('--json parses and carries every bucket',
   all(k in body for k in ('open', 'contested', 'michael', 'unclaimed',
                           'unowned', 'claims')), sorted(body))
ok('the buckets partition the open rows -- none is lost between them',
   body['open'] == len(body['contested']) + len(body['michael'])
   + len(body['unclaimed']) + len(body['unowned']),
   (body['open'], len(body['contested']), len(body['michael']),
    len(body['unclaimed']), len(body['unowned'])))


print('\nE. teeth -- a classifier that calls everything closed must not report '
      'an empty, tidy platform')
TMP2 = tempfile.mkdtemp(prefix='ds2_')
try:
    ANCHOR2 = '    return True\n'
    ok('the teeth anchor is present', src.count(ANCHOR2) >= 1)
    bp = os.path.join(TMP2, 'broken2.py')
    io.open(bp, 'w', encoding='utf-8').write(
        src.replace('def is_open(status):\n', 'def is_open(status):\n    return False\n', 1))
    rb = subprocess.run([sys.executable, bp], capture_output=True, text=True,
                        encoding='utf-8', errors='replace', cwd=REPO,
                        env=dict(os.environ, PYTHONPATH=os.path.join(REPO, 'tools')))
    ok('the broken copy runs', rb.returncode in (0, 1, 2), rb.stderr[-300:])
    # The fixtures run BEFORE any row is classified, so an always-closed
    # classifier is caught by the blind lock rather than producing a clean,
    # empty and completely wrong dispatch list.
    ok('TEETH: an always-closed classifier exits COULD NOT RUN (2), not 0',
       rb.returncode == 2, 'exit %s\n%s' % (rb.returncode, rb.stdout[-300:]))
    ok('...and names the rule that failed rather than printing a report',
       'open/closed rule failed' in rb.stdout, rb.stdout[:250])
finally:
    shutil.rmtree(TMP2, ignore_errors=True)
    ok('the second scratch directory is gone', not os.path.isdir(TMP2))


print('\nF. the REPORT ONLY claim, which the docstring states and nothing '
      'checked')
# ADDED 2026-09-16 BY A FIRST ARTICLE INSPECTION (item 47), by Hank, on a tool
# written by another session. The gate reported tools/dispatch_state.py as
# needing one; the inspection found the SAME GAP Fourth's three-tool FAI found
# the same day -- the docstring says "REPORT ONLY." in isolation on its own
# line, and nothing anywhere asserted it.
#
# THE EXIT-2 HALF OF THAT PATTERN IS ALREADY COVERED HERE and is called out so
# this section is not read as finding two gaps where there is one: sections C
# and E drive COULD-NOT-RUN through an absent claims directory and through a
# sabotaged classifier. It is the report-only half that had nothing.
#
# WHAT "REPORT ONLY" MEANS ON THIS PLATFORM is that the tool never MUTATES.
# It is not about the exit code: a report-only check registered with by_exit
# is expected to exit 1 on a finding. So these arms test for mutation, and they
# test the SOURCE as well as a run -- a run proves this run wrote nothing, and
# the source arm is what fails the day somebody adds a writer.
# THE SOURCE ARM IS AN AST WALK, NOT A REGEX, AND THAT IS NOT STYLE.
# The first version of this arm was `open\s*\([^)]*['"][rbt]*[wax]`, and its
# own sabotage pass walked straight through it: `io.open(os.path.join(REPO,
# '.dispatch_cache'), 'w')` has a nested call between `open(` and the mode, so
# `[^)]*` stops at the inner `)` and the pattern never reaches the 'w'. The arm
# reported clean against a tool that had just been made to write a file. Found
# 2026-09-16 by running the sabotage rather than by reading the pattern -- which
# is the whole argument for running it.
import ast as _ast


def _write_opens(source):
    """Every open()/io.open() call with a write-ish mode, however nested."""
    hits = []
    for n in _ast.walk(_ast.parse(source)):
        if not isinstance(n, _ast.Call):
            continue
        fname = (n.func.id if isinstance(n.func, _ast.Name)
                 else n.func.attr if isinstance(n.func, _ast.Attribute) else '')
        if fname != 'open':
            continue
        # ONLY THE MODE ARGUMENT, and this is the SECOND correction to this one
        # predicate in one sitting. Checking EVERY string argument for a write
        # character flagged four ordinary READS in tools/retry_backoff_check.py,
        # because `errors='replace'` contains an 'a'. An arm that cries wolf on
        # any file that reads carefully gets deleted, which is a slower way of
        # having no arm at all. Both corrections came from running the thing on
        # a second file rather than from re-reading it.
        mode = n.args[1] if len(n.args) > 1 else None
        for k in n.keywords:
            if k.arg == 'mode':
                mode = k.value
        if (isinstance(mode, _ast.Constant) and isinstance(mode.value, str)
                and any(c in mode.value for c in 'wax+')):
            hits.append(_ast.dump(n)[:120])
    return hits


_hits = _write_opens(src)
ok('no write-mode open() anywhere in the source, found by AST so a nested path '
   'expression cannot hide one', not _hits, _hits[:2])
# The arm proves it can FIRE, on a fixture, rather than being trusted because
# it returned nothing on the real file.
ok('...and that check really detects one when it is there',
   len(_write_opens("import io, os\n"
                    "io.open(os.path.join(a, b), 'w').write('x')\n")) == 1,
   'the detector cannot see a nested write-mode open')
ok('...and it does NOT fire on an ordinary careful READ, whose '
   "errors='replace' contains an 'a'",
   _write_opens("import io\n"
                "io.open(p, encoding='utf-8', errors='replace').read()\n") == [],
   'the detector fires on encoding/errors keywords')
ok('...and it sees a mode= keyword too, not only the positional form',
   len(_write_opens("import io\nio.open(p, mode='a').write('x')\n")) == 1,
   'a keyword mode is invisible')
# SPELLED OUT RATHER THAN LOOPED, and the reason is tooling rather than taste:
# a label built with %s reaches the AST as the literal '...and no %s', so every
# one of these nine arms is invisible to anything that reads arm labels --
# including the First Article worksheet that sent me here. A label that cannot
# be named cannot be cited in an inspection record.
ok('...and no json.dump( anywhere in the source', 'json.dump(' not in src)
ok('...and no shutil. anywhere in the source', 'shutil.' not in src)
ok('...and no os.remove anywhere in the source', 'os.remove' not in src)
ok('...and no os.rename anywhere in the source', 'os.rename' not in src)
ok('...and no os.makedirs anywhere in the source', 'os.makedirs' not in src)
ok('...and no os.mkdir anywhere in the source', 'os.mkdir' not in src)
# THE THREE THAT CARRY THE CLAIM-MATCHER CLAIM TOO. The header says this tool
# does NOT ask sairn_claim.py, and the only way it could is by invoking it.
ok('...and NO subprocess.run, so it never invokes sairn_claim.py to ask the '
   'claim matcher', 'subprocess.run' not in src)
ok('...and NO subprocess.call, same reason', 'subprocess.call' not in src)
ok('...and NO subprocess.check_output or check_call, same reason',
   'subprocess.check' not in src)

# THE RUN ITSELF LEAVES THE WHOLE WORKING TREE UNTOUCHED.
# The first version hashed the index and the claim files -- the two things the
# tool READS -- and a sabotage that wrote a NEW file somewhere else passed it
# untouched. `git status --porcelain` is the structurally different instrument:
# it sees a creation, a deletion or a modification ANYWHERE in the repo, which
# is the property "report only" actually names.
_before = TREE_AT_START
for _args in ([], ['--all'], ['--json'], ['--stale-review'], ['--self-check']):
    subprocess.run([sys.executable, SUBJECT] + _args, capture_output=True,
                   text=True, encoding='utf-8', errors='replace', cwd=REPO)
_after = _tree_state()
ok('EVERY subcommand leaves the WHOLE WORKING TREE unchanged -- nothing '
   'created, modified or deleted anywhere in the repo',
   _after == _before,
   'git status changed:\n' + '\n'.join(
       sorted(set(_after.splitlines()) ^ set(_before.splitlines()))))

# AND THE ORDINARY REPORT PATH CANNOT RETURN A FINDING EXIT, because it hands
# finish() a hardcoded empty findings list. Asserted on the source AND through
# the real entry point, since the source arm alone would survive a refactor
# that kept the literal and stopped using it.
ok('the ordinary report path passes an EMPTY findings list to finish()',
   'return finish([], could_not_run)' in src,
   'the report path can now produce findings')
for _args in ([], ['--all'], ['--json']):
    _r = subprocess.run([sys.executable, SUBJECT] + _args, capture_output=True,
                        text=True, encoding='utf-8', errors='replace', cwd=REPO)
    ok('...and %r really exits 0 on the live repo, not 1'
       % (' '.join(_args) or '(no args)'), _r.returncode == 0,
       'exit %s' % _r.returncode)
# THE OTHER DIRECTION, so the arms above are not passing on a tool that can
# never report anything: --stale-review is a GATE and returns 1 on a hit. That
# is not a contradiction of REPORT ONLY -- it still writes nothing -- and it is
# pinned here so the distinction is recorded rather than blurred.
ok('--stale-review is the one subcommand that CAN exit 1, and it is a gate '
   'rather than a writer', 'return 1 if hits else 0' in src,
   'the stale-review gate lost its finding exit')

print('\n' + '=' * 66)
print('%d passed, %d failed' % (PASSES[0], len(FAILS)))
for f in FAILS:
    print('  FAILED: %s' % f)
sys.exit(1 if FAILS else 0)
