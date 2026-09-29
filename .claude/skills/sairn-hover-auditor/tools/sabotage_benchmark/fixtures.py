"""sabotage_benchmark/fixtures.py -- the corpus itself.

DESIGNED IN SKILL.MD (2026-09-17, under Anthropic-benchmark research), never
built until tonight (2026-09-18), on direct instruction, using Petri 2.0's
published shape (a versioned, growing seed/fixture library with a real,
standing discrimination score) as a BENCHMARK for what this should look like
-- never imported, never installed. Everything below is SAIRN's own, built
from real, already-confirmed defect shapes this platform and this role's own
session have actually hit, which SKILL.md's own design text names as
STRONGER than Anthropic's synthetic quirky models for exactly that reason:
these are real incidents, not implants.

WHAT A FIXTURE IS. A named, real defect SHAPE (not one incident -- the
recurring pattern behind several), given as a VULNERABLE snippet and a FIXED
snippet that are otherwise as similar as possible, plus a REFERENCE DETECTOR:
a small, real function that is supposed to tell the two apart. Running
run_benchmark.py scores every reference detector against every fixture it
claims to cover and reports N of M correctly discriminated -- the same
standing, versioned, real number Petri reports for its own quirky-model
suite, built from this platform's own incidents instead.

SHAPE-PRESERVING, NOT LIFTED VERBATIM. Every snippet below is a minimal,
synthetic stand-in that reproduces the DEFECT'S SHAPE, not a copy-paste of
real platform source -- this file lives outside the platform repo and must
never become a second, unmaintained copy of platform code (the exact drift
class this file's own fixture #2 is about).
"""

import re


def _detect_csv_formula_injection(code):
    """Reference detector for fixture 1. Real shape, found and fixed
    platform-wide tonight (2026-09-17/18, hover_log #234/#241/#242, closed by
    Fourth's 885fd0b9 + tools/csv_formula_injection_check.py): a CSV cell
    helper that escapes embedded quotes but never neutralizes a leading
    =/+/-/@, the standard formula-injection vector. Returns True if the code
    looks VULNERABLE (quote-escaping present, no leading-char guard)."""
    has_quote_escape = bool(re.search(r"replace\(", code))
    # A real guard tests the value against a character class containing the
    # formula-trigger characters BEFORE the quote-escaping replace() runs --
    # matched here as any regex literal or test() call naming those chars.
    has_leading_char_guard = bool(re.search(r"[=+@-]", code) and
                                   re.search(r"test\(|\.test\b|/\^", code))
    # First self-scoring bug found by this benchmark itself, on its own first
    # run (2026-09-18): the vulnerable fixture's own code contains a
    # replace(/"/g,'""') call, and the ORIGINAL guard heuristic here also
    # matched on the unrelated double-quote character class inside that same
    # replace() call, scoring a false positive on the FIXED input too. The
    # guard must specifically require the formula-trigger class near a
    # test()/regex-literal construct, which /^[=+@-]/.test(t) satisfies and
    # the quote-escaping replace() does not.
    return has_quote_escape and not has_leading_char_guard


CSV_FORMULA_INJECTION = {
    "id": "001_csv_formula_injection",
    "name": "CSV cell helper escapes quotes but not a leading =/+/-/@",
    "real_incident": "hover_log #234 (2026-09-17), fixed 885fd0b9, 53 sites / 13 files",
    "vulnerable": (
        "function csvCell(v){\n"
        "  var t = String(v==null?'':v);\n"
        "  return '\"' + t.replace(/\"/g,'\"\"') + '\"';\n"
        "}\n"
    ),
    "fixed": (
        "function csvCell(v){\n"
        "  var t = String(v==null?'':v);\n"
        "  if(/^[=+@-]/.test(t)) t = \"'\" + t;\n"
        "  return '\"' + t.replace(/\"/g,'\"\"') + '\"';\n"
        "}\n"
    ),
    "reference_detector": _detect_csv_formula_injection,
}


def _detect_stale_dependency_list(injected_names, real_free_vars=None):
    """Reference detector for fixture 2. Real, recurring shape (SKILL.md:
    "the sairnbiz_ledger_source_id.js-shaped ReferenceError found five
    times"): a test harness hand-lists the free variables a lifted function
    body needs, and the list silently goes stale when the real function
    grows a new dependency, throwing ReferenceError at RUN time rather than
    failing the actual assertions. Returns True (VULNERABLE: will throw) if
    the harness's injected-name list does not cover every real free var.
    `real_free_vars` defaults to this fixture's own ground truth when the
    benchmark runner calls this generically without it."""
    real_free_vars = real_free_vars or STALE_DEPENDENCY_LIST["real_function_free_vars"]
    return not set(injected_names).issuperset(real_free_vars)


STALE_DEPENDENCY_LIST = {
    "id": "002_stale_dependency_injection_list",
    "name": "Hand-listed harness dependency list drifts from the real function's free vars",
    "real_incident": "SKILL.md: sairnbiz_ledger_source_id.js-shaped ReferenceError, found 5 times",
    "real_function_free_vars": {"localStorage", "toast", "fmt", "sbThreeWayMatch"},
    # Uniform contract with the other fixtures: vulnerable_input/fixed_input,
    # each passed as the detector's single positional argument.
    "vulnerable_input": ["localStorage", "toast", "fmt"],
    "fixed_input": ["localStorage", "toast", "fmt", "sbThreeWayMatch"],
    "reference_detector": _detect_stale_dependency_list,
}


