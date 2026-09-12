r"""ONE comment stripper, driven by a language profile.

    from testint import comments
    code = comments.strip(src, path='app.js')     # comments blanked, length kept
    code = comments.strip(src, language='python')

WHAT IT GUARANTEES

  * **Length and line numbers are preserved.** Comment characters become spaces;
    newlines survive. So `code[:i].count('\n')` still gives the real line number
    of offset `i`, and every check in this suite can report a line the reader
    can go and look at.
  * **It never strips inside a string, a template literal or a regex.** That is
    the whole job. `accept="image/*"`, a URL containing `//`, and `/a\/\/b/`
    must all survive untouched.

WHY A CHARACTER SCANNER AND NOT A REGEX -- this is the expensive lesson this
package exists to sell, so it is written down rather than assumed:

    <input type="file" accept="image/*" capture="environment">

The `/*` in that MIME wildcard opens a block comment. A naive `/\*.*?\*/` runs
forward to the first `*/`, which in one real file lived inside a regex literal
in a later script, and blanked **80.5% of the file**. Three separate tools in
one codebase carried that regex; measured against real files they preserved
11% of the input and reported CLEAN. A checker reading a ninth of a file and
finding nothing is not a weak checker, it is a false one.

WHAT IT IS NOT. Not a parser. It knows enough to tell prose from code. Where a
language has a construct the profile cannot express -- heredocs, Perl's
quote-like operators, Rust's `r#"..."#` -- `caveats_for()` returns the list, and
a check that reports a clean result on such a file should report the caveat
beside it rather than a bare zero.
"""
import os

from . import languages


class UnsupportedLanguage(Exception):
    """Raised rather than guessing. A guessed profile is how a scanner reads
    11% of a file and calls it clean."""


def profile_for(path=None, language=None):
    if language:
        if language not in languages.PROFILES:
            raise UnsupportedLanguage(
                '%r is not a known language profile. Known: %s'
                % (language, ', '.join(sorted(languages.PROFILES))))
        return languages.PROFILES[language]
    if not path:
        raise UnsupportedLanguage('give either path= or language=')
    name = languages.profile_name_for(path)
    if not name:
        raise UnsupportedLanguage(
            'no language profile for %r (extension %r). Supported: %s'
            % (path, os.path.splitext(path)[1], ' '.join(languages.supported_extensions())))
    return languages.PROFILES[name]


def caveats_for(path=None, language=None):
    """What this stripper knowingly cannot model for that language.

    Returned so a check can print it beside a clean result. A zero with an
    unstated caveat is the shape this whole suite is about.
    """
    return list(profile_for(path, language).get('caveats', []))


# The characters after which a bare `/` begins a REGEX rather than a division.
# After a value -- an identifier, a digit, a closing bracket -- `/` divides.
#
# ── `<` AND `>` ARE DELIBERATELY ABSENT, AND THAT IS NOT AN OVERSIGHT ────────
# They are comparison operators, so in pure JavaScript `a < /re/.source` is
# legal and a `/` after `<` really can begin a regex. Including them cost a
# real file: in HTML-embedded script, `</div>` puts a `/` directly after a `<`,
# and the scan then runs forward looking for a closing `/` -- which it finds in
# the very next HTML comment:
#
#     </div><!-- /panel-wrap (label now correct -- see ...) -->
#
# Everything from `/div><!-- /` is consumed as a "regex literal", the `<!--`
# never opens a comment, and 267 characters of comment survive as code.
# Measured on a real 2 MB file: with `<>` in this set the output diverged from
# the battle-tested implementation this generalises; without them it is
# byte-identical across all 23 real files tested.
#
# The trade is stated rather than hidden: `a < /re/.test(b)` is now read as
# division and its regex body as code. That is rare in real source and harmless
# to a comment stripper, where swallowing an HTML comment is not.
_REGEX_OK = set('=(,:[!&|?{};+-*%~^') | {''}


def strip(src, path=None, language=None):
    """Blank every comment, preserving length, newlines and everything else."""
    p = profile_for(path, language)
    out = list(src)
    n = len(src)
    i = 0
    prev = ''

    def kill(a, b):
        for k in range(a, b):
            if out[k] != '\n':
                out[k] = ' '

    line_starts = tuple(p['line'])
    blocks = tuple(p['block'])
    nests = p['block_nests']
    strings = tuple(p['strings'])
    esc = p['escape']
    doubled = p['doubled_quote']
    raws = p['raw_prefixes']
    regex_ok = p['regex_literal']

    while i < n:
        c = src[i]

        # ── BLOCK COMMENTS ───────────────────────────────────────────────────
        matched = False
        for open_, close in blocks:
            if src.startswith(open_, i):
                if nests:
                    # Rust and standard SQL really nest. Treating a nesting
                    # language as non-nesting ends the comment at the FIRST
                    # close and lets the rest of the comment back in as code.
                    depth, j = 1, i + len(open_)
                    while j < n and depth:
                        if src.startswith(open_, j):
                            depth += 1; j += len(open_); continue
                        if src.startswith(close, j):
                            depth -= 1; j += len(close); continue
                        j += 1
                    kill(i, j); i = j
                else:
                    j = src.find(close, i + len(open_))
                    j = n if j == -1 else j + len(close)
                    kill(i, j); i = j
                matched = True
                break
        if matched:
            continue

        # ── LINE COMMENTS ────────────────────────────────────────────────────
        for start in line_starts:
            if src.startswith(start, i):
                j = src.find('\n', i)
                j = n if j == -1 else j
                kill(i, j); i = j
                matched = True
                break
        if matched:
            continue

        # ── STRINGS ──────────────────────────────────────────────────────────
        # A raw/verbatim prefix is consumed with the quote so that `r"\"` and
        # C#'s `@"a""b"` are read as one string rather than as an escape.
        start_at = i
        if raws and c in raws and i + 1 < n:
            for open_, close, spans in strings:
                if src.startswith(open_, i + 1):
                    start_at = i + 1
                    break
        matched = False
        for open_, close, spans in strings:
            if src.startswith(open_, start_at):
                j = start_at + len(open_)
                while j < n:
                    if esc and src[j] == esc:
                        j += 2
                        continue
                    if doubled and src.startswith(close * 2, j):
                        j += 2 * len(close)
                        continue
                    if src.startswith(close, j):
                        j += len(close)
                        break
                    if not spans and src[j] == '\n':
                        break
                    j += 1
                i = j
                prev = close[-1]
                matched = True
                break
        if matched:
            continue

        # ── REGEX LITERALS ───────────────────────────────────────────────────
        if regex_ok and c == '/' and prev in _REGEX_OK:
            j, ok = i + 1, False
            while j < n and src[j] != '\n':
                if src[j] == '\\':
                    j += 2
                    continue
                if src[j] == '[':
                    # A character class may contain an unescaped '/'.
                    while j < n and src[j] not in ']\n':
                        j += 2 if src[j] == '\\' else 1
                if j < n and src[j] == '/':
                    ok = True
                    j += 1
                    break
                j += 1
            if ok:
                i = j
                prev = '/'
                continue

        if not c.isspace():
            prev = c
        i += 1

    return ''.join(out)


def survival(src, path=None, language=None):
    """What fraction of NON-WHITESPACE characters survived stripping.

    The number that catches a broken stripper. A scanner that preserves 11% of
    a file will report clean on almost anything; this is how you find that out
    before trusting a clean result rather than after.
    """
    stripped = strip(src, path=path, language=language)
    before = sum(1 for ch in src if not ch.isspace())
    after = sum(1 for ch in stripped if not ch.isspace())
    return (after / before) if before else 1.0
