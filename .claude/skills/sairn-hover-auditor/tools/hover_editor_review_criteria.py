#!/usr/bin/env python
"""hover_editor_review_criteria.py -- criteria and fixture lock for
hover_editor_review.py, kept in their own file per the blind-analysis
convention (docs/2026-09-13-cross-domain-disciplines.md item 1): the
pass/fail criteria were decided against these synthetic fixtures BEFORE the
tool judged any real report, and the tool refuses to judge anything real
until every fixture classifies correctly.

FIXTURE-CORRECTION DECLARATION (the distinction that keeps the lock honest):
as of CRITERIA_VERSION 1, no fixture has been changed to match tool output.
If a fixture's expected verdict is ever corrected because it was simply
wrong, or adjusted to match what the tool produced, say WHICH here, dated.
- 2026-09-24 v1: fixtures F4/F5/F6 were AUTHORED with backticked anchors
  because the anchor-candidate rules (below) do not treat plain English
  words as anchors -- that is a design decision made while writing the
  fixtures, before any real report was judged, not a post-hoc adjustment.
- 2026-09-24 v2: TWO CRITERIA CORRECTED after the first real-data runs,
  both directions of wrong, and the CRITERIA changed, not the fixtures'
  expected verdicts. (a) FALSE POSITIVE: the extension alternation put
  `js` before `json`, so "docs/tier-a-reviews.json" extracted as the
  nonexistent "docs/tier-a-reviews.js" and flagged MISSING -- fixed with a
  trailing (?![A-Za-z0-9]) boundary; F15 locks it. (b) FALSE NEGATIVE
  WEARING THE WRONG LABEL: `t.billable && !t.invoiced` was reported
  ANCHOR-ABSENT from sairnlaw.html when the code exists as
  `t.billable&&!t.invoiced` (cosmetic spacing) at :3858 vs the cited
  :3678 -- the true story is a 180-line LINE-MISMATCH, not an absence.
  Code-shaped anchors now match whitespace-normalized; F16 locks it.
- 2026-09-28 v3: IMPLIED-FILE CITATIONS ADDED, NOT A FIXTURE CORRECTION --
  a genuinely new claim class this tool could not extract before, flagged
  as a real gap across nine separate draws (H1 logs #534, #535, #536, #539
  and others) before being built: the platform's own register cells cite
  bare `:NNNN` with the file implied by which row's evidence cell it sits
  in ("READ OUT OF THE APP: `:5637` writes ..."), never restating the
  filename, so the old FILELINE-only extractor produced NOTHING-TO-CHECK
  on every one of them. See IMPLIED_LINE below and F17-F21.
- 2026-09-28 v3 (same day, testing the new feature against real rows, not a
  fixture correction -- two genuine bugs the new IMPLIED_LINE feature
  exposed): (c) sentences() split on bare whitespace after `.!?`, but register
  prose bolds sentence-final punctuation ("...individually.**") with NO
  space before the `**`, so that boundary was never split and an EARLIER
  clause's backticked token leaked into a LATER citation's anchor pool as
  one merged "sentence" -- fixed by consuming the bold markers in the split, F22
  locks it. (d) anchor_candidates accepted ANY backticked token 3-80 chars,
  so a citation's own wrapper ("`:6010`") became a candidate for itself --
  fixed by requiring at least one letter, F23 locks it. Found together on
  sf_ceremonial_items: the leaked token "`sf_*`" from an unrelated
  re-audit-header sentence coincidentally matched real text 4456 lines away
  in sairnfreedom.html and would have shipped as a false LINE-MISMATCH.
  (e) THIRD BUG, FOUND CHASING (c)+(d) TO GROUND ON THE SAME REAL ROW: with
  both fixed, sf_ceremonial_items still reported ANCHOR-ABSENT instead of the
  correct LINE-MISMATCH, because `{item, kind, serial, inspected}` is
  register shorthand for an object's KEYS and almost never appears as one
  literal substring in real source -- the individual field name `inspected`
  DOES sit on the real (drifted) write line, but was never extracted as its
  own candidate. Fixed by is_field_list()/anchor_candidates splitting a
  brace- or comma-shaped bare-identifier list into per-field candidates,
  narrowly enough that ordinary comma'd prose is never mistaken for one.
  F24/F25 lock it. With all three fixes, sf_ceremonial_items now correctly
  reports LINE-MISMATCH :6010 -> :6096 (drift 86), the real citation-drift
  finding the row actually has.

THRESHOLD DERIVATIONS (not preferences):
- LINE_DRIFT_FINDING = 3: the one measured real citation drift on this
  platform is 5 lines (98a37b09 cited report_only_checks.py:855; the entry
  sits at 860 today, ~859 when H2 re-checked it) and H2 judged that worth
  recording. Convention 4 says alarm TIGHTER than the observed failure
  point, so the finding threshold is 3, with drift 1..3 reported as a
  non-blocking DRIFT note (the margin, printed rather than swallowed).
- DURATION_TOLERANCE = max(15 minutes, 50% of the stated figure): the one
  measured real error is "four hours" stated vs ~1h0m actual (306e8930 vs
  cc2792cd..5c662411 committer dates) -- an error of 300%. Prose durations
  are rounded by authors, so the band is wide; it still catches a 4x error
  with 6x headroom. Both author and committer dates must disagree with the
  stated figure before it is a finding (conservative, fewer false flags).

KNOWN EXTRACTION LIMITS, stated rather than implied:
- HEX_TOKEN requires >=1 digit and >=1 [a-f] letter, length 7..40. A real
  abbreviated sha that is all-digits or all-letters is skipped: for 7 hex
  chars P(no digit) ~ (6/16)^7 = 0.1%, P(no letter) ~ (10/16)^7 = 3.7%.
  Cheap insurance against date/word false positives, and the miss rate is
  printed by the tool as a per-class extraction caveat, not hidden.
  {7,40} not {7,10}: the \\b{7,10}\\b shape silently drops full 40-char
  shas (hover_coverage_ledger.py's recorded SHA_TOKEN bug); {7,40} matches
  a full sha and still rejects 64-hex log hashes (no word boundary exists
  inside a longer hex run, so the regex cannot take a 40-char bite of one).
- A NEGATED claim ("X is NOT a valid object", "path does not exist") is the
  report asserting absence; flagging it would invert the meaning. The
  negation guard is sentence-scoped and word-listed below.
- This is a CITATION-integrity pass. A mechanism claim ("hydration bails
  before the adoption path") is out of reach by construction -- that class
  is caught by instrumented re-execution (what H2 did to 05cfb0ed), not by
  any static read of the report. Named as a limit, not implied otherwise.
- PERMANENT LIMIT, REGISTERED RATHER THAN FIXED (2026-09-29): LONG-SENTENCE
  ANCHOR BLEED. sentences() splits a paragraph only on `[.!?]` (plus the
  bold-glue fix, v3 correction c) -- it does NOT split on semicolons or
  colon-joined clauses. A real, heavily punctuated register-prose paragraph
  with several colon/semicolon clauses and no terminal period until its very
  end becomes ONE "sentence" to anchor_candidates(), so an identifier from
  an EARLY clause (e.g. `DISTRICT_REPORT_FORMAT`) can be picked up as a
  candidate anchor for a LATER, unrelated citation (`:286`, a plain-prose
  quote with no identifier-shaped anchor of its own) purely because both sit
  in the same run-on sentence. Reproduced live: this role's own log #657
  (2026-09-29) -- verdict LINE-MISMATCH on a citation hand-verified TRUE.
  WHY REGISTERED RATHER THAN FIXED: a real fix means either splitting on
  `[;:]` too (breaks every code-shaped colon citation this tool ALREADY
  parses correctly, e.g. `path/to/file.py:42`, and every field-list colon
  inside a backtick span -- both load-bearing, both would need their own
  new exemption, at real risk of a repeat of the F14 regression F28's fix
  just produced one line up in this same file's history) or scoping
  anchor_candidates() to a bounded WINDOW of characters around each
  citation instead of the whole sentence (a real redesign of the anchor
  model, not a bounded patch, and risks the opposite failure -- a genuine
  anchor sitting just outside the window reading as absent). Bounded
  workaround available to a HUMAN reader today: SHORTEN a long evidence-cell
  paragraph to one citation-bearing clause per sentence when precision
  matters, exactly as `:286`'s own neighbouring cells already do. Not
  fixed here; a future CRITERIA_VERSION bump is the right place for either
  real redesign, with its own fixture-locked criteria decided before any
  real report is judged against it, per this file's own founding discipline.
"""
import os
import re
import shutil
import subprocess
import tempfile

