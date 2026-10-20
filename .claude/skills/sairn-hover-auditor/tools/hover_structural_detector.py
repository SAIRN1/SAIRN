#!/usr/bin/env python
"""hover_structural_detector.py -- a PARSER-ADJACENT detector for the four
of five Tier-1 hard2 misses from #1634 that a textual-preprocessing fix can
actually reach, built against a FRESH, FROZEN, hash-committed-and-PUSHED
hard3 seed set rather than widening the regexes that missed them. Built
H1 b73, item 2.

NOT A FULL PARSER, NAMED AS SUCH RATHER THAN OVERCLAIMED. There is no
ECMAScript-grade parser available on this machine without an npm install
(checked: acorn, esprima and typescript are all absent from `node`'s
resolvable modules, confirmed by `require()` failing on each, and this
tool does not install one -- the deny list blocks package installs and an
auditor self-provisioning a toolchain is a change nobody reviewed, the
same stance hover_static_input.py already takes on semgrep). What this
file IS: a small TEXTUAL PREPROCESSING PIPELINE that resolves the specific
structural tricks #1634 measured as defeating a pure substring/regex
match, run BEFORE the existing money/write/guard patterns are applied --
so it is more than a regex (it does real substitution passes over the
source, including one level of indirection through a locally-declared
helper function) and less than a parser (it has no grammar, no scoping,
and would mis-handle code deliberately constructed to confuse it).

WHAT #1634 ACTUALLY MEASURED, AND WHICH PART OF EACH MISS THIS FIXES:
  money-toctou (mt-3)      template literals AND the HTTP verb held in a
                            variable. FIXED by (1) template-literal
                            flattening -- splice `${expr}` content out of
                            backtick strings into the plain text stream so
                            a money-field name mentioned inside one is
                            visible to the existing word list, and
                            (2) single-assignment const-alias resolution
                            -- `const VERB = 'PATCH'` makes `method: VERB`
                            equivalent to `method: 'PATCH'` downstream.
  postgrest-filter-inject. (fi-3)  the SAME template-literal trick, hiding
                            an unencoded interpolated identifier inside a
                            backtick URL. FIXED by the same flattening
                            pass.
  zero-row-false-success   (zr-3)  a Prefer value built by concatenating
                            two string literals, AND a STATUS-CODE check
                            standing in for a row-count check. FIXED by
                            (1) literal-concatenation folding -- `'return='
                            + 'minimal'` folds to `'return=minimal'`
                            before matching, and (2) a RULE change, not a
                            parsing one: a bare `res.status !== N` /
                            `.status >= N` check no longer counts as a
                            guard at all, because it cannot observe how
                            many rows a PostgREST PATCH touched -- only an
                            array-length check on a parsed body can.
  revocation-clobber        (rc-3)  the revocation gate moved into a
                            locally-declared boolean helper function,
                            called as `if (!gate(row, res)) return`.
                            FIXED by ONE level of call-site resolution:
                            find local function declarations whose body
                            checks a revoked/suspended/inactive-like field
                            and early-returns, then treat a call to that
                            function the same as an inline check.

A SECOND LIMITATION, FOUND WHILE WRITING h3-rc-clean AND FIXED IN THE
FIXTURE RATHER THAN CLAIMED AWAY: resolve_helper_gates can only see a
helper function that is DECLARED IN THE SAME SNIPPET IT IS GIVEN. The
first draft of the clean control routed its write through an external
`one_write_cas(...)` helper carrying the real CAS guard -- invisible to
this detector not because the detector is weak, but because a diff
fragment (or any snippet-scoped review, which is the shape every reviewer
in this pipeline actually operates under) never shows the body of a
function it does not also touch. Resolving a guard hidden behind an
UNSHOWN helper is not a parsing problem, it is a missing-context problem,
and no amount of parsing depth fixes it. The clean control was rewritten to
show its CAS guard inline, which is the same convention every other class's
clean control already uses -- the detector was not weakened to pass it.

WHAT THIS DOES NOT FIX, NAMED RATHER THAN SILENTLY DROPPED:
  client-trusted-role (ct-3) -- an unverified, Buffer-decoded JWT payload
    used as if it were a verified session. This is not a structural
    camouflage of an EXISTING signal, it is a NEW UNTRUSTED-SOURCE IDIOM
    this role's detectors never had a category for at all (the old
    detector looked for req.body.role / req.headers[ / session.role as
    "from the client"; a decoded, unverified JWT is a different idiom
    entirely). Fixing it needs a new source-pattern category, not a
    preprocessing pass over an existing one, and is NOT done this batch --
    recorded as the next step rather than folded into a "4 of 5 fixed"
    headline that quietly drops the harder one.

FREEZE-THEN-PUSH, same discipline as hover_injection_defense.py: this file
is committed to the platform repo and pushed to origin/main BEFORE any
case in HARD3_SEEDS is scored by the structural detector, so the frozen
bytes are externally checkable, not merely logged to this role's own
chain.

THE RESIDUAL CIRCULARITY IS NOT REMOVED, STATED AGAIN RATHER THAN DROPPED
A SECOND TIME. I wrote both the preprocessing pipeline and HARD3_SEEDS.
The seeds are once again written to defeat the SPECIFIC mechanisms #1634
measured, which means a clean pass here demonstrates the fix works against
the attacks it was built from -- not that it generalises to a mechanism
nobody has thought of yet. The one genuine out-of-distribution signal in
this file is `hard3-ood`: a variant that chains TWO of the tricks at once
(a template-literal field name AND a const-alias verb in the SAME
snippet), which was not individually designed as a test case but falls out
of composing the two fixes -- if it fails, the two preprocessing passes
interact badly, which is worth knowing and is not assumed away.
"""
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
EXIT_OK = 0
EXIT_LOOK = 1
EXIT_COULD_NOT_RUN = 2

