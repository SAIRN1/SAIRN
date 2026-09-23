"""defect_register.py -- a standing log of CONFIRMED defects, with a real denominator.

    python tools/defect_register.py --report
    python tools/defect_register.py --check
    python tools/defect_register.py --reseat   # rewrite SHAs a rebase moved
    python tools/defect_register.py --add --commit SHA --app X --layer product \\
        --severity high --method fault-injection --summary "..."

── WHY IT IS DELIBERATELY NOT A COMMIT LOG ─────────────────────────────────
`git log --grep '^fix('` returns thirty entries for 2026-09-10 alone, and most
of them are NOT product defects: harness corrections, checkers whose first real
run needed tightening, my own probe mistakes. Auto-ingesting those would make
the density figure large and meaningless, and the number would then be quoted.

So a record is ADDED DELIBERATELY and carries a judgement nobody can derive --
what LAYER it was in, how severe, and above all HOW IT WAS FOUND. The
mechanical half (date, files, lines, whether the commit exists) is derived from
git, because a field a human retypes is a field that goes wrong.

── THE NUMBER IS NOT THE SIGNAL, AND THIS FILE SAYS SO IN ITS OWN OUTPUT ───
A defect density needs a denominator, and this one uses real line counts. But a
density is a fact about what has been LOOKED AT, not about what is there. The
honest signal is CONSECUTIVE ZERO-NEW-FINDING SWEEPS BY DIFFERENT METHODS over
the same files -- which is why every record names its detection method and why
`--report` prints a method x app coverage matrix beside the density.

The evidence for that is one day old: on 2026-09-10 the mutation controls found
two defects in test code that reading the assertions had not, on the same files
in the same hour. One method returning zero means that method is exhausted.

── IT STARTS ON 2026-09-09 AND IS NOT BACKFILLED BEYOND THAT ───────────────
Every record here was verified by somebody who could attest to it. Reaching
further back would mean classifying commits nobody present can vouch for, and a
register padded with guesses is worse than a short one: its size would imply a
completeness it does not have.
"""
import io
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REG = os.path.join('docs', 'defect-density-register.json')

LAYERS = ('product', 'tooling', 'test')
SEVERITIES = ('critical', 'high', 'moderate', 'low')

# ── `--app` WAS FREE TEXT, AND FREE TEXT DRIFTS (2026-09-22) ───────────────
# The one-entity-one-spelling check below `--check` has been right since it was
# written and it is a DETECTOR, not a gate: it fires AFTER the bad value is in
# the file, on the next clone to rebase through it, having blocked that clone's
# push on somebody else's typo. Measured rather than argued -- 'platform' vs
# 'PLATFORM' was normalised by hand on 2026-09-14, again on 2026-09-22, and TWO
# MORE lower-case records landed within the hour of that second fix. Five
# corrections to one value, each one a session stopping what it was doing.
#
# The vocabulary is DERIVED, not listed. A hardcoded tuple is a second place
# that has to be edited when an app ships, and the register already knows how
# to enumerate apps -- app_lines() reads `git ls-files '*.html'` for the
# denominator. Same source, so they cannot disagree.
#
# TWO ENTITIES ARE NOT FILES and are named here because nothing can derive
# them: PLATFORM is cross-app work, `tooling` is the checkers themselves.
# Both already carry records and neither has a line count, which is why the
# density block already reports them as a count with no denominator.
NON_APP_ENTITIES = ('PLATFORM', 'tooling')

# `--check` enforces the vocabulary only from this date. OLD RECORDS ARE
# EXEMPT ON PURPOSE, the same way found_by_session is: an app file deleted
# tomorrow would otherwise turn every historical record against it red, and a
# checker that goes red for a reason nobody can fix is a checker somebody
# switches off. `--add` is strict for everything, which is where drift is
# actually stopped.
APP_VOCAB_FROM = '2026-09-22'


def known_apps():
    """Every value `--app` may take, derived from the repo rather than listed.

    Returns a dict {value: why} so a refusal can print what it wanted.
    """
    out = {}
    for f in (git('ls-files', '*.html') or '').split('\n'):
        f = f.strip()
        if f and '/' not in f:
            out[os.path.splitext(f)[0]] = 'an app file in this repo'
    for e in NON_APP_ENTITIES:
        out[e] = 'a non-file entity with no line denominator'
    return out


# ── A COMMIT IN A REPOSITORY THIS ONE CANNOT SEE (2026-09-22) ──────────────
# hover2's finding, and the gap is structural rather than an oversight. The
# hover auditor's own tooling lives OUTSIDE every clone by design -- the
# separation that makes its audits independent is the same separation that
# puts its commits beyond `git rev-parse`. `--add` requires `--commit` and
# `--check` requires every commit to resolve, so a real defect found and fixed
# in that repo had NO WAY INTO THIS FILE. The register's own coverage figure
# was therefore understating the hover channel by however many such fixes
# exist, and nothing in the file said so.
#
# THE FORMAT IS DELIBERATELY UGLY. `external:<repo-label>:<sha>` cannot be
# mistaken for a sha at a glance, cannot be pasted into `git show` and appear
# to work, and sorts away from real citations in any dump of the file. A
# prettier format would be one somebody reads past.
#
# AND IT IS NOT A CITATION THIS FILE CAN CHECK. That is the whole cost and it
# is stated in three places -- here, in the refusal text, and in `--check`'s
# own summary, which counts them SEPARATELY rather than folding them into
# "every commit resolves". A register that reported an unverifiable pointer
# with the same confidence as a verified one would be worth less than one that
# refused them outright.
EXTERNAL_RE = re.compile(r'^external:([a-z0-9][a-z0-9._-]{0,40}):([0-9a-f]{7,40})$')


def is_external(sha):
    return bool(EXTERNAL_RE.match(str(sha or '').strip()))

# ── WHAT THE FOUR WORDS MEAN (added 2026-09-15, and the evidence is measured)
# `layer` and `injection_phase` each carry a paragraph explaining what they are.
# SEVERITY CARRIED NOTHING -- four words and no definitions -- and two blind
# review rounds measured what that costs.
#
# tools/blind_review.py withholds the recorded severity, takes a reviewer's own
# judgment first, and only then reveals. Across two rounds, 14 records:
# **6 AGREED, 8 DID NOT -- and the 8 split 4 MORE severe and 4 LESS.**
#
# THE SPLIT IS THE FINDING, NOT THE RATE. A one-sided split would be a
# CALIBRATION OFFSET -- two people using the same scale from different places,
# fixed by agreeing an anchor. An even split is DISPERSION: the same scale
# applied inconsistently because it has no definition to be consistent with.
# Those need opposite fixes and an agreement rate alone cannot tell them apart.
#
# So the definitions below are written against CONSEQUENCE IF THE DEFECT
# REACHES A USER, which is the question every other tier on this platform asks:
#
#   critical  Money moves wrongly, a record is destroyed with no recovery, or
#             an unauthorised party reaches data. Reachable on a real
#             deployment by a real caller, not only in principle.
#   high      A silent failure that shows SUCCESS, a control that does not
#             refuse what it exists to refuse, or a platform-wide defect whose
#             trigger is a condition that really occurs. Recoverable, but the
#             user is not told.
#   moderate  A visible wrong answer, a refusal a user cannot act on, or a
#             control that stopped testing what it claims to test. Somebody
#             notices.
#   low       A cosmetic or documentation defect, or a wrong number in a report
#             nobody gates on.
#
# ── THE 85 RECORDS THAT PREDATE THIS ARE **NOT** RE-TIERED ─────────────────
# Stated because it matters to anything that reads the field: every record
# before 2026-09-15 was assigned with no definition to assign against, so the
# corpus is MIXED. tools/defect_budget_policy.py weights by severity, which
# means its numbers span two vocabularies. Re-tiering 85 records is a
# governance decision with a real cost either way and is not one a definition
# comment gets to make silently.
SEVERITY_DEFINED_FROM = '2026-09-15'
# The day found_by_session began to be required. Records before it are not
# back-filled: inventing which instance found a defect nobody re-attributed
# is the manufactured agreement this register refuses everywhere else.
SESSION_FIELD_FROM = '2026-09-22'

# ── WHERE THE DEFECT WAS INJECTED (item 77, added 2026-09-14) ──────────────
# `detection_method` records how a defect was REMOVED. This records where it
# was PUT IN. Two different questions, and only both together make an
# injection-vs-removal matrix mean anything: "code review found 25 defects" is
# a raw count until you can also say which phase those 25 came from, and
# therefore which phase is worth attacking.
#
# DELIBERATELY ORTHOGONAL TO `layer`. Layer says WHERE the defect lives
# (product / tooling / test); phase says WHEN it entered. A test file can carry
# a coding defect or a design defect, and collapsing the two axes would make
# the matrix unreadable in exactly the way one label per app made
# CRITICALITY-TIERS.md stop discriminating.
#
# THE DISCRIMINATOR, written down so it decides cases instead of describing
# them -- ask in this order and stop at the first that answers:
#   requirement  fixing it changes WHAT the thing is supposed to do
#   design       the code faithfully implements a plan that could not work;
#                the fix needs a different structure, not a corrected line
#   coding       the plan was right, the expression is not
#   config       the fix is outside the source entirely -- a grant, an env var,
#                a migration nobody ran, a clone's own git config
#   unknown      none of the above honestly fits
#
# `unknown` IS A REAL ANSWER AND REQUIRES A NOTE, for the same reason
# `not-citable` does: a vocabulary with no honest escape hatch does not produce
# accurate data, it produces data pushed into the nearest bin. A bare
# `unknown` is a silence, not a decision.
# ── WHICH CHECKPOINT CAUGHT IT (item 63, added 2026-09-14) ────────────────
# `detection_method` says WHICH TECHNIQUE found a defect. This says WHAT KIND OF
# CHECKPOINT that technique is, which is the question behind "are we relying on
# people reading code, or on something that runs".
#
#   human-read         a person read it. No automated checkpoint covered it.
#   automated-checker  a checker, probe or mutation control found it.
#   monitoring         it was observed in RUNNING behaviour -- live verification
#                      or a user report. Nothing static could have seen it.
#   unknown            requires a note.
#
# DERIVED FROM detection_method BY A FIXED RULE, not judged per record -- the
# mapping is in CHECKPOINT_OF below and there is nothing to get wrong twice.
#
# THE LIMIT, AND IT IS THE WHOLE HONEST FRAME: this measures the checkpoint that
# DID catch each defect, not the one that SHOULD have. Those differ exactly
# where a gate ought to exist and does not, so this UNDER-COUNTS gaps by
# construction. It is the closest thing the register's existing fields can
# support, and calling it the other thing would be a fabrication.
#
# AND IT CANNOT SPLIT GATE FROM REPORT-ONLY. A record names the technique, never
# the tool, so "a checker found it" cannot be resolved into "a blocking gate
# found it". Adding a `found_by_tool` field is the next thing somebody should do
# and is deliberately not invented here.
# ── WHICH TOOL FOUND IT (added 2026-09-14) ────────────────────────────────
# Item 63 could say "a checker found it" and could NOT say whether that checker
# BLOCKS. A record named the technique and never the tool, so the one question
# behind the whole checkpoint split -- are we stopped before a push, or merely
# told afterwards -- was unanswerable. This is that field.
#
# REQUIRED exactly when the checkpoint is `automated-checker`, and REFUSED
# otherwise: a code review has no tool, and inviting one would produce a column
# of plausible-looking names nobody could check.
#
# `unknown` is allowed and is honest for the backfill: 2026-09-14's records
# name their tool in the summary or not at all, and inventing one for the rest
# would be exactly the manufactured agreement the citation field is careful to
# avoid. The report prints the unknown share above the split.
TOOL_UNKNOWN = 'unknown'


