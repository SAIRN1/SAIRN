"""tests/push_gate/check3_probe.py

Run:  python tests/push_gate/check3_probe.py

CHECK 3 -- DOES THE GATE REFUSE, OR DOES ONLY THE TOOL EXIT NON-ZERO?

── THE REASON THIS WAS LEFT UNCOVERED WAS WRONG, AND THAT IS THE FINDING ──────
tests/push_gate/check2_and_check5_probe.py shipped on 2026-09-12 with checks 1
and 3 recorded as NOT COVERED, and gave this reason for check 3:

    "Check 3 runs the SQL preflight against db/schema_snapshot.json and
     --require-live. Both are could-not-tell from a clone with no credentials."

That is wrong about check 3, and I wrote it. Check 3 needs a snapshot FILE, not
database access -- and the hook reads its path from SAIRN_SCHEMA_SNAPSHOT before
falling back to db/schema_snapshot.json (sairn_push_gate_hook.py, the `snapshot =`
line in check 3). A probe can hand it any snapshot it likes. Every one of check
3's deny paths is therefore reachable from a clone with no credentials at all.

Check 1 is a different story and stays uncovered: its deny needs
tools/sairn_load_state_check.py to exit 1, which is a LIVE comparison against a
licence, and its could-not-tell path deliberately ALLOWS with a note. Nothing in
this file claims otherwise.

── WHAT THE TOOL ALREADY PROVES, AND WHY THAT IS NOT THIS ────────────────────
tests/sql_preflight/run_probe.py already proves tools/sairn_sql_preflight.py
exits 4 on an absent, corrupt or empty snapshot and 1 on a missing table. That
is the CHECKER. It says nothing about whether the GATE turns those exits into a
refusal -- which is exactly the distinction that made this pass necessary:
tools/checkblocks.py printed `FAILED_BLOCKS:1` and exited 0, so it HAD the
finding and lacked the SIGNAL. Wiring is a separate claim from detection and
needs a separate proof.

── WHAT IS PLANTED ───────────────────────────────────────────────────────────
A committed sql/ file, plus a snapshot handed to the gate through
SAIRN_SCHEMA_SNAPSHOT, in five shapes:

    absent snapshot     -> preflight exit 4 -> gate DENY
    corrupt snapshot    -> preflight exit 4 -> gate DENY
    no-tables snapshot  -> preflight exit 4 -> gate DENY
    valid snapshot, sql naming a table it does not have -> exit 1 -> gate DENY
    the preflight TOOL absent from the clone            ->          gate DENY
    valid snapshot, sql naming only tables it HAS       -> exit 0 -> gate ALLOW

The last one is the control. Without it the four denies cannot be told apart
from "this gate denies everything", which is the shape that let two arms of the
2026-09-12 pass report checks 2 and 5 as proven when check 8 had answered. Every
deny arm below therefore asserts the REASON, and asserts it is not check 2 (the
credential guard, which runs first on the same sql_changed list) answering.

── ONE DENY PATH IS NOT COVERED, STATED RATHER THAN IMPLIED ──────────────────
The `except Exception` arm -- the preflight subprocess failing to start or
timing out -- has no fixture here. Making it fire needs either a 120-second
timeout or a broken interpreter, and neither can be arranged without changing
the gate or the tool, which would mean the probe proving its own edit. It is
read rather than run.

ARM F WAS A FINDING AND IS NOW A GUARD, WHICH IS WHY IT IS WORTH READING.
When this file was written, check 3 was wrapped in `if os.path.isfile(pf):` with
no else -- so a clone missing tools/sairn_sql_preflight.py skipped check 3 in
silence and the push was allowed. Arm F planted that absence and asserted the
ALLOW, recording the fail-open rather than pretending it was covered. Michael's
call, 2026-09-13: fix it, fail closed -- a missing or unresolvable state must get
more scrutiny, never less. The gate now denies, and arm F asserts the deny.

The inversion is the point. An arm written to pin a defect has to be flipped when
the defect is fixed, or it starts asserting the bug is still there; the previous
version of this paragraph said so and this is it happening.

Every fixture lives in a throwaway WORKTREE, never on a branch of this clone.
"""
import io
import json
import os
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


def run_gate(cwd, tip, base, snapshot):
    """Drive the REAL hook in prepush mode, from inside `cwd`.

    `snapshot` is handed over as SAIRN_SCHEMA_SNAPSHOT, which is the whole
    reason this check is reachable without credentials.
    """
    env = dict(os.environ)
    env['SAIRN_SCHEMA_SNAPSHOT'] = snapshot
    line = 'refs/heads/probe %s refs/heads/probe %s\n' % (tip, base)
    r = subprocess.run([sys.executable, GATE, '--pre-push'],
                       input=line, capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=cwd, env=env)
    return r.returncode, (r.stdout or '') + (r.stderr or '')


# Deliberately NOT a credential writer: check 2 runs first on the same
# sql_changed list, and a fixture that trips it would prove check 2 again.
CLEAN_SQL = """-- fixture: reads and writes one ordinary table.
insert into public.probe_widgets (id, name) values ('a', 'b');
update public.probe_widgets set name = 'c' where id = 'a';
"""