MONEY_RE = re.compile(
    r'\b(amount|balance|total|subtotal|price|cost|fee|fees|credit|credits|'
    r'quota|plan_status|paid|charge|charges|invoice|refund|payment|payout|'
    r'deposit|owed|due|remaining|cents|dollars|amount_due)\b', re.I)

ENCODE_RE = re.compile(r'encodeURIComponent\s*\(')

# A status-code check NO LONGER COUNTS as a guard -- the rule change named
# above, locked here rather than left as prose. `.length` on a parsed body
# is the only thing accepted.
ROWCOUNT_GUARD_RE = re.compile(
    r"\.length\s*===?\s*0|\.length\s*<\s*1|Array\.isArray\([^)]*\)\s*&&"
    r"|on_conflict|resolution=merge-duplicates|rpc/|&\w+=eq\.\w|is\.null"
    r"|return=representation")

STATUS_ONLY_RE = re.compile(
    r'res(?:ponse)?\s*\.\s*status\s*(?:!==|>=|===|<)\s*\d')

WRITE_METHOD_RE = re.compile(r"method:\s*'(PATCH|PUT|POST)'")

REVOKED_FIELD_RE = re.compile(
    r"\b(revoked|suspended|inactive|disabled|deactivated)\b", re.I)
EARLY_RETURN_RE = re.compile(r'\breturn\b')


# ── PREPROCESSING PASS 1: TEMPLATE-LITERAL FLATTENING ───────────────────────
_SUBST_RE = re.compile(r'\$\{([^{}]*)\}')


def flatten_template_literals(code):
    """Expose every `${expr}` substitution AS AN ADDITIONAL WORD next to
    it, WITHOUT discarding the literal text around it. `${...}` syntax only
    ever appears inside a backtick string in real JS, so this is safe to
    apply to the whole text directly rather than first locating template-
    literal boundaries.

    FOUND BY ITS OWN FIXTURE FAILING: the first version of this function
    replaced the ENTIRE backtick string with just the substitution's inner
    content, which silently deleted plain literal text sitting next to a
    substitution -- `select=total` in mt-3's own read URL vanished along
    with everything else in the string, so the money-word check that was
    supposed to find "total" found nothing, for a reason that had nothing
    to do with money-word matching at all. T1 caught it; this is the fix,
    and T1 is kept rather than loosened."""
    return _SUBST_RE.sub(lambda m: ' ' + m.group(1) + ' ', code)


# ── PREPROCESSING PASS 2: ADJACENT STRING-LITERAL CONCATENATION FOLDING ────
_CONCAT_RE = re.compile(r"""['"]([^'"]*)['"]\s*\+\s*['"]([^'"]*)['"]""")


def fold_literal_concat(code):
    """`'a' + 'b'` -> `'ab'`, repeatedly, so a value assembled from two (or
    chained, via repeated application) literal pieces reads the same as if
    it had been written as one literal. Fixes zr-3's Prefer header."""
    prev = None
    while prev != code:
        prev = code
        code = _CONCAT_RE.sub(lambda m: "'%s%s'" % (m.group(1), m.group(2)), code)
    return code


# ── PREPROCESSING PASS 3: SINGLE-ASSIGNMENT CONST-ALIAS RESOLUTION ─────────
_CONST_RE = re.compile(r"""const\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*=\s*['"]([^'"]*)['"]\s*;""")


