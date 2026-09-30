#!/usr/bin/env python
"""The control for tools/dead_rule_sweep.py -- BOTH directions.

    python tests/run_dead_rule_sweep_probe.py

Exit 0 all arms pass, 1 any arm fails.

── THE ARM THAT MATTERS IS THE RESTORE ─────────────────────────────────────
This sweep MUTATES real tool files -- it neutralises one compiled pattern at a
time and re-runs the tool's own evidence. A restore that silently fails leaves
a broken rule in a tool somebody else pushes, and this repo has already paid
once for a probe whose restore was wrong. Section C drives a real neutralise /
restore cycle on a scratch copy and asserts BYTE IDENTITY afterwards.

── AND THE SECOND ARM IS THAT THE REWRITE PARSES ───────────────────────────
A neutralisation that breaks the module turns every rule red for the wrong
reason and the sweep reports a clean bill of exercised rules. Section B checks
the rewritten source still parses, still imports, and actually contains the
never-matching pattern -- because "the patch applied" and "the patch did
nothing" are the two answers that look identical from the outside.
"""
import ast
import io
import os
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
TOOL = os.path.join(REPO, 'tools', 'dead_rule_sweep.py')
CONTROLS_FOR = ['dead_rule_sweep.py']

import dead_rule_sweep as D                                      # noqa: E402

_pass, _fail = 0, 0


def check(name, cond, detail=''):
    global _pass, _fail
    if cond:
        print('  ok   ' + name)
        _pass += 1
    else:
        print('  FAIL ' + name)
        if detail != '':
            print('       %s' % (detail,))
        _fail += 1


def section(t):
    print('\n' + t)


def run(*args):
    r = subprocess.run([sys.executable, TOOL] + list(args), cwd=REPO,
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace',
                       env=dict(os.environ, PYTHONIOENCODING='utf-8',
                                PYTHONUTF8='1'))
    return r.returncode, (r.stdout or '') + (r.stderr or '')


print('DEAD RULE SWEEP -- the control for the sweep')

# ── A. THE CRITERIA LOCK GATES THE RUN ─────────────────────────────────────
section('A. break the rewrite and the sweep must REFUSE, not report clean')
rc, out = run('--fixtures')
check('A1. the lock passes on the shipped criteria', rc == 0
      and 'fixtures classify correctly' in out, (rc, out[-300:]))

_orig = io.open(TOOL, encoding='utf-8', newline='').read()
_sab = _orig.replace('NEVER = "(?!x)x"', 'NEVER = "(?!x)x"  # noqa\nNEVER = ""', 1)
check('A2a. THE SABOTAGE APPLIED -- without this A2 proves nothing',
      _sab != _orig, 'the NEVER anchor moved')
try:
    io.open(TOOL, 'w', encoding='utf-8', newline='').write(_sab)
    rc, out = run('--fixtures')
    check('A2. ...and with the never-matching pattern emptied the lock FAILS '
          'and the sweep exits 2. A sweep whose own rewrite is broken reports '
          'every rule as dead, which is the loudest possible wrong answer',
          rc == 2 and 'CRITERIA LOCK FAILED' in out, (rc, out[-400:]))
finally:
    io.open(TOOL, 'w', encoding='utf-8', newline='').write(_orig)
rc, out = run('--fixtures')
check('A3. THE RESTORE WORKED', rc == 0, (rc, out[-200:]))

# ── B. THE REWRITE IS REAL, AND IT PARSES ──────────────────────────────────
section('B. the neutralisation applies, parses, and can never match')

SRC = ("import re\n"
       "PAT = re.compile(\n    r'abc'\n    r'|def', re.I)\n"
       "OTHER = re.compile(r'zzz')\n")
_new = D.neutralise(SRC, 'PAT')
check('B1. a MULTI-LINE pattern with adjacent literals and a flag is rewritten '
      '-- text surgery gets this wrong, which is why it goes through ast',
      _new is not None and D.NEVER in _new, _new)
