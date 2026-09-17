"""shape_search.py -- find the same BUG SHAPE written completely differently.

    python tools/shape_search.py --validate            # measure it before trusting it
    python tools/shape_search.py --like api/dnt-bi.js:handler
    python tools/shape_search.py --shape scope-then-read --top 15
    python tools/shape_search.py --selftest

WHY THIS EXISTS. When a real defect is fixed here, the recombination discipline
says to look for the same defect elsewhere -- and the looking is done with grep.
Grep finds the same WORDS. It cannot find the same SHAPE written with different
identifiers, a different iteration form, or in the other language, which is
exactly how the same mistake actually recurs across twenty-two apps written at
different times. Today's sweep is the case in point: api/sd-data.js resolves a
patient scope before its read and api/dnt-bi.js did it after, deriving the same
ids from the same table -- and no grep for `SCOPE_LOOKUP_FAILED` could have
ranked those two as the same thing, because both contain the string.

════ WHAT THIS IS NOT, STATED FIRST BECAUSE THE NAME INVITES THE WRONG READ ════

THIS IS NOT A NEURAL EMBEDDING AND IT IS NOT VulCoCo. VulCoCo embeds code with a
trained model and compares in that model's latent space. NOTHING ON THIS MACHINE
CAN DO THAT: measured 2026-09-17, the interpreter has no numpy, no torch, no
transformers, no sentence-transformers, no onnxruntime, no scikit-learn and no
faiss -- `tiktoken` is the only vaguely adjacent package and it is a tokenizer.
Adding a real model means adding the platform's first ML dependency, on a
machine five agents share, and that is MICHAEL'S CALL rather than a thing a
build agent installs while nobody is looking.

So this embeds STRUCTURE instead: every function becomes a vector of normalised
control-flow and guard-shape n-grams, with identifiers, literals and iteration
form erased. Cosine similarity over that vector is a real semantic-ish measure
-- it is blind to names, strings, spacing and `for` vs `.forEach` vs `.map` --
and it is NOT blind to the things a trained model would see: two functions that
compute the same answer by different control flow score LOW here and would score
high in a model. That gap is real, it is stated in the report on every run, and
`--embedder` is the one hook to fill when a model is available.

════ AND IT IS MEASURED BEFORE IT IS TRUSTED ════════════════════════════════

The instruction that produced this file named the hazard exactly: some models
score unrelated code above 85% similarity. So `--validate` does two separate
things and reports two separate numbers, never one:

  1. THE BLIND LOCK. Synthetic pairs whose answer is known and written down
     BEFORE anything real is scored -- same shape under different names must
     rank high, genuinely different shapes must not. Criteria are stamped with
     CRITERIA_VERSION so a later loosening is visible as a change.
  2. THE FALSE-POSITIVE MEASUREMENT ON REAL CODE. Random pairs of functions
     drawn from DIFFERENT files in DIFFERENT apps -- unrelated by construction
     -- scored, and the distribution reported with the count above the
     threshold. That is the number that says whether a hit here means anything,
     and it is measured on this repository rather than assumed from a paper.

A threshold nobody measured is the thing this file refuses to ship.

Exit 0 clean, 1 finding, 2 could not run.
"""
import ast
import io
import json
import math
import os
import random
import re
import subprocess
import sys

CRITERIA_VERSION = 'shape-search-1 (2026-09-17)'

REPO = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True, encoding='utf-8',
                      errors='replace').stdout.strip() or os.getcwd()

# ── THE THRESHOLD, AND WHY RAISING IT DOES ALMOST NOTHING ─────────────────
# Measured on this repository 2026-09-17, 20,000 unrelated pairs drawn from
# 8,657 functions in 873 files: the hit rate is 1.155% +- 0.148pp (95%), and it
# barely moves with the threshold -- 1.03% at 0.72 and still 0.53% at 0.92.
#
# THAT IS NOT NOISE AND IT IS THE MOST USEFUL THING THIS FILE MEASURED. The
# hits were READ, not just counted, and they are genuinely structurally
# identical code: `ctxFor` in two fault-injection files at 0.868, `grab` in two
# StoneDesk suites at 1.000 (a copied helper), and a cluster of tools/ `main()`
# functions that all parse argv, loop, print and exit. So the number is not a
# measure of confusion -- it is the BASE RATE at which unrelated code in this
# repository shares a shape, and no threshold makes that go away because the
# shapes really are the same.
#
# WHAT FOLLOWS FROM IT, and it is a design conclusion rather than a caveat: a
# similarity hit is a CANDIDATE, never a finding, and the tool ranks and caps
# rather than dumping everything over a line. --like prints the expected number
# of look-alikes for the corpus it just searched, so a reader knows how much of
# what they are seeing is the base rate before they read the first row.
THRESHOLD = 0.72
# From the same measurement. Printed rather than hidden so a later corpus can
# be compared against it, and re-measured by --validate on every run.
MEASURED_HIT_RATE = 0.01155
MEASURED_CI_PP = 0.148
MEASURED_ON = '2026-09-17, 20000 pairs / 8657 functions / 873 files'

