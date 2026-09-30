"""Which resources persist raw MODEL OUTPUT? Derived twice, from opposite directions.

Run:  python tools/ai_output_resource_scan.py
      python tools/ai_output_resource_scan.py --root <dir>     # a fixture tree
      python tools/ai_output_resource_scan.py --evidence       # with the lines

── WHY TWO DERIVATIONS AND NOT ONE ────────────────────────────────────────
Raw AI scan text is persisted with no redaction. An auditor found it in
bld_photo_analyses, grd_progress_photos, scp_progress_photos and rf_photos by
walking FORWARD from the model call -- and found bld_ai_chat and
grd_ecosystem_reports only by working BACKWARD from the store.

THAT ASYMMETRY IS THE FINDING ABOUT THE METHOD, not a detail. Two resources
holding raw model output were invisible to a forward walk, so one direction is
not a universe and a single-method answer would have been reported as complete
while missing a third of the set.

FORWARD  starts at a model RESPONSE PARSE -- `data.content[0].text`, or a call
         to a function whose own body fetches the AI proxy -- and walks to any
         store reached from there: directly in the same function, through a
         module-level variable that function assigns, or through a function it
         calls passing the text along.

BACKWARD starts at every STORE SITE and walks the other way: which identifiers
         does the stored expression read, and is any of them assigned from a
         response parse anywhere in the file.

A resource found by ONLY ONE method is printed under its own heading. It is
never silently unioned in, because "both methods agree" and "one method found
it and the other is blind to that shape" are different states and only the
first is corroboration.

── WHAT IS STRIPPED, AND WHAT IS NOT ──────────────────────────────────────
COMMENTS ARE STRIPPED. sairnbuild.html:8066 is a comment reading "also gets
permanently saved into bld_ai_chat history if not caught" -- a text scanner
reads that as provenance for bld_ai_chat and is right by accident, which is
worse than being wrong, because the next comment it believes will not be.

STRING LITERALS ARE STRIPPED FOR PROVENANCE AND KEPT FOR RESOURCE NAMES, and
the asymmetry is deliberate. A system prompt naming a resource is not a store;
but `st('bld_ai_chat', list)` carries the resource name IN a string literal and
there is no other place to read it from. So resource names are extracted from
the un-stripped source at store-call positions found in the STRIPPED source --
the call has to be real code, the name may be a literal.

── WHAT IT CANNOT DO, STATED RATHER THAN IMPLIED ──────────────────────────
It is not a data-flow engine and does not pretend to be one on a 2MB
single-file app. It is a two-direction NARROWER: it takes ~1,500 store sites
down to a few dozen candidates and prints the evidence line for each, so every
one is confirmed by reading the real code. A candidate is a lead until read.
Both counts are printed, never a single number, and the file count is printed
so a shrinking universe is visible. An unreadable file is exit 2 COULD NOT RUN.
"""
import argparse
import io
import os
import re
import sys

EXIT_CLEAN = 0
EXIT_FINDING = 1
EXIT_COULD_NOT_RUN = 2

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# A model response parse. The three shapes this platform actually uses.
RESPONSE_PARSE = (
    re.compile(r'content\s*\[\s*0\s*\]\s*\.\s*text'),
    re.compile(r'\.content\s*&&\s*\w+\.content'),
    re.compile(r'\bstopReason\b|\btool_use\b'),
)
PROXY_FETCH = re.compile(r'/api/claude|\bPROXY\b')

# A store. `st(` is the shared localStorage+sync writer every app carries;
# `xData('write', '<res>'` is the direct server write.
STORE_LOCAL = re.compile(r"\bst\s*\(\s*'([a-z][a-z0-9_]+)'")
STORE_SERVER = re.compile(r"\w*[Dd]ata(?:Raw)?\s*\(\s*'write'\s*,\s*'([a-z][a-z0-9_]+)'")

IDENT = re.compile(r'[A-Za-z_$][\w$]*')


SPAN_PRECEDERS = set('(,=:[!&|?{};+-*%~^<>') | {chr(10), chr(13)}


