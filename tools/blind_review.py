"""Item 79 -- the reviewer judges FIRST, and only then sees what the tool said.

    python tools/blind_review.py --start 12          # write a blind worksheet
    python tools/blind_review.py --submit <file>     # judge, then reveal
    python tools/blind_review.py --fixtures          # blind lock, reads no data
    python tools/blind_review.py --json

Exit 0 when a round completes, 1 on a finding, 2 when a round could not run.
REPORT ONLY. It gates nothing; it changes the ORDER in which two things are
read.

── THE EFFECT THIS IS BUILT AGAINST ───────────────────────────────────────────
AUTOMATION BIAS: once an automated verdict is visible, the judgment that follows
anchors on it. The reviewer's number moves toward the tool's number, and both
the agreement rate and the reviewer's own confidence go up while the independent
information content goes DOWN. The failure is not that people trust tools -- it
is that a review AFTER the score cannot be distinguished from a review that
would have reached the same answer alone.

THE MITIGATION IS AN ORDERING, NOT A WARNING. Telling people not to anchor does
not work. Withholding the number until their judgment is recorded does.

── SO THE ROUND HAS TWO PHASES AND THEY CANNOT BE COLLAPSED ───────────────────
  --start    writes a worksheet of EVIDENCE ONLY -- what the record says, where
             it is, what changed -- with the recorded severity REMOVED, and
             seals the answers in a separate file the worksheet never names.
  --submit   takes the reviewer's own severities, THEN reveals the recorded
             ones, and reports where they differ.

The second phase is where the number appears, and it is the first moment it can.

── THE ACCEPT NEEDS A DEFEATER, OR THE ORDERING BUYS NOTHING ──────────────────
A reviewer who records a severity with no reasoning has not judged, and the
reveal re-anchors them for the next item anyway. So every judgment must carry a
DEFEATER: what would have to be true for this severity to be WRONG. Free text,
with a substance floor, refused when absent. It is a small friction and it is
the only part of the flow that forces engagement with the claim rather than with
the score.

── WHAT THE ORDERING CAN AND CANNOT BE ENFORCED BY, STATED PLAINLY ────────────
MECHANICAL, and these really are checked:
  * the worksheet is SCANNED for every withheld value and the round REFUSES to
    start if one appears in it. A blind worksheet that leaks the answer is worse
    than no worksheet, because the round then produces a measured agreement rate
    that means nothing;
  * the sealed answers live at a path the worksheet does not name;
  * the submission is refused if it was last modified BEFORE the round started,
    which catches a file prepared in advance;
  * every judgment must name a record that is really in the round.

NOT MECHANICAL, and no file-based flow can make it so: nothing stops a reviewer
opening the sealed file. The control is that doing so is a deliberate act with a
name, rather than the default reading order. That is the honest ceiling and it
is printed on every round rather than implied by the word "blind".

── WHAT IT CANNOT DO ──────────────────────────────────────────────────────────
  * Say who is right. A disagreement is a disagreement; the recorded severity is
    not ground truth and neither is the reviewer.
  * Measure automation bias from one round. It measures agreement under a blind
    ordering. Comparing that against agreement under a score-first ordering is
    the experiment, and it needs both.
"""
import hashlib
import io
import json
import os
import random
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTER = os.path.join(REPO, 'docs', 'defect-density-register.json')
ROUNDS = os.path.join(REPO, 'docs', 'blind-review-rounds.json')
WORKSHEET = os.path.join(REPO, 'docs', 'blind-review-worksheet.md')
SEALED = os.path.join(REPO, '.blind-review-sealed.json')

CRITERIA_VERSION = '2026-09-15.1'

# The field whose value is withheld, and the vocabulary it is drawn from. Both
# are withheld: seeing the LIST is fine, seeing which one applies is the anchor.
WITHHELD = 'severity'
VOCAB = ['critical', 'high', 'moderate', 'low']

# A defeater has to say something. Same shape as --decide's reason floor in
# tools/defect_budget_policy.py: "looks right" satisfies any keyword check.
MIN_DEFEATER_CHARS = 40

# Evidence a reviewer may see. Deliberately a WHITELIST -- a blacklist of the
# withheld field would leak the next field somebody adds to the register.
EVIDENCE_FIELDS = ['commit', 'date', 'app', 'layer', 'subject', 'summary',
                   'files', 'lines_added', 'lines_removed', 'detection_method',
                   'injection_phase', 'rules']


