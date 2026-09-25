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
# REQUIREMENT: push-gate check 9 refuses the real 2026-09-10 break, names the
#   failing guard test and what it guards, and answers COULD NOT TELL rather
#   than denying when a suite run in flight has left the working tree modified
#
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import time

REPO = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True, encoding='utf-8', errors='replace').stdout.strip()
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


# ── THIS PROBE WROTE A REAL ROW INTO THE REAL AUDIT LOG (2026-09-16) ────────
# Arm 3 below drives the hook with a real `SAIRN_SEED_GATE=off` payload, which
# is correct -- an override must be exercised, not described. The hook then did
# exactly what it exists to do and RECORDED the bypass, in
# `docs/BYPASS-LOG.jsonl`: a genuine row, attributed to a real session, for a
# command no human ever ran. That log is read to decide whether a repeatedly
# bypassed check is itself defective, so a fabricated row there is not residue,
# it is a false entry in an audit trail.
#
# `tools/bypass_log.py` has carried the redirect since it was written and says
# so in its own header. This probe simply never set it. Measured on the day it
# was found: of 24 test files that drive the hook, ONE did.
#
# A REDIRECT, NOT A SUPPRESSION. The write still happens, so the wiring is still
# exercised; it lands in a throwaway file instead of the record.
_BYPASS_LOG = os.path.join(tempfile.gettempdir(),
                           'check9-bypass-%d.jsonl' % os.getpid())
REAL_BYPASS_LOG = os.path.join(REPO, 'docs', 'BYPASS-LOG.jsonl')


def hook(cmd='git push origin main'):
    env = dict(os.environ)
    env['SAIRN_BYPASS_LOG'] = _BYPASS_LOG
    r = subprocess.run([sys.executable, HOOK], cwd=REPO, capture_output=True,
                       text=True, encoding='utf-8', errors='replace', env=env,
                       input=json.dumps({'tool_input': {'command': cmd}}))
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
                         capture_output=True, text=True, encoding='utf-8', errors='replace').stdout
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

_gate_orig = io.open(os.path.join(REPO, 'tools', 'sairn_push_gate_hook.py'),
                     encoding='utf-8', newline='').read()
ORIGINAL = io.open(TARGET, encoding='utf-8', newline='').read()
# ── EXACTLY ONCE, NOT MERELY PRESENT (2026-09-10) ─────────────────────────
# This checked `NEEDLE not in ORIGINAL`, which catches an anchor that has GONE
# and says nothing about one that matches SEVERAL places -- `.replace(..., 1)`
# below would then delete whichever came first and arm 2 would be planting a
# break nobody chose. Written the day after arm 15 of
# tests/sairndental_outbound_queue_probe.py was found in exactly that state,
# and it had the same hole: an anchor is a string match against code somebody
# else keeps editing, so going ambiguous is how it AGES, not an accident.
_anchor_hits = ORIGINAL.count(NEEDLE)
if _anchor_hits != 1:
    print('SKIPPED: the fixture anchor matches %d places in api/legal-deadlines.js, '
          'not 1.' % _anchor_hits)
    print('At 0 the field moved or is already broken; above 1 this probe would plant')
    print('its break in whichever came first. Nothing about check 9 was verified --')
    print('read the file and widen NEEDLE until it is unique.')
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
    real_before = (io.open(REAL_BYPASS_LOG, encoding='utf-8').read()
                   if os.path.isfile(REAL_BYPASS_LOG) else None)
    a3 = hook('SAIRN_SEED_GATE=off git push origin main')
    check('the documented override still gets past it',
          a3['decision'] != 'deny', str(a3)[:200])
    # THE WRITE REALLY HAPPENED -- redirected, not suppressed. A probe that
    # merely stopped the logging would leave the hook's own wiring unexercised,
    # which is the fail-open shape moved one level out.
    # `ALL`, not `seed-gate`: the inline override is the BLANKET form and
    # disables every check in the hook rather than one named one. This arm
    # asserted `seed-gate` first and went red -- which is the arm doing its job,
    # since a redirect nobody checks is indistinguishable from a suppression.
    check('...and the bypass was RECORDED, into the throwaway log',
          os.path.isfile(_BYPASS_LOG)
          and '"check": "ALL"' in io.open(_BYPASS_LOG, encoding='utf-8').read(),
          _BYPASS_LOG + ' :: ' + (io.open(_BYPASS_LOG, encoding='utf-8').read()[:200]
                                  if os.path.isfile(_BYPASS_LOG) else 'NO FILE'))
    # ...AND NOT INTO THE REAL ONE. This arm is the finding of 2026-09-16 turned
    # into a check: without it, the next probe to drive an override forgets the
    # redirect and nothing says so until somebody reads the audit trail and
    # finds a row for a command nobody ran.
    real_after = (io.open(REAL_BYPASS_LOG, encoding='utf-8').read()
                  if os.path.isfile(REAL_BYPASS_LOG) else None)
    check('...and the REAL audit log was not touched -- a fabricated row in it '
          'is an audit-integrity defect, not probe residue',
          real_after, real_before)

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
    # READS CHECK 9'S OWN SENTENCE, NOT THE GLOBAL DECISION (fixed 2026-09-25).
    # `decision != 'deny'` made this arm environment-dependent: hook() runs
    # EVERY check, so any unrelated blocker -- most often a generated document
    # another session left stale -- denied the run and this arm reported check
    # 9 as blocking when check 9 had correctly said nothing. Same correction
    # as the exit-code arms below, and the same one arm 1 above always had.
    check('a held suite lock turns the SAME planted break into COULD NOT TELL',
          'a named GUARD test is failing' not in a4['reason'],
          str(a4['decision']) + ' ' + a4['reason'][:200])
    # THE CONTEXT IS SINGULAR AND ANOTHER CHECK'S DENY REPLACES IT, so this
    # asserts the note when it is readable and asserts the WIRING when it is
    # not -- rather than going red for a reason that has nothing to do with
    # check 9. A silent pass is still refused: one of the two must hold.
    _a4_said = ('COULD NOT TELL' in a4['context'] and 'run lock' in a4['context'])
    check('...and it says so LOUDLY rather than passing silently',
          _a4_said or ('the full suite holds the run lock' in _gate_orig
                       and 'guard_note = (' in _gate_orig),
          'context=' + a4['context'][:200])
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
                        capture_output=True, text=True, encoding='utf-8', errors='replace').stdout
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

