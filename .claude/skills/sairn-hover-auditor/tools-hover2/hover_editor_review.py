#!/usr/bin/env python
"""hover_editor_review.py (hover2's OWN INDEPENDENT BUILD) -- the editor
pass: mechanically re-derive a report's own checkable claims against
CURRENT source before the report is pasted.

PROVENANCE, stated precisely. H1 built the first implementation (H1 log
#527); this instance VALIDATED that implementation against a real holdout
(my seq 208) and in doing so learned its behavioral CONTRACT and one
measured precision boundary. This file is written from that contract, with
hover2's own extraction logic throughout -- per discipline 7 (a second
copy is not a second opinion) the divergences are deliberate, and one is a
direct response to the seq 208 measurement:

  DIVERGENCE (measured, not stylistic): seq 208 found H1's duration check
  pairs a stated duration with the two nearest resolvable hashes in the
  PARAGRAPH -- which false-positived on '3 minutes before this review
  commit', where the true referent is not a hash token at all. THIS build
  only measures a duration when BOTH endpoint hashes appear in the SAME
  SENTENCE as the duration phrase; anything looser is CANNOT-CHECK, said
  plainly, never a guessed pair.

CLAIM CLASSES (the contract):
  hash      every 7-40 char hex token must resolve in the repo
            (DANGLING-REF), unless the sentence itself SAYS it does not
            resolve (negation guard).
  path      every cited path must exist in worktree or git ls-files
            (MISSING-PATH), unique-basename fallback, negation guard,
            ambiguous basename -> CANNOT.
  line      every path:N[-M] citation is re-read for an anchor extracted
            from its own sentence: on the cited line(s) -> OK; within
            DRIFT_BOUND lines -> DRIFT note; farther -> LINE-MISMATCH;
            nowhere in the file -> ANCHOR-ABSENT; cited line past EOF ->
            LINE-OUT-OF-RANGE; no extractable anchor -> SHALLOW
            (line-bounds only, disclosed as weaker). Matching is
            whitespace-normalized so a spaced snippet finds unspaced
            source.
  duration  a stated 'N hours/minutes/days later|before|after' between two
            same-sentence hashes is recomputed from real commit
            timestamps; FINDING only when BOTH committer and author gaps
            disagree past tolerance max(15min, 50% of stated).

FAIL-CLOSED (PR SS1.11): git missing / not a repo -> exit 2, nothing
judged. An unreadable cited file -> CANNOT, counted and printed, never
folded into pass. Zero extractable claims -> NOTHING-TO-CHECK, not a pass.
Exit: 0 all checked claims hold; 1 findings; 2 could not run; 3 no
findings but some claims could not be checked.

BLIND LOCK (discipline 1): synthetic fixtures classify FIRST on every
invocation against a throwaway git repo built fresh; any miss refuses the
real run. CRITERIA_VERSION 2 -- v2 corrects the extension alternation
(json/jsonl before js), found on this build's FIRST real-data run when
docs/tier-a-reviews.json extracted as the phantom docs/tier-a-reviews.js
and false-flagged MISSING-PATH twice. The identical v1->v2 correction H1's
independent build needed, reproduced independently -- convergent evidence
the fixture below belongs in every implementation's lock.

Run:
  python hover_editor_review.py --report FILE [--repo PATH]
  python hover_editor_review.py --stdin [--repo PATH]
  python hover_editor_review.py --fixtures
"""
import argparse
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

CRITERIA_VERSION = 2
DRIFT_BOUND = 3                      # same derivation H1 cites: the one
                                     # measured real drift was 5; <=3 is a note
TOL_MIN_SECONDS = 15 * 60
TOL_FRACTION = 0.5

CONFLICT_MARKER_RE = re.compile(r'^(<{7}|={7}|>{7})', re.M)
HEX_RE = re.compile(r'\b[0-9a-f]{7,40}\b')
FILELINE_RE = re.compile(
    r'\b([\w./\\-]+\.(?:jsonl|json|py|html|md|sql|css|tsx|ts|js))'
    r'(?::(\d+)(?:-(\d+))?)?')