check('B1b. ...and the result STILL PARSES. A rewrite that breaks the module '
      'turns every rule red for the wrong reason and the sweep then reports a '
      'clean bill of exercised rules',
      _new is not None and ast.parse(_new) is not None, _new)
check('B1c. ...and the FLAGS are carried over, not dropped. Dropping re.I '
      'changes behaviour beyond the neutralisation, so the ablation would be '
      'measuring two things at once',
      _new is not None and 're.I' in _new, _new)
check('B1d. ...and the OTHER pattern in the same module is untouched, so one '
      'ablation is one rule',
      _new is not None and "OTHER = re.compile(r'zzz')" in _new, _new)
check('B2. the never-matching pattern really matches NOTHING -- if it matched '
      'anything the ablation would be a no-op reported as an exercise',
      __import__('re').compile(D.NEVER).search('x') is None
      and __import__('re').compile(D.NEVER).search('') is None, D.NEVER)
check('B3. a name that is NOT a module-level pattern yields no rewrite, rather '
      'than a silent no-op that would be counted as a rule nothing depends on',
      D.neutralise(SRC, 'NOSUCH') is None, 'a phantom rewrite was produced')
check('B3b. ...and a pattern compiled INSIDE A FUNCTION is out of reach, which '
      'is a stated limit and not a gap',
      D.neutralise("def f():\n    P = re.compile(r'x')\n", 'P') is None, '')

# ── C. THE RESTORE, DRIVEN ON A REAL FILE ──────────────────────────────────
section('C. the sweep puts the file back, byte for byte')

_tmpdir = tempfile.mkdtemp(prefix='drs-')
_scratch = os.path.join(_tmpdir, 'scratch_tool.py')
_body = ("import re\nPAT = re.compile(r'abc')\n\n\n"
         "def main(argv):\n    return 0\n")
io.open(_scratch, 'w', encoding='utf-8', newline='').write(_body)
_before = io.open(_scratch, encoding='utf-8', newline='').read()
_patched = D.neutralise(_before, 'PAT')
io.open(_scratch, 'w', encoding='utf-8', newline='').write(_patched)
check('C1. the mutation really lands on disk -- a probe that asserts a restore '
       'without proving the mutation happened is asserting nothing',
      D.NEVER in io.open(_scratch, encoding='utf-8').read(), '')
io.open(_scratch, 'w', encoding='utf-8', newline='').write(_before)
check('C2. ...and the restore is BYTE IDENTICAL. This repo has already paid '
      'once for a probe whose restore was wrong, and this sweep mutates files '
      'other sessions push',
      io.open(_scratch, encoding='utf-8', newline='').read() == _before, '')
try:
    os.unlink(_scratch)
    os.rmdir(_tmpdir)
except OSError:
    pass

check('C3. ANCHOR: the sweep restores inside a `finally` and RAISES when the '
      'file on disk is not what it was -- a silent restore failure is worse '
      'than no sweep at all',
      'finally:' in _orig and 'RESTORE FAILED' in _orig,
      'the restore guard is gone')

# ── D. THE REAL RUN, ON ITSELF ─────────────────────────────────────────────
section('D. the real run')
rc, out = run('--tool', 'assertion_label_shape_check.py')
import re                                                        # noqa: E402
check('D1. it reads a NON-EMPTY rule list -- a zero would make the verdict '
      'vacuous', re.search(r'(\d+) module-level compiled rule', out) is not None
      and int(re.search(r'(\d+) module-level compiled rule', out).group(1)) > 0,
      out[:400])
check('D2. it publishes CHECKED / UNIVERSE and keeps COULD NOT TELL SEPARATE '
      'from clean -- "no evidence to ablate" and "the rule is exercised" are '
      'opposite findings that would otherwise print the same',
      # Matched on a SINGLE-LINE phrase. The first attempt keyed on 'could
      # not be compared', which the tool wraps across a newline and an indent --
      # a control failing on its own subject's formatting rather than on its
      # subject.
      'CHECKED / UNIVERSE' in out and 'STILL NOT CLEARED' in out
      and 'no lock, no control' in out, out[:1200])