def tool_required(method):
    return checkpoint_of(method) == 'automated-checker'


# ── WHICH HOVER INSTANCE FOUND IT (2026-09-22) ──────────────────────
# `hover-audit` names a POPULATION -- the fifth role, structurally separate
# from the four build agents -- and that population currently runs as TWO
# concurrent instances, hover and hover2. Without this field their findings
# are indistinguishable in the register, which matters for the one thing the
# second instance exists to provide: a PEER CHECK. Two records of the same
# defect are corroboration when two instances found it and a duplicate when
# one found it twice, and nothing here could tell those apart.
#
# REQUIRED-OR-REFUSED, exactly like found_by_tool above, and for the reason
# this file has now recorded three times in its own words: a field that is
# optional at the moment of recording is a field that stays empty. It is
# refused for every other method so the column cannot fill with plausible
# names nobody can check -- a build agent's own review is already identified
# by the obligation record, not by this field.
#
# THE VALUE IS NOT A CLOSED LIST. A third instance would be `hover3` and
# freezing the vocabulary at two would refuse it; the shape is checked
# instead, which is enough to keep the column meaningful without pinning a
# count that is somebody else's to change.
HOVER_SESSION_SHAPE = re.compile(r'^hover[0-9]*$')


def session_required(method):
    return method == 'hover-audit'


CHECKPOINTS = ('human-read', 'automated-checker', 'monitoring', 'unknown')
CHECKPOINT_OF = {
    'code-review': 'human-read',
    'independent-review': 'human-read',
    # A read, adversarially, of somebody else's diff -- the same CHECKPOINT
    # kind as the two above even though it is a different POPULATION. The two
    # axes are deliberately separate: `detection_method` says which channel
    # found it, `checkpoint_of` says whether a person or a program did, and
    # this role is a person-shaped check run by a different agent.
    'hover-audit': 'human-read',
    'static-checker': 'automated-checker',
    'mutation-testing': 'automated-checker',
    'fault-injection': 'automated-checker',
    'probe-control': 'automated-checker',
    'traceability-matrix': 'automated-checker',
    'live-verification': 'monitoring',
    'user-report': 'monitoring',
}


def checkpoint_of(method):
    """The checkpoint kind for a detection method. Unknown methods are NOT
    silently bucketed -- a new method added to METHODS without a row here comes
    back 'unknown' and --check says so, rather than being folded into whichever
    bucket happened to look closest."""
    return CHECKPOINT_OF.get(method, 'unknown')


PHASES = ('requirement', 'design', 'coding', 'config', 'unknown')

# How good the phase call is. Same shape as citation_confidence, and for the
# same reason: most of these are read from a one-line summary rather than from
# the diff, and a register that cannot say so would be overstating itself.
#   stated    the record's own summary names the defective construct
#   inferred  the phase is a judgement about the summary, not a quote from it
PHASE_CONFIDENCES = ('stated', 'inferred')
# Every method that has actually found something on this platform. Named rather
# than free text, so the coverage matrix means something -- and extended
# deliberately when a genuinely new method finds its first defect.
METHODS = (
    'code-review', 'mutation-testing', 'fault-injection', 'static-checker',
    'live-verification', 'independent-review', 'traceability-matrix',
    'probe-control', 'user-report',
    # ── THE FIFTH AGENT'S OWN CHANNEL (added 2026-09-21) ──────────────────
    # The hover auditor is not one of the four build agents and its findings
    # are not `independent-review`: that value is the build agents' PEER
    # channel, four sessions reviewing each other's diffs, and folding a
    # structurally separate third data source into it would make the coverage
    # matrix say there is one reviewing population where there are two.
    #
    # ADDED BY A BUILD AGENT, WHICH IS THE POINT. .claude/skills/
    # sairn-hover-auditor/SKILL.md has said since 2026-09-14 that this enum
    # has no hover-audit value, that adding one is "a code edit this role does
    # not make itself", and that findings needing the tag should be HELD and
    # the fix routed here. So the absence of this string was holding real
    # findings out of the register -- and a finding sitting in chat because a
    # tuple is one entry short is the quietest kind of missing data there is.
    'hover-audit',
)

# ── THE STANDING-RULE CITATION, added 2026-09-13 ───────────────────────────
# `tools/fmea_prediction_check.py` has scored ZERO since the day it was written
# and says so in its own docstring: matching a saved risk draft to a defect that
# then happened is by RULE CITATION ONLY, because the first matcher scored 38%
# on three-word overlap AND EVERY ONE OF THOSE FIVE HITS WAS A FALSE POSITIVE.
# Its answer was blocked on this field, not on its own logic.
#
# THREE CONFIDENCES, NOT TWO, AND THE THIRD IS THE POINT. A register that could
# only say "cites rule X" would push every awkward record into a citation it
# does not really instantiate, and the FMEA scorer would then match on
# manufactured agreement -- the 38% arriving through the data instead of the
# matcher. So `not-citable` is a first-class answer, it requires a note saying
# why, and 6 of 54 records carry it.
CONFIDENCES = ('clean', 'arguable', 'not-citable')
RULES_DOC = os.path.join('docs', 'SAIRN-PROCESS-RULES.md')

# ── ITEM 75: COOK'S CRITIQUE, AND WHY THERE IS NO `root_cause` FIELD ────────
# "Complex systems contain changing mixtures of failures latent within them...
# Post-accident attribution to a 'root cause' is fundamentally wrong. Because
# overt failure requires multiple faults, there is no isolated 'cause' of an
# accident." -- Richard Cook, How Complex Systems Fail, points 4 and 7.
#
# A CAPA form with one ROOT CAUSE box and one CORRECTIVE ACTION box does not
# merely record less. It ASSERTS that fixing the named thing closes the door,
# and the closure is the part that is wrong: the other contributors are still
# there, still latent, and now carry a signed-off record saying the incident is
# handled. That is the shape this register would have grown into.
#
# So: a LIST, never a field. `root_cause` is refused by name in --check rather
# than merely absent, because absence is a thing somebody adds back.
#
# EVERY RECORD WITH FACTORS ALSO STATES WHAT IS STILL OPEN. A corrective action
# is evidence about one contributor; it is not evidence about recurrence, and
# the register must not be readable as if it were.
#
# A SINGLE FACTOR IS ALLOWED and must say why it is single. Cook's point is not
# that every defect has three causes -- it is that a one-line cause is a claim
# and claims get stated, not assumed. Forcing a second factor would fabricate
# one, which is worse.
FACTOR_KINDS = (
    'technical',            # the code did the wrong thing
    'process',              # the way the work was done allowed it
    'detection',            # why nothing caught it, given it was there
    'latent-condition',     # a standing condition that made it possible
)
ACTION_STATES = (
    'done',                 # something changed; `action` says what
    'planned',              # named, not yet done
    'declined',             # deliberately not acted on; `note` says why
    'not-actionable',       # no action would address it; `note` says why
)


def factor_problems(rec, where_id):
    """Everything wrong with `rec`'s contributing factors, as a list of strings.

    ── ONE COPY, CALLED FROM BOTH ENDS (item 75, 2026-09-16) ────────────────
    This was inline in `--check`. It is a function because `--add` now applies
    the SAME rules at the moment of recording, and two copies of a validation
    that must agree is how they stop agreeing -- a record accepted by --add and
    refused by --check would be a register that cannot be both written and read.

    Returns [] when the record carries no factors at all. Whether ABSENCE is
    acceptable is the caller's decision and deliberately not this function's:
    --check tolerates it on the old records, --add refuses it on new ones, and
    that asymmetry is the whole of item 75's remaining half.
    """
    cf = rec.get('contributing_factors')
    if cf is None:
        return []
    bad = []
    if not isinstance(cf, list) or not cf:
        return ['%s -- contributing_factors is present but not a non-empty list'
                % where_id]
    for i, f in enumerate(cf):
        where = '%s factor %d' % (where_id, i + 1)
        if not isinstance(f, dict) or not str(f.get('factor') or '').strip():
            bad.append('%s -- no factor text' % where)
            continue
        if f.get('kind') not in FACTOR_KINDS:
            bad.append('%s -- kind %r is outside %s'
                       % (where, f.get('kind'), (FACTOR_KINDS,)))
        st = f.get('action_status')
        if st not in ACTION_STATES:
            bad.append('%s -- action_status %r is outside %s'
                       % (where, st, (ACTION_STATES,)))
        elif st in ('done', 'planned') and not str(f.get('action') or '').strip():
            bad.append('%s -- action_status %r with no action. A status without '
                       'the thing that was done is the CAPA box this field '
                       'replaces.' % (where, st))
        elif st in ('declined', 'not-actionable') and not str(
                f.get('note') or '').strip():
            bad.append('%s -- action_status %r with no note. Deciding not to '
                       'act is a decision and gets written down.' % (where, st))
    # A SINGLE FACTOR IS ALLOWED AND MUST SAY WHY IT IS SINGLE.
    if len(cf) == 1 and not str(rec.get('single_factor_note') or '').strip():
        bad.append('%s -- one contributing factor and no single_factor_note. '
                   'One cause is a CLAIM about a system, not the default shape '
                   'of one, so it is stated rather than assumed.' % where_id)
    # AND WHAT THE ACTIONS DO NOT CLOSE.
    if not str(rec.get('recurrence_open') or '').strip():
        bad.append('%s -- contributing factors with no recurrence_open. A '
                   'corrective action is evidence about one contributor and '
                   'never about recurrence; without this the record reads as '
                   'closed.' % where_id)
    return bad


def known_rules():
    """Section ids parsed out of the process rules themselves.

    DERIVED, NOT LISTED. A hand-kept vocabulary of rule ids is a second copy of
    the rules document, and this repo has corrected that exact shape in the
    Guardian App File Map seven times. A citation naming a section that does not
    exist is a finding; a citation naming one that was renumbered should fail
    loudly rather than sit there looking checked.

    Returns None when the document cannot be read -- the caller must treat that
    as COULD NOT CHECK, never as "every citation is fine" (PR 1.11).
    """
    p = os.path.join(REPO, RULES_DOC)
    if not os.path.isfile(p):
        return None
    try:
        src = io.open(p, encoding='utf-8').read()
    except Exception:
        return None
    ids = set(re.findall(r'^###\s+(\d+\.\d+)\s', src, re.M))
    ids.update(re.findall(r'^##\s+(Part \d+)\b', src, re.M))
    return ids or None


def git(*a):
    r = subprocess.run(['git', '-C', REPO] + list(a), capture_output=True, text=True, encoding='utf-8', errors='replace')
    return r.stdout.strip() if r.returncode == 0 else None


def load():
    p = os.path.join(REPO, REG)
    if not os.path.isfile(p):
        return {'started': '2026-09-09',
                'note': 'Confirmed defects only. See tools/defect_register.py '
                        'for why this is not a commit log and why the density '
                        'is not the signal.',
                'records': []}
    return json.load(io.open(p, encoding='utf-8'))