# ── ARM 7: THE DOCS-ONLY SKIP, DRIVEN IN BOTH DIRECTIONS (2026-09-24) ───────
# Added with the skip itself. The recurring failure it closes: the session-lock
# liveness probe is Windows-only, exits 2 on the Linux cloud runner, and this
# loop read every nonzero exit as a failing seam -- so every cloud push,
# docs-only or not, needed an override the auto-mode classifier correctly
# refuses. Three commits sat stranded on claude/jolly-gauss-uropwz.
#
# The predicate is the WHOLE safety argument for the skip, so it is a named
# function and every boundary is driven here -- including the two exclusions
# that keep the definition honest rather than convenient.
_dof = _hook_mod.docs_only_outgoing
check('docs-only: a pure docs/ range skips',
      _dof(['docs/a.md', 'docs/sub/deep/b.md']) is True)
check('docs-only: ONE code file disqualifies the whole range',
      _dof(['docs/a.md', 'api/sd-data.js']) is False)
check('docs-only: a claims file disqualifies',
      _dof(['docs/a.md', '.claude/claims/fourth.json']) is False)
check('docs-only: the tier-a-reviews LEDGER disqualifies even though it lives '
      'in docs/ -- it is machine-enforced, not prose',
      _dof(['docs/tier-a-reviews.json']) is False)
check('docs-only: an EMPTY range is NOT docs-only -- "could not tell what is '
      'outgoing" must never read as "safe to skip"',
      _dof([]) is False)
check('docs-only: a file whose name merely STARTS with docs is not docs/',
      _dof(['docs-backup/a.md']) is False)
# THE WIRING, not only the predicate: check 9's loop must actually consult it.
# A predicate nothing calls is one refactor from dead, and this arm is what
# notices the call being dropped.
_hook_src = io.open(HOOK, encoding='utf-8').read()
check('check 9 actually consults docs_only_outgoing before running the guards',
      '_docs_only = docs_only_outgoing(changed)' in _hook_src
      and 'if _docs_only:' in _hook_src,
      'the predicate exists but nothing gates the guard loop on it')
check('...and the skip says so on stderr rather than silently',
      'check 9) SKIPPED' in _hook_src)

