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
# ── WHAT SECTION A MUTATES: A COPY, OUTSIDE THIS CLONE ─────────────────────
# Section A has to break the sweep's criteria lock to prove the lock is
# load-bearing, and until 2026-09-30 it broke the TRACKED file and put it back
# in a `finally` -- the same defect the sweep itself was fixed for that morning
# (80c5984c), one layer up, inside its own control. A restore reached only on a
# normal exit is not isolation.
#
# A SCRATCH TREE RATHER THAN A LONE FILE: the sweep computes
# REPO = dirname(dirname(__file__)) and imports checker_kit from REPO/tools, so
# a copy dropped anywhere else cannot import and section A would be measuring an
# ImportError instead of the lock. tools/ is reproduced with the two modules the
# --fixtures path actually needs, and nothing else.
_SBX = tempfile.mkdtemp(prefix='drs-sabotage-')
os.makedirs(os.path.join(_SBX, 'tools'), exist_ok=True)
for _m in ('dead_rule_sweep.py', 'checker_kit.py'):
    _s = os.path.join(REPO, 'tools', _m)
    if os.path.isfile(_s):
        io.open(os.path.join(_SBX, 'tools', _m), 'w', encoding='utf-8',
                newline='').write(io.open(_s, encoding='utf-8',
                                          newline='').read())
SABOTAGE_TOOL = os.path.join(_SBX, 'tools', 'dead_rule_sweep.py')
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


def run_copy(*args):
    """The sabotage copy, in its own scratch tree. Never this clone."""
    r = subprocess.run([sys.executable, SABOTAGE_TOOL] + list(args), cwd=_SBX,
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace',
                       env=dict(os.environ, PYTHONIOENCODING='utf-8',
                                PYTHONUTF8='1'))
    return r.returncode, (r.stdout or '') + (r.stderr or '')


def run(*args):
    r = subprocess.run([sys.executable, TOOL] + list(args), cwd=REPO,
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace',
                       env=dict(os.environ, PYTHONIOENCODING='utf-8',
                                PYTHONUTF8='1'))
    return r.returncode, (r.stdout or '') + (r.stderr or '')


print('DEAD RULE SWEEP -- the control for the sweep')

# ── G. THIS FILE MUST NOT DO THE THING IT EXISTS TO CATCH ──────────────────
# Section A used to sabotage tools/dead_rule_sweep.py IN THIS CLONE and restore
# it in a `finally` -- the defect the sweep itself was fixed for on 2026-09-30
# (80c5984c), one layer up, inside the control for it. Named in that fix commit
# and in the defect register's recurrence_open, and fixed here.
#
# THE ARM IS STRUCTURAL, NOT BEHAVIOURAL, and that is the point. A behavioural
# arm can only observe a run that FINISHED, and a `finally` always runs on those
# -- which is exactly why D5 stayed green for as long as the defect existed. The
# only paths that expose it are the ones no assertion inside the process can
# reach: SIGKILL, a harness timeout, a closed laptop. So the check is on the
# TARGET rather than on the outcome: nothing in this file may open a tracked
# file for writing, whatever happens afterwards.
section('G. this control does not write the clone it is controlling')

_self_src = io.open(os.path.abspath(__file__), encoding='utf-8',
                    newline='').read()
check('G1. SABOTAGE_TOOL is OUTSIDE this clone -- section A mutates a copy, so '
      'there is no restore to fail to reach',
      not os.path.abspath(SABOTAGE_TOOL).startswith(os.path.abspath(REPO)
                                                    + os.sep),
      'SABOTAGE_TOOL=%s is under REPO=%s' % (SABOTAGE_TOOL, REPO))
# THE NEEDLE IS ASSEMBLED, NOT SPELLED, AND THE FIRST VERSION WAS WRONG BECAUSE
# IT WAS SPELLED. A grep arm that writes its own search string as a literal
# matches ITSELF and stays red forever after the defect is fixed -- which is
# what happened here: G2 failed on its own source once the real write was gone.
# Building it from pieces keeps the arm about the rest of the file.
_WRITE_SITES = tuple('open(TOOL,%s%sw%s' % (_sp, _q, _q)
                     for _q in (chr(39), chr(34))
                     for _sp in ('', ' '))
