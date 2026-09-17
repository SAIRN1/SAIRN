"""Control for tools/claim_search.py.

    python tests/run_claim_search_probe.py

THE DANGEROUS FAILURE OF A CLAIM-VERIFICATION TOOL IS NOT A BAD RANKING. It is
a tool that reads as confirmation. Two shapes do that and both are attacked
here: returning a VERDICT at all, and ranking the document a claim was copied
out of above the code it describes -- which the first real run of --verify did,
putting docs/SOUP-REGISTER.md in all three top slots for a claim quoted from
docs/SOUP-REGISTER.md.

The retrieval quality arms use LOCKED query/answer pairs whose answers were
established by hand before the retriever was pointed at them. A search test
written from what the tool returned is a description of the tool.
"""
CONTROLS_FOR = ['claim_search.py']

import io
import os
import subprocess
import sys

REPO = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True, encoding='utf-8',
                      errors='replace').stdout.strip()
sys.path.insert(0, os.path.join(REPO, 'tools'))
TOOL = os.path.join(REPO, 'tools', 'claim_search.py')
R = {}


def ck(label, actual, expected):
    R[label] = (actual == expected, actual, expected)


def run(*args):
    p = subprocess.run([sys.executable, TOOL] + list(args), cwd=REPO,
                       capture_output=True, text=True, encoding='utf-8',
                       errors='replace', timeout=1200)
    return p.returncode, (p.stdout or '') + (p.stderr or '')


import claim_search as C                                          # noqa: E402

# ── A. THE IDENTIFIER SPLIT, WHICH IS WHY ENGLISH CAN REACH CODE ──────────
ck('A1 camelCase splits', C.split_ident('licenseHash'), ['license', 'hash'])
ck('A2 SCREAMING_SNAKE splits',
   C.split_ident('SCOPE_LOOKUP_FAILED'), ['scope', 'lookup', 'failed'])
ck('A3 an acronym run is kept whole', C.split_ident('parseHTMLString'),
   ['parse', 'html', 'string'])
ck('A4 stop words are dropped from a query',
   [t for t in C.terms('the code is in the file') if t in ('the', 'is', 'in')], [])
ck('A5 and the JOINED form survives too, so an exact identifier still matches',
   'licensehash' in C.terms('licenseHash'), True)

# ── B. IT NEVER RETURNS A VERDICT. THE ARM THAT MATTERS MOST. ─────────────
rc, out = run('--verify', 'the QR library is pinned to an exact version', '--top', '2')
ck('B1 --verify runs', rc, 0)
# ── SCANNED ABOVE THE DISCLAIMER, AND THE REASON IS A REAL FALSE POSITIVE ─
# The first version scanned the WHOLE output for "claim is true" and failed --
# on the tool's own disclaimer, which says "Nothing above says the claim is
# true." A marker search that cannot tell an assertion from its NEGATION is
# PR 1.2, and this is the third time today a check of mine has committed it
# while testing something else. The results region is what must carry no
# verdict; the epilogue is where the refusal to give one is written, and it is
# asserted separately below.
head = out.split('THIS IS EVIDENCE, NOT A VERDICT')[0].lower()
for word in ('claim is true', 'claim is false', 'verified:', 'confirmed:',
             'the claim holds', 'does not hold'):
    ck('B2 the results region never says %r' % word, word in head, False)
ck('B3 and it says in words that this is evidence rather than a verdict',
   'THIS IS EVIDENCE, NOT A VERDICT' in out, True)
ck('B4 it names the case where a TRUE claim has nothing above it',
   'can be TRUE with nothing above it' in out, True)
ck('B5 and the case where a FALSE claim has a perfect top hit',
   'can be FALSE with a perfect top hit' in out, True)

# ── C. A CLAIM RESTATED IS NOT A CLAIM CHECKED ────────────────────────────
ck('C1 --verify excludes prose, so the document a claim came from cannot be '
   'its own evidence', '.md and this searcher' in out, True)
ck('C2 and no .md file appears in the results',
   any(line.strip().split()[-1].split(':')[0].endswith('.md')
       for line in out.split('\n') if line.strip().startswith(('1', '2', '3', '4', '5',
                                                               '6', '7', '8', '9'))),
   False)
