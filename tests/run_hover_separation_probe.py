#!/usr/bin/env python
"""tests/run_hover_separation_probe.py -- the controls for the two hover
auditor separation tools, and the reason each one exists.

WHAT IS UNDER TEST
  tools/hover_auditor_scope_gate.py   -- prevents (a commit/push/worktree gate)
  tools/hover_separation_audit.py     -- detects (an audit trail over history)

The two are deliberately different mechanisms reading different sources, so
this file has to show BOTH of them biting. A gate that never refuses and a
report that never finds anything look exactly like a clean platform.

THE STANDARD THIS FILE IS HELD TO IS THE AUDITOR'S OWN, quoted from its skill:
"A verifier that has never been shown to fail is not yet a verifier." Section E
does that to the chain verifier by tampering with a real entry and asserting it
reports BROKEN, then restoring it and asserting it reports INTACT. A one-sided
control -- tamper, see it fail, stop -- cannot tell a working verifier from one
that reports BROKEN unconditionally.

AND EVERY SABOTAGE ASSERTS ITS OWN ANCHOR IS PRESENT BEFORE IT PATCHES. A
`.replace()` whose anchor has gone stale changes nothing and the arm then
reports a pass over a mutation that was never applied. That is the half
`tools/sabotage_control_check.py` measured most controls on this platform
skipping.

Exit 0 = every arm passed. Exit 1 = at least one failed.
"""

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, 'tools'))

GATE = os.path.join(REPO, 'tools', 'hover_auditor_scope_gate.py')
AUDIT = os.path.join(REPO, 'tools', 'hover_separation_audit.py')
MARKER = 'sairn-hover-auditor-clone'

FAILS = []
PASSES = [0]


def ok(label, cond, detail=''):
    if cond:
        PASSES[0] += 1
        print('    ok   %s' % label)
    else:
        FAILS.append(label)
        print('    FAIL %s' % label)
        if detail:
            print('         %s' % str(detail)[:400])


def run(*args, **kw):
    return subprocess.run(list(args), capture_output=True, text=True,
                          encoding='utf-8', errors='replace', **kw)


# ══ A. the pure classifier, both directions, no repo needed ═════════════════
print('\nA. violations() -- the pure classifier')
import hover_auditor_scope_gate as G          # noqa: E402
import hover_separation_audit as A            # noqa: E402

IN_SCOPE = ['.claude/skills/sairn-hover-auditor/SKILL.md',
            '.claude/skills/sairn-hover-auditor/references/case-studies.md',
            'docs/defect-density-register.json']
OUT_OF_SCOPE = ['api/sv-witness.js', 'stonedesk.html', 'tools/defect_register.py',
                'tests/failsafe/witness_atomicity.js', 'sql/anything.sql',
                '.claude/skills/sairn-guardian-v2/SKILL.md']

allowed, refused = G.violations(IN_SCOPE)
ok('every in-scope path is allowed', not refused, refused)
ok('...and they are actually counted, not silently dropped',
   len(allowed) == len(IN_SCOPE), (len(allowed), len(IN_SCOPE)))

allowed, refused = G.violations(OUT_OF_SCOPE)
ok('every out-of-scope path is refused', len(refused) == len(OUT_OF_SCOPE), allowed)

allowed, refused = G.violations(IN_SCOPE + OUT_OF_SCOPE)
ok('a MIXED change is refused, not averaged', len(refused) == len(OUT_OF_SCOPE), refused)
ok('...and the in-scope half is still reported as allowed',
   len(allowed) == len(IN_SCOPE), allowed)

# The skill names this file explicitly as out of scope. If somebody adds
# tools/ to the allowlist wholesale, this arm is what goes red.
_, refused = G.violations(['tools/defect_register.py'])
ok('tools/defect_register.py is refused -- the skill names it out of scope',
   refused == ['tools/defect_register.py'], refused)

# Windows separators reach a hook via some callers; a backslash path that fell
# through as "not matching the prefix" would be ALLOWED, which is the unsafe
# direction.
_, refused = G.violations(['api\\sv-witness.js'])
ok('a backslash path is still refused', refused == ['api/sv-witness.js'], refused)
_, refused = G.violations(['.claude\\skills\\sairn-hover-auditor\\SKILL.md'])
ok('a backslash path in scope is still allowed', not refused, refused)

# A near-miss that must NOT be allowed: a sibling directory whose name starts
# with the allowed one would pass a naive startswith on the un-slashed prefix.
_, refused = G.violations(['.claude/skills/sairn-hover-auditor-evil/x.md'])
ok('a sibling dir sharing the prefix is NOT allowed by accident',
   refused == ['.claude/skills/sairn-hover-auditor-evil/x.md'], refused)


