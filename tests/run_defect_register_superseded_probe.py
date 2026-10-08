#!/usr/bin/env python
# OWNER: cc
"""Is `superseded_by` an EARNED skip, or a self-certifying exemption?

    python tests/run_defect_register_superseded_probe.py

Exit 0 all arms pass, 1 an arm failed, 2 COULD NOT RUN.

WHY THE FIELD EXISTS. Four pairs of records in docs/defect-density-register.json
are byte-identical apart from `commit` -- one defect recorded twice either side of
a rebase -- and they inflate the CRITICAL count from 31 to 34. Deleting the stale
twin loses nothing factual, and it fights this ledger's own append-only invariant:
`tools/sairn_rebase_resolve.py` REFUSES on a deleted record, in every clone. So the
stale twin stays and carries a pointer to its survivor instead.

WHY THE SKIP IS CONDITIONAL, which is the whole subject of this probe. An
unconditional `if rec.get('superseded_by'): continue` would be a SELF-CERTIFYING
EXEMPTION: one field, typed by anybody, and the record leaves every count with
nothing checked. And a superseded record with no live survivor is WORSE than the
duplicate it was clearing -- a duplicate at least double-counts a REAL defect,
while this DROPS one out of every figure with nothing carrying it.

So the skip is granted only when the named survivor EXISTS and is an ANCESTOR of
the base. Four failure shapes, each a FINDING rather than a skip:

    missing       the survivor does not resolve as an object at all
    unreachable   it resolves but is NOT an ancestor -- a dangling object, so the
                  pointer would retire a real record in favour of one that is not
                  on the branch. `resolves()` and `reachable()` are different
                  questions and this repo has paid for conflating them before.
    self          the record names ITSELF
    could-not-tell  reachability could not be measured; NOT folded into clean

AND --reseat NEVER TOUCHES ONE. Re-pointing a retired record's sha would either
recreate the duplicate it was retired to avoid or move a pointer nobody reads, and
either way a "re-seated 1 record(s)" line over a retired record is a success report
about nothing.

EVERY ARM RUNS IN A THROWAWAY GIT REPOSITORY IT BUILDS ITSELF, with two real
commits and a hand-built register. Nothing in this clone is read as a subject and
nothing in it is written -- which matters more than usual, because the subject under
test WRITES A SHARED LEDGER.

WHAT THIS PROBE CANNOT SEE, stated rather than discovered later:
  * whether a given pair SHOULD be collapsed. It asserts the mechanism is safe; the
    decision about which twin survives is the owner's and this field does not make
    it for them.
  * the real 2MB register's cross-clone merge behaviour. `sairn_rebase_resolve.py`
    reads `merge_policy` and is not exercised here, so whether a superseded record
    survives a 3-way merge intact is UNTESTED and is the obvious next arm.
  * a survivor that is an ancestor now and is rebased away later. The check is as
    of the run, like every reachability answer in this repo.
"""
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(ROOT, 'tools', 'defect_register.py')
NL = chr(10)
REGPATH = os.path.join('docs', 'defect-density-register.json')

if not os.path.isfile(TOOL):
    print('COULD NOT RUN -- %s is absent. This probe is about that file and '
          'reports nothing without it.' % TOOL)
    sys.exit(2)

_argv = sys.argv
sys.argv = ['superseded_probe']
try:
    _spec = importlib.util.spec_from_file_location('dr_sup_probe', TOOL)
    DR = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(DR)
finally:
    sys.argv = _argv

for _name in ('superseded_survivor', 'resolves', 'SUPERSEDED_FIELD'):
    if not hasattr(DR, _name):
        print('COULD NOT RUN -- %s has no %s. The feature this probe is about is '
              'absent, and reporting clean would be the defect.' % (TOOL, _name))
        sys.exit(2)


def git(cwd, *a):
    return subprocess.run(['git'] + list(a), cwd=cwd, capture_output=True,
                          text=True, encoding='utf-8', errors='replace')