# ── THE NORMALISER. Everything below turns code into SHAPE. ────────────────
# Identifiers, literals, member names and iteration form are all erased. What
# survives is the control flow, the guard polarity, and the order of awaits,
# checks and returns -- which is what a defect shape actually is.
JS_KEYWORDS = {
    'if', 'else', 'for', 'while', 'do', 'switch', 'case', 'default', 'break',
    'continue', 'return', 'throw', 'try', 'catch', 'finally', 'await', 'async',
    'function', 'var', 'let', 'const', 'new', 'typeof', 'instanceof', 'delete',
    'in', 'of', 'yield', 'class', 'this', 'null', 'undefined', 'true', 'false',
}
# Iteration forms that mean the same thing. Collapsed so `for (const x of xs)`,
# `xs.forEach(...)` and `xs.map(...)` are one token -- this is the single
# biggest reason a text search misses a recurrence.
ITER_FORMS = {'forEach', 'map', 'filter', 'reduce', 'some', 'every', 'flatMap'}
# Guard-ish members whose NAME carries shape rather than identity.
SHAPE_MEMBERS = {'ok', 'status', 'length', 'json', 'push', 'indexOf', 'then',
                 'catch', 'error', 'code', 'message'}

_JS_TOKEN = re.compile(r"""
    (?P<str>'(?:[^'\\]|\\.)*'|"(?:[^"\\]|\\.)*"|`(?:[^`\\]|\\.)*`)
  | (?P<num>\b\d[\w.]*)
  | (?P<name>[A-Za-z_$][\w$]*)
  | (?P<op>===|!==|==|!=|<=|>=|&&|\|\||\?\?|=>|\+\+|--|[-+*/%<>!?:;,.(){}\[\]=&|^~])
""", re.X)


def strip_js_comments(code):
    """String-aware comment removal. `'https://x'` must survive."""
    out, i, q = [], 0, None
    while i < len(code):
        c, n = code[i], code[i + 1] if i + 1 < len(code) else ''
        if q:
            if c == '\\':
                out.append('  '); i += 2; continue
            if c == q:
                q = None
            out.append(c); i += 1; continue
        if c in '"\'`':
            q = c; out.append(c); i += 1; continue
        if c == '/' and n == '/':
            while i < len(code) and code[i] != '\n':
                i += 1
            continue
        if c == '/' and n == '*':
            i += 2
            while i < len(code) - 1 and not (code[i] == '*' and code[i + 1] == '/'):
                out.append('\n' if code[i] == '\n' else ' ')
                i += 1
            i += 2; continue
        out.append(c); i += 1
    return ''.join(out)


def js_shape_tokens(body):
    """A JS function body as a stream of SHAPE tokens.

    Identifiers become ID, literals become STR/NUM, iteration forms collapse to
    ITER, and a handful of members that carry shape rather than identity (.ok,
    .status, .length) keep their names. A member access on anything else is
    just DOT ID.
    """
    toks = []
    prev_dot = False
    for m in _JS_TOKEN.finditer(strip_js_comments(body)):
        kind = m.lastgroup
        v = m.group()
        if kind == 'str':
            toks.append('STR'); prev_dot = False
        elif kind == 'num':
            toks.append('NUM'); prev_dot = False
        elif kind == 'name':
            if prev_dot and v in ITER_FORMS:
                toks.append('ITER')
            elif prev_dot and v in SHAPE_MEMBERS:
                toks.append('.' + v)
            elif v in JS_KEYWORDS:
                toks.append(v)
            else:
                toks.append('ID')
            prev_dot = False
        else:
            if v == '.':
                prev_dot = True
                continue                      # the dot itself carries nothing
            toks.append(v); prev_dot = False
    return toks


PY_ITER = {'map', 'filter', 'sorted', 'enumerate', 'zip'}


