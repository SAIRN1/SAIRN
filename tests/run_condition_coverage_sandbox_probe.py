#!/usr/bin/env python
"""Control: the mutation tester must never write a file in the real source tree.

# REQUIREMENT: tools/condition_coverage.py mutates source to see whether a suite
#   notices. It must do that in a THROWAWAY tree, never in api/_lib/. A kill
#   between the mutation and the restore cannot be caught by a `finally`, so the
#   real file must never be the one mutated in the first place.

THE INCIDENT. During the 2026-09-30 bare-run sweep this tool was launched with no
arguments under a 15-second timeout. It mutated `api/_lib/ledger.js` in place, was
killed mid-run, and the scratch clone was left with a mutated production engine --
`git status --porcelain` named it. The tool's `finally` and its three-stage
restore-verification are all correct and all irrelevant: a process that is killed
does not run its `finally`.

── WHAT A1 PROVES, AND WHY IT IS THE HONEST FORM OF "FAILING FIRST" ──────────
The old behaviour cannot be re-run -- it is gone. A1 instead reproduces the
MECHANISM on a fixture: the tool's own `write()` and `mutate()` are imported and
applied in place to a copy of a file, and the file changes. That is exactly what
was done to api/_lib/ledger.js. A2 then kills the real tool mid-run and asserts
the real engine is byte-identical, which is the arm that FAILED before the fix and
passes after it.

Run:  python tests/run_condition_coverage_sandbox_probe.py
"""
import hashlib
import io
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL_REL = os.path.join('tools', 'condition_coverage.py')
TOOL = os.path.join(REPO, TOOL_REL)
ENGINE_REL = 'api/_lib/ledger.js'
ENGINE = os.path.join(REPO, 'api', '_lib', 'ledger.js')

CRITERIA_VERSION = '2026-09-30.1'

_pass = _fail = 0


def ok(n):
    global _pass
    _pass += 1
    sys.stdout.write('  ok   %s\n' % n)


def bad(n, why):
    global _fail
    _fail += 1
    sys.stdout.write('  FAIL %s\n       %s\n' % (n, why))


def section(t):
    sys.stdout.write('\n%s\n' % t)


