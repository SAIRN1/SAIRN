"""The independent-review rule on Tier A code, as a gate rather than a habit.

    python tools/tier_a_review_gate.py                 # working tree AND the
                                                       # outgoing push range
    python tools/tier_a_review_gate.py --diff-range A..B   # check a commit range
    python tools/tier_a_review_gate.py --open "why"    # record this session's obligation
    python tools/tier_a_review_gate.py --list          # what is open, and whose
    python tools/tier_a_review_gate.py --discharge <author> [opened_at] "<verdict>"
        THE opened_at IS SECOND, NOT LAST. This line said `<author> "<verdict>"`
        and a real call passing the timestamp then a flag wrote `--help` as the
        verdict of a 70h obligation and printed DISCHARGED. Both shapes are now
        refused at write time; the usage line is corrected here so the refusal is
        the second line of defence rather than the only one.
    python tools/tier_a_review_gate.py --auto-discharge [--write]
    python tools/tier_a_review_gate.py --reseat-shas [--write]  # a DANGLING sha
    python tools/tier_a_review_gate.py --reseat-shas --write --write-weak-basis
    python tools/tier_a_review_gate.py --reseat-shas --json  # machine-readable reason CODES
    python tools/tier_a_review_gate.py --reseat-shas --include-reviewed  # REVIEWED records too
        A reviewed record whose sha is orphaned was outside the population
        entirely until 2026-10-08 -- not refused, not listed, absent. The
        default population is unchanged; the count of reviewed records with a
        sha, and how many of them dangle, is now printed either way.

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
import datetime
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

# How many times save_reviews() retries os.replace against the Windows
# concurrent-replace failure. THE CAP IS A DECISION, NOT A ROUND NUMBER: at the
# ~76% per-attempt failure rate cody measured (305 of 400 iterations raising,
# docs/2026-10-13-cody-b6-routed-to-cc.md PART 1), 20 attempts put exhaustion
# near 1e-11, so an exhaustion is a signal rather than noise. UNBOUNDED IS
# WRONG -- it turns a genuine deadlock into a hang, which PR 1.12 names as the
# shape that must never exist.
_REPLACE_RETRIES = 20
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
    # ── THE BATCH REPORT AND DIGEST (added 2026-10-13, cc) ─────────────────
    # The clause above says "every session worklog lives at the repo root by
    # convention" and keys on `.md` because worklogs are markdown. The batch
    # REPORT and DIGEST are the same class of artefact and are `.txt`, so they
    # were in scope -- and a report whose whole job is to EXPLAIN a Tier A
    # finding names the resource it is about.
    #
    # MEASURED, NOT ASSUMED, AND THE EVIDENCE IS AN OVERRIDE LOG. This push was
    # refused for `leg_invoices` and `rf_draws`, named nowhere in its code and
    # only in SAIRN-report-cc-b4.txt and SAIRN-digest-cc-b4.txt -- one of them
    # in a sentence reporting a DIFFERENT false positive in this same gate. The
    # four agents' eight report/digest files are all tracked, all prose, and
    # docs/BYPASS-LOG.jsonl carries 93 rows whose recent entries are hank using
    # the BLANKET SAIRN_SEED_GATE=off form, which disables every check in the
    # push. That is the hollowing-out this gate's own override message warns
    # about, arriving through a false positive rather than through impatience.
    #
    # THE ALTERNATIVES WERE WORSE AND ARE RECORDED SO THEY ARE NOT RETRIED.
    # Rewording the report to avoid the resource names is rewording to slip a
    # matcher, on the document whose value IS naming what was found. Opening an
    # obligation for leg_invoices and rf_draws would record a review of code
    # this session never touched -- a false entry in the one register that
    # decides who reviews what.
    #
    # SCOPED TO THE NAME, THE EXTENSION AND THE ROOT, all three. A `.txt`
    # anywhere would be too wide (a fixture or a golden file is not prose), and
    # the path must carry no separator, so docs/ and tools/ keep their own
    # classifications. Same "the predicate is about WHAT THE FILE IS" axis as
    # every clause above.
    (lambda c: ('/' not in c and '\\' not in c
                and c.lower().endswith('.txt')
                and re.match(r'^SAIRN-(report|digest)-', c)),
     'a batch report or digest is prose about findings -- the same class as the '
     'worklog above, in .txt rather than .md. A report that EXPLAINS a Tier A '
     'finding has to name the resource'),
    # ── THE HOVER AUDITOR'S OWN TOOLING (H2 seq 425, added 2026-09-30) ──────
    # This gate tripped TWICE in one session on a resource NAME appearing as a
    # bare token in auditor tooling -- "leg_insurance" in the citation linter's
    # fixtures (seq 416), "quotes" in stale_basis_check.py's prose (seq 422) --
    # and each trip demanded an obligation the auditor STRUCTURALLY CANNOT
    # COMMIT, because tools/hover_auditor_scope_gate.py refuses
    # docs/tier-a-reviews.json from that clone. A gate that requires a record
    # its subject is forbidden to write is a deadlock, not a gate.
    #
    # NO STRING ANALYSIS CAN FIX THIS AND THIS FILE ALREADY SAID SO.
    # strip_diff_noise() blanks PROSE and keeps SHORT tokens, because a resource
    # token in real serving code IS a short literal ('sb_ts') -- so a fixture
    # token is "character-for-character what a handler writes", in this file's
    # own words, and the dead end was left "for whoever owns this gate".
    #
    # SO THE PREDICATE IS ABOUT WHAT THE FILE IS, the axis every clause above
    # already uses. The auditor's core rule FORBIDS it writing platform code, so
    # a resource name in its rotation pool, its fixtures or a regex example is a
    # MENTION and can never be a handler. Same "naming is not serving" logic as
    # docs/ and sql/.
    #
    # SCOPED TO THE AUDITOR TREE ALONE, trailing slash included: a sibling skill
    # directory and a directory merely PREFIXED with this name are both still in
    # scope, and the probe holds all three directions.
    # ── NARROWED 2026-09-30, AND THE NARROWING IS MEASURED ─────────────────
    # It landed as the whole directory tree, which was the widest clause here.
    # Measured over all 79 tracked files in that tree: 13 carry a Tier A name
    # and EVERY ONE of them is inside a `tools*/` subdirectory. So the clause is
    # scoped to those, and a file directly under the auditor root or in some new
    # non-tools subdirectory stays IN SCOPE -- the same "a new directory must be
    # a decision, not a default" rule this gate's own probe already enforces for
    # top-level directories, applied one level down.
    #
    # NOT NARROWED FURTHER TO `.py`, though all 13 carriers are .py today. That
    # would re-open the deadlock for the data files beside them --
    # hover-watchlist.json is precisely the shape that will name resources one
    # day, and the obligation it would force is one the auditor cannot commit.
    # Trading a real future deadlock for 6 files of extra precision is the wrong
    # side of that bargain.
    #
    # `tools*` rather than the two names, for the same reason AuditorScope
    # replaced a hardcoded pair: a third auditor instance brings tools-hover3/.
    (lambda c: re.match(r'^\.claude/skills/sairn-hover-auditor/tools[^/]*/',
                        c.replace(os.sep, '/')) is not None,
     "the hover auditor's own tooling serves no platform resource by "
     'definition -- its core rule forbids writing platform code, so a resource '
     'NAME in a rotation-pool list, a fixture or a regex example is a mention, '
     "not a handler. Same 'naming is not serving' logic as docs/ and sql/, and "
     'the obligation it would otherwise force is one the auditor is refused '
     'permission to commit (H2 seq 416/422/425)'),
)


# The floor under a verdict. Not a quality bar -- nothing can measure that --
# but a length no genuine review of a Tier A change comes in under, chosen so
# that `--help`, `ok`, `looks fine` and a shifted timestamp are all refused.
# Declared 2026-09-29. Both halves of the pair were undeclared, so the
# repo's largest control -- 100-plus arms plus a 13-mutation sabotage probe
# -- registered as ABSENT to the one tool whose job is to notice a checker
# with no control.
CONTROLLED_BY = ['tests/run_tier_a_review_gate_probe.py',
                 'tests/run_tier_a_review_gate_sabotage_probe.py']

MIN_VERDICT_CHARS = 40

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
        for _attempt in range(_REPLACE_RETRIES):
            try:
                os.replace(tmp, REVIEWS)
                break
            except PermissionError:
                # WINDOWS ONLY, AND NAMED RATHER THAN CAUGHT BROADLY.
                # os.replace is MoveFileEx(MOVEFILE_REPLACE_EXISTING) here and
                # fails ERROR_ACCESS_DENIED (WinError 5) while the destination
                # is held open -- INCLUDING by another MoveFileEx in flight on
                # the same target. POSIX rename(2) cannot reach this branch, so
                # the retry costs nothing there.
                #
                # A bare `except OSError` would also swallow a full disk and a
                # vanished directory, and retrying those _REPLACE_RETRIES times
                # and THEN raising is strictly worse than raising once --
                # tests/run_save_reviews_retry_probe.py arm 4 is that case.
                #
                # IT RE-RAISES ON EXHAUSTION. A retry that gives up quietly
                # converts a lost record into a SILENT lost record, which is
                # worse than the defect it was added for.
                if _attempt == _REPLACE_RETRIES - 1:
                    raise
                time.sleep(0.01)
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


COMMENT_PROSE_WORDS = 3

# Which marker starts a comment, decided by extension rather than guessed. An
# extension that is in NEITHER set gets no comment stripping at all -- see the
# `path=None` paragraph in strip_diff_noise().
_HASH_EXT = ('.py', '.sh', '.bash', '.yml', '.yaml', '.toml', '.cfg', '.ini',
             '.conf', '.gitignore', '.gitattributes', '.env')
_SLASH_EXT = ('.js', '.mjs', '.cjs', '.ts', '.tsx', '.jsx', '.css', '.java',
              '.go', '.c', '.h', '.cpp', '.html', '.htm')


def _comment_body_start(body, path):
    """(marker, index-just-after-it) for the first UNQUOTED comment marker.

    None when there is none, or when `path` does not tell us which marker this
    language uses. Walks characters and tracks the open quote, so a marker inside
    a string literal is not a comment -- the failure mode a regex has here is
    silent, which is why _strip_code_noise() is also written this way.
    """
    if not path:
        return None
    p = path.replace('\\', '/').lower()
    base = p.rsplit('/', 1)[-1]
    ext = ('.' + base.rsplit('.', 1)[1]) if '.' in base else ''
    hash_ok = ext in _HASH_EXT or (ext == '' and '/' in p)   # extensionless hooks
    slash_ok = ext in _SLASH_EXT
    if not hash_ok and not slash_ok:
        return None
    i, n, in_s = 0, len(body), None
    while i < n:
        c = body[i]
        nxt = body[i + 1] if i + 1 < n else ''
        if in_s:
            if c == '\\':
                i += 2
                continue
            if c == in_s:
                in_s = None
            i += 1
            continue
        if c in ('"', "'", '`'):
            in_s = c
            i += 1
            continue
        if slash_ok and c == '/' and nxt == '/':
            # `https://` and `file://` are not comments. One character of
            # context is enough and is cheaper than a URL grammar.
            if i and body[i - 1] == ':':
                i += 2
                continue
            return '//', i + 2
        if hash_ok and c == '#':
            return '#', i + 1
        i += 1
    return None


def strip_diff_noise(line, path=None):
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

    ── THE COMMENT DECISION IS NOW REVERSED, DELIBERATELY AND BY MEASUREMENT
    (2026-10-06, open-work row 95 / H2 seq 546) ────────────────────────────
    The paragraph above left this open -- "whether a comment in a CHECKER should
    count the way a comment in a handler does" -- and declined to decide it from
    inside an unrelated change. TEN measured instances later it is decided, and
    the reason the old decision failed is not that it was unreasonable but that
    its cost ran one way: every false demand opens a real obligation that costs a
    reviewer a full read, and complying is always cheaper than fixing, so they
    accumulated instead of forcing the question.

    THE OLD ARGUMENT, restated so it is not lost: "a hunk that discusses
    sc_claims was edited by somebody thinking about sc_claims." True, and it is
    an argument for REPORTING, not for BLOCKING -- which is exactly the
    distinction context_only_tier_a() already draws for hunk context. A comment
    is now treated the same way: a weaker signal, demoted rather than deleted.

    THE RULE IS THE SAME ONE, NOT A SECOND ONE. A comment body is blanked when
    it reads as a SENTENCE -- three or more whitespace-separated words, the
    identical `_blank` threshold applied to prose string bodies. So:

        # the sc_claims branch must refuse an unassigned caller   -> BLANKED
        // sd_vendors                                             -> KEPT
        # sb_perf, sd_comms                                       -> KEPT

    A short code-shaped comment is how a developer labels a real code site, and
    those still count. A sentence is prose.

    THE MARKER IS CHOSEN BY EXTENSION AND DEFAULTS TO BLANKING NOTHING.
    `#` is a comment in .py/.sh/.yml and is a private field or a fragment
    elsewhere; `//` is a comment in .js and is the middle of `https://` in any
    language. With no `path` the function blanks no comments at all, because the
    direction of a wrong guess here is a gate going QUIET, which this docstring
    already names as the worse of the two failures.

    IT IS A CHARACTER WALK, NOT A REGEX, for the reason _strip_code_noise() gives
    in its own docstring: the regex version of exactly this already shipped a
    defect on this platform, and a string containing a comment marker breaks the
    regex version silently.

    WHAT IT STILL DOES NOT REACH, measured and reported rather than claimed
    fixed: a diff line in the INTERIOR of a multi-line Python docstring carries
    no quote character and no `#`, so neither this nor the prose rule sees it.
    That is instance 1 of the ten (`sc_anesthesia_base_units` out of
    citation_drift_hook.py's docstring). Fixing it needs line numbers from the
    hunk headers mapped against an `ast` parse of the file, which is a different
    change with a different control, and it is named here instead of being
    silently absent.
    """
    body = line[1:] if line[:1] in ('+', '-', ' ') else line

    def _blank(m):
        inner = m.group(2)
        return m.group(1) + (' ' * len(inner) if len(inner.split()) >= 3
                             else inner) + m.group(1)

    cut = _comment_body_start(body, path)
    if cut is not None:
        marker, start = cut
        inner = body[start:]
        if len(inner.split()) >= COMMENT_PROSE_WORDS:
            # Length preserved, like _blank above, so nothing downstream shifts.
            body = body[:start] + (' ' * len(inner))

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
        # THE PATH IS PASSED so the comment marker is chosen by extension rather
        # than guessed; with no path, strip_diff_noise() blanks no comments at
        # all. See its `path=None` paragraph for why that is the safe default.
        scanned = strip_diff_noise(line, cur)
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