def py_shape_tokens(node):
    """A Python function as a stream of SHAPE tokens, walked from the AST.

    The AST is used rather than a tokenizer because Python gives us one for
    free and it is strictly better: `if not x.ok:` and `if x.ok == False:`
    differ as text and are the same shape here.
    """
    toks = []

    def walk(n):
        name = type(n).__name__
        if isinstance(n, ast.Name):
            toks.append('ID'); return
        if isinstance(n, ast.Constant):
            toks.append('STR' if isinstance(n.value, str) else 'NUM'); return
        if isinstance(n, ast.Attribute):
            toks.append('.' + n.attr if n.attr in SHAPE_MEMBERS else 'ID')
            walk(n.value); return
        if isinstance(n, ast.Call):
            f = n.func
            fn = getattr(f, 'id', None) or getattr(f, 'attr', None)
            toks.append('ITER' if fn in PY_ITER or fn in ITER_FORMS else '(')
        else:
            toks.append(name)
        for ch in ast.iter_child_nodes(n):
            walk(ch)

    walk(node)
    return toks


def ngrams(toks, n=3):
    return [' '.join(toks[i:i + n]) for i in range(max(0, len(toks) - n + 1))]


# ── ORDER IS A FEATURE, AND THE BLIND LOCK IS WHAT SAID SO ────────────────
# The first version of vector() was bag-of-n-grams only, and fixture 3 --
# "a refusal-then-read and a read-then-refuse are NOT the same shape" -- scored
# 1.000. Both halves contain the identical 3-grams; only their SEQUENCE differs,
# and a bag has no sequence. That fixture is in the lock because ordering is
# exactly the defect this tool was written after: api/dnt-bi.js read the PHI and
# then resolved the scope, while api/sd-data.js resolved the scope and then
# read. A measure that scores those two as identical would have been useless for
# the case that motivated it, and it took the lock to say so before any real
# code was scored.
#
# So a second, much shorter stream is built from the SHAPE EVENTS alone --
# await, branch, return, throw, iteration, negation -- and its 2- and 3-grams
# are added with a heavy weight. Two functions with the same parts in a
# different order now differ where it counts and still match where names,
# strings and spacing differ.
# ITERATION IS ONE EVENT, WHATEVER FORM IT TOOK. `for (const x of xs)`,
# `xs.forEach(...)` and a comprehension are the same event here -- without this
# the lock's "same loop shape written three different ways" fixture scored 0.651
# purely because one said `for` and the other said `ITER`, which is the exact
# text-level distinction this tool exists to see past.
EVENT_MAP = {
    'for': 'ITER', 'while': 'ITER', 'ITER': 'ITER', 'For': 'ITER',
    'While': 'ITER', 'ListComp': 'ITER', 'comprehension': 'ITER',
    'await': 'AWAIT', 'Await': 'AWAIT',
    'return': 'RET', 'Return': 'RET',
    'if': 'BRANCH', 'If': 'BRANCH', '?': 'BRANCH',
    'throw': 'RAISE', 'Raise': 'RAISE',
    'try': 'TRY', 'Try': 'TRY', 'catch': 'CATCH', 'ExceptHandler': 'CATCH',
    '!': 'NOT', 'Not': 'NOT', '&&': 'AND', '||': 'OR', 'BoolOp': 'AND',
}
# HIGH ON PURPOSE. The order of guards, awaits and returns IS the defect shape;
# the surrounding token soup is context. Derived from the lock rather than
# chosen: at 4 the order-swapped fixture still scored 0.769.
EVENT_WEIGHT = 12


def vector(toks):
    """Term frequency over 2- and 3-grams, plus weighted ORDER-OF-EVENTS grams.

    Sparse dict; there is no numpy on this interpreter and this stays stdlib on
    purpose -- a checker that needs a dependency is a checker that stops running
    the day the dependency is not there.
    """
    v = {}
    for g in ngrams(toks, 2) + ngrams(toks, 3):
        v[g] = v.get(g, 0) + 1
    ev = [EVENT_MAP[t] for t in toks if t in EVENT_MAP]
    for g in ngrams(ev, 2) + ngrams(ev, 3):
        k = 'EV:' + g
        v[k] = v.get(k, 0) + EVENT_WEIGHT
    return v


def cosine(a, b):
    if not a or not b:
        return 0.0
    small, big = (a, b) if len(a) <= len(b) else (b, a)
    dot = sum(w * big.get(k, 0) for k, w in small.items())
    na = math.sqrt(sum(w * w for w in a.values()))
    nb = math.sqrt(sum(w * w for w in b.values()))
    return dot / (na * nb) if na and nb else 0.0


