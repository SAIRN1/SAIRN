"""
missing_dom_target_check.py -- flags any getElementById('X') call site
(direct, or via a detected wrapper function) where no element with
id="X" actually exists anywhere in the target HTML file.

A function can have entirely correct logic and still be dead on arrival
if its DOM target was never built -- this hit four times in one StoneDesk
session (inventory's #inv-form, remakes' #remake-form/#remake-list,
safety's #safe-incident-list/#safe-training-list/#safe-inspection-list/
#safe-checklist-items, and the customers kanban board's
#cust-kanban-cols), each only found by manually tracing a function and
checking markup by hand. This is the mechanical version of the check
sairn-software-architect now requires before wiring any render function:
"grep the HTML for that id first."

Method: (1) collect every literal id="X" (or id='X') appearing anywhere
in the raw file, including inside JS-generated HTML strings -- a render
function that builds another element's container via innerHTML still
counts as "the id exists", since it's created before anything tries to
getElementById it, and duplicate_global_check.py/other checks already
cover different failure classes; (2) collect every literal
getElementById('X') / getElementById("X") call site, PLUS every literal
call site of a detected DOM-access wrapper function (see below); (3) flag
any target with zero matching id="X" anywhere in the file.

Known limitation: only resolves STRING-LITERAL targets on both sides.
`getElementById(someVariable)` and `id="` + a JS template literal cannot
be resolved statically and are silently skipped, not flagged as missing
-- this mirrors the same limitation already accepted in key_collision_check.py.

Wrapper detection is AUTOMATIC, not a hardcoded function name (fixed
2026-08-07, was CONFIRMED REAL GAP, now closed). The original version of
this checker only matched literal `getElementById(...)` text plus one
hardcoded name, `sv(id,v)`, discovered specific to stonedesk.html. Running
this checker against sairnscape.html found the SAME class of bug in a
new shape: sairnscape wraps every DOM lookup through `scp$(s){return
document.getElementById(s);}`, a name the old hardcoded 'sv' check never
knew to look for -- so 261 real call sites (the overwhelming majority of
this app's actual DOM access) were invisible, and the checker's "0
missing" result on that app was a blind zero, not a clean one, confirmed
only by manually grepping the real wrapper usage by hand (see
sairn-portfolio-triage's Scanner Portability section).

Generalized fix: any single-statement-shaped function whose body calls
`document.getElementById(PARAM)` using its own first parameter -- by
name, not literally -- is auto-detected as a DOM-access wrapper for THIS
file, whatever it happens to be called (`$`, `scp$`, `sv`, or anything
else a future app names it). A literal-string call to any detected
wrapper is then treated exactly like a direct getElementById call for
missing-target purposes. An app with no such wrapper (StoneDesk's own
`sv` aside, most apps just call getElementById directly) simply detects
zero wrappers and behaves exactly as before.

Body-extraction is regex-literal-aware (fixed same day, before this file
was ever committed): the first version of `extract_balanced_body` here
reintroduced the EXACT bug duplicate_global_check.py had already fixed
in `ce43609` -- a naive quote scanner has no notion of a `/regex/`
literal, so `H(s)`'s own body (`.replace(/'/g,'&#39;')`, sairnbiz.html's
real escape helper) has a literal `'` sitting INSIDE regex delimiters;
the naive scanner mistook it for the start of a real string, ran off
looking for the next `'`, and silently swallowed 23,000+ characters
(several unrelated functions' worth) as "H's body" before this was
caught by manually inspecting the extracted body length. Ported the same
JS-lexer regex/division disambiguation heuristic duplicate_global_check.py
already uses (previous-significant-token based) rather than re-inventing
a different fix for the same bug class.
"""
import sys, re
from collections import defaultdict

GET_BY_ID_RE = re.compile(r'getElementById\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)')
ID_ATTR_RE = re.compile(r'\bid\s*=\s*[\'"]([^\'"]+)[\'"]')

# Matches `function NAME(param[, ...rest]){` -- candidate DOM-access
# wrapper declarations. `param` is captured so the body can be checked
# for a real getElementById(param) reference (by name, not literally).
WRAPPER_DEF_RE = re.compile(
    r'function\s+([A-Za-z_$][\w$]*)\s*\(\s*([A-Za-z_$][\w$]*)\s*(?:,[^)]*)?\)\s*\{'
)

# Characters/keywords after which a '/' is a regex-literal start, not
# division -- same heuristic as duplicate_global_check.py's already-fixed
# scanner, ported here rather than re-derived.
REGEX_PRECEDING_CHARS = set('([{,;:!&|?=<>+-*%~^\n')
REGEX_PRECEDING_KEYWORDS = ('return', 'typeof', 'instanceof', 'in', 'of',
                             'new', 'delete', 'void', 'throw', 'case', 'do',
                             'else', 'yield', 'await')


def _is_regex_start(last_sig_char, last_sig_word):
    if last_sig_char in REGEX_PRECEDING_CHARS:
        return True
    if last_sig_char == '/':
        return False
    if last_sig_word in REGEX_PRECEDING_KEYWORDS:
        return True
    return False