CRITERIA_VERSION = 3

# An implied-file citation: a bare `:NNNN` (optionally `:NNNN-NNNN`) with the
# colon immediately followed by a digit and NOT preceded by a filename
# character. The "immediately followed, no space" shape is deliberate --
# every real example measured across nine draws is glued tight
# ("`:5637`", "`:4134`", "(:6708-2270)" -- never "at : 5637"), and requiring
# it tight is also what keeps clock times and ratios ("10:30", "3:1") out:
# their colon is preceded by a DIGIT, which the lookbehind already excludes,
# so no separate time/ratio denylist is needed. The caller (main()) is
# responsible for not double-firing this on a colon already consumed by
# FILELINE ("sairnfreedom.html:6708") -- see review_text()'s span exclusion.
IMPLIED_LINE = re.compile(r"(?<![\w./])\:(\d{1,6})(?:-(\d{1,6}))?\b")

# --- extraction criteria -------------------------------------------------

# >=1 digit and >=1 a-f letter enforced by checker fn, not the regex alone.
HEX_TOKEN = re.compile(r"\b[0-9a-f]{7,40}\b")

# path with a code-ish extension, optional :line or :line-line
FILELINE = re.compile(
    r"(?<![\w/])((?:[\w.-]+/)*[\w.-]+\."
    r"(?:py|json|js|mjs|html|md|sql|ts|css|sh|yml|yaml))(?![A-Za-z0-9])"
    r"(?::(\d{1,6})(?:-(\d{1,6}))?)?"
)

