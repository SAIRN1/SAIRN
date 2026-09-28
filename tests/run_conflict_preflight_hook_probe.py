"""Does the pre-flight shim fire in the one state it is for, and stay out of
the way in every other -- and does it keep FOUND and COULD-NOT-RUN apart?

    python tests/run_conflict_preflight_hook_probe.py

WHY THIS EXISTS. The shim's whole value is a conditional: it must be
near-free on every ordinary Bash call and must run the 7-second pre-flight
during a rebase. Both halves are silent when they are wrong -- a shim that
never fires looks exactly like a clean repo, and one that always fires gets
switched off within the hour. Neither is visible without driving it.

NOTHING HERE TOUCHES THE REAL .git DIRECTORY. Every operation state is a
fabricated directory in a temp tree, because writing MERGE_HEAD into a live
clone to test a hook is the kind of thing that leaves a repo mid-merge.
"""
import io
import os
import subprocess
import sys
import tempfile
import shutil

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import conflict_marker_preflight_hook as hook           # noqa: E402

fails = []


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name
          + ('' if cond else '\n         ' + str(detail)[:400]))
    if not cond:
        fails.append(name)


print('\n1. THE DISCRIMINATOR -- which states count as an operation')
tmp = tempfile.mkdtemp(prefix='sairn-preflight-hook-')
try:
    gd = os.path.join(tmp, '.git')
    os.makedirs(gd)
    check('a clean .git is NOT an operation', hook.operation_in_progress(gd) is None,
          hook.operation_in_progress(gd))

    # The four shapes git actually writes. Each is created ALONE and removed
    # after, so a later one cannot be satisfied by an earlier one's leftovers --
    # which would make this section pass on a function that only checks the
    # first.
    for name, maker, want in (
            ('rebase-merge', lambda: os.makedirs(os.path.join(gd, 'rebase-merge')), 'rebase'),
            ('rebase-apply', lambda: os.makedirs(os.path.join(gd, 'rebase-apply')), 'rebase'),
            ('MERGE_HEAD', lambda: io.open(os.path.join(gd, 'MERGE_HEAD'), 'w').close(), 'merge'),
            ('CHERRY_PICK_HEAD', lambda: io.open(os.path.join(gd, 'CHERRY_PICK_HEAD'), 'w').close(), 'cherry-pick'),
            ('REVERT_HEAD', lambda: io.open(os.path.join(gd, 'REVERT_HEAD'), 'w').close(), 'revert')):
        maker()
        got = hook.operation_in_progress(gd)
        check('%s reads as %s' % (name, want), got == want, 'got %r' % got)
        p = os.path.join(gd, name)
        shutil.rmtree(p, ignore_errors=True)
        if os.path.isfile(p):
            os.remove(p)
    check('CONTROL -- removing every marker returns to None',
          hook.operation_in_progress(gd) is None,
          'the teardown above did not actually clear the state, so every arm '
          'after the first was checking a repo that still looked mid-rebase')
    check('an unresolvable git dir is None rather than a guess',
          hook.operation_in_progress(None) is None)
finally:
    shutil.rmtree(tmp, ignore_errors=True)


print('\n2. THE REAL REPO -- the no-op path, and what it costs')
# This clone is not mid-operation while a probe runs, so this is the common
# case and the one the shim exists to make cheap.
import time                                                   # noqa: E402
t0 = time.time()
r = subprocess.run([sys.executable,
                    os.path.join(REPO, 'tools', 'conflict_marker_preflight_hook.py')],
                   cwd=REPO, capture_output=True, text=True,
                   encoding='utf-8', errors='replace', timeout=120)
elapsed = time.time() - t0
check('the shim exits 0 on a clean tree', r.returncode == 0,
      'rc=%s out=%s' % (r.returncode, (r.stdout or '') + (r.stderr or '')))
check('...and says NOTHING when there is no operation in progress',
      not (r.stdout or '').strip() and not (r.stderr or '').strip(),
      'it printed %r -- a hook that speaks on every Bash call is noise, and '
      'noise is how a real warning gets skipped'
      % ((r.stdout or '') + (r.stderr or ''))[:200])
print('       measured: %.2fs' % elapsed)
check('...and the no-op path is under 2 seconds', elapsed < 2.0,
      'took %.2fs. The full pre-flight is ~7s over 2,670 paths and that is the '
      'cost this shim exists to avoid paying on every Bash call.' % elapsed)


