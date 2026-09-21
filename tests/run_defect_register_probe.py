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
# Declares, for tools/checker_control_check.py, which checker(s) this file is
# the control for. Attribution is DECLARED rather than inferred because three
# inference models were each wrong within an hour of being written.
CONTROLS_FOR = ['defect_register.py']

import io
import json
import os
import re
import subprocess
import sys
import tempfile

REPO = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True, encoding='utf-8', errors='replace').stdout.strip()
TOOL = 'tools/defect_register.py'
REG = 'docs/defect-density-register.json'
R = {}


def check(label, actual, expected):
    R[label] = (actual == expected, actual, expected)


def git(cwd, *a):
    return subprocess.run(['git'] + list(a), cwd=cwd, capture_output=True, text=True, encoding='utf-8', errors='replace')


def run(wt, *args):
    p = subprocess.run([sys.executable, TOOL] + list(args), cwd=wt,
                       capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=300)
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

    # A COMMIT THAT ACTUALLY CHANGED CODE, chosen deterministically.
    #
    # THIS LINE USED TO BE `git rev-parse HEAD`, AND THAT IS THE EXACT TRAP the
    # G-arms below now guard against: it reads as "a real commit" and means
    # "whatever landed last". On 2026-09-16 that was a register-only commit, so
    # the new guard REFUSED it and this arm failed -- the probe had been written
    # with the same reflex it exists to police, and passed only because HEAD had
    # always happened to touch code.
    #
    # `-- api/ tools/` makes the answer a fact about the repository rather than
    # about the minute the probe runs.
    real = git(wt, 'log', '-1', '--format=%H', '--', 'api/', 'tools/'
               ).stdout.strip()[:12]
    check('A0b the probe found a commit that really changed code, so every arm '
          'below is not passing on the trap it guards', len(real), 12)

    # ── A. it reports and it validates ─────────────────────────────────────
    rc, out = run(wt, '--report')
    check('A1 --report runs', rc, 0)
    rc, out = run(wt, '--check')
    check('A2 --check passes on the committed register', rc, 0)

    # ── B. IT REFUSES WHAT IT CANNOT VERIFY ────────────────────────────────
    rc, out = run(wt, '--add', '--commit', 'deadbeefdead', '--app', 'x',
                  '--layer', 'product', '--severity', 'high',
                  '--method', 'code-review', '--summary', 'nope',
                  '--rule', '1.1', '--phase', 'coding', '--injection-unknown', 'probe fixture',
                  '--factors-unknown', 'probe fixture -- item 75 makes --factors or an explicit unknown-reason required at --add; this probe is about other fields')
    check('B1 a commit that does not exist is REFUSED', rc, 2)
    check('B2 and it says so', 'no such commit' in out, True)

    rc, out = run(wt, '--add', '--commit', real, '--app', 'x',
                  '--layer', 'product', '--severity', 'high',
                  '--method', 'vibes', '--summary', 'nope', '--rule', '1.1', '--phase', 'coding', '--injection-unknown', 'probe fixture',
                  '--factors-unknown', 'probe fixture -- item 75 makes --factors or an explicit unknown-reason required at --add; this probe is about other fields')
    check('B3 an invented detection method is REFUSED', rc, 2)
    check('B4 because the matrix is meaningless with free text',
          '--method must be one of' in out, True)

    rc, out = run(wt, '--add', '--commit', real, '--app', 'x',
                  '--layer', 'guesswork', '--severity', 'high',
                  '--method', 'code-review', '--summary', 'nope',
                  '--rule', '1.1', '--phase', 'coding', '--injection-unknown', 'probe fixture',
                  '--factors-unknown', 'probe fixture -- item 75 makes --factors or an explicit unknown-reason required at --add; this probe is about other fields')
    check('B5 an invented layer is REFUSED', rc, 2)

    # ── C. it derives rather than trusting what it was told ────────────────
    rc, out = run(wt, '--add', '--commit', real, '--app', 'stonedesk',
                  '--layer', 'test', '--severity', 'low',
                  '--method', 'probe-control', '--found-by-tool', 'unknown', '--summary', 'a probe fixture',
                  '--rule', '1.1', '--phase', 'coding', '--injection-unknown', 'probe fixture',
                  '--factors-unknown', 'probe fixture -- item 75 makes --factors or an explicit unknown-reason required at --add; this probe is about other fields')
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
                  '--method', 'probe-control', '--found-by-tool', 'unknown', '--summary', 'a probe fixture',
                  '--rule', '1.1', '--phase', 'coding', '--injection-unknown', 'probe fixture',
                  '--factors-unknown', 'probe fixture -- item 75 makes --factors or an explicit unknown-reason required at --add; this probe is about other fields')
    after = len(json.load(io.open(os.path.join(wt, REG.replace('/', os.sep)),
                                  encoding='utf-8'))['records'])
    check('D1 a duplicate is not appended', after, before)
    # D1 ALONE PASSES FOR THE WRONG REASON AND THIS IS THE PROOF. When --rule
    # became required and this call had not been updated, --add refused it for
    # a MISSING FLAG -- so nothing was appended, D1 went green, and only D2
    # caught that the refusal had nothing to do with duplication. An arm that
    # asserts an absence needs an arm asserting the REASON beside it.
    check('D2 and it says so', 'already registered' in out, True)

    # ...but the SAME COMMIT with a DIFFERENT defect is a different record.
    # 5b98fd27 fixed three distinct faults in one commit, and collapsing them
    # would undercount by two.
    rc, out = run(wt, '--add', '--commit', real, '--app', 'stonedesk',
                  '--layer', 'test', '--severity', 'low',
                  '--method', 'probe-control', '--found-by-tool', 'unknown', '--summary', 'a SECOND fixture',
                  '--rule', '1.1', '--phase', 'coding', '--injection-unknown', 'probe fixture',
                  '--factors-unknown', 'probe fixture -- item 75 makes --factors or an explicit unknown-reason required at --add; this probe is about other fields')
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
    p_reg = p
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

    # ── H. THE STANDING-RULE CITATION (added 2026-09-13) ───────────────
    # tools/fmea_prediction_check.py scored 0 from the day it was written and
    # said so in its own docstring: it matches a saved risk draft to a defect
    # BY RULE CITATION ONLY, because its first matcher scored 38% on word
    # overlap and ALL FIVE of those hits were false positives. The field it
    # needed did not exist. These arms hold the field that closed that, and
    # the third confidence -- NOT-CITABLE -- that stops the gap being closed
    # by pushing every awkward record into the nearest rule.
    real2 = git(wt, 'rev-parse', 'HEAD~1').stdout.strip()[:12]
    rc, out = run(wt, '--add', '--commit', real2, '--app', 'stonedesk',
                  '--layer', 'test', '--severity', 'low',
                  '--method', 'probe-control', '--found-by-tool', 'unknown', '--summary', 'H fixture')
    check('H1 --add with NO citation is REFUSED', rc, 2)
    check('H2 and names the missing flag', '--rule' in out, True)

    rc, out = run(wt, '--add', '--commit', real2, '--app', 'stonedesk',
                  '--layer', 'test', '--severity', 'low',
                  '--method', 'probe-control', '--found-by-tool', 'unknown', '--summary', 'H fixture',
                  '--rule', '9.99', '--phase', 'coding', '--injection-unknown', 'probe fixture',
                  '--factors-unknown', 'probe fixture -- item 75 makes --factors or an explicit unknown-reason required at --add; this probe is about other fields')
    check('H3 a rule id that is not a section in the rules doc is REFUSED', rc, 2)
    check('H4 and says which document it checked against',
          'SAIRN-PROCESS-RULES' in out, True)

    rc, out = run(wt, '--add', '--commit', real2, '--app', 'stonedesk',
                  '--layer', 'test', '--severity', 'low',
                  '--method', 'probe-control', '--found-by-tool', 'unknown', '--summary', 'H fixture',
                  '--rule', 'not-citable', '--phase', 'coding', '--injection-unknown', 'probe fixture',
                  '--factors-unknown', 'probe fixture -- item 75 makes --factors or an explicit unknown-reason required at --add; this probe is about other fields')
    check('H5 not-citable with NO note is REFUSED -- a bare refusal to cite '
          'is a silence, not a decision', rc, 2)

    rc, out = run(wt, '--add', '--commit', real2, '--app', 'stonedesk',
                  '--layer', 'test', '--severity', 'low',
                  '--method', 'probe-control', '--found-by-tool', 'unknown', '--summary', 'H fixture',
                  '--rule', 'not-citable', '--phase', 'coding', '--injection-unknown', 'probe fixture',
                  '--factors-unknown', 'probe fixture -- item 75 makes --factors or an explicit unknown-reason required at --add; this probe is about other fields', '--rule-note', 'no rule names this')
    check('H6 not-citable WITH a note is accepted', rc, 0)
    doc4 = json.load(io.open(p_reg, encoding='utf-8'))
    hrec = [r for r in doc4['records'] if r['summary'] == 'H fixture'][0]
    check('H7 and stores an EMPTY rules list, not a placeholder citation',
          hrec['rules'], [])
    check('H8 with the confidence recorded as a first-class answer',
          hrec['citation_confidence'], 'not-citable')

    # ── I. --check enforces it on records that are already there ───────
    doc5 = json.load(io.open(p_reg, encoding='utf-8'))
    doc5['records'][0]['rules'] = ['9.99']
    doc5['records'][0]['citation_confidence'] = 'clean'
    io.open(p_reg, 'w', encoding='utf-8', newline='').write(json.dumps(doc5, indent=2))
    rc, out = run(wt, '--check')
    check('I1 a citation naming a section that does not exist FAILS --check', rc, 1)
    check('I2 and names the bad id', '9.99' in out, True)

    doc6 = json.load(io.open(p_reg, encoding='utf-8'))
    doc6['records'][0]['rules'] = []
    doc6['records'][0]['citation_confidence'] = 'not-citable'
    doc6['records'][0].pop('citation_note', None)
    io.open(p_reg, 'w', encoding='utf-8', newline='').write(json.dumps(doc6, indent=2))
    rc, out = run(wt, '--check')
    check('I3 not-citable with no note FAILS --check', rc, 1)

    doc7 = json.load(io.open(p_reg, encoding='utf-8'))
    doc7['records'][0]['rules'] = ['1.1']
    doc7['records'][0]['citation_confidence'] = 'arguable'
    doc7['records'][0].pop('citation_note', None)
    io.open(p_reg, 'w', encoding='utf-8', newline='').write(json.dumps(doc7, indent=2))
    rc, out = run(wt, '--check')
    check('I4 an ARGUABLE citation with no note FAILS -- what is arguable '
          'about it is the whole content of the word', rc, 1)

    # ── J. CONTROL: THE VOCABULARY IS DERIVED, AND IT FAILS CLOSED ─────
    # Without this pair every arm above could be passing because the rule set
    # is empty, or because it accepts anything.
    doc8 = json.load(io.open(p_reg, encoding='utf-8'))
    doc8['records'][0]['rules'] = ['1.11']
    doc8['records'][0]['citation_confidence'] = 'clean'
    io.open(p_reg, 'w', encoding='utf-8', newline='').write(json.dumps(doc8, indent=2))
    rc, out = run(wt, '--check')
    check('J1 CONTROL: a REAL section id passes, so the vocabulary is not '
          'simply empty', rc, 0)
    check('J2 and the citation coverage is reported, not silent',
          'standing-rule citations' in out, True)

    rules_doc = os.path.join(wt, 'docs', 'SAIRN-PROCESS-RULES.md')
    moved = rules_doc + '.moved'
    os.rename(rules_doc, moved)
    try:
        rc, out = run(wt, '--check')
        check('J3 PR 1.11: with the rules doc GONE, --check returns 2 -- could '
              'not check is never folded into a pass', rc, 2)
        check('J4 and says the vocabulary is unknown',
              'COULD NOT CHECK' in out, True)
    finally:
        os.rename(moved, rules_doc)

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

    # ── G. TWO FIGURES, NOT ONE (2026-09-13) ──────────────────────────────
    # The report printed a single ALL APPS rate: every product defect over
    # EVERY tracked app line, unswept files included. One number was answering
    # two different questions -- how dense are the defects where we have
    # looked, and how much have we not looked at -- and the second was folded
    # into the first as a smaller rate. The caveat under it had always said "an
    # app with no records is an app nobody has swept, not a clean one" while
    # the arithmetic said otherwise.
    check('G1 the swept rate is labelled as the signal',
          'SWEPT FILES' in out and 'the real signal' in out, True)
    check('G2 the unswept files are a COUNT, never a rate',
          'UNSWEPT FILES' in out and 'not a rate' in out, True)
    # ── PINNED TO A PROPERTY, NOT TO A MEMBER (corrected 2026-09-16) ──────
    # This read `'sairncode' in ...` and went red the day sairncode got its
    # first record -- reporting PROGRESS as a failure. An arm pinned to a value
    # that happened to be true when it was written is the brittle-anchor class
    # this repo keeps finding; what it meant to assert is that the unswept apps
    # are NAMED at all.
    _unswept = out.split('UNSWEPT FILES')[-1][:600].split('\n')
    _named = [t.strip() for t in (_unswept[1] if len(_unswept) > 1 else '').split(',')
              if t.strip()]
    check('G3 the unswept apps are NAMED, so the coverage owed is actionable',
          len(_named) > 0, True)
    check('G3a ...and every name is a real app HTML file rather than a label',
          all(os.path.isfile(os.path.join(wt, n + '.html')) for n in _named), True)
    check('G4 the single ALL APPS rate is gone',
          'ALL APPS' in out, False)

    # AND THE NUMERATOR MATCHES THE DENOMINATOR. Found by checking the first
    # version of this very block: len(prod) counts defects filed against
    # 'PLATFORM', which is not a file and contributes no lines, so both the old
    # ALL APPS rate and the new swept rate were dividing a defect by lines it
    # does not live in.
    # Parsed by PATTERN, not by column index. The first version read
    # `.split()[3]` and got the LINE COUNT, because the label "SWEPT FILES (7)"
    # is three tokens and the per-app labels are one -- the same
    # count-the-columns mistake PR §2.1 is about, in a test rather than a row.
    def _nums(line):
        return [int(t) for t in re.findall(r'(?<![.\d])(\d+)(?![.\d])', line)]

    swept_line = [l for l in out.split('\n') if 'SWEPT FILES' in l
                  and 'UNSWEPT' not in l][0]
    # STRUCTURE, NOT A LITERAL RATE PREFIX (corrected 2026-09-16). This
    # filtered on `' 0.' in l`, so the moment any app's rate reached 1.00 --
    # sairndental did, at 9 records -- its row stopped being counted and the
    # totals stopped matching. A row is: two spaces, a name, then exactly three
    # numeric columns, whatever their magnitude.
    per_app = [l for l in out.split('\n')
               if re.match(r'^  \S+\s+\d+\s+\d+\s+\d+\.\d+\s*$', l)
               and 'SWEPT' not in l and 'UNSWEPT' not in l
               and 'OFF-FILE' not in l]
    counted = sum(_nums(l)[1] for l in per_app) if per_app else 0
    # (7) in the label is a count of files, so the defect total is the LAST
    # integer on the line, after the file count and the line count.
    check('G5 the swept defect count equals the per-app rows above it',
          _nums(swept_line)[-1], counted)
    check('G6 an off-file defect is reported with NO rate rather than divided',
          ('OFF-FILE' in out and 'NO DENOMINATOR' in out) or 'PLATFORM' not in out,
          True)

    # ── P. the injection phase (item 77) ───────────────────────────────────
    # The field exists to make an injection-vs-removal matrix possible, so the
    # arms that matter are the ones that stop it filling up with guesses.
    rc, out = run(wt, '--add', '--commit', real2, '--app', 'stonedesk',
                  '--layer', 'product', '--severity', 'low',
                  '--method', 'code-review', '--summary', 'p1',
                  '--rule', '1.1', '--phase', 'vibes', '--injection-unknown', 'probe fixture',
                  '--factors-unknown', 'probe fixture -- item 75 makes --factors or an explicit unknown-reason required at --add; this probe is about other fields')
    check('P1 an invented phase is REFUSED', rc, 2)
    check('P2 and it names the vocabulary', '--phase must be one of' in out, True)

    rc, out = run(wt, '--add', '--commit', real2, '--app', 'stonedesk',
                  '--layer', 'product', '--severity', 'low',
                  '--method', 'code-review', '--summary', 'p3',
                  '--rule', '1.1', '--injection-unknown', 'probe fixture',
                  '--factors-unknown', 'probe fixture -- item 75 makes --factors or an explicit unknown-reason required at --add; this probe is about other fields')
    check('P3 a MISSING phase is refused, not defaulted -- a field that is '
          'optional at recording time is a field that stays empty', rc, 2)
    check('P4 and it says which field', 'missing --phase' in out, True)

    rc, out = run(wt, '--add', '--commit', real2, '--app', 'stonedesk',
                  '--layer', 'product', '--severity', 'low',
                  '--method', 'code-review', '--summary', 'p5',
                  '--rule', '1.1', '--phase', 'unknown', '--injection-unknown', 'probe fixture',
                  '--factors-unknown', 'probe fixture -- item 75 makes --factors or an explicit unknown-reason required at --add; this probe is about other fields')
    check('P5 a bare `unknown` is REFUSED -- the escape hatch exists so a '
          'record can say no phase fits, not so it can say nothing', rc, 2)
    check('P6 and it says a note is required',
          '--phase-note' in out and 'silence, not a decision' in out, True)

    rc, out = run(wt, '--add', '--commit', real2, '--app', 'stonedesk',
                  '--layer', 'product', '--severity', 'low',
                  '--method', 'code-review', '--summary', 'p7',
                  '--rule', '1.1', '--phase', 'unknown', '--injection-unknown', 'probe fixture',
                  '--factors-unknown', 'probe fixture -- item 75 makes --factors or an explicit unknown-reason required at --add; this probe is about other fields',
                  '--phase-note', 'none of the four honestly fits this one')
    check('P7 CONTROL: `unknown` WITH a note is accepted -- P5 is not passing '
          'because unknown is banned outright', rc, 0)

    doc = json.loads(io.open(os.path.join(wt, REG.replace('/', os.sep)),
                             encoding='utf-8').read())
    p7 = [r for r in doc['records'] if r['summary'] == 'p7'][0]
    check('P8 the note is stored, not just demanded',
          bool(str(p7.get('phase_note') or '').strip()), True)
    check('P9 confidence defaults to INFERRED, never to stated -- the register '
          'must not claim a quote it was not given',
          p7.get('phase_confidence'), 'inferred')

    rc, out = run(wt, '--report')
    check('P10 the report prints the unknown and inferred counts ABOVE the '
          'matrix, the way NO DRAFT sits above the FMEA hit rate',
          out.index('injection_phase = unknown') < out.index('INJECTION x REMOVAL'),
          True)
    check('P11 and the matrix carries its own do-not-quote warning',
          'DO NOT QUOTE A CELL ALONE' in out, True)

    # ── CC. CONFIRMED CLEAN (2026-09-17) ────────────────────────────────────
    # The verdict this register could not record. Until today a driven
    # confirmation had nowhere to go without inventing a severity and an
    # injection phase for a thing that was never injected -- so it went into
    # PROSE, in docs/2026-09-16-item83-independent-review.md's "What was checked
    # and found SOUND" section, where no tool can read it.
    #
    # EVERY ARM HERE ATTACKS THE FIELD RATHER THAN EXERCISING IT, because the
    # failure mode of a confirmation is not a crash: it is a reassuring row
    # nobody can re-check. R1-R6 are the three refusals that make it a record.
    rc, out = run(wt, '--confirm', '--commit', real2, '--app', 'stonedesk',
                  '--layer', 'product', '--method', 'code-review',
                  '--claim', 'fine', '--driven', 'ran the suite and it passed ok',
                  '--limits', 'this is a long enough limits sentence to pass the length gate')
    check('CC1 a claim too short to re-check is REFUSED', rc, 2)
    check('CC2 and it says a claim nobody can re-check is what the field exists '
          'to stop being written in prose', 'not a claim anybody can re-check' in out, True)

    rc, out = run(wt, '--confirm', '--commit', real2, '--app', 'stonedesk',
                  '--layer', 'product', '--method', 'code-review',
                  '--claim', 'the guard refuses when the upstream read fails rather than defaulting',
                  '--driven', 'looked',
                  '--limits', 'this is a long enough limits sentence to pass the length gate')
    check('CC3 a confirmation with nothing DRIVEN is REFUSED -- a reading is not '
          'a measurement', rc, 2)
    check('CC4 and it says so in those words',
          'tell a reading from a measurement' in out, True)

    rc, out = run(wt, '--confirm', '--commit', real2, '--app', 'stonedesk',
                  '--layer', 'product', '--method', 'code-review',
                  '--claim', 'the guard refuses when the upstream read fails rather than defaulting',
                  '--driven', 'ran tests/x.js, 12 arms, all green on 2026-09-17',
                  '--limits', 'none')
    check('CC5 a confirmation claiming NO limits is REFUSED -- every real check '
          'has an edge', rc, 2)
    check('CC6 and it names the edges a reader should expect',
          'a path not driven' in out, True)

    rc, out = run(wt, '--confirm', '--commit', 'deadbeefdead', '--app', 'stonedesk',
                  '--layer', 'product', '--method', 'code-review',
                  '--claim', 'the guard refuses when the upstream read fails rather than defaulting',
                  '--driven', 'ran tests/x.js, 12 arms, all green on 2026-09-17',
                  '--limits', 'static read only, the failing-upstream path was not driven')
    check('CC7 a confirmation on a commit that does not exist is REFUSED', rc, 2)

    rc, out = run(wt, '--confirm', '--commit', real2, '--app', 'stonedesk',
                  '--layer', 'product', '--method', 'vibes',
                  '--claim', 'the guard refuses when the upstream read fails rather than defaulting',
                  '--driven', 'ran tests/x.js, 12 arms, all green on 2026-09-17',
                  '--limits', 'static read only, the failing-upstream path was not driven')
    check('CC8 an invented method is REFUSED here too -- one vocabulary, both '
          'populations', rc, 2)

    # CONTROL: a well-formed confirmation IS accepted. Without this every
    # refusal above would be satisfied by a command that refuses everything.
    rc, out = run(wt, '--confirm', '--commit', real2, '--app', 'stonedesk',
                  '--layer', 'product', '--method', 'code-review',
                  '--claim', 'the guard refuses when the upstream read fails rather than defaulting',
                  '--driven', 'ran tests/x.js, 12 arms, all green on 2026-09-17',
                  '--limits', 'static read only, the failing-upstream path was not driven',
                  '--by', 'probe')
    check('CC9 CONTROL: a well-formed confirmation is ACCEPTED', rc, 0)
    check('CC10 and the acceptance line says it is NOT a defect record',
          'NOT a defect record' in out, True)

    rc, out = run(wt, '--confirm', '--commit', real2, '--app', 'stonedesk',
                  '--layer', 'product', '--method', 'code-review',
                  '--claim', 'the guard refuses when the upstream read fails rather than defaulting',
                  '--driven', 'ran tests/x.js again, same 12 arms',
                  '--limits', 'static read only, the failing-upstream path was not driven')
    check('CC11 the SAME claim on the same commit cannot be confirmed twice -- '
          'one check run again is not corroboration', rc, 2)

    doc = json.loads(io.open(os.path.join(wt, REG.replace('/', os.sep)),
                             encoding='utf-8').read())
    check('CC12 confirmations live in their OWN array, not in records',
          'confirmations' in doc and len(doc['confirmations']) >= 1, True)
    conf = doc['confirmations'][-1]
    check('CC13 and no confirmation carries a severity -- it is not a defect '
          'with the severity left out',
          any(k in conf for k in ('severity', 'injection_phase')), False)
    check('CC14 the register total did NOT move -- a confirmation is in no '
          'defect figure', len([r for r in doc['records'] if r.get('app') == 'stonedesk'
                                and r.get('summary') == 'CONFIRM']), 0)

    rc, out = run(wt, '--report')
    check('CC15 the report prints confirmations ABOVE the defect figures',
          out.index('CONFIRMED CLEAN') < out.index('BY LAYER'), True)
    check('CC16 and says they are in NO figure below', 'in NO figure below' in out, True)
    check('CC17 and tells a reader to read the limits before quoting one',
          'read' in out and 'limits' in out, True)

    rc, out = run(wt, '--check')
    check('CC18 --check still passes with confirmations present', rc, 0)
    check('CC19 and it counts them as a SEPARATE population',
          'SEPARATE population' in out, True)

    # -- Q. which checkpoint caught it (item 63) ---------------------------
    rc, out = run(wt, '--report')
    check('Q1 the report prints the checkpoint split',
          'WHICH CHECKPOINT CAUGHT IT' in out, True)
    check('Q2 and it says the split is what DID catch each defect, not what '
          'should have -- the difference is the whole honest frame',
          'NOT THE ONE' in out and 'UNDER-COUNTS gaps' in out, True)
    check('Q3 and it names `monitoring` being zero as a SELECTION EFFECT rather '
          'than a result -- a defect nobody found is not in the register',
          'SELECTION EFFECT' in out, True)

    import importlib
    sys.path.insert(0, os.path.join(REPO, 'tools'))
    dr = importlib.import_module('defect_register')
    check('Q4 a human method maps to human-read',
          dr.checkpoint_of('code-review'), 'human-read')
    check('Q5 an independent review is ALSO human-read -- a second reader is '
          'not an automated checkpoint', dr.checkpoint_of('independent-review'),
          'human-read')
    check('Q6 a checker method maps to automated-checker',
          dr.checkpoint_of('static-checker'), 'automated-checker')
    check('Q7 live verification maps to monitoring',
          dr.checkpoint_of('live-verification'), 'monitoring')
    check('Q8 AN UNMAPPED METHOD COMES BACK unknown rather than being folded '
          'into the nearest bucket', dr.checkpoint_of('telepathy'), 'unknown')
    check('Q9 ...and EVERY method in the vocabulary has a row, so Q8 can never '
          'fire on real data without --check saying so',
          [m for m in dr.METHODS if dr.checkpoint_of(m) == 'unknown'], [])

    # -- Q10-Q13. THE FIFTH AGENT'S CHANNEL (2026-09-21) --------------------
    # The hover auditor is a structurally separate third data source, not one
    # of the four build agents. Its skill has said since 2026-09-14 that this
    # enum had no value for it, that adding one was "a code edit this role
    # does not make itself", and that findings needing the tag should be HELD
    # -- so the absence of one string was keeping real findings out of the
    # register entirely.
    check('Q10 the hover auditor has a method value at all, so its findings '
          'have somewhere to go', 'hover-audit' in dr.METHODS, True)
    check('Q11 ...and it is DISTINCT from independent-review, which is the '
          'four build agents\' peer channel -- one value for two populations '
          'would make the matrix report one reviewing population',
          'independent-review' in dr.METHODS and 'hover-audit' in dr.METHODS
          and 'hover-audit' != 'independent-review', True)
    check('Q12 ...and it is a human-read checkpoint, so --add does not demand '
          'a --found-by-tool from a role whose method is reading a diff',
          (dr.checkpoint_of('hover-audit'), dr.tool_required('hover-audit')),
          ('human-read', False))
    # ── AND THE TAG IS READ FROM THE SKILL, NOT TYPED TWICE ──────────────
    # The enum and the role that uses it live in different files, which is the
    # two-copies shape this platform keeps recording. If the skill renames its
    # tag, this arm goes red rather than the two drifting apart in silence --
    # and a hover finding tagged with a value the register does not know is
    # refused at the moment somebody is trying to record a real defect.
    _skill = os.path.join(REPO, '.claude', 'skills', 'sairn-hover-auditor',
                          'SKILL.md')
    try:
        _sb = io.open(_skill, encoding='utf-8').read()
    except (OSError, IOError):
        _sb = None
    if _sb is None:
        # NOT folded into a pass. The arm could not run and says which file it
        # could not read, rather than reporting agreement it never checked.
        check('Q13 COULD NOT RUN -- the hover skill is not readable at ' + _skill,
              False, True)
    else:
        _tags = set(re.findall(r'detection_method\s+([a-z][a-z0-9-]+)', _sb))
        check('Q13 every detection_method the hover skill names is in the '
              'vocabulary -- tags found: ' + (','.join(sorted(_tags)) or '(none)'),
              bool(_tags) and _tags <= set(dr.METHODS), True)


    # -- R. which TOOL found it (2026-09-14) --------------------------------
    check('R1 a tool name is REQUIRED when a checker found it', dr.tool_required('static-checker'), True)
    check('R2 ...and NOT required when a person did -- a code review has no tool',
          dr.tool_required('code-review'), False)

    rc, out = run(wt, '--add', '--commit', real2, '--app', 'stonedesk',
                  '--layer', 'tooling', '--severity', 'low',
                  '--method', 'static-checker', '--summary', 'r3',
                  '--rule', '1.1', '--phase', 'coding', '--injection-unknown', 'probe fixture',
                  '--factors-unknown', 'probe fixture -- item 75 makes --factors or an explicit unknown-reason required at --add; this probe is about other fields')
    check('R3 an automated find with NO tool is refused', rc, 2)
    check('R4 and it offers `unknown` rather than forcing a guess',
          'unknown' in out and '--found-by-tool is required' in out, True)

    rc, out = run(wt, '--add', '--commit', real2, '--app', 'stonedesk',
                  '--layer', 'tooling', '--severity', 'low',
                  '--method', 'code-review', '--summary', 'r5',
                  '--rule', '1.1', '--phase', 'coding', '--injection-unknown', 'probe fixture',
                  '--factors-unknown', 'probe fixture -- item 75 makes --factors or an explicit unknown-reason required at --add; this probe is about other fields',
                  '--found-by-tool', 'nav_panel_check.py')
    check('R5 a tool name on a HUMAN find is REFUSED -- a column of plausible '
          'names nobody can check is worse than an empty one', rc, 2)

    rc, out = run(wt, '--add', '--commit', real2, '--app', 'stonedesk',
                  '--layer', 'tooling', '--severity', 'low',
                  '--method', 'static-checker', '--found-by-tool', 'unknown', '--summary', 'r6',
                  '--rule', '1.1', '--phase', 'coding', '--injection-unknown', 'probe fixture',
                  '--factors-unknown', 'probe fixture -- item 75 makes --factors or an explicit unknown-reason required at --add; this probe is about other fields',
                  '--found-by-tool', 'unknown')
    check('R6 CONTROL: `unknown` IS accepted, so R3 is not passing because the '
          'field is impossible to satisfy', rc, 0)

    doc = json.loads(io.open(os.path.join(wt, REG.replace('/', os.sep)),
                             encoding='utf-8').read())
    r6 = [r for r in doc['records'] if r['summary'] == 'r6'][0]
    check('R7 the value is stored', r6.get('found_by_tool'), 'unknown')

    rc, out = run(wt, '--report')
    check('R8 the report says how many automated catches NAME their tool',
          'the TOOL is named in' in out, True)
    check('R9 ...and refuses to recompute the blocking classification, because '
          'a second copy of it is a second thing to drift',
          'second thing to drift' in out, True)


    # -- S. the injection commit, and the lag it exists to build -----------
    # `--factors-unknown` is carried here for the same reason every call above
    # carries it: item 75 makes --factors or an explicit unknown-reason
    # REQUIRED at --add, and this section is about the INJECTION pair. The
    # injection check runs before the factors check in cmd_add, so S1/S2 below
    # still fail on the injection flags and not on these.
    base = ['--add', '--commit', real2, '--app', 'stonedesk', '--layer', 'tooling',
            '--severity', 'low', '--method', 'code-review', '--rule', '1.1',
            '--phase', 'coding',
            '--factors-unknown', 'probe fixture -- this section is about the '
                                 'injection pair, not the factors']

    rc, out = run(wt, *(base + ['--summary', 's1']))
    check('S1 NEITHER flag is refused -- silently optional is how '
          'detection_method got to 1 of 52', rc, 2)
    check('S2 and it says exactly one is required',
          'EXACTLY ONE' in out, True)

    rc, out = run(wt, *(base + ['--summary', 's3', '--injection-commit', real,
                                '--injection-unknown', 'both']))
    check('S3 BOTH flags is refused too -- a reason beside a sha is a record '
          'that cannot be read either way', rc, 2)

    rc, out = run(wt, *(base + ['--summary', 's4', '--injection-commit', 'deadbeefdead']))
    check('S4 an injection sha that does not resolve is REFUSED', rc, 2)
    check('S5 and it says a bad sha is a guess with a hash on it',
          'guess with a hash' in out, True)

    rc, out = run(wt, *(base + ['--summary', 's6', '--injection-unknown',
                                'the introducing commit was not identified']))
    check('S6 a stated reason IS accepted -- the escape hatch works', rc, 0)

    rc, out = run(wt, *(base + ['--summary', 's7', '--injection-commit', real]))
    check('S7 CONTROL: a REAL sha is accepted, so S4 is not passing because the '
          'field is impossible to satisfy', rc, 0)

    doc = json.loads(io.open(os.path.join(wt, REG.replace('/', os.sep)),
                             encoding='utf-8').read())
    s6 = [r for r in doc['records'] if r['summary'] == 's6'][0]
    s7 = [r for r in doc['records'] if r['summary'] == 's7'][0]
    check('S8 the reason is stored, not merely demanded',
          bool(s6['injection'].get('unknown_reason')), True)
    check('S9 a known injection carries the sha AND a computed lag',
          s7['injection'].get('commit') is not None
          and 'lag_days' in s7['injection'], True)
    check('S10 the lag is not negative -- real2 is an ancestor of itself here, '
          'so zero is the expected floor', s7['injection']['lag_days'] >= 0, True)

    import importlib
    sys.path.insert(0, os.path.join(REPO, 'tools'))
    dr2 = importlib.import_module('defect_register')
    check('S11 lag_days counts whole days between two dates',
          dr2.lag_days('2026-09-01', '2026-09-14'), 13)
    check('S12 ...and returns None rather than 0 on an unparseable date, so a '
          'bad input cannot look like a same-day discovery',
          dr2.lag_days('not-a-date', '2026-09-14'), None)

    rc, out = run(wt, '--report')
    check('S13 with no injection commits the report says NO LAG DISTRIBUTION '
          'EXISTS rather than printing a median of nothing',
          'NO LAG DISTRIBUTION EXISTS' in out or 'lag in days' in out, True)