# ── THE TWO ENTRY POINTS ANSWERED DIFFERENT QUESTIONS (2026-09-27) ──────────
# Register 1a79c8a08a1d, recorded 11 days and left planned: "the gate's two
# halves disagreed and nothing reconciled them -- a reader who checked first
# would have been told the opposite of what happened."
#
# WALKED INTO AGAIN TODAY, WHICH IS WHY IT IS BEING CLOSED RATHER THAN RE-AGED.
# A session committed a new Tier A engine, ran `python tools/tier_a_review_gate
# .py` to check before pushing, and was told in as many words:
#
#     "No file in this change names a Tier A resource on a changed line, and no
#      changed line falls inside a registered coding rule. Nothing to record."
#
# and then the push was DENIED by this same tool naming seven resources. Both
# answers were correct about what they read. The bare entry point read the
# WORKING TREE, which was clean because the work was already committed; the
# push hook reads `merge-base origin/main HEAD..HEAD`, the outgoing commits.
#
# THE SHAPE OF THE DEFECT IS NOT "ONE HALF WAS WRONG". It is that the default
# scope silently EXCLUDED the only scope the caller cared about, and said
# "nothing to record" -- a clean verdict about a question nobody asked. That is
# the same family as PR 1.11: an answer that cannot be told from the answer to
# the question you meant.
#
# So the default now reads BOTH, names what it read, and -- the half that keeps
# this from being a new silent pass -- if the outgoing range cannot be resolved
# it returns COULD NOT TELL for that half rather than quietly reporting on the
# working tree alone. `--diff-range` and `--stdin-diff` are unchanged: a caller
# that names a scope gets exactly that scope, and the push hook is such a caller.
PUSH_BASE_REF = 'origin/main'


def push_range():
    """(base, tip) -- the range tools/sairn_push_gate_hook.py will examine.

    Derived the same way the hook derives it, from the same refs, rather than
    copied as a string: two spellings of "what is being pushed" is the defect
    this function exists to remove, and writing a second one here would be it.
    """
    tip = git('rev-parse', 'HEAD').strip()
    if not tip:
        raise CouldNotTell('HEAD does not resolve to a commit')
    base = git('merge-base', PUSH_BASE_REF, tip).strip()
    if not base:
        raise CouldNotTell('no merge-base between %s and HEAD' % PUSH_BASE_REF)
    return base, tip


def default_scope_diff():
    """(diff text, notes, could_not_tell) for a run that named no scope.

    `could_not_tell` is a THIRD state and the caller must exit 2 on it. It is
    true when the outgoing range could not be read -- which is not "no Tier A
    resource touched", and is not a finding either.
    """
    wt = working_diff()
    try:
        base, tip = push_range()
    except CouldNotTell as e:
        return wt, [
            'COULD NOT TELL, and this is NOT a pass. The OUTGOING COMMIT RANGE '
            'could not be resolved (%s), so only the uncommitted working tree '
            'was examined.' % e,
            'The push gate examines the range, not the working tree. A clean '
            'answer about the working tree says NOTHING about whether your '
            'push will be blocked -- which is exactly how this tool told one '
            'session "nothing to record" minutes before denying its push.',
            'Name the scope yourself to get a real answer:  '
            'python tools/tier_a_review_gate.py --diff-range <base>..HEAD',
        ], True
    rng = range_diff(base, tip)
    n = len([ln for ln in git('rev-list', '%s..%s' % (base, tip)).split('\n')
             if ln.strip()])
    notes = [
        'SCOPE: the uncommitted working tree AND the outgoing range '
        '%s..%s (%d commit(s)) -- the same range the push gate reads. '
        'Both, because a clean working tree is not an empty push.'
        % (base[:12], tip[:12], n),
        # NAMED BECAUSE A LIMIT NOBODY STATES READS AS COVERAGE. working_diff()
        # is two `git diff` calls and neither sees an untracked file, so a
        # brand-new handler sitting unstaged contributes nothing to the answer
        # above. `git add` makes it visible; so does committing it, via the
        # range. Pinned in both directions by section 2b of the probe.
        'THE WORKING-TREE HALF EXCLUDES UNTRACKED FILES -- a new file that has '
        'never been `git add`ed is not in this answer. Add or commit it first.',
    ]
    if n == 0:
        notes.append('NOTE: 0 outgoing commits against %s. If you have not '
                     'fetched, that number is as stale as your last fetch and '
                     'the push may still find commits to examine.'
                     % PUSH_BASE_REF)
    return wt + '\n' + rng, notes, False


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


# ── A CLAIM FILE IS NOT A PULSE (cc b11) ────────────────────────────────────
# How long a session may be silent before it stops being an eligible reviewer.
#
# THE DEFECT, MEASURED: eligible_reviewers() listed every *.json in
# CLAIMS_DIR, so `cloud` -- whose newest claim is 2026-09-27, SEVENTEEN DAYS
# before this was written -- was still eligible. Worse, assign_owner() is
# LEAST-LOADED, and a dead session accrues no load, so the dead one looked
# like the best candidate and was preferentially picked. It owned FOUR of the
# twenty open obligations, including the oldest on the platform at 401 hours,
# and one had been assigned to it THAT MORNING -- so this was accumulating,
# not historical.
#
# WHY SEVEN DAYS AND WHY THAT IS NOT A TUNED NUMBER: the real separation is
# enormous. At the time of writing every live session's newest claim was HOURS
# old and the dead one's was 408 hours old, so any threshold between about one
# day and two weeks classifies this data identically. Seven days is stated as
# "has not participated in a week", and the margin is PRINTED by --roster so a
# reader can see how far from the boundary each session actually is rather
# than trusting the constant.
#
# EXCLUDING A LIVE SESSION BY MISTAKE IS THE SAFE DIRECTION, which is why the
# threshold can be generous without being dangerous: a roster that shrinks
# below two returns None, and None is a LOUD refusal to assign -- the caller
# prints why and no obligation is created. The unsafe direction is the one
# that was shipping: silently assigning to somebody who will never answer.
SESSION_DEAD_HOURS = 7 * 24


def session_last_activity(name):
    """-> (hours since this session's newest claim, note) or (None, why).

    None is the THIRD STATE and is never folded into alive or dead: an
    unreadable or unparseable claim file means liveness was not established,
    which is a different fact from "this session is gone".
    """
    p = os.path.join(CLAIMS_DIR, name + '.json')
    try:
        doc = json.loads(io.open(p, encoding='utf-8').read())
    except OSError as e:
        return None, 'claim file unreadable (%s)' % e.__class__.__name__
    except ValueError as e:
        return None, 'claim file will not parse (%s)' % e.__class__.__name__
    stamps = [c.get('claimed_at') for c in (doc.get('claims') or [])
              if c.get('claimed_at')]
    if not stamps:
        return None, 'the claim file holds no dated claim'
    try:
        newest = max(
            datetime.datetime.fromisoformat(s.replace('Z', '+00:00'))
            for s in stamps)
    except (ValueError, TypeError):
        return None, 'no claim timestamp could be parsed'
    now = datetime.datetime.now(datetime.timezone.utc)
    return (now - newest).total_seconds() / 3600.0, newest.isoformat()


def reviewer_roster_detail():
    """-> (eligible, excluded, unknown). The evidence behind eligible_reviewers.

    Separated so the roster can be REPORTED rather than only acted on: a
    session silently dropped from a roster is the same class of invisible as
    the dead one silently kept in it.
    """
    try:
        names = sorted(
            f[:-5] for f in os.listdir(CLAIMS_DIR)
            if f.endswith('.json') and re.match(r'^[a-z][a-z0-9_-]{1,31}\.json$', f))
    except OSError:
        return None, [], []
    names = [n for n in names if not is_hover_session(n)]
    eligible, excluded, unknown = [], [], []
    for n in names:
        hours, note = session_last_activity(n)
        if hours is None:
            unknown.append((n, note))
        elif hours > SESSION_DEAD_HOURS:
            excluded.append((n, hours, note))
        else:
            eligible.append((n, hours, note))
    return eligible, excluded, unknown


def eligible_reviewers():
    """Sessions that may be assigned a review, from the claim files on disk.

    LIVENESS IS REQUIRED, not just the existence of a claim file -- see
    SESSION_DEAD_HOURS. Returns a sorted list, or None for COULD NOT TELL --
    never a guess and never a hardcoded roster.

    A session whose liveness could NOT be established is excluded from the
    returned roster and is NOT counted toward the two-name minimum: an
    obligation assigned on the strength of a file nobody could read is the
    shape this whole change exists to stop.
    """
    detail = reviewer_roster_detail()
    if detail[0] is None:
        return None
    eligible, _excluded, _unknown = detail
    names = sorted(n for n, _h, _note in eligible)
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


# ── STALE BY CODE, NOT BY CLOCK (item 102 part 4, 2026-09-25) ───────────────
# OVERDUE_HOURS asks "has anybody got to this yet". It cannot ask the other
# question, and the other question is the one that decides whether the review
# is still WORTH anything: HAS THE CODE MOVED UNDER IT.
#
# An obligation opened an hour ago against a file three sessions have since
# rewritten is not fresh in any useful sense -- the reviewer would read a diff
# that no longer describes the tree, sign it, and the ledger would carry a
# verdict about code that is gone. That is not hypothetical here: this platform
# runs four build clones on one branch, and `docs/CRITICALITY-TIERS.md` alone
# took eleven commits in two days. The clock says an hour; the tree says the
# subject changed.
#
# WHAT IS COMPARED IS THE RECORD'S OWN FILES, NOT HEAD ITSELF. `HEAD != the
# recorded sha` is true within minutes of every push and would mark the whole
# queue stale, which is a signal nobody reads -- the same failure the overdue
# banner was nearly reduced to. So the test is whether any path in the record's
# `files` differs between the sha it was opened at and HEAD. That is the exact
# set the reviewer was pointed at.
#
# FOUR STATES, NOT TWO, and the two that are not FRESH/STALE are the reason
# this is written out rather than folded into a boolean:
#   UNSTAMPED       -- opened before this field existed, or naming no files.
#                      NOT fresh. Every record already in the ledger on the day
#                      this landed is in this state, and printing them as clean
#                      would be a fleet-wide false all-clear on arrival.
#   COULD-NOT-TELL  -- the sha does not resolve in this clone (rebased away,
#                      or never fetched), or git failed. PR 1.11: could-not-run
#                      is a third answer and is never folded into passed.
#
# AND IT IS RELATIVE TO THIS CLONE'S HEAD, which is said out loud in the output
# rather than assumed: a clone that has not fetched sees less movement than one
# that has, so FRESH here means "nothing I can see has moved it", never "nothing
# has".
def head_sha():
    return git('rev-parse', 'HEAD').strip()


# ── --open STAMPED HEAD, AND HEAD IS NOT THE COMMIT UNDER REVIEW (2026-10-07)
# THE COMMENT ABOVE _open_record SAYS the stamp is "the commit the reviewer's
# diff is relative to". That is only true when --open runs on top of the change
# commit and nothing else. In practice it runs after a regeneration, a
# chore(claims) commit, or a merge -- and then the stamped sha contains NONE of
# the files the record names.
#
# MEASURED AGAINST THE WHOLE LEDGER AT HEAD dea44d22, 2026-10-07, not against
# the two records that first showed it. 238 records; for each one that carries
# both a sha and a file list, `git show --format= --name-only <sha> -- <files>`:
#
#   145  no opened_at_sha at all -- the field postdates them, not a defect here
#    30  sha is not an object in this clone -- unfetched branch, CANNOT TELL
#    24  CONTAINS      the stamped commit really did touch the named files
#     5  EMPTY, merge  a merge's diff is empty by default, so also cannot tell
#    34  EMPTY, NON-MERGE -- the stamped commit's diff contains NONE of them
#
# So 34 of the 63 checkable records -- 54% -- anchor an obligation to a commit
# that never contained its subject, and they come from FIVE different sessions
# (hank 12, cody 12, hover2 4, cc 4, fourth 2). That spread is the replication:
# not two sessions agreeing, five independent record sets showing the same shape.
#
# IT IS NOT A COSMETIC FIELD. code_staleness() diffs the named files between
# this sha and HEAD, so a sha that never contained them makes STALE/FRESH a
# verdict about the wrong interval -- and the reviewer either reconstructs the
# subject by hand (what both of us did) or reviews the wrong diff.
#
# THE BASIS IS RECORDED BESIDE THE SHA rather than inferred, because a reader
# who cannot tell which rule produced a value has to trust it. `file-set` is the
# real answer; `head` is the honest fallback when there are no files to go on;
# and a git failure yields None, never a guess, for the reason head_sha()'s own
# callers already state -- a wrong sha reports a confident FRESH or STALE.
def _extra_file_count(sha, paths):
    """How many files that commit changed BEYOND the record's set, or None.

    NONE IS NOT ZERO. If git cannot answer, writing 0 would publish "this
    commit changed exactly the record's files" -- a claim nobody checked -- and
    that is the whole shape PR 1.11 is about. A merge commit with an empty
    --name-only is the same case.
    """
    try:
        out = git('show', '--name-only', '--format=', sha)
    except Exception:                                            # noqa: BLE001
        return None
    touched = set(x.strip().replace(chr(92), '/')
                  for x in out.split(chr(10)) if x.strip())
    if not touched:
        return None
    return len(touched - set(p.replace(chr(92), '/') for p in paths))