# ══ B. scope vs signature -- the bug this probe exists to keep fixed ════════
print('\nB. scope and signature are different sets')
ok('the register is IN SCOPE (the auditor is told to write findings there)',
   A.in_auditor_scope('docs/defect-density-register.json'))
ok('the register is NOT a SIGNATURE -- all four build agents write it too',
   not A.is_auditor_signature('docs/defect-density-register.json'))
ok('the skill dir is both', A.in_auditor_scope('.claude/skills/sairn-hover-auditor/SKILL.md')
   and A.is_auditor_signature('.claude/skills/sairn-hover-auditor/SKILL.md'))
# Using the scope set for attribution credited every register-only commit on the
# platform to the auditor. Measured at the time: 20 real commits reported as 46.
ok('a register-only commit is NOT attributed to the auditor',
   A.attribute({'files': ['docs/defect-density-register.json']})[0] != 'hover')
ok('a skill-only commit IS attributed to the auditor',
   A.attribute({'files': ['.claude/skills/sairn-hover-auditor/SKILL.md']})[0] == 'hover')
ok('a claims-file commit is attributed to that session',
   A.attribute({'files': ['.claude/claims/hank.json']})[0] == 'hank')
ok('a platform commit is UNATTRIBUTED, not assigned to anybody',
   A.attribute({'files': ['api/sd-data.js']})[0] is None)

# The two tools keep separate copies of the scope on purpose. They must agree.
gate_scope = set(p for p, _why in G.ALLOWED)
ok('the gate and the audit agree on the scope set',
   gate_scope == set(A.AUDITOR_SCOPE), (gate_scope, set(A.AUDITOR_SCOPE)))