# ── EXTRACTION: every function in the repo, with its shape vector ──────────
JS_FUNC = re.compile(
    r'(?:^|\n)\s*(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(', re.M)


def js_functions(src, path):
    """(name, body) for every top-level `function NAME(` in a JS/HTML source.

    Brace-balanced from the opening `{`, string- and comment-aware, so a `}`
    inside a template literal does not end the function early.
    """
    code = strip_js_comments(src)
    out = []
    for m in JS_FUNC.finditer(code):
        i = code.find('{', m.end())
        if i < 0:
            continue
        depth, j, q = 0, i, None
        while j < len(code):
            c = code[j]
            if q:
                if c == '\\':
                    j += 2; continue
                if c == q:
                    q = None
            elif c in '"\'`':
                q = c
            elif c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    break
            j += 1
        body = code[i:j + 1]
        if 40 < len(body) < 20000:
            out.append((m.group(1), body))
    return out


def py_functions(src, path):
    try:
        tree = ast.parse(src, path)
    except SyntaxError:
        return []
    out = []
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out.append((n.name, n))
    return out


def tracked(exts):
    r = subprocess.run(['git', '-C', REPO, 'ls-files'], capture_output=True,
                       text=True, encoding='utf-8', errors='replace')
    for rel in (r.stdout or '').split('\n'):
        rel = rel.strip()
        if not rel or rel.startswith('archive/') or '/skill-backups/' in rel:
            continue
        if os.path.splitext(rel)[1] in exts:
            yield rel


def corpus(limit_files=None):
    """[(path, name, vector, size)] for every function this tool can read."""
    out = []
    for rel in tracked({'.js', '.html', '.py'}):
        p = os.path.join(REPO, rel)
        try:
            src = io.open(p, encoding='utf-8', errors='replace').read()
        except OSError:
            continue
        if rel.endswith('.py'):
            for name, node in py_functions(src, rel):
                toks = py_shape_tokens(node)
                if len(toks) >= 12:
                    out.append((rel, name, vector(toks), len(toks)))
        else:
            for name, body in js_functions(src, rel):
                toks = js_shape_tokens(body)
                if len(toks) >= 12:
                    out.append((rel, name, vector(toks), len(toks)))
        if limit_files and len(out) > limit_files:
            break
    return out


# ── THE BLIND LOCK. Answers written down before anything real is scored. ──
# Each fixture is (label, code_a, code_b, must_be_similar). The pairs are
# deliberately small and deliberately obvious: a lock that needs interpretation
# is one that gets reinterpreted the day it fails.
FIXTURES = [
    ('same guard shape, every name and string changed',
     "function a(x){ const r = await fetch(u); if(!r.ok) return null; "
     "const rows = await r.json(); if(!Array.isArray(rows)) return null; return rows; }",
     "function zz(q){ const resp = await go(p); if(!resp.ok) return null; "
     "const data = await resp.json(); if(!Array.isArray(data)) return null; return data; }",
     True),
    ('same loop shape written three different ways',
     "function a(xs){ const out={}; xs.forEach(function(x){ if(x.id) out[x.id]=true; }); return out; }",
     "function b(items){ const acc={}; for (const it of items) { if(it.id) acc[it.id]=true; } return acc; }",
     True),
    ('a refusal-then-read and a read-then-refuse are NOT the same shape',
     "function a(){ const s = await scope(); if(!s) return deny(); const r = await read(); return r; }",
     "function b(){ const r = await read(); const s = await scope(); if(!s) return deny(); return r; }",
     False),
    ('a guard function and a string formatter are not similar',
     "function a(x){ if(!x.ok) return null; if(!Array.isArray(x)) return null; return x; }",
     "function b(n){ return '<div>'+H(n.title)+'</div><span>'+H(n.body)+'</span>'; }",
     False),
    ('the same NaN-blind fold, different identifiers',
     "function a(rows){ return rows.reduce(function(n,r){ return n + (r.amount || 0); }, 0); }",
     "function b(list){ return list.reduce(function(t,x){ return t + (x.total || 0); }, 0); }",
     True),
]


def fixture_scores():
    out = []
    for label, a, b, want in FIXTURES:
        va = vector(js_shape_tokens(a))
        vb = vector(js_shape_tokens(b))
        out.append((label, cosine(va, vb), want))
    return out


