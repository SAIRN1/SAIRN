"""tests/push_gate/missing_checker_probe.py

Run:  python tests/push_gate/missing_checker_probe.py

A MISSING CHECKER IS NOT A CLEAN PUSH -- the whole class, not one instance.

── WHY THIS EXISTS ───────────────────────────────────────────────────────────
On 2026-09-13 tests/push_gate/check3_probe.py found that check 3 was wrapped in
`if os.path.isfile(pf):` with no else, so a clone without
tools/sairn_sql_preflight.py skipped it in silence. Reading the file for the same
shape found FOUR MORE, all written the same way and none of them noticed:

    checks 2-10 entirely  `if not os.path.isfile(checker): sys.exit(0)`
    check 2               `if os.path.isfile(gcheck):`   employee_auth_guard_check
    check 2's subprocess  `except Exception: g = None`   then skipped
    check 4               `if os.path.isfile(seam):`     sairn_seam_check
    check 5               `if os.path.isfile(reach):`    sairn_reachability_check

The first is the widest fail-open this gate has had. The early exit dates from
when check 1 was the only check; nine more were added around it, and every one of
them stopped running whenever ONE unrelated tool was absent.

Michael's call, 2026-09-13: fail closed -- a missing or unresolvable state must
get more scrutiny, never less.

── TWO OF THE FIVE ARE NOT DENIES, AND THAT IS DELIBERATE ────────────────────
The whole-gate early exit was NOT converted to a deny. Check 1's could-not-tell
path ALLOWS with a notice by a standing decision -- a missing licence key must not
block somebody else's legitimate push -- so the tool's absence is routed into
check 1's own `untold` list, where it already has a voice, and checks 2 through 10
now run regardless of it. Section E below proves that: with the load-state checker
removed, a push carrying an unreachable feature is refused BY CHECK 5. Before the
fix the gate exited 0 and said nothing.

── ONE OF THE FIVE CHANGES HAS NO ARM HERE, AND IT IS SAID RATHER THAN HIDDEN ─
Check 2's `except Exception: g = None` -- an unrunnable guard subprocess -- now
denies instead of skipping. Nothing below proves it. Reaching it needs the
subprocess to fail to START or to time out, and neither can be arranged without
editing the gate or the tool, which would mean the probe proving its own edit.
Exactly the same boundary check 3's `except` arm sits behind. A mutation control
is recorded for it in the commit as SURVIVING rather than reported as covered.

── WHAT IS PLANTED ───────────────────────────────────────────────────────────
Each tool is removed from a throwaway WORKTREE -- never from this clone -- and a
push that should reach the check it belongs to is run against the real hook. Each
arm asserts the deny NAMES THE PATH IT LOOKED FOR, not just that something denied:
a gate in a clone missing one tool is missing several checks' worth of answers,
and an arm that accepts any refusal cannot tell which one spoke.

Separators are normalised before comparing. `os.path.join` gives backslashes and
`git rev-parse --show-toplevel` gives forward slashes, and an arm that compares
them literally fails on every run -- which, inside a mutation harness that counts
failing arms, reads as every mutation biting.
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


def norm(s):
    return s.replace('\\', '/')


def git(cwd, *args):
    return subprocess.run(['git', '-C', cwd] + list(args), capture_output=True, text=True, encoding='utf-8', errors='replace')


def run_gate(cwd, tip, base, snapshot):
    env = dict(os.environ)
    env['SAIRN_SCHEMA_SNAPSHOT'] = snapshot
    line = 'refs/heads/probe %s refs/heads/probe %s\n' % (tip, base)
    r = subprocess.run([sys.executable, GATE, '--pre-push'],
                       input=line, capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=cwd, env=env)
    return r.returncode, (r.stdout or '') + (r.stderr or '')


PLAIN_SQL = """-- fixture: one ordinary table, no credential rows.
insert into public.probe_widgets (id, name) values ('a', 'b');
"""

PLAIN_API = """// fixture: an api file with nothing interesting in it.
module.exports = function handler(req, res) { res.status(200).json({ ok: true }); };
"""

# THE HTML FIXTURE LIVES IN A SUBDIRECTORY, AND THAT IS NOT COSMETIC.
# A new ROOT-level .html is counted as an app by the generated documents, so
# on 2026-09-14 a new blocking check -- 'this push makes a GENERATED document
# stop matching what it is derived from' -- correctly refused the CONTROL arm
# for a reason that had nothing to do with the tool under test. Reachability
# (check 5) scans every changed .html wherever it lives, so the arm still
# exercises what it names; MASTER-PLAN.md counts root files only, so the
# fixture no longer makes a derived document stale.
PLAIN_HTML = """<!doctype html>
<div class="panel" id="panel-zz"><button onclick="zzProbe()">go</button></div>
<script>function zzProbe(){ return 1; }</script>
"""

# The 2026-08-30 StoneDesk shape: the only entry point is appended into a
# display:none stub. APPEND needs getElementById(...) and .appendChild( in ONE
# expression -- split them and the checker exits 0 and this proves nothing.
UNREACHABLE_HTML = """<!doctype html>
<div class="panel" id="panel-zz"></div>
<div id="zz-actions" style="display:none"></div>
<script>
function zzProbeFeature(){ return 1; }
(function(){
  var b = document.createElement('button');
  b.onclick = zzProbeFeature;
  document.getElementById('zz-actions').appendChild(b);
})();
</script>
"""

TMP = tempfile.mkdtemp(prefix='gate-missing-snap-')
SNAP = os.path.join(TMP, 'good.json')
io.open(SNAP, 'w', encoding='utf-8', newline='').write(json.dumps({
    '_generated_at': '2026-09-13T00:00:00Z',
    'probe_widgets': ['id', 'name'],
}))


def commit(wt, rel, body, subject):
    """Stage one file and commit. The subject must NOT begin with PROBE -- check
    8 refuses those, and it would answer instead of the check under test."""
    full = os.path.join(wt, rel)
    d = os.path.dirname(full)
    if d and not os.path.isdir(d):
        os.makedirs(d)
    io.open(full, 'w', encoding='utf-8', newline='').write(body)
    git(wt, 'add', rel)
    git(wt, '-c', 'user.name=probe', '-c', 'user.email=probe@local',
        'commit', '-q', '-m', subject)
    return git(wt, 'rev-parse', 'HEAD').stdout.strip()


def worktree():
    d = os.path.join(tempfile.gettempdir(), 'gate-missing-%d' % os.getpid())
    git(REPO, 'worktree', 'add', '-q', '--detach', d, 'HEAD')
    return d


def drop(d):
    git(REPO, 'worktree', 'remove', '--force', d)
    git(REPO, 'worktree', 'prune')


TOOLS = {
    'guard': 'tools/employee_auth_guard_check.py',
    'seam': 'tools/sairn_seam_check.py',
    'reach': 'tools/sairn_reachability_check.py',
    'loadstate': 'tools/sairn_load_state_check.py',
}

print('\nA. the worktree and every tool this probe removes really exist first')
wt = worktree()
try:
    ok('the worktree exists and is detached', os.path.isdir(os.path.join(wt, 'tools')))
    base = git(wt, 'rev-parse', 'HEAD').stdout.strip()
    for name, rel in sorted(TOOLS.items()):
        ok('%s is present before it is removed (%s)' % (name, rel),
           os.path.isfile(os.path.join(wt, rel)))

    def arm(section, title, rel_tool, fixture_rel, fixture_body, subject, expect_in):
        """Remove one tool, push one file, assert the deny names that tool's path."""
        print('\n%s' % section)
        git(wt, 'reset', '-q', '--hard', base)
        tip = commit(wt, fixture_rel, fixture_body, subject)
        victim = os.path.join(wt, rel_tool)
        ok('%s -- the tool is present before the sabotage removes it' % title,
           os.path.isfile(victim), victim)
        os.remove(victim)
        ok('...and the sabotage really applied -- it is gone',
           not os.path.exists(victim), victim)
        try:
            rc, out = run_gate(wt, tip, base, SNAP)
        finally:
            git(wt, 'checkout', '-q', '--', rel_tool)
        ok('%s -- the GATE refuses the push' % title, rc != 0,
           'exit=%d\n%s' % (rc, out[-400:]))
        ok('...and the refusal names the exact path it looked for',
           norm(victim) in norm(out), 'looked for %s in\n%s' % (victim, out[-500:]))
        for phrase in expect_in:
            ok('...and the refusal says %r' % phrase, phrase in out.lower(), out[-400:])
        ok('...and it is NOT the PROBE-fixture check answering instead',
           'PROBE fixture commit' not in out, out[-300:])
        ok('...and the tool is restored in the worktree', os.path.isfile(victim))
        # THE PER-ARM CONTROL, and it is stronger than a generic clean push.
        # Same commit, same gate, tool PRESENT: whatever happens now, it must not
        # be this deny. A separate "a clean file is allowed" arm cannot say that,
        # and for api/ it cannot exist at all -- a NEW api file is refused by the
        # public-endpoint-declaration check no matter what else is true, which is
        # correct behaviour and would have made a clean-push control impossible
        # to write honestly.
        rc2, out2 = run_gate(wt, tip, base, SNAP)
        ok('CONTROL: with the tool present, the gate does NOT give that answer',
           norm(victim) not in norm(out2), 'exit=%d\n%s' % (rc2, out2[-400:]))

    arm('B. CHECK 2 -- a missing credential-writer guard',
        'check 2', TOOLS['guard'], 'sql/probe_missing_checker.sql', PLAIN_SQL,
        'fixture: ordinary sql', ['credential-writer guard'])

    arm('C. CHECK 4 -- a missing endpoint/engine seam check',
        'check 4', TOOLS['seam'], 'api/probe_missing_checker.js', PLAIN_API,
        'fixture: an ordinary api file', ['seam'])

    arm('D. CHECK 5 -- a missing reachability check',
        'check 5', TOOLS['reach'], 'probe_fixtures/probe_missing_checker.html', PLAIN_HTML,
        'fixture: an ordinary html file', ['reachability'])

    # ── THE ONE THAT IS NOT A DENY ────────────────────────────────────────────
    print('\nE. THE WIDEST FAIL-OPEN -- a missing load-state checker must not '
          'switch off checks 2 to 10')
    git(wt, 'reset', '-q', '--hard', base)
    tip = commit(wt, 'probe_fixtures/probe_missing_checker.html', UNREACHABLE_HTML,
                 'fixture: a feature with no way in')
    victim = os.path.join(wt, TOOLS['loadstate'])
    ok('the load-state checker is present before the sabotage removes it',
       os.path.isfile(victim), victim)
    os.remove(victim)
    ok('...and the sabotage really applied -- it is gone',
       not os.path.exists(victim), victim)
    try:
        rc, out = run_gate(wt, tip, base, SNAP)
    finally:
        git(wt, 'checkout', '-q', '--', TOOLS['loadstate'])
    low = out.lower()
    # Before 2026-09-13 this was `sys.exit(0)` and the answer here was exit 0
    # with no output at all -- nine checks skipped over one unrelated tool.
    ok('the GATE still refuses, with the load-state checker absent', rc != 0,
       'exit=%d -- if this is 0 the early exit is back\n%s' % (rc, out[-400:]))
    ok('...and the refusal is CHECK 5, so checks 2-10 really did run',
       'reach' in low and 'probe_fixtures/probe_missing_checker.html' in out, out[-500:])
    ok('...and it is NOT the PROBE-fixture check answering instead',
       'PROBE fixture commit' not in out, out[-300:])
    ok('...and the load-state checker is restored in the worktree',
       os.path.isfile(victim))

    # ── CONTROLS: without these every arm above is "the gate denies everything" ─
    # No api/ arm here on purpose: a NEW api file is refused by the
    # public-endpoint-declaration check regardless, which is correct, so there is
    # no honest "clean api push" to write. The per-arm control above covers it.
    print('\nF. CONTROLS -- with every tool present, clean pushes are ALLOWED')
    for label, rel, body, subject in (
            ('a text file', 'probe_missing_checker.txt', 'probe\n',
             'fixture: harmless text'),
            ('an html file with a reachable control', 'probe_fixtures/probe_missing_checker.html',
             PLAIN_HTML, 'fixture: an ordinary html file'),
            ('a sql file whose table the snapshot has', 'sql/probe_missing_checker.sql',
             PLAIN_SQL, 'fixture: ordinary sql')):
        git(wt, 'reset', '-q', '--hard', base)
        tip = commit(wt, rel, body, subject)
        rc, out = run_gate(wt, tip, base, SNAP)
        ok('a push of %s is allowed' % label, rc == 0, 'exit=%d\n%s' % (rc, out[-400:]))
finally:
    drop(wt)
    ok('the throwaway worktree is removed', not os.path.isdir(wt))
    ok('every tool this probe removes is still in THIS clone',
       all(os.path.isfile(os.path.join(REPO, r)) for r in TOOLS.values()))
    ok('no fixture was left on this clone',
       not any(os.path.exists(os.path.join(REPO, p)) for p in
               ('probe_fixtures/probe_missing_checker.html', 'probe_missing_checker.txt',
                'api/probe_missing_checker.js', 'sql/probe_missing_checker.sql')))
    ok('and this clone has no fixture commit on its branch',
       'fixture:' not in git(REPO, 'log', '--oneline', '-5', '--pretty=format:%s').stdout)

print('\n%d failure(s)' % len(FAIL))
for f in FAIL:
    print('  - ' + f)
sys.exit(1 if FAIL else 0)
