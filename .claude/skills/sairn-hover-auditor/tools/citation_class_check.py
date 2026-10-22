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


# ── ABBREVIATION-SAFE SENTENCE SPLIT, h1 b55 ────────────────────────────────
# Found 2026-10-19 after THREE occurrences of the same symptom logged as a
# citation-guard refusal (h1 b53, b54, b55) and worked around each time by
# rephrasing rather than root-caused. The real cause: the plain
# `re.split(r'(?<=[.!?])\*{0,2}\s+', para)` split treats ANY period as a
# sentence end, including an abbreviation's -- "the Federal Reserve Bank's
# FRED/St. Louis Fed API" split mid-phrase at "St.", discarding the half of
# the sentence that carried the real anchor text and leaving only the two
# cited files' OWN names as anchor candidates. anchor_ok() in
# hover_editor_review_criteria deliberately excludes a citation's own file
# stem from its candidate set -- so with two different-file citations
# stranded in a fragment whose only candidates are each other's filenames,
# BOTH were guaranteed to fail: each citation's only remaining candidate is
# the OTHER file's name, which never appears near the correct line in the
# wrong file. Not a cross-file line-binding bug; a sentence-boundary false
# split that only shows symptoms when it strands two different-file
# citations together. A short, explicit list -- not a general abbreviation
# detector -- because the real cases seen are all this shape.
_ABBREV_TAILS = ('st', 'mr', 'mrs', 'ms', 'dr', 'prof', 'vs', 'etc', 'eg',
                  'ie', 'inc', 'ltd', 'corp', 'jr', 'sr', 'no', 'approx',
                  'u.s', 'co')


def _ends_with_abbreviation(fragment):
    """True if `fragment` ends right after a token from _ABBREV_TAILS
    followed by the period the split just broke on (the period itself was
    already consumed by the split, so the fragment ends in the bare word)."""
    tail = fragment.rstrip()
    if not tail:
        return False
    word = re.split(r'[\s(]', tail)[-1].rstrip('.').lower()
    return word in _ABBREV_TAILS


def split_sentences(para):
    """The shared, abbreviation-safe replacement for the bare
    `re.split(r'(?<=[.!?])\\*{0,2}\\s+', para)` call. Splits exactly where
    the bare regex would, then merges a fragment back into the next one
    whenever the split point was immediately after a known abbreviation --
    the one and only correction, so every other boundary (including the
    bolded-period case F22 already locks) behaves identically to before."""
    raw = re.split(r'(?<=[.!?])\*{0,2}\s+', para)
    if len(raw) <= 1:
        return raw
    out = []
    for part in raw:
        if out and _ends_with_abbreviation(out[-1]):
            out[-1] = out[-1] + ' ' + part
        else:
            out.append(part)
    return out


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


def _sentence_stems(sentence):
    """Name-stems of EVERY file cited in the sentence. A filename fragment
    is never a content anchor -- not for its own file (the seq-459 lesson)
    and not for a DIFFERENT file cited in the same sentence: seq 615's
    'locations (docs/CRITICALITY-TIERS.md:177 ... api/sd-data.js:2742'
    left 'CRITICALITY-TIERS' as the only candidate for the sd-data
    citation, which can never appear there, and a citation that was
    EXACTLY RIGHT at derivation read as WRONG (found deep-diving the
    2026-09-30 adjudication family 609/615/621/633/655/719)."""
    return {os.path.basename(p).rsplit('.', 1)[0]
            for p in re.findall(r'((?:[\w.-]+/)*[\w.-]+)\.'
                                r'(?:py|js|html|md|sql|json):', sentence)}


_WSRUN = re.compile(r'\s+')

# The four 2026-09-30 TOOL-NOISE shapes (28-row adjudication: every
# residual WRONG was a correct citation the anchor machinery could not
# see). Fixed locally -- the shared criteria module keeps its stricter
# rules for the editor pass; these widenings only ever turn a false WRONG
# into a match, never the reverse.
# NO whitespace around the colon, deliberately: `complete:false` is the
# code shape this extracts; "FILE: sairnlegacy" and every other prose
# label is not a candidate (first cut matched those and poisoned 13
# previously bounds-only citations -- caught on the same-day rerun).
COLON_TOKEN = re.compile(r'\b([A-Za-z_]\w*:[A-Za-z_]\w*)\b')
QUOTED_PROSE = re.compile(
    r'["“]([^"”]{15,120})["”]'
    r"|(?<![\w])'([^']{15,120})'(?![\w])")


def _cands(sentence, path='', pos=None):
    """C.anchor_candidates plus the two extraction gaps: `key:value`
    tokens (complete:false -- code-shaped, whitespace-normalized by
    anchor_in_line) and long quoted prose spans (a verbatim quote is a
    deliberate claim, unlike plain English words). `pos` is this
    citation's own character offset in the sentence: a quoted span
    attaches ONLY to its nearest citation, because a sentence-global
    quote poisoned the OTHER citations in multi-cite sentences the same
    way filename stems once did (seq 621's register quote read the
    sd-data citation WRONG)."""
    stems = _sentence_stems(sentence) | (
        {os.path.basename(path).rsplit('.', 1)[0]} if path else set())
    cands = {c for c in C.anchor_candidates(sentence) if c not in stems}
    for m in COLON_TOKEN.finditer(sentence):
        cands.add(m.group(1))
    cite_positions = [mm.start() for mm in FILELINE.finditer(sentence)]
    for m in QUOTED_PROSE.finditer(sentence):
        q = (m.group(1) or m.group(2) or '').strip()
        if not (' ' in q and any(c.isalpha() for c in q)):
            continue
        if pos is not None and len(cite_positions) > 1:
            # distance to the quote's START, not its midpoint: the
            # canonical shape is 'comment (path:N) states: "quote"', and
            # a long quote's midpoint drifts toward the NEXT citation
            # (seq 702 regressed on exactly that before this changed).
            nearest = min(cite_positions, key=lambda p: abs(p - m.start()))
            if nearest != pos:
                continue
        cands.add(q)
    return cands


