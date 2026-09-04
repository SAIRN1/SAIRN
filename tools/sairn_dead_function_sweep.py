"""sairn_dead_function_sweep.py -- EVERY function nothing references, not just
the restore-shaped ones.

WHY THIS EXISTS ALONGSIDE sairn_reachability_probe.py, WHICH ALREADY RAN.
That probe swept all 16 apps on 2026-08-30 and reported "one real instance
found". Its own source shows why that number was about a narrow question and
not about the platform:

    targets = [n for n in F if RESTORE.match(n)]

RESTORE is a name whitelist -- reverify|restore|resume|rehydrate|recheck|
checksession|loadstate|hydrate|refreshsession|validatetrial|checktrial|
checklicen|verifylicen|checkauth|restoresession|bootstrapsession. Every
function whose name does not match was never examined at all. That was the
right scope for the question it was asking (the SAIRNcash returning-customer
gap) and it found `mechRestore` correctly. It is the wrong scope for "what
else is dead."

THE EVIDENCE THAT THE GAP IS REAL, not hypothetical. On 2026-08-31, working
sairnmechanical.html by hand, EIGHT zero-caller functions turned up in the one
file the probe had already flagged -- loadWeather, renderRangeBars, crSave,
crPostGL, crUpdate, aiFollowUp, loadPricing, loadLastSync. None matches
RESTORE, so none was ever a candidate. Two of them mattered: loadWeather left
a panel reading "Loading weather..." forever, and crSave/crPostGL were an
abandoned second Check Register that wrote the live cheque key with its own
counter and toasted "Posted to GL" without posting.

THE SIGNAL, taken from the probe's own header: **CALLERS=0 needs no
entry-point tracing.** A function nothing references anywhere is dead however
the app is entered. So this tool does not trace reachability at all -- no
entry points, no transitive closure, no guessing which button is the real
door. It counts references. That is why it can be strict where the probe had
to hedge.

COMMENTS ARE STRIPPED BEFORE COUNTING, and the direction of that error is
deliberate. A function named in a comment ("// exportCSV() deleted 2026-08-27")
would otherwise count as referenced and be silently skipped -- a FALSE
NEGATIVE, a dead function this tool tells you is fine. Stripping comments
removes that. It cannot create a false positive: stripping only ever lowers a
count, and a count of 1 means the definition and nothing else.

TWO LISTS, because they need different handling and merging them would make
the strict one untrustworthy:

  DEAD (refs == 1)  The definition is the only occurrence of the name in the
                    whole file, comments excluded. No judgment call. This is
                    the column to act on.

  EXPORT-ONLY       Every reference is `window.NAME = NAME` or an alias
                    (`window.other = NAME`). NEEDS A HUMAN. The function may
                    be invoked from markup under the ALIAS name, which this
                    tool does not chase, so a hit here is a prompt to read the
                    file, not a finding. Reported separately and never counted
                    in the DEAD total.

KNOWN LIMITS, stated rather than discovered later. Object-literal methods
(`foo: function(){}`) and class methods are not collected as definitions, so
they are neither reported nor cleared -- they are out of scope, not passed.
Cross-file calls are not considered; these are single-file apps, and any that
stops being one breaks this assumption. A name referenced only inside a
string this tool does not parse as code would still be counted, since it
counts word occurrences in the whole stripped text rather than parsed calls.

This is a REPORT, not a gate. Nothing it prints should be deleted without
reading the site first -- the 2026-08-30 lesson was that four checkers in one
day over-reported on their first draft, and the fix is hand-verification
before action, not confidence in the tool.
"""
import re, sys, glob, os

# The one shared comment stripper. Four tools in tools/ were found blind on
# 2026-09-04; see the measured table in jscomments.py's docstring.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jscomments as _jscomments

DEF_PATTERNS = [
    re.compile(r'\bfunction\s+([A-Za-z_$][\w$]*)\s*\('),
    re.compile(r'(?:window\.|var\s+|let\s+|const\s+)([A-Za-z_$][\w$]*)\s*=\s*(?:async\s+)?function\b'),
    re.compile(r'(?:var\s+|let\s+|const\s+)([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>'),
]


SCRIPT_BLOCK = re.compile(r'(<script\b[^>]*>)(.*?)(</script\s*>)', re.S | re.I)


def _blank(m):
    return re.sub(r'\S', ' ', m.group(0))