def save(d):
    p = os.path.join(REPO, REG)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    io.open(p, 'w', encoding='utf-8', newline='').write(
        json.dumps(d, indent=2, sort_keys=False) + '\n')


# ── WHERE THE DEFECT CAME IN, AS A COMMIT (item 66's prerequisite) ────────
# IBNR -- estimating how many defects exist that nobody has found -- needs a LAG
# DISTRIBUTION: injection date to discovery date. `injection_phase` says when in
# the LIFECYCLE; this says when in TIME, and the two are different fields.
#
# OPTIONAL, WITH A REQUIRED REASON WHEN OMITTED. Exactly the shape of
# `--rule not-citable`, and for the same reason: MANDATORY WOULD PRODUCE
# GUESSES, and silently optional would leave it empty, which is what happened to
# detection_method before item 2/24 measured 1 of 52.
#
# CHEAP AT RECORD TIME AND ONLY THEN. Whoever fixes a defect has just read the
# code and usually knows, or finds it with one `git log -S`. It is NOT honestly
# backfillable -- reconstructing an injection point by blame months later
# produces a lag distribution built from guesses, which is worse than no
# distribution at all. The 67 records that predate this field say so in their
# own reason string rather than carrying an invented sha.
def lag_days(inj_date, fix_date):
    """Whole days between two YYYY-MM-DD strings, or None if either is unusable."""
    import datetime
    try:
        a = datetime.date(*[int(x) for x in str(inj_date)[:10].split('-')])
        b = datetime.date(*[int(x) for x in str(fix_date)[:10].split('-')])
    except Exception:                                          # noqa: BLE001
        return None
    return (b - a).days


# Files that are BOOKKEEPING or GENERATED -- a commit touching only these did
# not fix anything, so it cannot be the commit a defect record cites. Listed
# rather than pattern-guessed, because the point is to be sure about the ones
# that actually recur here.
BOOKKEEPING = (
    '.claude/claims/',
    'SAIRN-ACTIVE-WORK-',
    'docs/defect-density-register.json',
    'docs/traceability-matrix.md',
    'docs/MASTER-PLAN.md',
    'docs/TOOLING-INVENTORY.md',
    'docs/SAIRN-OPEN-WORK-INDEX.md',
)


def is_bookkeeping_only(files):
    """True when every changed path is bookkeeping or a generated document.

    ── WHY THIS GUARD EXISTS, MEASURED AT THREE OCCURRENCES IN ONE EVENING ────
    `--commit $(git rev-parse HEAD)` READS AS "this work" AND MEANS "whatever
    landed last". The fix has to be committed before it has a sha to cite, and
    the natural moment to record a finding is while it is fresh -- so the sha
    taken is the tip at that moment, which in a five-clone repo is frequently
    somebody else's commit.

    2026-09-16, same session, same person:
      * a finding filed against `chore(claims): cc releases cc`
      * two filed against `chore(docs): regenerate for the witness mint suite`
      * and a third near-miss, because amending the fix commit to correct the
        citation CHANGES THE SHA BEING CITED -- a citation can only be written
        after the thing it cites is final.

    NEITHER EXISTING CHECK CAN SEE IT. `--check` passes: every field is in
    vocabulary and the commit exists. `--reseat` correctly does nothing: it
    repairs shas a rebase made DANGLING, and these resolved and were reachable
    the whole time. They were not broken, they were WRONG, and that needed a
    different question asked at write time.

    THE PREDICATE IS "DID THIS COMMIT CHANGE ANYTHING THAT COULD CARRY A
    DEFECT", not a subject-prefix match. A `chore(` subject is a hint and
    nothing more -- real fixes have shipped under `chore(` on this platform,
    which `register_feed_gate.py`'s own open-work row records. The file list is
    the fact.
    """
    return bool(files) and all(
        any(f.startswith(b) for b in BOOKKEEPING) for f in files)


def derive(sha, external=None):
    """The mechanical half, from git. A field a human retypes goes wrong.

    An EXTERNAL citation has no mechanical half -- that is what makes it
    external -- so the caller supplies what git would have, and the line counts
    are recorded as 0 with the files list EMPTY rather than guessed at. The
    zeros are load-bearing: `--add`'s bookkeeping-only detector reads `files`,
    and the density block divides by lines that live in THIS repo. A fabricated
    line count would deflate a defect rate with a number nobody measured, which
    is the one thing this file exists to stop.
    """
    if is_external(sha):
        return {'commit': str(sha).strip(), 'date': external['date'],
                'subject': external['subject'], 'files': [],
                'lines_added': 0, 'lines_removed': 0,
                'external': {'repo': EXTERNAL_RE.match(str(sha).strip()).group(1),
                             'sha': EXTERNAL_RE.match(str(sha).strip()).group(2),
                             'note': external['note']}}
    full = git('rev-parse', sha)
    if not full:
        return None
    date = git('log', '-1', '--format=%cI', full)
    subject = git('log', '-1', '--format=%s', full)
    stat = git('show', '--numstat', '--format=', full) or ''
    files, added, removed = [], 0, 0
    for line in stat.split('\n'):
        parts = line.split('\t')
        if len(parts) == 3 and parts[0].isdigit() and parts[1].isdigit():
            added += int(parts[0])
            removed += int(parts[1])
            files.append(parts[2])
    return {'commit': full[:12], 'date': (date or '')[:10], 'subject': subject,
            'files': files, 'lines_added': added, 'lines_removed': removed}


def app_lines():
    """The denominator, measured rather than estimated."""
    out = {}
    for f in (git('ls-files', '*.html') or '').split('\n'):
        if f.strip() and '/' not in f:
            p = os.path.join(REPO, f)
            try:
                out[os.path.splitext(f)[0]] = sum(
                    1 for _ in io.open(p, encoding='utf-8', errors='replace'))
            except IOError:
                pass
    return out


# ── EVERY PROSE FIELD GETS A FILE ROUTE, NOT JUST ONE (2026-09-23) ─────────
# TOOL-BUGS ITEM 5, FOURTH INSTANCE, MEASURED IN THIS FILE. `--add` had no
# file route, so a summary typed at a shell lost three backtick spans to
# command substitution and landed reading:
#
#   "folds of the shape , seven of them money"
#   "the guard never fires and  concatenates"
#   "a fragment as common as  cannot separate"
#
# The words deleted were the CODE SHAPES -- the fold, the operator, the
# fragment -- which is the specific damage this class does: a summary about a
# coercion bug with the three coercion terms removed still reads as English
# and means nothing. Repaired in place afterwards, with the loss recorded.
#
# A SINGLE `--body-file` WOULD NOT HAVE BEEN ENOUGH, and that is why this is
# not a copy of tools/tier_a_review_gate.py's flag. `--add` takes EIGHT free
# text fields -- summary, rule-note, recurrence-open, injection-unknown,
# phase-note, single-factor-note, limits and the JSON of --factors -- and any
# of them can carry a backtick. One flag would have closed one of eight.
#
# SO THE ROUTE IS A CONVENTION AT THE ARGUMENT READER: any `--x` may be given
# as `--x-file <path>` instead. Nothing is enumerated, so a field added
# tomorrow has the route the day it exists rather than the day somebody
# remembers to add it.
#
# READ AS BYTES AND DECODED EXPLICITLY, deliberately: a file written by one
# session and read by another is where an encoding assumption becomes a
# corrupted record, and this platform has paid for cp1252 defaults 358 times
# in one sweep.
#
# BOTH FORMS AT ONCE IS A REFUSAL, and that is a deliberate difference from
# tier_a_review_gate, which silently prefers the file. Two values for one
# field means one of them was meant and the tool cannot know which; picking
# either is a guess about the author's intent, printed as a record.
class ArgFile(Exception):
    pass


def read_text_arg(argv, name):
    """The `--name-file` value for `--name`, or None if it was not given.

    Raises ArgFile with a reason for anything it cannot honestly return --
    absent, unreadable, not UTF-8, empty. An absent body is NOT an empty one,
    and a register that stored the difference as `""` would be recording a
    field nobody wrote.
    """
    flag = name + '-file'
    if flag not in argv:
        return None
    if name in argv:
        raise ArgFile('both %s and %s were given. Two values for one field '
                      'means one of them was meant and this cannot know '
                      'which -- pass one.' % (name, flag))
    i = argv.index(flag)
    if len(argv) <= i + 1:
        raise ArgFile('%s needs a path' % flag)
    path = argv[i + 1]
    if not os.path.isfile(path):
        raise ArgFile('%s %r does not exist. Nothing was recorded -- an '
                      'absent value is not an empty one.' % (flag, path))
    try:
        with open(path, 'rb') as fh:
            raw = fh.read()
    except OSError as e:
        raise ArgFile('%s %r could not be read: %s' % (flag, path, e))
    try:
        text = raw.decode('utf-8')
    except UnicodeDecodeError as e:
        raise ArgFile('%s %r is not UTF-8 (%s). Refusing rather than storing '
                      'a lossy decode.' % (flag, path, e))
    if not text.strip():
        raise ArgFile('%s %r is empty. A field with no content is a blank, '
                      'not a record.' % (flag, path))
    return text.strip()


