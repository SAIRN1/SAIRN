#!/usr/bin/env python
"""citation_class_check.py -- three honest classes for every cited claim in
this append-only log, because "correct when written, moved later" and
"wrong when written" look identical in a plain HEAD re-derivation
(2026-09-29, built from the memory-vs-derived sweep's own confusion).

Per explicit path:line citation in an entry's summary:
  WRONG-AT-DERIVATION  the anchor fails against the blob the entry's OWN
                       source_shas recorded -- a defect in this record.
  MOVED-SINCE          holds at the recorded sha, fails at HEAD -- honest
                       history that the world outgrew.
  NOT-A-REPO-PATH      the cited path is not in the platform repo (tool
                       dir files, user-store paths) -- out of scope here.
  UNVERIFIABLE-NO-SHA  the entry recorded no source sha for that file --
                       named, never folded into any of the above.
  HOLDS                anchor found within tolerance at both.

Anchor rule reused from hover_editor_review_criteria (same candidates,
same whitespace-normalized compare, same LINE_DRIFT_FINDING window) so
this tool and the editor pass cannot disagree about what a citation means.

Fixtures: one planted entry per class against a REAL throwaway git repo
(the moved-since plant is moved by a REAL commit), plus the KNOWN-BAD
CONTROL this build was asked for: a deliberately broken classifier that
skips the at-derivation check MUST misread the moved-since plant as
wrong-at-derivation, and the fixture asserts the REAL classifier does not.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hover_editor_review_criteria as C  # noqa: E402

LOG = os.path.join(HERE, 'hover-audit-log.jsonl')
REPO = os.path.join(os.path.expanduser('~'), 'Documents', 'SAIRN-hover')

FILELINE = re.compile(
    r'(?<![\w/])((?:[\w.-]+/)*[\w.-]+\.(?:py|js|html|md|sql|json)):(\d{2,6})\b')


def blob_lines(repo, sha, path):
    """hover_log's source_shas record BLOB shas (git cat-file -p reads
    them directly; `git show sha:path` only works for COMMIT shas). Found
    on this tool's own first real run: reading blobs as commits failed
    EVERY derivation check and mis-filed 233 citations as
    WRONG-AT-DERIVATION with zero MOVED-SINCE -- exactly the
    misclassification the known-bad control models, arriving through a
    sha-TYPE door the fixtures had not covered. Both types now read; both
    now covered in fixtures."""
    t = subprocess.run(['git', 'cat-file', '-t', sha], cwd=repo,
                       capture_output=True, text=True)
    kind = t.stdout.strip() if t.returncode == 0 else None
    if kind == 'blob':
        r = subprocess.run(['git', 'cat-file', '-p', sha], cwd=repo,
                           capture_output=True, text=True, encoding='utf-8',
                           errors='replace')
    elif kind == 'commit':
        r = subprocess.run(['git', 'show', '%s:%s' % (sha, path)], cwd=repo,
                           capture_output=True, text=True, encoding='utf-8',
                           errors='replace')
    else:
        return None
    if r.returncode != 0:
        return None
    return r.stdout.splitlines()


def head_lines(repo, path):
    p = os.path.join(repo, path)
    if not os.path.isfile(p):
        return None
    return open(p, encoding='utf-8', errors='replace').read().splitlines()


def anchor_ok(lines, lineno, sentence, path='', window=C.LINE_DRIFT_FINDING):
    if lines is None or lineno > len(lines):
        return False
    # The cited file's OWN name-stem is excluded as an anchor -- the same
    # rule hover_editor_review.check_fileline applies (own_stem) and for
    # the same reason: 'docs/CRITICALITY-TIERS.md:407.' extracts only
    # 'CRITICALITY-TIERS' as a candidate, register rows never contain
    # their own filename, and keeping it turned every bare register-row
    # citation into a false WRONG (found spot-checking seq 459 on the
    # first fixed-blob run). No candidates left -> bounds-only, holds.
    stem = os.path.basename(path).rsplit('.', 1)[0] if path else ''
    cands = {c for c in C.anchor_candidates(sentence) if c != stem}
    if not cands:
        return True   # nothing to anchor on: bounds-only, counts as holding
    lo, hi = max(1, lineno - window), min(len(lines), lineno + window)
    for i in range(lo, hi + 1):
        for c in cands:
            if C.anchor_in_line(c, lines[i - 1]):
                return True
    return False


def classify(entry, repo=REPO, skip_derivation=False):
    """[(path, line, cls)] for every explicit citation in the summary.
    skip_derivation exists ONLY for the known-bad control -- it is the
    deliberately broken classifier that never consults source_shas."""
    out = []
    s = entry.get('summary', '')
    shas = entry.get('source_shas') or {}
    for para in s.split('\n'):
        for sent in re.split(r'(?<=[.!?])\*{0,2}\s+', para):
            for m in FILELINE.finditer(sent):
                path, line = m.group(1), int(m.group(2))
                tracked = subprocess.run(
                    ['git', 'ls-files', '--error-unmatch', path], cwd=repo,
                    capture_output=True).returncode == 0
                if not tracked and not os.path.isfile(os.path.join(repo, path)):
                    out.append((path, line, 'NOT-A-REPO-PATH'))
                    continue
                at_head = anchor_ok(head_lines(repo, path), line, sent, path)
                if at_head:
                    out.append((path, line, 'HOLDS'))
                    continue
                rec = shas.get(path)
                if skip_derivation or not rec or not rec.get('sha'):
                    out.append((path, line,
                                'WRONG-AT-DERIVATION' if skip_derivation
                                else 'UNVERIFIABLE-NO-SHA'))
                    continue
                at_der = anchor_ok(blob_lines(repo, rec['sha'], path), line, sent, path)
                out.append((path, line,
                            'MOVED-SINCE' if at_der else 'WRONG-AT-DERIVATION'))
    return out


def stamp_line(counts):
    """One line for the report headers the list-printing tools stamp."""
    return ('[citation-classes] HOLDS %d | MOVED-SINCE %d | '
            'WRONG-AT-DERIVATION %d | NOT-A-REPO-PATH %d | NO-SHA %d'
            % (counts.get('HOLDS', 0), counts.get('MOVED-SINCE', 0),
               counts.get('WRONG-AT-DERIVATION', 0),
               counts.get('NOT-A-REPO-PATH', 0),
               counts.get('UNVERIFIABLE-NO-SHA', 0)))


def _fixtures():
    ok = [0]
    bad = [0]

    def ck(name, cond):
        (ok if cond else bad)[0] += 1
        print('  %s %s' % ('ok  ' if cond else 'FAIL', name))

    d = tempfile.mkdtemp(prefix='citation_class_fx_')
    try:
        def g(*a):
            subprocess.run(['git'] + list(a), cwd=d, capture_output=True,
                           check=True,
                           env=dict(os.environ, GIT_AUTHOR_NAME='fx',
                                    GIT_AUTHOR_EMAIL='f@x',
                                    GIT_COMMITTER_NAME='fx',
                                    GIT_COMMITTER_EMAIL='f@x'))
        g('init', '-q')
        body = ['# pad'] * 9 + ['def frobnicate():', '    return 1'] + ['# t'] * 5
        open(os.path.join(d, 'app.py'), 'w').write('\n'.join(body) + '\n')
        g('add', '-A'); g('commit', '-q', '-m', 'v1')
        sha1 = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=d,
                              capture_output=True, text=True).stdout.strip()
        # a REAL later commit shifts frobnicate from :10 to :15
        open(os.path.join(d, 'app.py'), 'w').write(
            '\n'.join(['# new'] * 5 + body) + '\n')
        g('add', '-A'); g('commit', '-q', '-m', 'v2 shifts by 5')

        # the BLOB sha for v1's app.py -- the type hover_log actually
        # records -- exercised alongside the commit-sha form below.
        blob1 = subprocess.run(['git', 'rev-parse', sha1 + ':app.py'],
                               cwd=d, capture_output=True,
                               text=True).stdout.strip()
        moved = {'summary': '`frobnicate` sits at app.py:10 today.',
                 'source_shas': {'app.py': {'sha': sha1}}}
        moved_blob = {'summary': '`frobnicate` sits at app.py:10 today.',
                      'source_shas': {'app.py': {'sha': blob1}}}
        # :99 -- out of bounds at BOTH the recorded sha and HEAD (the
        # FILELINE extractor requires >=2 digits, so a single-digit plant
        # would silently not extract at all -- caught on first run).
        wrong = {'summary': '`frobnicate` sits at app.py:99 today.',
                 'source_shas': {'app.py': {'sha': sha1}}}
        notrepo = {'summary': '`frobnicate` sits at nowhere/else.py:10 today.',
                   'source_shas': {}}
        holds = {'summary': '`frobnicate` sits at app.py:15 today.',
                 'source_shas': {'app.py': {'sha': sha1}}}

        ck('MOVED-SINCE plant classifies MOVED-SINCE (correct at its own '
           'sha, drifted at HEAD by a REAL commit)',
           classify(moved, repo=d)[0][2] == 'MOVED-SINCE')
        ck('MOVED-SINCE holds with a BLOB sha too -- the type hover_log '
           'actually records (the real-run bug: blobs read as commits '
           'failed every derivation check)',
           classify(moved_blob, repo=d)[0][2] == 'MOVED-SINCE')
        ck('WRONG-AT-DERIVATION plant classifies WRONG-AT-DERIVATION '
           '(fails even against its own recorded sha)',
           classify(wrong, repo=d)[0][2] == 'WRONG-AT-DERIVATION')
        ck('NOT-A-REPO-PATH plant classifies NOT-A-REPO-PATH',
           classify(notrepo, repo=d)[0][2] == 'NOT-A-REPO-PATH')
        ck('a citation that still holds at HEAD classifies HOLDS',
           classify(holds, repo=d)[0][2] == 'HOLDS')
        ck('KNOWN-BAD CONTROL: the BROKEN classifier (derivation check '
           'skipped) MISREADS the moved-since plant as wrong-at-derivation '
           '-- proving the derivation check is the load-bearing difference',
           classify(moved, repo=d, skip_derivation=True)[0][2]
           == 'WRONG-AT-DERIVATION')
        ck('...and the REAL classifier does NOT make that misread on the '
           'same plant', classify(moved, repo=d)[0][2] != 'WRONG-AT-DERIVATION')
    finally:
        shutil.rmtree(d, ignore_errors=True)
    print('%d ok, %d failed' % (ok[0], bad[0]))
    return bad[0] == 0


def main(argv):
    if '--selftest' in argv:
        return 0 if _fixtures() else 1
    if not _fixtures():
        print('REFUSED: fixtures failed -- nothing real was classified.')
        return 2
    counts = {}
    per_entry_wrong = {}
    with open(LOG, encoding='utf-8') as f:
        for line in f:
            e = json.loads(line)
            for path, ln, cls in classify(e):
                counts[cls] = counts.get(cls, 0) + 1
                if cls == 'WRONG-AT-DERIVATION':
                    per_entry_wrong.setdefault(e['seq'], []).append(
                        '%s:%d' % (path, ln))
    print(stamp_line(counts))
    if per_entry_wrong:
        print('WRONG-AT-DERIVATION entries (defects in this record):')
        for seq in sorted(per_entry_wrong):
            print('  seq %d: %s' % (seq, ', '.join(per_entry_wrong[seq][:6])))
    else:
        print('no WRONG-AT-DERIVATION citations anywhere in the log.')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
