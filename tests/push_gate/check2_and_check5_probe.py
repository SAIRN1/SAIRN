"""tests/push_gate/check2_and_check5_probe.py

Run:  python tests/push_gate/check2_and_check5_probe.py

DO THE BLOCKING CHECKS ACTUALLY REFUSE? Checks 2 and 5 had never been asked.

── WHY THIS EXISTS, AND IT IS NOT A HYPOTHETICAL ──────────────────────────────
On 2026-09-12 tools/checkblocks.py -- Guardian Check 0a, the one CLAUDE.md calls
non-negotiable -- was found printing `FAILED_BLOCKS:1` and exiting 0. It HAD the
finding and lacked the SIGNAL. Any wiring on its exit code would have reported a
clean pass on a file that does not parse.

That makes "does this checker have a non-zero exit path" the wrong question and
"does the gate refuse when given something to refuse" the right one. Measured
across the ten numbered checks in tools/sairn_push_gate_hook.py, by which probe
plants a finding and asserts a deny:

    check 4  tests/push_gate/check4_probe.py                 covered
    check 6  tests/push_gate/redaction_base_probe.py         covered
    check 7  check7_probe.py + preauth_exemption_anchor_probe covered
    check 8  tests/push_gate/check8_probe.py                 covered
    check 9  tests/push_gate/check9_probe.py                 covered
    check 10 tests/push_gate/gate_freshness_probe.py         covered (report-only)
    check 3  tests/push_gate/check3_probe.py                 covered (2026-09-13)
    check 1  -- NOT COVERED
    check 2  -- NOT COVERED   <- this file
    check 5  -- NOT COVERED   <- this file

tests/push_gate/refspec_and_override_probe.py MENTIONS 1, 2 and 3, and that is
all it does with them: it is about refspec parsing and the override, not about
whether those checks refuse.

── WHY 1 IS NOT IN HERE, stated rather than left as a silence ────────────────
Check 1 compares LIVE seed content against the repo and needs a licence key, and
a probe that cannot distinguish "the gate refused" from "the gate could not run"
would assert nothing. Its could-not-tell path deliberately ALLOWS with a note, so
there is nothing to plant from a clone with no credentials. Recorded here so the
remaining gap is visible rather than implied by its absence.

── THE REASON GIVEN FOR CHECK 3 WAS WRONG, AND IT IS CORRECTED HERE ──────────
This header originally said check 3 was uncoverable for the same reason as check
1. It is not. Check 3 needs a snapshot FILE, not database access, and the hook
reads its path from SAIRN_SCHEMA_SNAPSHOT before falling back to
db/schema_snapshot.json -- so a probe can hand it any snapshot it likes and reach
every one of its deny paths with no credentials at all.
tests/push_gate/check3_probe.py does that, 2026-09-13.

── WHAT IS PLANTED ───────────────────────────────────────────────────────────
Check 2: a sql/ file that writes *_employee_auth rows with no recoverability
         guard. That is a real shape -- sql/stonedesk_recovery_admin_seed.sql was
         exactly this until 2026-09-11, and the gate denied it on the day the
         fail-open hiding it was closed.
Check 5: an .html file with a feature whose only entry point is injected into an
         empty display:none stub -- the StoneDesk shape from 2026-08-30 where
         three complete AI-backed features had no way in.

── ONE MUTATION SURVIVED AND IS RECORDED RATHER THAN PATCHED AROUND ──────────
Changing check 5's `if rr.returncode == 1:` to `!= 0` does not fail these arms.
That is not a hole: `!= 0` makes the gate deny on COULD-NOT-TELL as well, which
is MORE strict, so the mutation is a behaviour change rather than a defect. And
it cannot be pinned from the other side cheaply -- tried, rather than assumed:
tools/sairn_reachability_check.py exits 0 on a file with no panels and on an
almost-empty file, so there is no reachable could-not-tell exit to build a
fixture from. Inventing one would be fabricating the fault.

The two mutations that DO matter both bite: emptying `sql_changed` so check 2
never looks, and discarding the reachability result so check 5 never denies.

Every fixture lives in a throwaway WORKTREE, never on a branch of this clone --
the discipline fourth's `push-gate-probes-commit-to-main` pass established after
check4 and check7 planted commits on the working branch.
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile

REPO = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True, encoding='utf-8', errors='replace').stdout.strip()
GATE = os.path.join(REPO, 'tools', 'sairn_push_gate_hook.py')
FAIL = []


def ok(name, cond, detail=''):
    print('  %s %s%s' % ('PASS ' if cond else 'FAIL ', name,
                         '' if cond else '\n        ' + str(detail)[:400]))
    if not cond:
        FAIL.append(name)


def git(cwd, *args):
    return subprocess.run(['git', '-C', cwd] + list(args), capture_output=True, text=True, encoding='utf-8', errors='replace')


def run_gate(cwd, tip, base):
    """Drive the REAL hook in prepush mode, from inside `cwd`."""
    line = 'refs/heads/probe %s refs/heads/probe %s\n' % (tip, base)
    r = subprocess.run([sys.executable, GATE, '--pre-push'],
                       input=line, capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=cwd)
    return r.returncode, (r.stdout or '') + (r.stderr or '')


UNGUARDED_SQL = """-- PROBE FIXTURE -- a credential writer with no recoverability guard.
insert into public.sd_employee_auth
  (license_hash, employee_id, display_name, role, pin_hash, pin_salt, active)
