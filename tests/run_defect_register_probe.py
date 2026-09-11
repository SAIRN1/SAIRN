"""Control for tools/defect_register.py.

    python tests/run_defect_register_probe.py

The register's only value is that its records are true. A register that accepts
a commit that does not exist, a made-up detection method, or the same defect
twice is worse than none: its LENGTH reads as evidence of thoroughness.

So the arms below attack it rather than exercise it -- and the report's own
caveats are asserted too, because a density figure quoted without them is the
failure this platform keeps recording. A number nobody qualifies gets quoted.

RUNS IN A THROWAWAY WORKTREE. It never writes this clone's register.
"""
import io
import json
import os
import subprocess
import sys
import tempfile

REPO = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True).stdout.strip()
TOOL = 'tools/defect_register.py'
REG = 'docs/defect-density-register.json'
R = {}


def check(label, actual, expected):
    R[label] = (actual == expected, actual, expected)


def git(cwd, *a):
    return subprocess.run(['git'] + list(a), cwd=cwd, capture_output=True, text=True)


def run(wt, *args):
    p = subprocess.run([sys.executable, TOOL] + list(args), cwd=wt,
                       capture_output=True, text=True, timeout=300)
    return p.returncode, (p.stdout or '') + (p.stderr or '')


TREE_BEFORE = git(REPO, 'status', '--porcelain').stdout
wt = os.path.join(tempfile.gettempdir(), 'defreg-probe-%d' % os.getpid())
add = git(REPO, 'worktree', 'add', '-q', '--detach', wt, 'HEAD')
check('A0 the throwaway worktree was created', add.returncode, 0)
try:
    # The worktree is at HEAD, which may not carry the tool or the register.
    for rel in (TOOL, REG):
        src = os.path.join(REPO, rel.replace('/', os.sep))
        if os.path.isfile(src):
            dst = os.path.join(wt, rel.replace('/', os.sep))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            io.open(dst, 'wb').write(io.open(src, 'rb').read())

    real = git(wt, 'rev-parse', 'HEAD').stdout.strip()[:12]

    # ── A. it reports and it validates ─────────────────────────────────────
    rc, out = run(wt, '--report')
    check('A1 --report runs', rc, 0)
    rc, out = run(wt, '--check')
    check('A2 --check passes on the committed register', rc, 0)

    # ── B. IT REFUSES WHAT IT CANNOT VERIFY ────────────────────────────────
    rc, out = run(wt, '--add', '--commit', 'deadbeefdead', '--app', 'x',
                  '--layer', 'product', '--severity', 'high',
                  '--method', 'code-review', '--summary', 'nope')
    check('B1 a commit that does not exist is REFUSED', rc, 2)
    check('B2 and it says so', 'no such commit' in out, True)

    rc, out = run(wt, '--add', '--commit', real, '--app', 'x',
                  '--layer', 'product', '--severity', 'high',
                  '--method', 'vibes', '--summary', 'nope')
    check('B3 an invented detection method is REFUSED', rc, 2)
    check('B4 because the matrix is meaningless with free text',
          '--method must be one of' in out, True)

    rc, out = run(wt, '--add', '--commit', real, '--app', 'x',
                  '--layer', 'guesswork', '--severity', 'high',
                  '--method', 'code-review', '--summary', 'nope')
    check('B5 an invented layer is REFUSED', rc, 2)

    # ── C. it derives rather than trusting what it was told ────────────────
    rc, out = run(wt, '--add', '--commit', real, '--app', 'stonedesk',
                  '--layer', 'test', '--severity', 'low',
                  '--method', 'probe-control', '--summary', 'a probe fixture')
    check('C1 a real commit is accepted', rc, 0)
    doc = json.load(io.open(os.path.join(wt, REG.replace('/', os.sep)),
                            encoding='utf-8'))
    rec = [r for r in doc['records'] if r['summary'] == 'a probe fixture'][0]
    check('C2 the date is DERIVED, not supplied', len(rec['date']), 10)
    check('C3 the files are DERIVED', isinstance(rec['files'], list), True)
    check('C4 and so are the line counts',
          isinstance(rec['lines_added'], int) and isinstance(rec['lines_removed'], int),
          True)

    # ── D. the same defect cannot be counted twice ─────────────────────────
    before = len(json.load(io.open(os.path.join(wt, REG.replace('/', os.sep)),
                                   encoding='utf-8'))['records'])
    rc, out = run(wt, '--add', '--commit', real, '--app', 'stonedesk',
                  '--layer', 'test', '--severity', 'low',
                  '--method', 'probe-control', '--summary', 'a probe fixture')
    after = len(json.load(io.open(os.path.join(wt, REG.replace('/', os.sep)),
                                  encoding='utf-8'))['records'])
    check('D1 a duplicate is not appended', after, before)
    check('D2 and it says so', 'already registered' in out, True)

    # ...but the SAME COMMIT with a DIFFERENT defect is a different record.
    # 5b98fd27 fixed three distinct faults in one commit, and collapsing them
    # would undercount by two.
    rc, out = run(wt, '--add', '--commit', real, '--app', 'stonedesk',
                  '--layer', 'test', '--severity', 'low',
                  '--method', 'probe-control', '--summary', 'a SECOND fixture')
    after2 = len(json.load(io.open(os.path.join(wt, REG.replace('/', os.sep)),
                                   encoding='utf-8'))['records'])
    check('D3 one commit CAN carry several distinct defects', after2, before + 1)

    # ── E. --check catches a register that has stopped being true ──────────
    # A RECORD POINTING AT NOTHING IS BOTH HALVES GONE (2026-09-11). This arm
    # used to plant `commit='000000000000'` while copying records[0], which
    # carried records[0]'s SUBJECT -- so the planted record still named a real
    # commit and only its hash was wrong. That is the REBASE case, not the
    # points-at-nothing case, and the two now behave differently on purpose.
    # The subject is blanked here so the record really resolves to nothing.
    p = os.path.join(wt, REG.replace('/', os.sep))
    doc = json.load(io.open(p, encoding='utf-8'))
    doc['records'].append(dict(doc['records'][0], commit='000000000000',
                               subject='no commit on this platform says this'))
    io.open(p, 'w', encoding='utf-8', newline='').write(json.dumps(doc, indent=2))
    rc, out = run(wt, '--check')
    check('E1 a record pointing at no commit FAILS --check', rc, 1)
    check('E2 and names it', '000000000000' in out, True)
    check('E3 and says both halves are gone, not just the hash',
          'neither the commit nor its subject' in out, True)

    # ── E4-E8. A REBASED SHA IS NOT A RECORD POINTING AT NOTHING ───────────
    # The register sat permanently red because `--add` derives the SHA from the
    # commit in front of it and four clones rebase before they reach origin, so
    # the recorded hash never existed on `main`. Every post-push report-only
    # sweep carried a finding, which is how a checker gets switched off.
    doc = json.load(io.open(p, encoding='utf-8'))
    doc['records'] = [r for r in doc['records'] if r['commit'] != '000000000000']
    real_subject = doc['records'][0]['subject']
    doc['records'][0]['commit'] = 'aaaaaaaaaaaa'      # a rebase moved it
    io.open(p, 'w', encoding='utf-8', newline='').write(json.dumps(doc, indent=2))
    rc, out = run(wt, '--check')
    check('E4 a SHA a rebase moved does NOT fail --check', rc, 0)
    check('E5 it is reported rather than swallowed', 'RE-SEATABLE' in out, True)
    check('E6 and the old and new hashes are both named',
          'aaaaaaaaaaaa ->' in out, True)

    # AMBIGUITY IS A FAILURE, NOT A GUESS. Two records cannot disambiguate a
    # subject that matches two commits, and picking one is the thing a register
    # must never do.
    # THE AMBIGUITY IS MANUFACTURED RATHER THAN HOPED FOR. The first version of
    # this arm planted a subject that happened to exist and SKIPPED itself when
    # it turned out to be unique -- a skipped arm is an untested branch wearing
    # a green tick. Two empty commits with the same subject are made HERE, in
    # the detached throwaway worktree, so the fixture is guaranteed and nothing
    # is committed on any branch of this clone.
    DUP = 'PROBE ambiguous-subject fixture -- not a real commit'
    for _ in range(2):
        git(wt, '-c', 'user.name=probe', '-c', 'user.email=probe@local',
            'commit', '--allow-empty', '-q', '-m', DUP)
    n_same = git(wt, 'log', '--format=%s', 'HEAD').stdout.count(DUP)
    doc2 = json.load(io.open(p, encoding='utf-8'))
    doc2['records'][0]['subject'] = DUP
    io.open(p, 'w', encoding='utf-8', newline='').write(json.dumps(doc2, indent=2))
    rc, amb = run(wt, '--check')
    check('E7a the fixture really is ambiguous -- two commits, one subject',
          n_same, 2)
    check('E7 an ambiguous subject FAILS rather than picking one', rc, 1)
    check('E8 and says why', 'more than one commit' in amb, True)

    # ── E9-E11. --reseat writes them back, and does not reorder the file ────
    io.open(p, 'w', encoding='utf-8', newline='').write(json.dumps(doc, indent=2))
    order_before = [r['summary'] for r in
                    json.load(io.open(p, encoding='utf-8'))['records']]
    rc, out = run(wt, '--reseat')
    check('E9 --reseat succeeds', rc, 0)
    after_doc = json.load(io.open(p, encoding='utf-8'))
    check('E10 the moved SHA was rewritten',
          [r for r in after_doc['records'] if r['commit'] == 'aaaaaaaaaaaa'], [])
    check('E11 and the file was NOT reordered -- a 12-line repair must not '
          'produce a 157-line diff',
          [r['summary'] for r in after_doc['records']], order_before)
    check('E12 the rewritten record still names the same commit subject',
          after_doc['records'][0]['subject'], real_subject)
    rc, out = run(wt, '--check')
    check('E13 and --check is clean afterwards, with nothing re-seatable',
          rc == 0 and 'RE-SEATABLE' not in out, True)

    # ── E14. THE VOCABULARY CHECKS RUN EVEN ON A RECORD WHOSE SHA IS STALE ──
    # They used to sit after a `continue`, so a stale SHA silently stopped the
    # rest of that record from being checked at all.
    doc3 = json.load(io.open(p, encoding='utf-8'))
    doc3['records'][0]['commit'] = 'aaaaaaaaaaaa'
    doc3['records'][0]['detection_method'] = 'vibes'
    io.open(p, 'w', encoding='utf-8', newline='').write(json.dumps(doc3, indent=2))
    rc, out = run(wt, '--check')
    check('E14 a bad field is still caught on a record with a moved SHA',
          rc == 1 and 'unknown detection method' in out, True)
    # Put the register back so section F reads a sane file.
    io.open(p, 'w', encoding='utf-8', newline='').write(json.dumps(after_doc, indent=2))

    # ── F. THE REPORT REFUSES TO BE QUOTED BARE ────────────────────────────
    rc, out = run(wt, '--report')
    check('F1 the density is printed against a MEASURED denominator',
          'MEASURED denominator' in out, True)
    check('F2 an app with no records is called unswept, not clean',
          'not a clean one' in out, True)
    check('F3 and the honest signal is stated as consecutive zero-finding '
          'sweeps by DIFFERENT methods',
          'DIFFERENT METHODS' in out, True)
    check('F4 the denominator states what it does NOT count',
          'It does not count' in out, True)
    check('F5 and the coverage matrix is printed beside the number',
          'COVERAGE -- which methods' in out, True)
finally:
    git(REPO, 'worktree', 'remove', '--force', wt)
    git(REPO, 'worktree', 'prune')

check('Z1 the worktree was cleaned up', os.path.exists(wt), False)
check('Z2 and this clone is exactly as it was',
      git(REPO, 'status', '--porcelain').stdout, TREE_BEFORE)

for k in sorted(R):
    ok, actual, expected = R[k]
    print('  %-6s %s' % ('ok' if ok else 'FAIL', k))
    if not ok:
        print('         expected %r, got %r' % (expected, actual))
bad = [k for k in R if not R[k][0]]
print()
print('defect-register: %d checks, %d failed' % (len(R), len(bad)))
sys.exit(1 if bad else 0)