def record(commit, subject, summary, method='code-review', **extra):
    r = {
        'commit': commit, 'date': '2026-10-07', 'subject': subject,
        'files': ['tools/x.py'], 'lines_added': 1, 'lines_removed': 0,
        'app': 'tooling', 'layer': 'tooling', 'severity': 'low',
        'detection_method': method, 'summary': summary,
        'rules': [], 'citation_confidence': 'not-citable',
        'citation_note': 'a probe fixture, cited against no standing rule',
        'injection_phase': 'coding', 'phase_confidence': 'stated',
        'found_by_tool': None, 'found_by_session': None,
        'injection': {'unknown_reason': 'a probe fixture'},
    }
    r.update(extra)
    return r


SUBJ = 'fix(thing): the real subject'


def build(make_records):
    """A repo with TWO commits: HEAD (reachable) and a DANGLING one.

    The dangling commit is made by committing on a temporary branch and then
    deleting the branch, so the object resolves while not being an ancestor of
    HEAD. That is the `unreachable` state and it cannot be faked with a random
    hex string, which would only ever be `missing`.
    """
    d = tempfile.mkdtemp(prefix='sup-probe-')
    git(d, 'init', '-q')
    git(d, 'config', 'user.email', 'probe@x.invalid')
    git(d, 'config', 'user.name', 'probe')
    os.makedirs(os.path.join(d, 'docs'))
    io.open(os.path.join(d, 'docs', 'SAIRN-PROCESS-RULES.md'), 'w',
            encoding='utf-8', newline=NL).write('### 1.1 a rule' + NL)
    io.open(os.path.join(d, 'a.txt'), 'w', encoding='utf-8', newline=NL).write('a' + NL)
    git(d, 'add', '-A')
    git(d, 'commit', '-q', '-m', 'base commit')
    io.open(os.path.join(d, 'b.txt'), 'w', encoding='utf-8', newline=NL).write('b' + NL)
    git(d, 'add', '-A')
    git(d, 'commit', '-q', '-m', SUBJ)
    head = git(d, 'rev-parse', 'HEAD').stdout.strip()

    git(d, 'checkout', '-q', '-b', 'zz-dangling')
    io.open(os.path.join(d, 'c.txt'), 'w', encoding='utf-8', newline=NL).write('c' + NL)
    git(d, 'add', '-A')
    git(d, 'commit', '-q', '-m', 'a commit that will be orphaned')
    dangling = git(d, 'rev-parse', 'HEAD').stdout.strip()
    git(d, 'checkout', '-q', '-')
    git(d, 'branch', '-q', '-D', 'zz-dangling')

    if len(head) != 40 or len(dangling) != 40:
        raise RuntimeError('fixture repo did not produce two commits')
    base = git(d, 'rev-parse', 'HEAD~1').stdout.strip()
    reg = {'started': '2026-09-09', 'note': 'probe fixture',
           'records': make_records(head, dangling, base)}
    io.open(os.path.join(d, REGPATH), 'w', encoding='utf-8', newline='').write(
        json.dumps(reg, indent=2) + NL)
    return d, head, dangling, base


def in_repo(d, fn):
    """Run `fn()` with the module pointed at the throwaway repo, stdout captured."""
    old_repo, old_out = DR.REPO, sys.stdout
    sink = io.StringIO()
    try:
        DR.REPO = d
        sys.stdout = sink
        rc = fn()
    except Exception as e:                                       # noqa: BLE001
        rc = 'RAISED %s: %s' % (type(e).__name__, e)
    finally:
        DR.REPO, sys.stdout = old_repo, old_out
    return rc, sink.getvalue()


def reg_text(d):
    return io.open(os.path.join(d, REGPATH), encoding='utf-8', newline='').read()