def load_records():
    if not os.path.exists(REGISTER):
        return None
    data = json.load(io.open(REGISTER, encoding='utf-8'))
    recs = data['records'] if isinstance(data, dict) else data
    return recs or None


def evidence_of(rec):
    return {k: rec.get(k) for k in EVIDENCE_FIELDS if rec.get(k) not in (None, '')}


def leak_scan(text, answers):
    """Every withheld value that appears in the worksheet text.

    A whole-word search, not a substring one: `low` is a substring of `follow`
    and `allowed`, and a scanner that could not tell those apart would refuse
    every round and be switched off.
    """
    import re
    found = []
    for a in sorted(set(answers)):
        if re.search(r'\b%s\b' % re.escape(a), text, re.I):
            found.append(a)
    return found


def build_worksheet(sample):
    """Returns (preamble, body). THE SPLIT IS NOT COSMETIC.

    The preamble names the whole vocabulary, so it necessarily contains every
    possible answer -- the first fixture run caught exactly that and refused
    the round. Naming the LIST is not the anchor; naming WHICH ONE APPLIES is.
    So the leak scan runs on the BODY, where a record's own evidence lives, and
    the preamble is excluded by construction rather than by a special case
    somebody could quietly widen later.
    """
    L = []
    L.append('# Blind review worksheet -- judge BEFORE you see the recorded answer')
    L.append('')
    L.append('**%d record(s).** The recorded `%s` has been removed from every '
             'one. The vocabulary is `%s` -- seeing the LIST is fine, seeing '
             'which one applies is the anchor this flow exists to remove.'
             % (len(sample), WITHHELD, '`, `'.join(VOCAB)))
    L.append('')
    L.append('For each record write YOUR OWN severity and a DEFEATER: what '
             'would have to be true for that severity to be wrong. A judgment '
             'with no defeater is refused, because recording a word is not '
             'judging and the reveal would re-anchor you for the next one '
             'anyway.')
    L.append('')
    L.append('Submit as JSON: `[{"id": "...", "severity": "...", '
             '"defeater": "..."}, ...]`, then')
    L.append('')
    L.append('    python tools/blind_review.py --submit <your-file.json>')
    L.append('')
    B = []
    for r in sample:
        B.append('---')
        B.append('')
        B.append('## %s' % r['id'])
        B.append('')
        for k, v in evidence_of(r['record']).items():
            B.append('- **%s:** %s' % (k, v if not isinstance(v, list)
                                       else ', '.join(str(x) for x in v)))
        B.append('')
    return '\n'.join(L) + '\n', '\n'.join(B) + '\n'


def start(n):
    recs = load_records()
    if recs is None:
        return 2, 'the defect register could not be read, so no round started'
    usable = [r for r in recs if r.get(WITHHELD) and r.get('subject')]
    if len(usable) < 3:
        return 2, ('only %d usable record(s); a round of fewer than 3 measures '
                   'nothing' % len(usable))
    n = max(3, min(n, len(usable)))
    # Deterministic from the register's own content, so two clones starting a
    # round from the same register get the same sample and the results can be
    # compared. Math.random would make every round its own population.
    seed = hashlib.sha256(
        json.dumps([r.get('commit') for r in usable], sort_keys=True)
        .encode('utf-8')).hexdigest()
    rnd = random.Random(seed)
    picked = rnd.sample(usable, n)
    sample = [{'id': 'R%02d' % (i + 1), 'record': r}
              for i, r in enumerate(picked)]
    answers = [r['record'][WITHHELD] for r in sample]

    preamble, body = build_worksheet(sample)
    text = preamble + body
    leaked = leak_scan(body, answers)
    if leaked:
        return 2, ('THE WORKSHEET LEAKS THE ANSWER (%s) and the round is '
                   'REFUSED. A blind worksheet that shows the verdict produces '
                   'a measured agreement rate that means nothing, which is '
                   'worse than not running the round.' % ', '.join(leaked))

    io.open(WORKSHEET, 'w', encoding='utf-8', newline='\n').write(text)
    io.open(SEALED, 'w', encoding='utf-8', newline='\n').write(json.dumps({
        'criteria_version': CRITERIA_VERSION,
        'started_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'started_epoch': int(time.time()),
        'answers': {s['id']: s['record'][WITHHELD] for s in sample},
        'commits': {s['id']: s['record'].get('commit') for s in sample},
    }, indent=2) + '\n')
    return 0, ('%d record(s) written to %s. The recorded %s is sealed in %s and '
               'is not in the worksheet -- checked, not asserted.'
               % (len(sample), os.path.relpath(WORKSHEET, REPO), WITHHELD,
                  os.path.relpath(SEALED, REPO)))


