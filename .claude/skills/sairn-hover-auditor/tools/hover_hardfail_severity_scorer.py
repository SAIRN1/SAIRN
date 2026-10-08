#!/usr/bin/env python
"""Star-flagged (security / data-integrity / irreversible-operation) items
cap a batch's result regardless of how many other items passed. An
unevidenced DONE/PASS claim scores 0 for that item, independent of the cap.

Own tool, own location. Built 2026-10-06 (H1, corrected batch H, item 8).
Design logged before this file was written (seq 972). Independent of H2's
own hover2_hardfail_score.py -- same question, separate implementation.
Reads only this role's own hover-audit-log.jsonl -- no build-agent tool.

CATEGORIES (keyword heuristic over an entry's own text -- INFERRED, not a
structured field; hover_log.py's schema carries no such tag):
  SECURITY: no role gate, PII, auth_bypass-shaped disclosure, unauthorized
  DATA_INTEGRITY: silent (failure/corruption), wrong answer, data loss
  IRREVERSIBLE: force-push, cannot be undone, no recovery

An entry matching a category is OPEN unless its own text ALSO contains a
closed-marker (closed / fixed / confirmed closed). An OPEN hard-fail entry
caps the whole batch's grade at FAIL; the report names which entry and
category did it, never a bare grade.

NEGATION GUARD (added 2026-10-07, H1 batch M, item 3 -- real catch, seq1043/
1052/1055-routed-finding): a bare keyword match cannot tell "PII exposed"
from "NOT ... PII ...", and this tool flagged its own entries seq1036/1037/
1040 as SECURITY purely because each contained the disclaimer phrase "NOT
MONEY/PII/REGULATED", explicitly DENYING the category it was read as
affirming. Before counting a keyword match as a real hit, the ~40 characters
immediately preceding it are checked for a NOT/not negation token with no
sentence break in between; a negated match does not count toward that
category. This is a narrow, local guard (one negation shape, one lookback
window) -- it does not attempt general sentiment analysis and will not catch
a negation phrased differently (e.g. "is not exploitable in this context").

EVIDENCE CHECK, SEPARATE FROM THE CAP: an entry asserting DONE / PASS /
CONFIRMED / MATCH needs a command+exit-or-timestamp pattern somewhere in
its own text (the same shape hover_log.py's own UNDERIVED CITATION warning
already looks for). Missing it scores 0 for that entry.
"""
import json
import re
import sys

HARDFAIL_PATTERNS = {
    'SECURITY': re.compile(r'no role gate|PII\b|AUTH_BYPASS|unauthori[sz]ed|no role check', re.I),
    'DATA_INTEGRITY': re.compile(r'\bsilent(ly)? (fail|corrupt)|wrong answer|data loss|silently wrong', re.I),
    'IRREVERSIBLE': re.compile(r'\bforce-?push|cannot be undone|no recovery|irreversibl', re.I),
}
CLOSED_MARKERS = re.compile(r'\bIS CLOSED\b|\bCLOSED,\b|\bNOW CLOSED\b|\bCONFIRMED CLOSED\b|commit [0-9a-f]{7,40}[^.]*clos', re.I)
EVIDENCE_PATTERNS = re.compile(r'\bexit\s*0?[0-9]\b|\bEXIT\s+[0-9]\b|20\d\d-\d\d-\d\dT\d\d:\d\d', re.I)
DONE_CLAIM_RE = re.compile(r'\bDONE\b|\bCONFIRMED\b|\bMATCH\b|\bPASS(ED)?\b', re.I)
NEGATION_LOOKBACK_CHARS = 40
NEGATION_RE = re.compile(r'\bnot\b', re.I)
SENTENCE_BREAK_RE = re.compile(r'[.!?\n]')


def _is_negated(text, match_start):
    """True if a NOT token sits within NEGATION_LOOKBACK_CHARS before
    match_start with no sentence-ending punctuation between them."""
    window_start = max(0, match_start - NEGATION_LOOKBACK_CHARS)
    window = text[window_start:match_start]
    # Only consider the segment after the LAST sentence break inside the
    # window, so a negation in a prior sentence never reaches across a period.
    pieces = SENTENCE_BREAK_RE.split(window)
    local = pieces[-1] if pieces else window
    return bool(NEGATION_RE.search(local))