arms = []
made = []
try:
    # ── ARM 1: SUPERSEDED WITH A LIVE SURVIVOR -- the duplicate test is SKIPPED.
    # Two records with the SAME (commit, summary) would normally be a duplicate.
    # A GENUINE duplicate -- same (commit, summary) -- where the second record is
    # retired in favour of a DIFFERENT commit that is live. The survivor is the
    # BASE commit: it resolves, it is an ancestor, and it is not the record's own
    # sha, so this exercises the 'live' path and not the self-reference path.
    d, head, dang, base = build(lambda h, g, b: [
        record(h[:12], SUBJ, 'one defect'),
        record(h[:12], SUBJ, 'one defect', superseded_by=b[:12]),
    ])
    made.append(d)
    rc, out = in_repo(d, DR.cmd_check)
    arms.append(('a LIVE survivor earns the skip: --check exits 0 on what would '
                 'otherwise be a duplicate', rc, 0))
    arms.append(('...and it SAYS it retired one rather than going quiet',
                 'SUPERSEDED (1)' in out, True))
    arms.append(('...and it does NOT report a duplicate',
                 'duplicate record' in out, False))

    # ── ARM 2: SURVIVOR MISSING -> FLAGGED, and the skip is refused.
    d, head, dang, base = build(lambda h, g, b: [
        record(h[:12], SUBJ, 'one defect'),
        record('a' * 12, SUBJ, 'one defect', superseded_by='f' * 12),
    ])
    made.append(d)
    rc, out = in_repo(d, DR.cmd_check)
    arms.append(('survivor MISSING is a FINDING, not a skip',
                 (rc, 'does not resolve' in out), (1, True)))

    # ── ARM 3: SURVIVOR RESOLVES BUT IS NOT AN ANCESTOR -> FLAGGED.
    # This is the arm a random hex string could not produce.
    d, head, dang, base = build(lambda h, g, b: [
        record(h[:12], SUBJ, 'one defect'),
        record('a' * 12, SUBJ, 'one defect', superseded_by=g[:12]),
    ])
    made.append(d)
    arms.append(('the dangling fixture really does RESOLVE (so arm 3 tests '
                 'reachability, not existence)',
                 in_repo(d, lambda: DR.resolves(dang))[0], True))
    rc, out = in_repo(d, DR.cmd_check)
    arms.append(('survivor NOT AN ANCESTOR is a FINDING, not a skip',
                 (rc, 'is NOT an ancestor' in out), (1, True)))

    # ── ARM 4: SELF-REFERENCE -> FLAGGED.
    d, head, dang, base = build(lambda h, g, b: [
        record('a' * 12, SUBJ, 'one defect', superseded_by='a' * 12),
    ])
    made.append(d)
    rc, out = in_repo(d, DR.cmd_check)
    arms.append(('SELF-REFERENCE is a FINDING',
                 (rc, 'names ITSELF' in out), (1, True)))

    # ── ARM 5: self-reference by PREFIX, not only by equality.
    d, head, dang, base = build(lambda h, g, b: [
        record(h[:12], SUBJ, 'one defect', superseded_by=h),
    ])
    made.append(d)
    rc, out = in_repo(d, DR.cmd_check)
    arms.append(('a 40-char self-reference against a 12-char commit is STILL self',
                 (rc, 'names ITSELF' in out), (1, True)))

    # ── ARM 6: --reseat NEVER re-seats a superseded record, and never counts it.
    d, head, dang, base = build(lambda h, g, b: [
        record('d' * 12, SUBJ, 'needs a reseat', superseded_by=h[:12]),
    ])
    made.append(d)
    pre = reg_text(d)
    rc, out = in_repo(d, DR.cmd_reseat)
    arms.append(('--reseat does NOT re-seat a superseded record',
                 reg_text(d) == pre, True))
    arms.append(('--reseat names it as SUPERSEDED rather than silently skipping',
                 'SUPERSEDED by' in out, True))
    arms.append(('--reseat does NOT report success over it',
                 ('re-seated 1 record(s).' in out, rc), (False, 1)))

    # ── ARM 7: the control. WITHOUT the field, the same record IS re-seated,
    # so arm 6 is measuring the field rather than a broken reseat.
    d, head, dang, base = build(lambda h, g, b: [
        record('d' * 12, SUBJ, 'needs a reseat'),
    ])
    made.append(d)
    rc, out = in_repo(d, DR.cmd_reseat)
    arms.append(('CONTROL: the SAME record WITHOUT the field IS re-seated',
                 (rc, json.loads(reg_text(d))['records'][0]['commit']),
                 (0, head[:12])))

finally:
    for d in made:
        shutil.rmtree(d, ignore_errors=True)

passed = 0
for name, got, want in arms:
    ok = got == want
    passed += ok
    print('  %-4s %s' % ('PASS' if ok else 'FAIL', name))
    if not ok:
        print('       wanted %r' % (want,))
        print('       got    %r' % (got,))
print('defect_register superseded_by probe: %d/%d arm(s) pass' % (passed, len(arms)))
sys.exit(0 if passed == len(arms) else 1)