check('D3. and it reports the tiers SEPARATELY rather than as one score: '
      'exercised and dead against SHIPPED evidence, and the weaker real-run '
      'tier counted apart from both. Folding the two would let a rule defended '
      'only by the corpus read as one defended by a lock',
      re.search(r'of which\s+\d+ exercised and \d+ dead', out) is not None
      and 'REAL RUN ONLY' in out, out[:1200])
check('D3b. ...and the output SAYS WHY the real-run tier is weaker, in words. A '
      'reader who cannot see the difference will treat the two as one number',
      'a lock changes when somebody decides' in out
      and 'anybody pushes' in out, out[:1200])
check('D4. exit is 0, 1 or 2 and nothing else', rc in (0, 1, 2), rc)
check('D5. THE FILE IT ABLATED IS UNCHANGED after the real run',
      subprocess.run(['git', 'diff', '--quiet', '--',
                      'tools/assertion_label_shape_check.py'],
                     cwd=REPO).returncode == 0,
      'the sweep left a real tool modified')

# ── E. ANCHORS ─────────────────────────────────────────────────────────────
section('E. the anchors this control depends on')
check('E1. neutralise() and sweep_tool() are still the names this control calls',
      'def neutralise(' in _orig and 'def sweep_tool(' in _orig, '')
check('E2. CRITERIA_VERSION is present and appears in the real output',
      bool(str(getattr(D, 'CRITERIA_VERSION', '')).strip())
      and D.CRITERIA_VERSION in out, getattr(D, 'CRITERIA_VERSION', None))
check('E3. the tool declares this file as its control',
      'run_dead_rule_sweep_probe.py' in _orig, 'CONTROLLED_BY is stale')

# ── F. NO TRACKED FILE IS EVER WRITTEN, INCLUDING WHEN THE SWEEP IS KILLED ─
# D5 asserts the file is unchanged AFTER a run that finished. That is the easy
# half and it passed for as long as the sweep mutated tracked files, because the
# `finally` restored them. THE FINALLY IS NOT REACHED WHEN THE PROCESS DIES --
# SIGKILL, a 240s harness bound, a closed laptop -- and the measured first full
# run left TWENTY tracked tool sources written, each carrying a rule replaced by
# a never-matching pattern, in a clone four other sessions push from.
#
# So this section drives the case D5 cannot see: start a real sweep, kill it
# while it is working, and require the tree to be clean anyway. That is only
# possible if the mutation never touched a tracked file in the first place.
#
# EVERY ARM HERE RUNS IN A THROWAWAY WORKTREE. A control for "does this write
# the clone" must not write the clone to find out.
section('F. the sweep works on a COPY -- killing it mid-run leaves nothing behind')

import shutil                                                    # noqa: E402
import time                                                      # noqa: E402

_wt = tempfile.mkdtemp(prefix='drs-kill-')
shutil.rmtree(_wt, ignore_errors=True)
_add = subprocess.run(['git', '-C', REPO, 'worktree', 'add', '-q', '--detach',
                       _wt, 'HEAD'], capture_output=True, text=True,
                      encoding='utf-8', errors='replace')
if _add.returncode != 0:
    check('F0. a worktree could be created -- without one nothing below ran',
          False, _add.stderr.strip()[:300])