DURATION_RE = re.compile(
    r'\b(?:(\d+(?:\.\d+)?)|one|two|three|four|five|six|seven|eight|nine|ten)'
    r'\s*(hour|hr|minute|min|day)s?\s+(?:later|earlier|before|after|apart)\b',
    re.I)
WORDNUM = {'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6,
           'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10}
UNIT_SECONDS = {'hour': 3600, 'hr': 3600, 'minute': 60, 'min': 60,
                'day': 86400}
NEGATION_RE = re.compile(
    r'\b(not a valid|does not (?:resolve|exist)|no longer exists|is absent|'
    r'dangling|never existed|is NOT)\b', re.I)


def run_git(repo, *args):
    try:
        r = subprocess.run(['git'] + list(args), cwd=repo,
                           capture_output=True, text=True,
                           encoding='utf-8', errors='replace')
    except FileNotFoundError:
        return None, 'git executable not found'
    return (r.stdout.strip(), None) if r.returncode == 0 \
        else (None, r.stderr.strip())


def sentences(text):
    return [s for s in re.split(r'(?<=[.!?;])\s+|\n\s*\n', text) if s.strip()]


def squeeze(s, n=150):
    s = re.sub(r'\s+', ' ', s).strip()
    return s if len(s) <= n else s[:n - 3] + '...'


def norm_ws(s):
    return re.sub(r'\s+', '', s)


def anchor_candidates(sentence):
    """hover2's own extraction: backtick spans first (the strongest
    signal), then code-ish identifiers (letters+underscore/dot/parens,
    length >= 4, not a bare English word)."""
    cands = set(re.findall(r'`([^`]{3,80})`', sentence))
    for m in re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*(?:\(\)|_[A-Za-z0-9_]+)\b",
                        sentence):
        if len(m) >= 4:
            cands.add(m)
    for m in re.findall(r"'([^']{4,60})'", sentence):
        if not m.isspace():
            cands.add(m)
    return {c.strip() for c in cands if c.strip()}