values ('deadbeef', 'probe-admin', 'Probe', 'admin', 'x', 'y', true)
on conflict (license_hash, employee_id) do update set active = true;
"""

UNREACHABLE_HTML = """<!doctype html>
<div class="panel" id="panel-zz"></div>
<div id="zz-actions" style="display:none"></div>
<script>
// PROBE FIXTURE -- the 2026-08-30 StoneDesk shape, written to the R2 DETECTOR'S
// shape deliberately. Two earlier versions did not reproduce the finding at all:
// one used innerHTML, and one split getElementById and appendChild across two
// statements -- APPEND requires them in ONE expression with no `;` or newline
// between, within 120 characters. Both times the checker exited 0 and the gate
// denied for a different reason (check 8, because the fixture commit subject
// began with "PROBE"), so two arms passed on the wrong check.
//
// A fixture that does not reproduce the finding tests nothing, and an arm that
// accepts any non-zero exit cannot tell which check answered.
function zzProbeFeature(){ return 1; }
(function(){
  var b = document.createElement('button');
  b.onclick = zzProbeFeature;
  document.getElementById('zz-actions').appendChild(b);
})();
</script>
"""


def worktree():
    d = os.path.join(tempfile.gettempdir(), 'gate-probe-%d' % os.getpid())
    git(REPO, 'worktree', 'add', '-q', '--detach', d, 'HEAD')
    return d


def drop(d):
    git(REPO, 'worktree', 'remove', '--force', d)
    git(REPO, 'worktree', 'prune')


print('\nA. the fixtures are valid before anything is asserted about the gate')
wt = worktree()
try:
    ok('the worktree exists and is detached', os.path.isdir(os.path.join(wt, 'tools')))
    base = git(wt, 'rev-parse', 'HEAD').stdout.strip()

    # ── CHECK 2 ────────────────────────────────────────────────────────────
    print('\nB. CHECK 2 -- an unguarded credential writer must be REFUSED')
    rel = os.path.join('sql', 'PROBE_unguarded_auth_writer.sql')
    io.open(os.path.join(wt, rel), 'w', encoding='utf-8', newline='').write(UNGUARDED_SQL)
    git(wt, 'add', rel)
    git(wt, '-c', 'user.name=probe', '-c', 'user.email=probe@local',
        'commit', '-q', '-m', 'fixture: unguarded credential writer')
    tip = git(wt, 'rev-parse', 'HEAD').stdout.strip()
    ok('the fixture commit really contains the sql file',
       rel.replace('\\', '/') in git(wt, 'show', '--name-only', '--pretty=format:', tip).stdout)
    # The guard tool must see it on its own first, or the gate arm proves nothing.
    g = subprocess.run([sys.executable, os.path.join(REPO, 'tools', 'employee_auth_guard_check.py'),
                        '--changed', os.path.join(wt, rel)],
                       capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=REPO)
    ok('the guard tool itself refuses the fixture (exit 1)', g.returncode == 1,
       'exit=%d %s' % (g.returncode, g.stdout[-200:]))
    rc, out = run_gate(wt, tip, base)
    ok('the GATE refuses the push', rc != 0, 'exit=%d\n%s' % (rc, out[-400:]))
    # THE REASON, NOT JUST THE EXIT CODE -- and that distinction is why this file
    # needed two passes. The first version accepted any non-zero exit as proof of
    # checks 2 and 5, while the deny was really CHECK 8: the fixture commit
    # subjects began with "PROBE", which is exactly what check 8 refuses. Two arms
    # passed on the WRONG CHECK. An arm that cannot say which check answered is the
    # same defect as a passing assertion that checks the wrong thing.
    ok('...and the refusal is CHECK 2, naming the credential guard',
       'credential' in out.lower() and 'recoverab' in out.lower(), out[-500:])
    ok('...and names the offending file',
       'PROBE_unguarded_auth_writer' in out, out[-400:])
    ok('...and it is NOT the PROBE-fixture check answering instead',
       'PROBE fixture commit' not in out, out[-400:])

    # ── CHECK 5 ────────────────────────────────────────────────────────────
    print('\nC. CHECK 5 -- an unreachable feature must be REFUSED')
    git(wt, 'reset', '-q', '--hard', base)
    rel2 = 'PROBE_unreachable.html'
    io.open(os.path.join(wt, rel2), 'w', encoding='utf-8', newline='').write(UNREACHABLE_HTML)
    git(wt, 'add', rel2)
    git(wt, '-c', 'user.name=probe', '-c', 'user.email=probe@local',
        'commit', '-q', '-m', 'fixture: unreachable feature')
    tip2 = git(wt, 'rev-parse', 'HEAD').stdout.strip()
    r = subprocess.run([sys.executable, os.path.join(REPO, 'tools', 'sairn_reachability_check.py'),
                        os.path.join(wt, rel2)], capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=REPO)
    ok('the reachability checker itself refuses the fixture (exit 1)', r.returncode == 1,
       'exit=%d %s' % (r.returncode, (r.stdout or '')[-300:]))
    rc2, out2 = run_gate(wt, tip2, base)
    ok('the GATE refuses the push', rc2 != 0, 'exit=%d\n%s' % (rc2, out2[-400:]))
    ok('...and the refusal is CHECK 5, naming reachability AND the file',
       'reach' in out2.lower() and 'PROBE_unreachable' in out2, out2[-500:])
    ok('...and it is NOT the PROBE-fixture check answering instead',
       'PROBE fixture commit' not in out2, out2[-400:])

    # ── THE CONTROL THAT MAKES BOTH ARMS MEAN ANYTHING ────────────────────
    print('\nD. CONTROL -- a clean push is ALLOWED, or the arms above prove nothing')
    git(wt, 'reset', '-q', '--hard', base)
    io.open(os.path.join(wt, 'PROBE_harmless.txt'), 'w', encoding='utf-8').write('probe\n')
    git(wt, 'add', 'PROBE_harmless.txt')
    git(wt, '-c', 'user.name=probe', '-c', 'user.email=probe@local',
        'commit', '-q', '-m', 'fixture: harmless text file')
    tip3 = git(wt, 'rev-parse', 'HEAD').stdout.strip()
    rc3, out3 = run_gate(wt, tip3, base)
    ok('a push touching neither sql/ nor .html is allowed', rc3 == 0,
       'exit=%d\n%s' % (rc3, out3[-400:]))
finally:
    drop(wt)
    ok('the throwaway worktree is removed', not os.path.isdir(wt))
    ok('no PROBE fixture was left on this clone',
       not os.path.exists(os.path.join(REPO, 'PROBE_unreachable.html'))
       and not os.path.exists(os.path.join(REPO, 'sql', 'PROBE_unguarded_auth_writer.sql')))
    ok('and this clone has no PROBE commit on its branch',
       'PROBE' not in git(REPO, 'log', '--oneline', '-5', '--pretty=format:%s').stdout)

print('\n%d failure(s)' % len(FAIL))
for f in FAIL:
    print('  - ' + f)
sys.exit(1 if FAIL else 0)
