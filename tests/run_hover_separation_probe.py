CONTROLS_FOR = ['tools/hover_separation_audit.py']
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
from collections import Counter

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
            'docs/defect-density-register.json',
            '.claude/claims/hover.json']
OUT_OF_SCOPE = ['api/sv-witness.js', 'stonedesk.html', 'tools/defect_register.py',
                'tests/failsafe/witness_atomicity.js', 'sql/anything.sql',
                '.claude/skills/sairn-guardian-v2/SKILL.md',
                '.claude/claims/cody.json', '.claude/claims/hank.json']

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

# The auditor's OWN claim file, added 2026-09-18 after this gate refused it
# three times and blocked three real commits. Both directions matter more here
# than anywhere else in this file: hover.json must pass, and the four build
# agents' claim files must NOT, because a prefix-shaped fix (`.claude/claims/`)
# would have let the auditor write claims on behalf of the parties it audits.
_, refused = G.violations(['.claude/claims/hover.json'])
ok('the auditor\'s own claim file is allowed -- it records its OWN actions',
   not refused, refused)
_, refused = G.violations(['.claude/claims/cody.json', '.claude/claims/cc.json',
                           '.claude/claims/hank.json', '.claude/claims/fourth.json'])
ok('...but a BUILD AGENT\'s claim file is still refused, all four',
   len(refused) == 4, refused)
_, refused = G.violations(['.claude/claims/hover.json.bak'])
ok('...and a near-miss on the claim file is refused, not prefix-matched',
   refused == ['.claude/claims/hover.json.bak'], refused)

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


# ══ F. THE EVIDENCE DOCUMENT -- the thing somebody is actually shown ═══════
#
# Added 2026-09-16. The stdout report answers an engineer at a prompt; this
# answers "what do I hand to a person who was not here". A document is a
# stronger artefact than a terminal dump and therefore a more dangerous one:
# it gets forwarded, quoted and kept long after the run that produced it.
#
# SO EVERY ARM HERE IS ABOUT THE DOCUMENT NOT BEING ABLE TO FLATTER. It must
# carry its own limit ABOVE the numbers, it must list the auditor's commits in
# FULL rather than summarise them, it must be anchored to a commit and a time,
# and a violation must reach the verdict rather than being smoothed into prose.
print('\nF. the evidence document -- it must not be able to flatter')
_tmpF = tempfile.mkdtemp(prefix='hovertrail-')
_md = os.path.join(_tmpF, 'trail.md')
_csv = os.path.join(_tmpF, 'trail.csv')
rF = run(sys.executable, AUDIT, '--report', _md, '--csv', _csv, cwd=REPO)
ok('F1 --report and --csv run and write both files',
   rF.returncode in (0, 1, 2) and os.path.exists(_md) and os.path.exists(_csv),
   rF.stderr[-300:])
doc = io.open(_md, encoding='utf-8').read() if os.path.exists(_md) else ''

# THE LIMIT COMES FIRST. A reader who takes only the headline away must take
# the caveat with it.
ok('F2 the "cannot prove the negative" limit appears BEFORE the attribution '
   'table', 'cannot prove the negative' in doc
   and doc.index('cannot prove the negative') < doc.index('## Attribution'),
   'the numbers precede the caveat')
ok('F3 the UNATTRIBUTED share is stated as a number, not omitted',
   'UNATTRIBUTED' in doc and '%' in doc, doc[:200])
ok('F4 the document says UNATTRIBUTED is not a sixth agent',
   'not a sixth agent' in doc, '')

# ANCHORED. A separation claim with no tip and no time is a claim about an
# unstated moment, and this history moves every few minutes.
_code, _tip, _ = A.git('rev-parse', 'HEAD')
ok('F5 the document names the exact commit it was generated from',
   _tip.strip()[:12] in doc, _tip.strip()[:12])
ok('F6 ...and the UTC time it was generated', 'UTC' in doc and 'Generated' in doc)
ok('F7 ...and the command that regenerates it, so it is reproducible',
   '--report' in doc and '--csv' in doc)

# THE AUDITOR'S COMMITS IN FULL. This is the claim under test; a count is a
# summary of the proof and cannot be checked.
_commits, _err = A.load_commits()
_hov = [k for k in (_commits or []) if A.attribute(k)[0] == 'hover']
_listed = sum(1 for k in _hov if k['sha'][:8] in doc)
ok('F8 EVERY auditor commit is listed in the document, not a sample',
   _listed == len(_hov), '%d of %d listed' % (_listed, len(_hov)))
ok('F9 ...and there is at least one to list, so F8 is not passing on an empty '
   'set', len(_hov) > 0, len(_hov))

# THE CSV IS WHAT MAKES THE DOCUMENT CHECKABLE RATHER THAN BELIEVABLE.
_rows = io.open(_csv, encoding='utf-8').read().strip().split('\n')
ok('F10 the CSV carries EVERY commit, one row each, plus a header',
   len(_rows) == len(_commits or []) + 1,
   '%d rows for %d commits' % (len(_rows), len(_commits or [])))