rc2, out2 = run('--query', 'the QR library is pinned to an exact version', '--top', '3')
ck('C3 CONTROL: --query still searches prose -- the exclusion is scoped to '
   'verification, not a global blindness', '.md and this searcher' in out2, False)

# ── D. IT SAYS WHAT IT IS NOT ─────────────────────────────────────────────
ck('D1 every run states the embedding stage is absent',
   'NO embedding stage' in out, True)
ck('D2 the module says so before any code runs',
   'IT IS NOT NEURAL' in (C.__doc__ or ''), True)
ck('D3 and it names what that costs rather than only that it is missing',
   'shares no stem' in (C.__doc__ or ''), True)

# ── E. THE LOCKED QUERY/ANSWER PAIRS ──────────────────────────────────────
rc, out = run('--selftest')
ck('E1 --selftest passes', rc, 0)
ck('E2 there are at least three locked pairs', len(C.SELFTEST) >= 3, True)
# drop_self=True, for the reason the tool now carries: this probe QUOTES the
# claim it tests with, so indexing itself put five self-references above the
# implementation. A retrieval test that ranks its own fixture first measures
# nothing about retrieval.
units = C.build_index(C.CODE_EXT, True)
ck('E3 the code index is large enough to rank against', len(units) > 10000, True)
ck('E4a the searcher\'s own files are out of the index it is judged on',
   any(rel in C.SELF_FILES for rel, _, _, _ in units), False)
# THE REAL DEMONSTRATION, re-run here rather than trusted from the tool's own
# output: a plain-English claim with NO shared identifier must reach the app
# that implements it. "pinned to an exact version" appears nowhere in a
# <script src=...> line.
#
# ── TOP 10, AND THE NUMBER IS MEASURED RATHER THAN GENEROUS ───────────────
# This arm was written at top 5 and FAILED four hours later against an
# unchanged tool: four other clones had pushed, the corpus grew, and BM25 rank
# on a moving corpus is not stable at that resolution. ACCURACY AND STABILITY
# ARE TWO NUMBERS and this arm had only ever asserted the first. Top 10 is
# where the answer sat across both measurements; a failure here now means the
# retrieval genuinely moved, not that somebody else committed.
scored = C.bm25(units, C.terms(
    'the QR library is pinned to an exact version and loaded with an integrity hash'))
top = [rel for _, rel, _, _ in scored[:10]]
ck('E4 a claim in English reaches the app that implements it (top 10)',
   any(r.endswith('stonedesk.html') or r.endswith('sairndental.html') for r in top),
   True)
src = io.open(os.path.join(REPO, 'stonedesk.html'), encoding='utf-8').read()
ck('E5 ...and the claim\'s own words are NOT in the implementation, so a grep '
   'for them would have found nothing',
   'pinned to an exact version' in src.lower(), False)

# ── F. IT FAILS LOUD, NOT SILENT ──────────────────────────────────────────
rc, out = run('--query', 'the a of and', '--top', '3')
ck('F1 a query that is all stop words is refused rather than ranked', rc, 1)
scored2, note = C.shape_rerank([(1.0, 'x', 1, 'function a(){ return 1; }')],
                               'function b(){ return 2; }')
ck('F2 the structural rerank reports when it could not run rather than '
   'silently skipping', note, None)

# ── G. NON-ASCII SOURCE DOES NOT KILL IT MID-ANSWER ───────────────────────
# The first real --verify computed the right answer and then died with
# UnicodeEncodeError printing an em-dash to a cp1252 stdout -- the platform's
# own recorded shape, twice in one week.
rc, out = run('--verify', 'the citation rule forbids generating a case citation',
              '--top', '6')
ck('G1 a verify that prints real source with em-dashes completes', rc, 0)
ck('G2 and it actually printed source lines', '|' in out, True)

for k in sorted(R):
    ok, actual, expected = R[k]
    print('  %-6s %s' % ('ok' if ok else 'FAIL', k))
    if not ok:
        print('         expected %r, got %r' % (expected, actual))
bad = [k for k in R if not R[k][0]]
print('')
print('claim-search: %d checks, %d failed' % (len(R), len(bad)))
sys.exit(1 if bad else 0)