def _detect_client_trusted_role_gate(code):
    """Reference detector for fixture 3. Real shape, found live on this
    platform's own undirected sweep (hover_log #228, sairnscape.html): a
    sensitive-action gate reads a role from client-side storage
    (sessionStorage/localStorage) with no server-side re-verification at the
    point of use. Returns True (VULNERABLE) if the role check reads from
    client storage and there is no accompanying server/API call in the same
    function."""
    reads_client_role = bool(re.search(r"(sessionStorage|localStorage)\.getItem\([^)]*role", code, re.I))
    has_server_check = bool(re.search(r"fetch\(|await\s+\w*[Dd]ata\(|verifySession", code))
    return reads_client_role and not has_server_check


CLIENT_TRUSTED_ROLE_GATE = {
    "id": "003_client_trusted_role_gate",
    "name": "Sensitive-tool gate trusts a client-side role with no server re-check",
    "real_incident": "hover_log #228 (2026-09-17), sairnscape.html scpExecuteTool/scpCurrentRole",
    "vulnerable": (
        "function executeTool(name){\n"
        "  var role = sessionStorage.getItem('role');\n"
        "  if(role !== 'owner') { return {error:'forbidden'}; }\n"
        "  return runTool(name);\n"
        "}\n"
    ),
    "fixed": (
        "async function executeTool(name){\n"
        "  var res = await verifyServerRole('owner');\n"
        "  if(!res.ok) { return {error:'forbidden'}; }\n"
        "  return runTool(name);\n"
        "}\n"
    ),
    "reference_detector": _detect_client_trusted_role_gate,
}


def _detect_bracket_class_silent_miss(pattern_src):
    """Reference detector for fixture 4. Real shape, found and fixed WITHIN
    THIS SESSION tonight building git_history_secrets_scan.py: a POSIX ERE
    bracket character class (`[:=]`, or `\\s` combined with other escapes
    inside `[...]`) that compiles with exit 0 and silently matches nothing --
    the single most dangerous checker shape there is, a check that passes
    while testing nothing. Returns True (VULNERABLE) if the pattern contains
    a `[:` bracket-class-prefix collision or a `\\s`/`\\d`/`\\w` shorthand
    used INSIDE a bracket expression."""
    has_colon_prefix_collision = bool(re.search(r"\[:[^\]]", pattern_src))
    has_shorthand_inside_bracket = bool(re.search(r"\[[^\]]*\\[sdw][^\]]*\]", pattern_src))
    return has_colon_prefix_collision or has_shorthand_inside_bracket


BRACKET_CLASS_SILENT_MISS = {
    "id": "004_regex_bracket_class_silent_miss",
    "name": "POSIX ERE bracket class silently matches nothing (git -G pickaxe)",
    "real_incident": "This session, 2026-09-18, building git_history_secrets_scan.py -- 3 real instances",
    "vulnerable": r"password\s*[:=]\s*['\"][^'\"\s]{8,}['\"]",
    "fixed": r"password\s*(:|=)\s*['\"][^'\"]{8,}['\"]",
    "reference_detector": _detect_bracket_class_silent_miss,
}


def _detect_self_referential_check(code):
    """Reference detector for fixture 5. Real, recurring shape SKILL.md
    names as the eighth cross-domain discipline and cites twice (entry 111's
    stale NHI-register warning): a generator's own `--check` mode compares a
    document to its OWN most recent output rather than to the real source of
    truth it is supposed to describe, so a stale-but-internally-consistent
    document reads as verified forever. Returns True (VULNERABLE) if a
    `--check` path compares generated output against a previously-generated
    file rather than against a named external source."""
    has_check_mode = "--check" in code or "def check(" in code
    compares_against_own_output = bool(
        re.search(r"(open|read)\([^)]*(GENERATED|OUTPUT|_FILE)\b", code, re.I) and
        "SOURCE" not in code.upper())
    return has_check_mode and compares_against_own_output


SELF_REFERENTIAL_CHECK = {
    "id": "005_self_referential_check",
    "name": "--check mode compares generated output to itself, not to the real source",
    "real_incident": "SKILL.md eighth cross-domain discipline; entry 111's stale NHI-register warning",
    "vulnerable": (
        "def check():\n"
        "    generated = build_report()\n"
        "    OUTPUT_FILE = 'report.md'\n"
        "    with open(OUTPUT_FILE) as f:\n"
        "        return generated == f.read()\n"
    ),
    "fixed": (
        "def check():\n"
        "    generated = build_report()\n"
        "    SOURCE_OF_TRUTH = read_real_source()\n"
        "    return generated == render(SOURCE_OF_TRUTH)\n"
    ),
    "reference_detector": _detect_self_referential_check,
}


ALL_FIXTURES = [
    CSV_FORMULA_INJECTION,
    STALE_DEPENDENCY_LIST,
    CLIENT_TRUSTED_ROLE_GATE,
    BRACKET_CLASS_SILENT_MISS,
    SELF_REFERENTIAL_CHECK,
]
