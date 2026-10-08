"""tools/hover_auditor_scope_gate.py must allow THIS clone's own claim file.

    python tests/run_hover_scope_own_claim_probe.py

Exit 0 all arms pass, 1 any arm fails, 2 could not run.

── THE DEFECT (H2 seq 401, re-filed with patch text at seq 409, sentinel
── corrected at seq 410) ───────────────────────────────────────────────────
Line 69 hardcoded `OWN_CLAIM = '.claude/claims/hover.json'`. A SECOND hover
instance -- identity `hover2` per tools/sairn_session_identity.py -- therefore
could not commit its OWN claim file: `.claude/claims/hover2.json` was refused at
`--pre-commit`, so hover2 structurally could not satisfy the claim-before-work
commit half (PR 2.2). The gate's 2026-09-18 ALLOW comment ("ONLY hover.json")
predates hover2 and had gone stale.

SECOND LOCATION OF ONE ASSUMPTION, not a new bug class: the same
single-instance hardcoding was already fixed once at hover finding #205
(`eligible_reviewers` hardcoding `HOVER_SESSION='hover'`).

── WHY THIS PROBE WAS WRITTEN BY A BUILD AGENT AND NOT BY H2 ───────────────
The finding is the auditor's; the fix is not. Per Michael 2026-09-30 (Option 2)
the verifier does not edit its own constraint gate, so H2 delivered patch text
and this fixture as TEXT and claimed nothing. This file is hank applying it.

── THE TWO ARMS, AND ARM 2 IS THE ONE THAT MAKES ARM 1 MEAN ANYTHING ───────
Arm 1 FAILS against the hardcoded OWN_CLAIM and passes after the patch. Arm 2 is
the KNOWN-BAD CONTROL and must pass BOTH before and after: the patch widens the
allowance to THIS clone's own claim file, never to all of them. Without arm 2,
"allow every claim file" would satisfy arm 1 and destroy the separation the gate
exists for. Arm 3 is the no-regression arm for H1.

EVERY ARM RUNS IN A THROWAWAY CLONE. Nothing here touches this repo.
"""
# Declares, for tools/checker_control_check.py, which checker(s) this file is
# the control for.
CONTROLS_FOR = ['hover_auditor_scope_gate.py']

import io
import os
import shutil
import subprocess
import sys
import tempfile


def _rm_ro(fn, path, _exc):
    """rmtree onerror: clear the read-only bit and retry once.

    git marks loose object files READ-ONLY and Windows will not unlink a
    read-only file, so `ignore_errors=True` leaves the object store behind and
    says nothing. Measured 2026-10-07: a cleanup that swallowed those refusals
    left 4,047 files, 38 of them read-only, in one abandoned clone.
    """
    import os as _os
    try:
        _os.chmod(path, 0o700)
        fn(path)
    except Exception:                                   # noqa: BLE001
        pass

REPO = subprocess.check_output(['git', 'rev-parse', '--show-toplevel'],
                               text=True).strip()
GATE = os.path.join(REPO, 'tools', 'hover_auditor_scope_gate.py')
IDENT = os.path.join(REPO, 'tools', 'sairn_session_identity.py')
SKILL = os.path.join(REPO, '.claude', 'skills', 'sairn-hover-auditor', 'SKILL.md')

# ── FAIL CLOSED ON AN ABSENT SUBJECT (PR §1.11) ─────────────────────────────
_absent = [p for p in (GATE, IDENT, SKILL) if not os.path.isfile(p)]
if _absent:
    print('COULD NOT RUN -- these do not exist, so NOTHING was verified:')
    for p in _absent:
        print('  MISSING  %s' % os.path.relpath(p, REPO))
    sys.exit(2)

fails = []


def check(name, cond, detail=''):
    print(('  ok   ' if cond else '  FAIL ') + name + ('' if cond else '  ' + detail))
    if not cond:
        fails.append(name)