def cmd_add(argv):
    def opt(name, required=True):
        # THE FILE ROUTE IS TRIED FIRST so `--x-file` works for every `--x`
        # without any field being listed anywhere. See read_text_arg().
        try:
            from_file = read_text_arg(argv, name)
        except ArgFile as e:
            print('%s' % e)
            sys.exit(2)
        if from_file is not None:
            return from_file
        if name in argv:
            return argv[argv.index(name) + 1]
        if required:
            print('missing %s (or %s-file <path>)' % (name, name))
            sys.exit(2)
        return ''

    sha, app = opt('--commit'), opt('--app')
    # ── THE APP VOCABULARY, ENFORCED AT THE POINT OF WRITING ───────────────
    # Strict and case-SENSITIVE. 'platform' is refused and the message names
    # 'PLATFORM', because the whole cost of this drift was five separate
    # sessions each discovering the difference after the fact.
    apps = known_apps()
    if app not in apps:
        near = [k for k in apps if k.lower() == str(app).lower()]
        print('unknown --app %r.' % app)
        if near:
            print('  Did you mean %r? This file is case-sensitive on purpose: '
                  'one entity with two spellings is two entities to every '
                  'per-app figure in it.' % near[0])
        print('  Allowed (derived from `git ls-files \'*.html\'` plus the two '
              'non-file entities, so it cannot drift from the denominator):')
        for k in sorted(apps, key=lambda s: (s not in NON_APP_ENTITIES, s)):
            print('    %-24s %s' % (k, apps[k]))
        return 2
    # ── AN EXTERNAL CITATION CARRIES ITS OWN THREE FIELDS ──────────────────
    ext = None
    ext_note = opt('--external-note', required=False)
    ext_date = opt('--external-date', required=False)
    ext_subject = opt('--external-subject', required=False)
    if is_external(sha):
        missing = [n for n, v in (('--external-note', ext_note),
                                  ('--external-date', ext_date),
                                  ('--external-subject', ext_subject))
                   if not str(v).strip()]
        if missing:
            print('an external citation cannot be derived from git, so it has '
                  'to be told: %s' % ', '.join(missing))
            print('  --external-subject is the commit subject in that repo; '
                  'it is what a reader searches for when they go and look.')
            print('  --external-note says WHERE that repo is and why the '
                  'commit is not in this one. At least 40 characters: a bare '
                  '"external" is the silence this format exists to replace.')
            return 2
        if len(str(ext_note).strip()) < 40:
            print('--external-note is %d characters. A pointer this file '
                  'cannot verify is only as good as the sentence telling a '
                  'reader where to go and look; 40 is the floor.'
                  % len(str(ext_note).strip()))
            return 2
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', str(ext_date).strip()):
            print('--external-date must be YYYY-MM-DD -- it feeds the '
                  'discovery-lag and per-period figures like any other date.')
            return 2
        # NO LINE DENOMINATOR EXISTS for a file that is not in this repo, so an
        # external record may only be filed against an entity that already has
        # none. Otherwise it would enter a per-app rate as a numerator with
        # nothing under it, which is the exact arithmetic the density block was
        # rewritten in 2026-09-13 to stop.
        if app not in NON_APP_ENTITIES:
            print('an external citation must use one of %s, not %r. The per-app '
                  'defect rate divides by lines counted in THIS repo, and a '
                  'commit in another one contributes none -- filing it against '
                  'an app file would add a numerator with no denominator.'
                  % (NON_APP_ENTITIES, app))
            return 2
        ext = {'note': str(ext_note).strip(), 'date': str(ext_date).strip(),
               'subject': str(ext_subject).strip()}
    layer, sev, method = opt('--layer'), opt('--severity'), opt('--method')
    summary = opt('--summary')
    # REQUIRED, not optional, and that is the whole fix. The field was absent
    # for 54 records because nothing ever asked for it, and `--check` cannot
    # demand of old records what `--add` never collected. Pass
    # `--rule not-citable` when no standing rule names the shape -- with a
    # `--rule-note` saying so. Refusing to record a defect because no rule fits
    # would be worse than the gap this closes.
    rule = opt('--rule')
    note = opt('--rule-note', required=False)
    # REQUIRED, like --rule and for the same reason: a field that is optional
    # at the moment of recording is a field that stays empty, and --check
    # cannot demand of a record what --add never collected. Pass
    # `--phase unknown` with a `--phase-note` when none of the four honestly
    # fits; refusing to record a defect because no phase fits would be worse
    # than the gap this closes.
    # REQUIRED when a tool did the finding, REFUSED when one did not.
    found_by = opt('--found-by-tool', required=False)
    # REQUIRED when the hover auditor found it, REFUSED otherwise -- the
    # same shape as --found-by-tool one line up, so the two cannot drift.
    found_session = opt('--found-by-session', required=False)
    inj = opt('--injection-commit', required=False)
    inj_unknown = opt('--injection-unknown', required=False)
    if bool(str(inj).strip()) == bool(str(inj_unknown).strip()):
        print('pass EXACTLY ONE of --injection-commit <sha> or '
              '--injection-unknown "<why>". Both, or neither, is how this field '
              'would quietly become empty -- which is what happened to '
              'detection_method before it was measured at 1 of 52.'); return 2
    phase = opt('--phase')
    phase_note = opt('--phase-note', required=False)
    # ── ITEM 75's REMAINING HALF, 2026-09-16 ───────────────────────────────
    # The validation below `--check` has been right since it was written and
    # could only ever inspect the records that happened to carry factors: FIVE
    # of eighty-five. `--add` never asked. This file already says, twice, in
    # its own words, why that ends one way -- "a field that is optional at the
    # moment of recording is a field that stays empty, and --check cannot
    # demand of a record what --add never collected." It was true of --rule at
    # 54 records and of --phase, and contributing_factors is the third.
    #
    # OLD RECORDS STAY EXEMPT AND THAT JUDGEMENT IS NOT BEING REVERSED:
    # back-filling a cause nobody re-investigated is how a CAPA form fills with
    # guesses. This asks at the one moment somebody has actually looked.
    #
    # THE ESCAPE HATCH IS DELIBERATE, and is the same shape as `--rule
    # not-citable` and `--phase unknown`: refusing to record a real defect
    # because the factors are not worked out yet would lose the record, which
    # is strictly worse than the gap being closed.
    factors_json = opt('--factors', required=False)
    factors_unknown = opt('--factors-unknown', required=False)
    if bool(str(factors_json).strip()) == bool(str(factors_unknown).strip()):
        print('pass EXACTLY ONE of --factors \'<json list>\' or '
              '--factors-unknown "<why not yet>". A failure in a system like '
              'this has contributors, plural; recording none of them is a '
              'claim and it gets stated rather than left blank.\n'
              '  each factor: {"factor": "...", "kind": one of %s,\n'
              '                "action_status": one of %s,\n'
              '                "action": "..." | "note": "..."}\n'
              '  with --factors you must also pass --recurrence-open "<what '
              'the actions do NOT close>",\n'
              '  and --single-factor-note "<why one>" if you pass exactly one.'
              % (', '.join(FACTOR_KINDS), ', '.join(ACTION_STATES)))
        return 2
    factors = None
    if str(factors_json).strip():
        try:
            factors = json.loads(factors_json)
        except ValueError as e:
            print('--factors is not valid JSON: %s' % e); return 2
    recurrence_open = opt('--recurrence-open', required=False)
    single_note = opt('--single-factor-note', required=False)
    if phase not in PHASES:
        print('--phase must be one of %s' % (PHASES,)); return 2
    if phase == 'unknown' and not str(phase_note).strip():
        print('--phase unknown requires --phase-note. A bare unknown is a '
              'silence, not a decision.'); return 2
    # `stated` is a claim that the SUMMARY names the defective construct, so it
    # is checked against the summary rather than taken on trust.
    phase_conf = opt('--phase-confidence', required=False) or 'inferred'
    if phase_conf not in PHASE_CONFIDENCES:
        print('--phase-confidence must be one of %s' % (PHASE_CONFIDENCES,)); return 2
    if layer not in LAYERS:
        print('--layer must be one of %s' % (LAYERS,)); return 2
    if sev not in SEVERITIES:
        print('--severity must be one of %s' % (SEVERITIES,)); return 2
    if method not in METHODS:
        print('--method must be one of %s' % (METHODS,)); return 2
    if tool_required(method) and not str(found_by).strip():
        print('--found-by-tool is required for %r, because it maps to '
              'automated-checker and the whole point of the field is to say '
              'WHICH checker -- pass %r if the record genuinely does not know.'
              % (method, TOOL_UNKNOWN)); return 2
    if not tool_required(method) and str(found_by).strip():
        print('--found-by-tool is not accepted for %r: %s found it, not a tool. '
              'A column of plausible names nobody can check is worse than an '
              'empty one.' % (method, checkpoint_of(method))); return 2
    if session_required(method) and not str(found_session).strip():
        print('--found-by-session is required for %r. The hover auditor runs as '
              'more than one instance, and two records of one defect are '
              'CORROBORATION when two instances found it and a DUPLICATE when one '
              'found it twice -- which is the whole point of the second instance '
              'and is unreadable without this field.' % method); return 2
    if not session_required(method) and str(found_session).strip():
        print('--found-by-session is not accepted for %r: it identifies WHICH hover '
              'instance found something, and a build agent\'s review is already '
              'identified by its obligation record.' % method); return 2
    if str(found_session).strip() and not HOVER_SESSION_SHAPE.match(str(found_session).strip()):
        print('--found-by-session %r does not look like a hover instance. Expected '
              'hover, hover2, hover3... -- the shape is checked rather than a closed '
              'list, so a third instance needs no code change here.'
              % str(found_session).strip()); return 2
    if rule == 'not-citable':
        rules, conf = [], 'not-citable'
    else:
        rules, conf = [rule], ('arguable' if note else 'clean')
        known = known_rules()
        if known is None:
            # PR 1.11. The vocabulary comes from a document; if that document
            # cannot be read the citation CANNOT BE CHECKED, and accepting it
            # would record an unverified claim as a verified one.
            print('COULD NOT READ %s, so --rule cannot be validated. Not '
                  'recording an unchecked citation.' % RULES_DOC); return 2
        if rule not in known:
            print('--rule %r is not a section in %s. Known: %s'
                  % (rule, RULES_DOC, ', '.join(sorted(known)))); return 2
    if conf != 'clean' and not note:
        print('--rule-note is required unless the citation is clean'); return 2
    d = derive(sha, ext)
    if not d:
        print('no such commit: %s' % sha)
        if re.match(r'^external', str(sha).strip()):
            print('  That looks like an attempt at an external citation. '
                  'The format is external:<repo-label>:<sha> -- lower-case '
                  'label, 7-40 hex characters, no spaces.')
        return 2
    # ── THE $(git rev-parse HEAD) TRAP. See is_bookkeeping_only(). ──────────
    # REFUSES rather than warns, because a warning printed above a `registered`
    # line is a warning nobody reads -- and the whole failure mode here is a
    # record that looks correct to every later check. The override exists and
    # requires a real sentence, the same decision `--rule not-citable` and the
    # `no-defect-record:` commit trailer already made on this platform: a
    # vocabulary with no honest escape hatch does not produce honesty, it
    # produces a forced value.
    if is_bookkeeping_only(d['files']) and not str(
            opt('--commit-is-bookkeeping', required=False)).strip():
        print('REFUSED: %s touches only bookkeeping or generated files:\n  %s'
              % (d['commit'], '\n  '.join(d['files'][:8])))
        print('\nA commit that changed nothing but bookkeeping did not fix '
              'anything, so it\nis almost certainly NOT the commit this record '
              'is about. This is the\n`--commit $(git rev-parse HEAD)` trap: '
              'that reads as "this work" and means\n"whatever landed last", '
              'which in a five-clone repo is often somebody else\'s.')
        print('\n  Its subject is: %s' % d['subject'][:90])
        print('\nCommit the fix FIRST, then cite it. If the record really does '
              'belong to a\nbookkeeping commit, say why:\n'
              '  --commit-is-bookkeeping "<a real sentence>"')
        return 2
    inj_rec = None
    if str(inj).strip():
        di = derive(inj)
        if not di:
            print('no such injection commit: %s -- a sha that does not resolve '
                  'is not a lag, it is a guess with a hash on it.' % inj); return 2
        inj_rec = {'commit': di['commit'], 'date': di['date'],
                   'subject': di['subject']}
        lag = lag_days(di['date'], d['date'])
        if lag is not None and lag < 0:
            print('the injection commit (%s) is NEWER than the fix (%s). One of '
                  'the two shas is wrong; a negative lag would poison the '
                  'distribution this field exists to build.'
                  % (di['date'], d['date'])); return 2
        inj_rec['lag_days'] = lag
    reg = load()
    key = (d['commit'], summary)
    if any((r['commit'], r['summary']) == key for r in reg['records']):
        print('already registered: %s' % d['commit']); return 0
    rec = dict(d)
    rec.update({'app': app, 'layer': layer, 'severity': sev,
                'detection_method': method, 'summary': summary,
                'rules': rules, 'citation_confidence': conf,
                'injection_phase': phase, 'phase_confidence': phase_conf,
                'found_by_tool': (str(found_by).strip() or None),
                'found_by_session': (str(found_session).strip() or None),
                'injection': inj_rec or {'unknown_reason': str(inj_unknown).strip()}})
    if note:
        rec['citation_note'] = note
    if phase_note:
        rec['phase_note'] = phase_note
    if factors is not None:
        rec['contributing_factors'] = factors
        if str(recurrence_open).strip():
            rec['recurrence_open'] = str(recurrence_open).strip()
        if str(single_note).strip():
            rec['single_factor_note'] = str(single_note).strip()
        # THE SAME FUNCTION --check USES, ON THE RECORD ABOUT TO BE WRITTEN.
        # Validating a different way here is how --add and --check would come
        # to disagree, and a record that one accepts and the other refuses is a
        # register that cannot be both written and read.
        problems = factor_problems(rec, d['commit'])
        if problems:
            print('NOT RECORDED -- the contributing factors do not validate. '
                  'These are the same rules --check applies, so recording it '
                  'now would only move the refusal to the next --check:')
            for p in problems:
                print('  ! %s' % p)
            return 2
    else:
        rec['factors_unknown_reason'] = str(factors_unknown).strip()
    reg['records'].append(rec)
    reg['records'].sort(key=lambda r: (r['date'], r['commit']))
    save(reg)
    print('registered %s (%s, %s, %s)' % (d['commit'], app, sev, method))
    fmea_loop(rec)
    return 0


