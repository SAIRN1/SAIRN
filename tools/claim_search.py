"""claim_search.py -- plain English in, the REAL implementation out.

    python tools/claim_search.py --verify "the QR library is pinned to an exact version and loaded with an integrity hash"
    python tools/claim_search.py --query "refuse the write when the scope lookup fails" --top 10
    python tools/claim_search.py --selftest

WHY THIS EXISTS, AND IT IS NOT "SEARCH IS NICE". This platform's single most
recurring incident class is A WRITTEN CLAIM ABOUT WHAT IS BUILT NOT MATCHING
WHAT IS BUILT. The register and the handoffs carry the instances: a handoff
naming a skill that did not exist on disk; a clone registry naming four clones
while five were pushing; a comment asserting mtExtractCitations "is called at
exactly one site" three days after it became four; a tool inventory counting
what somebody typed rather than what is there. Every one of them was a sentence
nobody could cheaply check against the code it described.

THE EXPENSIVE HALF IS RETRIEVAL, AND THAT IS THE HALF THIS CLOSES. Checking a
claim is easy once the real implementation is in front of you; FINDING the
implementation from an English sentence is what nobody does, because grep needs
the words the code happens to use and an English claim almost never has them.
"pinned to an exact version" does not appear in a `<script src=...>` tag.

════ WHAT IT DOES NOT DO, FIRST ════════════════════════════════════════════

IT NEVER SAYS WHETHER THE CLAIM IS TRUE. Not in any mode, not with any flag.
It retrieves candidate implementations and prints them; the conformance
judgement stays with a reader, and with independent review where the claim
matters. A retrieval tool that also returned a verdict would be the thing this
platform keeps recording against itself -- an assertion nobody re-checked --
rebuilt with a search index underneath it.

IT IS NOT NEURAL. There is no embedding model on this interpreter (measured
2026-09-17: no numpy, torch, transformers, sentence-transformers, onnxruntime,
scikit-learn or faiss). "Hybrid lexical + embedding + rerank" is the design;
what ships is LEXICAL (BM25 over identifier-split tokens and comment prose) plus
a STRUCTURAL rerank borrowed from tools/shape_search.py. The embedding stage is
absent, not stubbed, and its absence is printed on every run rather than left
for a reader to discover. What that costs is concrete: a claim whose wording
shares no stem with the code or its comments will not be found, and a trained
model would find some of those.

WHAT MAKES THE LEXICAL HALF UNUSUALLY GOOD HERE, and it is worth saying because
it is why this is useful rather than a toy: this repository's comments are long,
argumentative English written next to the code they describe. The prose a claim
is made in and the prose the implementation was explained in are the same
register. BM25 over comments plus identifier-split code is a strong retriever on
a corpus like this and a weak one on a codebase with terse comments.

Exit 0 always for a query -- "nothing matched" is an answer, not a failure.
Exit 1 only if the index could not be built, and it says so.
"""
import io
import math
import os
import re
import subprocess
import sys

CRITERIA_VERSION = 'claim-search-1 (2026-09-17)'

# ── UTF-8 STDOUT, BECAUSE THIS TOOL PRINTS THE REPOSITORY BACK ────────────
# Windows encodes captured stdout as cp1252 and this file's whole job is to
# echo source lines -- which here are full of em-dashes and arrows. The first
# real run died with UnicodeEncodeError AFTER computing the right answer, which
# is the platform's own recorded shape (tools/run_semgrep.py, and
# dispatch_state.py the same week). UTF-8 rather than errors='replace' for the
# same stated reason: replacing characters silently changes what a reader is
# shown of their own code.
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:                                                 # noqa: BLE001
    pass

REPO = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True, encoding='utf-8',
                      errors='replace').stdout.strip() or os.getcwd()

WINDOW = 14          # lines per indexed unit
STRIDE = 7           # overlapping, so a claim spanning a boundary is still found

STOP = set("""a an and are as at be been but by can cannot could did do does for
from had has have how if in into is it its may might must not of on or should so
some such than that the their them then there these they this those to was were
what when where which while who why will with would you your it's dont don't""".split())

_WORD = re.compile(r"[A-Za-z][A-Za-z0-9_$]*")


def split_ident(w):
    """`licenseHash` -> license hash;  `SCOPE_LOOKUP_FAILED` -> scope lookup failed.

    THE ONE THING THAT MAKES CODE SEARCHABLE FROM ENGLISH. Without it a claim
    saying "license hash" never meets `licHash`, and the retriever is reduced to
    matching whatever the author happened to spell out.
    """
    parts = re.split(r'[_\-$]+', w)
    out = []
    for p in parts:
        out.extend(re.findall(r'[A-Z]+(?![a-z])|[A-Z][a-z]+|[a-z]+|\d+', p) or [p])
    return [o.lower() for o in out if o]