finally:
    git(REPO, 'worktree', 'remove', '--force', wt)
    git(REPO, 'worktree', 'prune')

# ── RESOLVABLE IS NOT REACHABLE (2026-09-16) ────────────────────────────────
# `--check` calls a SHA good the moment `rev-parse --verify` accepts it, and
# that is the right contract for a checker: a record pointing at a real object
# is not a register pointing at nothing.
#
# IT IS THE WRONG QUESTION FOR A RE-SEAT. A rebase leaves the original commit
# behind as a DANGLING object -- it still resolves until the reflog expires --
# so `--reseat` skipped it and the record went on naming a commit that is not
# on the branch. Found when the register-feed gate refused a push twice: it asks
# whether a commit BEING PUSHED has a record, the register asked whether a
# recorded SHA is a valid object, and four records satisfied the second while
# failing the first.
#
# THE ARMS BELOW BUILD A REAL DANGLING COMMIT rather than stubbing one. A stub
# would prove the branch is written; only a real orphan proves it is reached.
import importlib.util as _ilu                                    # noqa: E402

_wt2 = os.path.join(tempfile.gettempdir(), 'reseat-probe-%d' % os.getpid())
git(REPO, 'worktree', 'add', '-q', '--detach', _wt2, 'HEAD')
try:
    io.open(os.path.join(_wt2, 'zz_reseat_probe.txt'), 'w',
            encoding='utf-8', newline='\n').write('one\n')
    git(_wt2, 'add', 'zz_reseat_probe.txt')
    git(_wt2, '-c', 'user.email=probe@x', '-c', 'user.name=probe',
        'commit', '-q', '-m', 'fix(zz): a reseat probe subject nothing else uses')
    orphan = git(_wt2, 'rev-parse', 'HEAD').stdout.strip()
    # Rewrite it, exactly as a rebase does. The old SHA survives as a dangling
    # object and the SAME SUBJECT now lives at a new one.
    io.open(os.path.join(_wt2, 'zz_reseat_probe.txt'), 'w',
            encoding='utf-8', newline='\n').write('two\n')
    git(_wt2, 'add', 'zz_reseat_probe.txt')
    git(_wt2, '-c', 'user.email=probe@x', '-c', 'user.name=probe',
        'commit', '-q', '--amend', '--no-edit')
    rewritten = git(_wt2, 'rev-parse', 'HEAD').stdout.strip()

    check('S0 the orphan and the rewrite are different commits',
          orphan != rewritten and len(orphan) == 40, True)

    _spec = _ilu.spec_from_file_location(
        'dr_live', os.path.join(REPO, 'tools', 'defect_register.py'))
    dr = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(dr)
    dr.REPO = _wt2

    check('S1 the orphaned SHA still RESOLVES -- which is why --check accepts '
          'it and why that is not the bug',
          bool(dr.git('rev-parse', '--verify', orphan + '^{commit}')), True)
    check('S2 ...and it is NOT REACHABLE from the branch, which is the question '
          'a re-seat is for', dr.reachable(orphan, 'HEAD'), False)
    check('S3 CONTROL: the rewritten commit IS reachable, so the test is about '
          'reachability and not about every SHA failing',
          dr.reachable(rewritten, 'HEAD'), True)
    check('S4 CONTROL: reachable() is not inverted -- HEAD reaches itself. '
          '`merge-base --is-ancestor` signals through its EXIT CODE and prints '
          'nothing, so a truthiness test would read every ancestor as not one',
          dr.reachable('HEAD', 'HEAD'), True)
    check('S5 the base is origin/main when it exists, because that is what '
          'another clone will fetch',
          dr.reseat_base()[0] in ('origin/main', 'HEAD'), True)