def submit(path):
    if not os.path.exists(SEALED):
        return 2, 'no round is open -- run --start first'
    sealed = json.load(io.open(SEALED, encoding='utf-8'))
    if not os.path.exists(path):
        return 2, 'no such submission: %s' % path
    # ORDERING, as far as a file can carry it: a submission last modified BEFORE
    # the round opened was not written in response to this worksheet.
    if os.path.getmtime(path) < sealed.get('started_epoch', 0):
        return 2, ('the submission predates the round, so it was not written '
                   'against this worksheet. That is a refusal and not a '
                   'failure: the whole value of the flow is the order.')
    try:
        subs = json.load(io.open(path, encoding='utf-8'))
    except ValueError as e:
        return 2, 'the submission is not valid JSON: %s' % e
    if not isinstance(subs, list) or not subs:
        return 2, 'the submission must be a non-empty list'

    answers = sealed['answers']
    rows, problems = [], []
    seen = set()
    for s in subs:
        ident = (s or {}).get('id')
        if ident not in answers:
            problems.append('%r is not a record in this round' % ident)
            continue
        if ident in seen:
            problems.append('%s judged twice' % ident)
            continue
        seen.add(ident)
        mine = (s.get(WITHHELD) or '').strip().lower()
        if mine not in VOCAB:
            problems.append('%s: %r is not one of %s' % (ident, mine, VOCAB))
            continue
        defeater = (s.get('defeater') or '').strip()
        if len(defeater) < MIN_DEFEATER_CHARS:
            problems.append(
                '%s: NO DEFEATER. Say what would have to be true for %r to be '
                'wrong. Recording a word is not judging, and an accept with no '
                'engagement is what the reveal re-anchors.' % (ident, mine))
            continue
        rows.append({'id': ident, 'mine': mine, 'recorded': answers[ident],
                     'agree': mine == answers[ident], 'defeater': defeater,
                     'commit': sealed['commits'].get(ident)})
    if problems:
        return 2, problems
    missing = sorted(set(answers) - seen)
    return 0, {'rows': rows, 'missing': missing, 'sealed': sealed}


# ── THE BLIND LOCK ────────────────────────────────────────────────────────────
def fixtures():
    out, bad = [], 0

    def ck(name, cond, detail=''):
        nonlocal bad
        out.append(('  ok   ' if cond else '  FAIL ') + name
                   + ('' if cond else '  <- ' + str(detail)[:220]))
        if not cond:
            bad += 1

    rec = {'commit': 'abc123', 'date': '2026-01-01', 'subject': 'a thing',
           'summary': 'it broke', 'severity': 'high', 'phase_confidence': 'x'}
    ev = evidence_of(rec)
    ck('the evidence carries the subject and the summary', 'subject' in ev and 'summary' in ev)
    ck('THE WITHHELD FIELD IS NOT IN THE EVIDENCE', WITHHELD not in ev, ev)
    ck('CONTROL: the evidence is a WHITELIST, so a field added to the register '
       'tomorrow is withheld by default rather than leaked by default',
       'phase_confidence' not in ev, ev)

    ck('a leak is detected when the answer appears in the text',
       leak_scan('this record is high severity', ['high']) == ['high'])
    ck('CONTROL: a clean worksheet scans clean',
       leak_scan('this record changed two files', ['high']) == [])
    ck('CONTROL: the scan is WHOLE-WORD -- `low` inside `allowed` and `follow` '
       'is not a leak, and a substring scanner would refuse every round and be '
       'switched off', leak_scan('the change is allowed, follow it', ['low']) == [],
       leak_scan('the change is allowed, follow it', ['low']))
    ck('...but a real `low` on its own IS a leak',
       leak_scan('severity is low here', ['low']) == ['low'])
    ck('the scan is case-insensitive, or LOW slips past',
       leak_scan('severity is LOW here', ['low']) == ['low'])

    sample = [{'id': 'R01', 'record': rec}]
    preamble, body = build_worksheet(sample)
    ck('the worksheet BODY does NOT contain the recorded answer',
       leak_scan(body, ['high']) == [], leak_scan(body, ['high']))
    ck('...and it DOES contain the evidence, or there is nothing to judge',
       'a thing' in body and 'it broke' in body)
    ck('THE ARM THAT CAUGHT THE FIRST DESIGN: the PREAMBLE names the whole '
       'vocabulary, so it contains every possible answer including this one. '
       'Naming the LIST is not the anchor -- naming which one APPLIES is -- '
       'which is why the scan runs on the body and not on the page',
       leak_scan(preamble, ['high']) == ['high'], leak_scan(preamble, ['high']))
    ck('CONTROL: a record whose EVIDENCE mentions the answer is STILL caught, '
       'so excluding the preamble did not quietly disable the scan',
       leak_scan(build_worksheet([{'id': 'R01', 'record': dict(
           rec, summary='this was a high severity break')}])[1], ['high'])
       == ['high'])
    ck('CONTROL: the worksheet names the vocabulary, which is deliberate',
       all(v in preamble for v in VOCAB), preamble[:300])
    ck('CONTROL: the worksheet never names the sealed file, so the answer is '
       'not one click away from the thing being read',
       os.path.basename(SEALED) not in preamble + body)
    ck('the worksheet demands a DEFEATER in as many words',
       'defeater' in preamble.lower())
    return out, bad