def digest(p):
    with io.open(p, 'rb') as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def main():
    for p in (TOOL, ENGINE):
        if not os.path.isfile(p):
            sys.stderr.write('COULD NOT RUN -- missing %s\n' % p)
            return 2
    sys.path.insert(0, os.path.join(REPO, 'tools'))
    try:
        import condition_coverage as cc
    except Exception as e:                                    # noqa: BLE001
        sys.stderr.write('COULD NOT RUN -- tools/condition_coverage.py does not '
                         'import: %s\n' % e)
        return 2

    sys.stdout.write('CONDITION-COVERAGE SANDBOX CONTROL -- criteria %s\n'
                     % CRITERIA_VERSION)

    section('A. THE MECHANISM, AND THE REAL TREE AFTER A KILL')

    d = tempfile.mkdtemp(prefix='ccsandbox_')
    try:
        # A1 -- the in-place mutation, reproduced on a fixture with the tool's own
        # functions. This is what happened to api/_lib/ledger.js.
        fx = os.path.join(d, 'engine.js')
        body = 'function f(a, b) {\n  if (a && b) { return 1; }\n  return 0;\n}\n'
        io.open(fx, 'w', encoding='utf-8', newline='\n').write(body)
        before = digest(fx)
        ops = cc.operands(body)
        if not ops:
            bad('A1. the operand scanner must find the fixture operand',
                'operands() returned nothing for a plain `a && b`')
        else:
            cc.write(fx, cc.mutate(body, ops[0]['pos'], ops[0]['op']))
            after = digest(fx)
            if after != before and '||' in io.open(fx, encoding='utf-8').read():
                ok('A1. KNOWN-BAD MECHANISM: write() + mutate() applied to a path '
                   'CHANGE THE FILE AT THAT PATH. Point them at api/_lib/ledger.js '
                   'and that is the production engine -- which is what the '
                   '2026-09-30 sweep left mutated when a 15s timeout killed the '
                   'run mid-mutation')
            else:
                bad('A1. the in-place mutation must be demonstrable',
                    'the fixture file did not change')

        # A2 -- THE ARM THAT FAILED BEFORE THE FIX. Launch the real tool and KILL
        # it while it is working, then check the real engine.
        engine_before = digest(ENGINE)
        dirty_before = subprocess.run(
            ['git', 'status', '--porcelain', '--untracked-files=no', '--', ENGINE_REL],
            cwd=REPO, capture_output=True, text=True, encoding='utf-8',
            errors='replace').stdout.strip()
        if dirty_before:
            bad('A2. PRECONDITION: api/_lib/ledger.js must be clean before this '
                'arm', 'git already reports it modified: %r -- this arm cannot '
                'attribute anything' % dirty_before)
        else:
            # POLLED, NOT SLEPT. The first version slept 14 seconds and then
            # killed; the ledger sweep finished first, so nothing was interrupted
            # and the arm said so instead of passing. This watches the REAL engine
            # for any change at all while the tool runs -- which is the strongest
            # form of the assertion, because on the old code the file was mutated
            # within the first second and `touched` would be True regardless of
            # when the kill landed.
            p = subprocess.Popen([sys.executable, TOOL_REL, '--engine', 'ledger'],
                                 cwd=REPO, stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT)
            touched = False
            alive_when_killed = False
            deadline = time.time() + 40
            killed_at = None
            while time.time() < deadline:
                if digest(ENGINE) != engine_before:
                    touched = True
                if p.poll() is not None:
                    break
                if time.time() > deadline - 34:      # ~6s in, definitely working
                    alive_when_killed = True
                    killed_at = time.time()
                    try:
                        p.kill()
                    except OSError:
                        pass
                    break
                time.sleep(0.2)
            try:
                p.wait(timeout=30)
            except subprocess.TimeoutExpired:
                pass
            time.sleep(0.5)
            engine_after = digest(ENGINE)
            dirty_after = subprocess.run(
                ['git', 'status', '--porcelain', '--untracked-files=no', '--',
                 ENGINE_REL], cwd=REPO, capture_output=True, text=True,
                encoding='utf-8', errors='replace').stdout.strip()
            if not alive_when_killed:
                bad('A2. the tool must still be running when it is killed',
                    'it exited within 6s, so nothing was interrupted and this arm '
                    'proves nothing about a killed run')
            elif touched:
                bad('A2. THE REAL ENGINE WAS MUTATED DURING THE RUN',
                    'api/_lib/ledger.js changed on disk while the tool was '
                    'working -- the mutation is still happening in the real tree')
            elif engine_after == engine_before and not dirty_after:
                ok('A2. THE ARM THAT MATTERS: the tool was KILLED mid-run, the '
                   'real api/_lib/ledger.js never changed at any point during the '
                   'run, and git reports it clean. A `finally` cannot run in a '
                   'killed process, so the only way to pass this is to never '
                   'mutate the real file')
            else:
                bad('A2. a killed run must leave the real engine untouched',
                    'hash changed=%s  git says=%r'
                    % (engine_after != engine_before, dirty_after))

        section('B. IT STILL MEASURES SOMETHING')

        r = subprocess.run([sys.executable, TOOL_REL, '--fixtures'], cwd=REPO,
                           capture_output=True, text=True, encoding='utf-8',
                           errors='replace', timeout=180)
        if r.returncode == 0 and 'blind lock' in (r.stdout or ''):
            ok('B1. the blind fixture lock still passes and still runs BEFORE '
               'anything is touched')
        else:
            bad('B1. the fixture lock must pass', 'exit=%s\n%s'
                % (r.returncode, ((r.stdout or '') + (r.stderr or ''))[-400:]))

        r = subprocess.run([sys.executable, TOOL_REL, '--engine', 'ledger',
                            '--limit', '2'], cwd=REPO, capture_output=True,
                           text=True, encoding='utf-8', errors='replace',
                           timeout=600)
        o = (r.stdout or '') + (r.stderr or '')
        if 'OPERANDS' in o and ('KILLED' in o or 'SURVIVED' in o):
            ok('B2. a real two-operand sweep still produces verdicts, so A2 is '
               'not passing because the tool stopped mutating anything at all')
        else:
            bad('B2. the tool must still produce verdicts', o[-500:])

        after_real = digest(ENGINE)
        if after_real == engine_before:
            ok('B3. ...and that completed sweep also left the real engine '
               'byte-identical')
        else:
            bad('B3. a completed sweep must not change the real engine',
                'the hash moved')

        section('C. THE REPORT PATH CANNOT BE A SOURCE FILE')

        rep = os.path.join(d, 'cov.json')
        r = subprocess.run([sys.executable, TOOL_REL, '--engine', 'ledger',
                            '--limit', '1', '--report', rep], cwd=REPO,
                           capture_output=True, text=True, encoding='utf-8',
                           errors='replace', timeout=600)
        if os.path.isfile(rep) and io.open(rep, encoding='utf-8').read().strip().startswith('{'):
            ok('C1. --report writes the result as JSON to the path given')
        else:
            bad('C1. --report must write the result',
                'no readable JSON at %s' % rep)

        r = subprocess.run([sys.executable, TOOL_REL, '--engine', 'ledger',
                            '--limit', '1', '--report', ENGINE_REL], cwd=REPO,
                           capture_output=True, text=True, encoding='utf-8',
                           errors='replace', timeout=600)
        o = (r.stdout or '') + (r.stderr or '')
        if r.returncode == 2 and digest(ENGINE) == engine_before:
            ok('C2. KNOWN-BAD: --report REFUSES a path under api/ and exits 2 '
               'rather than writing a report over a source file. The whole point '
               'of this change is that no output of this tool lands in src')
        else:
            bad('C2. --report must refuse a source path',
                'exit=%s  engine changed=%s\n%s'
                % (r.returncode, digest(ENGINE) != engine_before, o[-400:]))

        section('D. THE ANCHORS')

        src = io.open(TOOL, encoding='utf-8').read()
        for needle, why in (
            ('worktree', 'the sandbox mechanism A2 depends on'),
            ("'--report'", 'the option C1 and C2 drive'),
            ('def sandbox', 'the function that builds the throwaway tree'),
        ):
            if needle in src:
                ok('D. ANCHOR present: %s -- %s' % (needle, why))
            else:
                bad('D. ANCHOR MISSING: %s' % needle,
                    'the arms above stop testing the mechanism they name (%s)' % why)
    finally:
        shutil.rmtree(d, ignore_errors=True)

    sys.stdout.write('\n%d passed, %d failed\n' % (_pass, _fail))
    return 1 if _fail else 0


if __name__ == '__main__':
    sys.exit(main())
