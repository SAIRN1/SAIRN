#!/usr/bin/env python
"""run_copy_exactly_gate_probe.py -- the control on tools/copy_exactly_gate.py.

    python tests/run_copy_exactly_gate_probe.py

NOT tests/run_copy_exactly_probe.py, which is a DIFFERENT file probing a
DIFFERENT tool. `copy_exactly_check.py` asks whether the Copy-Exactly spec block
still matches the app it was lifted from; `copy_exactly_gate.py` asks whether a
propagation carries a recorded re-qualification. The two halves are named in
each tool's header. The near-collision is recorded here because the first draft
of this file was written to the other one's name and overwrote it.

The gate's own `--fixtures` lock covers DETECTION in both directions. This
covers the half a detector's own fixtures never do: the RECORD PARSER and the
EXIT CODES. A gate that detects perfectly and then accepts an empty record, or
that exits 0 on a range it could not read, protects nothing -- and neither
failure is visible from the detection fixtures.

Every arm builds a real throwaway git repository and runs the gate as a
subprocess, so what is exercised is the command a hook actually invokes rather
than an imported function.

── THE CONTROL ARM IS FIRST AND IT IS NOT DECORATION ───────────────────────
A1 asserts a COMPLETE record is ACCEPTED. Without it, every refusal arm below
is satisfied by a gate that refuses unconditionally -- which is the failure a
blocking gate actually reaches, because a gate nobody can satisfy gets
overridden and then it is decoration with a process around it.
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GATE = os.path.join(REPO, 'tools', 'copy_exactly_gate.py')

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

PASS, FAIL = [], []


def check(name, ok, detail=''):
    (PASS if ok else FAIL).append(name)
    print('  %-4s %s' % ('ok' if ok else 'FAIL', name))
    if not ok and detail:
        print('       %s' % detail.replace('\n', '\n       ')[:900])


def git(cwd, *args):
    r = subprocess.run(['git', '-C', cwd] + list(args), capture_output=True,
                       text=True, encoding='utf-8', errors='replace', timeout=180)
    return r.returncode, (r.stdout or ''), (r.stderr or '')


BLOCK = """function guardRow(row) {
  var amount = Number(row && row.amount);
  if (!isFinite(amount)) { return refuse('BAD_AMOUNT', 'amount must be a number'); }
  if (amount < 0) { return refuse('NEGATIVE', 'a refund is not a charge'); }
  var cents = Math.round(amount * 100);
  if (cents > MAX_CENTS) { return refuse('TOO_LARGE', 'over the per-row cap'); }
  var tag = String(row.tag || '').trim().toUpperCase();
  if (!TAGS[tag]) { return refuse('BAD_TAG', 'unknown tag ' + tag); }
  return { ok: true, cents: cents, tag: tag };
}"""

GOOD_RECORD = """propagate the row guard into b.js

copy-exactly: b.js <- a.js
  scale: b.js handles the same per-request single row a.js does, no batching
  input-range: b.js can receive a null tag where a.js could not, and the
    String() coercion covers it -- driven in the probe
  tier: a.js serves xx_prefs (Tier C), b.js serves xx_ledger (Tier A/A),
    so the money path was re-read rather than inheriting a.js's proof
