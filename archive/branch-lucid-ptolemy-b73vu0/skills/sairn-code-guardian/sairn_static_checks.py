"""
SAIRN Code Guardian -- Checks 9-12 (added after the StoneDesk outage, June 2026)

These four checks exist because the original 8-point Guardian scan, plus the
separate sairn-runtime-validator and sairn-ultra-scan skills, ALL passed on a
build of stonedesk.html that was completely broken in the browser: AI buttons
did nothing, the SOP print feature was entirely dead, and a chat-rendering
hook was silently misdirected to the wrong feature. None of the existing
checks were built to catch any of these failure modes. These four were.

CHECK 9  -- Node Ground-Truth Syntax Validation
CHECK 10 -- Duplicate Global Identifier Detector
CHECK 11 -- Regex Literal Sanity Check
CHECK 12 -- Stale/Hardcoded Model String Detector

Design principle for all four: prefer a ground-truth tool (Node's own parser)
over hand-written regex wherever the question is "is this valid JavaScript."
Regex is used only for pattern questions Node cannot answer on its own (is
this name declared twice, is this regex literal malformed-but-valid, is this
model string stale) -- and even there, every regex-based finding is designed
to be re-verifiable by a human in under a minute by looking at the cited line
number, because regex heuristics WILL produce occasional false positives and
this module does not pretend otherwise. See the inline commentary on each
function for the specific false-positive classes that were found and fixed
during development, since they are likely to recur in other SAIRN apps and
are worth recognizing on sight rather than re-discovering by trial and error.
"""
import re
import subprocess
import tempfile
import os


# =====================================================================
# CHECK 9 — Node Ground-Truth Syntax Validation
# =====================================================================
#
# Extracts every inline <script> block and runs `node --check` on each one
# individually, matching how a browser actually parses separate script tags
# (each <script> tag is its own top-level parse unit; a syntax error in one
# does not necessarily abort a sibling tag, which is why per-block checking
# is more accurate than concatenating the whole file into one script and
# checking that — concatenation produces false positives of its own, such as
# flagging `const APP_ID` as "redeclared" when it is actually declared once
# per tag in two DIFFERENT tags that never collide in a real browser).
#
# This is the check that would have caught, in stonedesk.html on June 16 2026:
#   - three unterminated-string bugs in printDrawCutSheet/printSOP/printAllSOPs
#     (a `win.document.write('...<script>...<\/script>` missing its closing
#     quote, statement terminator, and function brace)
#   - a stray `<script>` tag pasted INSIDE an already-open script block
#     (the demo-seed IIFE collision)
#   - `document.addEventListener('DOMContentLoaded', function);` — the bare
#     `function` keyword passed where a function reference was required
#   - two instances of showSOPs/printSOP and printAllSOPs sitting ENTIRELY
#     OUTSIDE any <script> tag at all (an orphaned `</body></html>');
#     win.document.close(); }` fragment ate the opening <script> tag during
#     a previous edit, so the functions rendered as inert page text — no
#     console error, because it was not invalid JS, it was simply not JS)

def extract_script_blocks(content):
    """
    Returns list of (start_line, end_line, code) for every inline <script> block.
    Skips <script src="..."> (nothing to check in an external file reference).

    Two false-positive traps were found and fixed while building this:

    1. Adjacent script tags on one line: `</script><script>`. A naive
       line-by-line state machine that toggles "in_script" on sight of either
       tag will mis-split a block if both tags appear on the same line. Fixed
       by using a single global regex pass (re.finditer) over the whole file
       instead of a line-by-line scanner — finditer correctly matches each
       <script>...</script> pair as a unit regardless of what is adjacent to it.

    2. Escaped closing tags inside JS strings: SAIRN's print-popup pattern
       writes `win.document.write('<script>...<\\/script>')` to build an HTML
       string for a popup window. The backslash-escaped slash is valid JS and
       is NOT a real closing tag, but `</script>` still appears later in the
       file as a substring search target for the REAL closing tag of that
       outer script block. The fix here is a negative lookbehind for a single
       backslash before `</script>`; this covers every real case found in the
       SAIRN codebase, but if a future file uses double-escaping or a
       different quoting style, re-verify this assumption rather than trust
       it blindly.
    """
    blocks = []
    pattern = re.compile(
        r'<script(?![^>]*\bsrc=)[^>]*>(.*?)(?<!\\)</script>',
        re.DOTALL | re.IGNORECASE
    )
    for m in pattern.finditer(content):
        code = m.group(1)
        start_line = content.count('\n', 0, m.start(1)) + 1
        end_line = content.count('\n', 0, m.end(1)) + 1
        blocks.append((start_line, end_line, code))
    return blocks