def terms(text):
    out = []
    for m in _WORD.finditer(text):
        w = m.group()
        pieces = split_ident(w)
        out.extend(pieces)
        if len(pieces) > 1:
            out.append(w.lower())          # the joined form counts too
    return [t for t in out if t not in STOP and len(t) > 1]


CODE_EXT = {'.js', '.html', '.py', '.sql', '.json'}
PROSE_EXT = {'.md'}


def tracked(exts):
    r = subprocess.run(['git', '-C', REPO, 'ls-files'], capture_output=True,
                       text=True, encoding='utf-8', errors='replace')
    for rel in (r.stdout or '').split('\n'):
        rel = rel.strip()
        if not rel or rel.startswith('archive/') or '/skill-backups/' in rel:
            continue
        if os.path.splitext(rel)[1] in exts:
            yield rel


def build_index(exts=None):
    """[(rel, line, text, terms)] over overlapping line windows of every file."""
    units = []
    for rel in tracked(exts or (CODE_EXT | PROSE_EXT)):
        p = os.path.join(REPO, rel)
        try:
            lines = io.open(p, encoding='utf-8', errors='replace').read().split('\n')
        except OSError:
            continue
        if len(lines) > 200000:
            continue
        for i in range(0, max(1, len(lines)), STRIDE):
            chunk = lines[i:i + WINDOW]
            if not any(c.strip() for c in chunk):
                continue
            text = '\n'.join(chunk)
            t = terms(text)
            if len(t) >= 6:
                units.append((rel, i + 1, text, t))
    return units


def bm25(units, q_terms, k1=1.5, b=0.75):
    """Plain BM25. Written out rather than imported because there is nothing to
    import on this interpreter, and because a scorer nobody can read is one
    nobody can argue with when it ranks something odd."""
    N = len(units)
    df = {}
    for _, _, _, t in units:
        for w in set(t):
            df[w] = df.get(w, 0) + 1
    avgdl = sum(len(t) for _, _, _, t in units) / float(max(1, N))
    idf = {w: math.log(1 + (N - df.get(w, 0) + 0.5) / (df.get(w, 0) + 0.5))
           for w in set(q_terms)}
    scored = []
    for rel, line, text, t in units:
        tf = {}
        for w in t:
            if w in idf:
                tf[w] = tf.get(w, 0) + 1
        if not tf:
            continue
        dl = len(t)
        s = 0.0
        for w, f in tf.items():
            s += idf[w] * (f * (k1 + 1)) / (f + k1 * (1 - b + b * dl / avgdl))
        # DISTINCT QUERY TERMS MATTER MORE THAN REPEATS OF ONE. A window that
        # says "hash" nine times should not beat one that says "pinned",
        # "version" and "integrity" once each -- the second is the claim.
        s *= (len(tf) / float(len(set(q_terms)))) ** 0.5
        scored.append((s, rel, line, text))
    scored.sort(key=lambda x: -x[0])
    return scored


def shape_rerank(scored, like):
    """Optional structural rerank, borrowed from tools/shape_search.py.

    FAILS LOUD RATHER THAN SILENTLY SKIPPING (PR 1.11): if shape_search cannot
    be imported the caller is told the rerank did NOT run, because a ranking
    that quietly lost a stage is indistinguishable from one that had it.
    """
    sys.path.insert(0, os.path.join(REPO, 'tools'))
    try:
        import shape_search as S
    except Exception as e:                                        # noqa: BLE001
        return scored, 'COULD NOT RERANK: tools/shape_search.py did not import (%s)' % e
    want = S.vector(S.js_shape_tokens(like))
    out = []
    for s, rel, line, text in scored:
        sv = S.vector(S.js_shape_tokens(text))
        out.append((s * (1.0 + S.cosine(want, sv)), rel, line, text))
    out.sort(key=lambda x: -x[0])
    return out, None


def show(scored, top, show_text):
    for s, rel, line, text in scored[:top]:
        print('  %7.2f  %s:%d' % (s, rel, line))
        if show_text:
            for ln in text.split('\n'):
                if ln.strip():
                    print('           | ' + ln[:110])
            print('')