def lex_spans(src):
    """ONE left-to-right pass returning (comments, literals) as (start, end) lists.

    THE TWO-PASS VERSION WAS WRONG AND LOST WHOLE FUNCTIONS WITHOUT SAYING SO.
    It blanked comments first, unconditionally, then strings. sairnscape.html
    carries `"... built by SAIRN Tech LLC.\n\n..."` and URLs containing `//`
    inside string literals, so the line-comment blanker fired INSIDE a string
    and erased the rest of that line -- on a long line that meant real code.
    `function scpUploadProgressPhoto(` vanished from the stripped source, its
    brace span was never built, and scp_progress_photos -- one of the four
    resources the auditor had already confirmed -- was reported as absent. No
    error, no warning, a shorter answer that looked complete.

    Getting it right needs ONE scan in which a string, a template, a regex, a
    block comment and a line comment all compete at the same position and the
    first one to start wins. Two passes cannot express that, whichever order
    they run in.
    """
    n = len(src)
    comments, literals = [], []
    i = 0
    while i < n:
        c = src[i]
        if c == '/' and i + 1 < n and src[i + 1] == '*':
            j = src.find('*/', i + 2)
            j = n if j < 0 else j + 2
            comments.append((i, j))
            i = j
            continue
        if c == '/' and i + 1 < n and src[i + 1] == '/':
            j = src.find(chr(10), i)
            j = n if j < 0 else j
            comments.append((i, j))
            i = j
            continue
        if c == '/':
            # Regex literal, but only where a value may start -- otherwise it
            # is division. A regex cannot span a line, and `/` inside a
            # character class is not a terminator.
            k = i - 1
            while k >= 0 and src[k] in ' 	':
                k -= 1
            if k < 0 or src[k] in SPAN_PRECEDERS:
                j, cls = i + 1, False
                while j < n and src[j] != chr(10):
                    if src[j] == chr(92):
                        j += 2
                        continue
                    if src[j] == '[':
                        cls = True
                    elif src[j] == ']':
                        cls = False
                    elif src[j] == '/' and not cls:
                        j += 1
                        break
                    j += 1
                literals.append((i, j))
                i = j
                continue
            i += 1
            continue
        if c == '"' or c == "'" or c == '`':
            j = i + 1
            while j < n:
                if src[j] == chr(92):
                    j += 2
                    continue
                if src[j] == c:
                    j += 1
                    break
                if src[j] == chr(10) and c != '`':
                    break
                j += 1
            literals.append((i, j))
            i = j
            continue
        i += 1
    return comments, literals


def _blank(src, spans):
    out = list(src)
    n = len(src)
    for a, b in spans:
        for k in range(a, min(b, n)):
            if out[k] != chr(10):
                out[k] = ' '
    return ''.join(out)


def strip_comments(src):
    """Comments blanked, string/template/regex literals intact. Line numbering
    preserved exactly, so every reported line number still points at the real
    line."""
    comments, _lit = lex_spans(src)
    return _blank(src, comments)


def strip_strings(src):
    """Comments AND literals blanked. Takes the ORIGINAL source, not the
    comment-stripped one, because the lexer has to see both to decide which
    construct starts first at any position."""
    comments, literals = lex_spans(src)
    return _blank(src, comments + literals)


def function_spans(code):
    """[(name, start, end)] for every `function NAME(` body, by brace matching."""
    spans = []
    for m in re.finditer(r'\bfunction\s+([A-Za-z_$][\w$]*)\s*\(', code):
        b = code.find('{', m.end())
        if b < 0:
            continue
        depth, k = 0, b
        while k < len(code):
            if code[k] == '{':
                depth += 1
            elif code[k] == '}':
                depth -= 1
                if depth == 0:
                    break
            k += 1
        if depth == 0:
            spans.append((m.group(1), m.start(), k + 1))
    return spans


def line_of(code, off):
    return code.count('\n', 0, off) + 1


def raw_line(raw, lineno):
    lines = raw.split('\n')
    return lines[lineno - 1].strip()[:150] if 0 < lineno <= len(lines) else ''


