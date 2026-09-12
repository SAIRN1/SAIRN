r"""How each language says *"read this file"* and *"is this literal in it?"*

The comment-quote check needs three facts out of a test file:

  1. a variable was bound to the RAW TEXT of a source file,
  2. that variable is searched for a quoted literal,
  3. which source file it was.

All three are spelled differently per language, so they live in a table for the
same reason the comment syntax does: adding a language is an entry, not a code
path.

── WHY THE VARIABLE MATTERS AND NOT JUST THE CALL ────────────────────────────
The first version of the tool this generalises matched any `x.indexOf('lit')`
and produced two false alarms immediately: one on a probe searching a
comment-STRIPPED copy it had made itself, and one searching a substring of the
file. Both were doing exactly the right thing. **Only a search against the
variable bound to the RAW file can be testing comments**, so that is the only
variable considered. Keep that property when adding a language.

── WHAT IS DELIBERATELY NOT MATCHED ──────────────────────────────────────────
A search whose needle is a variable, a concatenation or a regex is skipped, and
the skip is COUNTED and REPORTED rather than silent. A checker that quietly
narrows its own subject is the failure this suite exists to find; see the
`skipped` count in the report.
"""

PROFILES = {
    'javascript': {
        'extensions': ['.js', '.mjs', '.cjs', '.ts', '.jsx', '.tsx'],
        # `const src = fs.readFileSync(...)` -- captures the bound variable.
        'bind': r"(?:const|let|var)\s+(\w+)\s*=\s*(?:await\s+)?"
                r"(?:fs\.)?(?:promises\.)?readFileSync\s*\(([^;]*?)\)",
        # How that variable is searched. %s is the variable name.
        'search': [
            r"\b%s\.indexOf\s*\(\s*(['\"`])(.+?)\1",
            r"\b%s\.includes\s*\(\s*(['\"`])(.+?)\1",
            r"\b%s\.match\s*\(\s*(['\"`])(.+?)\1",
        ],
    },
    'python': {
        'extensions': ['.py'],
        # src = open(p).read() / io.open(p, ...).read() / Path(p).read_text()
        'bind': r"(\w+)\s*=\s*(?:io\.)?open\s*\(([^;]*?)\)\s*\.read\s*\(\s*\)"
                r"|(\w+)\s*=\s*Path\s*\(([^;]*?)\)\s*\.read_text\s*\(",
        'search': [
            r"(['\"])(.+?)\1\s+in\s+\b%s\b",
            r"\b%s\.count\s*\(\s*(['\"])(.+?)\1",
            r"\b%s\.find\s*\(\s*(['\"])(.+?)\1",
        ],
    },
    'go': {
        'extensions': ['.go'],
        'bind': r"(\w+)\s*,\s*_\s*:?=\s*os\.ReadFile\s*\(([^)]*)\)",
        'search': [
            r"strings\.Contains\s*\(\s*(?:string\()?\b%s\b\)?\s*,\s*\"(.+?)()\"",
        ],
    },
    'ruby': {
        'extensions': ['.rb'],
        'bind': r"(\w+)\s*=\s*File\.read\s*\(([^)]*)\)",
        'search': [
            r"\b%s\.include\?\s*\(\s*(['\"])(.+?)\1",
        ],
    },
}

BY_EXTENSION = {}
for _n, _p in PROFILES.items():
    for _e in _p['extensions']:
        BY_EXTENSION.setdefault(_e, _n)


def profile_for(path):
    """The assertion profile for a test file, or None when unsupported.

    None is not "nothing to check" -- the caller must count it as a file it
    COULD NOT READ and say so. A language this table does not know is a gap in
    coverage, and an unreported gap in coverage reads as a clean result.
    """
    import os
    return PROFILES.get(BY_EXTENSION.get(os.path.splitext(path)[1].lower()))