# ── ARM 8: EXIT 3 IS SKIPPED, EXIT 1 AND 2 ARE NOT (2026-09-25) ────────────
# Driven with a REAL stub guard test rather than asserted on source: a stub is
# planted in the registry on disk (the hook runs as a subprocess, so an
# in-memory patch cannot reach it), the hook is run, the decision read, and the
# gate restored byte-for-byte.
#
# THE TWO CONTROLS ARE THE ARM. A 3 that skips is worth nothing if a 1 also
# skips -- that is a real Windows-side failure masked, which is exactly what a
# floor-count "require N of the registry" fix would have done -- or if the 3
# reported success, which is unmeasured reading as measured-clean.
_STUB_REL = 'tests/push_gate/_check9_exit_stub.py'
_STUB_ABS = os.path.join(REPO, 'tests', 'push_gate', '_check9_exit_stub.py')
_GATE = os.path.join(REPO, 'tools', 'sairn_push_gate_hook.py')
# THE REGISTRY IS REPLACED, NOT APPENDED TO, and that is a cost decision made
# after the first version timed this probe out. Each hook() call runs the WHOLE
# registry, so appending one stub to eleven real guard tests meant running all
# eleven three more times. Replacing the list measures exactly the property
# under test -- how ONE exit code is routed -- for one python start-up.
_reg_start = _gate_orig.index('GUARD_TESTS = [')
_reg_end = _gate_orig.index('\n]', _reg_start) + 2

for _code, _want_deny, _label in (
        (3, False, 'exit 3 is SKIPPED -- the push is allowed'),
        (1, True, 'exit 1 still BLOCKS -- a genuine failure is not skippable'),
        (2, True, 'exit 2 still BLOCKS -- "I should have been able to run here '
                  'and could not" is a real problem on THIS machine, and only '
                  'the test itself can say it is inapplicable instead')):
    io.open(_STUB_ABS, 'w', encoding='utf-8', newline='\n').write(
        "import sys\n"
        "print('SKIPPED (not applicable on this platform): stub')\n"
        "print('NOTHING WAS VERIFIED. This is not a pass.')\n"
        "sys.exit(%d)\n" % _code)
    io.open(_GATE, 'w', encoding='utf-8', newline='').write(
        _gate_orig[:_reg_start]
        + "GUARD_TESTS = [\n    ('" + _STUB_REL + "', 'a stub guard planted by "
          "check9_probe', 'exit-code routing'),\n]"
        + _gate_orig[_reg_end:])
    try:
        _r = hook()
    finally:
        io.open(_GATE, 'w', encoding='utf-8', newline='').write(_gate_orig)
        if os.path.exists(_STUB_ABS):
            os.remove(_STUB_ABS)
    # ASSERTED ON CHECK 9'S OWN REASON TEXT, NOT ON THE GLOBAL DECISION, and
    # the first version of this arm got that wrong: hook() runs EVERY check,
    # so a stale generated document (check 12) denied the exit-3 run and the
    # arm read it as "check 9 blocked". Same convention arm 1 above already
    # uses -- the question is whether THIS check blocked, and only its own
    # sentence answers that.
    _c9_blocked = 'a named GUARD test is failing' in _r['reason']
    check(_label, _c9_blocked == _want_deny,
          'check9-blocked=%s decision=%s reason=%s'
          % (_c9_blocked, _r['decision'], _r['reason'][:160]))
    if _code == 3:
        # ── WHY THIS IS A SOURCE ASSERTION AND NOT AN END-TO-END ONE ───────
        # MEASURED, not assumed: GUARD_TESTS is itself a source the
        # traceability matrix derives from, so patching the registry to plant
        # the stub makes a GENERATED DOCUMENT stop matching -- check 12 then
        # denies the run and its reason REPLACES the guard note in the single
        # hookSpecificOutput object the hook is allowed to emit. The arms
        # above survive that because they read check 9's own sentence; a
        # context assertion cannot, because there is only one context.
        #
        # So the ROUTING is asserted where it stays readable: the skip must
        # land in `_guard_unrun` -- the same could-not-tell list that carries
        # every other unrun guard and is reported rather than folded into the
        # pass. The behaviour that matters (allowed, and check 9 silent about
        # a failing seam) is the arm immediately above.
        check('...and the SKIP routes into the could-not-tell list, not into '
              'silence',
              "_guard_unrun.append((_t, 'SKIPPED as not applicable" in _gate_orig
              and 'guard_note = (' in _gate_orig,
              'exit 3 is allowed but nothing records that the seam went unrun')

check('the gate is byte-identical after the exit-code arms',
      io.open(_GATE, encoding='utf-8', newline='').read() == _gate_orig)
check('...and the stub is gone', not os.path.exists(_STUB_ABS))

print('\n%s  check9_probe: %d failed' % ('FAILED' if fails else 'ok', len(fails)))
sys.exit(1 if fails else 0)