def store_sites(code_nostr, raw_code):
    """[(resource, offset)] -- the CALL must be real code, the NAME may be a
    literal. Positions are found in string-stripped code (so a prompt that
    happens to contain `st('x'` is not a call), then the name is read back out
    of the comment-stripped-but-string-bearing source at that same offset."""
    # THE HEADS ARE WRITTEN OUT, NOT DERIVED BY STRING SURGERY ON THE FULL
    # PATTERNS. The first version built them with
    #     rx.pattern.replace(r"\s*'", r"\s*")
    # which left a stray `'` in the middle of the server head -- a quote that
    # string-stripped source never contains -- so `xData('write', '<res>')`
    # NEVER MATCHED AND EVERY SERVER-SIDE STORE WAS INVISIBLE. Only the `st(`
    # sites were ever found, and scp_progress_photos (written exclusively
    # through scpData) was missing with no error to say so.
    sites = []
    for head, full in ((re.compile(r'\bst\s*\(\s*'), STORE_LOCAL),
                       (re.compile(r'\w*[Dd]ata(?:Raw)?\s*\(\s*'), STORE_SERVER)):
        for m in head.finditer(code_nostr):
            got = full.match(raw_code, m.start())
            if got:
                sites.append((got.group(1), m.start()))
    return sites