def load_entries(log_path, seq_from, seq_to):
    out = []
    with open(log_path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            e = json.loads(line)
            if seq_from <= e.get('seq', -1) <= seq_to:
                out.append(e)
    return out


def _category_hit(text, pattern):
    """True iff pattern matches somewhere in text with at least one match
    NOT negated by a preceding NOT within the lookback window."""
    for m in pattern.finditer(text):
        if not _is_negated(text, m.start()):
            return True
    return False


def classify(entry):
    text = entry.get('summary') or ''
    hits = [cat for cat, pat in HARDFAIL_PATTERNS.items() if _category_hit(text, pat)]
    if not hits:
        return None
    closed = bool(CLOSED_MARKERS.search(text))
    return {'categories': hits, 'closed': closed}


def evidence_check(entry):
    text = entry.get('summary') or ''
    if not DONE_CLAIM_RE.search(text):
        return None  # does not assert a DONE/PASS/CONFIRMED outcome -- nothing to check
    return bool(EVIDENCE_PATTERNS.search(text))


def score_batch(log_path, seq_from, seq_to):
    entries = load_entries(log_path, seq_from, seq_to)
    hardfail_hits = []
    unevidenced = []
    for e in entries:
        cls = classify(e)
        if cls and not cls['closed']:
            hardfail_hits.append({'seq': e['seq'], 'categories': cls['categories']})
        ev = evidence_check(e)
        if ev is False:
            unevidenced.append(e['seq'])
    grade = 'FAIL' if hardfail_hits else 'PASS'
    downgrade_rule = None
    if hardfail_hits:
        first = hardfail_hits[0]
        downgrade_rule = ('CAPPED BY HARD-FAIL RULE: seq %d, category %s, open (no closed-marker found)'
                           % (first['seq'], '/'.join(first['categories'])))
    return {
        'entries_scored': len(entries),
        'grade': grade,
        'downgrade_rule': downgrade_rule,
        'hardfail_hits': hardfail_hits,
        'unevidenced_claims': unevidenced,
    }


def _selftest():
    import os
    import tempfile
    fixture_open = [
        {'seq': 1, 'summary': 'Found: alf_staff/read has no role gate, PII exposed. OPEN.'},
        {'seq': 2, 'summary': 'Unrelated routine check, exit 0, 2026-10-06T10:00:00Z, PASS.'},
    ]
    fixture_closed = [
        {'seq': 1, 'summary': 'This finding was OPEN but is now CONFIRMED CLOSED, commit abc1234 closes it.'},
    ]
    fixture_unevidenced = [
        {'seq': 1, 'summary': 'The tool is DONE and everything is fine, trust me.'},
    ]
    # Built directly from the real false-positive text (seq1036/1037/1040 of
    # this role's own log), not a paraphrase -- the exact disclaimer phrase
    # that triggered the bug being fixed.
    fixture_negation_real_text = [
        {'seq': 1, 'summary':
            'DOCUMENTATION, NOT MONEY/PII/REGULATED: a code comment\'s own '
            'count has drifted from the code it describes.'},
        {'seq': 2, 'summary':
            'DOCUMENTATION/LEDGER, NOT MONEY/PII/REGULATED: docs/scrutiny-'
            'flags.json\'s current content does not match its own landing-'
            'time commit claim.'},
    ]
    # A genuine, UN-negated SECURITY hit must still fire -- the guard must not
    # overcorrect into silencing a real finding just because it mentions PII.
    fixture_negation_real_hit = [
        {'seq': 1, 'summary':
            'FINDING: alf_staff/read returns PII to any session with no role '
            'gate at all.'},
    ]

    def run(fixture):
        fd, path = tempfile.mkstemp(suffix='.jsonl')
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            for e in fixture:
                f.write(json.dumps(e) + '\n')
        try:
            return score_batch(path, 1, 999)
        finally:
            os.remove(path)

    ok = 0
    total = 5
    r1 = run(fixture_open)
    if r1['grade'] == 'FAIL' and r1['downgrade_rule']:
        ok += 1
        print('  ok   open hard-fail entry caps the batch at FAIL, rule named')
    else:
        print('  FAIL expected FAIL+named rule, got %r' % r1)

    r2 = run(fixture_closed)
    if r2['grade'] == 'PASS':
        ok += 1
        print('  ok   closed-marked hard-fail entry does NOT cap the batch')
    else:
        print('  FAIL expected PASS (closed marker respected), got %r' % r2)

    r3 = run(fixture_unevidenced)
    if r3['unevidenced_claims'] == [1]:
        ok += 1
        print('  ok   DONE claim with no command/exit/timestamp scores as unevidenced')
    else:
        print('  FAIL expected unevidenced_claims == [1], got %r' % r3)

    r4 = run(fixture_negation_real_text)
    if r4['grade'] == 'PASS' and r4['hardfail_hits'] == []:
        ok += 1
        print('  ok   negated disclaimer text ("NOT MONEY/PII/REGULATED") does NOT cap the batch')
    else:
        print('  FAIL expected PASS, no hardfail hits, got %r' % r4)

    r5 = run(fixture_negation_real_hit)
    if r5['grade'] == 'FAIL' and r5['hardfail_hits'] and r5['hardfail_hits'][0]['seq'] == 1:
        ok += 1
        print('  ok   a genuine un-negated PII/no-role-gate hit still caps the batch (guard does not overcorrect)')
    else:
        print('  FAIL expected FAIL with seq1 flagged, got %r' % r5)

    print('%d/%d fixture checks correct' % (ok, total))
    return ok == total


def main(argv):
    if '--selftest' in argv:
        return 0 if _selftest() else 1
    if '--score' in argv:
        i = argv.index('--score')
        log_path, seq_from, seq_to = argv[i + 1], int(argv[i + 2]), int(argv[i + 3])
        r = score_batch(log_path, seq_from, seq_to)
        print('HARD-FAIL SEVERITY SCORE -- seq %d-%d, %d entries scored'
              % (seq_from, seq_to, r['entries_scored']))
        print('GRADE: %s' % r['grade'])
        if r['downgrade_rule']:
            print(r['downgrade_rule'])
        for h in r['hardfail_hits']:
            print('  ! seq %d  categories: %s' % (h['seq'], '/'.join(h['categories'])))
        if r['unevidenced_claims']:
            print('UNEVIDENCED DONE/PASS/CONFIRMED CLAIMS (score 0 each): seq %s'
                  % ', '.join(str(s) for s in r['unevidenced_claims']))
        return 1 if r['grade'] == 'FAIL' else 0
    print('usage: hover_hardfail_severity_scorer.py --selftest | --score LOGPATH SEQ_FROM SEQ_TO')
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