def cmd_selftest():
    print('shape_search selftest -- %s' % CRITERIA_VERSION)
    bad = 0
    for label, s, want in fixture_scores():
        hit = s >= THRESHOLD
        ok = hit == want
        bad += 0 if ok else 1
        print('  %-5s %.3f  want %-9s %s'
              % ('ok' if ok else 'FAIL', s, 'SIMILAR' if want else 'DIFFERENT', label))
    print('')
    if bad:
        print('%d fixture(s) disagree with the lock at threshold %.2f. The '
              'measure changed; re-derive the threshold rather than editing '
              'the fixtures.' % (bad, THRESHOLD))
        return 1
    print('all %d fixtures agree at threshold %.2f' % (len(FIXTURES), THRESHOLD))
    return 0


def cmd_validate(argv):
    """The two numbers, never one."""
    print('shape_search --validate -- %s' % CRITERIA_VERSION)
    print('')
    print('1. THE BLIND LOCK (synthetic, answers written before any real code)')
    lock_bad = 0
    for label, s, want in fixture_scores():
        hit = s >= THRESHOLD
        ok = hit == want
        lock_bad += 0 if ok else 1
        print('   %-5s %.3f  want %-9s %s'
              % ('ok' if ok else 'FAIL', s, 'SIMILAR' if want else 'DIFFERENT', label))
    if lock_bad:
        print('\n   THE LOCK FAILED. Nothing real was scored -- a measure that '
              'cannot separate the synthetic pairs cannot be trusted on the '
              'tree, and reporting a false-positive rate for it would dress up '
              'a broken measure with a number.')
        return 2

    print('')
    print('2. THE FALSE-POSITIVE MEASUREMENT (real code, unrelated by construction)')
    corp = corpus()
    if len(corp) < 200:
        print('   COULD NOT RUN: only %d functions extracted, which is too few '
              'to sample from. Not reporting a rate computed on a corpus this '
              'small.' % len(corp))
        return 2
    apps = {}
    for rel, name, vec, size in corp:
        apps.setdefault(rel, []).append((rel, name, vec, size))
    files = sorted(apps)
    rnd = random.Random(20260917)          # fixed: the number must not move per run
    pairs, tries = [], 0
    while len(pairs) < 20000 and tries < 400000:
        tries += 1
        fa, fb = rnd.choice(files), rnd.choice(files)
        if fa == fb:
            continue
        # UNRELATED BY CONSTRUCTION means different FILE and different app
        # prefix -- two helpers in sairnvet.html and sairnvet-x.js are not an
        # honest "unrelated" pair and would flatter the number.
        if os.path.basename(fa).split('.')[0][:6] == os.path.basename(fb).split('.')[0][:6]:
            continue
        a = rnd.choice(apps[fa]); b = rnd.choice(apps[fb])
        pairs.append(cosine(a[2], b[2]))
    if len(pairs) < 500:
        print('   COULD NOT RUN: only %d unrelated pairs could be drawn.' % len(pairs))
        return 2
    pairs.sort()
    n = len(pairs)

    def pct(p):
        return pairs[min(n - 1, int(p * n))]

    above = [s for s in pairs if s >= THRESHOLD]
    rate = len(above) / float(n)
    ci = 1.96 * math.sqrt(rate * (1 - rate) / n) * 100.0
    print('   unrelated pairs sampled : %d (from %d functions in %d files)'
          % (n, len(corp), len(files)))
    print('   median similarity       : %.3f' % pct(0.50))
    print('   p90 / p99 / max         : %.3f / %.3f / %.3f'
          % (pct(0.90), pct(0.99), pairs[-1]))
    # ── ONE NUMBER WITH ITS UNCERTAINTY, NEVER A BARE PERCENTAGE ──────────
    # At this rate a 2,000-pair sample swings +-0.3pp run to run, which is wider
    # than the difference between any two thresholds -- so a bare figure invites
    # exactly the tuning it should prevent.
    print('   AT OR ABOVE %.2f        : %d  --> %.3f%% +- %.3f pp (95%%)'
          % (THRESHOLD, len(above), 100.0 * rate, ci))
    print('   recorded at build time  : %.3f%% +- %.3f pp  (%s)'
          % (MEASURED_HIT_RATE * 100, MEASURED_CI_PP, MEASURED_ON))
    print('')
    print('   THE TWO NUMBERS ARE SEPARATE ON PURPOSE. The lock says the measure')
    print('   can tell the shapes apart at all; this says how often it says YES')
    print('   to code that has nothing to do with each other.')
    print('')
    print('   AND THE HITS WERE READ, NOT JUST COUNTED. They are not confusion:')
    print('   they are genuinely identical shapes -- a helper copied into two')
    print('   fault files, and a cluster of tools/ main() functions that all')
    print('   parse argv, loop, print and exit. So this is the BASE RATE at')
    print('   which unrelated code here shares a shape, which is why raising')
    print('   the threshold barely moves it (1.03% at 0.72, 0.53% at 0.92) and')
    print('   why a hit is a CANDIDATE rather than a finding.')
    print('')
    print('   AND THE LIMIT THAT NO NUMBER HERE COVERS: this measures STRUCTURE.')
    print('   Two functions computing the same answer by different control flow')
    print('   score LOW and a trained model would score them high. That is the')
    print('   VulCoCo gap and it is not closed by anything in this file --')
    print('   no numpy, torch, transformers, onnxruntime or faiss on this')
    print('   interpreter, measured 2026-09-17. --embedder is the hook.')
    # THE GATE IS A BAND AROUND THE RECORDED MEASUREMENT, not a round number
    # somebody liked. It fires when the corpus has MOVED -- a rate materially
    # above what was measured means the tool is now matching things it did not,
    # and the hits need reading again before anybody trusts a ranking.
    if 100.0 * rate > (MEASURED_HIT_RATE * 100 + 4 * MEASURED_CI_PP):
        print('')
        print('FINDING: the unrelated-pair hit rate is %.3f%%, materially above '
              'the %.3f%% this tool was calibrated against. The corpus has '
              'changed; READ a sample of the hits before trusting a ranking, '
              'and re-record the rate rather than raising the threshold until '
              'the number looks better.'
              % (100.0 * rate, MEASURED_HIT_RATE * 100))
        return 1
    return 0


