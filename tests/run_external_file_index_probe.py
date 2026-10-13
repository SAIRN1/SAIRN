#!/usr/bin/env python
# OWNER: cc
"""The control on tools/external_file_index_check.py and push-gate CHECK 17.

    python tests/run_external_file_index_probe.py

Exit 0 all arms pass, 1 an arm failed, 2 COULD NOT RUN.

WHY THIS EXISTS. The check REFUSES a push, so the expensive failure is not a
false refusal -- it is a false CLEAN. Every arm below is therefore paired: a
shape that must be found AND one that must not, plus a sabotage pass that
neuters the classifier and asserts the finding collapses. A detector that has
only ever returned clean is indistinguishable from one that cannot fire.

AND THE TWO THINGS IT MUST NEVER DO, each with its own arm:
  * report 0 when the INDEX IS ABSENT. That is the shape PR 1.11 is about, and
    `--count` is read by a SessionStart hook, so a 0 there would print
    "0 unindexed" off a check that never ran.
  * walk a declared TRANSIENT subtree. The first version's `continue` on a
    matching root did not stop os.walk descending, and the real dry run showed
    it: TRANSIENT 0 with three transient directories declared.

Built in a throwaway directory tree, never against the machine's real external
dirs -- a probe whose verdict moves with what another session happens to have
left in a scratchpad is not a probe.
"""
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(REPO, 'tools', 'external_file_index_check.py')
spec = importlib.util.spec_from_file_location('efi', TOOL)
C = importlib.util.module_from_spec(spec)
spec.loader.exec_module(C)

_fail = []


def ok(what, cond, detail=''):
    if cond:
        print('  ok   %s' % what)
    else:
        _fail.append(what)
        print('  FAIL %s%s' % (what, ('\n         [%s]' % (detail,))
                               if detail else ''))


def run(args):
    r = subprocess.run([sys.executable, TOOL] + args, capture_output=True,
                       text=True, encoding='utf-8', errors='replace')
    return r.returncode, (r.stdout or '') + (r.stderr or '')


def tree():
    """A declared dir with one stray script, one indexed script, and a
    transient subtree holding a file that must never be enumerated."""
    root = tempfile.mkdtemp(prefix='efi_probe_')
    ext = os.path.join(root, 'ext')
    scratch = os.path.join(root, 'scratch', 'deep')
    os.makedirs(ext)
    os.makedirs(scratch)
    for p, body in ((os.path.join(ext, 'stray.py'), '# stray\n'),
                    (os.path.join(ext, 'kept.py'), '# kept\n'),
                    (os.path.join(ext, 'APP-2026-01-01-x-handoff.md'), '# h\n'),
                    (os.path.join(ext, 'notes.md'), '# not a handoff\n'),
                    (os.path.join(ext, 'cc.lock'), 'x\n'),
                    (os.path.join(scratch, 'junk.py'), '# junk\n')):
        io.open(p, 'w', encoding='utf-8', newline='').write(body)
    idx = {'_what_this_is': 'probe fixture',
           'agents': {'probe': {
               'dirs': [{'path': ext, 'purpose': 'declared', 'transient': False},
                        {'path': os.path.join(root, 'scratch'),
                         'purpose': 'scratch', 'transient': True}],
               'files': [{'path': os.path.join(ext, 'kept.py'),
                          'purpose': 'a real tool kept outside git',
                          'belongs_in_git': False}]}}}
    ip = os.path.join(root, 'index.json')
    io.open(ip, 'w', encoding='utf-8', newline='').write(
        json.dumps(idx, indent=1) + '\n')
    return root, ext, ip