def main(argv):
    if '--fixtures' in argv:
        lines, bad = fixtures()
        print('BLIND REVIEW -- blind lock, %d arms, no register read' % len(lines))
        for l in lines:
            print(l)
        print('  %s' % ('ALL FIXTURES PASS' if not bad
                        else '%d FIXTURE(S) FAILED' % bad))
        return 1 if bad else 0

    lines, bad = fixtures()
    if bad:
        print('THE FIXTURE LOCK FAILED -- no round was started or scored.')
        for l in lines:
            print(l)
        return 2

    if '--start' in argv:
        i = argv.index('--start')
        n = int(argv[i + 1]) if len(argv) > i + 1 and argv[i + 1].isdigit() else 12
        rc, msg = start(n)
        print('BLIND REVIEW -- item 79, criteria %s' % CRITERIA_VERSION)
        print('  ' + str(msg))
        if rc == 0:
            print('')
            print('  THE CEILING, said now rather than implied by the word')
            print('  "blind": nothing stops you opening the sealed file. The')
            print('  control is that doing so is a deliberate act with a name,')
            print('  instead of the default reading order.')
        return rc

    if '--submit' in argv:
        rc, res = submit(argv[argv.index('--submit') + 1])
        print('BLIND REVIEW -- item 79, criteria %s' % CRITERIA_VERSION)
        if rc != 0:
            for p in (res if isinstance(res, list) else [res]):
                print('  REFUSED: %s' % p)
            return rc
        rows, missing = res['rows'], res['missing']
        agree = [r for r in rows if r['agree']]
        print('  %d judged, %d agree with the recorded %s, %d differ.'
              % (len(rows), len(agree), WITHHELD, len(rows) - len(agree)))
        if missing:
            print('  %d record(s) NOT judged and NOT counted: %s'
                  % (len(missing), ', '.join(missing)))
        print('')
        print('  %-5s %-10s %-10s %s' % ('id', 'yours', 'recorded', ''))
        for r in rows:
            print('  %-5s %-10s %-10s %s'
                  % (r['id'], r['mine'], r['recorded'],
                     '' if r['agree'] else '<- DIFFERS'))
        print('')
        for r in rows:
            if not r['agree']:
                print('  %s (%s)' % (r['id'], r['commit']))
                print('    your defeater: %s' % r['defeater'][:200])
        print('')
        print('  A DISAGREEMENT IS NOT AN ERROR. The recorded severity is not')
        print('  ground truth and neither is yours -- what the round produces')
        print('  is an agreement rate measured under a BLIND ordering, which')
        print('  is the only kind that means anything.')
        print('')
        print('  AND ONE ROUND MEASURES NOTHING ABOUT AUTOMATION BIAS. The')
        print('  experiment is this number against the same reviewers under a')
        print('  SCORE-FIRST ordering, and that second arm does not exist yet.')
        return 1 if len(agree) != len(rows) else 0

    print(__doc__.strip().splitlines()[0])
    print('')
    print('  --start N          write a blind worksheet')
    print('  --submit FILE      judge, then reveal')
    print('  --fixtures         the blind lock')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