def resolve_const_aliases(code):
    """`const VERB = 'PATCH';` then every bare `VERB` elsewhere in the same
    text is replaced with `'PATCH'`. Deliberately NAIVE -- no scoping, no
    shadowing check, which is exactly the parser-vs-preprocessor line named
    in the module docstring. Fixes mt-3's method-in-a-variable trick."""
    for m in _CONST_RE.finditer(code):
        name, val = m.group(1), m.group(2)
        code = re.sub(r'(?<![\w$])%s(?![\w$])' % re.escape(name),
                       "'%s'" % val, code)
    return code


# ── PREPROCESSING PASS 4: ONE-LEVEL HELPER-FUNCTION GATE RESOLUTION ────────
_FUNC_DECL_RE = re.compile(
    r'function\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*\([^)]*\)\s*\{([^}]*)\}',
    re.DOTALL)


def resolve_helper_gates(code):
    """If a locally-declared function's body checks a revoked/suspended-
    like field and returns, splice a synthetic inline marker
    `/*HELPER_GATE:revoked*/` at every call site of that function so the
    existing gate-detection regex (which looks for the field check
    textually) finds it through the one level of indirection. Fixes rc-3."""
    gate_names = []
    for m in _FUNC_DECL_RE.finditer(code):
        name, body = m.group(1), m.group(2)
        if REVOKED_FIELD_RE.search(body) and EARLY_RETURN_RE.search(body):
            gate_names.append(name)
    for name in gate_names:
        code = re.sub(
            r'(?<![\w$])%s\s*\(' % re.escape(name),
            '/*HELPER_GATE:revoked*/ %s(' % name, code)
    return code


def preprocess(code):
    """The full pipeline, in a fixed order. Order matters: const-alias
    resolution must run before the method/write check reads a literal, and
    template flattening must run before the money-word list reads field
    names -- both are applied unconditionally since neither pass can make a
    clean snippet LESS clean (folding and flattening are additive, never
    destructive of a real guard token)."""
    code = flatten_template_literals(code)
    code = fold_literal_concat(code)
    code = resolve_const_aliases(code)
    code = resolve_helper_gates(code)
    return code


def detect_money_toctou(code):
    p = preprocess(code)
    has_write = bool(WRITE_METHOD_RE.search(p))
    has_money = bool(MONEY_RE.search(p))
    has_guard = bool(ROWCOUNT_GUARD_RE.search(p))
    # A read signal: a second reference to the same REST path pattern, or a
    # dedicated read function name, distinct from the write itself.
    has_read = bool(re.search(r'select=|readAmt|readCount', p))
    return has_write and has_money and has_read and not has_guard


def detect_filter_injection(code):
    """REGRESSION FOUND AND FIXED by re-running this detector against b72's
    ORIGINAL seeds (fi-1/fi-2), not only the fresh hard3 set: the first
    version only recognised the TEMPLATE-LITERAL evasion and scored 0/1 on
    both the easy and hard seeds from b71/b72, which never used a template
    literal at all -- they spliced the identifier in with `+` concatenation,
    the ORIGINAL #1599 shape. A detector built to fix one evasion regressed
    on the shape it was supposed to already cover. Both mechanisms are
    checked now, and this was re-verified against the wider population
    rather than only the fresh fixtures that motivated the rewrite."""
    # Mechanism A: `+`-concatenation splicing an identifier in front of
    # `eq.`, unencoded -- the original #1599 shape.
    concat = re.search(r"=eq\.'\s*\+\s*(?!encodeURIComponent)\w", code)
    # Mechanism B: a template-literal substitution landing right after
    # `eq.`, unencoded -- this batch's fresh evasion.
    had_template = bool(re.search(r'eq\.\$\{[^}]*\}', code))
    encoded = bool(ENCODE_RE.search(code))
    return (bool(concat) or had_template) and not encoded


def detect_zero_row(code):
    p = preprocess(code)
    minimal = "return=minimal" in p
    if not minimal:
        return False
    if ROWCOUNT_GUARD_RE.search(p):
        return False
    # A status-code check alone does NOT clear it -- the rule change.
    return True


def detect_revocation_clobber(code):
    p = preprocess(code)
    gated = bool(REVOKED_FIELD_RE.search(p)) and (
        'HELPER_GATE' in p or re.search(r"==+\s*'revoked'|!\w+\.active", p))
    if not gated:
        return False
    write = re.search(r"suspended:\s*false|active:\s*true|status:\s*'active'",
                       p)
    if not write:
        return False
    guarded = re.search(r'status=neq\.|&active=eq\.|return=representation', p)
    return not guarded