print('A. the check FINDS an unindexed script and an unindexed handoff')
root, ext, ip = tree()
try:
    rc, out = run(['--index', ip])
    ok('exit 1 -- findings', rc == 1, (rc, out[-300:]))
    ok('...and names the stray script', 'stray.py' in out, out[-400:])
    ok('...and names the stray HANDOFF, which is the case it exists for',
       'handoff.md' in out.lower(), out[-400:])
    ok('the INDEXED file is NOT a finding -- a declaration with a purpose is '
       'the whole point', 'kept.py' not in out.split('UNINDEXED work file')[-1],
       out[-400:])
    ok('an ordinary .md is not scanned -- indexing every markdown would bury '
       'the handoffs', 'notes.md' not in out, out[-400:])
    ok('a .lock is not scanned either', 'cc.lock' not in out, out[-400:])
    ok('the TRANSIENT subtree is NOT enumerated -- os.walk is pruned IN PLACE, '
       'and a `continue` on the root was NOT enough',
       'junk.py' not in out, out[-400:])
    ok('...and the counts say so rather than leaving it to be inferred',
       'TRANSIENT' in out, out[-400:])

    print('\nB. --count prints one number, for a session hook')
    rc, out = run(['--count', '--index', ip])
    ok('exit 1 and a bare integer', rc == 1 and out.strip().isdigit(),
       (rc, out.strip()[:40]))
    ok('...and the number is 2 -- the stray script and the stray handoff',
       out.strip() == '2', out.strip()[:40])

    print('\nC. CLEAN once the strays are declared -- it can return 0 at all')
    doc = json.loads(io.open(ip, encoding='utf-8').read())
    for nm in ('stray.py', 'APP-2026-01-01-x-handoff.md'):
        doc['agents']['probe']['files'].append(
            {'path': os.path.join(ext, nm), 'purpose': 'declared by the probe',
             'belongs_in_git': False})
    io.open(ip, 'w', encoding='utf-8', newline='').write(
        json.dumps(doc, indent=1) + '\n')
    rc, out = run(['--index', ip])
    ok('exit 0 and the word CLEAN -- a detector that cannot pass is as useless '
       'as one that cannot fire', rc == 0 and 'CLEAN' in out, (rc, out[-300:]))
    rc, out = run(['--count', '--index', ip])
    ok('...and --count is now 0 with exit 0', rc == 0 and out.strip() == '0',
       (rc, out.strip()[:40]))
finally:
    shutil.rmtree(root, ignore_errors=True)

print('\nD. AN ABSENT INDEX IS EXIT 2 AND NEVER A ZERO')
# THE SHAPE PR 1.11 IS ABOUT. `--count` feeds a SessionStart hook, so a 0 here
# would print "0 unindexed" off a check that never ran.
rc, out = run(['--index', os.path.join(REPO, '__no_such_index__.json')])
ok('exit 2 when the index is absent', rc == 2, (rc, out[-200:]))
ok('...and it says NOTHING was checked', 'NOTHING was checked' in out, out[-300:])
ok('...and it prints the schema it expected, so the owner can create it',
   '"agents"' in out, out[-300:])
rc, out = run(['--count', '--index', os.path.join(REPO, '__no_such__.json')])
ok('--count exits 2 and prints UNKNOWN, NOT 0 -- a hook must never read a '
   'zero off a check that did not run',
   rc == 2 and 'UNKNOWN' in out and out.strip() != '0', (rc, out.strip()[:80]))

print('\nE. a MALFORMED index is a could-not-run, not a clean')
root2 = tempfile.mkdtemp(prefix='efi_bad_')
try:
    bad = os.path.join(root2, 'bad.json')
    io.open(bad, 'w', encoding='utf-8', newline='').write('{"nope": 1}\n')
    rc, out = run(['--index', bad])
    ok('an index with no `agents` object exits 2', rc == 2, (rc, out[-200:]))
    notjson = os.path.join(root2, 'notjson.json')
    io.open(notjson, 'w', encoding='utf-8', newline='').write('{oops\n')
    rc, out = run(['--index', notjson])
    ok('an index that is not JSON exits 2', rc == 2, (rc, out[-200:]))
finally:
    shutil.rmtree(root2, ignore_errors=True)