check('G2. no write to the tracked tool appears in this file at all -- the '
      'grep is the arm, because a write guarded by a `finally` reads as safe '
      'and is only safe on the paths the interpreter reaches',
      not [n for n in _WRITE_SITES if n in _self_src],
      'this file still opens the tracked tool for writing: %s'
      % [n for n in _WRITE_SITES if n in _self_src])
check('G2b. ...and the needles really would match if a write came back -- a '
      'grep arm that cannot find its own subject is decoration. Driven '
      'against a synthesised line, both quote styles and both spacings',
      all(any(n in line for n in _WRITE_SITES)
          for line in ('%s%s%sw%s).write(x)' % ('io.', 'open(TOOL,', q, q)
                       for q in (chr(39), chr(34)))),
      _WRITE_SITES)
check('G3. ...and the tracked tool is still READ, so G2 was satisfied by '
      'moving the write rather than by deleting the subject',
      'io.open(TOOL, encoding=' in _self_src)

# ── A. THE CRITERIA LOCK GATES THE RUN ─────────────────────────────────────
section('A. break the rewrite and the sweep must REFUSE, not report clean')
rc, out = run('--fixtures')
check('A1. the lock passes on the shipped criteria', rc == 0
      and 'fixtures classify correctly' in out, (rc, out[-300:]))

# THE COPY IS THE SUBJECT, and it is verified to BE a copy before it is broken.
# A sabotage applied to an empty or missing file would exit 2 for the wrong
# reason and read exactly like A2 passing.
_orig = io.open(TOOL, encoding='utf-8', newline='').read()
check('A1b. the scratch copy is byte-identical to the tracked tool, so A2 '
      'breaks the REAL criteria lock and not some other file',
      io.open(SABOTAGE_TOOL, encoding='utf-8', newline='').read() == _orig,
      SABOTAGE_TOOL)
rc, out = run_copy('--fixtures')
check('A1c. ...and the COPY passes the lock before anything is done to it, so '
      'A2 measures the sabotage rather than the copying',
      rc == 0 and 'fixtures classify correctly' in out, (rc, out[-300:]))

_sab = _orig.replace('NEVER = "(?!x)x"', 'NEVER = "(?!x)x"  # noqa\nNEVER = ""', 1)
check('A2a. THE SABOTAGE APPLIED -- without this A2 proves nothing',
      _sab != _orig, 'the NEVER anchor moved')
io.open(SABOTAGE_TOOL, 'w', encoding='utf-8', newline='').write(_sab)
rc, out = run_copy('--fixtures')
check('A2. ...and with the never-matching pattern emptied the lock FAILS '
      'and the sweep exits 2. A sweep whose own rewrite is broken reports '
      'every rule as dead, which is the loudest possible wrong answer',
      rc == 2 and 'CRITERIA LOCK FAILED' in out, (rc, out[-400:]))
# NO `finally` AND NO RESTORE, and the absence IS the fix. There is nothing to
# put back: the tracked file was never opened for writing, so there is no window
# in which a kill leaves a neutralised tool behind in a clone four sessions push
# from.
rc, out = run('--fixtures')
check('A3. THE TRACKED TOOL IS UNTOUCHED THROUGHOUT -- it still passes its own '
      'lock, and it never needed restoring', rc == 0, (rc, out[-200:]))

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
                       capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
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


def _abandoned_sandboxes():
    """Sandboxes with no LIVE owner -- the only ones that are a leak.

    F9b used to assert the registered set was EMPTY, which was the right
    contract while the reap deleted every matching directory. The owner-aware
    reap (2026-10-06) changed that contract deliberately: a sandbox belonging to
    a live process is KEPT, because deleting it is what killed a 151-tool run.
    MEASURED THE DAY THE GUARD LANDED -- this arm failed while a legitimate
    concurrent sweep was running, owner pid 51032, alive. THE ARM WAS ASSERTING
    THE OLD CONTRACT; loosening it to "no ABANDONED sandbox" keeps the original
    intent (this control must not leak one per run) without re-opening the hole.
    """
    out = []
    for p in _sandboxes():
        owner = D._sandbox_owner(p)
        if owner is not None and owner != os.getpid() and D._pid_alive(owner):
            continue          # somebody else's live run; protected on purpose
        out.append(p)
    return out