finally:
    git(REPO, 'worktree', 'remove', '--force', _wt2)
    git(REPO, 'worktree', 'prune')

# ── THE $(git rev-parse HEAD) TRAP, THREE TIMES IN ONE EVENING ────────────
# `--commit $(git rev-parse HEAD)` reads as "this work" and means "whatever
# landed last". On 2026-09-16 that filed one finding against `chore(claims): cc
# releases cc` and two against `chore(docs): regenerate for the witness mint
# suite`. Neither existing check can see it -- `--check` passes because every
# field is in vocabulary and the commit exists, and `--reseat` correctly does
# nothing because the sha resolved and was reachable the whole time. It was not
# broken, it was WRONG, and that needed a question asked at WRITE time.
#
# Driven through the real is_bookkeeping_only(), imported, rather than through
# a copy of the file list.
sys.path.insert(0, os.path.join(REPO, 'tools'))
import defect_register as DR           # noqa: E402

check('TRAP1 a claims-only commit is bookkeeping',
      DR.is_bookkeeping_only(['.claude/claims/cc.json']), True)
check('TRAP2 a worklog-only commit is bookkeeping',
      DR.is_bookkeeping_only(['SAIRN-ACTIVE-WORK-hank.md']), True)
check('TRAP3 a generated-docs regeneration is bookkeeping',
      DR.is_bookkeeping_only(['docs/traceability-matrix.md',
                              'docs/MASTER-PLAN.md']), True)
