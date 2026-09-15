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

    real = git(wt, 'rev-parse', 'HEAD').stdout.strip()[:12]

    # ── A. it reports and it validates ─────────────────────────────────────
    rc, out = run(wt, '--report')
    check('A1 --report runs', rc, 0)
    rc, out = run(wt, '--check')
    check('A2 --check passes on the committed register', rc, 0)

    # ── B. IT REFUSES WHAT IT CANNOT VERIFY ────────────────────────────────
    rc, out = run(wt, '--add', '--commit', 'deadbeefdead', '--app', 'x',
                  '--layer', 'product', '--severity', 'high',
                  '--method', 'code-review', '--summary', 'nope',
                  '--rule', '1.1', '--phase', 'coding', '--injection-unknown', 'probe fixture')
    check('B1 a commit that does not exist is REFUSED', rc, 2)
    check('B2 and it says so', 'no such commit' in out, True)

    rc, out = run(wt, '--add', '--commit', real, '--app', 'x',
                  '--layer', 'product', '--severity', 'high',
                  '--method', 'vibes', '--summary', 'nope', '--rule', '1.1', '--phase', 'coding', '--injection-unknown', 'probe fixture')
    check('B3 an invented detection method is REFUSED', rc, 2)
    check('B4 because the matrix is meaningless with free text',
          '--method must be one of' in out, True)

    rc, out = run(wt, '--add', '--commit', real, '--app', 'x',
                  '--layer', 'guesswork', '--severity', 'high',
                  '--method', 'code-review', '--summary', 'nope',
                  '--rule', '1.1', '--phase', 'coding', '--injection-unknown', 'probe fixture')
    check('B5 an invented layer is REFUSED', rc, 2)

    # ── C. it derives rather than trusting what it was told ────────────────
    rc, out = run(wt, '--add', '--commit', real, '--app', 'stonedesk',
                  '--layer', 'test', '--severity', 'low',
                  '--method', 'probe-control', '--found-by-tool', 'unknown', '--summary', 'a probe fixture',
                  '--rule', '1.1', '--phase', 'coding', '--injection-unknown', 'probe fixture')
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
                  '--rule', '1.1', '--phase', 'coding', '--injection-unknown', 'probe fixture')
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
                  '--rule', '1.1', '--phase', 'coding', '--injection-unknown', 'probe fixture')
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
                  '--rule', '9.99', '--phase', 'coding', '--injection-unknown', 'probe fixture')
    check('H3 a rule id that is not a section in the rules doc is REFUSED', rc, 2)
    check('H4 and says which document it checked against',
          'SAIRN-PROCESS-RULES' in out, True)

    rc, out = run(wt, '--add', '--commit', real2, '--app', 'stonedesk',
                  '--layer', 'test', '--severity', 'low',
                  '--method', 'probe-control', '--found-by-tool', 'unknown', '--summary', 'H fixture',
                  '--rule', 'not-citable', '--phase', 'coding', '--injection-unknown', 'probe fixture')
    check('H5 not-citable with NO note is REFUSED -- a bare refusal to cite '
          'is a silence, not a decision', rc, 2)

    rc, out = run(wt, '--add', '--commit', real2, '--app', 'stonedesk',
                  '--layer', 'test', '--severity', 'low',
                  '--method', 'probe-control', '--found-by-tool', 'unknown', '--summary', 'H fixture',
                  '--rule', 'not-citable', '--phase', 'coding', '--injection-unknown', 'probe fixture', '--rule-note', 'no rule names this')
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
    check('G3 and they are NAMED, so the coverage owed is actionable',
          'sairncode' in out.split('UNSWEPT FILES')[-1][:600], True)
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
    per_app = [l for l in out.split('\n')
               if l.startswith('  ') and ' 0.' in l and 'SWEPT' not in l
               and 'UNSWEPT' not in l and 'OFF-FILE' not in l]
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
                  '--rule', '1.1', '--phase', 'vibes', '--injection-unknown', 'probe fixture')
    check('P1 an invented phase is REFUSED', rc, 2)
    check('P2 and it names the vocabulary', '--phase must be one of' in out, True)

    rc, out = run(wt, '--add', '--commit', real2, '--app', 'stonedesk',
                  '--layer', 'product', '--severity', 'low',
                  '--method', 'code-review', '--summary', 'p3',
                  '--rule', '1.1', '--injection-unknown', 'probe fixture')
    check('P3 a MISSING phase is refused, not defaulted -- a field that is '
          'optional at recording time is a field that stays empty', rc, 2)
    check('P4 and it says which field', 'missing --phase' in out, True)

    rc, out = run(wt, '--add', '--commit', real2, '--app', 'stonedesk',
                  '--layer', 'product', '--severity', 'low',
                  '--method', 'code-review', '--summary', 'p5',
                  '--rule', '1.1', '--phase', 'unknown', '--injection-unknown', 'probe fixture')
    check('P5 a bare `unknown` is REFUSED -- the escape hatch exists so a '
          'record can say no phase fits, not so it can say nothing', rc, 2)
    check('P6 and it says a note is required',
          '--phase-note' in out and 'silence, not a decision' in out, True)

    rc, out = run(wt, '--add', '--commit', real2, '--app', 'stonedesk',
                  '--layer', 'product', '--severity', 'low',
                  '--method', 'code-review', '--summary', 'p7',
                  '--rule', '1.1', '--phase', 'unknown', '--injection-unknown', 'probe fixture',
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


    # -- R. which TOOL found it (2026-09-14) --------------------------------
    check('R1 a tool name is REQUIRED when a checker found it', dr.tool_required('static-checker'), True)
    check('R2 ...and NOT required when a person did -- a code review has no tool',
          dr.tool_required('code-review'), False)

    rc, out = run(wt, '--add', '--commit', real2, '--app', 'stonedesk',
                  '--layer', 'tooling', '--severity', 'low',
                  '--method', 'static-checker', '--summary', 'r3',
                  '--rule', '1.1', '--phase', 'coding', '--injection-unknown', 'probe fixture')
    check('R3 an automated find with NO tool is refused', rc, 2)
    check('R4 and it offers `unknown` rather than forcing a guess',
          'unknown' in out and '--found-by-tool is required' in out, True)

    rc, out = run(wt, '--add', '--commit', real2, '--app', 'stonedesk',
                  '--layer', 'tooling', '--severity', 'low',
                  '--method', 'code-review', '--summary', 'r5',
                  '--rule', '1.1', '--phase', 'coding', '--injection-unknown', 'probe fixture',
                  '--found-by-tool', 'nav_panel_check.py')
    check('R5 a tool name on a HUMAN find is REFUSED -- a column of plausible '
          'names nobody can check is worse than an empty one', rc, 2)

    rc, out = run(wt, '--add', '--commit', real2, '--app', 'stonedesk',
                  '--layer', 'tooling', '--severity', 'low',
                  '--method', 'static-checker', '--found-by-tool', 'unknown', '--summary', 'r6',
                  '--rule', '1.1', '--phase', 'coding', '--injection-unknown', 'probe fixture',
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
    base = ['--add', '--commit', real2, '--app', 'stonedesk', '--layer', 'tooling',
            '--severity', 'low', '--method', 'code-review', '--rule', '1.1',
            '--phase', 'coding']

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