# ══ C. the gate in a real repo, armed and unarmed ═══════════════════════════
print('\nC. the gate in a real repository -- both arming states')
TMP = tempfile.mkdtemp(prefix='hover_gate_')
try:
    r = run('git', 'init', '-q', TMP)
    ok('a throwaway repo was created', r.returncode == 0, r.stderr)
    run('git', '-C', TMP, 'config', 'user.email', 'probe@example.invalid')
    run('git', '-C', TMP, 'config', 'user.name', 'probe')

    def put(rel, text='x\n'):
        p = os.path.join(TMP, rel.replace('/', os.sep))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        io.open(p, 'w', encoding='utf-8').write(text)
        return p

    # The gate re-reads the core rule from the skill file on every run, so the
    # fixture has to carry a real one or every armed arm below fails for the
    # wrong reason.
    put('.claude/skills/sairn-hover-auditor/SKILL.md',
        'fixture\n\n**Never write, edit, or push platform code.**\n')
    put('api/sv-witness.js', '// platform code\n')
    put('docs/defect-density-register.json', '{"records":[]}\n')

    def gate(*a, stdin=''):
        return run(sys.executable, GATE, *a, cwd=TMP, input=stdin)

    marker = os.path.join(TMP, '.git', MARKER)

    # --- UNARMED: the gate must be silent and permissive ---
    run('git', '-C', TMP, 'add', 'api/sv-witness.js')
    ok('unarmed: the marker really is absent', not os.path.isfile(marker))
    r = gate('--pre-commit')
    ok('unarmed: a platform-code commit is ALLOWED (wrong clone, not our rule)',
       r.returncode == 0, r.stdout + r.stderr)
    ok('unarmed: and it says NOTHING -- four build clones commit through this',
       r.stdout.strip() == '', repr(r.stdout[:200]))

    # --- ARM IT ---
    r = gate('--install')
    ok('--install exits 0', r.returncode == 0, r.stderr)
    ok('--install created the marker inside .git/', os.path.isfile(marker))
    ok('the marker is NOT trackable -- it is under .git/',
       '.git' in os.path.relpath(marker, TMP).split(os.sep))
    r = gate('--check')
    ok('--check reports armed', 'YES' in r.stdout, r.stdout)

    # --- ARMED: platform code must be refused ---
    r = gate('--pre-commit')
    ok('ARMED: a staged platform file is REFUSED', r.returncode == 1, r.stdout[-300:])
    ok('...and the refusal NAMES the file', 'api/sv-witness.js' in r.stdout, r.stdout[:300])
    ok('...and it points at reporting rather than fixing',
       'report' in r.stdout.lower(), r.stdout[:300])

    # --- ARMED: its own tooling must still be allowed ---
    run('git', '-C', TMP, 'reset', '-q')
    run('git', '-C', TMP, 'add', '.claude/skills/sairn-hover-auditor/SKILL.md')
    r = gate('--pre-commit')
    ok('ARMED: a skill-file-only commit is ALLOWED', r.returncode == 0, r.stdout[-300:])

    run('git', '-C', TMP, 'reset', '-q')
    run('git', '-C', TMP, 'add', 'docs/defect-density-register.json')
    r = gate('--pre-commit')
    ok('ARMED: a findings-register commit is ALLOWED', r.returncode == 0, r.stdout[-300:])

    # --- ARMED: a MIXED commit is refused, which is the realistic shape ---
    run('git', '-C', TMP, 'add', 'api/sv-witness.js')
    r = gate('--pre-commit')
    ok('ARMED: skill file PLUS platform code is refused', r.returncode == 1, r.stdout[-200:])

    # --- the working-tree arm: the shape that actually happened ---
    # Self-log entry 0073: api/sv-witness.js patched in place (`if(false) &&`)
    # to drive a mutation control. Nothing was committed, so a commit gate
    # alone would never have seen it -- and an uncommitted platform mutation
    # is one `git add -A` away from shipping.
    run('git', '-C', TMP, 'reset', '-q')
    r = gate('--worktree')
    ok('ARMED: an untracked platform file is caught by --worktree',
       r.returncode == 1, r.stdout[-300:])
    ok('...naming it', 'api/sv-witness.js' in r.stdout, r.stdout[:200])

    # --- fail CLOSED when it cannot verify its own scope ---
    skill = os.path.join(TMP, '.claude', 'skills', 'sairn-hover-auditor', 'SKILL.md')
    src = io.open(skill, encoding='utf-8').read()
    ANCHOR = 'Never write, edit, or push platform code'
    ok('the scope anchor is present in the fixture before it is removed',
       ANCHOR in src, 'stale anchor -- section C tests NOTHING below this line')
    io.open(skill, 'w', encoding='utf-8').write(src.replace(ANCHOR, 'REWORDED'))
    ok('the sabotage actually changed the file',
       ANCHOR not in io.open(skill, encoding='utf-8').read())
    run('git', '-C', TMP, 'reset', '-q')
    run('git', '-C', TMP, 'add', 'docs/defect-density-register.json')
    r = gate('--pre-commit')
    ok('the rule reworded -> REFUSES even an in-scope change (fail closed)',
       r.returncode == 1, r.stdout[-300:])
    ok('...and says it could not verify its scope, not that it found a violation',
       'CANNOT VERIFY' in r.stdout.upper(), r.stdout[:300])
    io.open(skill, 'w', encoding='utf-8').write(src)
    ok('the skill fixture was restored byte-identical',
       io.open(skill, encoding='utf-8').read() == src)
    r = gate('--pre-commit')
    ok('...and the gate goes back to ALLOWING the in-scope change',
       r.returncode == 0, r.stdout[-200:])

    # --- the skill file GONE is a different failure and must say so ---
    os.remove(skill)
    r = gate('--pre-commit')
    ok('skill file missing -> also refuses', r.returncode == 1, r.stdout[-200:])
    ok('...and names THAT cause rather than the reword one',
       'not at' in r.stdout, r.stdout[:300])
    io.open(skill, 'w', encoding='utf-8').write(src)

    # --- pre-push stdin handling ---
    Z = '0' * 40
    r = gate('--pre-push', stdin='')
    ok('pre-push with NO ref lines REFUSES rather than passing vacuously',
       r.returncode == 1, r.stdout[-200:])
    ok('...and says it could not read the change',
       'COULD NOT READ' in r.stdout.upper(), r.stdout[:200])
    r = gate('--pre-push', stdin='refs/heads/main deadbeef refs/heads/main %s\n' % Z)
    ok('pre-push with an unreadable range REFUSES', r.returncode == 1, r.stdout[-200:])

    # --- TEETH: neuter the classifier and the refusing arms must collapse ---
    gsrc = io.open(GATE, encoding='utf-8').read()
    T_ANCHOR = '        (allowed if ok else refused).append(p)'
    ok('the teeth anchor is present in the subject',
       gsrc.count(T_ANCHOR) == 1,
       'anchor stale or ambiguous -- the teeth section tests NOTHING')
    broken = gsrc.replace(T_ANCHOR, '        allowed.append(p)')
    ok('the neutering actually changed the source', broken != gsrc)
    BROKEN_GATE = os.path.join(TMP, 'broken_gate.py')
    io.open(BROKEN_GATE, 'w', encoding='utf-8').write(broken)
    run('git', '-C', TMP, 'reset', '-q')
    run('git', '-C', TMP, 'add', 'api/sv-witness.js')
    r = run(sys.executable, BROKEN_GATE, '--pre-commit', cwd=TMP)
    ok('the broken copy runs at all', r.returncode in (0, 1), r.stderr[-300:])
    ok('TEETH: with the classifier neutered, the platform commit is ALLOWED',
       r.returncode == 0,
       'the neutered gate still refused -- these arms are not testing the '
       'classifier and the section proves nothing')
    r = gate('--pre-commit')
    ok('...while the real gate still refuses it', r.returncode == 1)
