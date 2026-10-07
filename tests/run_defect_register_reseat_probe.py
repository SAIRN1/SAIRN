#!/usr/bin/env python
# OWNER: cc
"""Can --reseat still report SUCCESS over a register that fails --check?

    python tests/run_defect_register_reseat_probe.py

Exit 0 all arms pass, 1 an arm failed, 2 COULD NOT RUN.

THE DEFECT, MEASURED 2026-10-07 BEFORE THE FIX. `--reseat` re-seated 12 records
on a clean tree, `--check` went from 0 to "FAIL: 4 register problem(s)" -- four
DUPLICATE records -- and `--reseat` RETURNED 0. It maps a stale sha forward by
SUBJECT and never asked whether a record already existed at the destination, so
where one defect was recorded twice (before and after a rebase) both collapsed
onto one sha. A repair tool reporting success over a register its own checker
refuses is worse than a crash, because 0 is read as "fixed".

TWO GUARDS, AND THEY ARE DELIBERATELY NOT THE SAME GUARD TWICE:
  * PREVENTION -- a record whose destination (commit, summary) is already taken
    is LEFT ALONE and named. Which of two records survives is a content question
    and a pointer repair must not decide it.
  * BACKSTOP -- after writing, cmd_check() runs on what was just written. If it
    fails for ANY reason, the file is restored from a BYTE pre-image and the exit
    is 2. The backstop is what makes the prevention honest: it does not depend on
    the collision guard having thought of every shape.

EVERY ARM RUNS IN A THROWAWAY GIT REPOSITORY IT BUILDS ITSELF. Nothing in this
clone is read as a subject and nothing in it is written -- which matters more
than usual here, because the subject under test WRITES A SHARED LEDGER.

WHAT THIS PROBE CANNOT SEE, stated rather than discovered later:
  * whether a collision should be resolved by keeping the older or the newer
    record. It asserts the tool REFUSES TO CHOOSE, which is the only thing a
    pointer repair can honestly do.
  * the real 2MB register's size, performance, or cross-clone merge behaviour.
  * anything about --add. The identity rule (commit, summary) is shared between
    them, so a change on that side could reintroduce this from the other
    direction and no arm here would notice.
  * a revert that fails. The code reports that case and names
    `git checkout --`; no arm makes the filesystem refuse a write.
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

if not os.path.isfile(TOOL):
    print('COULD NOT RUN -- %s is absent. This probe is about that file and '
          'reports nothing without it.' % TOOL)
    sys.exit(2)

_argv = sys.argv
sys.argv = ['reseat_probe']
try:
    _spec = importlib.util.spec_from_file_location('dr_under_probe', TOOL)
    DR = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(DR)
finally:
    sys.argv = _argv


def git(cwd, *a):
    return subprocess.run(['git'] + list(a), cwd=cwd, capture_output=True,
                          text=True, encoding='utf-8', errors='replace')


def record(commit, subject, summary, method='code-review'):
    """A minimally valid record. The vocabulary values are ones --check accepts;
    this probe is about POINTERS, not about field validation -- except where an
    arm deliberately breaks one to make the backstop fire."""
    return {
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


REGPATH = os.path.join('docs', 'defect-density-register.json')


def build_repo(make_records):
    """A real git repo with two commits. `make_records(head)` returns the
    records, so a fixture can point at the real HEAD or at a dangling sha."""
    d = tempfile.mkdtemp(prefix='reseat-probe-')
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
    git(d, 'commit', '-q', '-m', 'fix(thing): the real subject')
    head = git(d, 'rev-parse', 'HEAD').stdout.strip()
    if len(head) != 40:
        raise RuntimeError('fixture repo has no HEAD')
    reg = {'started': '2026-09-09', 'note': 'probe fixture',
           'records': make_records(head)}
    io.open(os.path.join(d, REGPATH), 'w', encoding='utf-8', newline='').write(
        json.dumps(reg, indent=2) + NL)
    return d, head


def run_reseat(d):
    """Drive the REAL cmd_reseat against the throwaway repo, capturing stdout.

    `reseat_base()` measures reachability against a ref; in a fresh repo with no
    remote it falls back to a local one, and the fixture's HEAD is reachable from
    whatever it picks. If it cannot pick one the command returns 2 and the arm
    below reports that as a COULD-NOT-RUN rather than a pass.
    """
    old_repo, old_out = DR.REPO, sys.stdout
    sink = io.StringIO()
    try:
        DR.REPO = d
        sys.stdout = sink
        rc = DR.cmd_reseat()
    except Exception as e:                                       # noqa: BLE001
        rc = 'RAISED %s: %s' % (type(e).__name__, e)
    finally:
        DR.REPO, sys.stdout = old_repo, old_out
    return rc, sink.getvalue()


def reg_text(d):
    return io.open(os.path.join(d, REGPATH), encoding='utf-8', newline='').read()


SUBJ = 'fix(thing): the real subject'
arms = []
made = []
try:
    # ── ARM 1: a SAFE re-seat is applied, verified, and exits 0 ──────────────
    d, head = build_repo(lambda h: [record('d' * 12, SUBJ, 'only record')])
    made.append(d)
    rc, out = run_reseat(d)
    if rc == 2 and 'COULD NOT RE-SEAT' in out:
        print('COULD NOT RUN -- the fixture repo gave reseat_base() no ref to '
              'measure against, so no arm can mean anything:')
        print(out.rstrip())
        sys.exit(2)
    on_disk = json.loads(reg_text(d))['records'][0]['commit']
    arms.append(('a safe re-seat is APPLIED and written',
                 (rc, on_disk), (0, head[:12])))
    arms.append(('and it says it verified the register AFTER writing',
                 'verified after writing' in out, True))

    # ── ARM 2: THE REAL DEFECT -- two records, one subject, a COLLISION ──────
    d, head = build_repo(lambda h: [
        record(h[:12], SUBJ, 'one defect'),
        record('e' * 12, SUBJ, 'one defect'),
    ])
    made.append(d)
    pre = reg_text(d)
    rc, out = run_reseat(d)
    arms.append(('a destination COLLISION is named rather than written',
                 'COLLIDES' in out, True))
    arms.append(('a run that only collided does NOT exit 0 -- a partial repair '
                 'is not a success', rc, 1))
    arms.append(('the colliding record is NOT rewritten on disk',
                 reg_text(d) == pre, True))
    arms.append(('the tool says WHY it refuses -- which record survives is a '
                 'content question', 'content question' in out, True))

    # ── ARM 3: THE BACKSTOP, driven by a failure the collision guard cannot
    # see. One record needs a re-seat; a SECOND carries an invalid
    # detection_method, so --check fails after the write for a reason that has
    # nothing to do with duplicates. The write must be REVERTED and the exit
    # must be 2 -- never 0. This is the arm that makes the first guard honest.
    d, head = build_repo(lambda h: [
        record('d' * 12, SUBJ, 'needs a reseat'),
        record(h[:12], SUBJ, 'invalid method', method='not-a-real-method'),
    ])
    made.append(d)
    pre = reg_text(d)
    rc, out = run_reseat(d)
    arms.append(('BACKSTOP: a post-write --check failure REVERTS the write',
                 ('REVERTED' in out, rc), (True, 2)))
    arms.append(('BACKSTOP: the register on disk is byte-identical to before',
                 reg_text(d) == pre, True))
    arms.append(('BACKSTOP: the revert is CONFIRMED in the output, not assumed',
                 'byte-identical to what it was: CONFIRMED' in out, True))
    arms.append(('BACKSTOP: what --check objected to is re-printed as the '
                 'evidence', 'not-a-real-method' in out, True))
    arms.append(('BACKSTOP: and it never prints a success line',
                 're-seated 1 record(s).' in out, False))

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
print('defect_register --reseat probe: %d/%d arm(s) pass' % (passed, len(arms)))
sys.exit(0 if passed == len(arms) else 1)