def strip_comments(s):
    """Remove HTML comments everywhere, and JS comments ONLY inside <script>.

    Replaced with spaces of equal length so byte offsets stay usable and no two
    identifiers get accidentally glued together.

    THE SCRIPT SCOPING IS NOT TIDINESS, IT IS THE BUG THAT MADE THE FIRST RUN
    WRONG. Applying the JS block-comment rule to the whole document let this
    markup open a comment:

        <input type="file" accept="image/*" capture="environment" ...>

    The `/*` in the MIME wildcard matched, `.*?` ran forward 204,534 characters
    to the first `*/` -- which lived inside a regex literal in a later script --
    and blanked 80.5% of sairncare.html. Every identifier in that span
    disappeared, so `init`, `saveFacility` and seven others were reported DEAD
    while `onclick="saveFacility()"` was sitting in the markup the whole time.
    Nine of that app's twelve functions, all false. Caught by grepping the raw
    file for one name the tool had just called dead.

    Inside a script the same hazard is smaller but not zero -- a regex literal
    can still contain `/*` -- which is what the size guard in sweep() is for.

    ── AND "SMALLER BUT NOT ZERO" WAS 218 OF 1003 (2026-09-04) ───────────────
    Measured rather than estimated: the in-script `/\\*.*?\\*/` was still losing
    218 of stonedesk.html's 1003 function declarations -- 21.7% of the largest
    app on the platform -- while losing 0 on sairnvet and sairncare. Good on
    two apps and materially blind on the one that matters most, which is why a
    per-app spot check would have missed it.

    The JS half now goes through tools/jscomments.py, which walks the source
    with a real lexer and skips strings, template literals and regex literals,
    so a `/*` inside any of them cannot open a comment. Everything above still
    holds and is why it is applied PER SCRIPT BLOCK rather than to the whole
    document: jscomments knows JS, not HTML, so letting it near markup text
    would strip a bare `//` outside quotes. The scoping this tool learned the
    hard way is kept; only the blunt instrument inside it is replaced.
    """
    s = re.sub(r'<!--.*?-->', _blank, s, flags=re.S)

    def scrub(m):
        return m.group(1) + _jscomments.strip_comments(m.group(2)) + m.group(3)

    return SCRIPT_BLOCK.sub(scrub, s)


def _is_declaration(s, at):
    """True if `function NAME(` at offset `at` is a hoisted DECLARATION.

    A named function EXPRESSION is not dead just because its name is never
    referenced -- it is being used where it sits. The shape that matters here:

        (function init(){ ... })();

    sairnroofing.html runs its whole startup that way. `init` appears exactly
    once in the file, so a reference count alone calls it dead when it is in
    fact executing on every page load. Same for a named callback,
    `setTimeout(function tick(){...}, 0)`.

    A declaration follows `;`, `{`, `}`, the `>` closing a <script> tag, or the
    start of the file. An expression follows `(`, `=`, `,` or `:`. Only the
    former is collected.
    """
    i = at - 1
    while i >= 0 and s[i].isspace():
        i -= 1
    # Step back over a leading `async`. Without this, `async function foo(){}`
    # sees `c` and is discarded as an expression -- so every async declaration
    # in the platform silently left the sweep. stonedesk's vmAnalyze vanished
    # from the findings that way between two runs, which is how it was caught:
    # a finding disappearing without a fix is as suspicious as one appearing.
    if i >= 4 and s[i - 4:i + 1] == 'async':
        i -= 5
        while i >= 0 and s[i].isspace():
            i -= 1
    if i < 0:
        return True
    return s[i] in ';{}>'


def definitions(s):
    d = {}
    for pat in DEF_PATTERNS:
        for m in pat.finditer(s):
            if pat is DEF_PATTERNS[0] and not _is_declaration(s, m.start()):
                continue
            # start of the NAME, not of the `function` keyword. The
            # export-only pass compares this against reference offsets, and
            # with m.start() they never coincide -- so the definition itself
            # counted as a substantive reference and NOTHING was ever
            # classified export-only. Caught on the synthetic probe, where
            # `window.viaAlias = exportedOnly` was silently reported clean.
            d.setdefault(m.group(1), m.start(1))
    return d


