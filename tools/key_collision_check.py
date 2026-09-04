"""
key_collision_check.py -- flags any localStorage key written by more than
one DISTINCT BACKING VARIABLE, whether written via a direct
`localStorage.setItem(...)` call or via a detected storage-write wrapper
function (e.g. `st(k,v)`, `scpSt(k,v)`).

This is the mechanical enforcement of sairn-software-architect's rule
(added 2026-07-27): "grep for the storage key before creating it." Every
real collision bug found this session (sd_customers, sd_inventory,
sd_remakes, sd_safety) was exactly this pattern -- two independent,
differently-shaped in-memory variables (e.g. an IIFE's private `data`
array vs. a separate global `sdCustomers`) both serialized to the same
key, because the second feature never checked whether the key already
had an owner.

Method: extract every <script> block (reusing extract_scripts.py's real
HTML-parser-based extraction), scan each tracking brace depth (skipping
strings/comments/regex-literals), and capture every
`localStorage.setItem('KEY', JSON.stringify(VAR))` (or bare
`localStorage.setItem('KEY', VAR)`) call's VAR -- PLUS every equivalent
call through a detected wrapper function (see below). A key is flagged
only when 2+ DISTINCT NAMED variables write it -- this is the actual
signature of a real collision. Multiple *functions* writing the SAME
variable to the SAME key (e.g. an add/edit/delete trio all calling
`localStorage.setItem('sd_intake', JSON.stringify(intakeSubmissions))`)
is normal CRUD on one cohesive data model, not a bug, and is deliberately
NOT flagged -- an earlier function-name-based version of this check
flagged 9 keys that were all this exact false-positive shape before this
was corrected. Inline literal resets (`'{}'`, `'[]'`, or an inline object/
array literal) are tracked separately and never counted as a competing
variable, since clearing state to empty isn't a competing shape.

Wrapper detection is AUTOMATIC, not hardcoded (fixed 2026-08-07, was
CONFIRMED REAL GAP, now closed). The original version of this checker
only matched literal `localStorage.setItem(...)` text -- running it
against sairngrounds.html/sairnscape.html, both of which route every
storage write through `st(k,v){localStorage.setItem(k,JSON.stringify(v))}`
/ `scpSt(k,v){...}` wrappers instead of calling setItem directly,
returned a literal `TOTAL_KEY_WRITES:0` on sairngrounds.html -- a blind
zero, not a clean one; the app has 31 real distinct keys. Generalized
fix: any function whose body calls `localStorage.setItem(PARAM, ...)`
using its own first parameter -- by name, not literally -- is
auto-detected as a storage-write wrapper for THIS file, whatever it
happens to be named. A call to any detected wrapper is then parsed
exactly like a direct setItem call (same VAR/literal extraction, same
collision logic). An app with no such wrapper detects zero and behaves
exactly as before.

Also fixed the same day: the brace-depth scanner had zero regex-literal
awareness (the same bug class duplicate_global_check.py already fixed in
`ce43609`, and that missing_dom_target_check.py's new wrapper-body
extractor briefly reintroduced before being caught) -- a `.replace(/'/g,
'&#39;')`-style escape helper (`H()`/`scpH()`, present in every one of
these apps) has a literal `'` sitting inside regex delimiters, which the
naive quote scanner mistook for a real string start, silently
desyncing brace-depth tracking for the rest of the block. Ported the
same JS-lexer regex/division disambiguation heuristic
duplicate_global_check.py already uses.

Known limitation: dynamic keys (`localStorage.setItem(someVar, ...)` or
a wrapper call whose key argument isn't a string literal, including
concatenated literals like `st('grd_'+kind, ...)`) are not resolved --
only string-literal key names, immediately followed by a comma, are
tracked. This mirrors the same limitation accepted in this session's
manual traces and in missing_dom_target_check.py.
"""
import sys, os, re
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract_scripts import ScriptExtractor

FUNC_DECL_RE = re.compile(r'function\s+([A-Za-z_$][\w$]*)\s*\(')
FUNC_EXPR_RE = re.compile(r'([A-Za-z_$][\w$.]*)\s*=\s*function\s*\(')