def _prose_norm(s):
    """Verbatim-quote compare form: quote characters unified, whitespace
    collapsed, case folded -- a transcribed quote legitimately shifts
    case at sentence boundaries and swaps quote styles."""
    for a, b in (('“', "'"), ('”', "'"), ('‘', "'"),
                 ('’', "'"), ('"', "'")):
        s = s.replace(a, b)
    return _WSRUN.sub(' ', s).casefold()


def _anchor_in_line(cand, line):
    """C.anchor_in_line plus two narrow widenings: (a) an ALL-CAPS
    underscore mention (SV_STAFF) matches its lowercase form -- register
    rows are lowercase, prose mentions are often shouted; (b) an
    app-prefixed name (scp_widget) matches the backtick-wrapped
    unprefixed register row (`widget`) -- backtick-bound so code files
    cannot alias-match on a bare common word."""
    if C.anchor_in_line(cand, line):
        return True
    if '_' in cand and cand.replace('_', '').isupper():
        if C.anchor_in_line(cand.lower(), line.lower()):
            return True
    if '_' in cand:
        alias = cand.split('_', 1)[1]
        if len(alias) >= 5 and ('`%s`' % alias) in line:
            return True
    # key:value tokens -- ':' is not in the criteria module's code-char
    # set, so its whitespace-normalized branch never fires for them.
    if ':' in cand and _WSRUN.sub('', cand) in _WSRUN.sub('', line):
        return True
    # verbatim prose quotes: case-folded, quote-unified compare.
    if ' ' in cand and len(cand) >= 15:
        if _prose_norm(cand) in _prose_norm(line):
            return True
    return False


_COMMENT_LEAD = re.compile(r'^\s*(?://|#|\*)\s?')


def anchor_ok(lines, lineno, sentence, path='', window=C.LINE_DRIFT_FINDING,
              pos=None):
    if lines is None or lineno > len(lines):
        return False
    cands = _cands(sentence, path, pos)
    if not cands:
        return True   # nothing to anchor on: bounds-only, counts as holding
    lo, hi = max(1, lineno - window), min(len(lines), lineno + window)
    for i in range(lo, hi + 1):
        for c in cands:
            if _anchor_in_line(c, lines[i - 1]):
                return True
    # multi-line quoted prose: a verbatim quote that crosses a line break
    # (a wrapped comment) never matches any single line -- compare the
    # whitespace-normalized joined window instead.
    joined = _prose_norm(' '.join(
        _COMMENT_LEAD.sub('', l) for l in lines[lo - 1:hi]))
    for c in cands:
        if len(c) >= 15 and ' ' in c and _prose_norm(c) in joined:
            return True
    return False


def best_line_at(lines, sentence, path='', near=None, pos=None):
    """Whole-file anchor search (the editor's best-match idea): the line
    the anchors actually sit at, or None. `near` (the cited line) picks
    the occurrence NEAREST it -- first-match was a real adjudication bug
    (2026-09-29): `saveIrrSched` first occurs in an onclick attribute
    around line 820, so a citation of the function body at :3979 measured
    'nearest anchor' 3000+ lines away and a genuine 5-line def-vs-use
    near-miss fell through to WRONG-AT-DERIVATION."""
    if lines is None:
        return None
    cands = _cands(sentence, path, pos)
    if not cands:
        return None
    best = None
    for i, ln in enumerate(lines, 1):
        for c in cands:
            if _anchor_in_line(c, ln):
                if near is None:
                    return i
                if best is None or abs(i - near) < abs(best - near):
                    best = i
                break
    return best


_TS_COMMIT_CACHE = {}
_TS_BLOB_CACHE = {}


# RANGE_LOOKBACK, ADDED 2026-09-30 (#742, TS-DERIVED-RANGE-MOVED): 8
# commits before AND after the ts-resolved commit, on THIS path only --
# reasoned from real measurement, not picked in the abstract. api/sd-
# data.js (the busiest file in the TS-WRONG bucket) drew a median of ~8
# commits/day, 7-day window, at the time this was written; 8 commits on
# either side of the ts-resolved point covers roughly one real working
# day of drift on the platform's busiest file, the same reasoned-from-
# diagnosis-data discipline SKILL.md's own FRESHNESS_FLOOR constant uses.
RANGE_LOOKBACK = 8
_TS_RANGE_CACHE = {}