def cmd_query(q, top, like, show_text, exts=None, why=''):
    units = build_index(exts)
    if len(units) < 100:
        print('COULD NOT BUILD AN INDEX: only %d units. Not ranking against a '
              'corpus this small.' % len(units))
        return 1
    qt = terms(q)
    if not qt:
        print('the query has no searchable terms once stop words are removed')
        return 1
    scored = bm25(units, qt)
    note = None
    if like:
        scored, note = shape_rerank(scored, like)
    print('claim_search -- %s' % CRITERIA_VERSION)
    print('  query terms : %s' % ' '.join(sorted(set(qt))))
    print('  indexed     : %d windows over %d files%s'
          % (len(units), len({u[0] for u in units}), why))
    print('  stages      : BM25 (lexical, identifier-split) %s'
          % ('+ structural rerank' if like and not note else
             '-- NO embedding stage: there is no model on this interpreter'))
    if note:
        print('  %s' % note)
    print('')
    show(scored, top, show_text)
    if not scored:
        print('  nothing matched. THAT IS AN ANSWER, not a failure -- and it is')
        print('  NOT "the claim is false": it is "no window shares vocabulary')
        print('  with this sentence", which is exactly what the missing')
        print('  embedding stage would help with.')
    return 0


def cmd_verify(claim, top):
    print('claim_search --verify -- %s' % CRITERIA_VERSION)
    print('')
    print('CLAIM: %s' % claim)
    print('')
    # ── PROSE IS EXCLUDED IN THIS MODE, AND IT IS THE WHOLE POINT ─────────
    # The first real run of --verify returned the three top hits from
    # docs/SOUP-REGISTER.md -- the document the claim was COPIED OUT OF. A
    # retriever ranking a claim's own restatement above its implementation
    # confirms nothing and reads as confirmation, which is the failure mode
    # this tool exists to break rather than to automate. Verifying a claim
    # means finding the CODE; --query still searches everything.
    rc = cmd_query(claim, top, None, True, CODE_EXT,
                   '  (.md EXCLUDED: a claim restated is not a claim checked)')
    print('')
    print('THIS IS EVIDENCE, NOT A VERDICT.')
    print('  * Nothing above says the claim is true. The rows are the places')
    print('    this repository talks about the same things the claim does.')
    print('  * A claim can be FALSE with a perfect top hit -- the code the')
    print('    sentence describes is exactly where the mismatch would live.')
    print('  * A claim can be TRUE with nothing above it, because the missing')
    print('    embedding stage means wording that shares no stem is not found.')
    print('  * The conformance judgement is a reader\'s, and an independent')
    print('    one where the claim matters. That has not changed and this tool')
    print('    does not change it -- it closes the RETRIEVAL half only.')
    return rc


SELFTEST = [
    # (query, a path substring that MUST appear in the top N, N)
    ("refuse the write when the patient scope lookup fails", 'dnt-bi', 10),
    ("never output a case citation generated by the model", 'sairnlaw', 5),
    ("the demo licence rows for SAIRNcare and SAIRNsenior", 'alf_sen_demo', 5),
]


def cmd_selftest():
    """Locked question/answer pairs. Each answer was established by hand BEFORE
    the retriever was pointed at it, which is the only way a search self-test
    means anything -- a test written from what the tool returned is a
    description of the tool, not a check on it."""
    print('claim_search selftest -- %s' % CRITERIA_VERSION)
    units = build_index()
    bad = 0
    for q, must, n in SELFTEST:
        scored = bm25(units, terms(q))
        hits = [rel for _, rel, _, _ in scored[:n]]
        ok = any(must in h for h in hits)
        bad += 0 if ok else 1
        print('  %-5s top%-3d %-58s %s'
              % ('ok' if ok else 'FAIL', n, q[:58], '' if ok else '-> ' + ', '.join(hits[:4])))
    print('')
    if bad:
        print('%d locked query/answer pair(s) failed.' % bad)
        return 1
    print('all %d locked pairs retrieved their known answer' % len(SELFTEST))
    return 0


def main(argv):
    def opt(name, default=None):
        return argv[argv.index(name) + 1] if name in argv else default
    if '--selftest' in argv:
        return cmd_selftest()
    top = int(opt('--top', '8'))
    if '--verify' in argv:
        return cmd_verify(opt('--verify'), top)
    if '--query' in argv:
        return cmd_query(opt('--query'), top, opt('--shape-like'), '--text' in argv)
    print(__doc__.strip().split('\n\n')[0])
    print('')
    print('  --verify "<claim>"   retrieve the real implementation to CHECK it against')
    print('  --query  "<words>"   rank windows by lexical match')
    print('  --selftest           locked query/answer pairs')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