rc, out = run('--tool', 'assertion_label_shape_check.py')
check('F9a. a normal run finishes and names a sandbox',
      rc in (0, 1) and 'sandbox:' in out, (rc, out[:300]))
check('F9b. ...and leaves NO ABANDONED drs-sandbox- worktree registered '
      'afterwards, including the one F3 killed above -- otherwise every run of '
      'this control adds one to the clone forever. A sandbox owned by another '
      'LIVE process is excluded, because keeping it is the 2026-10-06 fix',
      not _abandoned_sandboxes(), _abandoned_sandboxes())
check('F9c. CONTROL for F9b: the raw registered set is reported too, so '
      '"no abandoned sandbox" can never be read as "no sandbox" -- a live '
      'concurrent run is a different fact from a clean clone',
      True, 'registered now: %s' % (_sandboxes() or 'none'))

# ── H. THE WRITER TIER, AND THE NEGATIVE ARM IS THE ONLY REASON TO TRUST IT ─
# Added 2026-10-06 with the tier. On its first real run the tier cleared all 22
# rules that had been COULD NOT RUN and reported EVERY ONE of them exercised.
# A tier that can only say "exercised" would produce exactly that output, and
# it would be the fail-open shape this whole file exists to catch. So H2 below
# is the arm that matters: a rule the writer provably does not use must come
# back DEAD, from the same tier, in the same run.
#
# EVERY FIXTURE WRITES NOTHING TO STDOUT. That is deliberate. If stdout were
# carrying the signal, the tier could pass these arms while the FILE comparison
# did nothing -- and a generator that rewrites a whole document without changing
# a byte of stdout is the normal case, not the edge case. With stdout empty and
# identical throughout, only the digest of what was WRITTEN can tell these arms
# apart.
section('H. the writer tier -- reset, reproducibility, and a rule it must call '
        'DEAD')


def _git(tree, *args):
    return subprocess.run(['git', '-C', tree] + list(args),
                          capture_output=True, text=True, encoding='utf-8',
                          errors='replace')


def _writer_tree(body):
    """A throwaway git repo holding one hand-built writer tool. Never the clone."""
    t = tempfile.mkdtemp(prefix='drs-writer-')
    os.makedirs(os.path.join(t, 'tools'), exist_ok=True)
    os.makedirs(os.path.join(t, 'docs'), exist_ok=True)
    io.open(os.path.join(t, 'docs', 'data.txt'), 'w', encoding='utf-8',
            newline='\n').write('alpha one\nbeta two\nalpha three\n')
    io.open(os.path.join(t, 'docs', 'out.txt'), 'w', encoding='utf-8',
            newline='\n').write('BASELINE\n')
    io.open(os.path.join(t, 'tools', 'w.py'), 'w', encoding='utf-8',
            newline='\n').write(body)
    _git(t, 'init', '-q')
    _git(t, 'config', 'user.email', 'probe@example.invalid')
    _git(t, 'config', 'user.name', 'probe')
    _git(t, 'add', '-A')
    _git(t, 'commit', '-q', '-m', 'fixture')
    return t


# USED feeds the written file; UNUSED is compiled, documented and never read --
# the precise shape of the 2026-09-29 defect this sweep was built for.
_W_BODY = '''import io, os, re
USED = re.compile(r'alpha')
UNUSED = re.compile(r'zzz-never-read')
D = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = io.open(os.path.join(D, 'docs', 'data.txt'), encoding='utf-8').read()
io.open(os.path.join(D, 'docs', 'out.txt'), 'w', encoding='utf-8',
        newline='\\n').write('\\n'.join(USED.findall(src)) + '\\n')
'''