print('\n3. FOUND AND COULD-NOT-RUN ARE KEPT APART -- driven, not read')
# The pre-flight is REPLACED by a stub that exits with a chosen code, so the
# shim's own branching is what is under test rather than the pre-flight's.
tmp2 = tempfile.mkdtemp(prefix='sairn-preflight-stub-')
try:
    real_tool, real_op = hook.TOOL, hook.operation_in_progress
    said_by_code = {}
    for code, must_say, must_not_say in (
            (1, 'FOUND SOMETHING', 'COULD NOT RUN'),
            (2, 'COULD NOT RUN', 'FOUND SOMETHING'),
            (0, 'CLEAN', 'FOUND SOMETHING')):
        stub = os.path.join(tmp2, 'stub%d.py' % code)
        io.open(stub, 'w', encoding='utf-8').write(
            'import sys\nprint("stub output line")\nsys.exit(%d)\n' % code)
        hook.TOOL = stub
        hook.operation_in_progress = lambda _gd: 'rebase'
        buf = io.StringIO()
        old = sys.stderr
        sys.stderr = buf
        try:
            rc = hook.main()
        finally:
            sys.stderr = old
        said = buf.getvalue()
        said_by_code[code] = said
        check('pre-flight exit %d says %r' % (code, must_say), must_say in said,
              'it said: %s' % said[:300])
        check('...and does NOT say %r' % must_not_say, must_not_say not in said,
              'it said: %s' % said[:300])
        check('...and the shim itself still exits 0 (warn, never deny)', rc == 0,
              'rc=%r. Denying Bash mid-rebase makes the tool that helps you '
              'finish a rebase unusable inside one, which is how it gets '
              'switched off.' % rc)
    # THE CONTROL, AND THE FIRST VERSION OF IT WAS `check(..., True, '')` --
    # a decorative control that could not fail, which is the exact defect class
    # this session has spent the week finding in other people's tools. It now
    # compares the three captured texts: without this, a shim that printed all
    # three banners on every exit code satisfies every arm above.
    check('CONTROL -- the three outcomes produce DIFFERENT text',
          len(set(said_by_code.values())) == 3,
          'the shim produced %d distinct message(s) for exit codes 0, 1 and 2, '
          'so the arms above are checking one string three times: %r'
          % (len(set(said_by_code.values())),
             {k: v[:60] for k, v in said_by_code.items()}))
    hook.TOOL, hook.operation_in_progress = real_tool, real_op

    # A MISSING PRE-FLIGHT IS NAMED, NOT SILENTLY SKIPPED.
    hook.TOOL = os.path.join(tmp2, 'does_not_exist.py')
    hook.operation_in_progress = lambda _gd: 'merge'
    buf = io.StringIO()
    old = sys.stderr
    sys.stderr = buf
    try:
        rc = hook.main()
    finally:
        sys.stderr = old
    check('a MISSING pre-flight during an operation is named, not silence',
          'MISSING' in buf.getvalue() and 'unchecked' in buf.getvalue(),
          buf.getvalue()[:300])
    check('...and still exits 0', rc == 0)
    hook.TOOL, hook.operation_in_progress = real_tool, real_op
finally:
    shutil.rmtree(tmp2, ignore_errors=True)


print('\n4. THE WIRING ITSELF -- a hook nothing registers is a file')
import json                                                   # noqa: E402
cfg = json.load(io.open(os.path.join(REPO, '.claude', 'settings.json'),
                        encoding='utf-8'))
wired = json.dumps(cfg)
check('conflict_marker_preflight_hook.py is registered in .claude/settings.json',
      'conflict_marker_preflight_hook.py' in wired,
      'the shim exists and nothing runs it, which is the state the tool it '
      'wraps was already in')
check('...as a PreToolUse hook, so it fires BEFORE the --continue lands',
      'conflict_marker_preflight_hook.py' in json.dumps(cfg.get('PreToolUse')
                                                        or cfg.get('hooks', {}).get('PreToolUse')),
      'a PostToolUse registration would report the marker AFTER the commit it '
      'was meant to prevent')

print('\n%s  conflict_preflight_hook probe: %d failed'
      % ('FAILED' if fails else 'ok', len(fails)))
sys.exit(1 if fails else 0)
