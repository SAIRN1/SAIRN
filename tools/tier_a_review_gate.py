"""The independent-review rule on Tier A code, as a gate rather than a habit.

    python tools/tier_a_review_gate.py                 # check the working tree
    python tools/tier_a_review_gate.py --diff-range A..B   # check a commit range
    python tools/tier_a_review_gate.py --open "why"    # record this session's obligation
    python tools/tier_a_review_gate.py --list          # what is open, and whose
    python tools/tier_a_review_gate.py --discharge <author> "<verdict>"
    python tools/tier_a_review_gate.py --auto-discharge [--write]

Exit 0 clean, 1 a finding, 2 COULD NOT TELL -- never folded into either of the
other two (PR 1.11).

── WHY THIS EXISTS ─────────────────────────────────────────────────────────────
The rule has been real and unenforced the whole time. docs/SAIRN-OPEN-WORK-INDEX
.md carries it in prose on the rows somebody happened to remember --
"⚠ Independent review, per the standing rule that the session which wrote the
code shares its own blind spot", "the reviewer should be someone else" -- and
nothing anywhere checks it. Of the 77 records in the defect register, 7 name
`independent-review` as the detection method, so the practice works when it
happens. Nothing made it happen.

A rule enforced by remembering is enforced on the days people remember, which
are not the days it matters.

── WHAT IT CAN AND CANNOT DO, SAID PLAINLY ────────────────────────────────────
IT CANNOT read a review, judge one, or know whether the reviewer looked. Any
gate claiming otherwise would be lying about its own reach.

WHAT IT CAN DO is exactly two things, and they are the two failures this
platform has actually had:

  1. A Tier A change reaching origin with the obligation never recorded, so
     nobody downstream can tell a reviewed change from an unreviewed one.
  2. A record signed by its own author. "I reviewed my own work" is the one
     claim the rule exists to refuse, and it is mechanically checkable.

── HOW "TOUCHES TIER A CODE" IS DECIDED, and the first version was useless ────
It reads the DIFF, not the file. A Tier A resource counts as touched when its
name appears in the changed hunks -- added lines, removed lines, or the three
lines of context around them. The names come from docs/CRITICALITY-TIERS.md,
the register the tier decision already lives in, and never from a second copy.

THE OBVIOUS IMPLEMENTATION WAS WRITTEN FIRST AND MEASURED, and it is worth
recording because it read as correct: "a changed file counts if its CONTENT
names a Tier A resource." Run against the working tree it reported **78 Tier A
resources touched**, because api/sd-data.js contains every resource name on the
platform. A gate that answers "you touched everything" on every push says
nothing and would have been switched off inside a week. At hunk granularity the
same commit reports the seven sc_* resources it actually changed.

Comments count as naming a resource, deliberately: a hunk that discusses
sc_claims was edited by somebody thinking about sc_claims.

THE FALSE-POSITIVE DIRECTION IS STILL THE SAFE ONE -- an over-inclusive answer
costs one register entry, an under-inclusive one is a Tier A change that slips
through looking clean. What changed is that the answer is now specific enough to
act on.

THE EXCLUSIONS, each narrow, each a predicate about what a file IS rather than a
filename somebody has to remember to add, and each named here rather than left
silent. Deliberately not counted: this list has grown twice and a number in
prose would be wrong the third time.

  * a REPORT-ONLY REVIEW ARTEFACT -- see is_report_only_artefact(), which also
    records why this is NOT "exclude tests/". A file that cannot fail cannot be
    a guard, so changing it cannot weaken one; and a review of a Tier A module
    necessarily names that module, so refusing it blocks the artefact that
    discharges the obligation being demanded.
  * docs/ and sql/ -- a document or a migration naming a resource is not code
    serving it, and CRITICALITY-TIERS.md names every Tier A resource by
    definition, so including docs/ would make every push a Tier A push and the
    gate would mean nothing within a week.
  * this file, the register it reads, and the gate that calls it -- otherwise
    recording an obligation is itself a Tier A change requiring an obligation.
"""
import calendar
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import sairn_session_identity as _identity            # noqa: E402
REGISTER = os.path.join(REPO, 'docs', 'CRITICALITY-TIERS.md')
REVIEWS = os.path.join(REPO, 'docs', 'tier-a-reviews.json')
RULE_REGISTRY = os.path.join(REPO, 'docs', 'coding-rule-registry.json')
# Module-level rather than inlined in _register_records(), for the same reason
# REVIEWS is: a path buried in a function body cannot be pointed at a fixture,
# so the auto-discharge path could only ever be exercised against the live
# register -- which means the only way to test a close is to perform one.
DEFECT_REGISTER = os.path.join(REPO, 'docs', 'defect-density-register.json')

# Files that can never themselves create an obligation. Kept tiny and explicit;
# a growing exclusion list is how a gate stops covering anything.
SELF = (
    'docs/tier-a-reviews.json',
    'tools/tier_a_review_gate.py',
    'tools/sairn_push_gate_hook.py',
    'tests/run_tier_a_review_gate_probe.py',
)


# ── WHY THIS IS STILL A DENY-LIST, MEASURED RATHER THAN PREFERRED ───────────
# After the THIRD false positive of one shape (a worklog, a review probe, a
# claim file -- each a file whose job is to TALK ABOUT Tier A work) the obvious
# recombination was to INVERT: allow-list what can SERVE a resource instead of
# deny-listing what describes it. That was measured before it was built, and the
# measurement says do not.
#
# An `api/ + tests/ + tools/ + root *.html` allow-list would SILENTLY DROP 42
# files that are in scope today, across ten path classes -- including
# `.claude/settings.json`, which wires the push hooks; `.githooks/pre-commit`;
# and `.github/workflows/codeql.yml`. Every one of those can change whether a
# Tier A resource is protected at all.
#
# THE TWO PREDICATES FAIL IN OPPOSITE DIRECTIONS AND THAT DECIDES IT.
#   deny-list  fails into a FALSE POSITIVE -- loud, annoying, and fixed in a line
#   allow-list fails into SILENCE -- a new directory serving Tier A code is never
#              reviewed and nothing says so
# For a gate whose entire subject is somebody not being told, failing into
# silence is the wrong direction. Inverting would have traded three loud
# annoyances for one quiet hole.
#
# SO THE REAL DEFECT WAS NEVER THE POLARITY. It was that each exclusion was an
# anonymous clause in a boolean, so a fourth false positive would be fixed by
# appending a fifth clause and nobody would be forced to notice the pattern.
# Every exclusion now carries a NAMED REASON, and
# tests/run_tier_a_review_gate_probe.py FAILS when a tracked path class is
# neither in scope nor explicitly excluded -- so a new top-level directory is a
# red arm rather than a silent gap, and a new documentation-shaped file is one
# line WITH a reason somebody has to write.
SKIP_REASONS = (
    # (predicate, reason). Order matters only for which reason is reported.
    (lambda c: c in SELF,
     'the gate itself -- recording an obligation must not create one'),
    (lambda c: c.startswith('docs/'),
     'prose. CRITICALITY-TIERS.md names every Tier A resource by definition, so '
     'including docs/ would make every push a Tier A push'),
    (lambda c: c.startswith('sql/'),
     'a migration naming a resource is not code serving it'),
    (lambda c: c.startswith('.claude/claims/'),
     'a claim is a record of INTENT. Narrower than .claude/ on purpose: '
     'settings.json and the hooks beside it genuinely change what gates a push'),
    (lambda c: c.lower().endswith('.md'),
     'markdown is prose, never a request handler -- and every session worklog '
     'lives at the repo root by convention'),
)


def skip_reason(cur):
    """The REASON this path cannot create an obligation, or None if it can.

    A reason rather than a boolean, so the classification is legible and so the
    coverage control can assert that every tracked path class has one.
    """
    for pred, why in SKIP_REASONS:
        if pred(cur):
            return why
    return None


class CouldNotTell(Exception):
    pass


# ── IDENTITY COMES FROM A MARKER, NOT FROM THE FOLDER NAME (2026-09-18) ────
# Hover finding #258, HIGH. This function existed here AND in tools/sairn_claim.py,
# byte for byte, and both derived identity from `os.path.basename(REPO)`. So
# "who am I" was a property of a directory name: a clone renamed `SAIRN-cody`
# would discharge its own Tier A obligation and the gate would report an
# INDEPENDENT REVIEW, and the same string decides who holds a claim, so a
# rename silently reassigns work in the other direction too.
#
# tools/sairn_session_identity.py is now the ONE implementation -- two answers
# to "who am I" is what made the self-review refusal meaningless. It reads a
# per-clone marker in .git/, the convention hover_auditor_scope_gate.py already
# uses, and it RAISES when the marker is absent rather than falling back: a
# fallback would leave the spoofable path live with nothing to say which one
# answered (PR 1.11).
#
# IT IS NOT A CRYPTOGRAPHIC CONTROL. Anything that can rename the directory can
# also write the marker. What it closes is DRIFT AND ACCIDENT -- identity stops
# being a side effect of a folder name and becomes a deliberate act with a file
# to point at.
def session_name():
    return _identity.session_name()


def tier_a_resources():
    """Read from the register. FAILS CLOSED: a register that cannot be parsed,
    or that yields no Tier A rows, is COULD NOT TELL and never an empty set --
    an empty set would make every push clean, which is the quietest possible
    way for this gate to stop working."""
    try:
        text = io.open(REGISTER, encoding='utf-8').read()
    except OSError as e:
        raise CouldNotTell('docs/CRITICALITY-TIERS.md could not be read: %s' % e)
    names = set()
    for line in text.split('\n'):
        m = re.match(r'^\|\s*`([a-z0-9_]+)`\s*\|\s*\*\*A\*\*\s*\|', line)
        if m:
            names.add(m.group(1))
    if not names:
        raise CouldNotTell(
            'docs/CRITICALITY-TIERS.md yielded ZERO Tier A rows. That is either '
            'a parse failure or a register that has lost its table; both mean '
            'this gate cannot answer, and an empty set would silently pass '
            'every push.')
    return names