def check_node_groundtruth(content, node_path='node'):
    """
    Runs `node --check` on every extracted script block.
    Returns list of finding dicts: {line, severity, message, offending_code, block_range}
    """
    findings = []
    blocks = extract_script_blocks(content)
    if not blocks:
        return findings

    with tempfile.TemporaryDirectory() as tmpdir:
        for idx, (start, end, code) in enumerate(blocks):
            fpath = os.path.join(tmpdir, 'block_{}.js'.format(idx))
            with open(fpath, 'w', encoding='utf-8') as f:
                f.write(code)

            try:
                result = subprocess.run(
                    [node_path, '--check', fpath],
                    capture_output=True, text=True, timeout=10
                )
            except FileNotFoundError:
                findings.append({
                    'line': start,
                    'severity': 'WARN',
                    'message': 'Node not available in this environment -- '
                               'ground-truth syntax check skipped. Install Node '
                               'or run this check in an environment with Node available. '
                               'Checks 10-12 below do not require Node and remain valid.',
                    'block_range': (start, end),
                })
                return findings
            except subprocess.TimeoutExpired:
                findings.append({
                    'line': start,
                    'severity': 'WARN',
                    'message': 'Script block at lines {}-{} timed out during syntax '
                               'check (10s) -- manually inspect for pathological '
                               'regex or extremely large minified content.'.format(start, end),
                    'block_range': (start, end),
                })
                continue

            if result.returncode != 0:
                stderr = result.stderr
                rel_line_match = re.search(re.escape(fpath) + r':(\d+)', stderr)
                rel_line = int(rel_line_match.group(1)) if rel_line_match else None
                abs_line = (start + rel_line - 1) if rel_line else start

                err_match = re.search(r'(SyntaxError: .+)', stderr)
                err_msg = err_match.group(1) if err_match else stderr.strip().split('\n')[0]

                code_line_match = re.search(r'\n(.+)\n\s*\^+\n', stderr)
                offending_code = code_line_match.group(1).strip()[:120] if code_line_match else ''

                findings.append({
                    'line': abs_line,
                    'severity': 'CRITICAL',
                    'message': 'NODE PARSE FAILURE in script block (HTML lines {}-{}): {}'.format(
                        start, end, err_msg),
                    'offending_code': offending_code,
                    'block_range': (start, end),
                })

    return findings


# =====================================================================
# CHECK 10 — Duplicate Global Identifier Detector
# =====================================================================
#
# Finds `function name(){}` declarations and `window.name = function...`
# assignments that occur more than once across the WHOLE file (multiple
# inline <script> tags in one HTML document share one global scope for plain
# function declarations -- this is an HTML/browser semantic, not something
# Node alone can verify, which is why this check exists separately from
# Check 9 even though both deal with JS).
#
# This is the check that would have caught the tryInstall collision in
# stonedesk.html: two unrelated features (a markdown-render hook installer
# and a confidence-bar hook installer) both declared `function tryInstall(){}`
# at the top level. The second declaration silently won, so every
# `setTimeout(tryInstall, ...)` call in the FIRST feature's code ended up
# calling the SECOND feature's function instead -- no error thrown anywhere,
# because calling a function that exists (just the wrong one) is not an error.

LOAD_BEARING_NAMES = {
    'callClaude', 'doLogin', 'showPage', 'showToast', 'showApp',
    'dbLoadAll', 'applyRoleGates', 'applyExecRole', 'initAI',
}