def ts_lines_range(repo, ts, path):
    """[(commit, lines)] for up to RANGE_LOOKBACK commits before AND
    after the ts-resolved commit that actually TOUCH `path` -- never
    a blind commit-count walk across the whole repo, which would mostly
    return copies identical to the resolved commit and prove nothing.
    Empty list if ts_lines() itself cannot resolve a starting commit."""
    base = None
    key = (repo, ts)
    if key in _TS_COMMIT_CACHE:
        base = _TS_COMMIT_CACHE[key]
    if not base:
        ts_lines(repo, ts, path)  # populate the cache as a side effect
        base = _TS_COMMIT_CACHE.get(key)
    if not base:
        return []
    rkey = (repo, base, path)
    if rkey in _TS_RANGE_CACHE:
        return _TS_RANGE_CACHE[rkey]
    r = subprocess.run(
        ['git', 'log', '--format=%H',
         '--before=%s^{commit}' % base, '-n', str(RANGE_LOOKBACK + 1),
         'HEAD', '--', path],
        cwd=repo, capture_output=True, text=True)
    before = [c for c in r.stdout.split() if c]
    r2 = subprocess.run(
        ['git', 'log', '--format=%H', '--reverse',
         '--after=%s^{commit}' % base, '-n', str(RANGE_LOOKBACK),
         'HEAD', '--', path],
        cwd=repo, capture_output=True, text=True)
    after = [c for c in r2.stdout.split() if c]
    out = []
    for c in before + after:
        if c == base:
            continue
        r3 = subprocess.run(['git', 'show', '%s:%s' % (c, path)],
                            cwd=repo, capture_output=True, text=True,
                            encoding='utf-8', errors='replace')
        if r3.returncode == 0:
            out.append((c, r3.stdout.splitlines()))
    _TS_RANGE_CACHE[rkey] = out
    return out


def ts_lines(repo, ts, path):
    """Lines of `path` in the last commit at or before `ts` -- the
    TS-DERIVED fallback for entries that recorded no source sha. A
    timestamp resolves the TREE on the current branch at that moment; it
    is NOT what the writer actually read (their clone may have lagged),
    so every verdict derived this way carries the TS- prefix and never
    joins a sha-verified count. Returns None (never a guess) when no
    commit predates ts or the path is absent there."""
    if not ts:
        return None
    key = (repo, ts)
    if key not in _TS_COMMIT_CACHE:
        r = subprocess.run(['git', 'rev-list', '-1', '--before=' + ts,
                            'HEAD'], cwd=repo, capture_output=True,
                           text=True)
        _TS_COMMIT_CACHE[key] = (r.stdout.strip()
                                 if r.returncode == 0 else '')
    commit = _TS_COMMIT_CACHE[key]
    if not commit:
        return None
    bkey = (commit, path)
    if bkey not in _TS_BLOB_CACHE:
        r = subprocess.run(['git', 'show', '%s:%s' % (commit, path)],
                           cwd=repo, capture_output=True, text=True,
                           encoding='utf-8', errors='replace')
        _TS_BLOB_CACHE[bkey] = (r.stdout.splitlines()
                                if r.returncode == 0 else None)
    return _TS_BLOB_CACHE[bkey]


# QUOTED-CLAIM markers (2026-09-29, item-1 adjudication shape): a sentence
# whose syntax REPORTS another document's assertion is quoting, not
# asserting -- 'the cell cites :7164', 'the note says', 'this row said'.
# Deliberately narrow verb list; a plain citation never matches.
QUOTE_MARKERS = re.compile(
    r"\b(cite[sd]?|cell (say|said|read)s?|note (say|read)s?|"
    r"comment (say|read)s?|row (say|said)s?|used to (say|cite|read)|"
    r"previously (said|cited|read)|old cell|the original citation|"
    r"text state[sd]?s?|evidence (say|said)s?|"
    r"quoted|quoting|verbatim)\b", re.IGNORECASE)


SHA_PREFIX = re.compile(r'([0-9a-f]{7,40}):\Z')


def _marker_claims(sentence, pos):
    """A reporting marker claims THIS citation only within a short window
    -- 'the cell cites :N', 'path:N ... evidence says X' -- never from
    across the sentence (queue-3 item 4: seqs 515/518/623 were assertion
    citations flagged by a verb about a different clause). 80 chars
    before the citation (a quoted span often sits between 'states' and
    the cite), 60 after."""
    for m in QUOTE_MARKERS.finditer(sentence):
        if m.end() <= pos and pos - m.end() <= 80:
            return True
        if m.start() >= pos and m.start() - pos <= 60:
            return True
    return False