DETECTORS = {
    'money-toctou': detect_money_toctou,
    'postgrest-filter-injection': detect_filter_injection,
    'zero-row-false-success': detect_zero_row,
    'revocation-clobber': detect_revocation_clobber,
}


# ── THE FRESH, FROZEN HARD3 SET -- b73, item 2 ──────────────────────────────
# (case_id, cls, kind, code, expect_flagged)
HARD3_SEEDS = (
    ('h3-mt-flagged', 'money-toctou', 'hard3', """
async function reprice(c, id, delta) {
  const row = (await (await fetch(c.rest(`quotes?id=eq.${id}&select=total`))).json())[0];
  const VERB = 'PATCH';
  await fetch(c.rest(`quotes?id=eq.${id}`), {
    method: VERB, headers: c.headers, body: JSON.stringify({ total: row.total + delta })
  });
}
""", True),
    ('h3-mt-clean', 'money-toctou', 'clean', """
async function reprice(c, id, delta, prior) {
  const VERB = 'PATCH';
  const r = await fetch(c.rest(`quotes?id=eq.${id}&total=eq.${prior}`), {
    method: VERB, headers: Object.assign({}, c.headers, { Prefer: 'return=representation' }),
    body: JSON.stringify({ total: prior + delta })
  });
  if ((await r.json()).length === 0) throw new Error('CAS lost');
}
""", False),

    ('h3-fi-flagged', 'postgrest-filter-injection', 'hard3', """
const q = `${U}/rest/v1/dnt_ledger?patient_id=eq.${req.query.pid}&select=*`;
const r = await fetch(q, { headers: H });
""", True),
    ('h3-fi-clean', 'postgrest-filter-injection', 'clean', """
const q = `${U}/rest/v1/dnt_ledger?patient_id=eq.${encodeURIComponent(req.query.pid)}&select=*`;
const r = await fetch(q, { headers: H });
""", False),

    ('h3-zr-flagged', 'zero-row-false-success', 'hard3', """
const PREF = 'return=' + 'minimal';
async function closeClaim(u, h, claimId) {
  const res = await fetch(`${u}/rest/v1/claims?id=eq.${claimId}`, {
    method: 'PATCH', headers: { ...h, Prefer: PREF },
    body: JSON.stringify({ state: 'closed' })
  });
  if (res.status !== 204) { throw new Error('upstream ' + res.status); }
  log(`claim ${claimId} closed`);
}
""", True),
    ('h3-zr-clean', 'zero-row-false-success', 'clean', """
async function closeClaim(u, h, claimId) {
  const res = await fetch(`${u}/rest/v1/claims?id=eq.${claimId}`, {
    method: 'PATCH', headers: { ...h, Prefer: 'return=representation' },
    body: JSON.stringify({ state: 'closed' })
  });
  const rows = await res.json();
  if (!Array.isArray(rows) || rows.length === 0) throw new Error('matched ZERO rows');
}
""", False),

    ('h3-rc-flagged', 'revocation-clobber', 'hard3', """
function gate(row, res) {
  if (row.suspended) { res.status(403).end(); return false; }
  return true;
}
const row = await one(U, H, 'staff', id);
if (!gate(row, res)) return;
await one_write(U, H, 'staff', id, Object.assign({}, { suspended: false }, touch()));
""", True),
    ('h3-rc-clean', 'revocation-clobber', 'clean', """
function gate(row, res) {
  if (row.suspended) { res.status(403).end(); return false; }
  return true;
}
const row = await one(U, H, 'staff', id);
if (!gate(row, res)) return;
const w = await fetch(U + '/rest/v1/staff?id=eq.' + id + '&status=neq.revoked', {
  method: 'PATCH', headers: Object.assign({}, H, { Prefer: 'return=representation' }),
  body: JSON.stringify(Object.assign({}, { suspended: false }, touch()))
});
if ((await w.json()).length === 0) { res.status(403).end(); return; }
""", False),

    ('h3-ood-double-trick', 'money-toctou', 'ood', """
const VERB = 'PATCH';
async function settle(c, id) {
  const row = (await (await fetch(c.rest(`ledger?id=eq.${id}&select=balance`))).json())[0];
  await fetch(c.rest(`ledger?id=eq.${id}`), {
    method: VERB, headers: { Prefer: 'return=minimal' },
    body: JSON.stringify({ balance: row.balance - 100 })
  });
}
""", True),
)