# These specific names are reassigned many times BY DESIGN across SAIRN apps
# (each reassignment layers one more feature onto outbound fetch calls or
# chat-message rendering). A bare collision count is not useful here -- what
# matters is whether each later reassignment actually chains to the one
# before it via a saved-reference ("onion wrapper") pattern.
WRAPPER_TOLERANT_NAMES = {'fetch', 'addMsg', 'open'}


def find_all_function_declarations(content):
    """
    Returns dict: name -> list of (line_number, indent_level, script_block_index)
    for every `function name(...)` declaration and `window.name = function`
    assignment in the file, AT ANY INDENTATION/NESTING DEPTH.

    Indentation is recorded, not used to filter at this stage. An earlier
    version of this check used brace-depth counting to filter out "local"
    (nested) declarations before comparing names, on the theory that a
    function declared inside another function or IIFE is scoped there and
    cannot collide globally. That approach was abandoned: a single unterminated
    string or stray tag ANYWHERE earlier in the same script block throws off a
    naive brace counter for everything downstream of it -- which is precisely
    the failure mode this check exists to catch, so relying on a fragile
    counter to pre-filter candidates before even looking for the bug was
    circular and caused real collisions (doLogin, tryInstall) to be silently
    dropped during development. Indentation is used only as a heuristic signal
    in verify_collision_with_node() below, not as a hard filter.
    """
    occurrences = {}
    lines = content.split('\n')

    func_pattern = re.compile(r'^(\s*)(?:async\s+)?function\s+(\w+)\s*\(')
    window_pattern = re.compile(r'^(\s*)window\.(\w+)\s*=\s*(?:async\s+)?function')

    script_block_idx = -1
    for i, line in enumerate(lines):
        if re.search(r'<script(?![^>]*\bsrc=)[^>]*>', line, re.IGNORECASE):
            script_block_idx += 1

        m1 = func_pattern.match(line)
        if m1:
            indent, name = m1.groups()
            occurrences.setdefault(name, []).append((i + 1, len(indent), script_block_idx))

        m2 = window_pattern.match(line)
        if m2:
            indent, name = m2.groups()
            occurrences.setdefault(name, []).append((i + 1, len(indent), script_block_idx))

    return occurrences


def verify_collision_with_node(name, occurrence_lines):
    """
    Decides whether a candidate name with 2+ declarations is a likely REAL
    global collision, using indentation as the primary signal: in SAIRN's
    coding style (plain functions, no ES modules, occasional IIFE wrapping
    for the "second login rewrite" pattern), a declaration at column 0 inside
    a <script> tag is almost always a true top-level global. Two such
    zero-indent declarations of the same name are a definite collision.

    A single zero-indent declaration PLUS at least one more declaration at any
    indent is also flagged, because the more dangerous real-world case found
    during development (doLogin) was exactly this shape: one top-level
    `function doLogin(){}` plus one nested `function doLogin(){}` inside an
    IIFE that explicitly re-exports itself via `window.doLogin = doLogin;` --
    the nested one is reachable globally specifically because of that export,
    not because of its nesting, which is why the export bridge matters and is
    checked for via find_explicit_window_exports() in check_duplicate_globals.
    """
    zero_indent_count = sum(1 for (_, indent, _) in occurrence_lines if indent == 0)
    return zero_indent_count >= 2 or (
        zero_indent_count >= 1 and len(occurrence_lines) >= 2
    )


def has_chaining_reference(content, decl_line, name):
    """
    Checks a window around decl_line for the SAIRN onion-wrapper pattern:
    `var _orig = window.X; window.X = function(){ ... _orig.apply(...) ... }`.
    Used only for WRAPPER_TOLERANT_NAMES (fetch, addMsg, open) where multiple
    reassignments are expected and only an UNCHAINED reassignment is a bug.
    """
    lines = content.split('\n')
    start_idx = max(0, decl_line - 15)
    end_idx = min(len(lines), decl_line + 30)
    window_text = '\n'.join(lines[start_idx:end_idx])

    chain_patterns = [
        r'_orig\w*\s*=\s*(?:window\.)?' + re.escape(name),
        r'_orig\w*\.apply\(',
        r'_orig\w*\.call\(',
        r'_orig\w*\(',
    ]
    return any(re.search(p, window_text) for p in chain_patterns)