_wt = _writer_tree(_W_BODY)
try:
    _wp = os.path.join(_wt, 'tools', 'w.py')
    _worig = io.open(_wp, encoding='utf-8', newline='').read()
    _wpats = D.module_patterns(_worig)
    _before_clone = D._porcelain(REPO)
    _rows = dict(D.sweep_writer('w.py', _wp, _worig, _wpats, _wt))

    check('H1. the writer tier RAN at all -- a verdict for every rule, not a '
          'blanket refusal',
          set(_rows) == {'USED', 'UNUSED'}, _rows)
    check('H2. THE NEGATIVE ARM: a rule the writer never reads comes back DEAD. '
          'Without this, "all 22 exercised" is indistinguishable from a tier '
          'that can only say exercised',
          _rows.get('UNUSED') == D.DEAD_WRITER, _rows.get('UNUSED'))
    check('H3. ...and the rule it DOES read comes back exercised, from the same '
          'run -- the paired positive, so H2 is not passing because the tier is '
          'simply broken',
          _rows.get('USED') == D.LIVE_WRITER, _rows.get('USED'))
    check('H4. STDOUT WAS IDENTICAL THROUGHOUT, so only the digest of the '
          'WRITTEN FILE could have told H2 and H3 apart',
          _rows.get('USED') != _rows.get('UNUSED'))
    check('H5. the fixture tool source is byte-identical after the tier -- the '
          'per-rule restore happened inside the copy',
          io.open(_wp, encoding='utf-8', newline='').read() == _worig)
    check('H6. the written file is back to its committed baseline -- the RESET '
          'worked, which is what makes each run a comparison rather than a '
          'reading of the previous run output',
          io.open(os.path.join(_wt, 'docs', 'out.txt'),
                  encoding='utf-8').read() == 'BASELINE\n',
          io.open(os.path.join(_wt, 'docs', 'out.txt'), encoding='utf-8').read())
    check('H7. the fixture tree is CLEAN afterwards -- nothing left dirty for '
          'the next comparison to inherit',
          D._porcelain(_wt) == {}, D._porcelain(_wt))
    check('H8. and THIS CLONE was not touched while a writer ran',
          D._porcelain(REPO) == _before_clone)
finally:
    shutil.rmtree(_wt, ignore_errors=True)

# A writer nobody can compare: the output depends on the process, not the rule.
# It must come back NOT REPRODUCIBLE -- never exercised, and never dead either.
_ND_BODY = '''import io, os, re
R = re.compile(r'alpha')
D = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
io.open(os.path.join(D, 'docs', 'out.txt'), 'w', encoding='utf-8',
        newline='\\n').write('%d\\n' % os.getpid())
'''
_nt = _writer_tree(_ND_BODY)
try:
    _np = os.path.join(_nt, 'tools', 'w.py')
    _norig = io.open(_np, encoding='utf-8', newline='').read()
    _nrows = dict(D.sweep_writer('w.py', _np, _norig,
                                 D.module_patterns(_norig), _nt))
    check('H9. a writer whose two identical baseline runs DIFFER is reported '
          'NOT REPRODUCIBLE -- a finding about the tool, not a verdict about '
          'its rule',
          _nrows.get('R') == D.WRITES_NONDET, _nrows.get('R'))
    check('H10. ...and it is NOT folded into exercised, and NOT into dead '
          'either -- three states, and this is the third',
          _nrows.get('R') not in (D.LIVE_WRITER, D.DEAD_WRITER))
finally:
    shutil.rmtree(_nt, ignore_errors=True)

# ── I. A CONCURRENT RUN MUST NOT REAP A LIVE SANDBOX ───────────────────────
# Measured 2026-10-06: the first full 151-tool run died 29 tools in with a
# FileNotFoundError naming tools/copy_exactly_gate.py, because a one-tool
# `--tool register_feed_gate.py` run was started in another shell and the reap
# deleted every drs-sandbox- directory regardless of owner. The victim's 28
# tools of verdicts went with it and nothing said what had happened -- it read
# like a defect in the tool being swept.
#
# THE NEGATIVE ARM IS I2. A reap that never deletes anything would pass I1
# trivially, so the dead-owner case has to be proved in the same run.
section('I. the reap is owner-aware -- a live run keeps its sandbox')


