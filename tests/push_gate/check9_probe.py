"""Push-gate check 9: the named guard and seam tests block a push.

WHY IT EXISTS. On 2026-09-10 a stranded PROBE fixture commit deleted
`service_methods: body.service_methods` from api/legal-deadlines.js and shipped.
api/_lib/deadline-endpoint-inputs.test.js -- named three lines above that very
line as "the guard against a third instance" -- FAILED EXACTLY AS DESIGNED and
could not stop it, because the suite is wired REPORT-ONLY after a push. Michael's
decision was to promote the guard/seam class, and only that class, to blocking.

A GATE WHOSE FINDINGS ARE CLEAN HAS NEVER DENIED ANYTHING, so this plants the
real historical break and proves check 9 refuses it, names the test, and says
what the test guards.

AND IT PROVES THE COULD-NOT-TELL PATH, which matters more than usual here. This
repo spent a session establishing that a tracked file modified DURING a suite run
is indistinguishable from residue after one. Check 9 reads the working tree, so a
run in flight could make it deny an innocent push. It must say COULD NOT TELL
instead, and that is arm 4.

Driven entirely through the PreToolUse stdin path: no `git push`, no remote, no
commits, and therefore no stranded PROBE commit of its own.

Run: python tests/push_gate/check9_probe.py
"""
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import time

REPO = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True).stdout.strip()
HOOK = os.path.join(REPO, 'tools', 'sairn_push_gate_hook.py')
TARGET = os.path.join(REPO, 'api', 'legal-deadlines.js')
NEEDLE = '        service_methods: body.service_methods,\n'
LOCK = os.path.join(tempfile.gettempdir(),
                    'sairn-suite-%s.lock'
                    % hashlib.sha256(REPO.encode('utf-8')).hexdigest()[:16])

fails = []


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name + ('' if cond else '  ' + detail))
    if not cond:
        fails.append(name)


def hook(cmd='git push origin main'):
    r = subprocess.run([sys.executable, HOOK], cwd=REPO, capture_output=True,
                       text=True, input=json.dumps({'tool_input': {'command': cmd}}))
    try:
        out = json.loads(r.stdout) if r.stdout.strip() else {}
    except ValueError:
        out = {'_unparsed': r.stdout}
    h = out.get('hookSpecificOutput', {}) or {}
    return {
        'decision': h.get('permissionDecision'),
        'reason': h.get('permissionDecisionReason', '') or '',
        'context': h.get('additionalContext', '') or '',
        'objects': r.stdout.count('"hookSpecificOutput"'),
        'raw': r.stdout,
    }


print('push-gate check 9 -- a named guard test must be able to stop a push\n')

# A PRECONDITION IS NOT A FAILURE. Exit 3 is SKIPPED, the convention its
# siblings use. Untracked files are not dirt: this probe rewrites ONE named
# tracked file and puts the original bytes back.
_status = subprocess.run(['git', '-C', REPO, 'status', '--porcelain'],
                         capture_output=True, text=True).stdout
if [l for l in _status.split('\n') if l.strip() and not l.startswith('??')]:
    print('SKIPPED: this probe rewrites api/legal-deadlines.js and restores it, so a')
    print('tracked-dirty tree could not be told apart from its own damage. Nothing')
    print('about check 9 was verified. Modified:')
    print('\n'.join(l for l in _status.split('\n')
                    if l.strip() and not l.startswith('??')))
    sys.exit(3)

if os.path.exists(LOCK):
    print('SKIPPED: the suite lock is held, so a run is in flight and arm 1 would be')
    print('measuring check 9 refusing to answer rather than answering. Nothing was')
    print('verified.')
    sys.exit(3)

ORIGINAL = io.open(TARGET, encoding='utf-8', newline='').read()
if NEEDLE not in ORIGINAL:
    print('SKIPPED: the fixture anchor is not in api/legal-deadlines.js -- either the')
    print('field moved or it is already broken. Read it before trusting this probe.')
    sys.exit(3)