MISSING_TABLE_SQL = """-- fixture: names a table the snapshot does not have.
update public.probe_absent_table set name = 'c' where id = 'a';
"""

GOOD_SNAPSHOT = {
    '_generated_at': '2026-09-13T00:00:00Z',
    'probe_widgets': ['id', 'name'],
}


def write(path, text):
    io.open(path, 'w', encoding='utf-8', newline='').write(text)


def commit(wt, rel, body, subject):
    """Stage one file and commit it. The subject must NOT begin with PROBE --
    check 8 refuses those, and it would answer instead of check 3."""
    full = os.path.join(wt, rel)
    if not os.path.isdir(os.path.dirname(full)):
        os.makedirs(os.path.dirname(full))
    write(full, body)
    git(wt, 'add', rel)
    git(wt, '-c', 'user.name=probe', '-c', 'user.email=probe@local',
        'commit', '-q', '-m', subject)
    return git(wt, 'rev-parse', 'HEAD').stdout.strip()


def worktree():
    d = os.path.join(tempfile.gettempdir(), 'gate-probe3-%d' % os.getpid())
    git(REPO, 'worktree', 'add', '-q', '--detach', d, 'HEAD')
    return d


def drop(d):
    git(REPO, 'worktree', 'remove', '--force', d)
    git(REPO, 'worktree', 'prune')


TMP = tempfile.mkdtemp(prefix='gate-probe3-snap-')
SNAP_GOOD = os.path.join(TMP, 'good.json')
SNAP_CORRUPT = os.path.join(TMP, 'corrupt.json')
SNAP_EMPTY = os.path.join(TMP, 'empty.json')
SNAP_ABSENT = os.path.join(TMP, 'does_not_exist.json')
write(SNAP_GOOD, json.dumps(GOOD_SNAPSHOT))
write(SNAP_CORRUPT, '{"probe_widgets": ["id", "na')
write(SNAP_EMPTY, json.dumps({'_generated_at': '2026-09-13T00:00:00Z'}))

SQL_REL = 'sql/probe_check3_fixture.sql'