def run_arm(rel_path, provision):
    """Exit code of --pre-commit in a throwaway clone provisioned as `provision`."""
    d = tempfile.mkdtemp(prefix='hscope-')
    try:
        subprocess.run(['git', 'init', '-q', d], check=True,
                       capture_output=True)
        gd = os.path.join(d, '.git')
        # ARMED: the gate only enforces in a clone marked as the auditor's.
        io.open(os.path.join(gd, 'sairn-hover-auditor-clone'), 'w').close()
        io.open(os.path.join(gd, 'sairn-session'), 'w',
                encoding='utf-8').write(provision)
        os.makedirs(os.path.join(d, 'tools'), exist_ok=True)
        shutil.copy(GATE, os.path.join(d, 'tools', 'hover_auditor_scope_gate.py'))
        shutil.copy(IDENT, os.path.join(d, 'tools', 'sairn_session_identity.py'))
        # The SKILL file is the gate's scope anchor -- without it the gate
        # refuses for a DIFFERENT reason and every arm below would be measuring
        # a missing file rather than the OWN_CLAIM rule.
        sk = os.path.join(d, '.claude', 'skills', 'sairn-hover-auditor')
        os.makedirs(sk, exist_ok=True)
        shutil.copy(SKILL, os.path.join(sk, 'SKILL.md'))
        tgt = os.path.join(d, rel_path.replace('/', os.sep))
        os.makedirs(os.path.dirname(tgt), exist_ok=True)
        io.open(tgt, 'w', encoding='utf-8').write('{}')
        subprocess.run(['git', '-C', d, 'add', rel_path], check=True,
                       capture_output=True)
        p = subprocess.run([sys.executable,
                            os.path.join(d, 'tools', 'hover_auditor_scope_gate.py'),
                            '--pre-commit'],
                           cwd=d, capture_output=True, text=True,
                           encoding='utf-8', errors='replace')
        return p.returncode, (p.stdout or '') + (p.stderr or '')
    finally:
        shutil.rmtree(d, onerror=_rm_ro)


print('hover scope gate -- a clone may commit ITS OWN claim file, and only '
      'its own\n')

rc1, out1 = run_arm('.claude/claims/hover2.json', 'hover2')
check('ARM 1: a hover2 clone may commit .claude/claims/hover2.json -- the '
      'defect: with OWN_CLAIM hardcoded to hover.json this rc is 1 and hover2 '
      'structurally cannot satisfy PR 2.2',
      rc1 == 0, 'rc=%d out=%s' % (rc1, out1[-400:]))

rc2, out2 = run_arm('.claude/claims/hank.json', 'hover2')
check('ARM 2 KNOWN-BAD CONTROL, must hold BOTH before and after: a hover2 '
      'clone must NOT commit hank.json. Without this arm, "allow every claim '
      'file" would satisfy arm 1 and delete the separation the gate exists for',
      rc2 != 0, 'rc=%d' % rc2)

rc3, out3 = run_arm('.claude/claims/hover.json', 'hover')
check('ARM 3 NO REGRESSION FOR H1: a hover clone may still commit hover.json',
      rc3 == 0, 'rc=%d out=%s' % (rc3, out3[-400:]))

rc4, out4 = run_arm('.claude/claims/hover.json', 'hover2')
check('ARM 4: a hover2 clone must NOT commit the OTHER auditor instance\'s '
      'claim file either -- "its own" means its own, and two auditor clones '
      'are still two parties',
      rc4 != 0, 'rc=%d' % rc4)

# ── ARM 5: THE UNPROVISIONED CLONE FAILS CLOSED ────────────────────────────
# H2's stated reason for choosing a sentinel over "fall back to hover.json": a
# silent fallback would let an UNMARKED clone commit hover.json again, which is
# the spoofable-by-absence shape sairn_session_identity.py's own header refuses.
# Provisioned with a name the identity module rejects, so session_name() raises
# and the fail-closed branch is the one under test.
rc5, out5 = run_arm('.claude/claims/hover.json', 'NOT A VALID NAME')
check('ARM 5 FAIL CLOSED: a clone whose identity cannot be established commits '
      'NO claim file at all, rather than defaulting to some session\'s',
      rc5 != 0, 'rc=%d out=%s' % (rc5, out5[-300:]))

print()
if fails:
    print('%d ARM(S) FAILED: %s' % (len(fails), ', '.join(fails)))
else:
    print('ALL ARMS PASS -- own claim file allowed per clone, every other '
          'session\'s still refused.')
sys.exit(1 if fails else 0)