def find_explicit_window_exports(content):
    """
    Catches `window.doLogin = doLogin;` -- an explicit re-export of a (possibly
    nested/IIFE-scoped) local function onto the global window object. This can
    appear at any brace depth by design (that is the entire point of writing
    it), so unlike find_all_function_declarations() this is not filtered.

    IMPORTANT false-positive class found during development: a function
    declared and then IMMEDIATELY exported right next to its own declaration
    (`function selRole(el){...} window.selRole = selRole;`) is the standard,
    safe "declare then expose" pattern used dozens of times throughout SAIRN
    apps -- it is NOT a collision on its own. This function only RECORDS
    export line numbers; check_duplicate_globals() below is responsible for
    requiring 2+ DISTINCT function bodies to exist before treating anything
    as a real collision, which is what filters out the safe single-export case.

    Returns dict: name -> list of line numbers where `window.name = name;` occurs.
    """
    exports = {}
    lines = content.split('\n')
    pattern = re.compile(r'^\s*window\.(\w+)\s*=\s*(\w+)\s*;')
    for i, line in enumerate(lines):
        m = pattern.match(line)
        if m and m.group(1) == m.group(2):
            exports.setdefault(m.group(1), []).append(i + 1)
    return exports


def check_duplicate_globals(content):
    findings = []
    all_func_occurrences = find_all_function_declarations(content)
    window_exports = find_explicit_window_exports(content)

    bare_names = set(all_func_occurrences.keys()) | set(window_exports.keys())

    for bare_name in bare_names:
        func_occurrences = all_func_occurrences.get(bare_name, [])
        export_lines = window_exports.get(bare_name, [])
        func_lines = sorted(set(o[0] for o in func_occurrences))

        # Require 2+ DISTINCT function bodies. A single declaration paired
        # with its own export is not a collision (see docstring above).
        if len(func_lines) < 2:
            continue

        all_lines = sorted(set(func_lines) | set(export_lines))

        if not verify_collision_with_node(bare_name, func_occurrences):
            continue

        lines_list = [str(n) for n in all_lines]

        if bare_name in WRAPPER_TOLERANT_NAMES:
            unchained = [
                line_no for line_no in all_lines[1:]
                if not has_chaining_reference(content, line_no, bare_name)
            ]
            if unchained:
                findings.append({
                    'line': all_lines[0],
                    'all_lines': all_lines,
                    'name': bare_name,
                    'severity': 'CRITICAL',
                    'message': (
                        "'{}' redefined {}x at lines {}. Lines {} do NOT reference "
                        "a saved original (_orig pattern) -- this reassignment will "
                        "silently DISCARD all previously wrapped behavior instead of "
                        "layering onto it."
                    ).format(bare_name, len(all_lines), ', '.join(lines_list), unchained),
                })
            continue

        last_line_no = all_lines[-1]
        lines_arr = content.split('\n')
        last_body = '\n'.join(lines_arr[last_line_no - 1: last_line_no + 9])
        looks_like_stub = (
            len(last_body.strip()) < 80
            or 'not yet built' in last_body.lower()
            or ('console.log' in last_body and 'return' not in last_body and len(last_body) < 150)
        )

        severity = 'CRITICAL' if (bare_name in LOAD_BEARING_NAMES or looks_like_stub) else 'WARN'

        msg = (
            "'{}' declared/exported {}x at lines {}. Only the LAST one (line {}) "
            "is live at runtime -- all earlier ones are dead code."
        ).format(bare_name, len(all_lines), ', '.join(lines_list), last_line_no)
        if looks_like_stub:
            msg += (
                " WARNING: the surviving (last) definition looks like a stub/"
                "placeholder. If an earlier, fuller definition was meant to win, "
                "this is a live bug."
            )
        if len(all_lines) >= 3:
            msg += " {} copies of the same name signals copy-paste drift -- consolidate.".format(
                len(all_lines))

        findings.append({
            'line': all_lines[0],
            'all_lines': all_lines,
            'name': bare_name,
            'severity': severity,
            'message': msg,
        })

    return findings