# ── CONFIRMED CLEAN: THE VERDICT THIS REGISTER COULD NOT RECORD ────────────
# Added 2026-09-17, on Michael's instruction, after the item 83 independent
# review had to put its sound findings in PROSE -- docs/2026-09-16-item83-
# independent-review.md's "What was checked and found SOUND" section -- because
# there was nowhere here to put them.
#
# THE PLATFORM ALREADY HAD THE PRINCIPLE AND NOT THE FIELD. The cron sweep row
# in the open-work index states it outright: "a clean result is a result, and an
# unchecked endpoint must not be mistaken for a sound one." Until now the only
# way to record a driven confirmation in this file was to invent a defect for
# it -- a severity it does not have, an injection_phase for a thing that was
# never injected, a fix commit for a fix that never happened. Every one of those
# would be a fabricated value in the register this platform uses to reason about
# its own defect rate, which is the worst possible place for one.
#
# A SEPARATE ARRAY, NOT A RECORD WITH A FLAG, AND THE REASON IS ARITHMETIC.
# `records` is the numerator of every figure this tool prints -- by layer, by
# severity, by detection method, the injection x removal matrix, the FMEA loop.
# A confirmation dropped in there with `severity: none` would either distort
# each of those or force a filter into all of them, and the filter that gets
# forgotten in one place is how a denominator goes quietly wrong. Confirmations
# are a DIFFERENT POPULATION answering a DIFFERENT QUESTION and they are stored,
# counted and reported as one.
#
# `limits` IS REQUIRED AND IS THE WHOLE POINT. A confirmation with no stated
# limit is "I looked and it was fine", which is the sentence this platform has
# been wrong with most often. Every real confirmation has an edge: a path not
# driven, a value not varied, an environment not reproduced. Refusing to record
# a confirmation because its limits are not worked out would lose the
# confirmation; refusing one that claims NO limits is refusing a claim nobody
# can check.
#
# `driven` IS REQUIRED FOR THE SAME REASON --check DEMANDS A FOUND-BY TOOL:
# "checked and found sound" with nothing naming what was RUN is a reading, and
# a reading is what this register exists to distinguish from a measurement.
CONFIRM_VERDICTS = ('sound', 'sound-with-limits')


def today():
    """The date to stamp a confirmation with, taken from git rather than the
    clock -- the same source every other date in this file comes from, so a
    machine whose clock is wrong cannot put a confirmation in the future."""
    d = git('log', '-1', '--format=%cI')
    return (d or '')[:10] or '0000-00-00'


def cmd_confirm(argv):
    def opt(name, required=True):
        # THE FILE ROUTE IS TRIED FIRST so `--x-file` works for every `--x`
        # without any field being listed anywhere. See read_text_arg().
        try:
            from_file = read_text_arg(argv, name)
        except ArgFile as e:
            print('%s' % e)
            sys.exit(2)
        if from_file is not None:
            return from_file
        if name in argv:
            return argv[argv.index(name) + 1]
        if required:
            print('missing %s (or %s-file <path>)' % (name, name))
            sys.exit(2)
        return ''

    sha = opt('--commit')
    app, layer = opt('--app'), opt('--layer')
    claim = opt('--claim')
    driven = opt('--driven')
    limits = opt('--limits')
    method = opt('--method')
    verdict = opt('--verdict', required=False) or 'sound-with-limits'
    by = opt('--by', required=False) or 'unattributed'

    if layer not in LAYERS:
        print('--layer must be one of %s' % (LAYERS,)); return 2
    if method not in METHODS:
        print('--method must be one of %s' % (METHODS,)); return 2
    if verdict not in CONFIRM_VERDICTS:
        print('--verdict must be one of %s' % (CONFIRM_VERDICTS,)); return 2
    # THE THREE REFUSALS THAT MAKE THIS A RECORD RATHER THAN A REASSURANCE.
    if len(str(claim).strip()) < 25:
        print('--claim must QUOTE OR STATE the specific claim that was checked, '
              'in at least 25 characters. "the code is fine" is not a claim '
              'anybody can re-check, and a confirmation nobody can re-check is '
              'the thing this field exists to stop being written in prose.')
        return 2
    if len(str(driven).strip()) < 20:
        print('--driven must say WHAT WAS RUN -- the suite, the probe, the '
              'command, the arms. A confirmation with nothing driven is a '
              'reading, and this register exists to tell a reading from a '
              'measurement.')
        return 2
    if verdict != 'sound' and len(str(limits).strip()) < 25:
        print('--limits is REQUIRED and must be a real sentence. Every real '
              'confirmation has an edge -- a path not driven, a value not '
              'varied, an environment not reproduced. A confirmation claiming '
              'none is a claim nobody can check.\n'
              '  Pass --verdict sound ONLY if the check is genuinely total, '
              'and it still takes a --limits line saying why it is.')
        return 2
    if len(str(limits).strip()) < 25:
        print('--limits is required even for --verdict sound: say why the '
              'check is total rather than leaving a reader to assume it.')
        return 2

    d = derive(sha)
    if not d:
        print('no such commit: %s' % sha); return 2

    reg = load()
    reg.setdefault('confirmations', [])
    # ONE CONFIRMATION PER (commit, claim). Re-confirming the same claim on the
    # same commit is not a second piece of evidence; it is the same check run
    # twice, and counting it twice would make a repeated run look like
    # corroboration. A DIFFERENT claim on the same commit is a new row.
    key = (d['commit'], str(claim).strip())
    if any((c.get('commit'), c.get('claim')) == key for c in reg['confirmations']):
        print('that claim is already confirmed on %s. Re-running the same check '
              'is not a second confirmation -- if the claim changed, say so in '
              'the claim text.' % d['commit'][:12])
        return 2
    rec = {
        'commit': d['commit'], 'date': d['date'], 'subject': d['subject'],
        'app': app, 'layer': layer, 'method': method,
        'claim': str(claim).strip(),
        'driven': str(driven).strip(),
        'verdict': verdict,
        'limits': str(limits).strip(),
        'confirmed': today(),
        'confirmed_by': by,
    }
    reg['confirmations'].append(rec)
    reg['confirmations'].sort(key=lambda c: (c['confirmed'], c['commit']))
    save(reg)
    print('confirmed %s (%s, %s, %s) -- NOT a defect record and NOT in any '
          'defect figure' % (d['commit'][:12], app, layer, verdict))
    return 0


def confirmation_problems(c, where):
    """Everything wrong with one confirmation, as a list of sentences."""
    out = []
    for f in ('commit', 'app', 'layer', 'method', 'claim', 'driven',
              'verdict', 'limits', 'confirmed'):
        if not str(c.get(f, '')).strip():
            out.append('%s: %s is empty' % (where, f))
    if c.get('layer') and c['layer'] not in LAYERS:
        out.append('%s: layer %r is outside the vocabulary' % (where, c['layer']))
    if c.get('method') and c['method'] not in METHODS:
        out.append('%s: method %r is outside the vocabulary' % (where, c['method']))
    if c.get('verdict') and c['verdict'] not in CONFIRM_VERDICTS:
        out.append('%s: verdict %r is outside %s' % (where, c['verdict'], (CONFIRM_VERDICTS,)))
    # A confirmation carrying defect fields is one somebody tried to file as a
    # defect, or a defect somebody tried to file as a confirmation. Either way
    # the two populations have started to mix, which is the failure the
    # separate array exists to prevent.
    for f in ('severity', 'injection_phase', 'contributing_factors'):
        if f in c:
            out.append('%s: carries the defect field %r -- a confirmation is '
                       'not a defect with the severity left out' % (where, f))
    return out


# ── THE FMEA LOOP, ASKED AT THE ONLY MOMENT THE ANSWER CHANGES ─────────────
# Item 26, the FMEA-prediction branch, wired 2026-09-13.
#
# tools/fmea_prediction_check.py's own docstring says its cadence is the defect
# register growing: "it recurs because the answer changes every time the defect
# register grows." Nothing was asking it at that moment. Run by hand it reports
# over the whole corpus and, today, correctly says nothing is scoreable yet --
# a standing 25-line report that a person has to remember to run, about a
# question that only becomes answerable one record at a time.
#
# So the question is asked HERE, about THIS record, while somebody is looking:
#   * was there a draft for the file, and did it PREDATE the defect;
#   * if so, did a risk in it cite the same standing rule;
#   * if not, say which file has no draft, because that is the gap that keeps
#     the corpus unscoreable and it is invisible from anywhere else.
#
# IT NEVER CHANGES THE EXIT CODE. --add succeeded or it did not; whether the
# defect was foreseen is a separate fact and folding it into the return value
# would make a registration fail for the wrong reason.
#
# ── AND IT FAILS LOUD WHEN THE CHECKER IS ABSENT, per PR 1.11 ─────────────
# The tempting shape is `try: import ... except ImportError: pass`, which is a
# check that silently does not run and is indistinguishable from one that ran
# and found nothing. It says which module was missing and that the loop did NOT
# close, and it says it every time.
def fmea_loop(rec):
    print('')
    print('  FMEA LOOP -- was this one foreseen?')
    try:
        sys.path.insert(0, os.path.join(REPO, 'tools'))
        import fmea_prediction_check as fp
    except Exception as e:                                     # noqa: BLE001
        print('    COULD NOT RUN: tools/fmea_prediction_check.py did not import'
              ' (%s). The loop did NOT close for this record -- this is not a'
              ' "no draft" answer and must not be read as one.' % e)
        return
    try:
        drafts = fp.load_drafts()
    except Exception as e:                                     # noqa: BLE001
        print('    COULD NOT RUN: the drafts under docs/fmea/ could not be read'
              ' (%s). Not a pass.' % e)
        return

    by_target = {}
    for dr in drafts:
        by_target.setdefault(dr.get('target'), []).append(dr)

    # A worklog or a doc cannot carry a code defect a draft could have
    # predicted -- the checker's own NOT_A_CODE_TARGET rule, reused rather than
    # re-typed so the two cannot drift apart.
    files = [f for f in rec.get('files', []) if not fp.NOT_A_CODE_TARGET.search(f)]
    if not files:
        print('    no code target in this commit (%d file(s), all worklogs or'
              ' docs) -- nothing a draft could have predicted'
              % len(rec.get('files', [])))
        return

    for f in files:
        cands = by_target.get(f) or []
        if not cands:
            print('    NO DRAFT: %s -- `python tools/fmea_draft.py %s --save`'
                  ' would make the next defect here scoreable' % (f, f))
            continue
        older = [c for c in cands if c.get('_asof') and c['_asof'] <= rec['date']]
        if not older:
            print('    DRAFT NEWER than the defect: %s -- unscoreable by'
                  ' construction, it cannot predict what already happened' % f)
            continue
        hit = None
        for c in older:
            how, risk = fp.matched(c, rec)
            if how:
                hit = (how, c, risk)
                break
        if hit:
            print('    PREDICTED: %s -- %s, from %s' % (f, hit[0], hit[1]['_file']))
        else:
            print('    MISSED: %s -- %d draft(s) predate it and none cites %s'
                  % (f, len(older), ', '.join(rec.get('rules') or ['(no rule)'])))