def _mk_marked(owner_pid):
    """A registered sandbox carrying a given owner pid. Reaped by the arms."""
    p = D.make_sandbox()
    if p and owner_pid is not None:
        io.open(os.path.join(p, D.OWNER_FILE), 'w', encoding='utf-8',
                newline='\n').write('%d\n' % owner_pid)
    return p


# A LIVE pid THAT IS NOT OURS, which is the only shape that matters: the reap
# deliberately DOES collect a tree marked with its own pid, because make_sandbox
# reaps on the way in and drop_sandbox on the way out. Marking the fixture with
# os.getpid() tested the wrong thing and failed -- recorded rather than quietly
# swapped, because the first version of this arm was wrong and passing it by
# changing production code would have removed the guard it is here to prove.
_helper = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(120)'])
try:
    _live = _mk_marked(_helper.pid)
    check('I0. a sandbox was made and carries an owner marker at all',
          _live is not None and os.path.isfile(os.path.join(_live, D.OWNER_FILE)),
          _live)
    check('I0b. CONTROL: the helper pid reads as ALIVE, and is not ours',
          D._pid_alive(_helper.pid) and _helper.pid != os.getpid(), _helper.pid)
    _skipped = D.reap_stale_sandboxes()
    check('I1. a sandbox owned by ANOTHER LIVE process SURVIVES the reap, and '
          'the reap says it skipped it -- this is the arm the 151-tool run '
          'needed and did not have',
          os.path.isdir(_live) and any(
              os.path.normcase(p) == os.path.normcase(_live)
              for p, _o in _skipped),
          (os.path.isdir(_live), _skipped))
finally:
    _helper.kill()
    _helper.wait()

# A pid that cannot be alive: the owner marker is rewritten to a free high pid.
# 0 and negative are rejected by tasklist/os.kill differently, so a plausible
# but dead pid is the honest fixture.
_dead_pid = 2
for _cand in range(999990, 999950, -1):
    if not D._pid_alive(_cand):
        _dead_pid = _cand
        break
check('I2a. CONTROL: the fixture pid really does read as dead, or every arm '
      'below is measuring nothing', not D._pid_alive(_dead_pid), _dead_pid)
if _live and os.path.isdir(_live):
    io.open(os.path.join(_live, D.OWNER_FILE), 'w', encoding='utf-8',
            newline='\n').write('%d\n' % _dead_pid)
    D.reap_stale_sandboxes()
    check('I2b. THE NEGATIVE ARM: the same sandbox, re-marked with a DEAD '
          'owner, IS reaped -- so I1 is not passing because the reap simply '
          'stopped deleting things',
          not os.path.isdir(_live), _live)
else:
    check('I2b. THE NEGATIVE ARM: the same sandbox, re-marked with a DEAD '
          'owner, IS reaped', False,
          'I1 left no sandbox to re-mark, so the negative half could not run '
          '-- reported, not skipped')

_unmarked = D.make_sandbox()
if _unmarked:
    try:
        os.unlink(os.path.join(_unmarked, D.OWNER_FILE))
    except OSError:
        pass
D.reap_stale_sandboxes()
check('I3. a sandbox with NO marker is still reaped -- a tree left by the '
      'pre-2026-10-06 version must not become permanent',
      _unmarked is not None and not os.path.isdir(_unmarked), _unmarked)

check('I4. "could not tell" is never a licence to delete -- _pid_alive returns '
      'True for a pid it cannot ask about',
      D._pid_alive(os.getpid()) is True)

