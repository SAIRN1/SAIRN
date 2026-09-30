#!/usr/bin/env python
"""run_memory_vs_derived_sweep.py -- entries #600+ re-derived at HEAD.

The failure mode (2026-09-29): a count, line number or sha QUOTED from an
earlier entry or from memory instead of derived in the writing turn. This
drives every explicit path:line citation, sha and duration claim in each
entry's summary through hover_editor_review.py against the CURRENT platform
worktree, one run per entry, and reports every claim that no longer holds,
by seq. (Bare implied `:NNNN` citations got their own per-candidate-file
pass at log #682 and are per-file ambiguous in multi-file entries -- they
are deliberately OUT of this sweep's scope, stated rather than silently
half-covered.)

PLANTED KNOWN-BAD CONTROL, run first: a synthetic draft quoting a REAL
function at a DRIFTED line number must come back FINDING, or the sweep
refuses to conclude anything (exit 2).

A FLAG IS NOT A VERDICT: a flagged claim may be QUOTED HISTORY that was
correct at its own date (the log is append-only and truthful per-date).
The output is the worklist for a human read, seq by seq.
"""
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, 'hover-audit-log.jsonl')
REPO = os.path.join(os.path.expanduser('~'), 'Documents', 'SAIRN-hover')
REVIEW = os.path.join(HERE, 'hover_editor_review.py')

FILELINE = re.compile(r'[\w.-]+\.(?:py|js|html|md|sql|json):\d{2,6}\b')
HEXTOK = re.compile(r'\b[0-9a-f]{7,40}\b')


def entries_from(seq_min):
    out = []
    with open(LOG, encoding='utf-8') as f:
        for line in f:
            d = json.loads(line)
            if d.get('seq', 0) >= seq_min:
                out.append(d)
    return out


def review(text):
    with tempfile.NamedTemporaryFile('w', suffix='.txt', delete=False,
                                      encoding='utf-8') as f:
        f.write(text)
        p = f.name
    try:
        r = subprocess.run([sys.executable, REVIEW, '--report', p,
                            '--repo', REPO],
                           capture_output=True, text=True, timeout=120)
        return r.stdout
    finally:
        os.unlink(p)


def findings_in(out):
    return [l.strip() for l in out.splitlines()
            if l.strip().startswith('[FINDING')]


def main():
    # ── control first ───────────────────────────────────────────────────────
    ctl = review('The linter helper `is_field_list` sits at '
                 'hover_editor_review_criteria.py:5.')
    # is_field_list exists in that file but NOT at line 5 -- a planted,
    # deliberately drifted quote of a real symbol.
    if not any('is_field_list' in f or 'LINE-MISMATCH' in f or
               'ANCHOR-ABSENT' in f for f in findings_in(ctl)):
        print('CONTROL FAILED: the planted drifted citation was not flagged. '
              'Nothing below can be trusted.')
        return 2
    print('control: planted drifted line number IS flagged -- sweep has teeth')
    # Three-class header (2026-09-29): the classes live in
    # citation_class_check.py; its stamp line prints here so every
    # flagged row below is read against the class split, never as a
    # flat defect list.
    try:
        import citation_class_check as _ccc
        print('[citation-classes] see citation_class_check.py -- only '
              'WRONG-AT-DERIVATION rows are defects in this record; '
              'MOVED-SINCE is honest history; NOT-A-REPO-PATH is tool scope.')
    except Exception as _e:
        print('[citation-classes] classifier unavailable: %s' % _e)

    hits = {}
    checked = 0
    universe = 0
    for e in entries_from(600):
        s = e.get('summary', '')
        if not (FILELINE.search(s) or
                any(any(c.isdigit() for c in t) and any(c in 'abcdef' for c in t)
                    for t in HEXTOK.findall(s))):
            continue
        universe += 1
        out = review(s)
        checked += 1
        fs = findings_in(out)
        if fs:
            hits[e['seq']] = fs
    print('universe (entries #600+ with explicit citations/shas): %d, '
          'driven: %d' % (universe, checked))
    if hits:
        print('%d entr(ies) with claims that do not hold at current HEAD:'
              % len(hits))
        for seq in sorted(hits):
            print('  seq %d:' % seq)
            for f in hits[seq][:4]:
                print('    %s' % f[:220])
    else:
        print('every explicit citation in #600+ still holds at HEAD.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