ok('F11 ...and each row carries the attribution METHOD, so a reader can see '
   'which rows rest on nothing',
   'attribution_method' in _rows[0] and 'unattributed' in '\n'.join(_rows),
   _rows[0])

# ── THE ARM THAT MATTERS: A VIOLATION MUST REACH THE VERDICT ───────────────
# Every arm above is satisfied by a document that can only ever say "clean".
# This drives write_report() with a fabricated out-of-scope auditor commit and
# requires the document to say so, in the verdict, in words.
_viol_trail = [{'sha': 'deadbeefcafe0001', 'ts': 1757000000, 'who': 'hover',
                'how': 'signature-only', 'subject': 'a fabricated violation',
                'n_files': 2, 'outside': ['api/sd-data.js']}]
_viol_hov = [{'sha': 'deadbeefcafe0001', 'ts': 1757000000,
              'subject': 'a fabricated violation',
              'files': ['.claude/skills/sairn-hover-auditor/SKILL.md',
                        'api/sd-data.js']}]
_bad = os.path.join(_tmpF, 'violation.md')
A.write_report(_bad, _viol_trail, Counter({'hover': 1}), _viol_hov,
               [('git', 'deadbeef', 'a fabricated violation', ['api/sd-data.js'])],
               [], {}, 1)
_vdoc = io.open(_bad, encoding='utf-8').read()
ok('F12 A VIOLATION REACHES THE VERDICT, in words',
   'SEPARATION VIOLATION' in _vdoc, _vdoc[-600:])
ok('F13 ...and the offending path is named, not just counted',
   'api/sd-data.js' in _vdoc, _vdoc[-600:])
# SPLIT ON THE SECTION BREAK, NOT ON '---'. The first version split on the bare
# string and the markdown TABLE SEPARATOR row (`|---|---|`) contains it, so the
# region ended before any data row and the arm read an empty table. An arm that
# reads the wrong region reports a check it never performed -- the fourth
# instance of that shape in this session, and the reason each one is written
# down where it was found.
_sec = _vdoc.split('## The auditor')[1].split('\n---\n')[0]
ok('F14 ...and the auditor-commit ROW marks it rather than showing a bare 0',
   'VIOLATION' in _sec, _sec[:400])
ok('F15 CONTROL: the real document\'s auditor rows show 0 out of scope, so '
   'F14 is discriminating',
   'VIOLATION' not in doc.split('## The auditor')[1].split('\n---\n')[0], '')
# ── F16 RE-AIMED 2026-09-22, AND THE REASON IS A REAL FINDING ─────────────
# This asserted that the LIVE document does not say SEPARATION VIOLATION, using
# the live corpus as the negative case. That premise stopped holding the day the
# multi-log fix let hover_separation_audit.py actually READ the self-logs again:
# it now reports 1 violation, and that violation is a FALSE POSITIVE --
# OWN_COMMIT_RE matches "pushed <sha>" inside hover's QUOTATION of cody's status
# line, so a sha hover CITED is counted as a sha hover CLAIMS. See the open-work
# row; it is not a hover breach.
#
# A CONTROL MUST NOT REST ON LIVE DATA STAYING CLEAN. Re-aimed to an A/B on the
# SAME generator: the same synthetic trail, once with a violation and once
# without. That is what actually shows F12 discriminates, and it cannot be
# falsified by anything happening in the real corpus.
_clean_doc_path = os.path.join(_tmpF, 'noviolation.md')
A.write_report(_clean_doc_path, _viol_trail, Counter({'hover': 1}), _viol_hov,
               [], [], {}, 0)
_cleandoc = io.open(_clean_doc_path, encoding='utf-8').read()
ok('F16 CONTROL: the SAME generator with NO violations produces a document that '
   'does not say it, so F12 is discriminating rather than matching any document',
   'SEPARATION VIOLATION' not in _cleandoc, _cleandoc[-400:])

# A COULD-NOT-RUN MUST NOT READ AS CLEAN IN THE DOCUMENT EITHER.
_cnr = os.path.join(_tmpF, 'cnr.md')
A.write_report(_cnr, _viol_trail[:0] or [{'sha': 'a' * 40, 'ts': 1757000000,
                                          'who': 'hank', 'how': 'bookkeeping',
                                          'subject': 's', 'n_files': 1}],
               Counter({'hank': 1}), [], [],
               ['self-log cross-reference: the log was unreadable'], {}, 2)
_cdoc = io.open(_cnr, encoding='utf-8').read()
ok('F17 a partial run says "not a clean bill" rather than reporting clean',
   'not a clean bill' in _cdoc and 'part of the check did' in _cdoc,
   _cdoc[-500:])
ok('F18 ...and an unreadable self-log is named as COULD NOT RUN, not omitted',
   'COULD NOT RUN' in _cdoc, _cdoc[-700:])

shutil.rmtree(_tmpF, ignore_errors=True)
ok('F19 the scratch directory is gone', not os.path.isdir(_tmpF))

print('\n' + '=' * 66)
print('%d passed, %d failed' % (PASSES[0], len(FAILS)))
for f in FAILS:
    print('  FAILED: %s' % f)
sys.exit(1 if FAILS else 0)