def scan_file(path):
    try:
        src = io.open(path, encoding='utf-8', errors='strict').read()
    except (OSError, UnicodeDecodeError) as e:
        return None, str(e)
    code = strip_comments(src)
    # From src, NOT from code: the lexer must see comments and literals
    # together to decide which starts first at a given position.
    nostr = strip_strings(src)
    spans = function_spans(nostr)

    def enclosing(off):
        best = None
        for name, s, e in spans:
            if s <= off < e and (best is None or (e - s) < (best[2] - best[1])):
                best = (name, s, e)
        return best

    # ── AI FUNCTIONS: a response parse or a proxy fetch in the body ─────────
    ai_fns = {}
    for name, s, e in spans:
        body = nostr[s:e]
        if any(rx.search(body) for rx in RESPONSE_PARSE) or PROXY_FETCH.search(body):
            ai_fns[name] = (s, e)

    # Response-parse offsets, for BACKWARD's provenance test.
    parse_offsets = []
    for rx in RESPONSE_PARSE:
        for m in rx.finditer(nostr):
            parse_offsets.append(m.start())

    # ── PROVENANCE, AND WHY IT HAS TO BE SCOPED ────────────────────────────
    # An identifier assigned from a response parse carries model provenance.
    # The first version kept ONE FLAT SET per file and it was useless: `text`
    # and `answer` are LOCALS inside an AI function, and once they were in a
    # file-wide set every function in sairnbuild.html that happened to use a
    # variable called `text` became a candidate -- 114 resources, including
    # bldSeedRows, which seeds every table in the app from hardcoded demo rows.
    # A set that matches everything is not a narrower.
    #
    # AND IT ADDED PROPERTY NAMES. `$('fp-result').textContent=fpLastResult`
    # matched `NAME = NAME` and put `textContent` in the set, so every DOM
    # write in the file read as provenance. An assignment target preceded by a
    # dot is a property, not a variable.
    #
    # So: LOCAL provenance is visible only inside the function that created it,
    # and only a MODULE-LEVEL variable carries provenance across functions.
    # That is exactly the distinction the real cases turn on -- bld_ai_chat is
    # written from a local inside its own AI function, bld_photo_analyses from
    # the module-level `fpLastResult` two functions away.
    def in_a_function(off):
        return any(s <= off < e for _n, s, e in spans)

    # EVERY DECLARATOR, NOT THE FIRST. sairnbuild.html:3590 reads
    #   var fpImg64=null,fpImgType='image/jpeg',fpLastResult='',fpSavedId=null;
    # and a regex capturing only the name after `var` sees fpImg64 and stops.
    # `fpLastResult` -- the identifier the entire bld_photo_analyses case turns
    # on -- therefore never entered the module set, was treated as
    # function-local, and the canonical resource went missing with no error.
    module_vars = set()
    for m in re.finditer(r'\b(?:var|let|const)\s', nostr):
        if in_a_function(m.start()):
            continue
        end = nostr.find(';', m.end())
        decl = nostr[m.end():end if end > 0 else m.end() + 400]
        depth, parts = 0, ['']
        for ch in decl:
            if ch in '([{':
                depth += 1
            elif ch in ')]}':
                depth -= 1
            if ch == ',' and depth == 0:
                parts.append('')
                continue
            parts[-1] += ch
        for part in parts:
            nm = re.match(r'\s*([A-Za-z_$][\w$]*)', part)
            if nm:
                module_vars.add(nm.group(1))

    local_prov = {}      # fn name -> identifiers
    global_prov = set()

    def note(ident, off):
        enc0 = None
        for n0, s0, e0 in spans:
            if s0 <= off < e0 and (enc0 is None or (e0 - s0) < (enc0[2] - enc0[1])):
                enc0 = (n0, s0, e0)
        if ident in module_vars:
            global_prov.add(ident)
        if enc0:
            local_prov.setdefault(enc0[0], set()).add(ident)

    for off in parse_offsets:
        ls = nostr.rfind('\n', 0, off) + 1
        le = nostr.find('\n', off)
        stmt = nostr[ls:le if le > 0 else len(nostr)]
        for m in re.finditer(r'(?:var|let|const)?\s*(?<![.\w$])([A-Za-z_$][\w$]*)\s*=(?!=)',
                             stmt):
            note(m.group(1), ls + m.start(1))

    # Two hops inside the AI functions, and no more: a third hop on a 2MB file
    # produces candidates nobody can confirm by reading.
    for _ in range(2):
        grew = False
        for name, (s, e) in ai_fns.items():
            seen = local_prov.get(name, set()) | global_prov
            body = nostr[s:e]
            for m in re.finditer(r'(?<![.\w$])([A-Za-z_$][\w$]*)\s*=(?!=)\s*'
                                 r'([A-Za-z_$][\w$]*)\b', body):
                if m.group(2) in seen and m.group(1) not in seen:
                    note(m.group(1), s + m.start(1))
                    grew = True
            # A function called with a provenance identifier gets its PARAMETER
            # marked -- the saveAndRender(answer) shape, which is how
            # bld_ai_chat is written.
            for m in re.finditer(r'([A-Za-z_$][\w$]*)\s*\(\s*([A-Za-z_$][\w$]*)\s*\)',
                                 body):
                if m.group(2) not in seen:
                    continue
                callee = m.group(1)
                ph2 = re.search(r'\bfunction\s+%s\s*\(\s*([A-Za-z_$][\w$]*)'
                                % re.escape(callee), body)
                if ph2:
                    local_prov.setdefault(callee, set()).add(ph2.group(1))
                    grew = True
                for fn2, s2, e2 in spans:
                    if fn2 == callee:
                        ph = re.match(r'\bfunction\s+\w+\s*\(\s*([A-Za-z_$][\w$]*)',
                                      nostr[s2:e2])
                        if ph:
                            local_prov.setdefault(fn2, set()).add(ph.group(1))
                            grew = True
        if not grew:
            break
    global_prov.discard('')

    fwd, bwd = {}, {}
    for res, off in store_sites(nostr, code):
        ln = line_of(code, off)
        ev = raw_line(src, ln)
        enc = enclosing(off)
        encname = enc[0] if enc else '(top level)'

        # FORWARD: the store sits inside an AI function, or inside a function
        # that reads an identifier this file gave model provenance to.
        stmt_end = code.find(';', off)
        stmt = code[off:stmt_end if stmt_end > 0 else off + 400]
        reads = set(IDENT.findall(nostr[off:off + len(stmt)]))
        # FORWARD reaches through the CALL GRAPH from the model call: the store
        # is inside an AI function, or inside a helper that AI function handed
        # the text to as an argument. That second case is bld_ai_chat --
        # saveAndRender(answer) at sairnbuild.html:8136, an inner function whose
        # own store statement reads only `st` and `list`, so narrowing FORWARD
        # to the store STATEMENT missed it. The scope is the enclosing
        # function's braces, not a character count.
        local_here = local_prov.get(encname, set())
        if encname in ai_fns:
            fwd.setdefault(res, []).append(
                (path, ln, encname, ev, 'store inside an AI function'))
        elif enc and local_here:
            fwd.setdefault(res, []).append(
                (path, ln, encname, ev,
                 'store in a helper the model text was passed into as %s'
                 % ', '.join(sorted(local_here))))

        # BACKWARD: independent of where the store sits. Which identifiers does
        # the code that BUILDS the stored value read?
        #
        # THE FIRST VERSION LOOKED AT THE STORE STATEMENT ALONE AND MISSED
        # bld_photo_analyses, WHICH IS THE CANONICAL CASE. fpSave() reads
        # `fpLastResult` into a `rec` literal two lines above, then calls
        # `st('bld_photo_analyses', list)` -- the store statement itself reads
        # only `st` and `list`. Narrowing to the store statement is the same
        # fixed-scope error as a fixed-size window, one syntactic level down.
        # So this reads the ENCLOSING FUNCTION's body, which is bounded by
        # brace matching rather than by a character count.
        scope = nostr[enc[1]:enc[2]] if enc else stmt
        scope_reads = set(IDENT.findall(scope))
        # ONLY MODULE-LEVEL provenance crosses a function boundary. A local
        # called `text` inside somebody else's AI function says nothing about
        # this store, and treating it as evidence is what produced 114
        # resources on the first run.
        carried = scope_reads & global_prov
        if carried:
            bwd.setdefault(res, []).append(
                (path, ln, encname, ev,
                 'the function building this record reads %s, a module-level '
                 'identifier assigned from a model response'
                 % ', '.join(sorted(carried))))
    return (fwd, bwd), None


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--root', default=REPO)
    ap.add_argument('--evidence', action='store_true')
    a = ap.parse_args(argv)

    targets = []
    for fn in sorted(os.listdir(a.root)):
        if fn.lower().endswith('.html'):
            targets.append(os.path.join(a.root, fn))

    FWD, BWD, unreadable = {}, {}, []
    for path in targets:
        got, err = scan_file(path)
        if err:
            unreadable.append((path, err))
            continue
        f, b = got
        for res, ev in f.items():
            FWD.setdefault(res, []).extend(ev)
        for res, ev in b.items():
            BWD.setdefault(res, []).extend(ev)

    fset, bset = set(FWD), set(BWD)
    print('AI-OUTPUT RESOURCE DERIVATION -- two independent directions')
    print('apps scanned  : %d  (*.html under %s)' % (len(targets), a.root))
    print('files scanned : %d' % len(targets))
    if unreadable:
        print('UNREADABLE    : %d -- NOT scanned, and not a clean universe:'
              % len(unreadable))
        for p, e in unreadable:
            print('   %s  %s' % (os.path.basename(p), e))
    print('')
    print('FORWARD  (model response parse -> store) : %d resource(s)' % len(fset))
    print('BACKWARD (store -> model provenance)     : %d resource(s)' % len(bset))
    print('AGREED   (both directions)               : %d' % len(fset & bset))
    print('')
    print('BOTH METHODS AGREE ON THESE %d:' % len(fset & bset))
    for res in sorted(fset & bset):
        print('  %s' % res)
        if a.evidence:
            for p, ln, fn, ev, why in (FWD[res] + BWD[res])[:4]:
                print('      %s:%d  in %s -- %s' % (os.path.basename(p), ln, fn, why))
                print('        %s' % ev)
    print('')
    print('FORWARD ONLY -- BACKWARD is blind to this shape: %d' % len(fset - bset))
    for res in sorted(fset - bset):
        print('  %s' % res)
        for p, ln, fn, ev, why in FWD[res][:3]:
            print('      %s:%d  in %s -- %s' % (os.path.basename(p), ln, fn, why))
    print('')
    print('BACKWARD ONLY -- FORWARD is blind to this shape: %d' % len(bset - fset))
    for res in sorted(bset - fset):
        print('  %s' % res)
        for p, ln, fn, ev, why in BWD[res][:3]:
            print('      %s:%d  in %s -- %s' % (os.path.basename(p), ln, fn, why))
    print('')
    print('EVERY NAME ABOVE IS A CANDIDATE, NOT A VERDICT. This is a')
    print('two-direction narrower, not a data-flow engine: confirm each by')
    print('reading the store site before gating it, and read the field list')
    print('before redacting -- a deliverable must not be redacted.')
    if unreadable:
        return EXIT_COULD_NOT_RUN
    return EXIT_FINDING if (fset | bset) else EXIT_CLEAN


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