def ref_regex(name):
    """Occurrences of `name` as an identifier, INCLUDING `window.name`.

    Two branches rather than one, because Python requires fixed-width
    lookbehind and these two are different widths. Without the second branch a
    function called only as `window.loadWeather()` reads as dead -- which it
    is not, and that exact shape is live in sairnmechanical.html.

    Every definition form contributes EXACTLY ONE match here -- `function f(`
    and `var f = function` via branch one, `window.f = function` via branch
    two -- so subtracting 1 gives real references regardless of how the
    function was declared. That mattered: counting only bare identifiers made
    `window.doRegister = function(){}` report refs=0 while `function foo(){}`
    reported refs=1 for the same emptiness, so one threshold could not serve
    both and a genuinely-called window.* function would have been called dead.
    """
    n = re.escape(name)
    return re.compile(r'(?:(?<![.\w$])' + n + r'|(?<=window\.)' + n + r')(?![\w$])')


IDENT = re.compile(r'[A-Za-z_$][\w$]*')


def index_identifiers(code):
    """Every identifier occurrence in ONE pass, name -> [offsets].

    Was a per-function regex scan of the whole file. That is O(functions x
    bytes) and stonedesk.html is ~2MB with hundreds of functions, so a full
    19-app run did not finish inside two minutes. Same results, one pass.

    An occurrence is kept if it is not preceded by `.`, OR is preceded by
    exactly `window.` -- matching ref_regex()'s two branches, which stay in the
    file as the readable statement of that rule.
    """
    idx = {}
    for m in IDENT.finditer(code):
        s = m.start()
        if s and code[s - 1] == '.':
            if not code[max(0, s - 7):s] == 'window.':
                continue
        idx.setdefault(m.group(0), []).append(s)
    return idx


def sweep(path):
    raw = open(path, encoding='utf-8', errors='replace').read()
    code = strip_comments(raw)
    # Size guard. A runaway comment match is silent and catastrophic -- it does
    # not error, it just deletes identifiers and turns live functions into
    # findings. 80.5% of sairncare.html vanished this way and the run still
    # exited 0. Real comment density in these files is single-digit percent, so
    # anything past 25% means a delimiter ran away and the output must not be
    # read as a result.
    blanked = sum(1 for a, b in zip(raw, code) if a != b)
    pct = 100.0 * blanked / max(1, len(raw))
    if pct > 25:
        print('WARNING %s: comment stripping blanked %.1f%% of the file -- a '
              'delimiter has almost certainly run away. Findings below are NOT '
              'trustworthy.' % (os.path.basename(path), pct))
    defs = definitions(code)
    idx = index_identifiers(code)
    dead, export_only = [], []
    for name in sorted(defs):
        offsets = idx.get(name, [])
        real = len(offsets) - 1       # minus the definition itself
        if real <= 0:
            dead.append((name, real))
            continue
        # An export/alias line -- `window.x = name;` -- contributes up to two
        # matches (the window.x LHS when x == name, and the bare RHS) and
        # proves nothing about the function being invoked.
        substantive = 0
        for off in offsets:
            if off == defs[name]:
                continue
            seg = code[max(0, off - 80):off + len(name) + 4]
            if re.search(r'window\.[\w$]+\s*=\s*' + re.escape(name) + r'\s*[;,\n]', seg):
                continue
            substantive += 1
        if substantive == 0:
            export_only.append((name, real))
    return defs, dead, export_only


def main(paths):
    total_defs = total_dead = 0
    for path in paths:
        defs, dead, export_only = sweep(path)
        total_defs += len(defs)
        total_dead += len(dead)
        status = 'DEAD:%-3d' % len(dead) if dead else 'clean   '
        print('%s %-26s functions=%-4d export-only=%d' %
              (status, os.path.basename(path), len(defs), len(export_only)))
        for name, n in dead:
            print('        DEAD          %s  (refs=%d)' % (name, n))
        for name, n in export_only:
            print('        export-only?  %s  (refs=%d) -- READ THE FILE, may be called under an alias' % (name, n))
    print('\nTOTAL_FUNCTIONS:%d' % total_defs)
    print('TOTAL_DEAD:%d' % total_dead)
    print('Comments stripped before counting. DEAD = the definition is the only '
          'occurrence of the name. Verify each site by hand before deleting.')


if __name__ == '__main__':
    args = sys.argv[1:] or sorted(glob.glob('*.html'))
    main(args)