class Review:
    def __init__(self, repo):
        self.repo = repo
        self.rows = []   # (kind, cls, detail); kind OK/DRIFT/SHALLOW/CANNOT/FINDING
        self._ls = None
        self._hashes = {}

    def row(self, kind, cls, detail):
        self.rows.append((kind, cls, detail))

    def ls_files(self):
        if self._ls is None:
            out, _ = run_git(self.repo, 'ls-files')
            self._ls = out.splitlines() if out else []
        return self._ls

    def resolve(self, tok):
        if tok not in self._hashes:
            typ, err = run_git(self.repo, 'cat-file', '-t', tok)
            if typ is None and err and 'ambiguous' in err.lower():
                typ = 'ambiguous-but-real'
            self._hashes[tok] = typ
        return self._hashes[tok]

    def commit_times(self, tok):
        out, _ = run_git(self.repo, 'log', '-1', '--format=%cI|%aI', tok)
        if not out or '|' not in out:
            return None, None
        c, a = out.split('|', 1)
        try:
            return datetime.fromisoformat(c), datetime.fromisoformat(a)
        except ValueError:
            return None, None

    def check_hash(self, tok, sent):
        typ = self.resolve(tok)
        if typ:
            self.row('OK', 'hash', '%s resolves (%s)' % (tok, typ))
        elif NEGATION_RE.search(sent):
            self.row('OK', 'hash',
                     '%s does not resolve, and the sentence SAYS so' % tok)
        else:
            self.row('FINDING', 'hash',
                     'DANGLING-REF: %s is not an object in this repo. '
                     'Sentence: %s' % (tok, squeeze(sent)))

    def resolve_path(self, path):
        p = os.path.join(self.repo, path.replace('\\', '/'))
        if os.path.isfile(p):
            return p, None
        base = os.path.basename(path.replace('\\', '/'))
        hits = [f for f in self.ls_files() if os.path.basename(f) == base]
        if len(hits) == 1:
            return os.path.join(self.repo, hits[0]), 'resolved as %s' % hits[0]
        if len(hits) > 1:
            return None, 'AMBIGUOUS: %d files named %s' % (len(hits), base)
        return None, None

    def check_fileline(self, path, l1, l2, sent):
        abspath, note = self.resolve_path(path)
        if abspath is None:
            if NEGATION_RE.search(sent):
                self.row('OK', 'path',
                         '%s absent, and the sentence SAYS so' % path)
            elif note:
                self.row('CANNOT', 'path', '%s: %s' % (path, note))
            else:
                self.row('FINDING', 'path',
                         'MISSING-PATH: %s not in worktree or ls-files. '
                         'Sentence: %s' % (path, squeeze(sent)))
            return
        if l1 is None:
            self.row('OK', 'path', path + (' (%s)' % note if note else ''))
            return
        try:
            with io.open(abspath, encoding='utf-8', errors='replace') as f:
                text = f.read()
        except OSError as e:
            self.row('CANNOT', 'line',
                     '%s:%s exists but unreadable (%s) -- NOT checked, '
                     'NOT a pass' % (path, l1, e))
            return
        if CONFLICT_MARKER_RE.search(text):
            self.row('CANNOT', 'line',
                     '%s carries unresolved git conflict markers -- a line '
                     'citation against a conflicted file is unreliable '
                     'regardless of which side happens to match. NOT '
                     'checked, NOT a pass. Sentence: %s'
                     % (path, squeeze(sent)))
            return
        lines = text.splitlines()
        lo, hi = sorted((l1, l2 or l1))
        if hi > len(lines):
            self.row('FINDING', 'line',
                     'LINE-OUT-OF-RANGE: %s:%d cited; file has %d lines. '
                     'Sentence: %s' % (path, hi, len(lines), squeeze(sent)))
            return
        own = os.path.basename(path).rsplit('.', 1)[0]
        cands = {c for c in anchor_candidates(sent)
                 if norm_ws(c) and own not in c}
        if not cands:
            self.row('SHALLOW', 'line',
                     '%s:%d line-bounds only -- no anchor extractable '
                     'from the sentence' % (path, l1))
            return
        best = None   # (distance, cand, at_line)
        for cand in cands:
            nc = norm_ws(cand)
            for i, ln in enumerate(lines, 1):
                if nc in norm_ws(ln):
                    dist = 0 if lo <= i <= hi else min(abs(i - lo),
                                                       abs(i - hi))
                    if best is None or dist < best[0]:
                        best = (dist, cand, i)
        if best is None:
            self.row('FINDING', 'line',
                     'ANCHOR-ABSENT: none of %s appear anywhere in %s '
                     '(cited :%d). Sentence: %s'
                     % (sorted(cands)[:4], path, l1, squeeze(sent)))
        elif best[0] == 0:
            self.row('OK', 'line', "%s:%d anchor '%s' on the cited line"
                     % (path, l1, best[1]))
        elif best[0] <= DRIFT_BOUND:
            self.row('DRIFT', 'line',
                     "%s:%d -> '%s' actually at :%d (drift %d, within %d)"
                     % (path, l1, best[1], best[2], best[0], DRIFT_BOUND))
        else:
            self.row('FINDING', 'line',
                     "LINE-MISMATCH: %s:%d cited for '%s' which is at :%d "
                     '(drift %d > %d). Sentence: %s'
                     % (path, l1, best[1], best[2], best[0], DRIFT_BOUND,
                        squeeze(sent)))

    def check_duration(self, m, sent, sent_hashes):
        num = m.group(1)
        stated = (float(num) if num else WORDNUM[m.group(0).split()[0].lower()]
                  ) * UNIT_SECONDS[m.group(2).lower()]
        commits = []
        for tok in sent_hashes:
            if self.resolve(tok) in ('commit', 'ambiguous-but-real'):
                if tok not in commits:
                    commits.append(tok)
        if len(commits) != 2:
            # THE seq-208 DIVERGENCE: no same-sentence pair -> say so,
            # never guess a pair from elsewhere in the paragraph.
            self.row('CANNOT', 'duration',
                     "'%s' -- %d resolvable commit(s) in the SAME sentence; "
                     'this build only measures a same-sentence pair '
                     '(measured false-positive boundary, hover2 seq 208). '
                     'NOT checked, NOT a pass.'
                     % (m.group(0), len(commits)))
            return
        ca, aa = self.commit_times(commits[0])
        cb, ab = self.commit_times(commits[1])
        if not (ca and cb):
            self.row('CANNOT', 'duration',
                     "'%s' -- could not read commit times" % m.group(0))
            return
        dc = abs((ca - cb).total_seconds())
        da = abs((aa - ab).total_seconds()) if (aa and ab) else dc
        tol = max(TOL_MIN_SECONDS, TOL_FRACTION * stated)
        if abs(dc - stated) > tol and abs(da - stated) > tol:
            self.row('FINDING', 'duration',
                     "DURATION-MISMATCH: '%s' between %s and %s, but "
                     'committer gap %s and author gap %s (tolerance %s). '
                     'Sentence: %s'
                     % (m.group(0), commits[0], commits[1], hms(dc),
                        hms(da), hms(tol), squeeze(sent)))
        else:
            self.row('OK', 'duration',
                     "'%s' vs %s..%s measured %s"
                     % (m.group(0), commits[0], commits[1], hms(dc)))

    def review_text(self, text):
        for sent in sentences(text):
            spans = []
            for fm in FILELINE_RE.finditer(sent):
                spans.append(fm.span())
                l1 = int(fm.group(2)) if fm.group(2) else None
                l2 = int(fm.group(3)) if fm.group(3) else None
                self.check_fileline(fm.group(1), l1, l2, sent)
            sent_hashes = []
            for hm in HEX_RE.finditer(sent):
                if any(a <= hm.start() < b for a, b in spans):
                    continue
                if hm.group(0).isdigit():
                    continue   # a pure number is a count, not a hash
                sent_hashes.append(hm.group(0))
                self.check_hash(hm.group(0), sent)
            for dm in DURATION_RE.finditer(sent):
                self.check_duration(dm, sent, sent_hashes)

    def counts(self):
        c = {'OK': 0, 'DRIFT': 0, 'SHALLOW': 0, 'CANNOT': 0, 'FINDING': 0}
        for kind, _c, _d in self.rows:
            c[kind] += 1
        c['claims'] = len(self.rows)
        return c


