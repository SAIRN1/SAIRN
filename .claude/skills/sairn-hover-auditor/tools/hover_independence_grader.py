#!/usr/bin/env python
"""For each finding in a batch (a seq range of this role's own log), grades
three independence dimensions -- EVIDENCE TYPE, MUTABILITY, METHOD
SEPARATION -- each STRONG/PARTIAL/WEAK. The batch grade is the WEAKEST
single dimension across every finding graded; the report names which
dimension and which finding limited it.

Own tool, own location. Built 2026-10-06 (H1, batch J, item 5). Design
logged (seq 1006) before this file was written. Reads only this role's own
hover-audit-log.jsonl.

DIMENSIONS, EACH A TEXT-PATTERN HEURISTIC OVER THE ENTRY'S OWN SUMMARY --
INFERRED, not a structured field; named as a real limitation, same as
every other hover tool's own keyword-based classification:

  EVIDENCE TYPE: STRONG if the entry's own text contains a captured
  deterministic-result pattern (an exit code, a tool's own printed
  output). WEAK if the entry asserts a conclusion with no such pattern
  anywhere -- reading/judgment alone.

  MUTABILITY: STRONG if the entry's own text shows independent
  re-derivation language ("re-run", "re-confirmed", "independently",
  "driven live") against a git-tracked artifact. WEAK if the entry's only
  evidence is QUOTING a build agent's own claim with no independent
  re-derivation language nearby.

  METHOD SEPARATION: WEAK if the entry's own text names a build-agent tool
  path (tools/*.py, not this role's own hover_*.py) used as the leading
  verb of detection ("ran", "found via", "used"). PARTIAL if a build-agent
  tool/output is mentioned only alongside "spot-check"/"corroborat"/
  "comparison only"/"read-only". STRONG if only this role's own hover_*.py
  tools or git/grep are named.
"""
import json
import re
import sys

ORDER = {'WEAK': 0, 'PARTIAL': 1, 'STRONG': 2}

EVIDENCE_PATTERN = re.compile(r'\bEXIT\s+-?\d+\b|\bexit_code\b|\bexit\s+code\b', re.I)
MUTABILITY_STRONG = re.compile(r're-?run|re-?confirm|independent(ly)?|driven live|re-?deriv', re.I)
BUILD_AGENT_TOOL = re.compile(r'\btools/(?!capture_exit)[A-Za-z_]+\.py\b')
HOVER_OWN_TOOL = re.compile(r'\bhover_[A-Za-z_]+\.py\b')
SPOT_CHECK_HEDGE = re.compile(r'spot-?check|corroborat|comparison only|read-only (evidence|spot)', re.I)


def grade_evidence_type(text):
    return 'STRONG' if EVIDENCE_PATTERN.search(text) else 'WEAK'


def grade_mutability(text):
    return 'STRONG' if MUTABILITY_STRONG.search(text) else 'WEAK'


def grade_method_separation(text):
    build_tool = BUILD_AGENT_TOOL.search(text)
    if not build_tool:
        return 'STRONG'
    if SPOT_CHECK_HEDGE.search(text):
        return 'PARTIAL'
    return 'WEAK'


def grade_finding(entry):
    text = entry.get('summary') or ''
    return {
        'seq': entry.get('seq'),
        'evidence_type': grade_evidence_type(text),
        'mutability': grade_mutability(text),
        'method_separation': grade_method_separation(text),
    }


def grade_batch(log_path, seq_from, seq_to, finding_type_only=True):
    entries = []
    with open(log_path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            e = json.loads(line)
            if seq_from <= e.get('seq', -1) <= seq_to:
                if finding_type_only and e.get('type') != 'finding':
                    continue
                entries.append(e)
    graded = [grade_finding(e) for e in entries]
    if not graded:
        return {'graded': [], 'grade': None, 'limiting': None}
    worst = None
    worst_dim = None
    worst_seq = None
    for g in graded:
        for dim in ('evidence_type', 'mutability', 'method_separation'):
            val = g[dim]
            if worst is None or ORDER[val] < ORDER[worst]:
                worst = val
                worst_dim = dim
                worst_seq = g['seq']
    return {'graded': graded, 'grade': worst, 'limiting_dimension': worst_dim, 'limiting_seq': worst_seq}


# ---------------------------------------------------------------------------
# Selftest: a fixture with one STRONG finding (deterministic, re-run, own
# tool) and one MODEL-JUDGMENT-ONLY finding (no exit code, no re-run
# language, no tool at all) -- the second must pull the batch grade to WEAK.
# ---------------------------------------------------------------------------

def _selftest():
    import os
    import tempfile
    fixture = [
        {'seq': 1, 'type': 'finding',
         'summary': 'Re-ran hover_cross_resource_gate_check.py fresh, EXIT 1, confirms the finding independently.'},
        {'seq': 2, 'type': 'finding',
         'summary': 'This code looks wrong to me on reading it; I believe it is a real gap, though I did not run anything.'},
    ]
    fd, path = tempfile.mkstemp(suffix='.jsonl')
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        for e in fixture:
            f.write(json.dumps(e) + '\n')
    try:
        r = grade_batch(path, 1, 999)
        ok = 0
        total = 3
        g1 = next(g for g in r['graded'] if g['seq'] == 1)
        if g1['evidence_type'] == 'STRONG' and g1['method_separation'] == 'STRONG':
            ok += 1
            print('  ok   deterministic, own-tool finding grades STRONG on evidence/method')
        else:
            print('  FAIL finding 1 graded %r' % g1)
        g2 = next(g for g in r['graded'] if g['seq'] == 2)
        if g2['evidence_type'] == 'WEAK':
            ok += 1
            print('  ok   model-judgment-only finding grades WEAK on evidence type')
        else:
            print('  FAIL finding 2 evidence_type expected WEAK, got %r' % g2['evidence_type'])
        if r['grade'] == 'WEAK' and r['limiting_seq'] == 2:
            ok += 1
            print('  ok   batch grade pulled down to WEAK by finding 2, named as the limiter')
        else:
            print('  FAIL batch grade expected WEAK/seq2, got %r' % r)
        print('%d/%d fixture checks correct' % (ok, total))
        return ok == total
    finally:
        os.remove(path)


def main(argv):
    if '--selftest' in argv:
        return 0 if _selftest() else 1
    if '--grade' in argv:
        i = argv.index('--grade')
        log_path, seq_from, seq_to = argv[i + 1], int(argv[i + 2]), int(argv[i + 3])
        r = grade_batch(log_path, seq_from, seq_to)
        print('INDEPENDENCE GRADE -- seq %d-%d, %d finding(s) graded' % (seq_from, seq_to, len(r['graded'])))
        for g in r['graded']:
            print('  seq %d: evidence=%s mutability=%s method=%s'
                  % (g['seq'], g['evidence_type'], g['mutability'], g['method_separation']))
        print('BATCH GRADE: %s (limited by seq %s, dimension %s)'
              % (r['grade'], r['limiting_seq'], r['limiting_dimension']))
        return 0 if r['grade'] == 'STRONG' else 1
    print('usage: hover_independence_grader.py --selftest | --grade LOGPATH SEQ_FROM SEQ_TO')
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