# ── THE SECOND SUBJECT KIND: A RULE, NOT A ROW (2026-09-24) ─────────────────
# Everything above this point answers "which stored Tier A resources does this
# change serve". That is the right question for a handler and the WRONG question
# for a validator, and the gate said so itself on 2026-09-24 when it refused to
# record an obligation for the GP therapy-discipline modifier: "Nothing in this
# change names a Tier A resource, so there is no obligation to record."
#
# IT WAS CORRECT. scValidatePtSession() persists nothing. But a missing GP makes
# a therapy claim UNPROCESSABLE -- never adjudicated at all -- so the change with
# no reviewable subject was the one that decides whether the practice gets paid,
# while a one-line edit to a handler that stores a row owes a full review. Six
# shipped rules were in the same position: the 8-minute aggregation, the KX
# threshold, CQ, MPPR, the RTM windows and DMEPOS.
#
# A RULE DECIDES WHETHER A CLAIM IS ADJUDICATED. A ROW DECIDES WHAT IS
# REMEMBERED. The obligation ledger, the author-cannot-self-sign refusal, the
# ownership assignment, the overdue clock and the merge policy are all correct
# for both and are REUSED RATHER THAN COPIED -- a record simply carries `rules`
# as well as `resources`, and a record may have either or both. A second ledger
# with a second discharge path would be a second place for the self-signing
# refusal to be got wrong.
#
# ATTRIBUTION IS BY LINE RANGE, NOT BY NAME, and that is the one place this half
# is stronger than the resource half. A resource is found by its name appearing
# on a changed line, which misses a change that does not mention it. A rule's
# range is BRACE-MATCHED out of the file as it now stands, so any changed line
# inside the body counts -- including one that names nothing.
def _anchor_range(text, anchor):
    """(first_line, last_line) 1-indexed for `anchor`'s block, or raise.

    FAILS CLOSED ON BOTH SIDES OF UNIQUENESS. Zero matches means the anchor was
    reworded and this rule is no longer locatable -- reporting it as untouched
    would be the silent half of a stale anchor, which is the failure this
    platform has recorded five times. More than one match means the gate cannot
    say WHICH site a change hit, which is the same answer wearing a different
    hat.

    An anchor with no `{` or `[` after it covers its own line. That is how a
    bare constant is expressed -- `var KX_MR_THRESHOLD_2026 = 3000;` has no
    block -- rather than inventing a second kind of entry for it.
    """
    n = text.count(anchor)
    if n != 1:
        raise CouldNotTell(
            'the anchor %r matches %d lines, not 1. Zero means it was reworded; '
            'more than one means this rule cannot say which site a change hit. '
            'Either way the gate cannot answer, and answering "untouched" would '
            'be the quiet half of a stale anchor.' % (anchor, n))
    start = text.index(anchor)
    first_line = text.count('\n', 0, start) + 1
    # The opening bracket must be on the anchor's own line, not the next one.
    # `var X = {` and `function f(a) {` both qualify; a bare `var X = 3;` does
    # not, and its range is that one line.
    eol = text.find('\n', start)
    if eol < 0:
        eol = len(text)
    head = text[start:eol]
    opener = None
    for ch in ('{', '['):
        i = head.find(ch)
        if i >= 0 and (opener is None or i < opener[0]):
            opener = (i, ch)
    if opener is None:
        return first_line, first_line
    close = {'{': '}', '[': ']'}[opener[1]]
    i, depth, q = start + opener[0], 0, None
    while i < len(text):
        c, p = text[i], text[i - 1] if i else ''
        if q:
            if c == q and p != '\\':
                q = None
        elif c in ('"', "'", '`'):
            q = c
        elif text.startswith('//', i):
            j = text.find('\n', i)
            i = len(text) if j < 0 else j
        elif text.startswith('/*', i):
            j = text.find('*/', i)
            i = len(text) if j < 0 else j + 1
        elif c == opener[1]:
            depth += 1
        elif c == close:
            depth -= 1
            if depth == 0:
                return first_line, text.count('\n', 0, i) + 1
        i += 1
    raise CouldNotTell('the block opened by %r is never closed' % anchor)


def coding_rules():
    """[{rule, app, file, anchor, ...}]. FAILS CLOSED exactly like
    tier_a_resources(): an unreadable or empty registry is COULD NOT TELL, never
    a clean answer, because an empty list would make every rule change invisible
    and that is the quietest way for this half to stop working."""
    try:
        data = json.load(io.open(RULE_REGISTRY, encoding='utf-8'))
    except OSError as e:
        raise CouldNotTell('docs/coding-rule-registry.json could not be read: %s' % e)
    except ValueError as e:
        raise CouldNotTell('docs/coding-rule-registry.json is not valid JSON: %s' % e)
    rules = data.get('rules') if isinstance(data, dict) else None
    if not isinstance(rules, list) or not rules:
        raise CouldNotTell(
            'docs/coding-rule-registry.json yielded ZERO rules. That is a parse '
            'failure or a registry that has lost its list; both mean this gate '
            'cannot answer about rule changes, and an empty set would pass every '
            'push silently.')
    for r in rules:
        for field in ('rule', 'app', 'file', 'anchor'):
            if not str(r.get(field) or '').strip():
                raise CouldNotTell(
                    'a rule entry is missing %r: %s. A rule the gate cannot '
                    'locate is one it would report as untouched forever.'
                    % (field, json.dumps(r)[:120]))
    return rules


def changed_lines_by_file(diff_text):
    """{path: set(new-file line numbers this diff CHANGED)}.

    An added line is at its own new-file position. A DELETED line is recorded at
    the position it was removed FROM -- the new-file line the deletion sits
    between -- because a rule gutted by a pure deletion is a rule change, and
    attributing nothing to it would make "delete the body" the one edit this
    gate cannot see. That is the shape the whole registry exists to refuse.

    CONTEXT LINES ARE NOT CHANGES and are deliberately not recorded. Counting
    them would attribute every rule within three lines of any edit anywhere in
    the file, which is how a range check quietly becomes a file check.
    """
    out, cur, new_ln = {}, None, None
    for line in diff_text.split('\n'):
        if line.startswith('+++ '):
            path = line[4:].strip()
            if path == '/dev/null':
                cur = None
                continue
            cur = (path[2:] if path[:2] in ('a/', 'b/') else path).replace('\\', '/')
            out.setdefault(cur, set())
            continue
        if cur is None:
            continue
        m = re.match(r'^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@', line)
        if m:
            new_ln = int(m.group(1))
            continue
        if new_ln is None:
            continue
        if line.startswith('+'):
            out[cur].add(new_ln)
            new_ln += 1
        elif line.startswith('-'):
            # The deletion happened HERE in the new file. No increment: the
            # removed line occupies no new-file position of its own.
            out[cur].add(new_ln)
        elif line.startswith(' '):
            new_ln += 1
    return out


def touched_rules(diff_text, rules):
    """rule name -> [files]. Raises CouldNotTell if an anchor cannot be located
    in a file this change actually touches."""
    changed = changed_lines_by_file(diff_text)
    hits = {}
    for r in rules:
        path = r['file'].replace('\\', '/')
        lines = changed.get(path)
        if not lines:
            continue
        try:
            text = io.open(os.path.join(REPO, path), encoding='utf-8').read()
        except OSError as e:
            raise CouldNotTell('%s is registered for rule %r and could not be '
                               'read: %s' % (path, r['rule'], e))
        lo, hi = _anchor_range(text, r['anchor'])
        if any(lo <= n <= hi for n in lines):
            hits.setdefault(r['rule'], []).append(path)
    return hits


def load_reviews():
    try:
        data = json.load(io.open(REVIEWS, encoding='utf-8'))
    except OSError as e:
        raise CouldNotTell('docs/tier-a-reviews.json could not be read: %s' % e)
    except ValueError as e:
        raise CouldNotTell('docs/tier-a-reviews.json is not valid JSON: %s' % e)
    if not isinstance(data, dict) or not isinstance(data.get('records'), list):
        raise CouldNotTell('docs/tier-a-reviews.json has no `records` list')
    return data