"""


def build(td, msg, second_file=True):
    git(td, 'init', '-q')
    git(td, 'config', 'user.email', 'probe@example.invalid')
    git(td, 'config', 'user.name', 'probe')
    io.open(os.path.join(td, 'a.js'), 'w', encoding='utf-8', newline='\n').write(
        'var MAX_CENTS = 1;\nvar TAGS = {};\n' + BLOCK + '\n')
    git(td, 'add', '-A'); git(td, 'commit', '-q', '-m', 'one')
    _c, base, _e = git(td, 'rev-parse', 'HEAD')
    if second_file:
        io.open(os.path.join(td, 'b.js'), 'w', encoding='utf-8', newline='\n').write(
            'var MAX_CENTS = 1;\nvar TAGS = {};\n' + BLOCK + '\n')
    else:
        io.open(os.path.join(td, 'c.js'), 'w', encoding='utf-8', newline='\n').write(
            '\n'.join('function f%d(){ return %d * 3 + 7; }' % (i, i)
                      for i in range(14)) + '\n')
    git(td, 'add', '-A')
    mf = os.path.join(td, '.msg')
    io.open(mf, 'w', encoding='utf-8', newline='\n').write(msg)
    git(td, 'commit', '-q', '-F', '.msg')
    os.remove(mf)
    _c, tip, _e = git(td, 'rev-parse', 'HEAD')
    return base.strip(), tip.strip()


def case(label, msg, want_code, needle=None, second_file=True):
    with tempfile.TemporaryDirectory() as td:
        base, tip = build(td, msg, second_file)
        r = subprocess.run([sys.executable, GATE, '--range', base + '..' + tip],
                           capture_output=True, text=True, encoding='utf-8',
                           errors='replace', cwd=td, timeout=600)
        out = (r.stdout or '') + (r.stderr or '')
        ok = r.returncode == want_code and (needle is None or needle in out)
        check(label, ok, 'exit=%d want=%d\n%s' % (r.returncode, want_code, out[-700:]))


def main():
    print('COPY-EXACTLY GATE -- the record parser and the exit codes')
    if not shutil.which('git'):
        print('COULD NOT RUN: no git on PATH'); return 2

    # The gate resolves its repo from the CWD. That is the assumption every arm
    # below rests on, and it was FALSE in the first version of the gate -- which
    # this arm caught on its first run. Checked before anything depends on it.
    print('\nTHE HARNESS ASSUMPTION, CHECKED BEFORE ANYTHING RESTS ON IT')
    with tempfile.TemporaryDirectory() as td:
        base, tip = build(td, GOOD_RECORD)
        r = subprocess.run([sys.executable, GATE, '--range', base + '..' + tip],
                           capture_output=True, text=True, encoding='utf-8',
                           errors='replace', cwd=td, timeout=600)
        out = (r.stdout or '') + (r.stderr or '')
        reads_fixture = r.returncode != 2 and 'does not resolve' not in out
        check('the gate reads the range in the CURRENT WORKING DIRECTORY\'s repo',
              reads_fixture,
              'the gate resolved the range against its OWN repo instead, so every '
              'arm below would be judging the SAIRN repository and not the '
              'fixture:\n' + out[-600:])
    if FAIL:
        print('\nSTOPPING: the harness cannot reach the gate the way it assumes.')
        print('%d passed, %d failed' % (len(PASS), len(FAIL)))
        return 1

    print('\nTHE CONTROL -- a satisfiable gate')
    case('A1 a COMPLETE record is ACCEPTED', GOOD_RECORD, 0)
    case('A2 no propagation at all is ACCEPTED with no record',
         'add unrelated new code\n', 0, second_file=False)

    print('\nTHE REFUSALS')
    case('A3 a propagation with NO record is REFUSED',
         'propagate the row guard into b.js\n', 1, 'no recorded re-qualification')

    for key in ('scale', 'input-range', 'tier'):
        stripped = '\n'.join(l for l in GOOD_RECORD.split('\n')
                             if not l.strip().startswith(key + ':'))
        case('A4 a record MISSING `%s` is REFUSED -- all three or none' % key,
             stripped, 1, 'incomplete')

    thin = GOOD_RECORD.replace(
        'scale: b.js handles the same per-request single row a.js does, no batching',
        'scale: same')
    case('A5 a ONE-WORD answer is REFUSED -- a field is not an answer',
         thin, 1, 'too short')

    case('A6 a copy-exactly-none note that is too SHORT is REFUSED',
         'propagate\n\ncopy-exactly-none: boilerplate\n', 1)

    print('\nTHE ESCAPE HATCH, WHICH HAS TO WORK OR THE GATE GETS RIPPED OUT')
    case('A7 a copy-exactly-none note with a real reason is ACCEPTED',
         'propagate\n\ncopy-exactly-none: both hunks are the standard CORS '
         'preamble every api/ handler carries; there is no pattern being moved '
         'and nothing to re-qualify\n', 0)

    print('\nCOULD-NOT-RUN IS A THIRD STATE, NEVER A PASS (PR 1.11)')
    with tempfile.TemporaryDirectory() as td:
        build(td, GOOD_RECORD)
        r = subprocess.run([sys.executable, GATE, '--range', 'f' * 40 + '..HEAD'],
                           capture_output=True, text=True, encoding='utf-8',
                           errors='replace', cwd=td, timeout=600)
        out = (r.stdout or '') + (r.stderr or '')
        check('A8 an unresolvable range exits 2 and says nothing was checked',
              r.returncode == 2 and 'COULD NOT RUN' in out,
              'exit=%d\n%s' % (r.returncode, out[-500:]))
        r = subprocess.run([sys.executable, GATE, '--range', 'nonsense'],
                           capture_output=True, text=True, encoding='utf-8',
                           errors='replace', cwd=td, timeout=600)
        check('A9 a malformed --range exits 2 rather than guessing',
              r.returncode == 2, 'exit=%d' % r.returncode)

    print('\nTHE BLIND LOCK IS NOT OPTIONAL ON THE REAL PATH')
    with tempfile.TemporaryDirectory() as td:
        # A copy of the gate with one fixture expectation inverted: the lock must
        # fail, and the gate must then refuse to judge anything at all rather
        # than run with criteria it has just proved unfit.
        src = io.open(GATE, encoding='utf-8').read()
        broken = src.replace(
            "    case('a proven guard copied into a SECOND file -- THE finding', p1, 1)",
            "    case('a proven guard copied into a SECOND file -- THE finding', p1, 99)")
        if broken == src:
            check('A10 a FAILING blind lock stops the sweep and exits 2', False,
                  'the lock-sabotage anchor moved, so this arm could not be '
                  'exercised at all -- that is a could-not-check, not a pass.')
        else:
            bp = os.path.join(td, 'broken_gate.py')
            io.open(bp, 'w', encoding='utf-8', newline='\n').write(broken)
            with tempfile.TemporaryDirectory() as td2:
                base, tip = build(td2, GOOD_RECORD)
                r = subprocess.run([sys.executable, bp, '--range', base + '..' + tip],
                                   capture_output=True, text=True, encoding='utf-8',
                                   errors='replace', cwd=td2, timeout=600)
                out = (r.stdout or '') + (r.stderr or '')
                check('A10 a FAILING blind lock stops the sweep and exits 2',
                      r.returncode == 2 and 'blind lock failed' in out,
                      'exit=%d\n%s' % (r.returncode, out[-500:]))

    print('\n%d passed, %d failed' % (len(PASS), len(FAIL)))
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