check('TRAP4 a register-only correction is bookkeeping',
      DR.is_bookkeeping_only(['docs/defect-density-register.json']), True)
# THE OTHER DIRECTION, and it carries the guard: a predicate that called
# everything bookkeeping would refuse every legitimate record, and the refusal
# message would then be the thing people learn to override by reflex.
check('TRAP5 a real code fix is NOT bookkeeping',
      DR.is_bookkeeping_only(['api/cron-watchdog.js']), False)
check('TRAP6 a MIXED commit is NOT bookkeeping -- a fix that also updates its own '
      'worklog is still a fix',
      DR.is_bookkeeping_only(['api/cron-watchdog.js',
                              'SAIRN-ACTIVE-WORK-hank.md']), False)
check('TRAP7 an empty file list is NOT bookkeeping -- "could not tell" must not '
      'become a refusal',
      DR.is_bookkeeping_only([]), False)

# AND THROUGH THE REAL ENTRY POINT, because the predicate being right is not
# the same as it being WIRED. A pure-function arm passes on a tool that never
# calls it.
# ── THE ENTRY POINT, IN ITS OWN THROWAWAY WORKTREE ────────────────────────
# G1-G7 above test the predicate. A predicate being right is not the same as it
# being WIRED, so this drives the real --add. It needs its own worktree: the
# one section A used is torn down hundreds of lines earlier, and calling run()
# against a removed directory is how this arm failed on its first write.
_wt3 = os.path.join(tempfile.gettempdir(), 'defreg-guard-%d' % os.getpid())
_add3 = git(REPO, 'worktree', 'add', '-q', '--detach', _wt3, 'HEAD')
check('TRAP8a the guard worktree was created', _add3.returncode, 0)
try:
    for rel in (TOOL, REG):
        _src = os.path.join(REPO, rel.replace('/', os.sep))
        _dst = os.path.join(_wt3, rel.replace('/', os.sep))
        os.makedirs(os.path.dirname(_dst), exist_ok=True)
        io.open(_dst, 'w', encoding='utf-8', newline=chr(10)).write(
            io.open(_src, encoding='utf-8').read())
    _book = git(REPO, 'log', '-1', '--format=%H', '--',
                '.claude/claims/').stdout.strip()
    if _book:
        rc, out = run(_wt3, '--add', '--commit', _book, '--app', 'PLATFORM',
                      '--layer', 'product', '--severity', 'low', '--method',
                      'code-review', '--rule', '1.11', '--phase', 'coding',
                      '--injection-unknown', 'probe', '--factors-unknown',
                      'probe', '--summary', 'a probe record that must be '
                      'refused because the commit it cites changed nothing but '
                      'bookkeeping files')
        check('TRAP8 --add REFUSES a bookkeeping-only commit', rc, 2)
        check('TRAP9 ...and names the trap rather than just erroring',
              'git rev-parse HEAD' in out and 'whatever landed last' in out, True)
        check('TRAP10 ...and offers the override rather than leaving no way '
              'through', '--commit-is-bookkeeping' in out, True)
        # THE OVERRIDE MUST ACTUALLY WORK. A refusal with an escape hatch
        # nobody can open is a refusal, and this platform's own rule is that a
        # vocabulary with no honest way out produces a forced value rather than
        # honesty.
        rc2, out2 = run(_wt3, '--add', '--commit', _book, '--app', 'PLATFORM',
                        '--layer', 'product', '--severity', 'low', '--method',
                        'code-review', '--rule', '1.11', '--phase', 'coding',
                        '--injection-unknown', 'probe', '--factors-unknown',
                        'probe', '--commit-is-bookkeeping',
                        'a probe exercising the documented override',
                        '--summary', 'a probe record accepted through the '
                        'override, to prove the escape hatch opens')
        check('TRAP11 ...and the override REALLY opens it', rc2, 0)
    else:
        check('TRAP8 SKIPPED -- no claims-only commit to drive the refusal with, '
              'declared rather than passed quietly', 'skipped', 'skipped')
finally:
    git(REPO, 'worktree', 'remove', '--force', _wt3)
check('TRAP12 the guard worktree is gone', os.path.exists(_wt3), False)

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