def subject_index():
    """subject -> [sha]. Built once, because a record that lost its SHA to a
    rebase kept its message: `git rebase` rewrites the hash and preserves the
    subject, which is precisely why the subject is the durable half."""
    out = git('log', '--format=%H%x1f%s', 'HEAD') or ''
    idx = {}
    for line in out.split('\n'):
        if '\x1f' not in line:
            continue
        sha, subj = line.split('\x1f', 1)
        idx.setdefault(subj, []).append(sha)
    return idx


def resolve(rec, idx):
    """(sha, how) -- how is 'sha', 'subject', 'ambiguous' or None.

    ── A REBASED SHA IS NOT A RECORD POINTING AT NOTHING (2026-09-11) ────────
    This used to fail outright on any SHA that would not resolve, and the
    register then sat permanently red: 5 problems when it was first noticed,
    12 hours later, growing because the cause is STRUCTURAL rather than
    anybody's mistake. `--add` derives the SHA from the commit in front of it,
    and with four clones pushing, most commits are rebased onto somebody
    else's work before they reach origin. The SHA recorded is the pre-rebase
    one; the commit it named never existed on `main`.

    That matters more than a stale field. This tool is one of the promoted
    report-only checkers, so **every post-push sweep in every clone carried a
    finding**, which is exactly how a report-only checker earns the reputation
    that gets it switched off before it is ever promoted to a gate.

    So the SHA is treated as what it actually is -- a convenience pointer --
    and the record's identity is its SUBJECT, which survives the rebase. A
    record still FAILS when neither resolves, because that is the real case
    this check exists for: a register pointing at nothing, whose length reads
    as evidence. An AMBIGUOUS subject fails too rather than picking one, since
    guessing which of two commits a record meant is the thing a register must
    never do.
    """
    # AN EXTERNAL CITATION RESOLVES BY DECLARATION AND NOTHING ELSE. It is
    # reported under its own heading rather than counted in "every commit
    # resolves", because it was never checked and saying otherwise would make
    # the summary line mean less for every record above it.
    if is_external(rec.get('commit')):
        return rec['commit'], 'external'
    if git('rev-parse', '--verify', rec['commit'] + '^{commit}'):
        return rec['commit'], 'sha'
    hits = idx.get(rec.get('subject') or '\x00absent', [])
    if len(hits) == 1:
        return hits[0][:12], 'subject'
    if len(hits) > 1:
        return None, 'ambiguous'
    return None, None


def cmd_check(argv=()):
    """Every record must still resolve. A register pointing at nothing is worse
    than none, because its length reads as evidence."""
    reg = load()
    bad, reseat = [], []
    could_not_check = 0
    known = known_rules()
    idx = subject_index()
    for r in reg['records']:
        sha, how = resolve(r, idx)
        if how == 'subject':
            reseat.append((r['commit'], sha, r['subject']))
        elif how == 'ambiguous':
            bad.append('%s -- its subject matches more than one commit, so the '
                       'record cannot be re-seated without guessing: %r'
                       % (r['commit'], r['subject']))
        elif how is None:
            bad.append('%s -- neither the commit nor its subject is in this '
                       'repo: %r' % (r['commit'], r.get('subject')))
        # THE VOCABULARY CHECKS RUN REGARDLESS. They used to sit after a
        # `continue`, so the moment a SHA went stale the rest of that record
        # stopped being checked at all -- a second, quieter hole underneath the
        # loud one, and it would have outlived the fix for the loud one.
        if r['detection_method'] not in METHODS:
            bad.append('%s -- unknown detection method %r'
                       % (r['commit'], r['detection_method']))
        # ITEM 63. A method with no CHECKPOINT_OF row would silently come back
        # 'unknown' and quietly shrink whichever bucket the asymmetry figure is
        # read from. The vocabulary and the mapping have to stay in step.
        elif checkpoint_of(r['detection_method']) == 'unknown':
            bad.append('%s -- detection method %r has no CHECKPOINT_OF row, so '
                       'it would fall into `unknown` and distort the checkpoint '
                       'split' % (r['commit'], r['detection_method']))
        if r['layer'] not in LAYERS or r['severity'] not in SEVERITIES:
            bad.append('%s -- layer/severity outside the vocabulary' % r['commit'])
        # ── THE INJECTION POINT, same rule as --add ──────────────────────
        ij = r.get('injection')
        if not isinstance(ij, dict):
            bad.append('%s -- no injection block. Every record carries either a '
                       'commit or a stated reason it has none.' % r['commit'])
        elif ij.get('commit'):
            if ij.get('lag_days') is not None and ij['lag_days'] < 0:
                bad.append('%s -- negative discovery lag (%s days): the '
                           'injection commit is newer than the fix'
                           % (r['commit'], ij['lag_days']))
        elif not str(ij.get('unknown_reason') or '').strip():
            bad.append('%s -- injection unknown with no reason. A bare unknown '
                       'is a silence, not a decision.' % r['commit'])
        # ── THE TOOL THAT FOUND IT, same rule as --add so a hand-edited
        # record cannot carry a shape --add would have refused.
        fbt = r.get('found_by_tool')
        if tool_required(r['detection_method']) and not str(fbt or '').strip():
            bad.append('%s -- found by an automated checker with no '
                       'found_by_tool' % r['commit'])
        if not tool_required(r['detection_method']) and str(fbt or '').strip():
            bad.append('%s -- carries found_by_tool %r but %s found it'
                       % (r['commit'], fbt, checkpoint_of(r['detection_method'])))
        # ── WHICH HOVER INSTANCE, same rule as --add for the same reason ──
        # OLD RECORDS ARE EXEMPT and that is deliberate: every hover-audit
        # record written before this field existed has no honest answer, and
        # back-filling one would invent the very attribution the field is for.
        # The exemption is by DATE rather than by absence, so a new record
        # that simply omits the field is still refused.
        fbs = r.get('found_by_session')
        if session_required(r['detection_method']):
            if r.get('date', '') >= SESSION_FIELD_FROM and not str(fbs or '').strip():
                bad.append('%s -- a hover-audit record from %s with no '
                           'found_by_session. Two instances run; this is what '
                           'separates a peer check from a duplicate.'
                           % (r['commit'], r.get('date')))
        elif str(fbs or '').strip():
            bad.append('%s -- carries found_by_session %r but its method is %r'
                       % (r['commit'], fbs, r['detection_method']))
        if str(fbs or '').strip() and not HOVER_SESSION_SHAPE.match(str(fbs).strip()):
            bad.append('%s -- found_by_session %r is not a hover instance name'
                       % (r['commit'], fbs))
        # ── THE INJECTION PHASE, checked the same way and for the same reason ─
        ph = r.get('injection_phase')
        phc = r.get('phase_confidence')
        if ph not in PHASES:
            bad.append('%s -- injection_phase %r is outside %s'
                       % (r['commit'], ph, (PHASES,)))
        elif ph == 'unknown' and not str(r.get('phase_note') or '').strip():
            bad.append('%s -- injection_phase unknown with no note. A bare '
                       'unknown is a silence, not a decision.' % r['commit'])
        if phc not in PHASE_CONFIDENCES:
            bad.append('%s -- phase_confidence %r is outside %s'
                       % (r['commit'], phc, (PHASE_CONFIDENCES,)))
        # ── THE CITATION, checked the same way and for the same reason ──────
        conf = r.get('citation_confidence')
        rules = r.get('rules')
        if conf not in CONFIDENCES:
            bad.append('%s -- citation_confidence %r is outside %s'
                       % (r['commit'], conf, (CONFIDENCES,)))
        elif conf == 'not-citable':
            if rules:
                bad.append('%s -- not-citable but carries rules %r'
                           % (r['commit'], rules))
            if not str(r.get('citation_note') or '').strip():
                bad.append('%s -- not-citable with no note. A bare refusal to '
                           'cite is a silence, not a decision.' % r['commit'])
        else:
            if not rules:
                bad.append('%s -- %s citation with no rule' % (r['commit'], conf))
            if conf == 'arguable' and not str(r.get('citation_note') or '').strip():
                bad.append('%s -- arguable citation with no note saying what is '
                           'arguable about it' % r['commit'])
            if known is None:
                could_not_check += 1
            else:
                for rid in (rules or []):
                    if rid not in known:
                        bad.append('%s -- cites %r, which is not a section in %s'
                                   % (r['commit'], rid, RULES_DOC))
        # ── ITEM 75: THE CONTRIBUTING FACTORS, AND WHAT IS STILL OPEN ────
        if 'root_cause' in r:
            bad.append('%s -- carries a `root_cause` field. There is no single '
                       'root cause of a failure in a system like this, and a '
                       'field with that name asserts one: fix the named thing '
                       'and the record reads as closed while every other '
                       'contributor is still there. Use contributing_factors, '
                       'which is a list.' % r['commit'])
        bad.extend(factor_problems(r, r['commit']))

    seen = set()
    for r in reg['records']:
        k = (r['commit'], r['summary'])
        if k in seen:
            bad.append('%s -- duplicate record' % r['commit'])
        seen.add(k)
    # REPORTED, NOT SILENT, AND NOT A FAILURE. A re-seated record is sound --
    # the commit is really there under a new hash -- but a reader deserves to
    # know the register's SHAs have drifted from `main`, and `--reseat` is one
    # command away. Saying nothing here would trade a false alarm for a silent
    # rot, which is the swap this repo keeps recording against itself.
    if reseat:
        print('RE-SEATABLE (%d): the SHA was rewritten by a rebase and the '
              'subject still resolves.' % len(reseat))
        for old, new, subj in reseat:
            print('    %s -> %s  %s' % (old, new, subj[:66]))
        print('    Not a failure. Run `python tools/defect_register.py '
              '--reseat` to write them back.')
    # ── ONE ENTITY, ONE SPELLING (2026-09-14) ──────────────────────────────
    # `SAIRNBIZ` and `sairnbiz` sat in this file as two apps, splitting one
    # entity in half. Nothing noticed, because every per-app figure simply
    # reported both. It surfaced while measuring whether there is enough data
    # for a PER-ENTITY baseline (item 51) -- where a silent split is not a
    # cosmetic problem, it halves the very count the baseline is computed from.
    seen_apps = {}
    for r in reg['records']:
        seen_apps.setdefault(str(r.get('app', '')).lower(), set()).add(r.get('app'))
    for low, spellings in sorted(seen_apps.items()):
        if len(spellings) > 1:
            bad.append('the app %r appears under %d spellings %s -- one entity '
                       'with two names is two entities to every per-app figure '
                       'in this file' % (low, len(spellings), sorted(spellings)))
    # ── AND THE VOCABULARY ITSELF, from APP_VOCAB_FROM (2026-09-22) ────────
    # The spelling check above only fires once BOTH spellings are in the file,
    # which makes it a detector of damage already done -- and the damage is
    # done to whoever rebases through it next, not to whoever caused it. This
    # asks the stronger question: is this value one of the names that exist?
    # A single consistently-wrong spelling passes the check above and fails
    # this one.
    apps = known_apps()
    for r in reg['records']:
        if r.get('date', '') < APP_VOCAB_FROM:
            continue
        if r.get('app') not in apps:
            near = [k for k in apps if k.lower() == str(r.get('app')).lower()]
            bad.append('%s -- app %r is not one of the %d known values%s'
                       % (r['commit'], r.get('app'), len(apps),
                          (' (did you mean %r?)' % near[0]) if near else ''))

    # ── CONFIRMATIONS ARE CHECKED TOO, AND KEPT OUT OF THE DEFECT NUMBERS ──
    # Same standard as a defect record: it must resolve, it must carry the
    # fields that make it re-checkable, and it must not have started to look
    # like a defect. A confirmation nobody validates is the reassurance this
    # field was added to replace.
    conf_seen = set()
    for c in reg.get('confirmations', []):
        where = 'confirmation %s' % str(c.get('commit', '?'))[:12]
        bad.extend(confirmation_problems(c, where))
        sha, how = resolve(c, idx) if c.get('subject') else (
            (c.get('commit'), 'sha') if git('rev-parse', '--verify',
                                            str(c.get('commit', '')) + '^{commit}') else (None, None))
        if how == 'subject':
            reseat.append((c['commit'], sha, c.get('subject', '')))
        elif not sha:
            bad.append('%s -- neither the SHA nor the subject resolves' % where)
        k = (c.get('commit'), c.get('claim'))
        if k in conf_seen:
            bad.append('%s -- the same claim is confirmed twice; running one '
                       'check again is not corroboration' % where)
        conf_seen.add(k)
        # THE SPELLING RULE APPLIES ACROSS BOTH POPULATIONS. An app named one
        # way in a defect and another in a confirmation is the same split.
        seen_apps.setdefault(str(c.get('app', '')).lower(), set()).add(c.get('app'))
    for low, spellings in sorted(seen_apps.items()):
        if len(spellings) > 1 and not any(
                ('the app %r appears' % low) in b for b in bad):
            bad.append('the app %r appears under %d spellings %s across records '
                       'and confirmations -- one entity with two names is two '
                       'entities to every per-app figure in this file'
                       % (low, len(spellings), sorted(spellings)))

    if bad:
        print('FAIL: %d register problem(s)' % len(bad))
        for b in bad:
            print('  ' + b)
        return 1
    if could_not_check:
        # PR 1.11, in this file's own output. The citations were NOT validated,
        # and saying "OK" here would be reporting a check that did not run.
        print('COULD NOT CHECK %d citation(s): %s is unreadable, so the rule '
              'vocabulary is unknown. This is not a pass.'
              % (could_not_check, RULES_DOC))
        return 2
    # ── ITEM 75 COVERAGE, PRINTED AND NOT ENFORCED ─────────────────────────
    # The field is new, so requiring it on all 77 records would mean
    # back-filling contributing factors for defects nobody is going to
    # re-investigate -- which is how a CAPA form fills up with guesses. The
    # count is printed so the gap is visible rather than absent.
    with_cf = [r for r in reg['records'] if r.get('contributing_factors')]
    n_factors = sum(len(r['contributing_factors']) for r in with_cf)
    unknown = [r for r in reg['records'] if r.get('factors_unknown_reason')]
    print('    contributing factors: %d of %d record(s) carry them, %d factors '
          'in total (%.1f per record).'
          % (len(with_cf), len(reg['records']), n_factors,
             (n_factors / float(len(with_cf))) if with_cf else 0.0))
    print('      NOT required of OLD records -- back-filling a cause nobody '
          're-investigated is how a CAPA form fills with guesses.')
    print('      REQUIRED of NEW ones since 2026-09-16: --add takes either '
          '--factors or an explicit --factors-unknown reason, because a field '
          'that is optional when a record is written is a field that stays '
          'empty. %d record(s) carry a stated unknown-reason.' % len(unknown))
    cited = sum(1 for r in reg['records'] if r.get('rules'))
    confs = reg.get('confirmations', [])
    print('    confirmations: %d checked -- a SEPARATE population, in no defect '
          'figure above or below' % len(confs))
    # ── EXTERNAL CITATIONS ARE COUNTED APART FROM "every commit resolves" ──
    # They did not resolve; nothing looked. Folding them into that sentence
    # would weaken it for every record it is true of, which is the whole
    # reason the sentence is worth printing.
    exts = [r for r in reg['records'] if is_external(r.get('commit'))]
    if exts:
        print('    external citations: %d -- in a repository this one cannot '
              'see, so NOT verified by the line below. Each carries the repo, '
              'the sha and a note saying where to look:' % len(exts))
        for r in exts:
            e = r.get('external') or {}
            print('      %-28s %s' % (r['commit'], (e.get('note') or '')[:88]))
    print('OK: %d record(s)%s, every commit resolves and every field is in '
          'vocabulary.%s'
          % (len(reg['records']),
             (' (%d of them external and unverified)' % len(exts)) if exts else '',
             ' %d by subject.' % len(reseat) if reseat else ''))
    print('    standing-rule citations: %d cited, %d deliberately not-citable, '
          'every id checked against %s'
          % (cited, len(reg['records']) - cited, RULES_DOC))
    return 0