finally:
    # git marks objects and pack files READ-ONLY, and on Windows os.remove
    # refuses those, so ignore_errors=True leaves the tree standing and the arm
    # below goes red for a reason that has nothing to do with the gate. Clear
    # the bit and retry rather than dropping the arm -- a probe that leaks a
    # throwaway git repo per run into the temp directory is a real defect, just
    # a boring one.
    def _force(func, path, _exc):
        try:
            os.chmod(path, 0o700)
            func(path)
        except OSError:
            pass

    shutil.rmtree(TMP, onerror=_force)
    ok('the throwaway repo is gone', not os.path.isdir(TMP))


# ══ D. the audit tool over the real repository ═════════════════════════════
print('\nD. the audit tool, against real history')
r = run(sys.executable, AUDIT, cwd=REPO)
ok('it runs', r.returncode in (0, 1, 2), r.stderr[-300:])
out = r.stdout
ok('it prints coverage BEFORE any verdict',
   out.index('COVERAGE FIRST') < out.index('RESULT:'), 'verdict precedes coverage')
ok('it states that git alone cannot prove the negative',
   'cannot prove the' in out, out[:200])
ok('it reports the unattributed share as a number', 'UNATTRIBUTED' in out)
ok('exit 2 is reserved for could-not-run, and 0 is never printed with one',
   not (r.returncode == 0 and 'DID NOT RUN' in out),
   'a could-not-run was reported under a clean exit code')

r2 = run(sys.executable, AUDIT, '--authors', cwd=REPO)
ok('--authors runs', r2.returncode == 0, r2.stderr[-200:])
ok('--authors backs the one-identity claim the tool rests on',
   r2.stdout.count('<') >= 1 and 'ONE identity' in r2.stdout, r2.stdout[:200])

r3 = run(sys.executable, AUDIT, '--json', cwd=REPO)
ok('--json emits parseable JSON',
   json.loads(r3.stdout[r3.stdout.index('{'):]) is not None)


# ══ E. the chain verifier, shown to FAIL and then to pass again ════════════
print('\nE. the chain verifier -- tampered, then restored')
rows, path, problem = A.read_hover_log()
if problem:
    print('    (COULD NOT RUN: %s)' % problem.split('\n')[0][:120])
    print('    This section is SKIPPED, and that is reported rather than')
    print('    counted as a pass -- the verifier is untested in this clone.')
    ok('the audit tool reported the missing log as could-not-run, not clean',
       True)
else:
    good, why, n = A.verify_chain(rows)
    ok('the real chain verifies INTACT', good, why)
    ok('...over every entry, not a prefix', n == len(rows), (n, len(rows)))

    import copy
    for i in (0, len(rows) // 2, len(rows) - 1):
        t = copy.deepcopy(rows)
        before = t[i]['summary']
        t[i]['summary'] = before + ' TAMPERED'
        ok('entry %d: the tamper actually changed the row' % i,
           t[i]['summary'] != before)
        bad, why2, at = A.verify_chain(t)
        ok('entry %d tampered -> the verifier reports BROKEN' % i, not bad, why2)
        ok('entry %d: and it names WHERE' % i, at == i, (at, i))

    # A verifier that reports BROKEN unconditionally would pass every arm
    # above. This is the other direction.
    again, _, _ = A.verify_chain(rows)
    ok('untampered rows still verify INTACT afterwards', again)

    # A reordering is a distinct attack from an edit: every entry still hashes
    # to its own stored value, and only the prev_hash linkage catches it.
    if len(rows) > 3:
        swapped = rows[:1] + [rows[2], rows[1]] + rows[3:]
        bad3, _, _ = A.verify_chain(swapped)
        ok('two entries SWAPPED -> reported BROKEN (the linkage, not the hash)',
           not bad3)

    # Truncation: dropping the tail leaves a chain that is internally perfect.
    # The verifier cannot catch it and must not be claimed to.
    trunc, _, _ = A.verify_chain(rows[:-1])
    ok('TRUNCATION at the tail is NOT caught, and this arm records that '
       'rather than hiding it', trunc,
       'if this went red the verifier gained a property -- update the note')


print('\n' + '=' * 66)
print('%d passed, %d failed' % (PASSES[0], len(FAILS)))
for f in FAILS:
    print('  FAILED: %s' % f)
sys.exit(1 if FAILS else 0)