def subject_sha(files):
    """(sha, basis) for the commit a review is really about.

    basis is 'file-set' when the sha is the last commit touching the named
    files, 'head' when the record names no files, and the sha is None with
    basis 'could-not-tell' when git cannot answer.

    ── THE SHA'S COMMIT IS USUALLY WIDER THAN THE RECORD (disclosed b15) ──
    `git log -1 -- <paths>` answers "the last commit that touched ANY of
    these", and that commit almost always touched other files too. The record
    then names N files and is anchored to a commit changing N+M, so a reviewer
    reading `opened_at_sha` and running `git show` sees a diff wider than the
    obligation they were given, with nothing in the record saying how much of
    it to ignore. (`code_staleness()` is UNAFFECTED -- it scopes its own `git
    diff` to the record's `files`. Checked, not assumed.)
    THIS IS NOT FIXED BY NARROWING THE SHA. There is no commit that changed
    exactly the record's file set in the general case, and inventing one by
    filtering the diff would be a sha that is not in the history. So the WIDTH
    IS DISCLOSED, as a THIRD RETURN VALUE and a separate record field rather
    than smuggled into the basis string: `tests/run_tier_a_open_basis_probe.py`
    pins `BASES = ('file-set', 'head', 'could-not-tell')` and a `file-set+3`
    would have been refused by cody's probe as an unknown basis. That probe is
    cody's and is not edited here. The reseat path already printed this for its
    weak basis -- *"that commit changed those AND more"* -- and the open path
    was the half that said nothing.

    -> (sha, basis, extra_file_count). extra is None when git could not say,
    which is a third answer and is not written as 0.
    """
    paths = sorted({f for f in (files or []) if f})
    if paths:
        try:
            out = git('log', '-1', '--format=%H', '--', *paths).strip()
        except Exception:
            out = ''
        if out:
            return (out, 'file-set', _extra_file_count(out, paths))
        # No commit has ever touched them -- a brand-new untracked file. HEAD is
        # then the only honest anchor and the basis says so.
    try:
        return (head_sha(), 'head', None)
    except CouldNotTell:
        return (None, 'could-not-tell', None)


def code_staleness(rec, head=None):
    """-> (state, detail). state in FRESH | STALE | UNSTAMPED | COULD-NOT-TELL."""
    sha = rec.get('opened_at_sha')
    if not sha:
        return ('UNSTAMPED', 'opened before the sha stamp existed, so whether '
                             'the code moved under it cannot be computed -- '
                             'which is not the same answer as fresh')
    files = sorted(set(f for f in (rec.get('files') or []) if f))
    if not files:
        return ('UNSTAMPED', 'the record names no files, so there is no subject '
                             'to compare a sha against')
    # ── A RECONSTRUCTED BASELINE IS SAID OUT LOUD ON EVERY LINE THAT USES IT.
    # Computed HERE, above every return that has a sha, because the first
    # version computed it at the bottom and the `sha == HEAD` early return
    # skipped it -- so the one record whose baseline was most obviously
    # reconstructed printed a bare FRESH. A backfilled record and a stamped
    # one must never read the same: the first errs EARLY by construction (see
    # backfill_shas) and can therefore over-report STALE, which a reader has
    # to be able to discount. Caught by the probe arm, not by review.
    how = ' [baseline BACKFILLED from the timestamp, not stamped at open]' \
        if rec.get('opened_at_sha_backfilled') else ''
    try:
        if head is None:
            head = head_sha()
        # Resolve FIRST and separately: `git diff` against an unknown sha fails
        # with the same exit code as a dozen other things, and "the sha is gone"
        # is a different report from "git broke".
        try:
            git('rev-parse', '--verify', '--quiet', sha + '^{commit}')
        except CouldNotTell:
            return ('COULD-NOT-TELL',
                    'the recorded sha %s does not resolve in this clone -- '
                    'rebased away without a reseat, or never fetched. NOT '
                    'fresh.%s' % (sha[:12], how))
        # CONVENTION 19, ADDED 2026-10-07: OBJECT EXISTENCE IS NEVER EVIDENCE
        # OF REACHABILITY. The resolve above is `rev-parse --verify`, which
        # answers OK for a commit that is ON A REF *and* for one that is
        # ORPHANED -- present in this clone's object store but reached by
        # nothing, gc-eligible here and ABSENT from every other clone. A diff
        # against an orphaned commit is a diff against something no other
        # session can reproduce, and it was being reported as a plain
        # FRESH/STALE verdict.
        #
        # MEASURED, NOT HYPOTHETICAL: at eb430f25, docs/tier-a-reviews.json
        # cited SEVEN orphaned 40-char shas -- 00030f2d11b7, 13e40c9d79b7,
        # 773fc2189cb0, 7d15d0a27af0, a9e35feef967, c4dd292fd8a8, e4b3f21a2ceb
        # -- and one of them, 00030f2d11b7, was the basis of a printed
        # "** STALE ** moved since 00030f2d11b7" verdict.
        #
        # This function already contained the right test: _is_reachable() uses
        # `git merge-base --is-ancestor`. The gate carried both methods and the
        # freshness path used the weaker one.
        #
        # HEAD is accepted as well as PUSH_BASE_REF deliberately: a record
        # opened at a local commit that has not been pushed yet is reachable
        # from HEAD and not from origin/main, and that is ordinary work, not an
        # orphan.
        if not (_is_reachable(sha, PUSH_BASE_REF) or _is_reachable(sha, 'HEAD')):
            return ('COULD-NOT-TELL',
                    'the recorded sha %s RESOLVES but is ORPHANED -- no ref '
                    'reaches it from %s or HEAD, so it is gc-eligible here and '
                    'absent from every other clone. A diff against it is not '
                    'reproducible. Needs a reseat, not a verdict.%s'
                    % (sha[:12], PUSH_BASE_REF, how))
        if sha.strip() == head.strip():
            return ('FRESH',
                    'HEAD is still the commit it was opened at%s' % how)
        moved = [ln.strip() for ln
                 in git('diff', '--name-only', sha + '..' + head, '--',
                        *files).split('\n') if ln.strip()]
    except CouldNotTell as e:
        return ('COULD-NOT-TELL', '%s%s' % (e, how))
    if moved:
        return ('STALE', 'moved since %s: %s%s'
                % (sha[:12], ', '.join(moved), how))
    return ('FRESH', 'none of its %d file(s) changed since %s%s'
            % (len(files), sha[:12], how))