def classify(entry, repo=REPO, skip_derivation=False, detail=False):
    """[(path, line, cls)] -- or with detail=True,
    [(path, line, cls, sentence, head_best_line)] -- for every explicit
    citation in the summary. skip_derivation exists ONLY for the known-bad
    control -- it is the deliberately broken classifier that never
    consults source_shas."""
    out = []
    s = entry.get('summary', '')
    shas = entry.get('source_shas') or {}
    for para in s.split('\n'):
        for sent in split_sentences(para):
            for m in FILELINE.finditer(sent):
                path, line = m.group(1), int(m.group(2))
                # BLOB-PINNED (queue-3 item 3, seq 635): a sha-prefixed
                # citation (885fd0b9:path:line) claims THAT blob's
                # content -- measured against the NAMED blob only, never
                # the entry's own source sha and never HEAD.
                pref = SHA_PREFIX.search(sent[:m.start()])
                if pref and not skip_derivation:
                    pl = blob_lines(repo, pref.group(1), path)
                    if pl is None:
                        cls = 'BLOB-PINNED-UNRESOLVED'
                    elif anchor_ok(pl, line, sent, path, pos=m.start()):
                        cls = 'BLOB-PINNED'
                    else:
                        cls = 'BLOB-PINNED-WRONG'
                    out.append((path, line, cls, sent, None)
                               if detail else (path, line, cls))
                    continue
                tracked = subprocess.run(
                    ['git', 'ls-files', '--error-unmatch', path], cwd=repo,
                    capture_output=True).returncode == 0
                if not tracked and not os.path.isfile(os.path.join(repo, path)):
                    out.append((path, line, 'NOT-A-REPO-PATH', sent, None)
                               if detail else (path, line, 'NOT-A-REPO-PATH'))
                    continue
                hl = head_lines(repo, path)
                at_head = anchor_ok(hl, line, sent, path, pos=m.start())
                emit = (lambda cls, _p=m.start(): out.append(
                    (path, line, cls, sent,
                     best_line_at(hl, sent, path, line, pos=_p))
                    if detail else (path, line, cls)))
                if at_head:
                    emit('HOLDS')
                    continue
                rec = shas.get(path)
                if skip_derivation:
                    emit('WRONG-AT-DERIVATION')
                    continue
                if not rec or not rec.get('sha'):
                    # TS-DERIVED fallback (2026-09-30): no recorded sha,
                    # so derive the tree at the entry's own timestamp.
                    # Separate TS- verdicts, never the sha-verified ones.
                    tl = ts_lines(repo, entry.get('ts'), path)
                    if tl is None:
                        emit('UNVERIFIABLE-NO-SHA')
                        continue
                    if anchor_ok(tl, line, sent, path, pos=m.start()):
                        emit('TS-DERIVED-MOVED')
                        continue
                    if _marker_claims(sent, m.start()):
                        emit('TS-DERIVED-QUOTED')
                        continue
                    near = best_line_at(tl, sent, path, line, pos=m.start())
                    if near is not None and abs(near - line) <= 10:
                        emit('TS-DERIVED-NEAR-MISS')
                        continue
                    # TS-DERIVED-RANGE-MOVED (#742): before calling this a
                    # flat WRONG, check whether the citation anchors at
                    # ANY nearby commit that also touched this path -- a
                    # single ts-resolved point cannot distinguish "wrong
                    # from the start" from "correct then, drifted before
                    # the exact snapshot landed". A range match is weaker
                    # evidence than a real sha (still no pinned moment)
                    # but strictly stronger than a flat miss -- its own
                    # honestly-named class, never folded into either
                    # TS-DERIVED-MOVED or TS-DERIVED-WRONG.
                    for _c, rl in ts_lines_range(repo, entry.get('ts'), path):
                        if anchor_ok(rl, line, sent, path, pos=m.start()):
                            emit('TS-DERIVED-RANGE-MOVED')
                            break
                    else:
                        emit('TS-DERIVED-WRONG')
                    continue
                dl = blob_lines(repo, rec['sha'], path)
                at_der = anchor_ok(dl, line, sent, path, pos=m.start())
                if at_der:
                    emit('MOVED-SINCE')
                    continue
                # ── the two TOOL-NOISE shapes the 54-row adjudication ──
                # named (2026-09-29), now classes of their own:
                # QUOTED-CLAIM -- the sentence's own syntax reports another
                # document's assertion; the citation restates a claim, it
                # does not assert current code.
                if _marker_claims(sent, m.start()):
                    emit('QUOTED-CLAIM')
                    continue
                # NEAR-MISS -- the anchor exists at derivation within a
                # wider band (<=10 lines): the citation named a write/use
                # line while the anchor matched the def line nearby. Not
                # wrong, imprecise; measured, never guessed.
                near = best_line_at(dl, sent, path, line, pos=m.start())
                if near is not None and abs(near - line) <= 10:
                    emit('NEAR-MISS')
                    continue
                emit('WRONG-AT-DERIVATION')
    return out