# ── J. THE ESCAPE CHECK MUST NOT ACCUSE AN INNOCENT TOOL ────────────────────
# Measured 2026-10-06: the escape check fired against
# tools/primitive_obsession_check.py 23 minutes into a 151-tool run and VOIDED
# IT. That tool is innocent -- driven alone on a clean tree the clone is
# byte-identical afterwards. THE CAUSE WAS MY OWN `git commit` IN THE CLONE
# WHILE THE SWEEP RAN, and the message named the tool as the writer.
#
# Same defect class as the push_retry message routed to fourth this session: a
# guard that detects a real change and attributes it to the wrong actor.
#
# J2 IS THE NEGATIVE ARM. A guard that simply stopped checking would pass J1.
section('J. a commit in the clone is not a writer escaping')

_st = D._clone_state()
check('J0. the clone state reads at all, and carries BOTH halves -- a dirty-set '
      'comparison alone is what made the false accusation possible',
      _st is not None and len(_st) == 2 and isinstance(_st[0], str),
      _st if _st is None else (_st[0][:8], len(_st[1])))
check('J1. the accused tool really is innocent: driven alone it leaves the '
      'clone state unchanged, which is why the message had to change rather '
      'than the tool',
      (lambda b: (subprocess.run([sys.executable,
                                  os.path.join(REPO, 'tools',
                                               'primitive_obsession_check.py')],
                                 cwd=REPO, capture_output=True, text=True,
                                 encoding='utf-8', errors='replace'),
                  D._clone_state() == b)[1])(D._clone_state()))
_h1 = ('a' * 40, ('M tools/x.py',))
_h2 = ('b' * 40, ('M tools/x.py',))
_d1 = ('a' * 40, ('M tools/y.py',))
check('J2. THE NEGATIVE ARM: a state whose HEAD moved is DIFFERENT from one '
      'whose dirty set moved -- without this distinction the check cannot tell '
      'a commit from an escape and must either accuse or stop checking',
      _h1 != _h2 and _h1 != _d1 and _h1[0] == _d1[0] and _h1[1] == _h2[1])
check('J3. ...and an unreadable clone state is None, not an empty state -- it '
      'must raise "could not read", never "nothing changed"',
      D._clone_state() is not None and D._porcelain(os.path.join(
          tempfile.mkdtemp(prefix='drs-notgit-'), 'nope')) is None)

# J4/J5: the discriminator that decides escape-vs-churn. The tool's own written
# set comes from _writer_sig's fourth element; an INTERSECTION with the clone's
# churn is an escape, a DISJOINT change is somebody else's work. Measured the
# day it landed: my own `python tools/traceability_matrix.py` voided a 12-minute
# sweep and the message named criticality_tier_check.py.
_churn = ['docs/traceability-matrix.md']
_wrote_disjoint = {'docs/TOOLING-INVENTORY.md'}
_wrote_overlap = {'docs/traceability-matrix.md', 'docs/MASTER-PLAN.md'}
check('J4. a clone change DISJOINT from what the tool wrote in the sandbox is '
      'NOT an escape -- this is the arm that keeps a 47-minute run survivable '
      'while four sessions push',
      not (set(_churn) & _wrote_disjoint))
check('J5. THE NEGATIVE HALF: a clone change INTERSECTING what the tool wrote '
      'IS an escape, so J4 is not passing because the discriminator always '
      'says "not an escape"',
      bool(set(_churn) & _wrote_overlap))

# ── K. A TIMEOUT MUST NEVER BE LABELLED "NO LOCK, NO CONTROL" ──────────────
# Measured 2026-10-06: tools/cross_tenant_isolation_scope.py needs 131s, the
# bound was 45, and all 21 of its rules printed "no fixture lock and no control
# to ablate against". IT HAS NO LOCK -- and the real run WAS available and the
# sweep declined to wait, so the sentence was false about the half that mattered
# and 21 rules were read as unmeasurable for a week.
#
# K1 IS THE ARM THAT FAILS IF THAT EVER COMES BACK. It is not about the bound
# being right; it is about the two verdicts being DISTINGUISHABLE IN TEXT, which
# is what a reader skimming 150 findings actually sees.
section('K. a timeout says COULD NOT RUN with its bound, never "no lock, no '
        'control"')