# Matches `function NAME(param1[, ...rest]){` -- candidate storage-write
# wrapper declarations. param1 is captured so the body can be checked for
# a real localStorage.setItem(param1, ...) reference (by name).
WRAPPER_DEF_RE = re.compile(
    r'function\s+([A-Za-z_$][\w$]*)\s*\(\s*([A-Za-z_$][\w$]*)\s*(?:,[^)]*)?\)\s*\{'
)

# Same heuristic as duplicate_global_check.py's already-fixed scanner,
# ported here rather than re-derived (see module docstring).
REGEX_PRECEDING_CHARS = set('([{,;:!&|?=<>+-*%~^\n')
REGEX_PRECEDING_KEYWORDS = ('return', 'typeof', 'instanceof', 'in', 'of',
                             'new', 'delete', 'void', 'throw', 'case', 'do',
                             'else', 'yield', 'await')

# Parse as identifiers (match the bare-variable regex group) but are
# literal values, not a real competing backing variable -- see the
# JS_LITERAL_KEYWORDS check at the m3 match site below.
JS_LITERAL_KEYWORDS = {'null', 'true', 'false', 'undefined'}


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


def detect_storage_wrappers(html):
    """Return the set of function names in this file whose first
    parameter is passed straight into localStorage.setItem(...)'s key
    slot -- i.e. a real storage-write wrapper, detected from this file's
    own code, not assumed from any other app's naming convention."""
    wrappers = set()
    for m in WRAPPER_DEF_RE.finditer(html):
        fname, param = m.group(1), m.group(2)
        body = extract_balanced_body(html, m.end() - 1)
        if re.search(r'localStorage\.setItem\s*\(\s*' + re.escape(param) + r'\s*,', body):
            wrappers.add(fname)
    return wrappers


def make_setitem_re(wrapper_names):
    """── LEFT WORD BOUNDARY, ADDED 2026-09-04 ────────────────────────────────
    This alternation had no left boundary, so the wrapper name `st` matched
    ANY identifier ending in those letters. `showToast('Brand colors saved for
    this shop')` was being counted as a storage write with that sentence as the
    key -- four toast messages were in the key list, and the reported totals
    (96 writes / 82 distinct keys) were inflated by them.

    It could not HIDE a real collision, only add noise. But noise in a collision
    detector is precisely what gets a collision detector ignored, and a toast
    string that happened to equal a real key would have manufactured a false
    one.

    Two boundaries, not one, because the two halves differ: `localStorage` may
    legitimately be preceded by a dot (`window.localStorage.setItem`), while a
    bare helper never should be -- `x.st(...)` is somebody's method, not this
    file's storage wrapper.
    """
    parts = [r'(?<![\w$])localStorage\.setItem']
    parts += [r'(?<![\w$.])' + re.escape(n) for n in sorted(wrapper_names)]
    alt = '|'.join(parts)
    return re.compile(
        r'(?:' + alt + r')\s*\(\s*[\'"]([^\'"]+)[\'"]\s*,\s*'
        r'(?:JSON\.stringify\s*\(\s*([A-Za-z_$][\w$.]*)|([A-Za-z_$][\w$.]*)|(\{|\[|[\'"]))'
    )