def stamp_line(counts):
    """One line for the report headers the list-printing tools stamp."""
    return ('[citation-classes] HOLDS %d | MOVED-SINCE %d | NEAR-MISS %d | '
            'QUOTED-CLAIM %d | WRONG-AT-DERIVATION %d | NOT-A-REPO-PATH %d '
            '| TS-MOVED %d | TS-NEAR-MISS %d | TS-QUOTED %d | TS-WRONG %d '
            '| NO-SHA %d'
            % (counts.get('HOLDS', 0), counts.get('MOVED-SINCE', 0),
               counts.get('NEAR-MISS', 0), counts.get('QUOTED-CLAIM', 0),
               counts.get('WRONG-AT-DERIVATION', 0),
               counts.get('NOT-A-REPO-PATH', 0),
               counts.get('TS-DERIVED-MOVED', 0),
               counts.get('TS-DERIVED-NEAR-MISS', 0),
               counts.get('TS-DERIVED-QUOTED', 0),
               counts.get('TS-DERIVED-WRONG', 0),
               counts.get('UNVERIFIABLE-NO-SHA', 0))
            + (' | TS-RANGE-MOVED %d' % counts.get('TS-DERIVED-RANGE-MOVED', 0)
               if 'TS-DERIVED-RANGE-MOVED' in counts else '')
            + (' | PINNED %d | PINNED-WRONG %d | PINNED-UNRES %d'
               % (counts.get('BLOB-PINNED', 0),
                  counts.get('BLOB-PINNED-WRONG', 0),
                  counts.get('BLOB-PINNED-UNRESOLVED', 0))
               if any(k.startswith('BLOB-PINNED') for k in counts) else ''))


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
        # A SECOND file, same commit, for the abbreviation-split regression
        # below -- each carries its own distinctive anchor word near its
        # own cited line, in a different file than app.py's.
        wbody = ['# pad'] * 9 + ['def sprocketize():', '    return 2'] + ['# t'] * 5
        open(os.path.join(d, 'widget.py'), 'w').write('\n'.join(wbody) + '\n')
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
        # ── REGRESSION, h1 b55: two different-file citations stranded in
        # the same sentence by an abbreviation-triggered false split.
        # Reproduces the real failure exactly: "St." mid-sentence used to
        # split app.py:10's citation away from "frobnicate" (its real
        # anchor), leaving only widget.py's name as a candidate -- which
        # is excluded as app.py's OWN-file check does not apply to it, but
        # never appears near app.py's line 10 either. BOTH must now HOLD.
        two_file_abbrev = {
            'summary': ("`frobnicate` lives in the St. Louis build of this "
                        "app, at app.py:10, and `sprocketize` is the matching "
                        "widget.py:10 helper."),
            'source_shas': {'app.py': {'sha': sha1}, 'widget.py': {'sha': sha1}}}
        tfa_result = {p: c for p, l, c in classify(two_file_abbrev, repo=d)}
        # app.py genuinely MOVED (the v2 commit above shifted it by 5) --
        # the correct, HONEST classification here is MOVED-SINCE, not
        # HOLDS. The actual regression this locks: BEFORE the fix, the
        # "St." split stranded this citation's anchor ("`frobnicate`")
        # in the OTHER fragment, so the anchor check failed even against
        # app.py's OWN recorded v1 blob and misclassified it as
        # WRONG-AT-DERIVATION -- a false "defect in this record" on a
        # citation that was correct when written. MOVED-SINCE is the
        # proof the derivation-time anchor now succeeds.
        ck('REGRESSION (h1 b55): app.py:10 classifies MOVED-SINCE (its '
           'real anchor `frobnicate` holds at derivation), NOT the false '
           'WRONG-AT-DERIVATION the "St."-split anchor failure used to '
           'produce',
           tfa_result.get('app.py') == 'MOVED-SINCE')
        ck('REGRESSION (h1 b55): widget.py:10 HOLDS too -- the other '
           'citation in the same abbreviation-split sentence, unmoved',
           tfa_result.get('widget.py') == 'HOLDS')
        ck('UNIT: split_sentences keeps an abbreviation period from ending '
           'a sentence ("St. Louis" stays in one fragment)',
           len(split_sentences('Visit the St. Louis office. Then leave.')) == 2)
        ck('UNIT: split_sentences still splits a REAL sentence boundary '
           '(F22\'s bolded-period case is untouched -- the separator\'s '
           'own ** markers are consumed by the split, same as before)',
           split_sentences('First.** Second.') == ['First.', 'Second.'])
        # ── the two adjudication-born classes (2026-09-29) ──────────────
        # NEAR-MISS: cite a line 9 past the def (head-window also missed) -- the write/use-vs-def
        # shape; anchor exists at derivation within the 10-line band but
        # outside the strict +/-3 window.
        near = {'summary': '`frobnicate` writes the row at app.py:19 today.',
                'source_shas': {'app.py': {'sha': sha1}}}
        ck('NEAR-MISS plant classifies NEAR-MISS (anchor at derivation '
           'within 10 lines, outside the strict window)',
           classify(near, repo=d)[0][2] == 'NEAR-MISS')
        # QUOTED-CLAIM: the sentence REPORTS another document's assertion.
        quoted = {'summary': 'The old cell cites app.py:99 for `frobnicate`.',
                  'source_shas': {'app.py': {'sha': sha1}}}
        ck('QUOTED-CLAIM plant classifies QUOTED-CLAIM (reporting syntax, '
           'not an assertion about current code)',
           classify(quoted, repo=d)[0][2] == 'QUOTED-CLAIM')
        # CONTROL: the same wrong line WITHOUT reporting syntax stays WRONG.
        ck('CONTROL: the identical wrong citation with PLAIN assertion '
           'syntax stays WRONG-AT-DERIVATION -- the quote class is keyed '
           'on the verbs, not on the failure',
           classify(wrong, repo=d)[0][2] == 'WRONG-AT-DERIVATION')

        # cross-file stem poisoning (the 2026-09-30 adjudication family):
        # a sentence citing TWO files whose only cross-candidate is the
        # OTHER file's stem must fall to bounds-only and HOLD.
        other = os.path.join(d, 'OTHER-DOC.md')
        open(other, 'w').write(chr(10).join(['x'] * 30) + chr(10))
        g('add', '-A'); g('commit', '-q', '-m', 'add other-doc')
        cross = {'summary': 'row (OTHER-DOC.md:20) -- gated upsert at app.py:10 with an id.',
                 'source_shas': {'app.py': {'sha': sha1}}}
        got = [c for c in classify(cross, repo=d) if c[0] == 'app.py']
        ck('cross-file stem is NOT an anchor: the app.py citation with only '
           'the other doc-stem as candidate falls to bounds-only and does '
           'not read WRONG', got and got[0][2] in ('HOLDS', 'MOVED-SINCE'))

        # ── the four 2026-09-30 TOOL-NOISE shapes, one fixture each ─────
        # (from the 28-row adjudication: every one was a correct citation
        # the anchor machinery could not see). REG.md is a register-shaped
        # file carrying each shape at a known line.
        reg_body = ['# pad'] * 9
        reg_body += ['| `sv_staff` | **B** | a register row |']        # :10
        reg_body += ['# pad']
        reg_body += ['    complete: false,']                            # :12
        reg_body += ['# pad']
        reg_body += ['// Internal content record only -- deliberately']  # :14
        reg_body += ['// no public URL or hosting for this record.']     # :15
        reg_body += ['# pad'] * 4
        reg_body += ['| `widget` | **B** | an alias row |']             # :20
        reg_body += ['# pad'] * 7
        reg_body += ['function nearFn(){} NOT_REDACTED_NOTE']           # :28
        open(os.path.join(d, 'REG.md'), 'w').write(
            '\n'.join(reg_body) + '\n')
        g('add', '-A'); g('commit', '-q', '-m', 'add REG.md')
        regsha = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=d,
                                capture_output=True, text=True).stdout.strip()
        case_e = {'summary': 'SV_STAFF (REG.md:10).',
                  'source_shas': {'REG.md': {'sha': regsha}}}
        ck('CASE: an ALL-CAPS resource mention (SV_STAFF) anchors the '
           'lowercase `sv_staff` register row -- HOLDS, not WRONG',
           classify(case_e, repo=d)[0][2] == 'HOLDS')
        alias_e = {'summary': 'scp_widget (REG.md:20) render only.',
                   'source_shas': {'REG.md': {'sha': regsha}}}
        ck('ALIAS: an app-prefixed name (scp_widget) anchors the '
           'backticked unprefixed register row (`widget`) -- HOLDS',
           classify(alias_e, repo=d)[0][2] == 'HOLDS')
        space_e = {'summary': '`NOT_REDACTED_NOTE` complete:false is '
                              'permanent (REG.md:12), by design.',
                   'source_shas': {'REG.md': {'sha': regsha}}}
        ck('SPACING: complete:false anchors `complete: false,` -- the '
           'colon-token is extracted and whitespace-normalized -- HOLDS',
           classify(space_e, repo=d)[0][2] == 'HOLDS')
        prose_e = {'summary': 'The comment (REG.md:14) states "Internal '
                              'content record only -- deliberately no '
                              'public URL or hosting for this record." '
                              'nearFn() logs each entry.',
                   'source_shas': {'REG.md': {'sha': regsha}}}
        ck('MULTI-LINE PROSE: a quoted span crossing a line break anchors '
           'the joined window around the cited line -- HOLDS',
           classify(prose_e, repo=d)[0][2] == 'HOLDS')

        squote_e = {'summary': "The comment (REG.md:14) states 'Internal "
                               'content record only -- deliberately no '
                               'public URL or hosting for this record.'
                               "' nearFn() logs it.",
                    'source_shas': {'REG.md': {'sha': regsha}}}
        ck('SINGLE-QUOTE PROSE: the same quoted span in single quotes is '
           'also a candidate -- HOLDS',
           classify(squote_e, repo=d)[0][2] == 'HOLDS')
        label_e = {'summary': 'FILE: REG.md:22.',
                   'source_shas': {'REG.md': {'sha': regsha}}}
        ck('NEGATIVE: a prose label (FILE: name) is NOT a colon-token '
           'candidate -- the space excludes it and a bounds-only citation '
           'stays HOLDS (first cut poisoned 13 real rows with this)',
           classify(label_e, repo=d)[0][2] == 'HOLDS')

        crossq_e = {'summary': 'REG.md:14 still carries "Internal content '
                               'record only -- deliberately no public URL '
                               'or hosting for this record." -- the gate '
                               'is a plain upsert at app.py:10 with an id.',
                    'source_shas': {'REG.md': {'sha': regsha},
                                    'app.py': {'sha': sha1}}}
        got = {c[0]: c[2] for c in classify(crossq_e, repo=d)}
        ck('CROSS-CITE QUOTE: a quoted span attaches only to its NEAREST '
           'citation -- the other citation in the sentence falls to '
           'bounds-only and does not read WRONG',
           got.get('app.py') in ('HOLDS', 'MOVED-SINCE'))
        qcase_e = {'summary': 'The comment (REG.md:14) states "internal '
                              'content record only -- Deliberately no '
                              'public URL or hosting for this record." '
                              'nearFn() logs it.',
                   'source_shas': {'REG.md': {'sha': regsha}}}
        ck('PROSE NORMALIZATION: a quoted span with shifted case still '
           'anchors its line -- verbatim quotes are compared case-folded '
           'with quote characters unified',
           classify(qcase_e, repo=d)[0][2] == 'HOLDS')
        evsays_e = {'summary': "REG.md:22's confidentiality evidence "
                               "says 'no PII on this row -- classified "
                               "by rule.' Read: it stores scanned text.",
                    'source_shas': {'REG.md': {'sha': regsha}}}
        ck("QUOTED-CLAIM: 'evidence says' is a reporting shape -- a "
           'paraphrased register quote on a failing citation classifies '
           'QUOTED-CLAIM, not WRONG',
           classify(evsays_e, repo=d)[0][2] == 'QUOTED-CLAIM')
        states_e = {'summary': "H2's own text states the deciding "
                               "sentence ('some other claim entirely "
                               "about the flag') -- REG.md:22.",
                    'source_shas': {'REG.md': {'sha': regsha}}}
        ck("QUOTED-CLAIM: 'states' is a reporting verb -- a failing "
           'citation whose sentence reports another text classifies '
           'QUOTED-CLAIM, not WRONG',
           classify(states_e, repo=d)[0][2] == 'QUOTED-CLAIM')

        # ── BLOB-PINNED (2026-09-30, queue-3 item 3, seq 635's shape) ───
        # A citation prefixed with an explicit sha (885fd0b9:path:line)
        # claims THAT blob's content, and must be measured against the
        # NAMED blob -- never the entry's own source sha.
        sha2 = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=d,
                              capture_output=True, text=True).stdout.strip()
        pinned = {'summary': 'FIXTURE: old blob at %s:app.py:10 is '
                             '`frobnicate` v1.' % sha1[:8],
                  'source_shas': {'app.py': {'sha': sha2}}}
        ck('BLOB-PINNED: a sha-prefixed citation correct at its NAMED blob '
           'classifies BLOB-PINNED, never NEAR-MISS against the entry '
           'source sha (the seq-635 misread)',
           classify(pinned, repo=d)[0][2] == 'BLOB-PINNED')
        pinned_bad = {'summary': 'FIXTURE: old blob at %s:app.py:99 is '
                                 '`frobnicate` v1.' % sha1[:8],
                      'source_shas': {'app.py': {'sha': sha2}}}
        ck('BLOB-PINNED-WRONG: a sha-prefixed citation wrong at its named '
           'blob is its own class -- a false claim about history',
           classify(pinned_bad, repo=d)[0][2] == 'BLOB-PINNED-WRONG')

        # ── PER-CITATION MARKER ATTRIBUTION (queue-3 item 4: 515/518/623
        # shapes -- a reporting verb elsewhere in the sentence must not
        # claim a citation that asserts current code) ───────────────────
        far_after = {'summary': 'app.py:99 holds the vocabulary applied '
                                'in this panel with `frobnicate` wired, '
                                'long padding text running well past the '
                                'attribution window before the comment '
                                'cites it by name.',
                     'source_shas': {'app.py': {'sha': sha1}}}
        ck('MARKER ATTRIBUTION (515 shape): a reporting verb >60 chars '
           'past the citation does not claim it -- the failing citation '
           'stays WRONG, not QUOTED-CLAIM',
           classify(far_after, repo=d)[0][2] == 'WRONG-AT-DERIVATION')
        gap73 = {'summary': 'app.py:99 still reads the identical wide '
                            'shape with `frobnicate` intact -- checked '
                            'against the note verbatim.',
                 'source_shas': {'app.py': {'sha': sha1}}}
        ck('MARKER ATTRIBUTION (518 shape): a marker ~70 chars past the '
           'citation is outside the window -- WRONG, not QUOTED-CLAIM',
           classify(gap73, repo=d)[0][2] == 'WRONG-AT-DERIVATION')
        far_before = {'summary': "The cell says 'lorem ipsum dolor sit "
                                 'amet padding text that runs long '
                                 'enough to pass the attribution window '
                                 'easily for this fixture case here '
                                 "today.' READ NOW: the real def is "
                                 '`frobnicate` at app.py:19.',
                      'source_shas': {'app.py': {'sha': sha1}}}
        ck('MARKER ATTRIBUTION (623 shape): a marker far BEFORE the '
           'citation does not claim it -- the read-now assertion earns '
           'its own class (NEAR-MISS here), not QUOTED-CLAIM',
           classify(far_before, repo=d)[0][2] == 'NEAR-MISS')

        # ── TS-DERIVED (2026-09-30, item 3): a NO-SHA citation gains a ──
        # timestamp-derived verdict from the commit at/before the entry's
        # own ts. SEPARATE from every sha-verified class: a timestamp
        # resolves the TREE at that moment, not what the writer actually
        # read (their clone may have lagged) -- the verdicts carry the TS-
        # prefix and never join a sha-verified count.
        d2 = tempfile.mkdtemp(prefix='citation_ts_fx_')
        try:
            def g2(date, *a):
                subprocess.run(['git'] + list(a), cwd=d2,
                               capture_output=True, check=True,
                               env=dict(os.environ, GIT_AUTHOR_NAME='fx',
                                        GIT_AUTHOR_EMAIL='f@x',
                                        GIT_COMMITTER_NAME='fx',
                                        GIT_COMMITTER_EMAIL='f@x',
                                        GIT_AUTHOR_DATE=date,
                                        GIT_COMMITTER_DATE=date))
            g2('2020-01-01T00:00:00Z', 'init', '-q')
            open(os.path.join(d2, 'app.py'), 'w').write(
                '\n'.join(body) + '\n')
            g2('2020-01-01T00:00:00Z', 'add', '-A')
            g2('2020-01-01T00:00:00Z', 'commit', '-q', '-m', 'v1')
            open(os.path.join(d2, 'app.py'), 'w').write(
                '\n'.join(['# new'] * 5 + body) + '\n')
            g2('2020-06-01T00:00:00Z', 'add', '-A')
            g2('2020-06-01T00:00:00Z', 'commit', '-q', '-m', 'v2 shifts 5')
            ts_moved = {'summary': '`frobnicate` sits at app.py:10 today.',
                        'ts': '2020-03-01T00:00:00Z'}
            ts_wrong = {'summary': '`frobnicate` sits at app.py:99 today.',
                        'ts': '2020-03-01T00:00:00Z'}
            ts_none = {'summary': '`frobnicate` sits at app.py:10 today.',
                       'ts': '2019-01-01T00:00:00Z'}
            ck('TS-DERIVED: a NO-SHA citation correct at its ts-resolved '
               'commit and failing at HEAD is TS-DERIVED-MOVED, never '
               'MOVED-SINCE', classify(ts_moved, repo=d2)[0][2]
               == 'TS-DERIVED-MOVED')
            ck('TS-DERIVED: a NO-SHA citation wrong even at its '
               'ts-resolved commit is TS-DERIVED-WRONG, never '
               'WRONG-AT-DERIVATION', classify(ts_wrong, repo=d2)[0][2]
               == 'TS-DERIVED-WRONG')
            ck('TS-DERIVED: a ts predating every commit stays '
               'UNVERIFIABLE-NO-SHA -- the fallback refuses to guess',
               classify(ts_none, repo=d2)[0][2] == 'UNVERIFIABLE-NO-SHA')
            ck('SEPARATION: stamp_line renders TS-DERIVED counts in their '
               'own buckets and never inside the sha-verified ones',
               'TS-MOVED 1' in stamp_line({'TS-DERIVED-MOVED': 1})
               and 'MOVED-SINCE 0' in stamp_line({'TS-DERIVED-MOVED': 1}))
        finally:
            shutil.rmtree(d2, ignore_errors=True)

        # ── TS-DERIVED-RANGE-MOVED (#742) ────────────────────────────────
        # v1 (ts resolves here): app.py:10 does NOT hold frobnicate -- the
        # citation is genuinely WRONG at the exact ts-resolved commit.
        # v2, ONE real commit later, on the SAME path: app.py:10 DOES hold
        # frobnicate -- genuinely correct nearby, the shape this class
        # exists to catch (correct-then, or correct-shortly-after, never
        # provable at the exact snapshot without a real sha).
        d3 = tempfile.mkdtemp(prefix='citation_tsrange_fx_')
        try:
            def g3(date, *a):
                subprocess.run(['git'] + list(a), cwd=d3,
                               capture_output=True, check=True,
                               env=dict(os.environ, GIT_AUTHOR_NAME='fx',
                                        GIT_AUTHOR_EMAIL='f@x',
                                        GIT_COMMITTER_NAME='fx',
                                        GIT_COMMITTER_EMAIL='f@x',
                                        GIT_AUTHOR_DATE=date,
                                        GIT_COMMITTER_DATE=date))
            g3('2021-01-01T00:00:00Z', 'init', '-q')
            v1_body = ['# other'] * 9 + ['def unrelated():', '    return 0']
            open(os.path.join(d3, 'app.py'), 'w').write(
                '\n'.join(v1_body) + '\n')
            g3('2021-01-01T00:00:00Z', 'add', '-A')
            g3('2021-01-01T00:00:00Z', 'commit', '-q', '-m', 'v1 wrong')
            v2_body = ['# pad'] * 9 + ['def frobnicate():', '    return 1']
            open(os.path.join(d3, 'app.py'), 'w').write(
                '\n'.join(v2_body) + '\n')
            g3('2021-01-02T00:00:00Z', 'add', '-A')
            g3('2021-01-02T00:00:00Z', 'commit', '-q', '-m',
              'v2 real drift, one commit later, correct now')
            # v3, HEAD: shifts frobnicate AWAY from :10 again, so HOLDS
            # (checked against HEAD first, ahead of any NO-SHA fallback)
            # cannot fire and the fixture actually reaches the ts path.
            open(os.path.join(d3, 'app.py'), 'w').write(
                '\n'.join(['# newer'] * 5 + v2_body) + '\n')
            g3('2021-01-03T00:00:00Z', 'add', '-A')
            g3('2021-01-03T00:00:00Z', 'commit', '-q', '-m',
              'v3 HEAD shifts it away again')
            range_e = {'summary': '`frobnicate` sits at app.py:10 today.',
                      'ts': '2021-01-01T12:00:00Z'}
            ck('TS-DERIVED-RANGE-MOVED: wrong at the exact ts-resolved '
               'commit, correct one real commit later on the same path -- '
               'its own class, never TS-DERIVED-WRONG and never '
               'TS-DERIVED-MOVED', classify(range_e, repo=d3)[0][2]
               == 'TS-DERIVED-RANGE-MOVED')

            # CONTROL: wrong at the resolved commit AND wrong throughout
            # the whole real range stays TS-DERIVED-WRONG -- the range
            # check must not manufacture a match that isn't there.
            g3('2021-01-04T00:00:00Z', 'commit', '-q', '--allow-empty',
              '-m', 'v4 still wrong, no path change')
            still_wrong = {'summary': '`frobnicate` sits at app.py:99 '
                                     'today.',
                          'ts': '2021-01-01T12:00:00Z'}
            ck('CONTROL: a citation wrong throughout the WHOLE real range '
               'stays TS-DERIVED-WRONG -- the range check does not '
               'invent a match', classify(still_wrong, repo=d3)[0][2]
               == 'TS-DERIVED-WRONG')
        finally:
            shutil.rmtree(d3, ignore_errors=True)

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