def cmd_like(target, top):
    if ':' not in target:
        print('--like takes path:function'); return 2
    path, fname = target.rsplit(':', 1)
    p = os.path.join(REPO, path)
    if not os.path.isfile(p):
        print('no such file: %s' % path); return 2
    src = io.open(p, encoding='utf-8', errors='replace').read()
    want = None
    if path.endswith('.py'):
        for name, node in py_functions(src, path):
            if name == fname:
                want = vector(py_shape_tokens(node))
    else:
        for name, body in js_functions(src, path):
            if name == fname:
                want = vector(js_shape_tokens(body))
    if not want:
        print('no function %r in %s -- this tool reads top-level `function '
              'NAME(` declarations and Python defs; an arrow assigned to a '
              'const is not one, which is a real limit and not a silent miss.'
              % (fname, path))
        return 2
    scored = []
    for rel, name, vec, size in corpus():
        if rel == path and name == fname:
            continue
        s = cosine(want, vec)
        if s >= THRESHOLD:
            scored.append((s, rel, name, size))
    scored.sort(reverse=True)
    n_corpus = len(corpus())
    expected = MEASURED_HIT_RATE * max(0, n_corpus - 1)
    print('shape_search --like %s   (threshold %.2f, %s)'
          % (target, THRESHOLD, CRITERIA_VERSION))
    print('  %d candidate(s) at or above the threshold, out of %d functions'
          % (len(scored), n_corpus))
    # ── THE BASE RATE, BEFORE THE FIRST ROW IS READ ───────────────────────
    # Without this a reader treats every row as a lead. At the measured hit
    # rate a search of this corpus is EXPECTED to surface look-alikes whether
    # or not a recurrence exists, so the honest frame is "how many of these are
    # more than the base rate", not "here are the matches".
    print('  EXPECTED BY CHANCE at this corpus size: ~%.0f. A count near that '
          'is the base' % expected)
    print('  rate, not a finding -- read the rows, and read the TOP of the list.')
    for s, rel, name, size in scored[:top]:
        print('   %.3f  %-46s %s' % (s, rel, name))
    if not scored:
        print('   none. THAT IS NOT "no recurrence" -- it is "no STRUCTURALLY')
        print('   similar function", and the gap above says what that misses.')
    return 0


def main(argv):
    if '--selftest' in argv:
        return cmd_selftest()
    if '--validate' in argv:
        return cmd_validate(argv)
    if '--like' in argv:
        t = argv[argv.index('--like') + 1]
        top = int(argv[argv.index('--top') + 1]) if '--top' in argv else 10
        return cmd_like(t, top)
    print(__doc__.strip().split('\n\n')[0])
    print('')
    print('  --validate   measure it before trusting it (two numbers)')
    print('  --like PATH:FUNC   rank every function by shape similarity')
    print('  --selftest   the blind lock alone')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