else:
    try:
        # THE SUBJECT IS THE WORKING TREE, NOT HEAD. Copied over, and the copy
        # asserted, so this section can be written BEFORE the fix is committed
        # and go red against the version actually on disk.
        shutil.copyfile(TOOL, os.path.join(_wt, 'tools', 'dead_rule_sweep.py'))
        check('F0. the working-tree sweep was copied into the worktree',
              io.open(os.path.join(_wt, 'tools', 'dead_rule_sweep.py'),
                      encoding='utf-8').read() == _orig, '')

        # THE ONE EXCLUSION, NAMED: this probe itself copied the working-tree
        # sweep over the worktree's copy in F0, so that path is dirt THIS FILE
        # put there. Excluding it by name keeps the arm about the subject --
        # without it F1 went red and the poll below broke at t=0 on the probe's
        # own edit, killing the sweep before it had printed a line, so F2 failed
        # too. Three red arms, one of them the control, none about the sweep.
        _MINE = 'tools/dead_rule_sweep.py'

        def _dirty():
            r = subprocess.run(['git', '-C', _wt, 'status', '--porcelain'],
                               capture_output=True, text=True,
                               encoding='utf-8', errors='replace')
            return [l for l in (r.stdout or '').split('\n')
                    if l.strip() and _MINE not in l]

        check('F1. CONTROL: the worktree is clean before the sweep starts -- '
              'without this every arm below could be measuring pre-existing dirt',
              not _dirty(), _dirty()[:5])

        _logp = os.path.join(_wt, '..', 'drs-kill.log')
        _log = io.open(_logp, 'w', encoding='utf-8', errors='replace')
        _p = subprocess.Popen(
            [sys.executable, os.path.join(_wt, 'tools', 'dead_rule_sweep.py'),
             '--tool', 'assertion_label_shape_check.py'],
            cwd=_wt, stdout=_log, stderr=subprocess.STDOUT,
            # UNBUFFERED, because this process is going to be KILLED. A buffered
            # child loses everything it printed, and F2 -- the paired positive
            # that proves the sweep started at all -- would fail on the plumbing
            # rather than on the subject.
            env=dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUTF8='1',
                     PYTHONUNBUFFERED='1'))
        # Poll for dirt rather than sleeping a fixed time: against a sweep that
        # mutates tracked files the very first neutralisation shows up here
        # within a second or two, so a hit is fast and a miss costs the bound.
        _seen, _deadline = [], time.time() + 30
        while time.time() < _deadline and _p.poll() is None:
            _seen = _dirty()
            if _seen:
                break
            time.sleep(0.5)
        _ran_to_completion = _p.poll() is not None
        if _p.poll() is None:
            _p.kill()
        try:
            _p.wait(timeout=30)
        except Exception:                                        # noqa: BLE001
            pass
        _log.close()
        _out = io.open(_logp, encoding='utf-8', errors='replace').read()

        check('F2. THE SWEEP REALLY STARTED -- the paired positive, without '
              'which a clean tree only proves the process died at import',
              'criteria lock' in _out or 'DEAD RULE SWEEP' in _out,
              _out[:400] or '(no output at all)')
        check('F3. NO TRACKED FILE WAS MODIFIED WHILE THE SWEEP WAS WORKING. '
              'This is the arm the restore-in-finally cannot satisfy: the '
              'finally is not reached when the process is killed, and the first '
              'full run left 20 tool sources written in a shared clone',
              not _seen,
              'modified DURING the run: %s' % (_seen[:6],))
        check('F4. ...and the tree is clean after the kill too%s'
              % ('' if not _ran_to_completion else ' (it finished on its own)'),
              not _dirty(), _dirty()[:6])
        check('F5. the sweep NAMES the copy it worked in, so a reader can tell '
              'an isolated run from an in-place one without reading the source',
              'sandbox:' in _out, _out[:600])
    finally:
        subprocess.run(['git', '-C', REPO, 'worktree', 'remove', '--force', _wt],
                       capture_output=True, text=True)
        shutil.rmtree(_wt, ignore_errors=True)

# ── F6. THE SANDBOX IS REMOVED, AND A SANDBOX THAT CANNOT BE MADE IS EXIT 2 ─
# Not a fallback to the real clone. A tool that quietly works in place when its
# copy fails is the original defect wearing a new branch (PR 1.11): "could not
# isolate" is a third state and is never folded into "ran".
rc, out = run('--fixtures')
_m = __import__('re').search(r'sandbox:\s*(\S.*?)\s*$', out, __import__('re').M)
check('F6. --fixtures needs no sandbox and makes none, so the criteria lock '
      'stays runnable with no disk to copy 90MB onto', _m is None, out[:300])