def scan_block(content, base_line, SETITEM_RE):
    depth = 0
    i = 0
    n = len(content)
    line = base_line
    func_stack = []  # [name, depth_of_body_open_brace_or_None]
    results = []  # (key, enclosing_fn, line)
    last_sig_char = ''
    last_sig_word = ''
    word_buf = ''

    while i < n:
        c = content[i]
        if c == '\n':
            line += 1
            i += 1
            last_sig_char = '\n'
            continue
        if c.isspace():
            i += 1
            continue
        if c == '/' and i + 1 < n and content[i+1] == '/':
            j = content.find('\n', i)
            if j == -1:
                break
            i = j
            continue
        if c == '/' and i + 1 < n and content[i+1] == '*':
            j = content.find('*/', i+2)
            if j == -1:
                break
            line += content.count('\n', i, j)
            i = j + 2
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
            j = i + 1
            while j < n:
                if content[j] == '\\':
                    j += 2
                    continue
                if content[j] == quote:
                    break
                j += 1
            line += content.count('\n', i, j)
            i = j + 1
            last_sig_char = quote
            last_sig_word = ''
            continue

        m = FUNC_DECL_RE.match(content, i)
        if m:
            func_stack.append([m.group(1), None])
            i = m.end()
            last_sig_char = ')'
            last_sig_word = ''
            continue
        m2 = FUNC_EXPR_RE.match(content, i)
        if m2:
            func_stack.append([m2.group(1), None])
            i = m2.end()
            last_sig_char = ')'
            last_sig_word = ''
            continue
        m3 = SETITEM_RE.match(content, i)
        if m3:
            key = m3.group(1)
            var = m3.group(2) or m3.group(3)  # named variable, if any
            is_literal = m3.group(4) is not None  # '{', '[', or a quote -- inline reset, not a competing var
            if var in JS_LITERAL_KEYWORDS:
                # 'null'/'true'/'false'/'undefined' parse as identifiers
                # but are literal values, not a competing backing
                # variable -- e.g. `st('sb_role', null)` on logout next
                # to `st('sb_role', prole)` on login is normal
                # clear-on-logout, not two independent shapes writing the
                # same key. Confirmed real false positive: every one of
                # tonight's 4 apps has a *_role key that follows exactly
                # this pattern, and all 4 flagged as a "collision" before
                # this fix.
                var = None
                is_literal = True
            fn = func_stack[-1][0] if func_stack else '(top-level)'
            results.append((key, fn, var, is_literal, line))
            i = m3.end()
            last_sig_char = ')'
            last_sig_word = ''
            continue

        if c == '{':
            depth += 1
            if func_stack and func_stack[-1][1] is None:
                func_stack[-1][1] = depth
            i += 1
            last_sig_char = c
            last_sig_word = ''
            continue
        if c == '}':
            if func_stack and func_stack[-1][1] == depth:
                func_stack.pop()
            depth -= 1
            i += 1
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
    return results