def reseat_base():
    """The ref reachability is measured against, and its name for the report.

    origin/main when it exists -- that is what every other clone will fetch and
    what an auditor following a SHA will actually have. HEAD when it does not,
    which is the case in a fresh worktree or a clone with no remote.

    Returns (ref, None) or (None, why). A refusal rather than a default: with no
    ref to compare against, EVERY record would look unreachable and this would
    re-seat the whole register on the strength of not being able to look.
    """
    for ref in ('origin/main', 'HEAD'):
        if git('rev-parse', '--verify', ref):
            return ref, None
    return None, 'neither origin/main nor HEAD could be read'


def reachable(sha, base):
    """Is this commit an ancestor of `base`?

    ── RESOLVABLE IS NOT REACHABLE (2026-09-16) ─────────────────────────────
    `resolve()` calls a SHA good the moment `rev-parse --verify` accepts it, and
    that is the RIGHT contract for `--check`: a record pointing at a real object
    is not a register pointing at nothing.

    IT IS THE WRONG QUESTION FOR A RE-SEAT. A rebase rewrites a commit and
    leaves the original behind as a DANGLING object -- it still resolves, for as
    long as it takes the reflog to expire, so `--reseat` skipped it and the
    record went on naming a commit that is not on the branch. Found on
    2026-09-16 when the register-feed gate refused a push twice: it asks whether
    a commit BEING PUSHED has a record, the register asked whether a recorded
    SHA is a valid object, and four records satisfied the second while failing
    the first.

    With four clones rebasing onto one branch that is the normal case rather
    than an edge one, so the repair command now asks the question the repair is
    for. `--check`'s acceptance contract is deliberately unchanged.
    """
    # `git()` returns '' on success-with-no-output and None on a non-zero exit.
    # `merge-base --is-ancestor` prints NOTHING and signals through the exit
    # code alone, so the test is `is not None` -- `bool()` would read every
    # ancestor as not-an-ancestor, which is the inverted answer and would
    # re-seat the entire register.
    return git('merge-base', '--is-ancestor', sha, base) is not None


def cmd_reseat():
    """Write re-seated SHAs back. A separate command on purpose: `--check` is
    read-only, and a checker that edits the thing it checks is not a checker."""
    reg = load()
    idx = subject_index()
    base, why = reseat_base()
    if base is None:
        print('COULD NOT RE-SEAT: %s.' % why)
        print('  Nothing was written. With no ref to measure reachability')
        print('  against, every record would look unreachable and this would')
        print('  re-seat the whole register on the strength of not looking.')
        return 2
    print('reachability measured against %s' % base)
    n = 0
    for r in reg['records']:
        sha, how = resolve(r, idx)
        # ── NO `if how == 'external': continue` HERE, AND THAT IS MEASURED ──
        # One was written and then DELETED, because its own negative control
        # proved it could not fire: with `resolve()` returning 'external', the
        # two branches below test `how == 'sha'` and `how in ('subject',
        # 'dangling')`, so an external record already falls through the loop
        # untouched. tests/run_defect_register_vocab_sabotage_probe.py planted
        # the removal of that `continue` and the suite stayed GREEN -- a
        # guard indistinguishable from its own absence, which is PR 1.1 in a
        # file that exists to count exactly that shape.
        #
        # THE PROTECTION IS REAL AND IT LIVES IN resolve(). Remove its external
        # branch and the same control goes red, because --check then reports a
        # pointer to another repository as a record pointing at nothing -- or
        # re-seats it onto a local commit that happens to share a subject. One
        # guard, in one place, with a control that bites on it.
        #
        # A SHA THAT RESOLVES BUT IS NOT ON THE BRANCH is exactly the case a
        # re-seat exists for, and it was the one case this skipped.
        if how == 'sha' and not reachable(r['commit'], base):
            hits = idx.get(r.get('subject') or '\x00absent', [])
            if len(hits) == 1:
                sha, how = hits[0][:12], 'dangling'
            else:
                print('  %s  DANGLING and %s -- left alone'
                      % (r['commit'],
                         'AMBIGUOUS by subject' if hits else 'no subject match'))
                continue
        if how in ('subject', 'dangling'):
            print('  %s -> %s  %s%s'
                  % (r['commit'], sha, r['subject'][:58],
                     '   (was dangling)' if how == 'dangling' else ''))
            r['commit'] = sha
            n += 1
    if not n:
        print('nothing to re-seat -- every SHA resolves AND is reachable '
              'from %s.' % base)
        return 0
    # DELIBERATELY NOT RE-SORTED. The sort key is (date, commit), so re-seating
    # twelve SHAs reorders the file and produces a 157-line diff for a 12-line
    # change -- measured, not guessed, because the first version did sort and
    # that is what it produced. A repair nobody can review is a repair nobody
    # checks.
    #
    # THE KNOWN CONSEQUENCE, SAID RATHER THAN DISCOVERED LATER: the next
    # `--add` DOES sort, so it normalises the order this left behind and its
    # diff is correspondingly large. That is the right place for the churn --
    # an add is a deliberate content change somebody is already reviewing,
    # while a re-seat is a mechanical repair that must stay legible.
    save(reg)
    print('re-seated %d record(s).' % n)
    return 0