# THE FIRST ATTEMPT AT THIS ARM WAS VACUOUS, AND IS RECORDED RATHER THAN
# QUIETLY REPLACED: it set TMPDIR/TEMP/TMP to a nonexistent path and expected
# mkdtemp to fail. IT DOES NOT -- tempfile walks its candidate list and falls
# through to a real directory, so the sweep ran completely normally and the arm
# was asserting nothing while reading like a refusal test. The tool now honours
# an explicit sandbox-parent override for exactly this purpose, the same way
# criticality_tier_check.py takes SAIRN_TIER_REGISTER so its parser can be
# DRIVEN rather than only observed.
def _tools_state():
    r = subprocess.run(['git', '-C', REPO, 'status', '--porcelain', '--', 'tools/'],
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace')
    return sorted(l for l in (r.stdout or '').split('\n') if l.strip())


# BEFORE/AFTER, NOT ABSOLUTE CLEANLINESS. The first version of F8 asserted
# `git diff --quiet -- tools/` and went red on the author's own uncommitted
# edit to the sweep -- an arm measuring the session rather than the subject,
# which is the shape this repo keeps paying for in probe anchors.
_tools_before = _tools_state()

_badtmp = os.path.join(REPO, 'no', 'such', 'dir', 'anywhere')
_r = subprocess.run([sys.executable, TOOL, '--tool',
                     'assertion_label_shape_check.py'], cwd=REPO,
                    capture_output=True, text=True, encoding='utf-8',
                    errors='replace',
                    env=dict(os.environ, PYTHONIOENCODING='utf-8',
                             PYTHONUTF8='1',
                             SAIRN_DRS_SANDBOX_PARENT=_badtmp))
check('F7. with no writable temp directory the sweep exits 2 COULD NOT RUN and '
      'does NOT fall back to mutating the clone -- "could not isolate" is a '
      'third state, never folded into "ran"',
      _r.returncode == 2 and 'COULD NOT RUN' in (_r.stdout or '') + (_r.stderr or ''),
      'exit=%s out=%s' % (_r.returncode,
                          ((_r.stdout or '') + (_r.stderr or ''))[-400:]))
check('F8. ...and the refusal path changed NOTHING under tools/ in this clone',
      _tools_state() == _tools_before,
      'before=%s after=%s' % (_tools_before, _tools_state()))


# ── F9. THE SANDBOX DOES NOT ACCUMULATE ────────────────────────────────────
# The honest trade this fix makes is a leftover directory OUTSIDE the clone in
# place of a neutralised rule INSIDE it -- a killed sweep cannot run its own
# cleanup, and F3 above kills one every time this control runs. `git worktree
# prune` does NOT collect those: it only forgets entries whose directory is
# already gone. So the sweep reaps its own by NAME on the way in and on the way
# out, and this arm is what stops that from silently regressing into a clone
# carrying one stale worktree per probe run.
def _sandboxes():
    r = subprocess.run(['git', '-C', REPO, 'worktree', 'list', '--porcelain'],
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace')
    return [l[len('worktree '):].strip()
            for l in (r.stdout or '').split('\n')
            if l.startswith('worktree ')
            and os.path.basename(l.strip().rstrip('/\\')).startswith('drs-sandbox-')]


rc, out = run('--tool', 'assertion_label_shape_check.py')
check('F9a. a normal run finishes and names a sandbox',
      rc in (0, 1) and 'sandbox:' in out, (rc, out[:300]))
check('F9b. ...and leaves NO drs-sandbox- worktree registered afterwards, '
      'including the one F3 killed above -- otherwise every run of this '
      'control adds one to the clone forever',
      not _sandboxes(), _sandboxes())

print('\n%s -- %d passed, %d failed' % ('FAIL' if _fail else 'ALL ARMS PASS',
                                        _pass, _fail))
sys.exit(1 if _fail else 0)