# ── ACKNOWLEDGED COLLISIONS (added 2026-09-04) ─────────────────────────────
# Two distinct backing variables writing one key is a POINTER, not a verdict.
# Some of them are correct by design, and without a record every session that
# runs this re-traces the same ones by hand -- which is what happened on
# 2026-09-04, when four collisions were reported and three turned out benign.
#
# An entry here needs the key, the two variable names it is acknowledged FOR,
# and a reason. Naming the variables matters: if a THIRD writer appears, or one
# of these is renamed, the acknowledgement stops applying and the collision is
# reported again. An allowlist that silences a key forever would be worse than
# no allowlist -- it is exactly how sd_referrals hid until 2026-08-07.
ACKNOWLEDGED = {
    'stonedesk:ai_memories': (
        {'_sdMemories', 'data'},
        "syncSDMemoriesFromSupabase() caches the server's list ('data'); "
        "writeSDMemory() writes the locally-extended list ('_sdMemories'). One "
        "owner, one shape, server-wins-on-sync by design. Traced by hand "
        "2026-09-04; the real defect found there was that BOTH writes were "
        "unchecked, which is fixed, and is not a collision."),
    'stonedesk:business_profile': (
        {'data', 'profile'},
        "syncSDProfileFromSupabase() caches the server copy ('data'); "
        "saveSDProfile() writes the edited copy ('profile'). Same shape as the "
        "memories pair. NOTE saveSDProfile() has ZERO CALLERS and is "
        "quarantined in stonedesk.html with its own unchecked-write defect "
        "documented -- fix that before wiring it up."),
    'dnt_settings_obj': (
        {'rec', 'serverSettings'},
        "TRACED BY HAND 2026-09-04 (CC), after Fourth reported it and left it "
        "because sairndental was claimed at the time. The three 'rec' writers -- "
        "saveBookingSettings(), dnPersistWindows() and saveGfeIdentity() -- are "
        "one shape, not three: each does Object.assign({}, <base>, {only its own "
        "keys}), so no two of them write a different schema into this key. That "
        "is the discipline, added after the earlier lost-update, and it is "
        "correct. dntSyncFromServer() writes 'serverSettings', the server's row, "
        "replacing wholesale -- which every one of the three relies on and says "
        "so in a comment. "
        "THE REAL DEFECT FOUND IN THE SAME TRACE WAS NOT A COLLISION, exactly as "
        "the stonedesk:ai_memories entry above records for its own key: the merge "
        "BASE was this device's cached copy, so a workstation working from a "
        "stale copy erased fields another workstation had set. Fixed -- the base "
        "is now a fresh server read, and all three write server-first. The "
        "residual true race is in docs/SAIRN-OPEN-WORK-INDEX.md."),
    'sd_quote_history': (
        {'h', 'hist'},
        "window.sdQuoteSaveHistory() appends a new quote ('h'); the History "
        "panel's save() writes back the rows it owns ('hist'). Two writers is "
        "what the 2026-09-04 fix INTRODUCED on purpose: save() now partitions a "
        "merged array and routes each half to its own store. Held by "
        "tests/quote_history_duplication.js."),
    'sd_aiquotes': (
        {'ai', 'd'},
        "The other half of the same 2026-09-04 fix: the History panel's save() "
        "routes AI-quote rows back here ('ai'), and the AI quote builder writes "
        "its own list ('d'). Same suite."),
}


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else 'stonedesk.html'
    with open(path, encoding='utf-8', errors='replace') as f:
        html = f.read()

    wrappers = detect_storage_wrappers(html)
    SETITEM_RE = make_setitem_re(wrappers)

    parser = ScriptExtractor()
    parser.feed(html)

    all_writes = []
    for start_line, end_line, content in parser.blocks:
        all_writes.extend(scan_block(content, start_line, SETITEM_RE))

    by_key_vars = defaultdict(set)      # key -> set of distinct NAMED variables
    by_key_all = defaultdict(list)      # key -> list of (fn, var_or_literal_marker, line)
    for key, fn, var, is_literal, line in all_writes:
        label = var if var else ('(inline literal reset)' if is_literal else '(unresolved)')
        by_key_all[key].append((fn, label, line))
        if var:  # only named variables count toward collision detection
            by_key_vars[key].add(var)

    collisions = {k: v for k, v in by_key_vars.items() if len(v) > 1}

    print("DETECTED_STORAGE_WRAPPERS:%s" % (sorted(wrappers) if wrappers else "none"))
    print("TOTAL_KEY_WRITES:%d" % len(all_writes))
    print("DISTINCT_KEYS:%d" % len(by_key_all))
    # An acknowledgement applies only while the variable pair is EXACTLY the one
    # recorded. A third writer, or a rename, and it is reported again.
    known, unknown = {}, {}
    for key, vars_ in collisions.items():
        ack = ACKNOWLEDGED.get(key)
        (known if ack and ack[0] == vars_ else unknown)[key] = vars_

    print("COLLISIONS:%d  (unacknowledged: %d)" % (len(collisions), len(unknown)))
    for key in sorted(unknown):
        print("COLLISION: %s -> distinct backing variables: %s" % (key, sorted(unknown[key])))
        for fn, label, line in by_key_all[key]:
            print("    %s() writes %s @ line %d" % (fn, label, line))
        if key in ACKNOWLEDGED:
            print("    NOTE: this key IS acknowledged, but for %s -- the writers "
                  "have changed, so the acknowledgement does not apply."
                  % sorted(ACKNOWLEDGED[key][0]))
    for key in sorted(known):
        print("ACKNOWLEDGED: %s %s -- %s"
              % (key, sorted(known[key]), ACKNOWLEDGED[key][1]))

    if not unknown:
        print("RESULT:CLEAN -- every collision is one somebody traced by hand and "
              "wrote down. A key with two writers is a pointer, not a verdict.")
    sys.exit(1 if unknown else 0)


if __name__ == '__main__':
    main()