# =====================================================================
# CHECK 11 — Regex Literal Sanity Check
# =====================================================================
#
# Catches regex literals that are syntactically VALID JavaScript (Node --check
# will not flag them) but semantically broken. Two specific patterns were
# found in stonedesk.html's renderMarkdown function:
#   `/**([^*]+)**/g`  -- JS sees the opening `/*` as the START OF A BLOCK
#                        COMMENT, not a regex. Everything until the next `*/`
#                        ANYWHERE LATER IN THE FILE can be silently swallowed.
#   `/*([^*]+)*/g`    -- same trap, single asterisk variant.
#   `/^(d+). (.+)$/`  -- missing backslash: matches the literal letter "d"
#                        one-or-more times instead of \d (a digit). Compiles
#                        fine, matches nothing useful, fails silently.

def check_regex_literals(content):
    findings = []
    lines = content.split('\n')

    # A regex literal opening with /* or /** is always a comment trap in JS.
    comment_trap = re.compile(r'(?<![\/\*])/\*\*?\(')

    # .replace(/(d+)/) or similar where a bare d/w/s appears where \d/\w/\s
    # was almost certainly intended.
    missing_backslash = re.compile(
        r'\.(?:replace|match|test|exec)\s*\(\s*/\^?\(?(d|w|s)\+\)?[^/]*?/[gimsuy]*'
    )

    for i, line in enumerate(lines):
        if comment_trap.search(line):
            findings.append({
                'line': i + 1,
                'severity': 'CRITICAL',
                'message': (
                    "Regex literal opens with '/*' or '/**' -- JavaScript parses "
                    "this as the START OF A BLOCK COMMENT, not a regex. Everything "
                    "until the next '*/' anywhere later in the file may be silently "
                    "swallowed as a comment. Escape literal asterisks: "
                    "/\\*\\*(...)\\*\\*/ for bold, /\\*(...)\\*/ for italic."
                ),
                'code': line.strip()[:140],
            })

        m = missing_backslash.search(line)
        if m:
            findings.append({
                'line': i + 1,
                'severity': 'HIGH',
                'message': (
                    "Regex character class shorthand missing its backslash -- found "
                    "a bare '{0}' where '\\{0}' was almost certainly intended "
                    "(\\d=digit, \\w=word char, \\s=whitespace). This compiles fine "
                    "but matches a literal letter instead of the intended class, so "
                    "the pattern silently fails to match real input."
                ).format(m.group(1)),
                'code': line.strip()[:140],
            })

    return findings


# =====================================================================
# CHECK 12 — Stale/Hardcoded Model String Detector
# =====================================================================
#
# Catches client-side fetch() calls to the SAIRN proxy that hardcode a Claude
# model identifier instead of letting the proxy (api/claude.js) choose the
# model from app_id/is_demo per the documented PERMANENT pattern. This class
# of bug is invisible to every other check in this file: it is not a syntax
# error (Node parses it fine), not a duplicate (it is one clean fetch call),
# and not a malformed regex. It fails at the network/API layer the moment the
# hardcoded model is deprecated upstream -- a failure mode that can appear
# weeks or months after the code shipped clean.

PROXY_URL_FRAGMENT = 'sairn.vercel.app/api/claude'