try:
    # ── ARM 1: CONTROL. A clean tree is not blocked by check 9 ──────────────
    # First, so a deny in arm 2 cannot be confused with the gate denying
    # everything for some unrelated reason.
    a1 = hook()
    check('a clean tree is NOT blocked by check 9',
          'a named GUARD test is failing' not in a1['reason'], a1['reason'][:200])
    check('...and exactly one hookSpecificOutput object is emitted, never two',
          a1['objects'] <= 1, 'objects=%d raw=%s' % (a1['objects'], a1['raw'][:200]))

    # ── ARM 2b: AN ORDINARY DIRTY TREE IS NOT A FINDING ────────────────────
    # The hazard this whole family keeps producing is a check that treats
    # "somebody is working" as "something is wrong" -- check4_probe skipped for
    # twelve days over one untracked file. Check 9 reads the working tree by
    # design, so it MUST be indifferent to uncommitted work that does not break
    # a seam. Proven with a real modification to a tracked file none of the five
    # guard tests reads, rather than argued from the fact that they read files.
    _innocent = os.path.join(REPO, 'docs', 'SAIRN-OPEN-WORK-INDEX.md')
    _innocent_original = None
    if os.path.isfile(_innocent):
        _innocent_original = io.open(_innocent, encoding='utf-8', newline='').read()
        io.open(_innocent, 'a', encoding='utf-8', newline='').write(
            '\n<!-- check9_probe: transient, removed by this probe -->\n')
        try:
            a2b = hook()
            check('an ordinary DIRTY tree is not a finding -- uncommitted work is not a break',
                  'a named GUARD test is failing' not in a2b['reason'],
                  a2b['reason'][:200])
        finally:
            io.open(_innocent, 'w', encoding='utf-8', newline='').write(_innocent_original)
    else:
        check('the innocent-dirty fixture file exists', False, _innocent)

    # ── ARM 2: THE REAL HISTORICAL BREAK ────────────────────────────────────
    # Not an invented failure: this is the exact line fab44663 deleted, and its
    # absence is what made SAIRNlaw run Florida five days late for five days.
    io.open(TARGET, 'w', encoding='utf-8', newline='').write(ORIGINAL.replace(NEEDLE, '', 1))
    a2 = hook()
    check('the planted seam break IS blocked',
          a2['decision'] == 'deny' and 'a named GUARD test is failing' in a2['reason'],
          str(a2['decision']) + ' ' + a2['reason'][:200])
    check('...and the refusal NAMES the test',
          'deadline-endpoint-inputs.test.js' in a2['reason'], a2['reason'][:300])
    check('...and says WHAT IT GUARDS rather than only that it failed',
          'GUARDS:' in a2['reason'] and 'forwards every input' in a2['reason'],
          a2['reason'][:300])
    check('...and carries the test\'s own output',
          'service_methods' in a2['reason'], a2['reason'][-400:])
    check('...and tells the reader it may not be their change',
          'may not be your change' in a2['reason'].lower(), a2['reason'][-400:])
    check('...and refuses the escape of relaxing the assertion',
          'Do not raise a count' in a2['reason'], a2['reason'][-400:])

    # ── ARM 3: THE OVERRIDE STILL WORKS, and is not silent ──────────────────
    a3 = hook('SAIRN_SEED_GATE=off git push origin main')
    check('the documented override still gets past it',
          a3['decision'] != 'deny', str(a3)[:200])

    # ── ARM 4: A SUITE RUN IN FLIGHT MUST NOT READ AS A FAILURE ────────────
    # The break is STILL PLANTED here. The only difference is the lock, so this
    # arm isolates exactly one thing: check 9 must stop answering, not answer
    # wrongly. Without it, a probe mutating a tracked file mid-run would deny an
    # innocent push -- the mid-run-vs-residue confusion, reintroduced through a
    # different door.
    io.open(LOCK, 'w').write('%d %f\n' % (os.getpid(), time.time()))
    try:
        a4 = hook()
    finally:
        os.remove(LOCK)
    check('a held suite lock turns the SAME planted break into COULD NOT TELL',
          a4['decision'] != 'deny', str(a4['decision']) + ' ' + a4['reason'][:200])
    check('...and it says so LOUDLY rather than passing silently',
          'COULD NOT TELL' in a4['context'] and 'run lock' in a4['context'],
          a4['context'][:300])
    check('...and still emits only one object',
          a4['objects'] <= 1, 'objects=%d' % a4['objects'])
finally:
    io.open(TARGET, 'w', encoding='utf-8', newline='').write(ORIGINAL)
    if os.path.exists(LOCK):
        os.remove(LOCK)

# ── ARM 5: THE RESTORE IS ASSERTED, not assumed ─────────────────────────────
check('the target file was restored byte for byte',
      io.open(TARGET, encoding='utf-8', newline='').read() == ORIGINAL)
_after = subprocess.run(['git', '-C', REPO, 'status', '--porcelain'],
                        capture_output=True, text=True).stdout
check('...and no tracked file is left modified',
      not [l for l in _after.split('\n') if l.strip() and not l.startswith('??')],
      _after[:200])
check('...and the lock this probe created is gone', not os.path.exists(LOCK))

# ── ARM 6: EVERY REGISTRY ENTRY NAMES A FILE THAT EXISTS ───────────────────
# A registry entry pointing at a moved or deleted test is a suppression nobody
# would notice: check 9 reports it and allows, by design, so nothing else would
# ever say so.
#
# IMPORTED, NOT PARSED OUT OF THE SOURCE. The first version split the file on
# `GUARD_TESTS = [` and then on `]`, and truncated at the FIRST `]` -- which
# lands inside one entry's own prose, `["mail","email"]`. It reported a
# one-entry registry and passed the existence check on that one entry, i.e. a
# check that looked green while inspecting a fifth of what it named. GUARD_TESTS
# is module-level for this reason: a probe should read the real object.
import importlib.util  # noqa: E402
_spec = importlib.util.spec_from_file_location('sairn_push_gate_hook', HOOK)
_hook_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_hook_mod)
_paths = [e[0] for e in _hook_mod.GUARD_TESTS]
check('the registry was parsed at all', len(_paths) >= 5, str(_paths))
check('...and every entry carries what it guards and why it exists',
      all(len(e) == 3 and e[1].strip() and e[2].strip()
          for e in _hook_mod.GUARD_TESTS),
      str([e[0] for e in _hook_mod.GUARD_TESTS if len(e) != 3]))
for _p in _paths:
    check('registry entry exists on disk: ' + _p, os.path.isfile(os.path.join(REPO, _p)))

print('\n%s  check9_probe: %d failed' % ('FAILED' if fails else 'ok', len(fails)))
sys.exit(1 if fails else 0)