# ── BACKFILLING THE STAMP, AND WHY IT IS NOT THE SAME THING (2026-09-25) ────
# The field landed on a ledger that already had 15 open records, and every one
# of them reports UNSTAMPED -- correct, and useless. A record whose staleness
# cannot be computed is exactly the one nobody is tracking, which is the state
# this check was built to leave.
#
# THE BASELINE IS RECONSTRUCTED, NOT RECOVERED, and the difference is written
# INTO THE RECORD rather than left for a reader to infer. `opened_at` says when
# the obligation was written; `git rev-list -1 --before=<that> origin/main`
# says which commit was the tip of the shared branch at that moment. That is a
# very good guess and it is still a guess, so the record carries
# `opened_at_sha_backfilled: true` and every reader prints it. A backfilled
# record and a stamped one must not be indistinguishable -- that is the whole
# defect shape this file keeps recording.
#
# THE ERROR HAS A KNOWN DIRECTION, WHICH IS WHY IT IS SAFE TO DO AT ALL. A
# session opens an obligation from ITS OWN HEAD, which may carry unpushed
# commits, so the real baseline can be AHEAD of origin/main's tip at that
# instant. The reconstruction therefore errs EARLY, and an early baseline makes
# MORE files look moved -- it can over-report STALE and can never under-report
# it. A check that errs toward "look again" is the right direction for this one.
#
# IT NEVER OVERWRITES AN EXISTING STAMP, it is DRY RUN unless --write is given,
# and a timestamp that resolves to no commit is left alone rather than filled
# with something. The tool that READS this field is the tool that writes it, so
# the writer is deliberately the most conservative thing that is still useful.
def backfill_shas(write=False):
    try:
        data = load_reviews()
    except CouldNotTell as e:
        sys.stderr.write('COULD NOT TELL: %s\n' % e)
        return 2
    rows = [r for r in (data.get('records') or [])
            if r.get('status') == 'open' and not r.get('opened_at_sha')]
    already = sum(1 for r in (data.get('records') or [])
                  if r.get('status') == 'open' and r.get('opened_at_sha'))
    print('%d open record(s) already stamped; %d with no sha'
          % (already, len(rows)))
    if not rows:
        print('Nothing to backfill.')
        return 0
    filled, skipped = [], []
    for r in rows:
        when = r.get('opened_at') or ''
        if not re.match(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$', when):
            skipped.append((r, 'opened_at %r is not a readable timestamp' % when))
            continue
        try:
            sha = git('rev-list', '-1', '--before=' + when, 'origin/main').strip()
        except CouldNotTell as e:
            skipped.append((r, str(e)))
            continue
        if not sha:
            skipped.append((r, 'no commit on origin/main at or before %s -- '
                               'left unstamped rather than filled with a guess'
                            % when))
            continue
        filled.append((r, sha))
    for r, sha in filled:
        print('  %-8s %s  ->  %s  (%s)'
              % (r.get('author_session'), r.get('opened_at'), sha[:12],
                 ', '.join((r.get('resources') or [])[:3]) or 'no resources'))
    for r, why in skipped:
        print('  %-8s %s  SKIPPED -- %s'
              % (r.get('author_session'), r.get('opened_at'), why[:110]))
    if not write:
        print('')
        print('DRY RUN -- nothing was written. Add --write to stamp them.')
        print('Each sha is RECONSTRUCTED from the timestamp, not recovered, and')
        print('every stamped record will carry opened_at_sha_backfilled: true so')
        print('a reader can never mistake one for a stamp taken at open time.')
        return 0
    for r, sha in filled:
        r['opened_at_sha'] = sha
        r['opened_at_sha_backfilled'] = True
    save_reviews(data)
    print('')
    print('STAMPED %d record(s), %d left alone. Commit docs/tier-a-reviews.json.'
          % (len(filled), len(skipped)))
    return 0


def stale_records(data, session=None):
    """[(record, state, detail)] for every open record that is not FRESH."""
    try:
        head = head_sha()
    except CouldNotTell as e:
        head = None
        _ = e
    out = []
    for r in open_records(data, session):
        state, detail = code_staleness(r, head)
        if state != 'FRESH':
            out.append((r, state, detail))
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


# ── THE IRREVERSIBLE CLASS (item 99, 2026-09-25) ────────────────────────────
# THE GAP THIS CLOSES IS MEASURED, NOT ARGUED. Everything above matches on
# RESOURCE NAMES appearing on changed lines, which cannot see a change to the
# machinery every resource depends on. Driven against dadfedf4 -- "all 48 role
# membership sets get a null prototype", a change to api/_lib/auth.js, the file
# 82 API files require -- this gate answers:
#
#     "No file in this change names a Tier A resource on a changed line ...
#      Nothing to record."   exit 0
#
# A platform-wide change to role membership, landing with no obligation, because
# no resource name happened to appear in the hunk.
#
# ── WHY A SEPARATE CLASS AND NOT "JUST ADD MORE NAMES" ──────────────────────
# Tier A is 261 resources; a pre-landing requirement on all of them would refuse
# essentially every push, and this file's own history says what happens then --
# a gate red on arrival gets switched off, and the rule ends up worse than when
# it was merely unenforceable. The criterion here is NOT the tier. It is
# whether a later commit undoes the effect: a revert does not un-execute SQL,
# does not recall a minted token, does not un-rely a firm on a reconciliation.
# Scoped and measured in
# docs/2026-09-25-item99-graduated-approval-proposal.md -- the candidate class
# is about 1% of commits (30 of 2894 in fourteen days).
#
# ── IT STARTS EMPTY, AND THAT IS THE DESIGN ─────────────────────────────────
# With no members this changes NOTHING: every existing push behaves exactly as
# it did. Nothing historical is retroactively non-compliant, which is the
# objection item 99's own section 5 raised against its `Reviewed-By:` proposal
# and the reason that proposal was never built.
#
# ── ADDING A MEMBER IS A CLAIM ──────────────────────────────────────────────
# Same convention run_all_tests.py's CONCURRENCY_SENSITIVE uses. Each entry
# says, in a written reason, WHY a revert does not undo this file's effect. Do
# not add a path because it looks important.
#
#   ('path',    'api/_lib/auth.js',  'why a revert does not undo it')
#   ('sqlgrant', None,               'any sql/ file whose diff adds a grant or
#                                     revoke -- the statement has already run')
#
# WHAT THIS REQUIRES IS A RECORDED OBLIGATION, NOT A DISCHARGED ONE. Requiring
# the review itself before landing is a different and larger decision -- it
# makes a push wait a median 8.2h and a p90 of 55.3h on a four-session platform
# -- and it is Michael's to make. That proposal is written up in the document
# above and deliberately NOT implemented here.
IRREVERSIBLE_CLASS = ()

_SQL_GRANT_RE = re.compile(r'^[+].*\b(grant|revoke)\b', re.I | re.M)


def touched_irreversible(diff_text, members=None):
    """{label: [paths]} for every irreversible-class member this diff changes.

    FAILS CLOSED BY CONSTRUCTION: an entry whose `kind` this function does not
    recognise raises CouldNotTell rather than being skipped. A member silently
    ignored is a member that protects nothing while appearing in the list --
    the exact shape PR 1.11 is about, and the one a class like this fails by.
    """
    members = IRREVERSIBLE_CLASS if members is None else members
    if not members:
        return {}
    per_file = {}
    cur = None
    for line in diff_text.splitlines():
        if line.startswith('diff --git '):
            parts = line.split(' b/')
            cur = parts[-1].strip() if len(parts) > 1 else None
            if cur:
                per_file.setdefault(cur, [])
        elif cur is not None:
            per_file[cur].append(line)
    out = {}
    for entry in members:
        kind, key, reason = entry[0], entry[1], entry[2]
        if kind == 'path':
            if key in per_file:
                out.setdefault(key, []).append(key)
        elif kind == 'sqlgrant':
            for path, body in per_file.items():
                if path.startswith('sql/') and _SQL_GRANT_RE.search(chr(10).join(body)):
                    out.setdefault('sql/ grant|revoke', []).append(path)
        else:
            raise CouldNotTell(
                'irreversible-class entry %r has kind %r, which this gate does '
                'not know how to evaluate. A member it cannot check is a member '
                'that protects nothing.' % (key or reason, kind))
    return out


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
    # THE IRREVERSIBLE CLASS, matched on PATH rather than on a resource name --
    # see the block above touched_irreversible for the measured gap this closes.
    # Raised, not swallowed: an unevaluatable member is a COULD NOT TELL for the
    # whole run, never a quiet skip.
    try:
        irr_hits = touched_irreversible(diff_text)
    except CouldNotTell as e:
        return 2, ['COULD NOT TELL -- this is NOT a pass:',
                   '  ' + str(e)]
    if not hits and not rule_hits and not irr_hits:
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
    covered_irr = set()
    for r in mine:
        covered |= set(r.get('resources') or [])
        covered_rules |= set(r.get('rules') or [])
        covered_irr |= set(r.get('irreversible') or [])
    uncovered = sorted(set(hits) - covered)
    # PER RULE, FOR THE SAME REASON COVERAGE IS PER RESOURCE. An obligation
    # naming the KX threshold does not cover a change to the SWO element list
    # that happened to ride along in the same push.
    uncovered_rules = sorted(set(rule_hits) - covered_rules)
    uncovered_irr = sorted(set(irr_hits) - covered_irr)
    if not uncovered and not uncovered_rules and not uncovered_irr:
        if verbose:
            if hits:
                lines.append('Tier A code changed: %s' % ', '.join(sorted(hits)))
            if rule_hits:
                lines.append('Coding rules changed: %s' % ', '.join(sorted(rule_hits)))
            if irr_hits:
                lines.append('Irreversible-class files changed: %s'
                             % ', '.join(sorted(irr_hits)))
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
    for name in uncovered_irr:
        lines.append('  %-22s %s  [IRREVERSIBLE]'
                     % (name, ', '.join(sorted(set(irr_hits[name])))[:92]))
    if uncovered_irr:
        lines.append('')
        lines.append('AN IRREVERSIBLE-CLASS FILE CHANGED WITH NO RECORDED OBLIGATION.')
        lines.append('')
        lines.append('This class is matched on PATH, not on a resource name, because')
        lines.append('the name-based half above CANNOT SEE a change to the machinery')
        lines.append('every resource depends on. Measured: dadfedf4 changed all 48')
        lines.append('role membership sets in api/_lib/auth.js -- required by 82 API')
        lines.append('files -- and this gate answered "Nothing to record", exit 0.')
        lines.append('')
        lines.append('MEMBERSHIP MEANS A REVERT DOES NOT UNDO THE EFFECT: a statement')
        lines.append('that has already run, a token already minted, a figure a')
        lines.append('customer already relied on. It is NOT a second name for Tier A,')
        lines.append('and the list is deliberately tiny.')
        lines.append('')
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


# ── THE RECORD-WRITING HALF, SHARED (2026-09-25) ────────────────────────
# Factored out when --resources landed, so the explicit-naming path and
# the diff-attribution path write the SAME record through the SAME code.
# Two spellings of a ledger write is how the two drift.
def _open_record(why, hits, rule_hits, irr_hits=None):
    data = load_reviews()
    author = session_name()
    owner, owner_note = assign_owner(author, data)
    # ── THE SHA THE OBLIGATION IS ABOUT (item 102 part 4) ──────────────────
    # Stamped at open, never later, because code_staleness() has nothing to
    # compare without it. None rather than a guess when git cannot answer -- an
    # UNSTAMPED record reports as could-not-compute, which is honest, where a
    # wrong sha would report a confident FRESH or a confident STALE.
    #
    # IT USED TO BE head_sha(), AND THE COMMENT HERE CLAIMED head was "the
    # commit the reviewer's diff is relative to" -- true only when --open runs
    # directly on top of the change. See subject_sha() for the measurement that
    # overturned it. The dead `opened_sha = head_sha()` that this fix left
    # sitting above the real assignment is gone with it; a value computed and
    # then unconditionally overwritten reads as a fallback that is never taken.
    # ── THE FILE SET IS COMPUTED FIRST so the sha can be derived FROM it ────
    # It used to be computed inline in the dict below, which is why the sha had
    # nothing to go on and HEAD was the only thing available. See subject_sha().
    # ALL THREE SOURCES, and the first draft of this used only two. The record's
    # own `files` field is built from hits, rule_hits AND irr_hits; deriving the
    # sha from a SMALLER set than the record publishes would have anchored the
    # obligation to a different file set than the one it names -- a quieter
    # version of the defect being fixed. Caught by reading the field rather than
    # trusting the patch.
    _files = sorted(set(list(f for fs in hits.values() for f in fs)
                        + list(f for fs in rule_hits.values() for f in fs)
                        + list(f for fs in (irr_hits or {}).values() for f in fs)))
    opened_sha, opened_basis, opened_extra = subject_sha(_files)
    rec = {
        'author_session': author,
        'opened_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'opened_at_sha': opened_sha,
        # Recorded beside the sha, never inferred: 'file-set' is the real
        # answer, 'head' the honest fallback when a record names no files, and
        # 'could-not-tell' a refusal rather than a guess.
        'opened_at_sha_basis': opened_basis,
        # ── HOW MUCH WIDER THE SHA'S COMMIT IS THAN THIS RECORD (b15) ──────
        # `git log -1 -- <paths>` answers "the last commit touching ANY of
        # these", and that commit almost always changed other files too. A
        # reviewer who runs `git show opened_at_sha` therefore sees a diff
        # WIDER than the obligation, with no way to tell from the record how
        # much of it to ignore. (code_staleness() is NOT affected -- it scopes
        # its `git diff` to `*files`, which was checked rather than assumed.)
        # ALWAYS PRESENT, for the same reason `rules` is; and None when git
        # could not say, because 0 would publish an unchecked claim that the
        # commit changed exactly these files.
        'opened_at_sha_extra_files': opened_extra,
        'resources': sorted(hits),
        # ── ALWAYS PRESENT, EVEN WHEN EMPTY (2026-09-24) ───────────────────
        # A field that appears only when non-empty is a field every reader has
        # to remember might be absent, and `set(r.get('rules') or [])` in three
        # places is one missing `or []` away from a silent miss. Written on
        # every record so the shape is one shape.
        'rules': sorted(rule_hits),
        # Same always-present rule as `rules` above, for the same reason.
        'irreversible': sorted(irr_hits or {}),
        # The SAME list the sha was derived from, by construction.
        'files': _files,
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
    subjects = (rec['resources'] + ['%s [rule]' % r for r in rec['rules']]
                + ['%s [IRREVERSIBLE]' % r for r in rec['irreversible']])
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


def cmd_open(why, rng=None, named=None):
    resources = tier_a_resources()
    rules = coding_rules()
    # ── NAMING THE RESOURCES OUTRIGHT (2026-09-25) ──────────────────────────
    # The refusal below ends with "say which resource or rule and why -- an
    # entry naming neither cannot be discharged by anybody." Until now there
    # was no way to say it, so that sentence was advice with no route.
    #
    # THE CASE IT EXISTS FOR IS NOT AN EXCEPTION TO THE docs/ EXCLUSION, IT IS
    # OUTSIDE IT. That exclusion is right and stays: CRITICALITY-TIERS.md
    # names every Tier A resource by definition, so attributing a diff of it
    # would make every push a Tier A push. But a TIER PROMOTION is a judgement
    # that lives ONLY in that document -- no code changes, so the gate
    # correctly raises nothing, and the judgement with the widest blast radius
    # on the platform is the one thing that can never be reviewed. Michael's
    # call, 2026-09-25, after two promotions landed unreviewable.
    #
    # IT CANNOT BE USED TO INVENT AN OBLIGATION: every name given must already
    # be Tier A in the register, and a name that is not is refused rather than
    # recorded. What it adds is the ability to say WHICH of the resources the
    # register already knows about this judgement is about -- not to add one.
    if named:
        unknown = [n for n in named if n not in resources]
        if unknown:
            sys.stderr.write(
                '--resources names %s, which %s not Tier A in '
                'docs/CRITICALITY-TIERS.md. This flag says WHICH known Tier A '
                'resources a judgement is about; it cannot make one.\n'
                % (', '.join(unknown), 'is' if len(unknown) == 1 else 'are'))
            return 1
        hits = {n: ['docs/CRITICALITY-TIERS.md'] for n in named}
        rule_hits = {}
        return _open_record(why, hits, rule_hits)
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
    try:
        irr_hits = touched_irreversible(text)
    except CouldNotTell as e:
        sys.stderr.write('COULD NOT TELL -- the irreversible class could not be '
                         'evaluated, so this record would be incomplete:'
                         + chr(10) + '  %s' % e + chr(10))
        return 2
    if not hits and not rule_hits and not irr_hits:
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
    return _open_record(why, hits, rule_hits, irr_hits)


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
    stale = dict((id(r), (s, d)) for r, s, d in stale_records(data))
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
        # UNSTAMPED is counted in the summary, not printed per record. On the
        # day this landed EVERY record was unstamped, and sixteen identical
        # lines saying "cannot be computed" is how a real STALE line stops
        # being seen. STALE and COULD-NOT-TELL are per record, because those
        # two name a specific thing a reader has to act on.
        if id(r) in stale and stale[id(r)][0] != 'UNSTAMPED':
            st, detail = stale[id(r)]
            print('           %-16s %s' % ('** %s **' % st, detail[:150]))
        # ── HOW MUCH OF THE SHA'S DIFF IS NOT THIS OBLIGATION (b15) ───────
        # Printed only when there IS extra, and only for a file-set basis.
        # A reviewer who runs `git show <opened_at_sha>` otherwise has no way
        # to tell how much of what they are looking at they were asked about.
        if r.get('opened_at_sha_basis') == 'file-set':
            _ex = r.get('opened_at_sha_extra_files')
            if isinstance(_ex, int) and _ex > 0:
                print('           WIDER THAN THE OBLIGATION: the commit this '
                      'is anchored to also changed %d other file(s). `git '
                      'show` on it shows more than you were asked to review.'
                      % _ex)
            elif _ex is None and r.get('opened_at_sha'):
                print('           WIDTH UNKNOWN: whether the anchored commit '
                      'touched files beyond this record was not recorded -- '
                      'opened before b15, or git could not say. Not the same '
                      'answer as "exactly these files".')
        print('           %s' % (r.get('what') or '')[:110])
    moved = [k for k, (s, _) in stale.items() if s == 'STALE']
    unknown = [k for k, (s, _) in stale.items() if s != 'STALE']
    if moved:
        print('')
        print('%d of them are STALE BY CODE: a file the obligation is about has'
              % len(moved))
        print('changed since the commit it was opened at, so the diff a reviewer')
        print('would read is no longer the diff that was recorded. That is a')
        print('separate question from the %dh clock and can be true within the'
              % OVERDUE_HOURS)
        print('hour. Relative to THIS clone\'s HEAD -- fetch before trusting a FRESH.')
    if unknown:
        print('')
        print('%d could not be compared at all (UNSTAMPED or COULD-NOT-TELL).'
              % len(unknown))
        print('That is NOT a clean bill: it is the absence of an answer, and')
        print('every record opened before the sha stamp existed is in it.')
    if late:
        print('')
        print('%d of them are past the %dh deadline. An obligation nobody closes'
              % (len(late), OVERDUE_HOURS))
        print('is a queue people stop reading, which is the state this register was')
        print('built to leave. Discharge them, or run --auto-discharge to close the')
        print('ones a defect-register record already covers.')
    if late or moved:
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
    # ── A SHIFTED ARGUMENT SILENTLY BECAME A VERDICT, 2026-09-29 ────────────
    # The usage line at the top of this file reads
    #     --discharge <author> "<verdict>"
    # and the parser wants the opened_at SECOND when there is more than one open
    # record for that author. A real call of
    #     --discharge cc 2026-09-26T13:13:44Z --help
    # therefore dispatched cleanly, wrote `--help` as the verdict, printed
    # DISCHARGED, and marked a 70h Tier A obligation `reviewed`. Nothing was
    # wrong with the dispatch; the defect is that a flag and a two-word grunt
    # were both accepted as the artefact the whole register exists to hold.
    #
    # An obligation closed with a meaningless verdict is WORSE than one left
    # open: the queue shortens, the record reads as satisfied, and the next
    # session has no reason to look. So the two shapes that cannot be a review
    # are refused at WRITE time, where --takeover and --body-file are already
    # stripped, rather than trusted to the caller getting the order right.
    _v = verdict.strip()
    if _v.startswith('--'):
        sys.stderr.write(
            'REFUSED: the verdict starts with %r, which is a FLAG and not a '
            'review.\nThe argument order is:  --discharge <author> [opened_at] '
            '"<verdict>"\nand a shifted call is how a flag becomes a verdict. '
            'Nothing was written.\n' % _v.split()[0])
        return 1
    if len(_v) < MIN_VERDICT_CHARS:
        sys.stderr.write(
            'REFUSED: the verdict is %d characters. A review of a Tier A change '
            'that fits\nin under %d is a tick, and an obligation closed with a '
            'tick is worse than one\nleft open -- the queue shortens and the '
            'next session has no reason to look.\nNothing was written. Use '
            '--body-file <path> for anything long.\n'
            % (len(_v), MIN_VERDICT_CHARS))
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


# ── THE LIVENESS LOCK (cc b11) ──────────────────────────────────────────────
# Fixtures over a FAKE claims directory, so the arms are about the rule and
# not about whichever sessions happen to be running today. Nothing here reads
# or writes the real register.
def selftest_roster():
    import shutil
    import tempfile
    print('TIER A REVIEW GATE -- eligible-reviewer liveness lock')
    bad = total = 0

    def ck(label, got, want=True):
        nonlocal bad, total
        total += 1
        if got != want:
            bad += 1
            print('  FAIL ' + label)
            print('       wanted %r, got %r' % (want, got))
        else:
            print('  ok   ' + label)

    global CLAIMS_DIR, REPO
    real = CLAIMS_DIR
    tmp = tempfile.mkdtemp(prefix='tier-a-roster-')
    try:
        now = datetime.datetime.now(datetime.timezone.utc)

        def plant(name, hours_ago, claims=1):
            stamp = (now - datetime.timedelta(hours=hours_ago)
                     ).strftime('%Y-%m-%dT%H:%M:%SZ')
            io.open(os.path.join(tmp, name + '.json'), 'w',
                    encoding='utf-8', newline='\n').write(json.dumps(
                        {'claims': [{'subject': name, 'claimed_at': stamp,
                                     'status': 'released'}] * claims}))

        def raw(name, body):
            io.open(os.path.join(tmp, name + '.json'), 'w',
                    encoding='utf-8', newline='\n').write(body)

        CLAIMS_DIR = tmp
        plant('alive1', 1)
        plant('alive2', 4)
        plant('dead', 422)              # the real `cloud` figure at fix time
        ck('THE DEFECT: a session silent for 422h is NOT eligible. It owned 4 '
           'of 20 open obligations including the oldest at 401h, and had been '
           'assigned a new one that morning',
           'dead' not in (eligible_reviewers() or []))
        ck('...and the two live sessions ARE eligible, so the fix excludes the '
           'dead one rather than emptying the roster',
           eligible_reviewers(), ['alive1', 'alive2'])
        el, ex, un = reviewer_roster_detail()
        ck('...and the exclusion is REPORTED with its evidence, not silent -- '
           'a session quietly dropped is the same class of invisible as the '
           'dead one quietly kept',
           [n for n, _h, _no in ex], ['dead'])

        # A6 THE THIRD STATE. Liveness that cannot be established is neither
        # alive nor dead and must not be folded into either.
        raw('broken', '{not json')
        el, ex, un = reviewer_roster_detail()
        ck('A6 THIRD STATE: an unparseable claim file is UNKNOWN, not dead and '
           'not alive', [n for n, _no in un], ['broken'])
        ck('A6: ...and an UNKNOWN session is not handed a review -- an '
           'obligation assigned on a file nobody could read is the shape this '
           'change exists to stop', 'broken' not in (eligible_reviewers() or []))
        raw('nostamp', json.dumps({'claims': [{'subject': 'x'}]}))
        el, ex, un = reviewer_roster_detail()
        ck('A6: a claim file with no dated claim is UNKNOWN too, by its own '
           'named reason', 'nostamp' in [n for n, _no in un])

        # A3 FAIL-CLOSED. Too few live reviewers must REFUSE, never pick one.
        for f in os.listdir(tmp):
            os.remove(os.path.join(tmp, f))
        plant('onlyone', 1)
        ck('A3 FAIL-CLOSED: ONE live session is None (could-not-tell), not a '
           'roster of one -- the only candidate would be the author',
           eligible_reviewers() is None)
        plant('dead2', 500)
        ck('A3 FAIL-CLOSED: one live plus one DEAD is still None. The dead one '
           'does not make up the quorum, which is exactly what the old count '
           'over claim FILES would have done',
           eligible_reviewers() is None)
        plant('alive3', 2)
        ck('...and a second LIVE session restores the roster, so the arm above '
           'is about liveness and not about the directory being small',
           eligible_reviewers(), ['alive3', 'onlyone'])

        # ABLATION: the pre-fix rule was "every claim file in the directory".
        # It must classify the dead session as eligible, or the arms above are
        # not about this change.
        names = sorted(f[:-5] for f in os.listdir(tmp) if f.endswith('.json'))
        prefix_rule = [n for n in names if not is_hover_session(n)]
        ck('ABLATION: the PRE-FIX rule -- every claim file, no liveness test '
           '-- DOES include the dead session, so the arms above are about this '
           'fix and nothing else', 'dead2' in prefix_rule)
        ck('ABLATION CONTROL: ...and it also includes the live ones, which is '
           'why the old code looked like it worked',
           'alive3' in prefix_rule and 'onlyone' in prefix_rule)

        # ── THE REASSIGN PATH'S DANGEROUS DIRECTION ─────────────────────────
        # Moving a DEAD owner's record is the point; moving a LIVE owner's is
        # stealing their queue. Driven through the real selector rather than
        # asserted, with a fake register.
        for f in os.listdir(tmp):
            os.remove(os.path.join(tmp, f))
        plant('livea', 1)
        plant('liveb', 2)
        plant('goner', 500)
        fake = {'records': [
            {'status': 'open', 'opened_at': 'x', 'author_session': 'livea',
             'reviewer_owner': 'liveb', 'owner_assigned_at': 'x'},
            {'status': 'open', 'opened_at': 'y', 'author_session': 'livea',
             'reviewer_owner': 'goner', 'owner_assigned_at': 'y'},
        ]}
        live_now = eligible_reviewers() or []
        ck('the live roster for the reassign arms is the two live sessions',
           sorted(live_now), ['livea', 'liveb'])
        would_move = [r for r in fake['records']
                      if r.get('status') == 'open'
                      and r.get('reviewer_owner') not in live_now]
        ck('REASSIGN: a record owned by a DEAD session is selected',
           [r['opened_at'] for r in would_move], ['y'])
        ck('REASSIGN, THE DANGEROUS DIRECTION: a record owned by a LIVE '
           'session is NOT selected -- moving a live owner\'s record is '
           'taking their queue, not fixing a dead one',
           'x' not in [r['opened_at'] for r in would_move])
        newo, _note = assign_owner('livea', fake, roster=live_now)
        ck('REASSIGN: the new owner is never the record\'s own author -- an '
           'author may not review its own obligation, and a reassignment '
           'that forgot this would create exactly that',
           newo != 'livea' and newo == 'liveb')

        CLAIMS_DIR = tmp + '-does-not-exist'
        ck('an UNREADABLE claims directory is None, never an empty roster '
           'reported as "nobody is eligible"', eligible_reviewers() is None)

        # ── THE RESEAT WINDOW IS ON AUTHOR TIME (b15) ──────────────────────
        # FAILING-FIRST: with `%cI` in _file_set_index the third element of a
        # _PER_SHA row was the COMMITTER time, so this fixture's gap computed
        # as 10.0h, the record fell outside WEAK_BASIS_WINDOW_HOURS, and a
        # reseat six minutes after its own commit was REFUSED. Measured over
        # 500 commits in this clone: 102 of 200 have the two times differing
        # at all, and 13 of 500 differ by more than the 6h window -- worst
        # 13.4h at d0ec2d57.
        # ── THE SUBJECT SHA'S WIDTH IS DISCLOSED (b15) ─────────────────────
        # Driven against THIS repo, because the point is a real commit that
        # touched more than one file. `_extra_file_count` is the layer.
        _s, _b, _x = subject_sha(['tools/tier_a_review_gate.py'])
        ck('subject_sha returns a THIRD value: how many files beyond the '
           'record\'s set its commit also changed. `git log -1 -- <paths>` '
           'answers "the last commit touching ANY of these", and a reviewer '
           'running `git show` on it sees a diff wider than the obligation',
           _b == 'file-set' and isinstance(_x, int))
        ck('...and the basis string is UNCHANGED, because '
           'tests/run_tier_a_open_basis_probe.py pins BASES to exactly three '
           'values and a `file-set+3` would have been refused as unknown. '
           'That probe is cody\'s and is not edited here',
           _b in ('file-set', 'head', 'could-not-tell'))
        ck('...and a commit git cannot read is None and NOT 0 -- writing 0 '
           'would publish "this commit changed exactly the record\'s files", '
           'a claim nobody checked',
           _extra_file_count('0' * 40, ['x']) is None)
        _w = subject_sha([])
        ck('...and a record naming NO files still returns three values, so no '
           'caller unpacks a 2-tuple',
           len(_w) == 3 and _w[1] in ('head', 'could-not-tell')
           and _w[2] is None)

        # DRIVEN THROUGH _file_set_index AGAINST A REAL REPO, not by stuffing
        # _PER_SHA. The first version of these arms injected the row directly
        # and the ablation reported the layer UNPROVEN -- correctly: the arms
        # were about _iso_hours_apart and never reached the `%aI` in the
        # format string. An arm that bypasses the layer it is for is the
        # thing this whole file exists to catch.
        keep_per_sha = dict(_PER_SHA)
        keep_repo = REPO
        fix = os.path.join(tmp, 'timerepo')
        try:
            os.makedirs(fix)
            env = dict(os.environ,
                       GIT_AUTHOR_DATE='2026-10-14T21:38:00+00:00',
                       GIT_COMMITTER_DATE='2026-10-15T07:57:00+00:00',
                       GIT_AUTHOR_NAME='a', GIT_AUTHOR_EMAIL='a@x',
                       GIT_COMMITTER_NAME='c', GIT_COMMITTER_EMAIL='c@x')
            for argv in (['init', '-q'], ['add', 'x.py'],
                         ['commit', '-q', '-m', 'subj']):
                if argv[0] == 'add':
                    io.open(os.path.join(fix, 'x.py'), 'w',
                            encoding='utf-8').write('pass\n')
                subprocess.run(['git'] + argv, cwd=fix, env=env,
                               capture_output=True)
            REPO = fix
            _PER_SHA.clear()
            idx, err = _file_set_index()
            row = list(_PER_SHA.values())[0] if _PER_SHA else None
            sha = list(_PER_SHA)[0] if _PER_SHA else ''
            ck('the fixture repo built one commit whose author and committer '
               'times are 10.3h apart, so there is something to measure',
               err is None and row is not None and len(row) == 4)
            gap = _iso_hours_apart(row[2], '2026-10-14T21:44:00Z') \
                if row else None
            ck('the reseat window measures a record against its commit\'s '
               'AUTHOR time -- a rebase rewrites committer time and leaves '
               'author time alone, and on a four-clone night every commit '
               'here has been rebased',
               gap is not None and gap < 0.2)
            ck('...and the committer time would have put this same pair '
               'outside the %dh window, refusing a reseat six minutes after '
               'its own commit' % WEAK_BASIS_WINDOW_HOURS,
               row is not None
               and (_iso_hours_apart(row[3], '2026-10-14T21:44:00Z') or 0)
               > WEAK_BASIS_WINDOW_HOURS)
            ck('...and the rebase is NAMED in the output rather than left as '
               'an unexplained gap, because "this was rebased" is the fact '
               'that explains it',
               'REBASED' in rebase_note(sha)
               and '10.3h' in rebase_note(sha))
            ck('a sha the index never saw gets NO rebase note -- half the '
               'commits here differ by seconds and that is noise',
               rebase_note('nosuchsha') == '')
        finally:
            REPO = keep_repo
            _PER_SHA.clear()
            _PER_SHA.update(keep_per_sha)
    finally:
        CLAIMS_DIR = real
        shutil.rmtree(tmp, ignore_errors=True)

    print('  %d/%d arm(s) pass' % (total - bad, total))
    if bad:
        print('  THE ROSTER RULE IS BROKEN. Every assignment it makes is '
              'suspect until these pass.')
        return 1
    return 0


# ── REASSIGNING AWAY FROM A DEAD OWNER (cc b11) ─────────────────────────────
# A DEAD OWNER IS AN ASSIGNMENT FAILURE, NOT A REVIEW FAILURE, and the two
# need different remedies. `--takeover` is coupled to `--discharge`: it means
# "I have done this review and I am recording it over the owner's head", and
# it REFUSES below OWNER_STALE_HOURS because taking a live owner's work early
# is the race the assignment stamp removed.
#
# Neither half fits a session that is simply gone. `cloud`'s four obligations
# were 401h, 338h, 33h and 7h old when this was written: two were past the
# takeover threshold and two were not, so takeover could not even reach them
# all -- and waiting 48h for a session last seen seventeen days ago is waiting
# for nothing. The alternative, one session discharging four reviews it had
# not budgeted for, trades a stuck queue for four rushed Tier A verdicts,
# which is the worse failure: an unreviewed obligation is visible and a bad
# verdict is not.
#
# SO THIS MOVES OWNERSHIP AND NOTHING ELSE. It writes no verdict, does not
# mark anything discharged, and re-runs the ordinary least-loaded assignment
# over the LIVE roster -- so the obligation lands on somebody who can act and
# the review still has to happen. The handover is recorded with the liveness
# evidence that justified it, because an ownership change with no reason on it
# is indistinguishable from somebody quietly dodging a queue.
#
# IT CANNOT TOUCH A LIVE OWNER'S RECORD. The only records it will move are
# those whose owner is absent from the live roster, which is checked per
# record rather than passed in.
def cmd_reassign_dead(session, apply_changes=False):
    detail = reviewer_roster_detail()
    if detail[0] is None:
        sys.stderr.write('COULD NOT RUN: the roster could not be read from '
                         '%s, so no owner is known to be dead.\n' % CLAIMS_DIR)
        return 2
    el, ex, un = detail
    live = sorted(n for n, _h, _no in el)
    if not live:
        sys.stderr.write('COULD NOT RUN: no session is live, so there is '
                         'nobody to reassign to.\n')
        return 2
    dead = dict((n, h) for n, h, _no in ex)
    unknown = dict(un)
    data = load_reviews()
    moved, blocked = [], []
    for rec in data.get('records', []):
        if rec.get('status') != 'open':
            continue
        owner = rec.get('reviewer_owner')
        if owner in live or not owner:
            continue
        if owner in unknown:
            # A6 THIRD STATE: liveness was not established, so this is NOT a
            # dead owner and must not be moved on a guess.
            blocked.append((rec, owner, 'owner liveness UNKNOWN (%s) -- not '
                                        'moved on a guess' % unknown[owner]))
            continue
        if owner not in dead:
            continue
        new_owner, note = assign_owner(rec.get('author_session') or '',
                                       data, roster=live)
        if not new_owner:
            blocked.append((rec, owner, note or 'no eligible live reviewer'))
            continue
        moved.append((rec, owner, new_owner, dead[owner]))
        if apply_changes:
            rec['reviewer_owner'] = new_owner
            rec['owner_assigned_at'] = time.strftime(
                '%Y-%m-%dT%H:%M:%SZ', time.gmtime())
            rec.setdefault('owner_reassignments', []).append({
                'from': owner, 'to': new_owner, 'by': session,
                'at': rec['owner_assigned_at'],
                'from_silent_hours': round(dead[owner], 1),
                'why': ('the assigned owner has been silent for %.0fh, past '
                        'the %dh liveness threshold, so it was never going to '
                        'discharge this. Ownership moved; NO verdict was '
                        'written and the review still has to happen.'
                        % (dead[owner], SESSION_DEAD_HOURS)),
            })

    print('REASSIGN AWAY FROM A DEAD OWNER%s'
          % ('' if apply_changes else '  (DRY RUN -- nothing written)'))
    print('  live roster : %s' % ', '.join(live))
    for n, h in sorted(dead.items()):
        print('  DEAD        %-12s silent %.0fh' % (n, h))
    for n, why in sorted(unknown.items()):
        print('  UNKNOWN     %-12s %s' % (n, why))
    print('')
    if not moved and not blocked:
        print('  Nothing to do: every open obligation has a live owner.')
        return 0
    for rec, old, new, hours in moved:
        print('  %s  %s -> %s   (owner silent %.0fh, author %s)'
              % (rec.get('opened_at'), old, new, hours,
                 rec.get('author_session')))
    for rec, old, why in blocked:
        print('  %s  owner %s NOT MOVED -- %s'
              % (rec.get('opened_at'), old, why))
    print('')
    print('  NO VERDICT WAS WRITTEN. Ownership moved so a live session can '
          'discharge it;')
    print('  the review itself is still owed.')
    if apply_changes:
        save_reviews(data)
        print('  WROTE %s -- commit it with the change it covers.'
              % os.path.relpath(REVIEWS, REPO))
    else:
        print('  Re-run with --apply to write it.')
    return 1 if blocked else 0


def main(argv):
    if '--selftest' in argv:
        return selftest_roster()
    if '--reassign-dead' in argv:
        return cmd_reassign_dead(session_name(), apply_changes='--apply' in argv)
    if '--roster' in argv:
        detail = reviewer_roster_detail()
        if detail[0] is None:
            print('COULD NOT READ %s -- no roster was computed.' % CLAIMS_DIR)
            return 2
        el, ex, un = detail
        print('ELIGIBLE REVIEWERS -- liveness from the newest claim per session')
        print('  dead after: %dh (%d days)'
              % (SESSION_DEAD_HOURS, SESSION_DEAD_HOURS // 24))
        for n, h, note in el:
            print('  LIVE     %-12s %8.1fh since %s' % (n, h, note))
        for n, h, note in ex:
            print('  SILENT   %-12s %8.1fh since %s   NOT eligible'
                  % (n, h, note))
        for n, why in un:
            print('  UNKNOWN  %-12s %s   NOT eligible, and NOT counted as dead'
                  % (n, why))
        # THE MARGIN, PRINTED. The constant separates this data by ~100x, so a
        # reader can see the threshold is not finely tuned rather than take it
        # on faith.
        if el and ex:
            print('  margin: newest live %.1fh, oldest silent %.1fh'
                  % (max(h for _n, h, _no in el),
                     min(h for _n, h, _no in ex)))
        return 0 if eligible_reviewers() else 1
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
        named = None
        if '--resources' in argv:
            j = argv.index('--resources')
            raw = argv[j + 1] if len(argv) > j + 1 else ''
            named = [n.strip() for n in raw.split(',') if n.strip()]
            if not named:
                sys.stderr.write('--resources takes a comma-separated list '
                                 'of Tier A resource names.' + chr(10))
                return 1
            if rng:
                sys.stderr.write('--resources and --range answer the same '
                                 'question two ways. Pick one: --range '
                                 'attributes a real diff, --resources names '
                                 'the subjects of a judgement that has no '
                                 'diff to attribute.' + chr(10))
                return 1
        try:
            return cmd_open(why.strip(), rng, named)
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
    if '--backfill-shas' in argv:
        return backfill_shas('--write' in argv)
    if '--reseat-shas' in argv:
        _only = None
        if '--only' in argv:
            _i = argv.index('--only')
            if _i + 1 >= len(argv) or argv[_i + 1].startswith('--'):
                sys.stderr.write('--only needs an opened_at timestamp, e.g. '
                                 '--only 2026-10-06T22:18:54Z. Nothing was '
                                 'examined.\n')
                return 2
            _only = argv[_i + 1]
        return reseat_shas('--write' in argv, '--write-weak-basis' in argv,
                           '--json' in argv,
                           '--include-reviewed' in argv, _only)
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
    scope_notes, scope_unknown = [], False
    try:
        if '--diff-range' in argv:
            rng = argv[argv.index('--diff-range') + 1]
            base, _, tip = rng.partition('..')
            text = range_diff(base, tip or 'HEAD')
        elif '--stdin-diff' in argv:
            text = sys.stdin.read()
        else:
            # SEE default_scope_diff() -- a bare run used to read the working
            # tree ONLY and answer "nothing to record" about a scope the push
            # gate does not examine.
            text, scope_notes, scope_unknown = default_scope_diff()
    except CouldNotTell as e:
        sys.stderr.write('COULD NOT TELL -- the diff could not be read, so NOTHING '
                         'WAS CHECKED. This is NOT a pass:\n  %s\n' % e)
        return 2
    code, lines = check(text)
    out = sys.stderr if code else sys.stdout
    # THE SCOPE IS PRINTED BEFORE THE VERDICT, and on the same stream, because a
    # verdict whose scope is one scroll away is a verdict read without it.
    for ln in scope_notes:
        out.write(ln + '\n')
    if scope_notes:
        out.write('\n')
    for ln in lines:
        out.write(ln + '\n')
    # An unresolvable outgoing range outranks a clean verdict about the other
    # half: 0 would say "checked, nothing found". It does NOT outrank a real
    # finding -- a finding is something that WAS found and stays a 1.
    if scope_unknown and code == 0:
        return 2
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



# ── PRESENT-AND-DANGLING IS A THIRD STATE, AND NEITHER COMMAND OWNED IT ──────
# `--list` reports a record whose recorded sha no longer resolves as
# "COULD-NOT-TELL -- rebased away without a reseat", and there was no reseat.
# `backfill_shas` does not cover it: it fills a sha that is MISSING and prints
# "0 with no sha" while a record sits there present-and-dangling.
#
# HIT BY HAND TWICE BEFORE THIS EXISTED. The 2026-09-26T01:43:54Z record pointed
# at 59e85d77 and the real commit was 9ff4b87f; the 2026-09-27T02:17:49Z record
# pointed at 191d2dce and the real commit was c123a925. Both were found by
# matching the record's FILE LIST and its opening sentence against the log --
# which is the algorithm below, and which nobody should perform by hand a third
# time.
#
# THE DURABLE KEY IS THE FILE LIST, not the subject. `defect_register.py --reseat`
# matches on subject because its records store one; a review record stores
# `files`, `resources`, `what` and `opened_at`. A rebase rewrites the hash and
# preserves the tree, so the set of paths a commit touched is what survives.
#
# RESOLVABLE IS NOT REACHABLE, and that distinction is inherited deliberately
# rather than rediscovered: a rebase leaves the original commit behind as a
# dangling object that still `rev-parse`s for as long as the reflog holds it. The
# test is ancestry against origin/main, which is what another clone will fetch.
#
# IT REFUSES RATHER THAN GUESSES, in three named ways: no candidate, more than
# one candidate, or no readable base ref. A ledger an auditor follows is the last
# place to write a best guess, and picking one of two matches is a guess.
def _reseat_base():
    """The ref reachability is measured against. (ref, None) or (None, why)."""
    for ref in ('origin/main', 'HEAD'):
        try:
            if git('rev-parse', '--verify', '--quiet', ref).strip():
                return ref, None
        except CouldNotTell:
            continue
    return None, ('neither origin/main nor HEAD could be read, so EVERY record '
                  'would look unreachable and this would reseat the whole '
                  'ledger on the strength of not being able to look')


def _is_reachable(sha, base):
    """True / False / None(could not tell)."""
    if not sha:
        return None
    try:
        git('merge-base', '--is-ancestor', sha, base)
        return True
    except CouldNotTell:
        pass
    try:
        # Distinguish "not an ancestor" from "git could not answer at all": a
        # sha that does not even resolve is not an ancestor, which is the answer
        # this function needs rather than an error.
        git('rev-parse', '--verify', '--quiet', sha + '^{commit}')
        return False
    except CouldNotTell:
        return False


def _file_set_index(since=None):
    """{frozenset(paths): [(sha, subject)]} from ONE git log pass.

    ── ONE PASS, AND THE FIRST VERSION WAS UNUSABLE ────────────────────────
    The first draft ran `git show --name-only` per commit. Against ~7,000 commits
    that is 7,000 subprocesses and it did not finish inside two minutes -- a
    repair command nobody can run is not a repair. `git log --name-only` emits
    every commit and its paths in a single stream; the parse below is the whole
    cost.

    `since` narrows the walk. A review record is opened in the same push as the
    commit it describes, so a window around `opened_at` is generous rather than
    tight -- and it is a WINDOW rather than a cutoff, because an early baseline
    is the error direction backfill_shas already argues for.
    """
    # ── AUTHOR TIME, NOT COMMITTER TIME (fixed 2026-10-15, cc b15) ───────
    # This read `%cI` and fed it to the 6-hour WEAK_BASIS_WINDOW_HOURS below.
    # A REBASE REWRITES COMMITTER TIME AND LEAVES AUTHOR TIME ALONE, and on a
    # four-clone night every commit here has been rebased. Measured over the
    # last 500 commits in this clone rather than argued:
    #
    #   102 of 200 recent commits have committer time != author time
    #   13 of 500 diverge by MORE than the 6-hour window; worst 13.4h
    #     (d0ec2d57), and in b14's own range 3474df69 is
    #     c=2026-10-15T07:57 against a=2026-10-14T21:38 -- 10.3h apart
    #
    # It is wrong in BOTH directions, which is why it had to be the author
    # time and not a wider window. A record opened six minutes after its
    # commit was authored reads as 10 hours from the committer time and gets
    # REFUSED; and every commit swept into one rebase lands in the same
    # committer minute, so a DIFFERENT commit can fall inside the window and
    # be wrongly accepted. Widening the window makes the second failure worse
    # while fixing the first, and the window's own comment already says
    # widening it is how a wrong reseat happens.
    #
    # Both are carried so a reader can see the rebase. The window uses the
    # author time; the committer time is PRINTED beside it when they differ,
    # because "this was rebased" is the fact that explains the gap.
    args = ['log', '--format=' + chr(30) + '%H' + chr(31) + '%s'
            + chr(31) + '%aI' + chr(31) + '%cI', '--name-only']
    if since:
        args.append('--since=' + since)
    try:
        out = git(*args)
    except CouldNotTell as e:
        return None, str(e)
    idx = {}
    for chunk in out.split(chr(30)):
        chunk = chunk.strip(chr(10))
        if not chunk or chr(31) not in chunk:
            continue
        head, _, rest = chunk.partition(chr(10))
        parts = head.split(chr(31))
        sha, subj = parts[0], parts[1]
        when = parts[2] if len(parts) > 2 else ''          # AUTHOR time
        ctime = parts[3] if len(parts) > 3 else ''         # committer time
        paths = frozenset(x.strip().replace(chr(92), '/')
                          for x in rest.split(chr(10)) if x.strip())
        if paths:
            idx.setdefault(paths, []).append((sha, subj))
            _PER_SHA[sha] = (paths, subj, when, ctime)
    return idx, None


def rebase_note(sha):
    """'' or a sentence naming the committer/author gap for this sha.

    SAID ONLY WHEN IT MATTERS. The two times differ on roughly half the
    commits in this clone by seconds, which is noise; the sentence appears
    once the gap could change a window verdict.
    """
    rec = _PER_SHA.get(sha)
    if not rec or len(rec) < 4 or not rec[3] or not rec[2]:
        return ''
    gap = _iso_hours_apart(rec[2], rec[3])
    if gap is None or gap < 1.0:
        return ''
    return (' [REBASED: committer time %s is %.1fh after the author time '
            '%s, and the window above is measured on the AUTHOR time]'
            % (rec[3], gap, rec[2]))


# Filled by _file_set_index:
# {sha: (frozenset(paths), subject, AUTHOR-ISO, committer-ISO)}.
# A module-level cache rather than a return value, so the extra bases below can
# ask about a sha the file-set index already walked past without a second git log.
_PER_SHA = {}

# ── THE WINDOW FOR A WEAK BASIS. REASONED, NOT CALIBRATED, AND SAID SO.
# A review record is opened in the same working session as the commit it
# describes -- the real pair measured while writing this was SIX MINUTES apart
# (record 2026-09-28T03:34:57Z, commit bb840eeccb3c at 2026-09-28T03:40:40Z). Six
# hours is generous against that and still refuses a commit from another day.
# WIDENING THIS IS HOW A WRONG RESEAT HAPPENS and it should not be widened to make
# a stubborn record match.
WEAK_BASIS_WINDOW_HOURS = 6


def _iso_hours_apart(a, b):
    """Absolute hours between two ISO timestamps, or None if either is unreadable."""
    import datetime
    def _p(x):
        x = (x or '').strip()
        if not x:
            return None
        x = x.replace('Z', '+00:00')
        try:
            d = datetime.datetime.fromisoformat(x)
        except ValueError:
            return None
        if d.tzinfo is None:
            d = d.replace(tzinfo=datetime.timezone.utc)
        return d
    da, db = _p(a), _p(b)
    if da is None or db is None:
        return None
    return abs((da - db).total_seconds()) / 3600.0


def _subject_twin(sha, base):
    """The commit on `base` whose FULL SUBJECT matches this dangling sha's.

    ── THIS IS THE STRONGEST BASIS OF THE THREE AND IT WAS NOT BEING USED.
    This file's own header says "THE DURABLE KEY IS THE FILE LIST, NOT THE
    SUBJECT", on the ground that a review record does not store a subject. TRUE
    ABOUT THE RECORD AND FALSE ABOUT THE COMMIT: when the recorded sha still
    RESOLVES in this clone -- which it does whenever the rebase that orphaned it
    happened here -- its own subject can be read out of the object store, and a
    rebase preserves the subject exactly. That is the rebase's identity, not an
    inference from it.

    Measured over the 17 dangling records on 2026-09-29: FIVE had a unique
    subject twin on origin/main, and all five were this clone's own commits. The
    other twelve had no object to read a subject from -- which is the structural
    answer to why they cannot be told from here, and is reported as such.

    Returns (twin_sha, subject, None) or (None, None, why).
    """
    try:
        head = git('log', '-1', '--format=%s', sha)
    except CouldNotTell:
        return None, None, ('the recorded sha is not in this clone\'s object '
                            'store, so its subject cannot be read. A dangling '
                            'sha is reseatable by subject only from the clone '
                            'whose rebase orphaned it -- run this there, or '
                            'fetch the object in first')
    subj = (head or '').strip().split(chr(10))[0].strip()
    if not subj:
        return None, None, 'the recorded sha resolves but carries no subject line'
    try:
        out = git('log', base, '--format=%H', '--fixed-strings', '--grep=' + subj,
                  '-n', '5')
    except CouldNotTell as e:
        return None, None, 'git log could not search %s for that subject (%s)' % (base, e)
    hits = [l.strip() for l in (out or '').split(chr(10)) if l.strip()]
    if not hits:
        return None, subj, ('the recorded sha resolves and its subject appears '
                            'nowhere on %s, so the commit was not rebased -- it '
                            'was dropped, or its message was rewritten' % base)
    if len(hits) > 1:
        return None, subj, ('%d commits on %s share that subject, so the twin is '
                            'ambiguous. Picking one would be a guess written into '
                            'a ledger an auditor follows' % (len(hits), base))
    return hits[0], subj, None


def _twin_file_agreement(twin_sha, files):
    """Does the subject twin's own diff account for the record's files?

    ── THIS CHECK EXISTS BECAUSE SUBJECT-TWIN ALONE WROTE TWO WRONG SHAS, and it
    was caught by hand-verifying all five matches before applying any of them --
    which is the "the real costly thing earns exhaustive verification" rule doing
    exactly what it is for. Measured 2026-09-29 over the five twins found:

      record 2026-09-27T01:22:40Z  files stonedesk_server_backup.js,
                                   mech_panels_live_check.py
                     twin 873e72d8  touched NEITHER -- DISJOINT
      record 2026-09-27T02:31:54Z  files api/_lib/compliance-rules*.js, sd-data.js
                     twin 4bb4d29e  touched two DOCS -- DISJOINT
      record 2026-09-27T03:42:29Z  twin 52c54530 covers 2 of its 4 -- PARTIAL
      record 2026-09-28T21:33:14Z  twin cc956d9e is a SUPERSET -- agrees
      record 2026-09-29T12:21:14Z  twin 8fd013e3 is a SUPERSET -- agrees

    A DISJOINT TWIN IS NOT A RESEAT TARGET AND THE REASON IS NOT A ROUNDING
    ERROR: it means the RECORDED SHA WAS ALREADY WRONG FOR THIS RECORD when it was
    written -- somebody stamped whatever HEAD happened to be rather than the
    commit carrying the work. Following that sha to its rebased twin preserves the
    error faithfully, which is worse than leaving it dangling, because a dangling
    sha is visibly broken and a wrong one is not. That is this command's own
    founding sentence, and subject-twin matching would have violated it.

    Returns 'SUPERSET' | 'PARTIAL' | 'DISJOINT' | 'UNKNOWN'.
    """
    want = frozenset(x.replace(chr(92), '/') for x in (files or []))
    if not want:
        return 'UNKNOWN'
    got = _PER_SHA.get(twin_sha, (None, None, None))[0]
    if got is None:
        try:
            out = git('show', '--name-only', '--format=', twin_sha)
        except CouldNotTell:
            return 'UNKNOWN'
        got = frozenset(x.strip().replace(chr(92), '/')
                        for x in (out or '').split(chr(10)) if x.strip())
    if not got:
        return 'UNKNOWN'
    if want <= got:
        return 'SUPERSET'
    if want & got:
        return 'PARTIAL'
    return 'DISJOINT'


def _subset_candidate(files, opened_at):
    """The single commit whose changed set CONTAINS `files` and lands in the window.

    ── A WEAKER BASIS, WITH ITS OWN FLAG AND ITS OWN STAMP.
    `_candidates_by_files` requires EQUALITY and says why: a commit that touched
    the record's files and ten others is a different change. That is right as the
    DEFAULT and wrong as the only rule, because a record whose file list is
    partial -- a session naming the four files it cared about out of a six-file
    commit -- can never match anything.

    So containment is admitted only when ALL of these hold:
      * exactly ONE commit anywhere contains the set,
      * NO commit matches the set exactly (equality always wins),
      * and the commit lands within WEAK_BASIS_WINDOW_HOURS of `opened_at`.

    It is never applied by --write alone; it needs --write-weak-basis, and it
    stamps `opened_at_sha_reseat_basis: 'file-set-subset'` so the weaker basis
    is never indistinguishable from the stronger one.
    """
    want = frozenset(x.replace(chr(92), '/') for x in (files or []))
    if not want:
        return None, None, 'the record names no files'
    hits = [(sha, rec[1], rec[2]) for sha, rec in _PER_SHA.items()
            if want <= rec[0] and rec[0] != want]
    if not hits:
        return None, None, 'no commit anywhere contains that file set either'
    in_window = []
    for sha, subj, when in hits:
        gap = _iso_hours_apart(when, opened_at)
        if gap is not None and gap <= WEAK_BASIS_WINDOW_HOURS:
            in_window.append((sha, subj, when, gap))
    if not in_window:
        return None, None, ('%d commit(s) contain that file set but none lands '
                            'within %dh of the record, so none of them is the '
                            'commit it was opened against'
                            % (len(hits), WEAK_BASIS_WINDOW_HOURS))
    if len(in_window) > 1:
        return None, None, ('%d commits contain that file set within the window, '
                            'so containment does not single one out'
                            % len(in_window))
    sha, subj, when, gap = in_window[0]
    return sha, (subj, when, gap), None


def _candidates_by_files(idx, files, want_subject=None):
    """Commits whose CHANGED FILE SET equals `files`.

    Equality, not containment. A commit that touched the record's files AND ten
    others is a different change, and matching it would reseat a record onto
    somebody else's push -- worse than leaving it dangling, because a dangling
    sha is visibly broken and a wrong one is not.
    """
    want = frozenset(x.replace(chr(92), '/') for x in (files or []))
    if not want:
        return [], 'the record names no files, so there is nothing to match on'
    hits = list(idx.get(want) or [])
    # THE SUBJECT IS A TIE-BREAK, NEVER THE PRIMARY KEY. When two commits touched
    # the same file set, a record whose `what` text opens with the commit's own
    # subject identifies which -- which is exactly how both real cases were
    # resolved by hand. It only ever NARROWS; it never admits a commit the file
    # set rejected.
    if len(hits) > 1 and want_subject:
        first = (want_subject or '').strip().split(chr(10))[0].strip()
        if first:
            narrowed = [h for h in hits if h[1].strip() == first]
            if len(narrowed) == 1:
                return narrowed, None
    return hits, None


def reseat_shas(write=False, weak_ok=False, as_json=False,
                include_reviewed=False, only=None):
    """Repoint a review record whose recorded sha is dangling. DRY RUN default.

    include_reviewed widens the population from open records to open AND
    reviewed. Reviewed records carrying a sha are counted and disclosed either
    way -- see the block below the status filter.
    """
    try:
        data = load_reviews()
    except CouldNotTell as e:
        sys.stderr.write('COULD NOT TELL: %s\n' % e)
        return 2
    base, why = _reseat_base()
    if base is None:
        print('COULD NOT RESEAT: %s.' % why)
        return 2

    # ── REVIEWED RECORDS WERE SILENTLY OUTSIDE THE POPULATION (2026-10-08) ──
    # This line read `status == 'open'` and nothing said so. A REVIEWED record
    # whose sha is orphaned was therefore unreachable by the only reseat path on
    # the platform: not refused, not listed, not counted -- absent. Found
    # 2026-10-07 on cody/2026-10-06T22:18:54Z, whose sha 4aa33b4565dd resolves,
    # is reachable from no ref, and appears ZERO times in this tool's own report
    # while the report names 22 open records and gives a reason for all 8 it
    # refuses.
    #
    # THE DEFAULT POPULATION IS UNCHANGED ON PURPOSE. Widening it silently would
    # move every count this tool has ever printed, and a figure that changes
    # meaning without changing name is the drift PR 2.3 is about. So:
    #   * default: open records only, exactly as before, AND
    #   * the reviewed records carrying a sha are COUNTED AND DISCLOSED, with how
    #     many of them are dangling, so the omission is visible without the flag
    #   * --include-reviewed widens the population and says it did
    # The third state is reported either way; only ACTING on it is opt-in.
    wanted = ('open', 'reviewed') if include_reviewed else ('open',)
    rows = [r for r in (data.get('records') or [])
            if r.get('status') in wanted]
    # ── --only, SO A WRITE NEED NOT RECLASSIFY EVERY SESSION'S RECORDS ──────
    # Without it `--write` repoints EVERY fixable record in one keystroke -- 11
    # of them across four sessions at the time this was added. Reseating another
    # session's record is editing their finding, and the rule on this platform is
    # that you close only what you originated. A per-record selector is the
    # difference between fixing your own and rewriting the ledger.
    #
    # A SELECTOR THAT MATCHES NOTHING IS A REFUSAL, NEVER A QUIET NO-OP: the most
    # likely typo here is a wrong timestamp, and "reseated 0 records" printed as
    # success is how that typo would be mistaken for "already fine".
    if only:
        picked = [r for r in rows if (r.get('opened_at') or '') == only]
        if not picked:
            present = sorted((r.get('opened_at') or '') for r in rows)
            print('COULD NOT RESEAT: --only %r matches no record in the %s '
                  'population. Nothing was examined and nothing was written.'
                  % (only, 'open+reviewed' if include_reviewed else 'open'))
            print('  %d record(s) are in that population; the nearest by date '
                  'are:' % len(present))
            for d in present[:6]:
                print('    %s' % d)
            if not include_reviewed:
                print('  IF THE RECORD IS REVIEWED, add --include-reviewed -- the '
                      'default population is open-only.')
            return 2
        rows = picked
    reviewed_with_sha = [r for r in (data.get('records') or [])
                         if r.get('status') == 'reviewed' and r.get('opened_at_sha')]
    # ── THE WALK WINDOW IS COMPUTED FROM THE WHOLE POPULATION, NOT FROM `rows`.
    #
    # FIXED 2026-10-11 (cody, batch 27 item 2) AFTER A MEASURED FLIP. This line
    # read `for r in rows`, and `rows` has already been narrowed by --only, so
    # the selector set the window. The same record then got two different
    # verdicts:
    #
    #   full population : window from 2026-09-15, 1311 file sets indexed
    #                     -> cody 2026-10-05T09:25:27Z RESEATABLE [EXACT FILE SET]
    #   --only that one : window from 2026-10-05,  310 file sets indexed
    #                     -> REFUSED [TWIN_SUBJECT_AMBIGUOUS]
    #
    # THAT IS THE WRONG WAY ROUND FOR A SAFETY FLAG. --only exists so a session
    # repairs its OWN records without rewriting anybody else's, so it is the
    # path a careful person takes -- and it was the path that saw less. A
    # selector must change WHICH records are acted on and never change the
    # VERDICT for one of them.
    #
    # The window is therefore taken from every record in the selected STATUS
    # population, before --only. The index costs one git log pass either way.
    _window_rows = [r for r in (data.get('records') or [])
                    if r.get('status') in wanted]
    dates = sorted(r.get('opened_at') or '' for r in _window_rows if r.get('opened_at'))
    since = (dates[0][:10] if dates else None)
    idx, err = _file_set_index(since)
    if idx is None:
        print('COULD NOT RESEAT: the log could not be read (%s), so no record '
              'was examined. That is a third state, not "nothing to reseat".'
              % err)
        return 2
    print('RESEAT DANGLING REVIEW-RECORD SHAS')
    print('  reachability measured against: %s' % base)
    print('  log walked from              : %s (the oldest open record, computed)'
          % (since or 'the beginning'))
    print('  distinct file sets indexed   : %d' % len(idx))
    print('  population                   : %s'
          % ('open + reviewed (--include-reviewed)' if include_reviewed
             else 'open only (default)'))
    print('  records examined: %d' % len(rows))
    # ── THE DISCLOSURE, PRINTED WHETHER OR NOT THE FLAG IS USED ─────────────
    # Without this the default run is indistinguishable from one where no
    # reviewed record has a problem. Counting them costs one reachability check
    # each and turns a silent omission into a number somebody can act on.
    if not include_reviewed:
        dangling_reviewed = [r for r in reviewed_with_sha
                             if _is_reachable(r.get('opened_at_sha'), base) is not True]
        print('  REVIEWED records carrying a sha: %d -- NOT examined in this '
              'mode' % len(reviewed_with_sha))
        if dangling_reviewed:
            print('    of those, %d are NOT reachable from %s and so are '
                  'dangling:' % (len(dangling_reviewed), base))
            for r in dangling_reviewed[:12]:
                print('      %-8s %s  %s'
                      % (r.get('author_session'), r.get('opened_at'),
                         (r.get('opened_at_sha') or '')[:12]))
            if len(dangling_reviewed) > 12:
                print('      ... and %d more' % (len(dangling_reviewed) - 12))
            print('    RE-RUN WITH --include-reviewed TO EXAMINE THEM. Until '
                  'then this run says nothing about them, which is not the '
                  'same as saying they are fine.')
        else:
            print('    and none of them is dangling, so nothing is hidden by '
                  'the default population this run.')

    # ── THREE BASES, IN STRENGTH ORDER, AND EVERY OUTCOME CARRIES WHICH ──
    # 1. SUBJECT TWIN -- the dangling sha resolves here and exactly one commit on
    #    the base shares its full subject. That IS the rebase identity.
    # 2. EXACT FILE SET -- one commit changed precisely the record's files.
    # 3. FILE-SET SUBSET within a time window -- weaker, own flag, own stamp.
    # A refusal names which of the six reasons it is, so "could not tell" is a
    # diagnosis rather than a shrug.
    healthy, fixable, weak, refused = [], [], [], []
    for r in rows:
        sha = r.get('opened_at_sha')
        if not sha:
            refused.append((r, 'NO_SHA_AT_ALL',
                            'NO SHA AT ALL -- that is --backfill-shas\'s job, '
                            'not this one'))
            continue
        if _is_reachable(sha, base) is True:
            healthy.append(r)
            continue

        twin, twin_subj, twin_why = _subject_twin(sha, base)
        if twin:
            agree = _twin_file_agreement(twin, r.get('files'))
            if agree == 'SUPERSET':
                fixable.append((r, twin, 'SUBJECT TWIN', twin_subj or ''))
                continue
            if agree == 'PARTIAL':
                weak.append((r, twin, 'SUBJECT TWIN, FILES PARTIAL',
                             (twin_subj or '', '', 0.0)))
                continue
            if agree == 'DISJOINT':
                refused.append((r, 'SHA_WRONG_WHEN_WRITTEN',
                                'THE RECORDED SHA WAS ALREADY WRONG FOR THIS '
                                'RECORD, and that is a different fault from a '
                                'rebase. Its subject twin on %s is %s (%r), '
                                'whose diff touches NONE of the files this '
                                'record names (%s). Following the sha to its '
                                'twin would preserve the original mis-stamp '
                                'faithfully -- a wrong sha is worse than a '
                                'dangling one, because a dangling one is '
                                'visibly broken. FIX THE RECORD, not the sha'
                                % (base, twin[:12], (twin_subj or '')[:70],
                                   sorted(set(r.get('files') or []))[:4])))
                continue
            refused.append((r, 'TWIN_CROSSCHECK_UNREADABLE',
                            'a subject twin exists on %s (%s) but neither its '
                            'diff nor the record\'s file list could be read, '
                            'so the two could not be cross-checked. A twin '
                            'accepted without that check wrote two wrong shas '
                            'in testing' % (base, twin[:12])))
            continue

        hits, err = _candidates_by_files(idx, r.get('files'), r.get('what'))
        if hits and len(hits) == 1:
            # ── AN EXACT FILE SET IS NOT A STRONG BASIS ON ITS OWN. IT NEEDS
            # THE SAME WINDOW THE SUBSET BASIS ALREADY CARRIES.
            #
            # ADDED 2026-10-11 (cody, batch 27 item 2) BECAUSE IT PRODUCED A
            # WRONG ANSWER, not because it looked thin. Record
            # 2026-10-05T09:25:27Z names exactly ['tools/sairn_claim.py'] and
            # describes the claim matcher's disclosure rule. Exactly one commit
            # in the window changes that set alone -- 6b9dc2635433,
            # "chore(claims): stamp the own-claim guard with the sha it actually
            # landed in", dated 2026-09-17, EIGHTEEN DAYS EARLIER and about a
            # different change. The tool offered it as a STRONG basis, which
            # --write alone would have applied.
            #
            # A ONE-FILE RECORD IS WHERE THIS BITES, and single-file records are
            # common: "the only commit in the window whose file set equals this
            # one" says nothing about WHEN, and a frequently-edited tool has many
            # such commits spread over weeks. Uniqueness within an arbitrary
            # window is not identity -- the same lesson the UNIQUENESS-is-not-
            # POSITION finding carries for text anchors.
            #
            # The bound is WEAK_BASIS_WINDOW_HOURS, reused rather than a second
            # invented number: a record is opened in the same working session as
            # the commit it describes, which is the premise both bases rest on.
            # Outside it this REFUSES rather than demoting to WEAK -- an 18-day
            # gap is not weaker containment, it is a different commit, and this
            # tool's own SHA_WRONG_WHEN_WRITTEN refusal already says a wrong sha
            # is worse than a dangling one because a dangling one is visibly
            # broken.
            _gap = _iso_hours_apart(_PER_SHA.get(hits[0][0], ('', '', ''))[2],
                                    r.get('opened_at'))
            if _gap is None:
                refused.append((r, 'EXACT_SET_DATE_UNREADABLE',
                                'exactly one commit changed that file set (%s) '
                                'but its date or the record\'s opened_at could '
                                'not be read, so the %dh window could not be '
                                'applied. An unbounded exact-set match is what '
                                'put an 18-day-older commit forward as a strong '
                                'basis once already'
                                % (hits[0][0][:12], WEAK_BASIS_WINDOW_HOURS)))
                continue
            if _gap > WEAK_BASIS_WINDOW_HOURS:
                refused.append((r, 'EXACT_SET_OUT_OF_WINDOW',
                                'exactly one commit changed that file set -- %s '
                                '(%r) -- but it is %.1fh from this record\'s '
                                'opened_at, outside the %dh window. A record is '
                                'opened in the same working session as the '
                                'commit it describes; a unique file-set match '
                                'from another day is a DIFFERENT commit that '
                                'happens to touch the same files. FIX THE '
                                'RECORD, not the sha%s'
                                % (hits[0][0][:12], (hits[0][1] or '')[:70],
                                   _gap, WEAK_BASIS_WINDOW_HOURS,
                                   rebase_note(hits[0][0]))))
                continue
            fixable.append((r, hits[0][0], 'EXACT FILE SET',
                            '%s, %.1fh apart%s'
                            % (hits[0][1], _gap, rebase_note(hits[0][0]))))
            continue
        if len(hits) > 1:
            # SAY WHETHER ANY CANDIDATE PRE-DATES THE RECORD. When every one
            # post-dates it, that is positive evidence that NONE of them is the
            # commit it was opened against -- a stronger statement than
            # "ambiguous", and it stops the next reader re-deriving it.
            opened = r.get('opened_at') or ''
            after = [h for h in hits
                     if (_PER_SHA.get(h[0], ('', '', ''))[2] or '') > opened]
            tail = ''
            if len(after) == len(hits):
                tail = ('. AND EVERY ONE OF THEM POST-DATES THE RECORD, so none '
                        'of them is the commit it was opened against -- the '
                        'original is gone, not mis-recorded')
            refused.append((r, 'AMBIGUOUS_EXACT_SET',
                            'AMBIGUOUS EXACT FILE SET: %d commits changed '
                            'exactly that set (%s) and the record\'s own text '
                            'does not single one out%s'
                            % (len(hits), ', '.join(h[0][:12] for h in hits[:4]),
                               tail)))
            continue
        if err:
            refused.append((r, 'NO_FILES_ON_RECORD', err))
            continue

        sub, meta, sub_why = _subset_candidate(r.get('files'), r.get('opened_at'))
        if sub:
            weak.append((r, sub, 'FILE-SET SUBSET', meta))
            continue

        # Nothing worked. The reason is the FIRST one that applies, and the
        # subject-twin reason is the most informative when there is no object.
        # THE FILE SET IS NAMED IN EVERY REFUSAL. The first version of this
        # rewrite dropped it, and the probe arm asserting that a record matching
        # NOTHING is "named, not skipped in silence" went red -- correctly. A
        # refusal that does not say what it looked for is one a reader cannot act
        # on, and the old single-reason message did say.
        # THE CODE IS DERIVED FROM WHICH FACT BLOCKED IT, not from the prose.
        code = ('NO_OBJECT_IN_CLONE' if 'object store' in (twin_why or '')
                else 'TWIN_SUBJECT_ABSENT' if 'appears' in (twin_why or '')
                else 'TWIN_SUBJECT_AMBIGUOUS' if 'share that subject' in (twin_why or '')
                else 'NO_MATCH_ANYWHERE')
        if 'contain that file set within the window' in (sub_why or ''):
            code = code + '+SUBSET_AMBIGUOUS'
        refused.append((r, code, '%s; and %s. FILES SOUGHT: %s'
                        % (twin_why or 'no subject twin',
                           sub_why or 'no subset match',
                           sorted(set(r.get('files') or [])))))

    print('  reachable already   : %d -- not touched' % len(healthy))
    print('  reseatable          : %d  (subject twin or exact file set)'
          % len(fixable))
    print('  reseatable, WEAK    : %d  (file-set subset in a %dh window -- needs '
          '--write-weak-basis)' % (len(weak), WEAK_BASIS_WINDOW_HOURS))
    print('  REFUSED             : %d -- named below with the reason, never '
          'silently skipped' % len(refused))
    print()
    for r, newsha, basis, extra in fixable:
        print('  %-8s %s  %s -> %s   [%s]'
              % (r.get('author_session'), r.get('opened_at'),
                 (r.get('opened_at_sha') or '')[:12], newsha[:12], basis))
        if basis == 'SUBJECT TWIN':
            print('           the dangling commit\'s own subject, matched once on %s:'
                  % base)
            print('           %s' % (extra or '')[:96])
        else:
            print('           matched on the file set %s'
                  % sorted(set(r.get('files') or []))[:4])
            print('           commit subject: %s' % (extra or '')[:88])
    for r, newsha, basis, meta in weak:
        subj, when, gap = meta
        tail = (', %.1fh apart' % gap) if gap else ''
        print('  %-8s %s  %s -> %s   [%s%s]'
              % (r.get('author_session'), r.get('opened_at'),
                 (r.get('opened_at_sha') or '')[:12], newsha[:12], basis, tail))
        if basis.startswith('SUBJECT TWIN'):
            print('           the twin\'s diff covers SOME of the record\'s files '
                  'and not all of them: %s'
                  % sorted(set(r.get('files') or []))[:4])
            print('           a partial overlap is not a match and is not a '
                  'refusal either -- it is the third state, and the record may '
                  'name files from more than one commit')
        else:
            print('           the record names %s; that commit changed those AND '
                  'more' % sorted(set(r.get('files') or []))[:4])
        print('           commit subject: %s' % (subj or '')[:88])
        print('           WEAKER BASIS. --write alone will NOT apply this.')
    # NOT TRUNCATED. The first version cut the reason at 300 characters and the
    # probe caught it: the arm asserting that a record matching NOTHING is
    # "named, not skipped in silence" went red because the file list it looks for
    # was past the cut. A refusal truncated mid-diagnosis is the same defect as a
    # refusal with no diagnosis -- so these wrap instead.
    import textwrap as _tw
    for r, code, whynot in refused:
        # ── THE CODE IS PRINTED AND IS A CONTRACT; THE PROSE IS NOT.
        # A both-ways mutation on 2026-09-29 removed the ambiguity refusal and
        # exactly ONE arm caught it -- an arm asserting on the SENTENCE "it says
        # the match is ambiguous". The behavioural arm could not: with the
        # ambiguity branch gone the record fell through to the subset branch,
        # which refused it too, so the sha was unchanged and the behaviour arm
        # still passed. THE ONLY DIFFERENCE WAS THE REASON, and the reason lived
        # in prose. A stable code is the handle that makes "refused for the right
        # reason" observable without pinning a sentence.
        print('  %-8s %s  REFUSED [%s]'
              % (r.get('author_session'), r.get('opened_at'), code))
        for line in _tw.wrap(whynot, 96):
            print('           %s' % line)

    if as_json:
        # MACHINE-READABLE, so a control can assert on WHICH refusal fired
        # without asserting on a sentence.
        #
        # EMITTED BEFORE THE "nothing to reseat" EARLY RETURN, and the probe is
        # why: with the JSON printed after it, a ledger whose only dangling
        # records are all REFUSED returned before printing anything, so the arm
        # asserting on a refusal code got an empty list and failed. A
        # machine-readable report that disappears exactly when every record is
        # refused is useless for the case it exists to serve.
        print(json.dumps({
            'base': base,
            'reachable': [r.get('opened_at') for r in healthy],
            'reseatable': [{'opened_at': r.get('opened_at'), 'to': sha,
                            'basis': basis} for r, sha, basis, _e in fixable],
            'reseatable_weak': [{'opened_at': r.get('opened_at'), 'to': sha,
                                 'basis': basis} for r, sha, basis, _m in weak],
            'refused': [{'opened_at': r.get('opened_at'),
                         'session': r.get('author_session'),
                         'code': code} for r, code, _w in refused],
        }, indent=2))

    if not fixable and not weak:
        print()
        print('Nothing to reseat.' if not refused else
              'Nothing reseatable. Every dangling record above was REFUSED, '
              'which is the honest outcome: a record still naming a commit that '
              'is not on the branch is visibly broken, and a record naming the '
              'WRONG commit is not.')
        return 1 if refused else 0

    if not write:
        print()
        print('DRY RUN -- nothing was written. Add --write to repoint the %d '
              'strong-basis record(s).' % len(fixable))
        if weak:
            print('The %d WEAK-basis record(s) need --write --write-weak-basis as '
                  'well. Two flags on purpose: containment is a different claim '
                  'from equality and must not ride along on one keystroke.'
                  % len(weak))
        print('Every repointed record will carry opened_at_sha_reseated: true and')
        print('an opened_at_sha_reseat_basis naming WHICH basis was used, so a')
        print('reseated sha, a weakly reseated one and one stamped at open time')
        print('are never indistinguishable -- the same rule backfill_shas follows')
        print('for its own reconstruction.')
        return 0

    applied = 0
    for r, sha, basis, _extra in fixable:
        r['opened_at_sha_was'] = r.get('opened_at_sha')
        r['opened_at_sha'] = sha
        r['opened_at_sha_reseated'] = True
        r['opened_at_sha_reseat_basis'] = basis
        applied += 1
    weak_applied = 0
    if weak_ok:
        for r, sha, basis, _meta in weak:
            r['opened_at_sha_was'] = r.get('opened_at_sha')
            r['opened_at_sha'] = sha
            r['opened_at_sha_reseated'] = True
            r['opened_at_sha_reseat_basis'] = basis
            weak_applied += 1
    save_reviews(data)
    print()
    print('RESEATED %d record(s) on a strong basis, %d on the WEAK basis, %d '
          'refused. Commit docs/tier-a-reviews.json.'
          % (applied, weak_applied, len(refused)))
    if weak and not weak_ok:
        print('The %d weak-basis record(s) were NOT written -- pass '
              '--write-weak-basis if containment is the claim you want in the '
              'ledger.' % len(weak))
    return 0


if __name__ == '__main__':
    sys.exit(_guarded(sys.argv[1:]))