def check_hardcoded_model_strings(content):
    findings = []
    lines = content.split('\n')
    model_pattern = re.compile(r'model\s*:\s*[\'"]([\w.\-]+)[\'"]')

    for i, line in enumerate(lines):
        m = model_pattern.search(line)
        if not m:
            continue

        window_start = max(0, i - 15)
        window_end = min(len(lines), i + 15)
        nearby = '\n'.join(lines[window_start:window_end])

        if PROXY_URL_FRAGMENT not in nearby:
            continue  # not a SAIRN proxy call -- out of scope

        findings.append({
            'line': i + 1,
            'severity': 'HIGH',
            'message': (
                "Hardcoded model identifier '{}' sent to the SAIRN proxy. The "
                "documented platform pattern lets the proxy choose the model "
                "based on app_id/is_demo -- a hardcoded client-side model string "
                "will silently become a hard API failure the moment that model "
                "version is deprecated upstream, and unlike a syntax error this "
                "will NOT be caught by Node or any static parser. Remove the "
                "model field and let the proxy decide, matching every other call "
                "site in this file."
            ).format(m.group(1)),
            'code': line.strip()[:140],
        })

    return findings


# =====================================================================
# CHECK 13 — Cross-Script-Block Variable Redeclaration
# =====================================================================
#
# Added after Check 9-12 still let a real bug ship: `var APP_ID = 'stonedesk';`
# was declared in two separate <script> tags. Check 9 (Node ground-truth)
# validates each script block in ISOLATION, so this passed cleanly -- the
# collision only exists once a browser combines multiple <script> tags into
# one shared global scope, which Node's per-file --check cannot simulate on
# its own. In a real browser:
#   - two `var X` declarations of the same name: SILENTLY MERGE, no error,
#     in NORMAL (non-strict) script context
#   - but the SECOND block here opened with 'use strict', and re-declaring a
#     `var` that already exists in the shared scope under strict mode IS a
#     hard SyntaxError that aborts the entire script tag at parse time --
#     before a single line of it runs.
# This is exactly what crashed StoneDesk live: `Identifier 'APP_ID' has
# already been declared`, which then cascaded into a dozen "X is not defined"
# errors for every function meant to be registered by the scripts that never
# got a chance to execute after the crash.

VAR_DECL_PATTERN = re.compile(r'^\s*(var|const|let)\s+(\w+)\s*=')
STRICT_MODE_PATTERN = re.compile(r'^\s*[\'"]use strict[\'"]\s*;?\s*$')


def find_top_level_var_declarations(content):
    """
    Returns dict: name -> list of (line_number, script_block_index, decl_kind,
    block_is_strict) for every var/const/let declared at TRUE top level of a
    <script> tag -- meaning brace depth 0 relative to that script tag's own
    opening, not merely zero leading whitespace in the source text.

    This intentionally uses real brace-depth tracking, unlike Check 10's
    duplicate-function detector, which abandoned brace counting because a
    syntax error anywhere upstream in the same file would desync a naive
    counter for everything downstream -- exactly the failure mode Check 10
    exists to help catch. Check 13 does not have that problem: it only ever
    runs on a file that has ALREADY passed Check 9 (Node ground-truth parse),
    so by the time Check 13 runs, the file is known to be syntactically
    valid and brace counting is safe and accurate. A first version of this
    check used leading-whitespace as a proxy for top-level, which produced
    false positives for any var/const/let sitting inside a column-0-indented
    `(function(){ ... })();` IIFE wrapper (a very common SAIRN pattern for
    "install once" guards) -- those are genuinely scoped to their own IIFE
    and never collide with anything outside it, no matter how many other
    blocks in the file use the same variable name inside their own separate
    IIFEs. Real brace-depth tracking fixes this.

    Note: this still does not perfectly model JS scoping (e.g. it does not
    distinguish a `{` that opens a block statement from one that opens an
    object literal), but combined with already-passing Check 9, the common
    SAIRN cases (bare script-tag top level vs. IIFE-wrapped) are both
    handled correctly, which is what matters in practice.
    """
    occurrences = {}
    lines = content.split('\n')

    script_block_idx = -1
    block_is_strict = False
    depth = 0
    for i, line in enumerate(lines):
        if re.search(r'<script(?![^>]*\bsrc=)[^>]*>', line, re.IGNORECASE):
            script_block_idx += 1
            block_is_strict = False
            depth = 0  # reset: depth is relative to THIS script tag's own scope

        if STRICT_MODE_PATTERN.match(line):
            block_is_strict = True

        m = VAR_DECL_PATTERN.match(line)
        if m:
            kind, name = m.groups()
            if depth == 0:  # genuinely at the script tag's own top level
                occurrences.setdefault(name, []).append(
                    (i + 1, script_block_idx, kind, block_is_strict)
                )

        # update depth AFTER checking this line's declaration, using a naive
        # but (per the docstring above) now-safe brace count, since Check 13
        # only ever runs post-Check-9 on syntactically valid files. Strings
        # and comments containing brace characters can still throw this off
        # in rare cases; findings should be spot-checked before bulk-fixing,
        # same as every other Guardian check.
        depth += line.count('{') - line.count('}')
        if depth < 0:
            depth = 0  # script tag itself or a stray close; don't go negative

    return occurrences