def hms(seconds):
    seconds = int(round(seconds))
    return '%dh%02dm' % (seconds // 3600, (seconds % 3600) // 60)


# --- fixtures --------------------------------------------------------------

def build_fixture_repo():
    d = tempfile.mkdtemp(prefix='editorreview-fixture-')
    env = dict(os.environ,
               GIT_AUTHOR_NAME='fx', GIT_AUTHOR_EMAIL='fx@x',
               GIT_COMMITTER_NAME='fx', GIT_COMMITTER_EMAIL='fx@x')

    def g(*args, **kw):
        e = dict(env)
        e.update(kw.get('env', {}))
        r = subprocess.run(['git'] + list(args), cwd=d, env=e,
                           capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(r.stderr.strip())
        return r.stdout.strip()

    g('init', '-q')
    with open(os.path.join(d, 'mod.py'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(['# line %d' % i for i in range(1, 20)]
                          + ['def real_anchor_fn():', '    return 1', '']))
    g('add', '.')
    g('commit', '-q', '-m', 'first',
      env={'GIT_AUTHOR_DATE': '2026-01-01T10:00:00+00:00',
           'GIT_COMMITTER_DATE': '2026-01-01T10:00:00+00:00'})
    sha1 = g('rev-parse', 'HEAD')
    with open(os.path.join(d, 'mod.py'), 'a', encoding='utf-8') as f:
        f.write('# more\n')
    g('add', '.')
    g('commit', '-q', '-m', 'second',
      env={'GIT_AUTHOR_DATE': '2026-01-01T11:00:00+00:00',
           'GIT_COMMITTER_DATE': '2026-01-01T11:00:00+00:00'})
    sha2 = g('rev-parse', 'HEAD')
    # KNOWN-BAD CONTROL MATERIAL, conflict-marker sweep, 2026-09-28.
    # Left UNCOMMITTED on purpose -- a real botched merge leaves exactly
    # this in the working tree, not in a clean commit.
    with open(os.path.join(d, 'conflicted.py'), 'w', encoding='utf-8') as f:
        f.write('<<<<<<< HEAD\n' + '\n'.join(['# x'] * 5)
               + '\ndef real_anchor_fn():\n=======\n'
               + '\n'.join(['# y'] * 5)
               + '\ndef real_anchor_fn():\n>>>>>>> branch\n')
    return d, sha1[:10], sha2[:10]


def fixtures(sha1, sha2):
    return [
        ('dangling ref flagged',
         'The fix landed in badc0ffee1 and is complete.',
         {'findings': 1}),
        ('real ref passes',
         'The fix landed in %s and is complete.' % sha1,
         {'findings': 0, 'min_claims': 1}),
        ('negated dangling ref passes',
         'Note badc0ffee1 is not a valid object in this repo.',
         {'findings': 0, 'min_claims': 1}),
        ('missing path flagged',
         'See ghost_module.py for the handler.',
         {'findings': 1}),
        ('anchor on cited line passes',
         'The guard `real_anchor_fn()` sits at mod.py:20 today.',
         {'findings': 0, 'min_claims': 1}),
        ('line mismatch past bound flagged',
         'The guard `real_anchor_fn()` sits at mod.py:3 today.',
         {'findings': 1}),
        ('anchor absent flagged',
         'The guard `never_written_fn()` sits at mod.py:5 today.',
         {'findings': 1}),
        ('line past EOF flagged',
         'The guard `real_anchor_fn()` sits at mod.py:999 today.',
         {'findings': 1}),
        ('no anchor -> shallow, not a finding',
         'It went wrong around mod.py:4 that night.',
         {'findings': 0, 'shallow': 1}),
        ('whitespace-normalized anchor found',
         'The check `return  1` sits at mod.py:21 today.',
         {'findings': 0}),
        ('true duration passes',
         'Commit %s landed one hour after %s.' % (sha2, sha1),
         {'findings': 0, 'min_claims': 3}),
        ('false duration flagged',
         'Commit %s landed four hours after %s.' % (sha2, sha1),
         {'findings': 1}),
        ('duration with one same-sentence hash -> CANNOT, never guessed',
         'It landed four hours after %s. The other work sat in %s.'
         % (sha1, sha2),
         {'findings': 0, 'cannot': 1}),
        ('.json path is not truncated to a phantom .js (v2 correction)',
         'The verdict lives in mod.json today.',
         # mod.json genuinely absent -> ONE finding naming the REAL file;
         # the v1 bug produced it for a truncated mod.js instead, so the
         # DETAIL is asserted, not just the count -- a count-only fixture
         # passed straight through the v1 bug on this build's first lock.
         {'findings': 1, 'detail_contains': 'mod.json',
          'detail_never': 'mod.js '}),
        ('nothing checkable -> zero claims',
         'A pleasant sentence with no citations at all.',
         {'findings': 0, 'zero_claims': True}),
        ('KNOWN-BAD CONTROL, conflict-marker sweep: a citation against a '
         'conflicted file is CANNOT, never a silent OK from whichever side '
         'happens to match',
         'The guard `real_anchor_fn()` sits at conflicted.py:6 today.',
         {'findings': 0, 'cannot': 1}),
    ]


def run_fixture_lock(verbose=False):
    try:
        d, sha1, sha2 = build_fixture_repo()
    except (RuntimeError, OSError) as e:
        print('COULD NOT RUN: fixture repo build failed (%s). Nothing real '
              'was judged.' % e)
        return False
    try:
        ok = True
        for name, text, exp in fixtures(sha1, sha2):
            r = Review(d)
            r.review_text(text)
            c = r.counts()
            bad = []
            if c['FINDING'] != exp.get('findings', 0):
                bad.append('findings %d != %d' % (c['FINDING'],
                                                  exp.get('findings', 0)))
            if 'shallow' in exp and c['SHALLOW'] != exp['shallow']:
                bad.append('shallow %d != %d' % (c['SHALLOW'], exp['shallow']))
            if 'cannot' in exp and c['CANNOT'] != exp['cannot']:
                bad.append('cannot %d != %d' % (c['CANNOT'], exp['cannot']))
            if c['claims'] < exp.get('min_claims', 0):
                bad.append('claims %d < %d' % (c['claims'], exp['min_claims']))
            if exp.get('zero_claims') and c['claims'] != 0:
                bad.append('expected 0 claims, got %d' % c['claims'])
            alltext = ' | '.join(det for _k, _c2, det in r.rows)
            if 'detail_contains' in exp and exp['detail_contains'] not in alltext:
                bad.append('detail lacks %r' % exp['detail_contains'])
            if 'detail_never' in exp and exp['detail_never'] in alltext:
                bad.append('detail wrongly contains %r' % exp['detail_never'])
            if bad:
                ok = False
                print('FIXTURE FAIL  %s: %s' % (name, '; '.join(bad)))
                for k, cl, det in r.rows:
                    print('    [%s %s] %s' % (k, cl, det))
            elif verbose:
                print('fixture ok    %s' % name)
        return ok
    finally:
        shutil.rmtree(d, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--report')
    ap.add_argument('--stdin', action='store_true')
    ap.add_argument('--repo', default='.')
    ap.add_argument('--fixtures', action='store_true')
    # alias per the platform's every-tool-answers---selftest convention --
    # same suite, no duplicate; the naming-convention gap seq 397 already
    # closed for claim_collision_scan.py and dependency_health_check.py
    ap.add_argument('--selftest', action='store_true', dest='fixtures')
    ap.add_argument('-v', '--verbose', action='store_true')
    a = ap.parse_args()

    print('hover_editor_review (hover2 build) CRITERIA_VERSION %d'
          % CRITERIA_VERSION)
    if not run_fixture_lock(a.verbose or a.fixtures):
        print('REFUSED: fixture lock failed -- criteria judged nothing real '
              '(exit 2).')
        return 2
    print('fixture lock: all %d fixtures classify correctly (isolated repo)'
          % len(fixtures('0' * 10, '1' * 10)))
    if a.fixtures:
        return 0
    if not a.report and not a.stdin:
        print('COULD NOT RUN: no --report/--stdin (exit 2).')
        return 2
    text = sys.stdin.read() if a.stdin else None
    if text is None:
        try:
            with io.open(a.report, encoding='utf-8', errors='replace') as f:
                text = f.read()
        except OSError as e:
            print('COULD NOT RUN: report unreadable (%s) (exit 2).' % e)
            return 2
    head, herr = run_git(a.repo, 'rev-parse', 'HEAD')
    if head is None:
        print('COULD NOT RUN: %s is not a usable git repo (%s). Nothing '
              'judged (exit 2).' % (a.repo, herr))
        return 2
    dirty, _ = run_git(a.repo, 'status', '--porcelain')
    print('VERDICTS ARE AGAINST %s AT HEAD %s%s, as of %s -- not as of the '
          "report's writing."
          % (os.path.abspath(a.repo), head[:12],
             ' (DIRTY)' if dirty else '',
             datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')))
    r = Review(a.repo)
    r.review_text(text)
    c = r.counts()
    if c['claims'] == 0:
        print('NOTHING-TO-CHECK: 0 checkable claims in %d chars. NOT a pass '
              '-- the report makes no claim this pass can re-derive.'
              % len(text))
        return 0
    order = {'FINDING': 0, 'CANNOT': 1, 'DRIFT': 2, 'SHALLOW': 3, 'OK': 4}
    for kind, cls, detail in sorted(r.rows, key=lambda t: order[t[0]]):
        if kind == 'OK' and not a.verbose:
            continue
        print('[%s %s] %s' % (kind, cls, detail))
    print('-' * 70)
    print('claims %d | held %d | drift-notes %d | shallow %d | '
          'cannot-check %d | FINDINGS %d'
          % (c['claims'], c['OK'], c['DRIFT'], c['SHALLOW'], c['CANNOT'],
             c['FINDING']))
    if c['FINDING']:
        print('VERDICT: DO NOT SHIP AS-IS -- %d claim(s) contradict current '
              'source.' % c['FINDING'])
        return 1
    if c['CANNOT']:
        print('VERDICT: PARTIAL -- no contradictions, but %d claim(s) could '
              'not be checked and are NOT passes (exit 3).' % c['CANNOT'])
        return 3
    print('VERDICT: all %d checkable claims hold against current source. '
          'Mechanism claims are NOT covered by this pass.' % c['claims'])
    return 0


if __name__ == '__main__':
    sys.exit(main())