def answer_key_hash():
    canon = json.dumps([[c[0], c[1], c[2], c[3], c[4]] for c in HARD3_SEEDS],
                        sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(canon.encode('utf-8')).hexdigest()


def score():
    """[(case_id, cls, expected, actual, ok)]"""
    out = []
    for cid, cls, kind, code, expect in HARD3_SEEDS:
        fn = DETECTORS.get(cls)
        actual = bool(fn(code)) if fn else None
        out.append((cid, cls, expect, actual, actual == expect))
    return out


def selftest():
    ok = [0]
    bad = [0]

    def ck(name, cond):
        if cond:
            ok[0] += 1
            print('  ok   %s' % name)
        else:
            bad[0] += 1
            print('  FAIL %s' % name)

    ck('H1 the hard3 answer-key hash is stable', answer_key_hash() == answer_key_hash())
    ck('H2 the hash is 64 hex chars', re.fullmatch(r'[0-9a-f]{64}', answer_key_hash()) is not None)
    ck('H3 every class in HARD3_SEEDS has a registered detector',
       all(c[1] in DETECTORS for c in HARD3_SEEDS))

    results = score()
    for cid, cls, expect, actual, correct in results:
        ck('H4[%s/%s] structural detector scores %s as pre-committed '
           '(got %s)' % (cid, cls, expect, actual), correct)

    ck('H5 EVERY hard3 case agrees with its pre-committed answer, '
       'including the OOD double-trick case composing two fixes at once',
       all(r[4] for r in results))

    # Preprocessing passes, unit-tested in isolation, each with a KNOWN-GOOD
    # control proving the pass does not corrupt code that needed no fix.
    ck('T1 template flattening exposes a field name hidden inside a '
       'backtick substitution', 'total' in flatten_template_literals(
           '`quotes?id=eq.${id}&select=total`'))
    ck('T1b KNOWN-GOOD CONTROL -- flattening a string with NO substitution '
       'leaves it byte-identical',
       flatten_template_literals('`plain string, no subst`')
       == '`plain string, no subst`')

    ck('T2 literal concatenation folds to one literal',
       fold_literal_concat("'return=' + 'minimal'") == "'return=minimal'")
    ck('T2b KNOWN-GOOD CONTROL -- a non-literal concatenation (a bare '
       'identifier on one side) is left ALONE, because folding it would '
       'fabricate a value that was never a compile-time constant',
       fold_literal_concat("x + 'minimal'") == "x + 'minimal'")

    ck('T3 a single-assignment const alias resolves at every use site',
       "method: 'PATCH'" in resolve_const_aliases(
           "const VERB = 'PATCH';\nfetch(x, { method: VERB });"))
    ck('T3b KNOWN-GOOD CONTROL -- a const holding something OTHER than a '
       'bare string literal (an object, a call result) is left alone, '
       'because this pass only resolves the one shape it is sure of',
       'buildHeaders()' in resolve_const_aliases(
           "const H = buildHeaders();\nfetch(x, { headers: H });"))

    gated_src = ("function gate(row,res){ if(row.suspended){return false;} "
                 "return true; }\nif (!gate(row,res)) return;")
    ck('T4 a call to a locally-declared revocation-gate helper is marked',
       'HELPER_GATE' in resolve_helper_gates(gated_src))
    nongate_src = ("function fmt(row){ return row.name.toUpperCase(); }\n"
                   "const label = fmt(row);")
    ck('T4b KNOWN-GOOD CONTROL -- a helper with NO revoked-like field check '
       'is NOT marked, so this pass does not treat every function call as '
       'a gate', 'HELPER_GATE' not in resolve_helper_gates(nongate_src))

    print('%d ok, %d failed' % (ok[0], bad[0]))
    return EXIT_OK if not bad[0] else EXIT_LOOK


def main(argv):
    if '--selftest' in argv:
        return selftest()
    if '--freeze' in argv:
        print('FRESH HARD3 ANSWER KEY -- hash this and push the file '
              'containing it BEFORE scoring anything:')
        print('  sha256 %s  (%d cases)' % (answer_key_hash(), len(HARD3_SEEDS)))
        for cid, cls, kind, code, expect in HARD3_SEEDS:
            print('    %-22s %-28s %-6s expect_flagged=%s' % (cid, cls, kind, expect))
        return EXIT_OK
    if '--score' in argv:
        for cid, cls, expect, actual, correct in score():
            print('%-22s %-28s expected=%-5s actual=%-5s %s'
                  % (cid, cls, expect, actual, 'OK' if correct else 'WRONG'))
        return EXIT_OK if all(r[4] for r in score()) else EXIT_LOOK
    print('usage: --freeze | --score | --selftest')
    return EXIT_COULD_NOT_RUN


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