def save_reviews(data):
    """Write the register ATOMICALLY -- temp file, then os.replace.

    ── WHY, AND IT IS NOT HYPOTHETICAL (2026-09-21) ────────────────────────
    This used to open REVIEWS for writing directly. Two sessions saving at once
    therefore interleaved inside one file, and the result was not a lost record
    -- it was a CORRUPT one. Driven before the change, two threads appending and
    saving:

        json.decoder.JSONDecodeError: Extra data: line 1162 column 1

    The shorter write left the tail of the longer one behind, so the file held
    two JSON documents concatenated. load_reviews() reads that as CouldNotTell,
    which the push-gate hook maps to "COULD NOT TELL -- this is NOT a pass", so
    it fails CLOSED and blocks every push on this platform until somebody
    repairs the JSON by hand. Failing closed is right; needing a hand repair to
    get moving again is not.

    os.replace is atomic on the same filesystem on both POSIX and Windows, so a
    reader sees the old file or the new one and never a half-written one. This
    does NOT make the read-modify-write safe -- two concurrent --open calls can
    still LOSE one record, because both read before either writes -- and that is
    a separate defect, disclosed rather than quietly assumed away. What this
    removes is the mode that stops the whole platform.
    """
    # THE TEMP NAME MUST BE UNIQUE PER WRITER, NOT PER PROCESS, and the first
    # version of this was `REVIEWS + '.tmp-%d' % os.getpid()`. Two THREADS share
    # a pid, so both wrote the same temp file, interleaved inside it, and then
    # both replaced REVIEWS with it -- the corruption simply moved one file
    # along and the arm written to catch it caught it. mkstemp in the same
    # directory gives a name nothing else can hold, and same-directory keeps
    # os.replace atomic (a cross-filesystem replace is not).
    d = os.path.dirname(os.path.abspath(REVIEWS)) or '.'
    fd, tmp = tempfile.mkstemp(prefix=os.path.basename(REVIEWS) + '.tmp-', dir=d)
    try:
        with io.open(fd, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(json.dumps(data, indent=2, ensure_ascii=False) + '\n')
        os.replace(tmp, REVIEWS)
    except BaseException:
        # A temp file left behind is picked up by nothing and sits in docs/ for
        # ever, so it goes even when the write fails.
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def git(*args):
    """Run git and return its stdout as text, or raise CouldNotTell.

    ── ENCODING IS EXPLICIT, AND THIS IS A REAL DEFECT THAT WAS HERE (2026-09-15).
    # `text=True` alone decodes with the LOCALE default, which is cp1252 on this
    platform -- and this repo's diffs are full of box-drawing characters and
    em-dashes. Two clones hit this within an hour of each other and diagnosed the
    symptom DIFFERENTLY, which is worth keeping: one saw stdout come back
    TRUNCATED, the other saw the decode raise on the subprocess reader THREAD and
    leave `r.stdout` as None, which then crashed `.split('\\n')`. Both are the
    same cause and both are fixed by naming the codec.

    ── AND THE RETURN LINE FAILED OPEN, WHICH THE ENCODING FIX DID NOT CLOSE ──
    `return r.stdout if r.returncode == 0 else ''` collapses THREE outcomes into
    two: a real empty diff and a git command that FAILED both became `''`. An
    empty diff means NO TIER A RESOURCE WAS TOUCHED, which is a PASS. So any git
    failure produced a clean push, in a BLOCKING gate, on the check whose entire
    subject is somebody not being told (PR 1.11).

    That is the half worth the extra lines. The crash was the loud version of a
    failure mode that was otherwise completely silent, and fixing only the
    encoding converts a visible crash into an invisible pass.

    `errors='replace'` rather than `'strict'`: a lone undecodable byte must not
    take a blocking gate down, and a replacement character cannot create or hide
    a resource NAME, which is the only thing the caller looks for.
    """
    try:
        r = subprocess.run(['git'] + list(args), cwd=REPO, capture_output=True,
                           encoding='utf-8', errors='replace')
    except Exception as e:                      # noqa: BLE001 -- any launch failure
        raise CouldNotTell('could not run `git %s`: %r' % (' '.join(args), e))
    if r.returncode != 0:
        raise CouldNotTell('`git %s` exited %d: %s'
                           % (' '.join(args), r.returncode,
                              (r.stderr or '').strip()[:200]))
    if r.stdout is None:
        raise CouldNotTell('`git %s` produced no readable output' % ' '.join(args))
    return r.stdout


def _strip_code_noise(text, lang):
    """Comments and string literals blanked, so a predicate about CODE is not
    answered by PROSE. Written char-by-char rather than with regexes because the
    regex version of exactly this has already shipped a defect on this platform
    -- a literal backspace inside a heredoc'd `\\b` -- and because a string
    containing a comment marker breaks the regex version silently."""
    out = []
    i, n = 0, len(text)
    in_s = None          # the quote character currently open, or None
    while i < n:
        c = text[i]
        nxt = text[i + 1] if i + 1 < n else ''
        if in_s:
            if c == '\\':
                i += 2
                continue
            if c == in_s:
                in_s = None
            out.append(' ')
            i += 1
            continue
        if lang == 'js' and c == '/' and nxt == '*':
            j = text.find('*/', i + 2)
            i = n if j == -1 else j + 2
            continue
        if lang == 'js' and c == '/' and nxt == '/':
            j = text.find('\n', i)
            i = n if j == -1 else j
            continue
        if lang == 'py' and c == '#':
            j = text.find('\n', i)
            i = n if j == -1 else j
            continue
        if c in ('"', "'", '`'):
            in_s = c
            out.append(' ')
            i += 1
            continue
        out.append(c)
        i += 1
    return ''.join(out)


def is_report_only_artefact(path, content):
    """Is this a REVIEW ARTEFACT rather than code that serves a resource?

    ── WHY THIS PREDICATE EXISTS (2026-09-15) ──────────────────────────────
    Second recorded false positive of the same shape. The first was a WORKLOG
    (`SAIRN-ACTIVE-WORK-fourth.md`), fixed by excluding markdown. The second was
    `tests/dnt_rollup_review_probe.js` -- an independent review of somebody
    else's Tier A module, report-only by design, which the gate refused because
    a review of dnt_rollup necessarily NAMES dnt_rollup.

    A review artefact that serves nothing cannot be reviewed for correctness;
    there is no behaviour in it to review. Refusing it does not protect
    anything, and the failure is self-perpetuating: the gate blocks the very
    artefact that discharges the obligation it is asking for.

    ── WHY THIS IS NOT "EXCLUDE tests/" ────────────────────────────────────
    That would be the dangerous direction and it is worth being explicit. A
    test is often the ONLY thing pinning a Tier A behaviour, and weakening one
    is exactly the blind-spot case the review rule exists for. Excluding
    `tests/` wholesale would let a session delete assertions from a Tier A suite
    and push it as clean.

    ── THE PREDICATE, AND WHY IT IS THIS ONE ───────────────────────────────
    A file that CANNOT FAIL cannot be a guard, so changing it cannot weaken
    one. Three conditions, all required:

      1. it lives under `tests/` -- not beside a handler in `api/`;
      2. with comments and strings stripped, it makes NO assertion;
      3. with comments and strings stripped, every exit it takes is the literal
         0 -- so no input can make it report a failure.

    Condition 3 is the load-bearing one and it is deliberately strict.
    `tests/failsafe/countersign_coverage_probe.py` is report-only in intent but
    ends `sys.exit(main())`, whose value is not visibly constant -- so it is NOT
    excluded by this and would still raise an obligation. That is the safe
    direction, it is a known consequence rather than an oversight, and the fix
    if it ever matters is for that file to exit a literal.

    THE EXCLUSION SHRINKS THE RULE RATHER THAN GROWING A LIST, which this
    file's own header warns about: one predicate about what a file IS, not a
    filename somebody has to remember to add.
    """
    p = path.replace('\\', '/')
    if not p.startswith('tests/'):
        return False
    lang = 'py' if p.endswith('.py') else ('js' if p.endswith('.js') else None)
    if lang is None:
        return False
    code = _strip_code_noise(content, lang)
    # 2. no assertion of any kind.
    if re.search(r'(?<![A-Za-z0-9_])assert(?![A-Za-z0-9_])', code):
        return False
    # 3. every exit is a literal zero, and there is at least one -- a file with
    #    no exit at all is not evidence of anything and is left to the gate.
    exits = re.findall(r'(?:process|sys)\s*\.\s*exit\s*\(([^)]*)\)', code)
    if not exits:
        return False
    return all(a.strip() == '0' for a in exits)


# A string literal whose content reads as PROSE rather than as a token: it has
# at least three whitespace-separated words. `'sb_ts'`,
# `'sb_ts?license_hash=eq.'` and `'ts_id'` are tokens; "Storage full -- clear
# old quotes and retry." is a sentence.
# FIXED 2026-09-17: the body excluded EVERY quote character, not just the
# delimiter, so a prose string containing the other one never matched at all --
# and the commonest prose in this repo is a possessive or a contraction.
#
#     "the plan quotes the matrix's own numerator"
#
# is nine words of English in a comment. The apostrophe in `matrix's` is not in
# `[^'"`...]`, so the `"`-delimited match could never span it, nothing was
# blanked, and the gate read the word `quotes` -- a Tier A resource name -- as
# a Tier A touch in a test file. That is the THIRD recorded false positive of
# this shape and the first one the prose rule was already meant to cover: the
# docstring below cites "clear old quotes and retry." as the case it handles,
# and it does, right up until somebody writes "don't".
#
# `(?!\1)` EXCLUDES ONLY THE DELIMITER, which is the whole widening. It does
# not change what counts as prose -- that is still three or more whitespace-
# separated words, decided in _blank() -- and it does not touch the true
# positive this rule was narrowed for: `'sb_ts'` is one word either way.
_PROSE = re.compile(r'''(['"`])((?:(?!\1)[^\\\n]|\\.)*?)\1''')


def strip_diff_noise(line):
    """One diff line with comments and PROSE string bodies blanked.

    ── WHY NOT SIMPLY STRIP EVERY STRING (2026-09-16) ──────────────────────
    Because on this platform the resource name in real serving code IS a string
    literal. `api/sd-data.js` line 9838 is:

        if (resource === 'sb_ts' && action === 'write') {

    and that is the gate's most important true positive, not an edge case. A
    blanket string-strip would make the gate blind to exactly the change it
    exists to catch, and the gate would go quiet rather than noisy -- which is
    the worse of the two failures and the harder one to notice.

    So the rule is narrower and is about SHAPE, not about quoting:

      * A string body is blanked only when it reads as a SENTENCE -- three or
        more whitespace-separated words. A handler never references a table
        from inside a sentence; a checker's fixture and a user-facing message
        almost always do.

    ── COMMENTS ARE STILL COUNTED, AND THAT IS NOT AN OVERSIGHT ────────────
    The first version of this stripped comment bodies too. It is the obvious
    move and it REVERSES A STATED DECISION of this file's own header --
    "Comments count as naming a resource, deliberately: a hunk that discusses
    sc_claims was edited by somebody thinking about sc_claims." That decision
    is defensible and it is not mine to overturn from inside a change whose
    purpose is fixing false positives I personally hit.

    It was also caught rather than argued: stripping comments made
    tests/run_tier_a_review_gate_probe.py go red on
    `a REAL Tier A touch is still exit 1`, whose fixture is a comment line --
    the probe encoding the design decision exactly as intended.

    Left for whoever owns this gate: whether a comment in a CHECKER should
    count the way a comment in a handler does. Both false positives that
    survive today are checkers.

    WHAT THIS DOES NOT FIX, stated rather than left to be discovered: a
    checker's fixture that contains the BARE token, e.g.
    `FIXTURE_TIERS = {'dnt_payments': 'A'}` in tools/suite_control_triage.py.
    That is character-for-character what a handler writes, so no amount of
    string analysis can separate them -- the difference is what the FILE is,
    not what the token looks like. Naming it here so the next reader does not
    re-derive the same dead end.
    """
    body = line[1:] if line[:1] in ('+', '-', ' ') else line

    def _blank(m):
        inner = m.group(2)
        return m.group(1) + (' ' * len(inner) if len(inner.split()) >= 3
                             else inner) + m.group(1)

    return _PROSE.sub(_blank, body)


def touched_tier_a(diff_text, resources):
    """resource -> [files whose CHANGED HUNKS name it].

    Walks a unified diff and attributes every hunk line to the file its header
    named. Only hunk bodies are scanned -- the rest of the file is not part of
    this change, and reading it is what made the first version of this report
    78 resources for a one-line edit to api/sd-data.js.
    """
    hits = {}
    cur = None
    skip = False
    for line in diff_text.split('\n'):
        if line.startswith('+++ '):
            path = line[4:].strip()
            if path == '/dev/null':
                cur, skip = None, True
                continue
            cur = (path[2:] if path[:2] in ('a/', 'b/') else path).replace('\\', '/')
            # docs/ and sql/ are excluded by design: a document or a migration
            # naming a resource is not code serving it, and CRITICALITY-TIERS.md
            # names every Tier A resource by definition, so including docs/ would
            # make every push a Tier A push and the gate would mean nothing.
            #
            # ── AND ANY .md ANYWHERE, ADDED 2026-09-15 ──────────────────────
            # This gate refused a push whose only Tier-A-naming file was
            # `SAIRN-ACTIVE-WORK-fourth.md` -- a WORKLOG, describing dnt_rollup
            # and dnt_patients in prose. The reasoning three lines above already
            # covers that case exactly: a document naming a resource is not code
            # serving it. It was missed only because the rule was keyed on the
            # `docs/` PREFIX rather than on what the file IS, and every session's
            # worklog lives at the repo root by convention.
            #
            # THIS SHRINKS THE RULE RATHER THAN GROWING THE LIST, which matters
            # because this file's own header warns that "a growing exclusion list
            # is how a gate stops covering anything". One principled predicate --
            # markdown is prose, never a request handler -- replaces what would
            # otherwise be four root-level filenames plus the next one somebody
            # adds. It cannot under-cover: no `.md` file has ever served a
            # resource at runtime on this platform.
            # ── AND A REPORT-ONLY REVIEW ARTEFACT, ADDED 2026-09-15 ────────
            # Second false positive of this shape, after the worklog above.
            # `tests/dnt_rollup_review_probe.js` is an independent review of
            # somebody else's Tier A module and was refused because a review of
            # dnt_rollup necessarily names dnt_rollup. See
            # is_report_only_artefact() for the predicate and, more importantly,
            # for why this is NOT "exclude tests/", which would let a session
            # delete assertions from a Tier A suite and push it as clean.
            #
            # READ FROM THE WORKING TREE, not from the diff: the question is
            # what the file IS after this change, and the diff carries only the
            # hunks. A file deleted by this change is not on disk and is not
            # excluded, which is correct -- deleting a guard is a change worth
            # reviewing.
            # ── AND A CLAIM FILE, ADDED 2026-09-16 ─────────────────────────
            # THIRD false positive of this exact shape. The gate refused a push
            # whose only Tier-A-naming file was `.claude/claims/cody.json` -- the
            # coordination record written by `tools/sairn_claim.py`, containing
            # the TASK STRING a session typed. Claiming work on `sv_controlled`
            # necessarily names `sv_controlled`.
            #
            # It is the worklog case again with a different extension: a record
            # of INTENT is not code serving a resource. `.claude/claims/` is
            # written only by the claim tool, is never required by any handler,
            # and naming it here is narrower than excluding `.claude/` -- which
            # holds settings and hooks that genuinely can change behaviour.
            #
            # THE PATTERN IS WORTH NAMING NOW THAT IT IS THREE: every false
            # positive this gate has had is a file whose JOB is to TALK ABOUT
            # Tier A work -- a worklog, a review probe, a claim. The gate asks
            # "does this hunk name a Tier A resource", and the one category that
            # always names one without serving it is documentation OF the work.
            # A fourth instance should be treated as evidence the predicate
            # wants inverting -- allow-list the files that can SERVE a resource
            # (api/, the app HTML) rather than deny-listing the ones that
            # describe it.
            skip = skip_reason(cur) is not None
            if not skip and cur.replace('\\', '/').startswith('tests/'):
                try:
                    body = io.open(os.path.join(REPO, cur), encoding='utf-8',
                                   errors='replace').read()
                except OSError:
                    body = None
                if body is not None and is_report_only_artefact(cur, body):
                    skip = True
            continue
        if cur is None or skip:
            continue
        if line.startswith('diff --git') or line.startswith('--- '):
            continue
        if not (line[:1] in ('+', '-', ' ') or line.startswith('@@')):
            continue
        # ── CHANGED LINES ONLY, AND I ARGUED THE OPPOSITE (2026-09-15) ───────
        # This counted a resource named in a hunk's CONTEXT as strongly as one
        # on an added or removed line, on my own argument that "an edit three
        # lines from law_trusttx is an edit about law_trusttx".
        #
        # MEASURED AGAINST EVERY REAL CASE THE GATE HAS SEEN, and the argument
        # does not survive it:
        #
        #   item 97 soft-delete        TRUE   context 8   changed 8
        #   sc_denial_events gate      TRUE   context 7   changed 7
        #   358-site decode sweep      FALSE  context 1   changed 0
        #   report-only artefact fix   FALSE  context 0   changed 0
        #
        # CONTEXT ADDED NOTHING TO EITHER TRUE POSITIVE and produced the only
        # remaining false one -- `rf_certifications`, sitting three lines from a
        # mechanical one-argument edit in a probe. A platform-wide sweep touches
        # a line in 137 files and therefore produces context lines everywhere,
        # which is how a gate that blocks on context becomes a gate people
        # override.
        #
        # THE INFORMATION IS NOT THROWN AWAY. A context-only name is collected
        # separately and REPORTED, never blocking -- see context_only_tier_a().
        # Demoting a signal is not the same as deleting it.
        if line[:1] not in ('+', '-'):
            continue
        # COMMENTS AND PROSE STRINGS BLANKED FIRST. Four false positives in two
        # days came from a resource named in text rather than in code -- a
        # worklog, a review probe, and two checkers whose fixtures must contain
        # real resource names to be worth anything. See strip_diff_noise() for
        # why this is not a blanket string-strip.
        scanned = strip_diff_noise(line)
        for name in resources:
            # Word-bounded. `sc_ar` must not match `sc_archive`, and this
            # platform has already been bitten once by a substring search --
            # `esign` matching 47 occurrences of `design`.
            if re.search(r'(?<![a-z0-9_])' + re.escape(name) + r'(?![a-z0-9_])', scanned):
                fs = hits.setdefault(name, [])
                if cur not in fs:
                    fs.append(cur)
    return hits


def context_only_tier_a(diff_text, resources):
    """Names that appear ONLY in hunk context, never on a changed line.

    Reported and never blocking. Kept because the weaker signal is still worth a
    human seeing -- a change that edits around a Tier A resource without
    touching its name may still be about it -- but four-for-four, every real
    case where this fired alone was a false positive.
    """
    everything = _scan(diff_text, resources, changed_only=False)
    changed = touched_tier_a(diff_text, resources)
    return {k: v for k, v in everything.items() if k not in changed}


def _scan(diff_text, resources, changed_only=True):
    """The context-inclusive walk, kept for context_only_tier_a() to diff
    against. Deliberately a thin duplicate of the loop above rather than a flag
    threaded through it: the blocking path must not gain a parameter that could
    be passed the wrong way and quietly restore the behaviour this removed."""
    hits, cur, skip = {}, None, False
    for line in diff_text.split('\n'):
        if line.startswith('+++ '):
            path = line[4:].strip()
            if path == '/dev/null':
                cur, skip = None, True
                continue
            cur = (path[2:] if path[:2] in ('a/', 'b/') else path).replace('\\', '/')
            skip = skip_reason(cur) is not None
            continue
        if cur is None or skip:
            continue
        if line.startswith('diff --git') or line.startswith('--- '):
            continue
        if not (line[:1] in ('+', '-', ' ') or line.startswith('@@')):
            continue
        if changed_only and line[:1] not in ('+', '-'):
            continue
        for name in resources:
            if re.search(r'(?<![a-z0-9_])' + re.escape(name) + r'(?![a-z0-9_])', line):
                hits.setdefault(name, []).append(cur)
    return hits


def working_diff():
    """Everything not yet in HEAD, staged or not. -U3 rather than -U0 because a
    resource name three lines from an edit is what the edit was about."""
    return git('diff', '-U3', 'HEAD') + '\n' + git('diff', '-U3', '--cached', 'HEAD')


def range_diff(base, tip):
    return git('diff', '-U3', base, tip)


def open_records(data, session=None):
    out = []
    for r in data['records']:
        if r.get('status') != 'open':
            continue
        if session is not None and r.get('author_session') != session:
            continue
        out.append(r)
    return out


# ── THE DEADLINE, AND WHY IT REPORTS RATHER THAN DENIES (2026-09-16) ────────
# Michael's decision: an obligation nobody discharges within 24 hours is
# escalated. Measured before choosing the escalation: 27 open, and SEVEN are
# already past 24 hours -- 2 cc, 2 cody, 2 fourth, 1 hank. So the deny variant
# (refuse a push by the AUTHOR of an overdue obligation, which is the targeted
# version that does not stop anybody else working) would halt all four sessions
# the moment it shipped.
#
# TURNING IT ON AT SEVEN-ALREADY-OVERDUE IS A DIFFERENT DECISION FROM TURNING
# IT ON AT ZERO, and it is not one a tool should take on its own at the end of
# a long night. So this REPORTS, loudly, on every push and from --list, which
# exits non-zero so a human runner sees it -- and the deny is one constant away
# and named here so the choice is visible rather than forgotten.
OVERDUE_HOURS = 24
DENY_ON_OWN_OVERDUE = False      # flip with Michael, once the seven are cleared


# ── OWNERSHIP: AN OBLIGATION IS ASSIGNED WHEN IT IS OPENED (2026-09-21) ──────
# Michael's direction, after FOUR duplicate reviews in one day. Two sessions
# discharged the same obligation within minutes on four separate records, and
# every time the collision was invisible until a git rebase surfaced it.
#
# THE RACE NEEDED NO CONCURRENCY, which is why detecting it was never going to
# work. Driven against a throwaway copy of the register before this change:
# `fourth` discharged a record, then `cody` discharged the same record, and the
# second write replaced the first's reviewer_session AND its verdict outright --
# `fourth verdict survives: False`. Nothing in the gate keyed on who the
# obligation belonged to, so the LATER writer always won regardless of timing.
# The four collisions today were saved only because both sessions committed and
# one hit a conflict; a session that discharged, committed and pushed while the
# other was still writing would have destroyed a verdict with nothing to notice.
#
# THREE WEAKER FIXES WERE TRIED FIRST AND ALL THREE FAILED, which is the case
# for doing it here rather than around it:
#   * sairn_claim.py -- compares WORDS, and an obligation has no name, so two
#     correct descriptions of one record share none. It answered CLEAR every
#     time.
#   * oldest-first by convention -- both sessions followed it, so both picked
#     the same record.
#   * announcing the specific record in the live status registry before starting
#     -- tried on the fourth collision; the other session took it 2.5 minutes
#     later anyway. An announcement only helps if the other session re-reads
#     after choosing its next item, and there is no reason it would.
#
# SO THE STAMP GOES ON AT CREATION, NOT AT CLAIM TIME. An obligation carries a
# reviewer_owner from the moment --open writes it, and --discharge refuses
# anybody else. That is an IDENTITY CHECK rather than a lock, so it has no
# window: the second session is refused whether it arrives a second later or a
# day later.
#
# WHO IS ELIGIBLE IS DERIVED, NEVER HARDCODED. CLAUDE.md is explicit that the
# clone list has been wrong in this repository before -- it named four clones
# for weeks after a fifth existed -- so the roster is read from the claim files
# that exist on disk, one per clone, which is the registry that document points
# at. It FAILS CLOSED: fewer than two names is COULD NOT TELL, and a record
# opened then is left UNOWNED with the reason in it rather than assigned to a
# guess.
#
# THE HOVER AUDITOR IS EXCLUDED BY ROLE AND THAT IS STRUCTURAL, not tidying.
# The auditor does not build; it adversarially checks what the four build
# agents built, on its own rotation, and docs/2026-09-15-hover-auditor-
# separation-enforcement.md plus two gates exist to keep that boundary.
# Handing it a build agent's review queue would erase the separation from the
# other side.
#
# A PREFIX, NOT A NAME (fixed 2026-09-24, H2 seq #205). This was the literal
# 'hover', and the auditor already runs as more than one instance -- the
# shared status registry lists `hover` AND `hover2` today. The day hover2
# created `.claude/claims/hover2.json` it would have silently entered the
# reviewer pool and started being ASSIGNED build-agent review obligations,
# with nothing anywhere saying the boundary had been crossed. The roster's
# own header says why hardcoded lists fail here ("named four clones for weeks
# after a fifth existed"); excluding one auditor by literal name was the same
# mistake one shelf over. Any session whose name is `hover` or starts with
# `hover` followed by a digit or separator is the auditor role.
HOVER_SESSION = 'hover'


def is_hover_session(name):
    """True for every instance of the auditor role: hover, hover2, hover-3...

    Deliberately NOT a bare startswith('hover'): a build agent legitimately
    named `hoverboard` (unlikely, but rosters grow) must not be silently
    excluded from review duty -- over-exclusion here starves the pool the
    same way over-inclusion poisons it.
    """
    return bool(re.match(r'^hover(\d|[-_]|$)', str(name or '')))
CLAIMS_DIR = os.path.join(REPO, '.claude', 'claims')
# How long an owner may sit on an obligation before anybody else may TAKE IT
# OVER. Deliberately longer than OVERDUE_HOURS: overdue means "somebody should
# be told", takeover means "the assignment itself has failed", and collapsing
# the two would let a busy owner lose an obligation to a race again.
OWNER_STALE_HOURS = 48


class NotOwner(Exception):
    """The caller is not this obligation's assigned reviewer."""


def eligible_reviewers():
    """Sessions that may be assigned a review, from the claim files on disk.

    Returns a sorted list, or None for COULD NOT TELL -- never a guess and never
    a hardcoded roster.
    """
    try:
        names = sorted(
            f[:-5] for f in os.listdir(CLAIMS_DIR)
            if f.endswith('.json') and re.match(r'^[a-z][a-z0-9_-]{1,31}\.json$', f))
    except OSError:
        return None
    names = [n for n in names if not is_hover_session(n)]
    # One name cannot review anything: the only candidate would be the author.
    return names if len(names) >= 2 else None


def assign_owner(author, data, roster=None):
    """Which session should review an obligation this author is opening.

    LEAST-LOADED, TIE-BROKEN ALPHABETICALLY. Deterministic on purpose -- this
    file may not use randomness (a random assignment cannot be re-derived when
    somebody asks why a record went where it did) and least-loaded self-levels
    as the queue moves, where round-robin on a counter would need state nobody
    would keep in sync.

    Returns (owner, note). `owner` is None when no assignment can be made, and
    then `note` says why in words a reader can act on.
    """
    roster = eligible_reviewers() if roster is None else roster
    if roster is None:
        return None, ('the eligible-reviewer roster could not be read from '
                      '.claude/claims/, so no owner was assigned and this record '
                      'is first-come. Fix the roster and re-assign by hand.')
    candidates = [n for n in roster if n != author]
    if not candidates:
        return None, ('%s is the only eligible session on this roster, so there '
                      'is nobody to assign -- an author may never review its own '
                      'obligation. This record is UNOWNED and first-come.' % author)
    load = dict((n, 0) for n in candidates)
    for r in data.get('records', []):
        if r.get('status') != 'open':
            continue
        o = r.get('reviewer_owner')
        if o in load:
            load[o] += 1
    best = min(candidates, key=lambda n: (load[n], n))
    return best, None


def owner_age_hours(rec):
    """Hours since the owner was assigned, or None if unusable -- the third
    state, and never counted as fresh."""
    try:
        t = time.strptime(rec.get('owner_assigned_at') or '', '%Y-%m-%dT%H:%M:%SZ')
    except (ValueError, TypeError):
        return None
    return (time.time() - calendar.timegm(t)) / 3600.0


def _age_hours(rec):
    """Hours since the obligation was opened, or None if the stamp is unusable.

    None is a THIRD ANSWER and is never counted as fresh: an obligation whose
    age cannot be read is exactly the one nobody is tracking.
    """
    try:
        t = time.strptime(rec.get('opened_at') or '', '%Y-%m-%dT%H:%M:%SZ')
    except (ValueError, TypeError):
        return None
    return (time.time() - calendar.timegm(t)) / 3600.0


def overdue_records(data, session=None):
    """[(record, age_hours_or_None)] past the deadline, oldest first."""
    out = []
    for r in open_records(data, session):
        age = _age_hours(r)
        if age is None or age > OVERDUE_HOURS:
            out.append((r, age))
    out.sort(key=lambda p: (p[1] is not None, p[1]), reverse=True)
    return out


def self_signed(data):
    """A record whose reviewer is its own author. The one claim the rule exists
    to refuse, and the only part of a review a machine can check."""
    bad = []
    for r in data['records']:
        rev = r.get('reviewer_session')
        if rev and rev == r.get('author_session'):
            bad.append(r)
    return bad


def check(diff_text, verbose=True):
    """Returns (exit_code, lines)."""
    lines = []
    try:
        resources = tier_a_resources()
        data = load_reviews()
        rules = coding_rules()
    except CouldNotTell as e:
        return 2, ['COULD NOT TELL -- this is NOT a pass:', '  ' + str(e)]

    # 1. SELF-SIGNED RECORDS. Checked first and on EVERY run, not only when the
    #    push touches Tier A code: a self-signed record already in the file is a
    #    finding whatever this particular push contains.
    bad = self_signed(data)
    if bad:
        lines.append('SELF-SIGNED REVIEW -- a session recorded itself as the reviewer '
                     'of its own change. That is the one claim this rule exists to refuse:')
        for r in bad:
            lines.append('  %s reviewed by %s  (%s)'
                         % (r.get('author_session'), r.get('reviewer_session'),
                            ', '.join(r.get('resources') or []) or 'no resources listed'))
        return 1, lines

    hits = touched_tier_a(diff_text, resources)
    # RAISED, NOT SWALLOWED: a rule whose anchor no longer matches is a
    # COULD NOT TELL for the whole run. Reporting it as "untouched" would let
    # the registry decay into silence one rule at a time, which is exactly the
    # stale-anchor failure this platform has now recorded six times.
    try:
        rule_hits = touched_rules(diff_text, rules)
    except CouldNotTell as e:
        return 2, ['COULD NOT TELL -- this is NOT a pass:',
                   '  a registered coding rule could not be located: ' + str(e),
                   '  Fix the anchor in docs/coding-rule-registry.json, or remove',
                   '  the rule deliberately. A rule the gate cannot find is a rule',
                   '  it would report as untouched forever.']
    # DEMOTED, NOT DELETED. A name that appears only in hunk CONTEXT used to
    # block; four-for-four it was a false positive and it added nothing to
    # either true one. It is still worth a human seeing, so it is said out loud
    # and never gates.
    ctx_only = context_only_tier_a(diff_text, resources)
    if not hits and not rule_hits:
        if verbose:
            lines.append('No file in this change names a Tier A resource on a '
                         'changed line, and no changed line falls inside a '
                         'registered coding rule. Nothing to record.')
            if ctx_only:
                lines.append('FYI, not blocking: %s appear(s) in hunk CONTEXT '
                             'only. If the change really is about one of them, '
                             'record it -- the gate cannot tell from context '
                             'alone and no longer pretends to.'
                             % ', '.join(sorted(ctx_only)))
        return 0, lines

    session = session_name()
    # ── COVERAGE IS PER RESOURCE, NOT PER CHANGE (hover #270, 2026-09-18) ────
    # This read:
    #
    #     covering = [r for r in open_records(data, session)
    #                 if set(hits) & set(r.get('resources') or [])]
    #     if covering: return 0
    #
    # An INTERSECTION, so ONE resource in common cleared the WHOLE change. A
    # session holding an open obligation on sc_claims could push a change
    # touching sc_claims AND dnt_patients and the gate said covered, with the
    # dnt_patients half unrecorded and invisible to every later reader.
    #
    # REPRODUCED BEFORE IT WAS CHANGED, and the sharpest part is that the gate
    # PRINTED THE EVIDENCE OF ITS OWN GAP: the pass message read
    # "Tier A code changed: dnt_patients, sc_claims" on the very run where it
    # cleared a push carrying one obligation for two resources.
    #
    # THE UNION ACROSS ALL OF THIS SESSION'S OPEN RECORDS, not "one record must
    # cover everything". A session may legitimately hold two obligations that
    # together cover one change, and requiring a single record to carry the
    # whole set would block honest work -- which is how a gate gets talked past.
    #
    # WHAT IS DELIBERATELY NOT CHANGED HERE: a record whose own text says "no
    # product code changed" still covers a later PRODUCT change to the same
    # resource. That is the kind axis, it is a separate decision about a
    # blocking gate, and folding it in would make one change do two things.
    mine = open_records(data, session)
    covered = set()
    covered_rules = set()
    for r in mine:
        covered |= set(r.get('resources') or [])
        covered_rules |= set(r.get('rules') or [])
    uncovered = sorted(set(hits) - covered)
    # PER RULE, FOR THE SAME REASON COVERAGE IS PER RESOURCE. An obligation
    # naming the KX threshold does not cover a change to the SWO element list
    # that happened to ride along in the same push.
    uncovered_rules = sorted(set(rule_hits) - covered_rules)
    if not uncovered and not uncovered_rules:
        if verbose:
            if hits:
                lines.append('Tier A code changed: %s' % ', '.join(sorted(hits)))
            if rule_hits:
                lines.append('Coding rules changed: %s' % ', '.join(sorted(rule_hits)))
            lines.append('EVERY resource and rule it touches has an OPEN obligation '
                         '(%s). Recording it is this session\'s job; discharging '
                         'it is somebody else\'s.' % session)
            for r in mine:
                shared = sorted((set(hits) & set(r.get('resources') or []))
                                | (set(rule_hits) & set(r.get('rules') or [])))
                if shared:
                    lines.append('  opened %s covers %s'
                                 % (r.get('opened_at', '?'), ', '.join(shared)))
        return 0, lines

    partial = sorted((set(hits) & covered) | (set(rule_hits) & covered_rules))
    if partial:
        lines.append('TIER A CODE CHANGED AND ONLY PART OF IT IS RECORDED.')
        lines.append('')
        lines.append('  already covered by an open obligation:  %s'
                     % ', '.join(partial))
        lines.append('  NOT covered, and this is what blocks:    %s'
                     % ', '.join(uncovered + uncovered_rules))
        lines.append('')
        lines.append('An obligation covers the RESOURCES IT NAMES, not every resource')
        lines.append('a later change happens to touch alongside them.')
        lines.append('')
    elif uncovered:
        lines.append('TIER A CODE CHANGED WITH NO RECORDED REVIEW OBLIGATION.')
        lines.append('')
    else:
        lines.append('A CODING RULE CHANGED WITH NO RECORDED REVIEW OBLIGATION.')
        lines.append('')
        lines.append('This half of the gate exists because the other half refused a')
        lines.append('real obligation on 2026-09-24 and was RIGHT to: a validator')
        lines.append('stores nothing, so changing one names no Tier A resource. A')
        lines.append('rule decides whether a claim is ADJUDICATED; a row decides what')
        lines.append('is REMEMBERED. docs/coding-rule-registry.json names the rules,')
        lines.append('and they are found by LINE RANGE rather than by name -- so a')
        lines.append('changed line inside the body counts even when it mentions')
        lines.append('nothing the gate could have grepped for.')
        lines.append('')
    for name in uncovered:
        lines.append('  %-22s %s' % (name, ', '.join(sorted(set(hits[name])))[:110]))
    for name in uncovered_rules:
        lines.append('  %-22s %s  [coding rule]'
                     % (name, ', '.join(sorted(set(rule_hits[name])))[:96]))
    lines.append('')
    lines.append('The standing rule is that a Tier A change is reviewed by a session')
    lines.append('OTHER than the one that wrote it -- the author shares the blind spot')
    lines.append('that produced the code. Until now that rule lived in prose on')
    lines.append('whichever open-work rows somebody remembered to annotate.')
    lines.append('')
    lines.append('THIS DOES NOT ASK YOU TO GET REVIEWED BEFORE PUSHING. It asks you to')
    lines.append('RECORD that the obligation exists, so the next session can see an')
    lines.append('unreviewed Tier A change instead of having to guess:')
    lines.append('')
    lines.append('    python tools/tier_a_review_gate.py --open "what you changed and why"')
    lines.append('')
    lines.append('Another session discharges it later; this gate refuses any record')
    lines.append('whose reviewer is its own author.')
    return 1, lines


# ── --body-file: THE SHELL IS WHERE THE TEXT DIES, NOT THIS TOOL ────────────
# Audited 2026-09-22 after several sessions landed corrupted verdict bodies.
# THIS TOOL WAS NEVER THE VULNERABILITY and the audit says so rather than
# implying it: every subprocess call here passes an ARGUMENT LIST with no
# `shell=`, so by the time a body reaches `argv[1]` no metacharacter in it can
# mean anything. There is no injection path inside this file to close.
#
# THE DAMAGE HAPPENS BEFORE argv EXISTS, in the caller's shell, and it was
# reproduced rather than assumed:
#
#   "the anchor is `echo SUBSTITUTED` in the file"
#       -> arrives as 'the anchor is SUBSTITUTED in the file', 37 bytes.
#          Twelve characters of the author's sentence are simply gone.
#
#   "$(cat <<EOF ... $(echo INJECTED) ... EOF)"     [UNQUOTED delimiter]
#       -> the substitution RUNS and its output is spliced into the body.
#
# Both shapes report success. The shell did what it was told, the tool stores
# what it was handed, and nobody re-reads a verdict they just wrote -- which is
# bug class 18 in `.claude/skills/sairn-code-scrubber/SKILL.md`, and the reason
# class 23 exists for commit messages.
#
# SO THE FIX IS TO REMOVE THE NEED FOR COMMAND SUBSTITUTION, not to sanitise
# anything. A path is a short argument with no metacharacters in it; the body
# never passes through a shell at all. `--body-file` is the same answer
# CLAUDE.md already gives for commit messages (`git commit -F <path>`) and for
# regexes, applied to the third place free text is typed on this platform.
#
# READ AS BYTES AND DECODED HERE, deliberately: a file written by one session
# and read by another is the seam where an encoding assumption becomes a
# corrupted verdict, and this platform has already paid for `cp1252` defaults
# 358 times in one sweep. An unreadable or empty file is COULD NOT TELL --
# never silently the empty string, which this gate would store as a review.
def body_from_file_or(argv, fallback):
    """Return the body from --body-file if given, else `fallback`."""
    if '--body-file' not in argv:
        return fallback
    i = argv.index('--body-file')
    if len(argv) <= i + 1:
        raise CouldNotTell('--body-file needs a path')
    path = argv[i + 1]
    if not os.path.isfile(path):
        raise CouldNotTell('--body-file %r does not exist. Nothing was '
                           'recorded -- an absent body is not an empty one.'
                           % path)
    try:
        with open(path, 'rb') as fh:
            raw = fh.read()
    except OSError as e:
        raise CouldNotTell('--body-file %r could not be read: %s' % (path, e))
    try:
        text = raw.decode('utf-8')
    except UnicodeDecodeError as e:
        raise CouldNotTell('--body-file %r is not UTF-8 (%s). Refusing rather '
                           'than storing a lossy decode.' % (path, e))
    if not text.strip():
        raise CouldNotTell('--body-file %r is empty. A record with no content '
                           'is a tick, not a review.' % path)
    return text.strip()


def cmd_open(why, rng=None):
    resources = tier_a_resources()
    rules = coding_rules()
    if rng:
        # ── RECORDING AN OBLIGATION FOR WORK ALREADY PUSHED (2026-09-16) ────
        # Without this there is no way to open an accurate record after the
        # fact, and that is not a hypothetical gap: the gate is satisfied
        # PER RESOURCE, so a push carrying a real product change to sb_po and
        # sb_recv went through on an OPEN obligation whose own text reads "NEW
        # NEGATIVE CONTROL, no product code changed". The change was recorded
        # by nobody. The honest repair needs a range, because by the time you
        # notice, the working diff and the unpushed range are both empty.
        #
        # This does NOT change what the gate blocks on, and deliberately so --
        # whether an obligation should be per-CHANGE rather than per-RESOURCE
        # is a decision about a blocking gate and belongs in its own change.
        left, _, right = rng.partition('..')
        if not left or not right:
            sys.stderr.write('--range takes A..B, e.g. origin/main~1..origin/main\n')
            return 1
        text = range_diff(left, right)
        if not text.strip():
            sys.stderr.write('That range has no diff, so there is nothing to '
                             'record about it. An empty range is not an '
                             'obligation with no resources -- it is a range '
                             'that names no change.\n')
            return 1
    else:
        text = working_diff()
        base = git('merge-base', 'origin/main', 'HEAD').strip()
        if base:
            # Unpushed commits count. The obligation is about the work being
            # SENT, not only about whatever happens to be uncommitted when
            # --open runs.
            text += '\n' + range_diff(base, 'HEAD')
    hits = touched_tier_a(text, resources)
    rule_hits = touched_rules(text, rules)
    if not hits and not rule_hits:
        sys.stderr.write('Nothing in this change names a Tier A resource, and no '
                         'changed line falls inside a registered coding rule, so '
                         'there is no obligation to record. If you believe there '
                         'is, say which resource or rule and why -- an entry '
                         'naming neither cannot be discharged by anybody.\n'
                         '\nIf it IS a coding or billing rule and the registry '
                         'does not know about it yet, that is the gap rather than '
                         'the answer: add it to docs/coding-rule-registry.json. '
                         'Seven shipped rules sat in exactly that position until '
                         '2026-09-24.\n')
        return 1
    data = load_reviews()
    author = session_name()
    owner, owner_note = assign_owner(author, data)
    rec = {
        'author_session': author,
        'opened_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'resources': sorted(hits),
        # ── ALWAYS PRESENT, EVEN WHEN EMPTY (2026-09-24) ───────────────────
        # A field that appears only when non-empty is a field every reader has
        # to remember might be absent, and `set(r.get('rules') or [])` in three
        # places is one missing `or []` away from a silent miss. Written on
        # every record so the shape is one shape.
        'rules': sorted(rule_hits),
        'files': sorted(set(list(f for fs in hits.values() for f in fs)
                            + list(f for fs in rule_hits.values() for f in fs))),
        'what': why,
        'status': 'open',
        # ── THE OWNER IS STAMPED NOW, NOT WHEN SOMEBODY CLAIMS IT ──────────
        # This is the whole point: first-come is what produced four duplicate
        # reviews in a day. See the OWNERSHIP block above OVERDUE_HOURS.
        'reviewer_owner': owner,
        'owner_assigned_at': (time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
                              if owner else None),
        'reviewer_session': None,
        'reviewed_at': None,
        'verdict': None,
    }
    if owner_note:
        rec['owner_note'] = owner_note
    data['records'].append(rec)
    save_reviews(data)
    subjects = rec['resources'] + ['%s [rule]' % r for r in rec['rules']]
    print('RECORDED -- %s owes an independent review on: %s'
          % (rec['author_session'], ', '.join(subjects)))
    if owner:
        print('ASSIGNED TO %s, now, rather than left first-come. Only %s can '
              'discharge it (or anybody after %dh, with --takeover).'
              % (owner, owner, OWNER_STALE_HOURS))
    else:
        print('UNOWNED and first-come: %s' % owner_note)
    print('Commit docs/tier-a-reviews.json with the change it covers.')
    return 0


def cmd_list():
    try:
        data = load_reviews()
    except CouldNotTell as e:
        sys.stderr.write(str(e) + '\n')
        return 2
    rows = open_records(data)
    if not rows:
        print('No open Tier A review obligations.')
        return 0
    late = dict((id(r), a) for r, a in overdue_records(data))
    print('%d open Tier A review obligation(s):' % len(rows))
    for r in rows:
        age = late.get(id(r))
        mark = ''
        if id(r) in late:
            mark = ('   ** OVERDUE, age UNREADABLE **' if age is None
                    else '   ** OVERDUE %.0fh **' % age)
        print('  %-8s %s  %s%s' % (r.get('author_session'), r.get('opened_at'),
                                   ', '.join((r.get('resources') or [])
                                             + ['%s [rule]' % x
                                                for x in (r.get('rules') or [])]),
                                   mark))
        # ── WHOSE IT IS, ON THE LINE PEOPLE ACTUALLY READ ──────────────────
        # --list is where a session decides what to pick up. Printing the owner
        # anywhere else would leave that decision on first-come, which is the
        # thing this stamp exists to remove.
        owner = r.get('reviewer_owner')
        if owner:
            held = owner_age_hours(r)
            print('           ASSIGNED TO %s%s' % (
                owner,
                ('  (held %.0fh -- past %dh, anybody may --takeover)'
                 % (held, OWNER_STALE_HOURS)) if held is not None and held > OWNER_STALE_HOURS
                else ('  (held %.0fh)' % held) if held is not None
                else '  (assignment time UNREADABLE -- no takeover possible)'))
        else:
            print('           UNOWNED -- first-come. %s'
                  % (r.get('owner_note')
                     or 'opened before ownership was stamped; whoever reviews it '
                        'should say so in the live status registry first.'))
        print('           %s' % (r.get('what') or '')[:110])
    if late:
        print('')
        print('%d of them are past the %dh deadline. An obligation nobody closes'
              % (len(late), OVERDUE_HOURS))
        print('is a queue people stop reading, which is the state this register was')
        print('built to leave. Discharge them, or run --auto-discharge to close the')
        print('ones a defect-register record already covers.')
        return 1
    return 0


# ── --validate: IS THE FILE SOUND? NOT "IS THE QUEUE CLEAN?" ───────────────
# Added 2026-09-23. `--list` returns 1 when any obligation is past the 24h
# deadline, and that is correct for a human reading the queue -- it is how a
# session notices work nobody has closed.
#
# IT IS WRONG AS A MERGE VALIDATOR, AND IT WAS BEING USED AS ONE.
# docs/tier-a-reviews.json declares `["tools/tier_a_review_gate.py", "--list"]`
# in its merge_policy, and tools/sairn_rebase_resolve.py refuses any merge whose
# validator exits non-zero, printing "merged cleanly, and then its own validator
# rejected the result". So a perfectly correct union-by-identity merge of this
# ledger was REFUSED whenever anybody, anywhere, held an obligation older than a
# day -- which is most of the time, and is the state the deadline exists to make
# VISIBLE rather than a reason to block a rebase.
#
# TWO DIFFERENT QUESTIONS WERE SHARING ONE EXIT CODE:
#   "is this file structurally sound"      -- what a merge validator needs
#   "does the queue contain overdue work"  -- what a person needs
#
# Fixing it by changing --list's exit code would have been the wrong direction:
# that code is the only mechanical signal that an obligation is being ignored,
# and silencing it to unblock a rebase trades a real alarm for a convenience.
# So a SECOND mode is added and the merge policy points at it.
#
# IT EXITS 0 OR 2 AND NEVER 1, deliberately. A validator with three outcomes
# invites exactly the conflation this replaces. 2 is COULD NOT RUN -- unreadable,
# unparseable, or the wrong shape -- and 0 is sound.
# Every status any writer in this file can set. _discharge() is the only
# function that assigns one, and it has exactly two callers: cmd_discharge
# ('reviewed') and cmd_auto_discharge ('reviewed-by-record'). 'open' is
# written at --open. Derived by reading those three sites rather than by
# sampling the ledger, so a status nothing writes cannot creep in here.
STATUSES = ('open', 'reviewed', 'reviewed-by-record')


# ── --rules: IS EVERY REGISTERED RULE STILL FINDABLE? ──────────────────────
# The registry's own validator, and the answer this half depends on. Every
# other question here -- did this change touch a rule, is it covered -- assumes
# each anchor resolves to exactly one range. When one stops resolving, the gate
# already refuses with COULD NOT TELL on any push touching that FILE; this is
# how somebody asks the question without needing a push to ask it with.
#
# EXIT 2 AND NOT 1 WHEN AN ANCHOR IS GONE. A rule that cannot be located is a
# could-not-tell about that rule, not a finding about the code -- the same
# three-state discipline the rest of this file holds.
def cmd_rules():
    try:
        rules = coding_rules()
    except CouldNotTell as e:
        sys.stderr.write('COULD NOT TELL: %s\n' % e)
        return 2
    print('%d registered coding rule(s) in docs/coding-rule-registry.json\n'
          % len(rules))
    # ── THE REVIEW BACKLOG, WHICH IS THE POINT OF REGISTERING THEM ─────────
    # Reading the ledger for which rules have ever been the subject of an
    # obligation, and whether it was discharged. A registry that only answers
    # "can I find this rule" would be a lookup table; what somebody actually
    # needs to know is which shipped rules nobody outside their author has ever
    # read. On the day this was built that was ALL of them.
    #
    # NEVER-RECORDED IS NOT A FINDING AND IS NOT PRINTED AS ONE. The gate opens
    # obligations for CHANGES, so a rule that has not been touched since the
    # registry existed has no obligation and should not have one invented. It
    # is a coverage figure, and it is reported as a figure.
    try:
        data = load_reviews()
        records = data.get('records') or []
    except CouldNotTell:
        records = None
    seen, reviewed = {}, {}
    if records is not None:
        for rec in records:
            for name in (rec.get('rules') or []):
                seen[name] = seen.get(name, 0) + 1
                if rec.get('status') in ('reviewed', 'reviewed-by-record'):
                    reviewed[name] = reviewed.get(name, 0) + 1
    bad = 0
    for r in sorted(rules, key=lambda x: (x['app'], x['rule'])):
        try:
            text = io.open(os.path.join(REPO, r['file']), encoding='utf-8').read()
            lo, hi = _anchor_range(text, r['anchor'])
            where = '%s:%d-%d  (%d lines)' % (r['file'], lo, hi, hi - lo + 1)
        except (OSError, CouldNotTell) as e:
            where = 'UNLOCATABLE -- %s' % e
            bad += 1
        if records is None:
            mark = '[ledger unreadable]'
        elif reviewed.get(r['rule']):
            mark = '[reviewed %d]' % reviewed[r['rule']]
        elif seen.get(r['rule']):
            mark = '[obligation OPEN]'
        else:
            mark = '[never recorded]'
        print('  %-34s %-18s %s' % (r['rule'], mark, where))
        print('      %s' % (r.get('decides') or '(no `decides` recorded)'))
    if bad:
        print('\n%d rule(s) COULD NOT BE LOCATED. Every push touching their file '
              'will refuse with COULD NOT TELL until the anchor is repaired or '
              'the rule is removed deliberately. An unlocatable rule reads as '
              'untouched forever, which is the failure this registry exists to '
              'prevent.' % bad)
        return 2
    never = [r['rule'] for r in rules if not seen.get(r['rule'])]
    print('\nEvery anchor resolves to exactly one range. That is the property '
          'the\nwhole rule half depends on -- it says nothing about whether any '
          'rule is\nCORRECT, which is what the review obligation is for.')
    if records is None:
        print('\nTHE LEDGER COULD NOT BE READ, so the review column above says '
              'nothing.\nThat is a could-not-tell about coverage, not a clean '
              'backlog.')
    elif never:
        print('\n%d of %d registered rule(s) have NEVER been the subject of a '
              'review\nobligation: %s.\n'
              'That is a coverage figure and not a finding -- this gate opens '
              'an\nobligation for a CHANGE, so a rule nobody has touched since '
              'the registry\nexisted correctly has none. It is printed because '
              'the reason the registry\nwas built is that these rules had no '
              'channel at all, and "no channel" and\n"reviewed" look identical '
              'from the outside.'
              % (len(never), len(rules), ', '.join(sorted(never))))
    return 0


def cmd_validate():
    try:
        data = load_reviews()
    except CouldNotTell as e:
        sys.stderr.write(str(e) + '\n')
        return 2
    records = data.get('records')
    bad = []
    seen = set()
    for i, r in enumerate(records):
        if not isinstance(r, dict):
            bad.append('record %d is not an object' % i)
            continue
        # The identity the merge policy unions on. A record missing either half
        # cannot be de-duplicated, so two clones would silently keep both copies
        # -- which is the failure a union-by-identity merge exists to prevent,
        # arriving through the ledger instead of through the merge.
        key = (r.get('author_session'), r.get('opened_at'))
        if not key[0] or not key[1]:
            bad.append('record %d has no author_session/opened_at -- the merge '
                       'identity this ledger unions on' % i)
            continue
        if key in seen:
            bad.append('two records share the identity %r, so a union-by-identity '
                       'merge cannot tell them apart' % (key,))
        seen.add(key)
        # THE VOCABULARY IS READ OUT OF THE WRITERS, NOT GUESSED. The first
        # version of this check typed ('open', 'discharged') and refused 109 of
        # 127 real records on their first run -- the actual closed status is
        # `reviewed`, and --auto-discharge writes a third, `reviewed-by-record`,
        # which is deliberately weaker and says so in its own verdict text. A
        # validator that refuses the file it is meant to certify is worse than
        # none; driving it against the real ledger is what caught it.
        st = r.get('status')
        if st not in STATUSES:
            bad.append('record %r has status %r, which is outside %s'
                       % (key[1], st, (STATUSES,)))
    if bad:
        sys.stderr.write('docs/tier-a-reviews.json is NOT sound:' + '\n')
        for b in bad:
            sys.stderr.write('  ' + b + '\n')
        return 2
    print('tier-a-reviews.json: %d record(s), identities unique, statuses in '
          'vocabulary.' % len(records))
    print('    This says the FILE is sound. It says nothing about whether the '
          'queue is clear -- run --list for that, which exits 1 on an overdue '
          'obligation and is the reason this mode exists separately.')
    return 0


# ── AUTO-DISCHARGE: CAPTURE THE REVIEW THAT ALREADY HAPPENED ────────────────
# Michael's decision, and the case for it is measured: 27 obligations open, and
# at least one of them had SEVEN real defects found and fixed against it
# informally -- by another session, in its own report -- and never logged here.
# The review happened. The register could not see it. A queue that only grows
# because the closing step is manual is a queue people stop reading.
#
# THE EVIDENCE IT ACCEPTS IS NARROW ON PURPOSE. A defect-register record whose
# `detection_method` is literally `independent-review`, whose files OVERLAP the
# obligation's, and which was recorded AFTER the obligation was opened. All
# three, or no match.
#
# AND THE THING IT CANNOT DO, WHICH MATTERS MORE THAN WHAT IT CAN:
# THE DEFECT REGISTER CARRIES NO SESSION ATTRIBUTION. There is no author field
# on a record and all five roles share one git identity, so this CANNOT prove
# the reviewer was not the author -- the one claim this whole gate exists to
# refuse. What it can do is trust a recorded claim: `independent-review` means
# that, in the register's own vocabulary, and somebody chose it.
#
# SO AN AUTO-CLOSE IS A WEAKER CLOSE, AND IT SAYS SO IN THE RECORD. The status
# is `reviewed-by-record`, not `reviewed`, and the reviewer_session names the
# mechanism rather than a person. A reader can tell the two apart at a glance,
# and `--list` counts them separately. Folding them into one status would buy a
# tidier number by losing the only distinction that matters.
AUTO_METHOD = 'independent-review'


def _register_records():
    """[(commit, date, files, summary)] for independent-review records, or None.

    None if the register cannot be read, which is a refusal rather than an empty
    list: 'no evidence exists' and 'I could not look' would otherwise close the
    same obligations.
    """
    try:
        d = json.load(io.open(DEFECT_REGISTER, encoding='utf-8'))
    except (OSError, ValueError):
        return None
    recs = d['records'] if isinstance(d, dict) and 'records' in d else d
    if not isinstance(recs, list):
        return None
    out = []
    for r in recs:
        if (r.get('detection_method') or '') != AUTO_METHOD:
            continue
        # The record's own words, for the resource test below. A register record
        # has no resource LIST -- only an app, a summary and a subject -- so the
        # resource has to be looked for in the text, which is the same way this
        # gate decides a diff "touches" one.
        text = ' '.join([str(r.get('summary') or ''), str(r.get('subject') or ''),
                         str(r.get('app') or '')])
        out.append((str(r.get('commit') or ''), str(r.get('date') or ''),
                    set(r.get('files') or []), str(r.get('summary') or ''), text))
    return out


def cmd_auto_discharge(write=False):
    try:
        data = load_reviews()
    except CouldNotTell as e:
        sys.stderr.write(str(e) + '\n')
        return 2
    evidence = _register_records()
    if evidence is None:
        print('COULD NOT TELL: the defect register could not be read, so whether')
        print('an independent review already exists is UNKNOWN. Nothing was')
        print('closed -- "no evidence" and "I could not look" are not the same')
        print('answer and must not close the same obligations.')
        return 2

    matched, suggested = [], []
    for rec in open_records(data):
        files = set(rec.get('files') or [])
        opened = (rec.get('opened_at') or '')[:10]
        # ── A FILE OVERLAP IS NOT A REVIEW OF THE SAME QUESTION ──────────
        # The first version matched on files and the date alone, and the
        # DRY RUN is what caught it: an obligation on sb_po/sb_recv paired with
        # evidence about law_trusttx, because both touched api/sd-data.js --
        # the file that names every resource on the platform, and the very
        # reason this gate reads HUNKS rather than file content. Six matches
        # became three once the resource had to be named too.
        #
        # So the record must also NAME one of the obligation's resources in its
        # own words. Narrower than file overlap and looser than proof, which is
        # the honest place for an auto-close to sit.
        res = [x for x in (rec.get('resources') or []) if x]
        hits = [e for e in evidence
                if (e[2] & files) and e[1] >= opened
                and any(x in e[4] for x in res)]
        if not hits:
            continue
        # ── AND EVEN RESOURCE + FILE + DATE IS NOT "REVIEWED THE SAME
        # ── QUESTION". THE DRY RUN CAUGHT THIS TOO, ON THE ONE SURVIVOR.
        # Fourth's obligation asks for review of IOLTA reconciliation
        # ARITHMETIC -- can allocation_vs_ledger genuinely disagree, the
        # on-or-before statement-date boundary, the undated-transaction case,
        # the single Math.round at the cents boundary. The matching record is
        # about a MISSING SESSION GATE on law_trusttx: a real independent
        # finding, on the same resource, in the same file, about something else
        # entirely. Closing the obligation on it would record a review of
        # arithmetic nobody checked.
        #
        # A register record says WHAT WAS FOUND. It does not say WHAT WAS
        # REVIEWED, and no amount of overlap recovers that. So inference
        # SUGGESTS and only an explicit CITATION closes: a record naming the
        # obligation's opened_at stamp is a reviewer saying "this is the
        # obligation I looked at", which is a fact rather than a proximity.
        #
        # That is currently ZERO records, and saying so is the point -- the
        # honest way to make future reviews auto-closable is for a reviewer to
        # cite the obligation, which costs one timestamp.
        stamp = rec.get('opened_at') or '(no stamp)'
        cited = [e for e in hits if stamp in e[4]]
        (matched if cited else suggested).append((rec, cited or hits))

    if suggested:
        print('CANDIDATES -- evidence that is CLOSE, and does not close anything.')
        print('An independent-review record on the same resource and file is not')
        print('a review of the same QUESTION. Read them and run --discharge if')
        print('one really is:')
        print('')
        for rec, hits in suggested:
            print('  %-8s %s  %s' % (rec.get('author_session'), rec.get('opened_at'),
                                     ', '.join(rec.get('resources') or [])))
            for c, dt, _f, summary, _t in hits:
                print('      near  : %s %s  %s' % (c[:12], dt, summary[:70]))
        print('')

    if not matched:
        print('NOTHING TO CLOSE. No open obligation is CITED by a defect-register')
        print("record -- a record naming the obligation's opened_at stamp, which is")
        print('a reviewer saying which obligation they looked at.')
        print('%d obligation(s) remain open and need a human --discharge.'
              % len(open_records(data)))
        print('')
        print("TO MAKE A FUTURE REVIEW CLOSE ITSELF: put the obligation's")
        print("opened_at stamp in the register record's summary. One timestamp.")
        return 0
    print('CITED -- these name the obligation they reviewed:')

    for rec, hits in matched:
        print('%s  %s' % (rec.get('author_session'), rec.get('opened_at')))
        print('   resources : %s' % ', '.join(rec.get('resources') or []))
        for c, dt, _f, summary, _t in hits:
            print('   evidence  : %s %s  %s' % (c[:12], dt, summary[:78]))
        if write:
            # Through the SHARED write point, not inline. This used to set the
            # same four fields itself, which meant the self-review refusal
            # guarded one closure path and not the other -- see _discharge().
            try:
                _discharge(
                    rec, '(defect register: %s)' % AUTO_METHOD,
                    'AUTO-DISCHARGED against %d defect-register record(s) whose '
                    'detection_method is %s and whose files overlap this '
                    'obligation: %s. THIS IS A WEAKER CLOSE THAN A HUMAN '
                    'DISCHARGE and the status says so: the register carries no '
                    'session attribution, so this cannot prove the reviewer was '
                    'not the author -- it trusts the recorded method.'
                    % (len(hits), AUTO_METHOD, ', '.join(h[0][:12] for h in hits)),
                    'reviewed-by-record')
            except SelfSigned as e:
                sys.stderr.write('REFUSED: %s\n' % e)
                return 1
    print('')
    if not write:
        print('%d obligation(s) WOULD be closed as `reviewed-by-record`. Nothing'
              % len(matched))
        print('was written -- re-run with --write.')
        print('')
        print('READ THE EVIDENCE LINES FIRST. A file overlap is not a review of')
        print('the same question, and this closes on an overlap.')
        return 0
    save_reviews(data)
    print('%d obligation(s) closed as `reviewed-by-record`.' % len(matched))
    return 0


class SelfSigned(Exception):
    """A closure whose reviewer is its own author, refused at write time."""


def _discharge(rec, reviewer, verdict, status):
    """THE ONLY PLACE AN OBLIGATION IS EVER CLOSED. Both paths come through
    here so the self-review refusal cannot be true on one and forgotten on the
    other.

    ── IT WAS NOT SHARED WHEN THIS DOCSTRING FIRST CLAIMED IT WAS (2026-09-16) ─
    The helper existed and said this, and only `--discharge` called it;
    `cmd_auto_discharge` wrote the same four fields inline. So there were two
    write points, one of them with no refusal on it, under a comment asserting
    there was one. That is the defect this file's own header is about -- a check
    that reads as present and tests nothing -- committed by the gate that
    enforces it.

    ── WHY THE REFUSAL LIVES HERE AND *ALSO* IN cmd_discharge ─────────────────
    Deliberate, not a leftover. cmd_discharge refuses EARLY so a session that
    types its own name gets the rule quoted at it before anything is read; this
    one refuses at the WRITE, against the record's own stored `author_session`
    rather than against a string somebody typed on the command line. The second
    is the one a future third path cannot skip.

    The auto path can never trip it -- its reviewer names a MECHANISM, not a
    session -- and that is the point: the guard is unconditional, so it does not
    need each caller to be trusted to have thought about it.
    """
    if reviewer and reviewer == rec.get('author_session'):
        raise SelfSigned(
            '%s cannot be recorded as the reviewer of its own obligation '
            '(opened %s). That is the one claim this rule exists to refuse.'
            % (reviewer, rec.get('opened_at')))
    if not (verdict or '').strip():
        raise SelfSigned('a closure with no verdict sentence is a tick, not a '
                         'review.')
    # ── AND THE OWNER CHECK, AT THE WRITE, FOR THE SAME REASON ─────────────
    # The self-review refusal lives here rather than only in cmd_discharge
    # because a future third path cannot skip a guard at the write. Ownership
    # gets the same treatment: an obligation stamped for somebody else is
    # refused HERE, against the record's own stored owner, not against a string
    # somebody typed.
    #
    # THREE EXEMPTIONS, EACH NARROW AND EACH FOR A STATED REASON:
    #   * an UNOWNED record (reviewer_owner absent or None) -- every obligation
    #     opened before this shipped is in that state, and refusing them all
    #     would freeze the existing queue rather than protect it. Those stay
    #     first-come, and --list says so out loud.
    #   * the AUTO path, whose reviewer names a MECHANISM rather than a session
    #     (`by-defect-register`). Ownership is about two humans colliding; a
    #     record-backed close is neither of them, and blocking it would break a
    #     mechanism Michael turned on deliberately.
    #   * a recorded TAKEOVER, which cmd_discharge sets only when the owner has
    #     sat past OWNER_STALE_HOURS and the caller asked for it explicitly.
    owner = rec.get('reviewer_owner')
    if (owner and reviewer and reviewer != owner
            and not str(reviewer).startswith('by-')
            and not rec.get('owner_takeover')):
        raise NotOwner(
            'this obligation is assigned to %s, not %s. It was stamped at open '
            'time (%s) precisely so two sessions cannot both review it -- four '
            'obligations were double-reviewed on 2026-09-21 before that existed. '
            'If %s is not going to do it, wait until the assignment is %dh old '
            'and re-run with --takeover, which RECORDS the handover instead of '
            'overwriting a verdict.'
            % (owner, reviewer, rec.get('owner_assigned_at') or 'unstamped',
               owner, OWNER_STALE_HOURS))
    rec['status'] = status
    rec['reviewer_session'] = reviewer
    rec['reviewed_at'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    rec['verdict'] = verdict.strip()


def cmd_discharge(author, verdict, opened_at=None, takeover=False):
    """Close somebody ELSE'S obligation.

    ── IT DID NOT EXIST FOR THE FIRST TWO HOURS, AND THAT WAS A REAL DEFECT ────
    The gate shipped with --open and --list and NO WAY TO CLOSE. Within the hour
    Hank did the review -- ce7764fa, two real findings against Fourth's
    dnt_rollup work, citing the obligation by name -- and the record still said
    `open`, because there was nothing to run. The reviewer had done the harder
    half and the register could not show it. A list of obligations that only
    ever grows is one people stop reading.

    THE SELF-REVIEW REFUSAL IS ENFORCED HERE, AT WRITE TIME, and not only by the
    check that reads the file afterwards. Refusing to WRITE a self-signed record
    and refusing to PASS one are different controls: with only the second, the
    file can hold the claim until somebody notices. Both now.
    """
    session = session_name()
    if session == author:
        sys.stderr.write(
            'REFUSED: %s cannot discharge an obligation authored by %s. The rule '
            'is that a Tier A change is reviewed by a session OTHER than the one '
            'that wrote it, because the author shares the blind spot that '
            'produced the code. That is the one thing this gate exists to '
            'refuse.\n' % (session, author))
        return 1
    if not verdict.strip():
        sys.stderr.write('--discharge needs a verdict sentence. "reviewed" with '
                         'no content is a tick, not a review.\n')
        return 1
    data = load_reviews()
    hit = open_records(data, author)
    if opened_at:
        hit = [r for r in hit if r.get('opened_at') == opened_at]
    if not hit:
        sys.stderr.write('No OPEN obligation authored by %r%s. `--list` shows '
                         'what is open and whose.\n'
                         % (author, (' opened at %r' % opened_at) if opened_at else ''))
        return 1
    if len(hit) > 1:
        # REFUSES TO GUESS. Two obligations by one author are two different
        # reviews, and closing the wrong one would record a review of work
        # nobody looked at -- which is worse than leaving both open.
        sys.stderr.write('%r has %d open obligations and this closes ONE. '
                         'Refusing to guess which:\n' % (author, len(hit)))
        for r in hit:
            sys.stderr.write('  %s  %s\n'
                             % (r.get('opened_at'), ', '.join(r.get('resources') or [])))
        sys.stderr.write('Pass the opened_at as the second argument to pick one.\n')
        return 1
    rec = hit[0]
    # ── TAKEOVER: AN OWNER THAT NEVER RUNS AGAIN MUST NOT BLOCK FOR EVER ───
    # This is the failure the owner stamp CREATES, and it has to be answered in
    # the same change or the fix is worse than the race: an obligation assigned
    # to a session that dies is an obligation nobody can close, and this
    # platform already has that shape recorded for expired claims. So a takeover
    # exists -- and it is EXPLICIT, TIME-GATED and RECORDED, never silent.
    if takeover:
        owner = rec.get('reviewer_owner')
        if not owner:
            sys.stderr.write('REFUSED: that obligation is UNOWNED, so there is '
                             'nothing to take over -- just discharge it.\n')
            return 1
        if owner == session:
            sys.stderr.write('REFUSED: %s already owns that obligation. '
                             'Discharge it without --takeover.\n' % session)
            return 1
        age = owner_age_hours(rec)
        if age is None:
            sys.stderr.write(
                'COULD NOT TELL: owner_assigned_at is missing or unreadable on '
                'that record (%r), so how long %s has held it is unknown. A '
                'takeover on an unknown age is a takeover on a guess. Fix the '
                'stamp, or discharge as the owner.\n'
                % (rec.get('owner_assigned_at'), owner))
            return 2
        if age <= OWNER_STALE_HOURS:
            sys.stderr.write(
                'REFUSED: %s has held that obligation for %.1fh and the takeover '
                'threshold is %dh. Taking it now is the race this stamp removed, '
                'wearing a flag.\n' % (owner, age, OWNER_STALE_HOURS))
            return 1
        rec['owner_takeover'] = {
            'from': owner, 'by': session,
            'at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'owner_held_hours': round(age, 1),
            'why': ('assigned owner did not discharge within %dh'
                    % OWNER_STALE_HOURS),
        }
    try:
        _discharge(rec, session, verdict, 'reviewed')
    except (SelfSigned, NotOwner) as e:
        rec.pop('owner_takeover', None)      # do not leave a half-done handover
        sys.stderr.write('REFUSED: %s\n' % e)
        return 1
    save_reviews(data)
    print('DISCHARGED -- %s reviewed the obligation %s opened %s, on %s'
          % (session, author, rec.get('opened_at'),
             ', '.join(rec.get('resources') or [])))
    if rec.get('owner_takeover'):
        print('TAKEOVER RECORDED -- was assigned to %s, held %.1fh'
              % (rec['owner_takeover']['from'],
                 rec['owner_takeover']['owner_held_hours']))
    return 0


def main(argv):
    if '--open' in argv:
        i = argv.index('--open')
        why = argv[i + 1] if len(argv) > i + 1 else ''
        try:
            why = body_from_file_or(argv, why)
        except CouldNotTell as e:
            sys.stderr.write('COULD NOT TELL: %s\n' % e)
            return 2
        if not why.strip():
            sys.stderr.write('--open needs a sentence saying what changed. An entry '
                             'nobody can read is not a record.\n')
            return 1
        rng = None
        if '--range' in argv:
            j = argv.index('--range')
            rng = argv[j + 1] if len(argv) > j + 1 else ''
            if not rng.strip():
                sys.stderr.write('--range needs A..B\n')
                return 1
            rng = rng.strip()
        try:
            return cmd_open(why.strip(), rng)
        except CouldNotTell as e:
            sys.stderr.write('COULD NOT TELL: %s\n' % e)
            return 2
    if '--discharge' in argv:
        # --takeover is stripped BEFORE the positional parse so it can be given
        # anywhere, and so it can never be swallowed into a verdict sentence --
        # a flag that silently became part of the prose would be a handover
        # nobody could find.
        takeover = '--takeover' in argv
        argv = [a for a in argv if a != '--takeover']
        # --body-file and its path are stripped before the positional parse for
        # the same reason --takeover is: a flag swallowed into the verdict
        # prose is a verdict nobody can search and a flag nobody can find.
        try:
            file_body = body_from_file_or(argv, None)
        except CouldNotTell as e:
            sys.stderr.write('COULD NOT TELL: %s\n' % e)
            return 2
        if '--body-file' in argv:
            k = argv.index('--body-file')
            argv = argv[:k] + argv[k + 2:]
        rest = argv[argv.index('--discharge') + 1:]
        if file_body is not None:
            if len(rest) >= 2 and re.match(r'^\d{4}-\d{2}-\d{2}T', rest[1]):
                return cmd_discharge(rest[0], file_body, opened_at=rest[1],
                                     takeover=takeover)
            if len(rest) >= 1:
                return cmd_discharge(rest[0], file_body, takeover=takeover)
            sys.stderr.write('--discharge <author-session> [opened_at] '
                             '--body-file <path>\n')
            return 1
        if len(rest) >= 3 and re.match(r'^\d{4}-\d{2}-\d{2}T', rest[1]):
            return cmd_discharge(rest[0], ' '.join(rest[2:]), opened_at=rest[1],
                                 takeover=takeover)
        if len(rest) >= 2:
            return cmd_discharge(rest[0], ' '.join(rest[1:]), takeover=takeover)
        sys.stderr.write('--discharge <author-session> [opened_at] <verdict '
                         'sentence>   [--takeover]\n')
        return 1
    if '--rules' in argv:
        return cmd_rules()
    if '--validate' in argv:
        return cmd_validate()
    if '--list' in argv:
        return cmd_list()
    if '--auto-discharge' in argv:
        return cmd_auto_discharge('--write' in argv)
    # READING THE DIFF CAN FAIL, AND THAT IS A THIRD ANSWER. It used to be a
    # silent empty string, which this gate reads as "no Tier A resource touched"
    # -- a pass. Exit 2 keeps could-not-tell separate from both a finding and a
    # clean run, the same way check() has always treated an unreadable register.
    try:
        if '--diff-range' in argv:
            rng = argv[argv.index('--diff-range') + 1]
            base, _, tip = rng.partition('..')
            text = range_diff(base, tip or 'HEAD')
        elif '--stdin-diff' in argv:
            text = sys.stdin.read()
        else:
            text = working_diff()
    except CouldNotTell as e:
        sys.stderr.write('COULD NOT TELL -- the diff could not be read, so NOTHING '
                         'WAS CHECKED. This is NOT a pass:\n  %s\n' % e)
        return 2
    code, lines = check(text)
    out = sys.stderr if code else sys.stdout
    for ln in lines:
        out.write(ln + '\n')
    return code


def _guarded(argv):
    """An unexpected exception must NOT leave here as exit 1.

    ── THE HALF THE ENCODING FIX DID NOT REACH, AND THE WORSE HALF ─────────────
    tools/sairn_push_gate_hook.py maps this tool's exit codes:

        returncode == 1  ->  deny("this push changes code serving a Tier A
                                   resource and no independent-review
                                   obligation is recorded for it")
        returncode == 2  ->  "COULD NOT TELL -- this is NOT a pass"

    An uncaught Python exception ALSO exits 1. So when the decode defect above
    crashed this tool on a real push, the hook did not report a crash -- IT MADE
    A SPECIFIC, CREDIBLE, FALSE ACCUSATION, naming a review obligation that did
    not exist for a change touching no Tier A resource. Re-running the identical
    range against the fixed tool returns "No file in this change names a Tier A
    resource", exit 0. Verified by running the PRE-FIX file from a scratch copy
    against that same range: AttributeError, exit 1.

    A gate that cries wolf in the vocabulary of a genuine finding is worse than
    one that crashes visibly: a crash gets fixed, a false finding gets believed
    and worked around. Every unexpected exception now becomes exit 2, which the
    hook already treats as not-a-pass WITHOUT inventing a reason.

    The FINDING path still exits 1. Nothing about what this gate refuses has
    changed -- only what it is allowed to claim when it does not know.
    """
    try:
        return main(argv)
    except SystemExit:
        raise
    except Exception as e:                      # noqa: BLE001 -- deliberate
        import traceback
        sys.stderr.write(
            'COULD NOT TELL -- the Tier A review gate raised an unexpected '
            'exception, so NOTHING WAS CHECKED. This is NOT a pass, and it is '
            'NOT a finding either:\n  %s: %s\n' % (type(e).__name__, e))
        traceback.print_exc(file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(_guarded(sys.argv[1:]))