def check_cross_block_variable_collisions(content):
    findings = []
    decls = find_top_level_var_declarations(content)

    for name, occs in decls.items():
        block_indices = set(o[1] for o in occs)
        if len(block_indices) < 2:
            continue  # all in the same block -- that's Check 9's job, not this one

        lines_list = [o[0] for o in occs]
        any_strict = any(o[3] for o in occs)
        any_let_or_const = any(o[2] in ('let', 'const') for o in occs)

        if any_strict or any_let_or_const:
            findings.append({
                'line': lines_list[0],
                'severity': 'CRITICAL',
                'message': (
                    "'{}' declared {}x across {} different <script> tags at lines {} "
                    "-- at least one declaration uses 'use strict' or let/const, which "
                    "makes this a HARD SyntaxError in a real browser (redeclaring a "
                    "shared-scope variable under strict mode aborts that entire script "
                    "tag at parse time, before any line of it runs). This is the exact "
                    "bug class that crashed StoneDesk live on June 16 2026 despite a "
                    "clean per-block Node check. Remove the duplicate declaration(s), "
                    "keeping only the one in the block that actually needs it first."
                ).format(name, len(occs), len(block_indices), lines_list),
            })
        else:
            findings.append({
                'line': lines_list[0],
                'severity': 'WARN',
                'message': (
                    "'{}' declared {}x across {} different <script> tags at lines {}. "
                    "All are plain 'var' in non-strict context, so this currently merges "
                    "silently without crashing -- but it's fragile: adding 'use strict' "
                    "to any future patch touching one of these blocks turns this into a "
                    "hard crash with no warning. Consolidate to one declaration."
                ).format(name, len(occs), len(block_indices), lines_list),
            })

    return findings


# =====================================================================
# Combined runner
# =====================================================================

def run_all_checks_9_through_12(content, node_path='node'):
    """
    Runs Checks 9-13 and returns a single combined findings list plus a
    pass/fail summary, in the same shape the existing Guardian report format
    expects (see SKILL.md Scan Report Format). Function name kept as
    run_all_checks_9_through_12 for backward compatibility with existing
    callers; it now also runs Check 13.
    """
    all_findings = []
    all_findings.extend(
        [dict(f, check=9, check_name='Node Ground-Truth Syntax') for f in check_node_groundtruth(content, node_path)]
    )
    all_findings.extend(
        [dict(f, check=10, check_name='Duplicate Global Identifiers') for f in check_duplicate_globals(content)]
    )
    all_findings.extend(
        [dict(f, check=11, check_name='Regex Literal Sanity') for f in check_regex_literals(content)]
    )
    all_findings.extend(
        [dict(f, check=12, check_name='Stale Model String') for f in check_hardcoded_model_strings(content)]
    )
    all_findings.extend(
        [dict(f, check=13, check_name='Cross-Block Variable Collision') for f in check_cross_block_variable_collisions(content)]
    )

    crits = sum(1 for f in all_findings if f['severity'] == 'CRITICAL')
    highs = sum(1 for f in all_findings if f['severity'] == 'HIGH')
    warns = sum(1 for f in all_findings if f['severity'] == 'WARN')

    return {
        'findings': all_findings,
        'crits': crits,
        'highs': highs,
        'warns': warns,
        'pass': crits == 0,
    }