def extract_balanced_body(content, open_brace_idx):
    """Return the substring from open_brace_idx (a '{') through its
    matching '}', skipping braces inside strings/comments/regex-literals
    so none of them can desync the depth count."""
    depth = 0
    i = open_brace_idx
    n = len(content)
    last_sig_char = ''
    last_sig_word = ''
    word_buf = ''
    while i < n:
        c = content[i]
        if c == '\n':
            last_sig_char = '\n'
            i += 1
            continue
        if c.isspace():
            i += 1
            continue
        if c == '/' and i + 1 < n and content[i+1] == '/':
            j = content.find('\n', i)
            i = j if j != -1 else n
            continue
        if c == '/' and i + 1 < n and content[i+1] == '*':
            j = content.find('*/', i + 2)
            i = j + 2 if j != -1 else n
            continue
        if c == '/' and _is_regex_start(last_sig_char, last_sig_word):
            j = i + 1
            in_class = False
            while j < n:
                if content[j] == '\\':
                    j += 2
                    continue
                if content[j] == '\n':
                    break
                if content[j] == '[':
                    in_class = True
                elif content[j] == ']':
                    in_class = False
                elif content[j] == '/' and not in_class:
                    break
                j += 1
            j += 1
            while j < n and content[j] in 'gimsuy':
                j += 1
            i = j
            last_sig_char = '/'
            last_sig_word = ''
            continue
        if c in ("'", '"', '`'):
            quote = c
            i += 1
            while i < n:
                if content[i] == '\\':
                    i += 2
                    continue
                if content[i] == quote:
                    i += 1
                    break
                i += 1
            last_sig_char = quote
            last_sig_word = ''
            continue
        if c == '{':
            depth += 1
            i += 1
            last_sig_char = c
            last_sig_word = ''
            continue
        if c == '}':
            depth -= 1
            i += 1
            if depth == 0:
                return content[open_brace_idx:i]
            last_sig_char = c
            last_sig_word = ''
            continue
        if c.isalnum() or c == '_' or c == '$':
            word_buf = (word_buf + c) if (last_sig_char.isalnum() or last_sig_char in ('_', '$')) else c
        else:
            word_buf = ''
        if word_buf:
            last_sig_word = word_buf
        last_sig_char = c
        i += 1
    return content[open_brace_idx:]


def detect_dom_wrappers(html):
    """Return the set of function names in this file whose first
    parameter is passed straight into document.getElementById(...) --
    i.e. a real DOM-access wrapper, detected from this file's own code,
    not assumed from any other app's naming convention."""
    wrappers = set()
    for m in WRAPPER_DEF_RE.finditer(html):
        fname, param = m.group(1), m.group(2)
        body = extract_balanced_body(html, m.end() - 1)
        if re.search(r'document\.getElementById\s*\(\s*' + re.escape(param) + r'\s*\)', body):
            wrappers.add(fname)
    return wrappers


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else 'stonedesk.html'
    with open(path, encoding='utf-8', errors='replace') as f:
        html = f.read()

    lines = html.split('\n')

    existing_ids = set()
    for m in ID_ATTR_RE.finditer(html):
        existing_ids.add(m.group(1))

    wrappers = detect_dom_wrappers(html)
    # (?<![\w$]) instead of \b: \b requires a \w-class transition, but '$'
    # itself isn't a \w character, so \b\$ silently fails to match `$(...)`
    # in the exact contexts that matter (after whitespace/`(`/`;`/etc) --
    # confirmed live: this exact bug produced TOTAL_WRAPPER_FORWARD_CALLS:0
    # for sairngrounds.html despite the wrapper being correctly detected.
    # Trailing \s*(?:\)|,) -- accepts a single-arg call `$('id')` (next
    # char ')') and a multi-arg wrapper's first arg `sv('id', value)`
    # (next char ','), but rejects a concatenated call like
    # `$('panel-'+id)` (next char '+'), which is dynamic/unresolvable and
    # must be skipped, not misread as a complete call to a literal id
    # "panel-". Confirmed live: without this exclusion, every app's tab/
    # panel-toggle helpers (`$('irr-tab-'+t)`, `scp$('scp-panel-'+id)`,
    # etc.) produced false MISSING_TARGETS entries for the literal prefix
    # alone; without ALSO accepting ',', multi-arg wrappers like `sv`
    # would have silently gone back to zero matches.
    wrapper_call_res = {
        name: re.compile(r'(?<![\w$])' + re.escape(name) + r'\s*\(\s*[\'"]([^\'"]+)[\'"]\s*(?:\)|,)')
        for name in wrappers
    }

    calls = defaultdict(list)  # id -> [line, ...]
    wrapper_call_count = 0
    for i, line_text in enumerate(lines, 1):
        for m in GET_BY_ID_RE.finditer(line_text):
            calls[m.group(1)].append(i)
        for name, cre in wrapper_call_res.items():
            for m in cre.finditer(line_text):
                calls[m.group(1)].append(i)
                wrapper_call_count += 1

    missing = {tid: lns for tid, lns in calls.items() if tid not in existing_ids}

    print("DETECTED_DOM_WRAPPERS:%s" % (sorted(wrappers) if wrappers else "none"))
    print("TOTAL_GETELEMENTBYID_CALLS:%d" % (sum(len(v) for v in calls.values()) - wrapper_call_count))
    print("TOTAL_WRAPPER_FORWARD_CALLS:%d" % wrapper_call_count)
    print("DISTINCT_TARGETS:%d" % len(calls))
    print("EXISTING_IDS_IN_FILE:%d" % len(existing_ids))
    print("MISSING_TARGETS:%d" % len(missing))
    for tid in sorted(missing):
        lns = missing[tid]
        print("MISSING: id=\"%s\" referenced at line(s) %s -- never appears as id=\"%s\" anywhere in the file"
              % (tid, ', '.join(str(l) for l in lns[:5]) + ('...' if len(lns) > 5 else ''), tid))

    sys.exit(1 if missing else 0)


if __name__ == '__main__':
    main()