_T = D.NO_EVIDENCE_TIMEOUT % 45
check('K1. THE TIMEOUT VERDICT NEVER SAYS "no lock" OR "no control" -- those '
      'words are what made 21 rules read as having no evidence when the '
      'evidence existed',
      'no lock' not in _T.lower() and 'no control' not in _T.lower(), _T)
check('K2. ...and it LEADS with COULD NOT RUN and names the bound in seconds, '
      'so the cause is the first thing read rather than the last',
      _T.startswith('COULD NOT RUN: bound 45s exceeded'), _T)
check('K3. THE NEGATIVE HALF: the genuine no-evidence verdict is still the one '
      'that says "no lock, no control" -- without this, K1 would pass if both '
      'verdicts had simply been blanked',
      'no lock' in D.NO_EVIDENCE and 'no control' in D.NO_EVIDENCE, D.NO_EVIDENCE)
check('K4. and the two are not the same string, so a reader can tell them '
      'apart at all', _T != D.NO_EVIDENCE)

# The bound itself: measured entries must carry 2x headroom, and an unmeasured
# tool must SAY it is on the default rather than look tuned.
check('K5. every TOOL_BOUNDS entry carries a measured runtime and a date, and '
      'the bound is at least 2x the measurement -- an entry without a '
      'measurement is a tuned-looking guess',
      all(isinstance(v, tuple) and len(v) == 3 and v[0] >= 2 * v[1] and v[2]
          for v in D.TOOL_BOUNDS.values()), D.TOOL_BOUNDS)
check('K6. bound_basis NAMES the default as not-measured, so a tuned bound and '
      'an untouched one are never printed the same way',
      'not measured' in D.bound_basis('a_tool_nobody_timed.py').lower()
      and 'measured' in D.bound_basis(sorted(D.TOOL_BOUNDS)[0]).lower(),
      (D.bound_basis('a_tool_nobody_timed.py'),
       D.bound_basis(sorted(D.TOOL_BOUNDS)[0])))
check('K7b. THE UNBOUNDABLE VERDICT never says "no lock" or "no control" '
      'either, and names >420s as the measurement -- the first version of this '
      'guard sat inside _bare_baseline(), which the WRITER tier never reaches, '
      'so run_all_tests.py still printed "no fixture lock and no control". '
      'Caught by DRIVING the tool, not by reading it',
      'no lock' not in (D.NO_EVIDENCE_UNBOUNDABLE % 'x').lower()
      and 'no control' not in (D.NO_EVIDENCE_UNBOUNDABLE % 'x').lower()
      and '420s' in D.NO_EVIDENCE_UNBOUNDABLE,
      D.NO_EVIDENCE_UNBOUNDABLE % 'x')
check('K7c. every UNBOUNDABLE entry carries the measurement, the date and WHY '
      'the real run is not evidence for it -- "it is slow" is not a reason, '
      '"its output is dominated by what it orchestrates" is',
      all(len(v) == 3 and 'did not finish' in v[0] and v[1] and len(v[2]) > 30
          for v in D.UNBOUNDABLE.values()), D.UNBOUNDABLE)
check('K7d. and UNBOUNDABLE and TOOL_BOUNDS are DISJOINT -- a tool cannot both '
      'have a measured bound and be unmeasurable',
      not (set(D.UNBOUNDABLE) & set(D.TOOL_BOUNDS)),
      set(D.UNBOUNDABLE) & set(D.TOOL_BOUNDS))
check('K7. an explicit --corpus-timeout beats a measured per-tool bound, '
      'because re-asking a closed question is the whole point of the flag',
      D.tool_bound(sorted(D.TOOL_BOUNDS)[0], 999) == 999)

# The sabotage scratch tree, removed. Outside this clone either way, so a
# leftover is untidy rather than dangerous -- which is the whole trade section G
# makes: debris in temp instead of a neutralised rule in a shared repo.
shutil.rmtree(_SBX, ignore_errors=True)

print('\n%s -- %d passed, %d failed' % ('FAIL' if _fail else 'ALL ARMS PASS',
                                        _pass, _fail))
sys.exit(1 if _fail else 0)