def cmd_report():
    reg = load()
    recs = reg['records']
    lines = app_lines()
    confs = reg.get('confirmations', [])
    print('DEFECT REGISTER -- %d confirmed record(s) since %s'
          % (len(recs), reg.get('started', '?')))
    # ── PRINTED FIRST, SO THE DENOMINATOR IS NEVER READ AS THE WHOLE STORY ─
    # Confirmations are what was CHECKED AND FOUND SOUND. They are not defects,
    # they are in none of the figures below, and they are here because a
    # register that only records failures makes an unchecked thing and a
    # checked-sound thing look identical -- which is the platform's own
    # standing sentence about the cron sweep, applied to this file.
    print('CONFIRMED CLEAN -- %d, a SEPARATE population and in NO figure below'
          % len(confs))
    if confs:
        for c in confs[-6:]:
            print('  %s %-12s %-18s %s'
                  % (c.get('confirmed', '?'), str(c.get('commit', ''))[:12],
                     c.get('verdict', '?'), str(c.get('claim', ''))[:60]))
        if len(confs) > 6:
            print('  ... %d earlier' % (len(confs) - 6))
        print('  EVERY ONE CARRIES ITS LIMITS. A confirmation is "this specific')
        print('  claim was driven and held", never "this area is fine" -- read')
        print('  the `limits` field before quoting one.')
    else:
        print('  none yet. An EMPTY confirmation list is not evidence that')
        print('  nothing has been checked -- it is indistinguishable from a')
        print('  field nobody writes to, which is the same shape the shared')
        print('  status registry refuses to report as all-clear.')
    print('')
    print('BY LAYER')
    for L in LAYERS:
        n = len([r for r in recs if r['layer'] == L])
        print('  %-9s %d' % (L, n))
    print('')
    print('BY SEVERITY')
    for S in SEVERITIES:
        n = len([r for r in recs if r['severity'] == S])
        print('  %-9s %d' % (S, n))
    print('')
    print('BY DETECTION METHOD -- the column that matters')
    for M in METHODS:
        n = len([r for r in recs if r['detection_method'] == M])
        if n:
            print('  %-20s %d' % (M, n))
    print('')
    # ── WHICH CHECKPOINT CAUGHT IT (item 63) ───────────────────────────────
    known = [r for r in recs
             if isinstance(r.get('injection'), dict) and r['injection'].get('commit')
             and r['injection'].get('lag_days') is not None]
    print('DISCOVERY LAG -- injection to fix')
    print('  records with an injection commit : %d of %d' % (len(known), len(recs)))
    if not known:
        print('  NO LAG DISTRIBUTION EXISTS YET, so no IBNR reserve is offered.')
        print('  That is the honest state and not a missing feature -- see')
        print('  docs/2026-09-14-ibnr-scoping.md. Backfilling these by blame')
        print('  would build the distribution out of guesses.')
    else:
        lags = sorted(r['injection']['lag_days'] for r in known)
        mid = lags[len(lags) // 2]
        print('  lag in days: min %d, median %d, max %d' % (lags[0], mid, lags[-1]))
        print('  DO NOT QUOTE THIS AS A RESERVE. It is the lag of the defects')
        print('  that were FOUND; the ones still hiding are by definition absent')
        print('  from it, which is the whole reason IBNR needs a fitted tail')
        print('  rather than a median.')
    print('')
    print('WHICH CHECKPOINT CAUGHT IT')
    ck = {}
    for r in recs:
        k = checkpoint_of(r['detection_method'])
        ck[k] = ck.get(k, 0) + 1
    for k in CHECKPOINTS:
        if ck.get(k):
            print('  %-19s %3d   (%.0f%%)' % (k, ck[k], 100.0 * ck[k] / len(recs)))
    auto = [r for r in recs if checkpoint_of(r['detection_method']) == 'automated-checker']
    if auto:
        named = [r for r in auto
                 if str(r.get('found_by_tool') or '').strip()
                 and r['found_by_tool'] != TOOL_UNKNOWN]
        print('')
        print('  of the %d automated catches, the TOOL is named in %d'
              % (len(auto), len(named)))
        print('  BLOCKING vs REPORT-ONLY is the question behind this split, and')
        print('  it needs the tool classification -- run')
        print('  `python tools/tooling_inventory.py` and read the class column')
        print('  for the names below. It is deliberately NOT recomputed here: a')
        print('  second copy of that classification is a second thing to drift.')
        by = {}
        for r in named:
            by[r['found_by_tool']] = by.get(r['found_by_tool'], 0) + 1
        for t in sorted(by, key=lambda k: -by[k])[:10]:
            print('      %-38s %d' % (t, by[t]))
    print('')
    print('  THIS IS THE CHECKPOINT THAT DID CATCH EACH DEFECT, NOT THE ONE')
    print('  THAT SHOULD HAVE. Those differ exactly where a gate ought to exist')
    print('  and does not, so this UNDER-COUNTS gaps by construction.')
    print('  AND `monitoring` BEING %d IS A SELECTION EFFECT, NOT A RESULT: a'
          % ck.get('monitoring', 0))
    print('  defect nobody found is not in this register, so escape rate cannot')
    print('  be measured here at all.')
    print('')
    # ── INJECTION x REMOVAL (item 77) ──────────────────────────────────────
    # UNKNOWN AND INFERRED ARE PRINTED FIRST, ABOVE THE MATRIX, and that
    # ordering is the same decision fmea_prediction_check.py makes when it puts
    # NO DRAFT above the hit rate. A matrix read without them looks like
    # knowledge; read with them it is a matrix over the records somebody could
    # actually place, which is a different and smaller claim.
    unk = [r for r in recs if r.get('injection_phase') == 'unknown']
    inferred = [r for r in recs if r.get('phase_confidence') == 'inferred']
    print('WHERE DEFECTS WERE INJECTED -- read these two lines FIRST')
    print('  injection_phase = unknown       : %d of %d' % (len(unk), len(recs)))
    print('  phase called INFERRED, not stated: %d of %d   <- most of the '
          'matrix below rests on a judgement about a one-line summary, not on '
          'a quote from it' % (len(inferred), len(recs)))
    print('')
    print('BY INJECTION PHASE')
    for P in PHASES:
        n = len([r for r in recs if r.get('injection_phase') == P])
        if n:
            print('  %-12s %d' % (P, n))
    print('')
    print('INJECTION x REMOVAL -- the matrix the phase field exists for')
    used = [M for M in METHODS if any(r['detection_method'] == M for r in recs)]
    print('  %-12s %s' % ('', ' '.join('%-6s' % M[:6] for M in used)))
    for P in PHASES:
        row = [len([r for r in recs
                    if r.get('injection_phase') == P and r['detection_method'] == M])
               for M in used]
        if sum(row):
            print('  %-12s %s' % (P, ' '.join('%-6d' % n for n in row)))
    print('  DO NOT QUOTE A CELL ALONE. The columns are how a defect was '
          'FOUND, which is a fact about where people looked, not about where '
          'defects are.')
    print('')
    print('PRODUCT DEFECTS PER 1,000 LINES, against a MEASURED denominator')
    print('  %-22s %8s %8s %s' % ('app', 'lines', 'defects', 'per 1k'))
    prod = [r for r in recs if r['layer'] == 'product']
    for app in sorted(lines):
        n = len([r for r in prod if r['app'] == app])
        if not n:
            continue
        print('  %-22s %8d %8d %6.2f'
              % (app, lines[app], n, 1000.0 * n / max(1, lines[app])))
    # ── TWO FIGURES, NOT ONE (2026-09-13) ──────────────────────────────────
    # This printed a single ALL APPS rate: every product defect divided by
    # EVERY tracked app line, including the files nobody has ever swept. One
    # number was being asked to answer two different questions -- "how dense
    # are the defects where we have looked" and "how much have we looked at" --
    # and the second answer was silently folded into the first as a smaller
    # rate. A file with no records is a file nobody has swept, not a clean one;
    # the caveat below has always said so while the arithmetic said otherwise.
    #
    # The swept figure is the real signal. The unswept figure is a COUNT, and
    # deliberately not a rate: dividing by lines nobody has examined would be
    # the same mistake in the other direction.
    # ── AND THE NUMERATOR HAS TO MATCH THE DENOMINATOR ─────────────────────
    # Found by checking the first version of this very block: `len(prod)` counts
    # every product defect, INCLUDING those filed against app 'PLATFORM', which
    # is not a file and contributes no lines. The old ALL APPS rate divided
    # those by the whole-repo line count and the new swept rate divided them by
    # the swept subset -- both dividing a defect by lines it does not live in.
    # The caveat below has said "registered but not divided by anything" since
    # this tool shipped while the arithmetic did exactly that.
    #
    # They get their own line, with no rate, for the same reason the unswept
    # files do: a count with no honest denominator is reported as a count.
    swept = sorted(a for a in lines if any(r['app'] == a for r in prod))
    unswept = sorted(a for a in lines if a not in swept)
    swept_lines = sum(lines[a] for a in swept)
    unswept_lines = sum(lines[a] for a in unswept)
    in_files = [r for r in prod if r['app'] in lines]
    no_denom = [r for r in prod if r['app'] not in lines]
    print('  %-22s %8d %8d %6.2f   <- SWEPT: the real signal'
          % ('SWEPT FILES (%d)' % len(swept), swept_lines, len(in_files),
             1000.0 * len(in_files) / max(1, swept_lines)))
    print('  %-22s %8d %8s %6s   <- UNMEASURED, not a rate'
          % ('UNSWEPT FILES (%d)' % len(unswept), unswept_lines, '--', '--'))
    if unswept:
        print('     %s' % ', '.join(unswept))
    if no_denom:
        print('  %-22s %8s %8d %6s   <- NO DENOMINATOR: not app HTML'
              % ('OFF-FILE (%s)' % ', '.join(sorted({r['app'] for r in no_denom})),
                 '--', len(no_denom), '--'))
    print('')
    print('COVERAGE -- which methods have found something in which app')
    apps = sorted({r['app'] for r in recs})
    for app in apps:
        ms = sorted({r['detection_method'] for r in recs if r['app'] == app})
        print('  %-22s %s' % (app, ', '.join(ms)))
    print('')
    print('READ THIS BEFORE QUOTING ANY NUMBER ABOVE.')
    print('  * A density is a fact about what has been LOOKED AT, not about')
    print('    what is there. An app with no records is an app nobody has')
    print('    swept, not a clean one.')
    print('  * WHICH IS WHY THERE ARE TWO FIGURES AND NOT ONE. The swept rate')
    print('    is the signal; the unswept line count is coverage owed, stated')
    print('    as a COUNT because dividing by lines nobody has examined would')
    print('    manufacture a reassuring rate out of an absence of work.')
    print('  * FIVE OF THE FILES COUNTED ARE SATELLITE PAGES, not apps --')
    print('    stonedesk-hr, stonedesk-intake, stonedesk-catalog,')
    print('    sairndental-book, sairndental-complaint. 2,647 lines, ~2%% of')
    print('    the denominator. Real files, really unswept; named so the')
    print('    unswept count is not read as five whole applications.')
    print('  * The honest signal is CONSECUTIVE ZERO-NEW-FINDING SWEEPS BY')
    print('    DIFFERENT METHODS over the same files. One method returning')
    print('    zero means that method is exhausted. On 2026-09-10 the mutation')
    print('    controls found two defects in test code that reading the')
    print('    assertions had not, on the same files in the same hour.')
    print('  * The denominator counts LINES OF APP HTML. It does not count')
    print('    api/, sql/ or tools/, so a product defect in an endpoint is')
    print('    registered but not divided by anything. That is a known')
    print('    limitation, not an oversight.')
    return 0


def main(argv):
    if '--add' in argv:
        return cmd_add(argv)
    # BEFORE --check, because `--confirm` is a write and `--check` is a read;
    # an argv carrying both is a mistake and the write is the surprising half.
    if '--confirm' in argv:
        return cmd_confirm(argv)
    if '--check' in argv:
        return cmd_check(argv)
    if '--reseat' in argv:
        return cmd_reseat()
    return cmd_report()


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