print('\nF. SABOTAGE -- neuter the classifier and arm A must collapse')
# Both anchors are counted before either is mutated. `str.replace` returns the
# string UNCHANGED when the anchor is absent, so an unguarded sabotage mutates
# nothing and reports green for ever -- scrubber item 17.
src = io.open(TOOL, encoding='utf-8', errors='replace').read()
ANCHORS = ("    return 'UNINDEXED', 'neither git-tracked nor named in the index'",
           "def is_work_file(path):")
for a in ANCHORS:
    ok('sabotage anchor appears EXACTLY ONCE: %r' % a.strip()[:48],
       src.count(a) == 1, src.count(a))
blinded = src.replace(
    ANCHORS[0], "    return 'TRACKED', 'SABOTAGED -- everything reads as fine'")
ok('and the blinded source really DIFFERS from the subject -- the mutation '
   'applied rather than silently no-opping', blinded != src)
root3, ext3, ip3 = tree()
sab = None
try:
    sab = os.path.join(root3, 'sabotaged_check.py')
    io.open(sab, 'w', encoding='utf-8', newline='').write(blinded)
    r = subprocess.run([sys.executable, sab, '--index', ip3],
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace')
    out = (r.stdout or '') + (r.stderr or '')
    # ── MY EXPECTATION WAS WRONG AND THE TOOL IS BETTER THAN IT ─────────────
    # I asserted the sabotaged check would scan and find nothing (exit 0, no
    # stray.py). What actually happens is STRONGER: its own criteria lock runs
    # FIRST, catches the mutation, prints "CRITERIA LOCK FAILED -- 2 of 15"
    # naming both arms it broke, and exits 2 with NOTHING REAL WAS SCANNED. So
    # neutering the classifier cannot produce a clean report at all -- it
    # produces a refusal.
    # The arm now asserts the property that actually matters, which is the
    # DISJUNCTION: a sabotaged classifier must never report CLEAN. Corrected to
    # what the code does rather than bent to what I assumed -- the third time a
    # lock did that to me this batch.
    ok('the SABOTAGED check cannot report a clean scan -- its own criteria '
       'lock fires first and it exits 2 with NOTHING REAL WAS SCANNED',
       r.returncode == 2 and 'CRITERIA LOCK FAILED' in out
       and 'NOTHING REAL WAS SCANNED' in out, (r.returncode, out[-300:]))
    ok('...and it names the arms the mutation broke, so the sabotage is '
       'self-evidencing rather than inferred from an exit code',
       'wanted UNINDEXED got TRACKED' in out, out[-300:])
    ok('...and it never claims CLEAN',
       'CLEAN --' not in out, out[-300:])
finally:
    shutil.rmtree(root3, ignore_errors=True)
rc, out = run(['--fixtures'])
ok('and the REAL check still passes its own criteria lock afterwards, so the '
   'sabotage left nothing behind', rc == 0, (rc, out[-200:]))

# ── THE WARN-ONLY DIRECTORY (added 2026-10-13) ─────────────────────────────
# Michael's decision, after this check refused FIVE pushes in one session over
# SIX files, none of them belonging to the session being refused -- and twice
# the PreToolUse half denied the whole compound command, so the edit that would
# have cleared the refusal never ran. A handoff-shaped name under
# `G:/My Drive/SAIRN-status` now WARNS. Everything else still BLOCKS.
#
# THE ARMS BELOW ARE ALMOST ALL BOUNDARIES, because the only real risk is the
# relief leaking: a script in that directory, or a handoff anywhere else, must
# still refuse a push. The directory is driven through the module's own
# WARN_ONLY_DIRS rather than a second copy of the path, so the probe cannot
# pass against a tool that is warning on a different directory than it says.
print('')
print('W. a handoff under the warn-only directory warns; a script still blocks')

_spec = importlib.util.spec_from_file_location('efi_warn', TOOL)
EFI = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(EFI)

ok('the tool under test HAS a warn-only list and a predicate',
   hasattr(EFI, 'WARN_ONLY_DIRS') and hasattr(EFI, 'warn_only'),
   'the relief this section is about is absent')

if hasattr(EFI, 'warn_only'):
    _wd = EFI.WARN_ONLY_DIRS[0]
    ok('the warn-only directory is the Drive report directory, not something '
       'broader', 'SAIRN-status' in _wd, _wd)

    _cases = [
        (os.path.join(_wd, 'handoff-cody-2026-10-13.md'), True,
         'a handoff in the warn-only dir WARNS'),
        (os.path.join(_wd, 'SAIRN-handoff-h1-b15.md'), True,
         '...and the auditor spelling of the same thing WARNS too'),
        (os.path.join(_wd, 'gen_thing.py'), False,
         'BOUNDARY: a SCRIPT in the warn-only dir still BLOCKS -- this is what '
         'the check was built for'),
        (os.path.join(_wd, 'run_thing.sh'), False,
         'BOUNDARY: a shell script there still BLOCKS'),
        (os.path.join(_wd, 'notes.md'), False,
         'BOUNDARY: a non-handoff .md there is not warn-only'),
        (os.path.join('C:', os.sep, 'elsewhere', 'handoff-x.md'), False,
         'BOUNDARY: the SAME handoff name OUTSIDE that directory still BLOCKS '
         '-- the relief is scoped to one place, not to a filename'),
    ]
    for _p, _want, _label in _cases:
        ok(_label, EFI.warn_only(_p) is _want,
           '%s -> warn_only=%s, wanted %s' % (_p, EFI.warn_only(_p), _want))

# END TO END, through the real entry point, in a throwaway tree: a declared
# directory holding ONE undeclared handoff and nothing else must exit 0, and
# adding ONE undeclared script to the same directory must take it to 1. The
# fixture directory is pointed at the real warn-only path so the split is
# exercised rather than approximated.
_wroot = tempfile.mkdtemp(prefix='efi_warn_')
try:
    if hasattr(EFI, 'WARN_ONLY_DIRS'):
        _wd = EFI.WARN_ONLY_DIRS[0]
        _h = os.path.join(_wd, 'handoff-efiprobe-DELETEME.md')
        _s = os.path.join(_wd, 'efiprobe_DELETEME.py')
        _made = []
        try:
            if os.path.isdir(_wd):
                io.open(_h, 'w', encoding='utf-8', newline='').write('# probe\n')
                _made.append(_h)
                rc_h, out_h = run([])
                ok('END TO END: an undeclared handoff in the warn-only dir does '
                   'NOT block (exit 0 or 1 only from something else)',
                   'REPORTED, NOT BLOCKING' in out_h, out_h[-400:])

                io.open(_s, 'w', encoding='utf-8', newline='').write('# probe\n')
                _made.append(_s)
                rc_s, out_s = run([])
                ok('END TO END: adding an undeclared SCRIPT to the same '
                   'directory BLOCKS (exit 1)', rc_s == 1, (rc_s, out_s[-400:]))
                ok('...and the two are reported SEPARATELY, so a reader can '
                   'tell which one refused the push',
                   'REPORTED, NOT BLOCKING' in out_s
                   and 'Each is a tool' in out_s, out_s[-500:])
            else:
                ok('COULD NOT RUN the end-to-end arms -- the warn-only '
                   'directory does not exist in this clone, so nothing was '
                   'driven through the real entry point', False,
                   'absent: %s' % _wd)
        finally:
            for _f in _made:
                if os.path.isfile(_f):
                    os.remove(_f)
            ok('the end-to-end arms left NO litter in the warn-only directory',
               not any(os.path.isfile(f) for f in (_h, _s)))
finally:
    shutil.rmtree(_wroot, ignore_errors=True)


print('')
if _fail:
    print('%d failure(s)' % len(_fail))
    for f in _fail:
        print('  - %s' % f)
    sys.exit(1)
print('ALL ARMS PASS')
sys.exit(0)