DURATION = re.compile(
    r"\b(\d{1,3}|one|two|three|four|five|six|seven|eight|nine|ten|eleven|"
    r"twelve|an?|half an?)\s+(hours?|hrs?|minutes?|mins?)\s+"
    r"(later|after|before|earlier|apart|gap)\b",
    re.IGNORECASE,
)
WORD_NUMBERS = {
    "a": 1, "an": 1, "half a": 0.5, "half an": 0.5, "one": 1, "two": 2,
    "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
    "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
}

NEGATION_WORDS = (
    "not a valid", "no longer", "does not exist", "did not exist",
    "doesn't exist", "absent", "missing", "none found", "not found",
    "dangling", "removed", "deleted", "never existed", "no such",
    "fails", "cannot resolve", "unresolvable", "stale ref", "gitignored",
    "not carried", "not in the repo", "not committed",
)

BACKTICK = re.compile(r"`([^`]+)`")
UNDERSCORE_ID = re.compile(r"\b([A-Za-z][A-Za-z0-9]*_[A-Za-z0-9_]+)\b")
CAMEL_ID = re.compile(r"\b([a-z][a-z0-9]+[A-Z][A-Za-z0-9]+)\b")
CALL_ID = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]{2,})\(")

LINE_DRIFT_FINDING = 3      # derivation above
LINE_ANCHOR_WINDOW = 3      # same number: within it -> DRIFT note at most
DURATION_TOLERANCE_MIN_SECONDS = 15 * 60
DURATION_TOLERANCE_FRACTION = 0.5


FIELD_TOKEN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def is_field_list(tok):
    """True for a backtick span that is SPECIFICALLY the register's own
    'writes `{a, b, c}`' shape -- braced or comma-joined, every segment a
    bare identifier, nothing else. Deliberately narrow: normal prose
    containing a comma ('the rate, which is capped...') will not have every
    segment match a bare-identifier pattern, so it is never mistaken for a
    field list. Added 2026-09-28 (v3 correction e, see declaration above)."""
    inner = tok.strip()
    if inner.startswith("{") and inner.endswith("}"):
        inner = inner[1:-1]
    elif "," not in inner:
        return False
    parts = [p.strip() for p in inner.split(",")]
    return len(parts) >= 2 and all(FIELD_TOKEN.match(p) for p in parts if p)


def anchor_candidates(sentence):
    """Identifier-looking tokens from the sentence that may pin a cited
    line: backticked tokens, underscore/camelCase identifiers, call-shaped
    names, the stems of OTHER cited filenames, and (v3) the individual
    field names inside a `{a, b, c}`-shaped backtick span. Plain English
    words are never anchors, by design (see declaration above)."""
    cands = set()
    for m in BACKTICK.finditer(sentence):
        tok = m.group(1).strip()
        # A candidate must contain at least one LETTER. Without this, a
        # citation's OWN backticked wrapper ("`:6010`") becomes a candidate
        # for itself, and a bare number/symbol string is exactly the kind of
        # token likely to match some unrelated byte sequence in a large file
        # by coincidence -- found 2026-09-28 on sf_ceremonial_items, where
        # ":6010" as a candidate would have searched for that literal
        # substring platform-wide. Locked by F23.
        if 3 <= len(tok) <= 80 and any(c.isalpha() for c in tok):
            cands.add(tok)
        # v3 correction (e): the register's single most common citation
        # shape is "`:NNNN` writes `{field1, field2, ...}`" -- the WHOLE
        # blob almost never appears verbatim in real source (real code has
        # punctuation, defaults and other keys between the field names), so
        # it silently produced ANCHOR-ABSENT even when every individual
        # field name is right there in the file. Found on sf_ceremonial_items:
        # `{item, kind, serial, inspected}` never matches as one string, but
        # `inspected` alone sits on the real (drifted) write line. Splitting
        # is deliberately narrow (is_field_list) so ordinary comma'd prose
        # is never treated as a field list. Locked by F24/F25.
        if is_field_list(tok):
            inner = tok.strip()
            if inner.startswith("{") and inner.endswith("}"):
                inner = inner[1:-1]
            for part in inner.split(","):
                part = part.strip()
                if 3 <= len(part) <= 80:
                    cands.add(part)
    for rx in (UNDERSCORE_ID, CAMEL_ID, CALL_ID):
        for m in rx.finditer(sentence):
            cands.add(m.group(1))
    for m in FILELINE.finditer(sentence):
        stem = os.path.basename(m.group(1))
        stem = stem.rsplit(".", 1)[0]
        if len(stem) >= 4:
            cands.add(stem)
    # strip trailing call parens variants
    return {c[:-2] if c.endswith("()") else c for c in cands}


_CODE_CHARS = set("&|!=<>+().[]{}")
_WS = re.compile(r"\s+")


def anchor_in_line(cand, line):
    """Substring test; code-shaped anchors (operators/punctuation) compare
    whitespace-normalized so `a && !b` finds `a&&!b` -- v2 correction (b)."""
    if cand in line:
        return True
    if any(c in _CODE_CHARS for c in cand):
        return _WS.sub("", cand) in _WS.sub("", line)
    return False


# WORD-BOUNDARY, not bare substring -- found 2026-09-29 chasing the F28
# negation-exemption fix: a bare `w in low` check matched "missing" as a
# SUBSTRING of the identifier `quux_missing_fn` (F14's own fixture anchor),
# wrongly negating a sentence that names a missing-shaped FUNCTION, not an
# absence claim. Underscore is a \w char, so \b correctly refuses to match
# inside `quux_missing_fn` (no boundary either side of "missing" there)
# while still matching a real standalone word. F30/F31 lock both directions.
NEGATION_PATTERN = re.compile(
    r'\b(?:' + '|'.join(re.escape(w) for w in NEGATION_WORDS) + r')\b'
)


def is_negated(sentence):
    return bool(NEGATION_PATTERN.search(sentence.lower()))


def hexish(tok):
    return any(c.isdigit() for c in tok) and any(c in "abcdef" for c in tok)


def parse_duration_seconds(num_word, unit_word):
    w = num_word.lower()
    n = float(w) if w.isdigit() else WORD_NUMBERS.get(w)
    if n is None:
        return None
    return n * 3600 if unit_word.lower().startswith(("hour", "hr")) else n * 60


# --- fixture lock --------------------------------------------------------
# Fixtures run against a THROWAWAY git repo built here, in isolation --
# never against the real repo, never alongside a real report (item 5:
# a lock that rides beside live data can be satisfied by the data).

_APP_PY = "\n".join(
    ["# fixture module"] * 9
    + ["def frobnicate():"]                     # line 10
    + ["    return None"]
    + ["# filler %d" % i for i in range(12, 20)]
    + ["WIDGET_LIMIT = 5"]                      # line 20
    + ["# tail %d" % i for i in range(21, 25)]
    + ["checked = t.billable&&!t.invoiced"]     # line 25, unspaced on purpose
    + ["# tail %d" % i for i in range(26, 31)]
) + "\n"

DANGLING = "0a1b2c3d4e5f"  # asserted unresolvable at build time


def build_fixture_repo():
    """git-init a temp repo with THREE commits: sha1/sha2 one hour apart (as
    before), then sha3 -- a REAL git commit that inserts 5 lines above
    `def frobnicate():`, shifting it from line 10 to line 15 and the
    billable check from line 25 to line 30. Returns (path, sha1, sha2, sha3).

    sha3 exists for the realistic-transition fixtures (F26/F27, 2026-09-28):
    a citation accurate AT sha2 (line 10/25) is checked against the repo's
    CURRENT working tree, which is now at sha3 -- the drift the tool must
    detect is produced by an ACTUAL git commit shifting real lines, not a
    fixture author hand-picking "the wrong number." This is the realistic
    version of exactly what happened for real on sf_ceremonial_items: a
    citation was accurate when written, then a later commit moved the code.

    Raises RuntimeError on any git failure -- the caller treats that as
    COULD NOT RUN, never as fixtures-passed."""
    d = tempfile.mkdtemp(prefix="hover_editor_fx_")
    def g(*args, **env_extra):
        env = dict(os.environ,
                   GIT_AUTHOR_NAME="fx", GIT_AUTHOR_EMAIL="fx@x",
                   GIT_COMMITTER_NAME="fx", GIT_COMMITTER_EMAIL="fx@x",
                   **env_extra)
        r = subprocess.run(["git"] + list(args), cwd=d, env=env,
                           capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError("fixture git %s: %s" % (args[0], r.stderr.strip()))
        return r.stdout.strip()
    g("init", "-q")
    os.makedirs(os.path.join(d, "src"), exist_ok=True)
    os.makedirs(os.path.join(d, "data"), exist_ok=True)
    with open(os.path.join(d, "src", "app.py"), "w") as f:
        f.write(_APP_PY)
    with open(os.path.join(d, "data", "config.json"), "w") as f:
        f.write('{"widget_limit": 5}\n')
    g("add", "-A")
    # salt the message until the 12-char sha prefix satisfies hexish() --
    # a fixture sha with no digit or no a-f letter would be skipped by the
    # extractor and fail the lock spuriously (~0.4% per sha at 12 chars).
    def committed(msg, date, amend=False):
        for salt in range(200):
            args = ["commit", "-q", "-m", "%s %d" % (msg, salt)]
            if salt or amend:
                args.insert(1, "--amend")
            g(*args, GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date)
            sha = g("rev-parse", "HEAD")
            if hexish(sha[:12]):
                return sha
        raise RuntimeError("fixture invalid: no hexish sha prefix in 200 salts")
    sha1 = committed("first", "2026-01-01T10:00:00Z")
    with open(os.path.join(d, "src", "app.py"), "a") as f:
        f.write("# second commit touch\n")
    g("add", "-A")
    sha2 = committed("second", "2026-01-01T11:00:00Z")
    # the dangling token must actually be dangling in this repo
    r = subprocess.run(["git", "cat-file", "-t", DANGLING], cwd=d,
                       capture_output=True, text=True)
    if r.returncode == 0:
        raise RuntimeError("fixture invalid: DANGLING token resolves")

    # sha3: a REAL later edit that shifts everything below it down 5 lines.
    with open(os.path.join(d, "src", "app.py")) as f:
        pre_shift = f.read()
    shifted = ("# five NEW lines landed here in a later, real commit\n" * 5) + pre_shift
    with open(os.path.join(d, "src", "app.py"), "w") as f:
        f.write(shifted)
    g("add", "-A")
    sha3 = committed("third: a real edit shifts everything below by 5 lines",
                     "2026-01-01T12:00:00Z")
    # LEAVE THE WORKING TREE AT sha2, not sha3. F1-F25 were all authored
    # against sha2's line numbers (frobnicate at :10, billable at :25,
    # WIDGET_LIMIT at :20); if the working tree stayed at sha3 by default,
    # every one of them would silently start checking the WRONG lines. Only
    # F26/F27 need sha3, and they check it out themselves (see "checkout"
    # in their fixture dict) and restore sha2 afterward.
    g("checkout", "-q", sha2)
    return d, sha1, sha2, sha3


def fixtures(sha1, sha2, sha3=None):
    """(name, report_text, expected) where expected is a dict of exact
    counts the run must produce: findings / drift_notes / cannot_check /
    claims (total extracted). Both directions are covered: texts that MUST
    flag and texts that MUST NOT.

    sha3 (default None, only real when called with a live build_fixture_repo()
    result): the realistic-transition fixtures F26/F27 need the repo to
    genuinely BE at sha3 (lines shifted by a real commit) when the tool runs
    against its working tree -- the count-only call site
    (`len(fixtures("0"*40, "1"*40))`) never executes these against a repo,
    so sha3=None there is harmless."""
    return [
        ("F1 good hash",
         "The gap was fixed in %s and verified." % sha1[:12],
         dict(findings=0, cannot_check=0, min_claims=1)),
        ("F2 dangling hash",
         "The control was written and committed in %s instead." % DANGLING,
         dict(findings=1, cannot_check=0, min_claims=1)),
        ("F3 negated hash is the report asserting absence",
         "%s is NOT a valid object in this repo -- a dangling ref." % DANGLING,
         dict(findings=0, cannot_check=0, min_claims=1)),
        ("F4 good line citation",
         "`frobnicate` at src/app.py:10 returns early.",
         dict(findings=0, drift_notes=0, cannot_check=0, min_claims=1)),
        ("F5 small drift is a note, not a finding",
         "`frobnicate` at src/app.py:12 returns early.",
         dict(findings=0, drift_notes=1, cannot_check=0, min_claims=1)),
        ("F6 wrong line is a finding",
         "`frobnicate` at src/app.py:25 returns early.",
         dict(findings=1, cannot_check=0, min_claims=1)),
        ("F7 missing path",
         "The helper lives in src/gone.py alongside the rest.",
         dict(findings=1, cannot_check=0, min_claims=1)),
        ("F8 negated missing path",
         "src/gone.py does not exist anywhere in the tree.",
         dict(findings=0, cannot_check=0, min_claims=1)),
        ("F9 correct duration between two commits",
         "%s landed one hour after %s." % (sha2[:12], sha1[:12]),
         dict(findings=0, cannot_check=0, min_claims=3)),
        ("F10 wrong duration between two commits",
         "%s landed four hours after %s." % (sha2[:12], sha1[:12]),
         dict(findings=1, cannot_check=0, min_claims=3)),
        ("F11 duration with no commits nearby cannot be checked",
         "The replacement landed four hours later that night.",
         dict(findings=0, cannot_check=1, min_claims=1)),
        ("F12 line beyond end of file",
         "See the guard at src/app.py:999 for the refusal.",
         dict(findings=1, cannot_check=0, min_claims=1)),
        ("F13 nothing checkable is not a pass",
         "Everything held up fine and the work is done.",
         dict(findings=0, cannot_check=0, min_claims=0, nothing_to_check=True)),
        ("F14 anchor absent from cited file entirely",
         "`quux_missing_fn` at src/app.py:10 handles it.",
         dict(findings=1, cannot_check=0, min_claims=1)),
        ("F15 .json is not truncated to .js (v2 correction a)",
         "The verdict lives in data/config.json.",
         dict(findings=0, cannot_check=0, min_claims=1)),
        ("F16 spaced code snippet finds unspaced source (v2 correction b)",
         "The picker at src/app.py:25 filters `t.billable && !t.invoiced`.",
         dict(findings=0, drift_notes=0, cannot_check=0, min_claims=1)),
        # v3: implied-file citations (bare `:NNNN`, file given by --default-file)
        ("F17 implied-file good citation with default_file",
         "READ OUT OF THE APP: `:10` calls `frobnicate`.",
         dict(findings=0, cannot_check=0, min_claims=1,
              default_file="src/app.py")),
        ("F18 implied-file small drift with default_file is a note",
         "READ OUT OF THE APP: `:12` calls `frobnicate`.",
         dict(findings=0, drift_notes=1, cannot_check=0, min_claims=1,
              default_file="src/app.py")),
        ("F19 implied-file wrong citation with default_file is a finding",
         "READ OUT OF THE APP: `:25` calls `frobnicate`.",
         dict(findings=1, cannot_check=0, min_claims=1,
              default_file="src/app.py")),
        ("F20 implied-file citation with NO default_file cannot be checked",
         "READ OUT OF THE APP: `:10` calls `frobnicate`.",
         dict(findings=0, cannot_check=1, min_claims=1)),
        ("F21 explicit path:line is not ALSO counted as an implied citation",
         "See `frobnicate` at src/app.py:10 for the details.",
         dict(findings=0, cannot_check=0, min_claims=1, max_claims=1,
              default_file="src/gone_should_not_be_used.py")),
        ("F22 a bold-glued sentence boundary must still split, or an EARLIER "
         "clause's anchor leaks into a LATER citation's search "
         "(v3 correction c)",
         "**Uses `frobnicate` elsewhere.** READ OUT: `:25` confirms it.",
         dict(findings=0, cannot_check=0, min_claims=1, shallow=1,
              default_file="src/app.py")),
        ("F23 a citation's own numeric wrapper is not an anchor candidate "
         "for itself (v3 correction d)",
         "READ OUT OF THE APP: `:10` handles it.",
         dict(findings=0, cannot_check=0, min_claims=1, shallow=1,
              default_file="src/app.py")),
        ("F24 a field-list backtick span is split into per-field candidates, "
         "and a split field matching the CITED line is an exact OK "
         "(v3 correction e)",
         "READ OUT: `:10` writes `{item, frobnicate, kind}`.",
         dict(findings=0, drift_notes=0, cannot_check=0, min_claims=1,
              default_file="src/app.py")),
        ("F25 a split field matching a DIFFERENT line is the real "
         "LINE-MISMATCH the row has, not a false ANCHOR-ABSENT "
         "(v3 correction e)",
         "READ OUT: `:10` writes `{item, checked, kind}`.",
         dict(findings=1, cannot_check=0, min_claims=1,
              default_file="src/app.py")),
        # F28: negated anchor-absence -- fixed 2026-09-29, H1's own log #658.
        # is_negated(sentence) was already computed in check_fileline() but
        # was ONLY consulted in the MISSING-PATH branch (abspath is None);
        # the anchor-search branch a few lines later had no exemption at
        # all, so a report correctly claiming "field X is no longer written
        # at line Y" -- true, and the report SAYING so -- still read as a
        # false ANCHOR-ABSENT finding. Real incident: stonedesk.html's
        # sd_seamai push sites genuinely no longer write a `remake` field
        # (removed on purpose, documented in the code's own comment); this
        # role's own editor pass flagged the TRUE claim as a FINDING.
        ("F28 a negated anchor claim (report correctly says the anchor is "
         "NO LONGER there) is OK, not FINDING -- the real #658 incident "
         "shape, reproduced against this fixture's own file rather than "
         "against a paraphrase",
         "The old `gizmo_counter` field is no longer set at src/app.py:10 "
         "-- removed on purpose.",
         dict(findings=0, cannot_check=0, min_claims=1)),
        # F29 KNOWN-BAD CONTROL, same mechanism, opposite direction: an
        # anchor-absence claim with NO negation language must STILL be a
        # FINDING -- the exemption is negation-scoped, not "anchor absent
        # is always fine now". Worded as close to F28 as possible (same
        # anchor, same cited line, same file) so the ONLY variable changing
        # is the negation phrase -- proving the fix is keyed on the
        # negation, not on coincidental sentence shape.
        ("F29 KNOWN-BAD CONTROL: the SAME absent anchor, SAME cited line, "
         "with NO negation wording -- must stay FINDING, proving the F28 "
         "exemption is negation-scoped and not a blanket anchor-absent "
         "pass",
         "The `gizmo_counter` field is set at src/app.py:10.",
         dict(findings=1, cannot_check=0, min_claims=1)),
        # F30: is_negated() word-boundary regression, found WHILE fixing
        # F28/F29 above -- a bare substring check matched "missing" inside
        # the identifier `quux_missing_fn` (this is F14's own fixture,
        # replayed here to name the mechanism directly) and wrongly
        # exempted it via the F28 fix, breaking F14. Locks that F14 stays a
        # real FINDING now that negation is consulted on this branch.
        ("F30 REGRESSION GUARD: a negation WORD embedded as a substring "
         "inside an unrelated identifier (`quux_missing_fn` contains "
         "'missing') must NOT trigger the negation exemption -- this is "
         "F14 restated to name why it must keep passing after F28's fix",
         "`quux_missing_fn` at src/app.py:10 handles it.",
         dict(findings=1, cannot_check=0, min_claims=1)),
        # F31 CONTROL: a genuine STANDALONE negation word must still work
        # after switching to word-boundary matching -- proves NEGATION_PATTERN
        # is not accidentally over-tightened into matching nothing at all.
        ("F31 CONTROL: a genuine standalone negation word (not embedded in "
         "an identifier) still triggers the exemption after the "
         "word-boundary fix",
         "The `gizmo_counter` field is missing from src/app.py:10 now.",
         dict(findings=0, cannot_check=0, min_claims=1)),
    ] + ([] if sha3 is None else [
        # REALISTIC-TRANSITION FIXTURES, added 2026-09-28. Every fixture
        # above plants its "wrong line" by hand-picking a number the fixture
        # author chose. These two instead cite the line that was ACTUALLY
        # correct at sha2 -- :10 for frobnicate, :25 for the billable check
        # -- and run against the repo's CURRENT working tree, which a REAL
        # third commit (sha3) has since shifted by 5 real lines. The drift
        # the tool must catch is PRODUCED by git, not injected by the test.
        ("F26 REALISTIC, IMPLIED-FILE SHAPE (the register's own dominant "
         "citation form): a bare `:10` accurate at sha2 (frobnicate) is "
         "checked against the repo NOW AT sha3, which a real commit shifted "
         "it to :15 -- the tool must report the ACTUAL git-produced drift, "
         "not a hand-picked wrong number",
         "READ OUT OF THE APP: `:10` calls `frobnicate`.",
         dict(findings=1, cannot_check=0, min_claims=1,
              default_file="src/app.py", checkout=sha3)),
        ("F27 REALISTIC, IMPLIED-FILE SHAPE: the billable check, accurate "
         "at sha2 (:25), is now at :30 after the SAME real sha3 commit -- "
         "drift 5, one past the LINE_DRIFT_FINDING threshold of 3, so this "
         "is a FINDING not a DRIFT note, exactly because a real commit "
         "moved it that far, not because a fixture author chose 5",
         "READ OUT: `:25` filters `t.billable && !t.invoiced`.",
         dict(findings=1, cannot_check=0, min_claims=1,
              default_file="src/app.py", checkout=sha3)),
    ])