print('\nA. the fixtures are valid before anything is asserted about the gate')
wt = worktree()
try:
    ok('the worktree exists and is detached', os.path.isdir(os.path.join(wt, 'tools')))
    base = git(wt, 'rev-parse', 'HEAD').stdout.strip()
    tip_clean = commit(wt, SQL_REL, CLEAN_SQL, 'fixture: ordinary sql touching one table')
    ok('the fixture commit really contains the sql file',
       SQL_REL in git(wt, 'show', '--name-only', '--pretty=format:', tip_clean).stdout)
    ok('the absent snapshot really is absent', not os.path.exists(SNAP_ABSENT))

    # The tool must produce each exit on its own, or the gate arms below cannot
    # say WHICH condition the gate was reacting to.
    pf = os.path.join(REPO, 'tools', 'sairn_sql_preflight.py')
    for label, snap, want in (('absent', SNAP_ABSENT, 4),
                              ('corrupt', SNAP_CORRUPT, 4),
                              ('no tables', SNAP_EMPTY, 4)):
        p = subprocess.run([sys.executable, pf, '--gate', '--require-live', '--live', snap,
                            os.path.join(wt, SQL_REL)],
                           capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=REPO)
        ok('the preflight itself exits %d on a %s snapshot' % (want, label),
           p.returncode == want, 'exit=%d %s' % (p.returncode, (p.stdout or '')[-200:]))

    print('\nB. CHECK 3 -- an unusable snapshot must be REFUSED, three ways')
    for label, snap in (('absent', SNAP_ABSENT),
                        ('corrupt', SNAP_CORRUPT),
                        ('no tables', SNAP_EMPTY)):
        rc, out = run_gate(wt, tip_clean, base, snap)
        low = out.lower()
        ok('the GATE refuses a push whose snapshot is %s' % label, rc != 0,
           'exit=%d\n%s' % (rc, out[-400:]))
        ok('...and the refusal is CHECK 3, naming the snapshot' % (),
           'schema snapshot' in low and 'cannot be checked' in low, out[-500:])
        ok('...and it is NOT check 2, the credential guard, answering instead',
           'credential' not in low, out[-400:])
        ok('...and it is NOT the PROBE-fixture check answering instead',
           'PROBE fixture commit' not in out, out[-400:])

    print('\nC. CHECK 3 -- sql naming a table the database does not have must be REFUSED')
    git(wt, 'reset', '-q', '--hard', base)
    tip_missing = commit(wt, SQL_REL, MISSING_TABLE_SQL,
                         'fixture: sql naming a table the snapshot lacks')
    p = subprocess.run([sys.executable, pf, '--gate', '--require-live', '--live', SNAP_GOOD,
                        os.path.join(wt, SQL_REL)],
                       capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=REPO)
    ok('the preflight itself exits 1 on the missing table', p.returncode == 1,
       'exit=%d %s' % (p.returncode, (p.stdout or '')[-300:]))
    rc, out = run_gate(wt, tip_missing, base, SNAP_GOOD)
    low = out.lower()
    ok('the GATE refuses the push', rc != 0, 'exit=%d\n%s' % (rc, out[-400:]))
    ok('...and the refusal is CHECK 3, naming the live database',
       'live' in low and 'does not have' in low, out[-500:])
    ok('...and it names the offending table',
       'probe_absent_table' in low, out[-500:])
    ok('...and it is NOT check 2, the credential guard, answering instead',
       'credential' not in low, out[-400:])

    print('\nD. CONTROL -- the same sql against a snapshot that HAS the table is ALLOWED')
    git(wt, 'reset', '-q', '--hard', base)
    tip_ok = commit(wt, SQL_REL, CLEAN_SQL, 'fixture: ordinary sql, table present in snapshot')
    rc, out = run_gate(wt, tip_ok, base, SNAP_GOOD)
    ok('a push whose sql matches the snapshot is allowed', rc == 0,
       'exit=%d\n%s' % (rc, out[-500:]))

    print('\nE. CONTROL -- an unusable snapshot does NOT block a push that ships no sql')
    git(wt, 'reset', '-q', '--hard', base)
    tip_nosql = commit(wt, 'probe_check3_harmless.txt', 'probe\n',
                       'fixture: harmless text file')
    rc, out = run_gate(wt, tip_nosql, base, SNAP_ABSENT)
    ok('a push touching no sql/ file is allowed even with no snapshot at all', rc == 0,
       'exit=%d\n%s' % (rc, out[-500:]))

    print('\nF. CHECK 3 -- a MISSING CHECKER must be REFUSED, not skipped in silence')
    # Remove the tool from the WORKTREE -- never from this clone. Before
    # 2026-09-13 this arm asserted the opposite: the gate skipped check 3 and
    # allowed the push without a word. See the header.
    git(wt, 'reset', '-q', '--hard', base)
    tip_missing2 = commit(wt, SQL_REL, MISSING_TABLE_SQL,
                          'fixture: sql naming a table the snapshot lacks')
    wt_pf = os.path.join(wt, 'tools', 'sairn_sql_preflight.py')
    ok('the preflight is present before the sabotage removes it',
       os.path.isfile(wt_pf), wt_pf)
    os.remove(wt_pf)
    ok('...and the sabotage really applied -- it is gone',
       not os.path.exists(wt_pf), wt_pf)
    rc, out = run_gate(wt, tip_missing2, base, SNAP_GOOD)
    low = out.lower()
    ok('the GATE refuses a push shipping sql when the checker is absent', rc != 0,
       'exit=%d\n%s' % (rc, out[-400:]))
    # ASSERT THE PATH IT LOOKED FOR, NOT THE TOOL'S NAME. First version checked
    # only that "sairn_sql_preflight.py" appeared somewhere in the output, and a
    # mutation that blanked the `expected:` line SURVIVED -- the deny's closing
    # `git checkout -- tools/sairn_sql_preflight.py` hint carries the same name,
    # so the arm passed on a different sentence than the one it meant to read.
    # AND NORMALISE SEPARATORS BEFORE COMPARING. `wt_pf` comes from os.path.join
    # and is all backslashes on Windows; the gate builds its path from
    # `git rev-parse --show-toplevel`, which returns FORWARD slashes, so the two
    # never matched literally. The first version of this arm failed on every run
    # -- including inside the mutation harness, where it inflated every verdict by
    # one failing arm and made a SURVIVING mutation read as BITES.
    ok('...and the refusal names the exact path it looked for, rather than going quiet',
       'not in this' in low and wt_pf.replace('\\', '/') in out.replace('\\', '/'),
       'looked for %s in\n%s' % (wt_pf, out[-500:]))
    ok('...and it names the sql the push ships, so the reader knows what went unchecked',
       'probe_check3_fixture.sql' in out, out[-500:])
    ok('...and it is NOT check 2, the credential guard, answering instead',
       'credential' not in low, out[-400:])
    git(wt, 'checkout', '-q', '--', 'tools/sairn_sql_preflight.py')
    ok('the tool is restored in the worktree before it is dropped',
       os.path.isfile(wt_pf))
finally:
    drop(wt)
    ok('the throwaway worktree is removed', not os.path.isdir(wt))
    ok('no fixture was left on this clone',
       not os.path.exists(os.path.join(REPO, SQL_REL))
       and not os.path.exists(os.path.join(REPO, 'probe_check3_harmless.txt')))
    ok('this clone still has its own sql preflight tool',
       os.path.isfile(os.path.join(REPO, 'tools', 'sairn_sql_preflight.py')))
    ok('and this clone has no fixture commit on its branch',
       'fixture:' not in git(REPO, 'log', '--oneline', '-5', '--pretty=format:%s').stdout)

print('\n%d failure(s)' % len(FAIL))
for f in FAIL:
    print('  - ' + f)
sys.exit(1 if FAIL else 0)
