"""Control for tools/defect_register.py's APP VOCABULARY and EXTERNAL citations.

    python tests/run_defect_register_vocab_probe.py

Exit 0  every refusal fires and the one accepted shape is stored intact
Exit 1  one did not

── WHY THIS IS A SECOND FILE AND NOT MORE ARMS IN run_defect_register_probe.py
Those arms were written there first and moved out, MEASURED rather than felt:
that probe takes 279 seconds on this machine. A negative control has to run
the suite once per mutation plus a baseline plus a restore, so controlling
these five refusals through it would cost over half an hour -- and a control
nobody will sit through is a control that gets skipped, which is the failure
this platform names in its own words about report-only checkers. This file
drives only the new behaviour, in one worktree, in seconds.

── WHAT IS BEING GUARDED ───────────────────────────────────────────────────
TWO CHANGES, both 2026-09-22, both about a field that was free text.

(1) `--app` DRIFTED FIVE TIMES ON ONE VALUE. 'platform' against 'PLATFORM',
    normalised by hand on 2026-09-14, again on 2026-09-22, and two more
    lower-case records landed within the hour of that second fix. The
    one-entity-one-spelling check under `--check` is a DETECTOR: it fires only
    once BOTH spellings are in the file, so it reports damage already done, to
    whoever rebases through it next rather than to whoever caused it. The
    vocabulary is now DERIVED from `git ls-files '*.html'` plus two non-file
    entities, so it cannot drift from the per-app denominator it shares.

(2) A COMMIT IN A REPOSITORY THIS ONE CANNOT SEE had no way into the file.
    hover2's finding: the hover auditor's tooling lives outside every clone BY
    DESIGN -- that separation is what makes its audits independent -- and
    `--add` requires `--commit` while `--check` requires every commit to
    resolve. A defect found and fixed there could not be recorded, so the
    register's hover coverage was understated by however many such fixes exist
    and nothing in the file said so.

THE COST OF (2) IS THAT THE POINTER CANNOT BE CHECKED, and the arms below
insist that cost is paid out loud: the note has a length floor, the line
counts are stored as ZERO rather than guessed, the record may only be filed
against an entity that already has no line denominator, `--check` counts them
SEPARATELY from "every commit resolves", and `--reseat` never touches one.

RUNS IN A THROWAWAY WORKTREE. It never writes this clone's register.
"""
CONTROLS_FOR = ['defect_register.py']

import io
import json
import os
import subprocess
import sys
import tempfile

REPO = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True, encoding='utf-8',
                      errors='replace').stdout.strip()
TOOL = 'tools/defect_register.py'
REG = 'docs/defect-density-register.json'
R = {}


def check(label, actual, expected):
    R[label] = (actual == expected, actual, expected)


def git(cwd, *a):
    return subprocess.run(['git'] + list(a), cwd=cwd, capture_output=True,
                          text=True, encoding='utf-8', errors='replace')


def run(wt, *args):
    p = subprocess.run([sys.executable, TOOL] + list(args), cwd=wt,
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace', timeout=300)
    return p.returncode, (p.stdout or '') + (p.stderr or '')


TREE_BEFORE = git(REPO, 'status', '--porcelain').stdout
wt = os.path.join(tempfile.gettempdir(), 'defreg-vocab-%d' % os.getpid())
add = git(REPO, 'worktree', 'add', '-q', '--detach', wt, 'HEAD')
check('A0 the throwaway worktree was created', add.returncode, 0)
try:
    # The worktree is at HEAD; the tool and the register under test may not be
    # committed yet, so they are copied in from this clone.
    for rel in (TOOL, REG):
        src = os.path.join(REPO, rel.replace('/', os.sep))
        if os.path.isfile(src):
            dst = os.path.join(wt, rel.replace('/', os.sep))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            io.open(dst, 'wb').write(io.open(src, 'rb').read())

    # A commit that really changed code, chosen deterministically rather than
    # `rev-parse HEAD` -- which reads as "a real commit" and means "whatever
    # landed last", and would hit the bookkeeping-only refusal at random.
    real = git(wt, 'log', '-1', '--format=%H', '--', 'api/', 'tools/'
               ).stdout.strip()[:12]
    check('A0b the probe found a commit that really changed code', len(real), 12)
    rc, out = run(wt, '--check')
    check('A1 the register under test starts clean, so every arm below is '
          'about a mutation rather than about a pre-existing failure', rc, 0)

    # ── BA. THE APP VOCABULARY (2026-09-22) ────────────────────────────────
    # `--app` was free text and drifted five times on ONE value -- 'platform'
    # vs 'PLATFORM' -- each correction a session stopping to normalise somebody
    # else's typo mid-rebase. The one-entity-one-spelling check under --check
    # fires only once BOTH spellings are in the file, so it detects damage
    # already done, to whoever rebases next.
    #
    # THE ARMS ABOVE USED `--app x` UNTIL THIS CHANGE, and that is worth
    # recording rather than quietly fixing: B1/B3/B5 assert rc==2, so with a
    # strict enum they would have gone on passing while testing the APP
    # refusal instead of the commit, method and layer refusals they are named
    # for -- green arms measuring the wrong thing. They now pass a real app.
    common = ('--layer', 'tooling', '--severity', 'low', '--method',
              'code-review', '--rule', 'not-citable', '--rule-note',
              'probe fixture, no standing rule is being tested here',
              '--phase', 'coding', '--injection-unknown', 'probe fixture',
              '--factors-unknown', 'probe fixture')
    rc, out = run(wt, '--add', '--commit', real, '--app', 'platform',
                  '--summary', 'nope', *common)
    check('BA1 a lower-case app is REFUSED', rc, 2)
    check('BA2 and the refusal names the spelling it wanted',
          "Did you mean 'PLATFORM'" in out, True)
    check('BA3 and prints the derived vocabulary rather than a hardcoded list',
          "git ls-files '*.html'" in out, True)
    rc, out = run(wt, '--add', '--commit', real, '--app', 'sairnmade-up',
                  '--summary', 'nope', *common)
    check('BA4 an app with no file at all is REFUSED', rc, 2)
    check('BA5 ...with no misleading did-you-mean, because there is no near '
          'match', 'Did you mean' in out, False)

    # ── BB. AN EXTERNAL CITATION (2026-09-22, hover2's finding) ────────────
    # The hover auditor's tooling lives outside every clone BY DESIGN, so a
    # defect fixed there had no way into this file: --add requires --commit
    # and --check requires every commit to resolve. The register's hover
    # coverage was understated by however many such fixes exist and nothing
    # in the file said so.
    NOTE = ('the hover auditor keeps its tooling outside every clone by '
            'design; this commit is in that repository and cannot be '
            'rev-parsed from here')
    rc, out = run(wt, '--add', '--commit', 'external:hover2-audit-log:a1b2c3d4e5f6',
                  '--app', 'PLATFORM', '--summary', 'external probe fixture', *common)
    check('BB1 an external citation with no supporting fields is REFUSED', rc, 2)
    check('BB2 and names all three that are missing',
          all(f in out for f in ('--external-note', '--external-date',
                                 '--external-subject')), True)

    rc, out = run(wt, '--add', '--commit', 'external:hover2-audit-log:a1b2c3d4e5f6',
                  '--app', 'PLATFORM', '--summary', 'external probe fixture',
                  '--external-note', 'too short', '--external-date', '2026-09-22',
                  '--external-subject', 'fix: something', *common)
    check('BB3 a token note is REFUSED -- an unverifiable pointer is only as '
          'good as the sentence telling a reader where to look', rc, 2)

    rc, out = run(wt, '--add', '--commit', 'external:hover2-audit-log:a1b2c3d4e5f6',
                  '--app', 'stonedesk', '--summary', 'external probe fixture',
                  '--external-note', NOTE, '--external-date', '2026-09-22',
                  '--external-subject', 'fix: something', *common)
    check('BB4 an external citation against a real app file is REFUSED, '
          'because a per-app rate would gain a numerator with no denominator',
          rc, 2)

    rc, out = run(wt, '--add', '--commit', 'external:hover2-audit-log:BADSHA',
                  '--app', 'PLATFORM', '--summary', 'external probe fixture',
                  '--external-note', NOTE, '--external-date', '2026-09-22',
                  '--external-subject', 'fix: something', *common)
    check('BB5 a malformed external sha is REFUSED', rc, 2)
    check('BB6 and the refusal teaches the format rather than saying no such '
          'commit and stopping', 'external:<repo-label>:<sha>' in out, True)

    rc, out = run(wt, '--add', '--commit', 'external:hover2-audit-log:a1b2c3d4e5f6',
                  '--app', 'PLATFORM', '--summary', 'external probe fixture',
                  '--external-note', NOTE, '--external-date', 'yesterday',
                  '--external-subject', 'fix: something', *common)
    check('BB7 a free-text external date is REFUSED -- it feeds the lag figure '
          'like any other date', rc, 2)

    rc, out = run(wt, '--add', '--commit', 'external:hover2-audit-log:a1b2c3d4e5f6',
                  '--app', 'PLATFORM', '--summary', 'external probe fixture',
                  '--external-note', NOTE, '--external-date', '2026-09-22',
                  '--external-subject', 'fix: the real subject in that repo', *common)
    check('BB8 a complete external citation is ACCEPTED', rc, 0)
    doc = json.load(io.open(os.path.join(wt, REG.replace('/', os.sep)), encoding='utf-8'))
    xr = [r for r in doc['records'] if r['summary'] == 'external probe fixture']
    check('BB9 exactly one record was written', len(xr), 1)
    if xr:
        xr = xr[0]
        check('BB10 the line counts are ZERO, not guessed at -- a fabricated '
              'count would deflate a rate with a number nobody measured',
              (xr['lines_added'], xr['lines_removed']), (0, 0))
        check('BB11 and the file list is EMPTY for the same reason',
              xr['files'], [])
        check('BB12 the repo label and sha are split out so a reader can go '
              'and look', (xr['external']['repo'], xr['external']['sha']),
              ('hover2-audit-log', 'a1b2c3d4e5f6'))
        check('BB13 the subject is the one supplied, not invented',
              xr['subject'], 'fix: the real subject in that repo')

    rc, out = run(wt, '--check')
    check('BB14 --check PASSES with an external citation in the file', rc, 0)
    # NOT A HARDCODED COUNT. This read `external citations: 1`, which was true
    # the day it was written and stopped being true the moment a real external
    # record landed in the register the probe copies in -- the count went to 2
    # and the arm failed against a tool doing exactly the right thing. A
    # number in an assertion that tracks live data is a staleness bomb; the
    # question was always whether THIS citation is listed separately.
    check('BB15 ...and counts it SEPARATELY rather than folding it into '
          '"every commit resolves"',
          'external citations:' in out
          and 'external:hover2-audit-log:a1b2c3d4e5f6' in out, True)
    check('BB16 ...saying plainly that it was not verified',
          'NOT verified' in out, True)

    # A RE-SEAT MUST NEVER TOUCH IT. There is no ref to measure it against, and
    # the subject fallback would hunt for it among THIS repo's commits -- where
    # a coincidental match would rewrite a pointer to another repository into a
    # pointer to a local commit.
    rc, out = run(wt, '--reseat')
    doc = json.load(io.open(os.path.join(wt, REG.replace('/', os.sep)), encoding='utf-8'))
    still = [r for r in doc['records'] if r['summary'] == 'external probe fixture']
    check('BB17 --reseat leaves the external citation exactly as it was',
          still[0]['commit'] if still else None,
          'external:hover2-audit-log:a1b2c3d4e5f6')


    # ── BC. THE FILE ROUTE (2026-09-23, tool-bugs item 5) ──────────────────
    # --add had no file route, so a summary typed at a shell lost three
    # backtick spans to command substitution and landed reading "folds of the
    # shape , seven of them money". The words deleted were the CODE SHAPES,
    # which is the specific damage: a summary about a coercion bug with the
    # coercion terms removed still reads as English and means nothing.
    #
    # A SINGLE --body-file WOULD HAVE CLOSED ONE FIELD OF EIGHT. --add takes
    # summary, rule-note, recurrence-open, injection-unknown, phase-note,
    # single-factor-note, limits and the JSON of --factors. So the route is a
    # CONVENTION at the argument reader -- any --x may be given as --x-file --
    # and these arms hold that convention rather than a list of flags.
    HOSTILE = (
        "The guard is `senServerWinsMerge` and the fold is `s + (x || 0)`." + chr(10) +
        "Cost: $(git rev-parse HEAD) must stay literal, and so must ${HOME}." + chr(10) +
        "$USER expands to EMPTY in a shell -- the shape that leaves no trace." + chr(10) +
        "Nested: $(echo `echo inner`), a backslash \\ and a quote \" here."
    )
    bf = os.path.join(wt, 'bodyfile.txt')
    io.open(bf, 'w', encoding='utf-8', newline='').write(HOSTILE)

    common = ('--layer', 'tooling', '--severity', 'low', '--method',
              'code-review', '--rule', 'not-citable', '--rule-note',
              'probe fixture, no standing rule is being tested here',
              '--phase', 'coding', '--injection-unknown', 'probe fixture',
              '--factors-unknown', 'probe fixture')

    rc, out = run(wt, '--add', '--commit', real, '--app', 'PLATFORM',
                  '--summary-file', bf, *common)
    check('BC1 a summary given as --summary-file is ACCEPTED', rc, 0)
    doc = json.load(io.open(os.path.join(wt, REG.replace('/', os.sep)), encoding='utf-8'))
    hit = [r for r in doc['records'] if r.get('summary', '').startswith('The guard is')]
    check('BC2 exactly one record was written', len(hit), 1)
    if hit:
        got = hit[0]['summary']
        check('BC3 it is byte-for-byte what the file held -- no shell ever '
              'saw it', got, HOSTILE.strip())
        for shape in ('`senServerWinsMerge`', '`s + (x || 0)`',
                      '$(git rev-parse HEAD)', '${HOME}', '$USER',
                      '$(echo `echo inner`)'):
            check('BC4 survives literally: %s' % shape, shape in got, True)

    # EVERY FIELD, NOT ONE. --factors is JSON and --recurrence-open is prose;
    # both go through the same reader, which is the whole point of doing it at
    # the argument layer rather than adding one flag.
    fj = os.path.join(wt, 'factors.json')
    io.open(fj, 'w', encoding='utf-8', newline='').write(
        '[{"factor": "a factor holding `backticks` and $(substitution)",'
        ' "kind": "technical", "action_status": "done",'
        ' "action": "proved by reading it back"}]')
    ro = os.path.join(wt, 'recurrence.txt')
    io.open(ro, 'w', encoding='utf-8', newline='').write(
        'the recurrence keeps `its backticks` and $(this) too')
    real2 = git(wt, 'log', '-2', '--format=%H', '--', 'api/', 'tools/'
                ).stdout.strip().split(chr(10))[-1][:12]
    rc, out = run(wt, '--add', '--commit', real2, '--app', 'PLATFORM',
                  '--summary', 'a second probe fixture for the file route',
                  '--layer', 'tooling', '--severity', 'low', '--method',
                  'code-review', '--rule', 'not-citable', '--rule-note',
                  'probe fixture', '--phase', 'coding',
                  '--injection-unknown', 'probe fixture',
                  '--factors-file', fj, '--recurrence-open-file', ro,
                  # ONE factor needs a stated reason, which is the register's
                  # own rule and nothing to do with the file route -- the
                  # first version of this arm omitted it and failed for a
                  # reason the arm is not about.
                  '--single-factor-note',
                  'probe fixture: one factor is enough to prove the JSON '
                  'came through a file rather than a shell')
    check('BC5 --factors-file and --recurrence-open-file are accepted too', rc, 0)
    doc = json.load(io.open(os.path.join(wt, REG.replace('/', os.sep)), encoding='utf-8'))
    hit = [r for r in doc['records']
           if r.get('summary') == 'a second probe fixture for the file route']
    if hit:
        check('BC6 the factor JSON was parsed, not stored as text',
              hit[0]['contributing_factors'][0]['factor'].startswith('a factor holding `back'), True)
        check('BC7 and the recurrence kept its backticks',
              '`its backticks`' in (hit[0].get('recurrence_open') or ''), True)

    # THE REFUSALS. An absent value is not an empty one, and a register that
    # stored the difference as "" would be recording a field nobody wrote.
    rc, out = run(wt, '--add', '--commit', real, '--app', 'PLATFORM',
                  '--summary-file', os.path.join(wt, 'no-such-file.txt'), *common)
    check('BC8 a --x-file that does not exist is REFUSED', rc, 2)
    check('BC9 and says an absent value is not an empty one',
          'absent value is not an empty one' in out, True)

    empty = os.path.join(wt, 'empty.txt')
    io.open(empty, 'w', encoding='utf-8').write('   ' + chr(10))
    rc, out = run(wt, '--add', '--commit', real, '--app', 'PLATFORM',
                  '--summary-file', empty, *common)
    check('BC10 an empty --x-file is REFUSED', rc, 2)

    latin = os.path.join(wt, 'latin.txt')
    io.open(latin, 'wb').write(u'a summary about r\xe9sum\xe9 handling'.encode('latin-1'))
    rc, out = run(wt, '--add', '--commit', real, '--app', 'PLATFORM',
                  '--summary-file', latin, *common)
    check('BC11 a --x-file that is not UTF-8 is REFUSED rather than decoded '
          'lossily', rc, 2)

    rc, out = run(wt, '--add', '--commit', real, '--app', 'PLATFORM',
                  '--summary', 'inline', '--summary-file', bf, *common)
    check('BC12 BOTH --x and --x-file is REFUSED rather than one silently '
          'winning -- two values for one field means one of them was meant '
          'and this cannot know which', rc, 2)
    check('BC13 and the refusal names both forms',
          '--summary and --summary-file' in out, True)

    rc, out = run(wt, '--add', '--commit', real, '--app', 'PLATFORM', *common)
    check('BC14 a missing required field advertises the file route',
          '--summary-file <path>' in out, True)

finally:
    git(REPO, 'worktree', 'remove', '--force', wt)
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
print('defect-register vocab/external: %d checks, %d failed' % (len(R), len(bad)))
sys.exit(1 if bad else 0)
