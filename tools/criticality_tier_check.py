"""Every registered resource in a re-tiered app must carry a criticality tier.

    python tools/criticality_tier_check.py            # report, exit 1 on drift
    python tools/criticality_tier_check.py --quiet    # exit code only
    python tools/criticality_tier_check.py --fix-rollup-list
                                       # INSERT the derived half of a rollup
                                       # line -- the Tier A NAME LIST -- and
                                       # nothing else. See fix_rollup_lists().

WHY THIS EXISTS. `docs/CRITICALITY-TIERS.md` states, for each RESOURCE, the worst
consequence of it being wrong, and cites something already recorded in this repo
as the evidence. Third of the three standing disciplines for vertical work,
alongside the SOUP register and the traceability matrix.

── IT USED TO CHECK APPS, AND THAT WAS THE DEFECT (2026-09-10) ─────────────
The register tiered whole apps. Measuring the eight Tier B apps moved every one
of them to A -- their B rested on an absence of RECORDING, not a measured
absence -- and 21 of 22 verticals became Tier A, at which point the register had
stopped discriminating. The measurement was honest; the GRANULARITY was wrong.
A roofing app's invoicing panel and its colour-theme settings do not carry the
same consequence, and one label per app forces them into one answer.

The unit is now `api/_resources/<app>.js`, the same unit the SOUP register and
the traceability matrix already use.

IT REPORTS AND NEVER REWRITES ANY JUDGEMENT, deliberately. The tier and its
sentence are a JUDGEMENT; a tool that regenerated this file would delete exactly
the part that matters and leave a table that looks authoritative because a
machine made it.

── THE ONE EXCEPTION, AND WHY IT IS NOT ONE (2026-09-24) ───────────────────
`--fix-rollup-list` writes. It inserts, into a rollup line's name list, Tier A
names that are already stated by the rows underneath it -- and it inserts
NOTHING ELSE, deletes nothing, and never touches a tier, a sentence or a count.
That list is not judgement; it is a restatement of rows this tool already
parses, which is exactly why it rotted while the COUNT -- the other derived
thing on that line -- never did. The count was guarded from day one AND is
re-derived on every run, so it stayed right with nobody thinking about it.

THE RECURRENCE IS THE ARGUMENT. The LIST MISSING arm landed 2026-09-23 and
caught the same class of omission FIVE times in the following day. Every catch
was real and every fix was correct; none of them changed the fact that
promoting a row leaves a derived sentence elsewhere for a human to retype. A
check firing five times in a day is not a check working harder, it is a check
reporting that the step in front of it is hand-done.

LIST STALE -- a name listed whose row says B -- is NOT fixed, and the asymmetry
is deliberate: that one may mean the ROW is wrong rather than the list, and
there is no derivation that can tell which.

WHAT IT CAN AND CANNOT SEE, said plainly because a checker that overstates its
reach is worse than none:

  IT CAN SEE    an app with no rollup line; a re-tiered app whose rows and
                registry disagree in either direction; a rollup count that does
                not match the rows under it; **a rollup LIST that does not match
                the Tier A rows under it, in BOTH directions** (2026-09-23 --
                the count half had been guarded since this file was written and
                the list half never was, and a sweep found the list drifted in
                six of sixteen apps while every count was correct); a tier
                outside A/B/C; a Tier A row with no evidence; resource rows
                under an app that claims not to be re-tiered yet; and -- on a
                row that has MIGRATED to the two-axis shape -- a sentence still
                asserting that an access control gate exists (§2.3).

  IT CANNOT SEE whether a tier is RIGHT. Nothing mechanical can. That is what
                the evidence column is for. It also cannot see whether the gate
                a row asserts actually EXISTS -- it only refuses the assertion,
                on migrated rows, because that claim was false for 41 rows and
                nothing in this table ever verified it.
"""
import io
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# SAIRN_TIER_REGISTER points this at a constructed table instead of the live
# one. Added 2026-09-22 so the two-axis parser can be DRIVEN: step 1 of the
# migration lands the parser before any row moves, so on the live file every
# new branch is dead code and a control run against it would report a
# confident pass over something that never executed. Not a behaviour switch
# -- the same code runs, against a different table.
REGISTER = os.environ.get('SAIRN_TIER_REGISTER') or os.path.join(
    REPO, 'docs', 'CRITICALITY-TIERS.md')
RESOURCES = os.path.join(REPO, 'api', '_resources')
VALID_TIERS = ('A', 'B', 'C')

# ── §2.3: THE B BOILERPLATE MADE TWO CLAIMS AND ONE OF THEM WAS FALSE ──────
# The default B sentence -- "Employee-auth-gated operational data: neither
# money nor a regulated record" -- packs an ACCESS-CONTROL claim and a CONTENT
# claim into one sentence. The content half is a judgement the stated B rule
# supports. The access-control half is a CODE FACT, and it was false for all 41
# SV_RESOURCES rows: SAIRNvet has no per-employee authentication at all, `role`
# is a self-selected dropdown, and api/sd-data.js says so in its own comment.
# AND THE GATE LANDED LATER THE SAME DAY, WHICH IS THE ARGUMENT RATHER THAN A
# REASON TO DELETE THIS. When the check below was written the handler had no
# session gate at all and said so in its own comment. A few hours on, `6fb6d696`
# added one -- `verifySessionToken(..., 'sairnvet')` over the whole map -- so
# the boilerplate's claim became true by accident, on that day, having been
# false on every day before it. That is precisely why a table must not assert a
# code fact: it is right only until the code moves, and it never says which day
# that was. Do not take the current state from this comment either; read the
# handler.
#
# THIS TABLE MUST NOT ASSERT A CODE FACT IT DOES NOT VERIFY. That is the whole
# finding, and the enforceable half of it is this: a row that has MIGRATED to
# the two-axis shape may not carry the assertion forward.
ACCESS_CONTROL_CLAIM = re.compile(
    r'auth-gated|auth gated|employee-auth|session-gated|session gate', re.I)

# WHY THE CHECK BINDS ONLY TO MIGRATED ROWS, stated rather than discovered.
# 260 un-migrated B rows carry that sentence right now. Firing on all of them
# turns this checker red in one step on a 387-row hand-edited file -- the
# atomic unreviewable diff §3.4 step 1 exists to avoid, and a red gate nobody
# can clear is a gate people switch off. Binding it to migration makes the
# sentence get fixed as each row moves, by the person moving it.
#
# THE COST OF THAT IS A CHECK THAT TESTS NOTHING UNTIL A ROW MOVES, which is
# the eighth cross-domain discipline exactly -- nothing announces the day a
# check stops testing anything, and a check that has not STARTED reads
# identically to one that passed. So the outstanding count is DERIVED from the
# table and PRINTED on every run, clean or not.


# ── A QUOTED CLAIM IS NOT AN ASSERTED ONE, AND THE FIRST SPELLING COULD NOT
#    TELL THE DIFFERENCE ───────────────────────────────────────────────────
# Found the moment the migration reached SAIRNgrounds. `grd_boq_rates` is a
# re-tiered row whose evidence explains the correction by QUOTING the sentence
# it was rescued from -- *"It was B on the generic sentence &ldquo;employee-
# auth-gated operational data...&rdquo;"*. That row is the check's own success
# story and the check refused it. The cell is not claiming a gate exists; it is
# citing the claim in order to say it was wrong, which is exactly the writing
# this register wants more of.
#
# The same shape is already on this platform's record: a comment quoting the
# old code makes the scanner re-flag the fix. So the quotation spans are
# blanked before the search rather than the pattern being narrowed -- narrowing
# it would have lost real assertions to keep one citation.
#
# SINGLE QUOTES ARE DELIBERATELY NOT TREATED AS QUOTATION. Apostrophes are
# everywhere in this file ("the firm's own"), and pairing them would blank
# arbitrary spans of real prose -- which is the fail-open direction.
QUOTE_SPANS = [
    re.compile(r'`[^`]*`'),                      # code span
    re.compile(r'&ldquo;.*?&rdquo;', re.S),      # HTML curly quotes
    re.compile(r'“.*?”', re.S),        # literal curly quotes
    re.compile(r'"[^"]*"'),                      # straight quotes
]


def strip_quotations(s):
    """Blank quoted spans so a CITED claim is not read as an ASSERTED one."""
    for pat in QUOTE_SPANS:
        s = pat.sub(lambda m: ' ' * len(m.group(0)), s)
    return s


# ── AND AN UNCITED CLAIM IS NOT A CITED ONE ───────────────────────────────
# Found at SAIRNlaw, one app after the quotation case. `law_portalmessages`
# says *the resource is already genuinely session-gated (`LAW_RESOURCES` in
# `api/sd-data.js`, driven to 401 with no session in
# `api/sd-data-sairnlaw-resources.test.js`)*. That is an access-control claim
# and it is a TRUE, CHECKABLE one: it names the dispatcher, the handler and a
# test that drives the refusal.
#
# 2.3's words are "must stop asserting things NOTHING VERIFIED", and this
# register's governing sentence is that a tier asserted with no evidence is a
# label. Both point the same way: the defect is an UNCITED claim, not a claim.
# Refusing a cited one would have deleted the best-evidenced sentence in the
# file to protect a rule against the worst-evidenced one.
#
# THE WEAKENING IS REAL AND IS STATED: a row could satisfy this by appending a
# backticked filename to the old boilerplate. What it cannot do is satisfy it
# by accident -- the 264 rows carrying the false sentence cite nothing, and the
# act of adding a citation is the act of pointing at something a reader can go
# and check, which is the whole standard this file holds everything else to.
CITATION = re.compile(r'`[^`]*\.(?:js|py|sql|html|md|json)`|`[^`]*test[^`]*`',
                      re.I)


def _sentence_around(s, i):
    """The sentence containing offset i, bounded so a neighbour's citation
    cannot be borrowed to excuse this sentence's claim."""
    lo = max(0, i - 250)
    hi = min(len(s), i + 250)
    a = s.rfind('. ', lo, i)
    b = s.find('. ', i, hi)
    return s[(a + 2) if a != -1 else lo: b if b != -1 else hi]


def asserts_access_control(*cells_):
    """An UNCITED access-control claim, wherever it sits in a row.

    Quotations are excluded (QUOTE_SPANS): a row quoting the old sentence to
    say it was wrong is doing the opposite of asserting it. A claim whose own
    sentence cites a file or a test is allowed: this check is about claims
    nothing verifies, not about the subject matter.
    """
    joined = ' '.join(c or '' for c in cells_)
    for m in ACCESS_CONTROL_CLAIM.finditer(strip_quotations(joined)):
        # Offsets align: strip_quotations blanks in place, preserving length.
        if not CITATION.search(_sentence_around(joined, m.start())):
            return True
    return False


def cells(line):
    """Split a markdown row, honouring an escaped pipe as CONTENT -- this repo
    has a standing rule about it, and this file's own index row tripped it."""
    out, cur, i, bs = [], '', 0, chr(92)
    while i < len(line):
        if line[i] == bs and i + 1 < len(line) and line[i + 1] == '|':
            cur += '|'
            i += 2
            continue
        if line[i] == '|':
            out.append(cur.strip())
            cur = ''
            i += 1
            continue
        cur += line[i]
        i += 1
    out.append(cur.strip())
    return out[1:-1] if len(out) >= 2 else []


def apps_with_registries():
    out = {}
    if not os.path.isdir(RESOURCES):
        return out
    for f in sorted(os.listdir(RESOURCES)):
        if not f.endswith('.js') or f.endswith('.test.js'):
            continue
        app = f[:-3]
        if app in ('index', 'shared'):
            continue
        names, err = resource_names(os.path.join(RESOURCES, f))
        if err:
            # A FILE WHOSE SHAPE IS NOT RECOGNISED IS AN ERROR, NOT AN EMPTY
            # APP. Returning an empty set would make every resource in it
            # vanish from the register check and the app would read CLEAN --
            # which is the fail-open direction and the worst possible answer
            # from a completeness checker.
            out[app] = SHAPE_ERROR(err)
            continue
        out[app] = names
    return out


class SHAPE_ERROR(str):
    """A file this reader could not parse. Truthy and NOT a set, so any use of
    it as a name collection fails loudly instead of contributing zero names."""


def resource_names(path):
    """Names inside the `resources: [...]` array ONLY.

    ── WHY THIS IS NOT "any line that looks like a quoted string" ────────────
    It was, until 2026-09-14, and the answer depended on WHERE SOMEBODY PUT A
    COMMENT. api/_resources/sairnvet.js declares three local-only keys together
    in `notSynced`:

        'sv_examrooms_turnover',  // NOT RECORDS -- a flat array of NUMBERS
        'sv_settings',            // device configuration
        ...
        'sv_audit_backed',

    The old rule required the line to END in `',` with exactly two quotes. The
    first two carry trailing comments and so were invisible; the third has its
    comment on the lines ABOVE and so was scraped as a server resource. The
    checker then reported `sairnvet/sv_audit_backed is registered and has no
    row` -- a finding produced entirely by comment placement, about a key that
    is DECLARED LOCAL-ONLY and correctly has no tier row.

    `notSynced` is the opposite of registered: it is the list of things that
    deliberately never reach a server. Counting it was always wrong; the
    comment style merely decided which of the three got noticed.
    """
    try:
        lines = io.open(path, encoding='utf-8').read().splitlines()
    except Exception as e:
        return None, 'could not read (%s)' % type(e).__name__
    # THREE SHAPES EXIST IN api/_resources/ AND ALL THREE ARE REAL. The first
    # version of this reader knew only the first and reported the other two as
    # a changed file shape -- which was loud and wrong, and is why it is worth
    # enumerating them here rather than widening a regex until nothing
    # complains.
    #
    #   resources: [            multi-line array          (13 files)
    #   resources: [],          explicitly EMPTY          (sairncash)
    #   resources: RESOURCES,   a reference to a const    (sairncode)
    start = None
    for i, l in enumerate(lines):
        # An explicitly empty array is a real answer, not a parse failure: the
        # app owns no resources of its own and the master plan already says so.
        if re.match(r'^\s*resources:\s*\[\s*\]\s*,?\s*$', l):
            return set(), None
        if re.match(r'^\s*resources:\s*\[\s*$', l):
            start = i + 1
            break
        m = re.match(r'^\s*resources:\s*([A-Z_][A-Z0-9_]*)\s*,\s*$', l)
        if m:
            # Follow the reference to `const NAME = [`. One hop only -- a chain
            # is a shape nobody has written and guessing at it would be the
            # widening this comment warns against.
            for j, l2 in enumerate(lines):
                if re.match(r'^\s*const\s+' + re.escape(m.group(1)) + r'\s*=\s*\[\s*$', l2):
                    start = j + 1
                    break
            if start is None:
                return None, ('resources references %s and no `const %s = [` was '
                              'found' % (m.group(1), m.group(1)))
            break
    if start is None:
        return None, 'no `resources:` array or reference found -- the file shape changed'
    names = set()
    for l in lines[start:]:
        # Another TOP-LEVEL key (two-space indent) ends the array. That is what
        # `notSynced:` and `extraActions:` are, and stopping here is the whole
        # fix.
        if re.match(r'^  \w+:', l) or re.match(r'^\};', l) or re.match(r'^\s*\]\s*;?\s*$', l):
            break
        m = re.match(r"^\s*'([\w.-]+)'\s*,", l)
        if m:
            names.add(m.group(1))
    if not names:
        return None, 'the `resources: [` array parsed to ZERO names -- that is a '                     'broken reader, not an app with no resources'
    return names, None


# A resource row's cell 1 is BOLD; a rollup row's is a bare integer. That
# difference -- not the column count -- is what tells the two apart from
# 2026-09-22 onward.
#
# IT MATCHES ANY BOLD TOKEN, NOT ONLY A/B/C, AND THAT IS THE POINT. The first
# spelling was `^\*\*([ABC])\*\*$`, which made a row carrying an invented tier
# (`| **CRITICAL** |`) match NEITHER branch: it was not a resource row because
# the letter was wrong, and not a rollup row because cell 1 was not an integer,
# so it was dropped in silence. The BAD TIER check could then never see it --
# the check that exists to stop a second tier vocabulary starting became
# unreachable by the exact rows it was written for, and the register reported
# the resource as having no row at all rather than as having a wrong one.
#
# Caught by run_criticality_tier_probe's arm 4 going red, which is the probe
# doing its job -- and it was red for a reason with nothing to do with the
# property it guards, which is the state the file's own arm 6 comment says
# teaches a reader to stop reading it.
#
# Recognising the row is what lets BAD TIER refuse it. Validating the letter
# is BAD TIER's job and stays there; this regex's job is only to answer "is
# this a resource row or a rollup row", and a wrong tier is still a resource
# row.
RESOURCE_CELL1 = re.compile(r'^\*\*([^*|]+)\*\*$')


def parse():
    """(rollup, resource_rows). Anchored on CELL SHAPE, not on column count.

    ── WHY NOT COLUMN COUNT ANY MORE (2026-09-22) ──────────────────────
    This told a rollup row from a resource row by `len(c) == 6` versus
    `len(c) == 4`. The two-axis migration
    (docs/2026-09-21-criticality-tiers-two-axis-spec.md) grows resource rows to
    SIX cells as well -- Resource | Tier | Confidentiality | worst-if-wrong |
    worst-if-read | Evidence -- so the moment one row migrates it becomes
    indistinguishable by count from a rollup line, falls into the rollup
    branch, and has its confidentiality letter read as a resource COUNT. A
    mis-parse, not a crash: nothing would say so.

    hover2 found that before a single row moved, which is the only reason it is
    being fixed rather than discovered. It is the same shape CLAUDE.md's PR
    1.11 names -- a check reporting a pass it never performed -- arriving
    through a parser instead of a gate.

    The data already carried the distinguishing signal: cell 1 is `**A**` on a
    resource row and a bare integer on a rollup row, in BOTH the old and new
    shapes, because the spec deliberately keeps the tier in column 2 so the
    three regex-based consumers of this file keep working unchanged.

    BOTH SHAPES ARE ACCEPTED DURING THE MIGRATION, deliberately. A hard cutover
    on a 387-row hand-edited file is the one-atomic-unreviewable-diff this
    platform's own precedent says not to land. A row that has not migrated
    yields confidentiality None, which every new check below treats as
    not-yet-answered rather than as a pass.
    """
    src = io.open(REGISTER, encoding='utf-8').read()
    rollup, rows = {}, []
    for line in src.split('\n'):
        if not line.startswith('|'):
            continue
        c = cells(line)
        m = re.match(r'^`([\w.-]+)`$', c[0]) if c else None
        if not m:
            continue
        name = m.group(1)
        if len(c) >= 2 and RESOURCE_CELL1.match(c[1].strip()):
            tier = re.sub(r'[*`]', '', c[1]).strip()
            if len(c) == 6:
                conf = re.sub(r'[*`]', '', c[2]).strip()
                rows.append((name, tier, conf, c[3], c[4], c[5]))
            elif len(c) == 4:
                # Pre-migration shape. `None` for confidentiality is NOT `B` --
                # an unanswered axis and a low one are different facts and are
                # reported differently below.
                rows.append((name, tier, None, c[2], '', c[3]))
            else:
                rows.append((name, tier, None, ' '.join(c[2:-1]), '', c[-1]))
        elif len(c) == 6:
            rollup[name] = {
                'n': c[1], 'a': c[2], 'b': c[3], 'c': c[4], 'status': c[5]}
    return rollup, rows


BACKTICKED = re.compile(r'`([\w.-]+)`')


def listed_names(status, names):
    """The registered resources of this app that its rollup cell NAMES.

    Only backticked tokens that are registered resources of THIS app count. A
    rollup cell may legitimately name a file, another app's resource, or
    describe its resources in plain words, and none of those is a claim this
    can judge.
    """
    return {n for n in BACKTICKED.findall(status) if n in names}


def rollup_list_gap(status, names, present, by_name):
    """Tier A rows this rollup cell does not name, sorted.

    ── ONE DERIVATION, TWO CALLERS (2026-09-24) ──────────────────────────
    Extracted so `--fix-rollup-list` inserts EXACTLY the names the LIST
    MISSING arm reports and cannot answer a different question from the
    check it exists to satisfy. A fixer with its own copy of the rule is a
    second rule, and the two drift in the direction where the fixer writes
    something the checker then refuses -- or worse, stops refusing.
    """
    return sorted({n for n in present if by_name[n][1] == 'A'}
                  - listed_names(status, names))


def _rollup_line_indices(lines):
    """{app: line index} for the rollup rows, identified the way parse() does.

    Cells are read to IDENTIFY a line and never to rebuild one: every edit
    below is a character insert into the original string. PR 2.1 -- an index
    row that is split on `|` and re-joined loses whatever the split did not
    model, and this file's rows carry escaped pipes, bold runs and em dashes.
    """
    out = {}
    for i, line in enumerate(lines):
        if not line.startswith('|'):
            continue
        c = cells(line)
        m = re.match(r'^`([\w.-]+)`$', c[0]) if c else None
        if not m or len(c) != 6:
            continue
        if RESOURCE_CELL1.match(c[1].strip()):
            continue
        out[m.group(1)] = i
    return out


# The character that may follow the LAST name in a list for an append to be
# safe. Anything else -- ` (`, a word, an opening bracket -- means the name is
# carrying a decoration the insert would land inside, and the fixer refuses
# rather than guessing where the decoration ends.
_TAIL_OK = re.compile(r'^\s*(,|\||&mdash;|—|$)')


def _insert_one(line, name, names):
    """Insert one backticked name into a rollup line, or say why not.

    Returns (new_line, None) or (None, reason).

    ── IT PLACES AMONG THE PLAIN NAMES ONLY, AND THAT IS THE WHOLE DESIGN ──
    These cells are NOT one alphabetical list. They are an annotated run --
    `**`sd_crm` (2026-09-23, B->A on BOTH axes ...)**` -- followed by a plain
    alphabetical run of bare names. The first version of this sorted against
    every backticked name in the cell, which put a new `sd_a*` ahead of an
    annotated `sd_crm` at the very front of the sentence: not wrong as a fact,
    but it moved the name out of the list a reader scans and into the middle
    of somebody's prose. Found by arm 12 refusing to round-trip.

    So: alphabetical WITHIN the plain run, and a cell with no plain run is
    REFUSED rather than given one. Inserting into an annotated name's bold
    span would silently widen an annotation to cover a resource it was never
    written about, which is a worse defect than the missing name.
    """
    # ── A NAME MENTIONED TWICE IS IN THE LIST ONCE (added 2026-09-25, found
    # ── reviewing this change) ──────────────────────────────────────────────
    # FIRST OCCURRENCE ONLY. These cells name a resource in the alphabetical
    # list AND SOMETIMES AGAIN in the prose that follows it -- *"&mdash; the
    # sharpest is `sf_operators`, which carried a named volunteer..."*. Without
    # this, `plain[-1]` is the PROSE mention rather than the end of the list,
    # and the append path below lands a new name inside that sentence.
    #
    # MEASURED RATHER THAN ARGUED, on the real register at the time: four of
    # seventeen cells mention a name twice -- stonedesk (`exec_context`),
    # sairnlaw (`law_clecredits`), sairnroofing (`rf_settings`), sairnfreedom
    # (`sf_operators`) -- and taking the first occurrence only makes ALL
    # SEVENTEEN plain runs monotonic, where four were not.
    #
    # `_TAIL_OK` CAUGHT THREE OF THE FOUR AND NOT THE FOURTH, which is why this
    # is a fix and not a tidy-up. Three of those prose mentions are followed by
    # a word, so the append refused. sairnfreedom's is followed by a COMMA,
    # which `_TAIL_OK` accepts -- so a name sorting after every plain name was
    # inserted into the middle of that sentence, turning "the sharpest is
    # `sf_operators`, which carried..." into "...is `sf_operators`,
    # `zzz_sorts_last`, which carried...". Driven, not reasoned: _insert_one is
    # pure, so it was called with a probe name and the placement read off.
    #
    # AND THE SELF-CHECK WOULD HAVE BLESSED IT. cmd_fix_rollup_lists re-parses
    # from disk and asks whether the cell names the resource. It would -- the
    # name is in the cell. So the fixer's own verification confirms the bad
    # placement as success, which is the "cosmetic and silent" failure this
    # change's own review request predicted, one step worse than predicted
    # because it lands inside a claim about a DIFFERENT resource.
    toks, _seen = [], set()
    for m in BACKTICKED.finditer(line):
        if m.group(1) not in names or m.group(1) in _seen:
            continue
        _seen.add(m.group(1))
        # Inside a bold run iff an odd number of `**` markers precede it.
        bold = line.count('**', 0, m.start()) % 2 == 1
        toks.append((m.start(), m.end(), m.group(1), bold))
    if not toks:
        return None, ('its rollup cell names no registered resource of this '
                      'app, so there is no list to insert into. A cell that '
                      'DESCRIBES its resources is not a list and this refuses '
                      'to turn one into the other')
    plain = [t for t in toks if not t[3]]
    if not plain:
        return None, ('every name in its rollup list carries a bold annotation '
                      'and there is no plain run to insert into. Placing a bare '
                      'name inside one of those spans would widen somebody\'s '
                      'annotation to cover a resource it was not written about. '
                      'Place it by hand')
    after = [t for t in plain if t[2] > name]
    if after:
        return line[:after[0][0]] + '`%s`, ' % name + line[after[0][0]:], None
    end, prev = plain[-1][1], plain[-1][2]
    if not _TAIL_OK.match(line[end:]):
        return None, ('it sorts after every plain name in the list and the last '
                      'one (`%s`) is followed by %r rather than a separator -- '
                      'so an append would land inside that annotation. Place it '
                      'by hand' % (prev, line[end:end + 12]))
    return line[:end] + ', `%s`' % name + line[end:], None


def fix_rollup_lists(rollup, rows, reg):
    """Insert the Tier A names each rollup list is missing. Nothing else.

    ── WHY THIS DOES NOT CONTRADICT "IT REPORTS AND NEVER REWRITES" ──────
    That rule is at the top of this file and it is right: the TIER and the
    EVIDENCE SENTENCE are judgement, and a tool that regenerated them would
    delete the only part that matters. THE NAME LIST IS NOT JUDGEMENT. It is
    a restatement of which rows say A, derived entirely from rows this same
    tool already reads -- which is exactly why it rotted while the COUNT, the
    other derived thing on that line, never did. Guarding the count made it
    correct; deriving it is what kept it correct with nobody thinking about
    it.

    THE RECURRENCE IS THE POINT. The LIST MISSING arm landed 2026-09-23 and
    caught the same omission FIVE times in the following day -- 2a7e72f3's
    sweep, then again on each retier commit that promoted a row. Every catch
    was real and every fix was correct; what none of them changed is that
    promoting a row leaves a sentence somewhere else that a human has to
    remember to retype. A checker that fires five times in a day is not
    failing, it is reporting that the work upstream of it is hand-done.

    IT ONLY EVER INSERTS. A name listed whose row is Tier B is LIST STALE,
    and that is a genuine question -- the row may be wrong rather than the
    list -- so it is reported and never silently deleted. The two halves of
    the same arm get different treatment on purpose: one has a derivable
    answer and one does not.

    Returns (applied, refusals) where applied is [(app, name)].
    """
    src = io.open(REGISTER, encoding='utf-8', newline='').read()
    lines = src.split('\n')
    idx = _rollup_line_indices(lines)
    by_name = {r[0]: r for r in rows}
    applied, refusals = [], []
    for app in sorted(set(rollup) & set(reg)):
        if 'NOT YET RE-TIERED' in rollup[app]['status']:
            continue
        names = reg[app]
        if isinstance(names, SHAPE_ERROR):
            continue
        present = {n for n in names if n in by_name}
        gap = rollup_list_gap(rollup[app]['status'], names, present, by_name)
        if not gap:
            continue
        if app not in idx:
            refusals.append((app, None, 'its rollup row could not be located in '
                                        'the file by the same reader that parsed it'))
            continue
        i = idx[app]
        for name in gap:
            new, why = _insert_one(lines[i], name, names)
            if why:
                refusals.append((app, name, why))
                continue
            lines[i] = new
            applied.append((app, name))
    if applied:
        io.open(REGISTER, 'w', encoding='utf-8', newline='').write('\n'.join(lines))
    return applied, refusals


def cmd_fix_rollup_lists():
    rollup, rows = parse()
    reg = apps_with_registries()
    applied, refusals = fix_rollup_lists(rollup, rows, reg)
    for app, name in applied:
        print('INSERTED  %s/%s into the rollup list' % (app, name))
    for app, name, why in refusals:
        print('REFUSED   %s%s -- %s'
              % (app, ('/' + name) if name else '', why))
    if not applied and not refusals:
        print('Nothing to insert: every rollup list already names every Tier A '
              'row under it.')
        return 0
    # ── THE FIXER CHECKS ITS OWN WORK, against the arm and not against
    #    itself. Re-parsing from disk is the point: an in-memory "I inserted
    #    N names" is the fixer agreeing with the fixer.
    rollup, rows = parse()
    reg = apps_with_registries()
    by_name = {r[0]: r for r in rows}
    left = []
    for app in sorted(set(rollup) & set(reg)):
        if 'NOT YET RE-TIERED' in rollup[app]['status']:
            continue
        names = reg[app]
        if isinstance(names, SHAPE_ERROR):
            continue
        present = {n for n in names if n in by_name}
        for n in rollup_list_gap(rollup[app]['status'], names, present, by_name):
            left.append('%s/%s' % (app, n))
    if left:
        print('\n%d LIST MISSING problem(s) REMAIN after the fix -- %s'
              % (len(left), ', '.join(left)))
        print('Every one of them is a refusal above, or this fixer wrote '
              'something the check does not accept. Either way nothing here '
              'is done.')
        return 1
    print('\nEvery rollup list now names every Tier A row under it. Re-run the '
          'check itself before committing -- this verified ONE arm.')
    return 0


def main(argv):
    quiet = '--quiet' in argv
    problems = []

    if '--fix-rollup-list' in argv:
        if not os.path.isfile(REGISTER):
            print('docs/CRITICALITY-TIERS.md is missing -- that is the finding, '
                  'not a reason to pass.')
            return 1
        return cmd_fix_rollup_lists()

    if not os.path.isfile(REGISTER):
        print('docs/CRITICALITY-TIERS.md is missing -- that is the finding, not a '
              'reason to pass.')
        return 1

    rollup, rows = parse()
    reg = apps_with_registries()
    by_name = {r[0]: r for r in rows}

    for app in sorted(reg):
        if app not in rollup:
            problems.append('NO ROLLUP    %s has a resource registry and no rollup line. '
                            'An app nobody has even said "not yet" about is invisible.'
                            % app)
    for app in sorted(set(rollup) - set(reg)):
        problems.append('GONE         %s has a rollup line and no resource registry.' % app)

    for app in sorted(set(rollup) & set(reg)):
        retiered = 'NOT YET RE-TIERED' not in rollup[app]['status']
        names = reg[app]
        present = {n for n in names if n in by_name}
        if retiered:
            for n in sorted(names - present):
                problems.append('NO TIER      %s/%s is registered and has no row.' % (app, n))
            counts = {'A': 0, 'B': 0, 'C': 0}
            for n in sorted(present):
                t = by_name[n][1]
                if t in counts:
                    counts[t] += 1
            for key, label in (('a', 'A'), ('b', 'B'), ('c', 'C')):
                want = rollup[app][key]
                got = str(counts[label])
                if re.sub(r'[^0-9]', '', want) != got:
                    problems.append('COUNT        %s rollup says %s=%s, the rows say %s. '
                                    'A summary that disagrees with its own detail is worse '
                                    'than no summary.' % (app, label, want, got))
            # ── THE ROLLUP LIST (2026-09-23) ──────────────────────────────
            # The COUNT half of this row has been guarded since this file was
            # written. THE LIST HALF NEVER WAS, and the header below did not
            # claim it either -- which was honest and is now out of date.
            #
            # MEASURED before this was added: the list had drifted in SIX of
            # sixteen apps while EVERY COUNT WAS CORRECT. That is the opposite
            # way round from the obvious guess, and the reason is mechanical
            # rather than about care: a count is one integer that a checker
            # re-derives and refuses, so it stayed right; a list is prose that
            # nothing read, so it rotted. The guarded half was fine and the
            # unguarded half was not, which is the whole argument for guarding
            # this one too.
            #
            # SCOPE, STATED SO IT IS NOT OVERREAD: only backticked names that
            # are REGISTERED RESOURCES OF THIS APP are judged. A rollup cell may
            # legitimately name a file, another app's resource, or a plain-words
            # description, and this refuses to guess about any of those. So a
            # rollup that DESCRIBES its resources instead of naming them is not
            # flagged -- it is simply unverifiable, which is its own problem and
            # not one a set comparison can state.
            listed = listed_names(rollup[app]['status'], names)
            a_rows = {n for n in present if by_name[n][1] == 'A'}
            for n in rollup_list_gap(rollup[app]['status'], names, present, by_name):
                problems.append('LIST MISSING %s/%s is Tier A and is not named in the '
                                'rollup list. Whatever promoted it updated the COUNT and '
                                'not the sentence -- which is how a summary stops being '
                                'readable while still adding up. Do not retype the '
                                'sentence: `python tools/criticality_tier_check.py '
                                '--fix-rollup-list` inserts exactly the names this arm '
                                'is naming and touches nothing else.' % (app, n))
            # ── ONLY NAMES THAT HAVE A ROW, and the reason is a real crash ──
            # The first version of this iterated `listed - a_rows` and read
            # `by_name[n]`. Delete a resource row and that name is still in the
            # rollup list with no row behind it -- KeyError, traceback, exit 1,
            # and the NO TIER problem that was the actual finding never printed.
            # `run_criticality_tier_probe.py` arm 2 caught it on the first run:
            # the arm went red about the marker while the tool was dying. A
            # checker that CRASHES on a register it is meant to describe fails
            # in the one way it must not -- loudly about the wrong thing.
            #
            # A listed name with no row is ALREADY reported, as NO TIER above.
            # Saying it twice in two vocabularies would make one defect look
            # like two.
            for n in sorted((listed & present) - a_rows):
                problems.append('LIST STALE   %s/%s is named in the rollup list and is '
                                'Tier %s. Being in that list IS a claim the row is A.'
                                % (app, n, by_name[n][1]))
        else:
            for n in sorted(present):
                problems.append('HALF DONE    %s/%s has a resource row while the rollup '
                                'says NOT YET RE-TIERED. One of the two is wrong, and a '
                                'half-tiered app reads as an untiered one.' % (app, n))

    all_registered = set()
    for names in reg.values():
        all_registered |= names
    migrated = 0
    stale_boilerplate = []
    for name, tier, conf, worst, worst_read, ev in rows:
        if name not in all_registered:
            problems.append('NOT A RESOURCE  %s has a row and is not registered in any '
                            'api/_resources/*.js. The unit of this table is the registry.'
                            % name)
        if tier not in VALID_TIERS:
            problems.append('BAD TIER     %s has tier %r, not one of %s'
                            % (name, tier, '/'.join(VALID_TIERS)))
        if not worst:
            problems.append('NO WORST CASE  %s states no consequence' % name)
        # A TIER A ROW MUST CARRY ITS OWN EVIDENCE. This is the line that stops
        # the A tier degrading into rule-guessing: B and C are classified by the
        # stated rule, A is hand-verified, and the difference has to be
        # enforceable rather than promised.
        if tier == 'A' and not ev:
            problems.append('NO EVIDENCE  %s is Tier A with an empty evidence cell -- '
                            'that is a label, not a tier.' % name)
        if conf is None:
            # ── §3.4 STEP 4, ARMED 2026-09-22 WHEN THE LAST ROW MIGRATED ────
            # While the migration was in flight this was a silent skip, and it
            # had to be: firing on 387 un-migrated rows is the atomic
            # unreviewable diff step 1 exists to avoid.
            #
            # NOW THAT 387 OF 387 CARRY BOTH AXES, THE SAME SKIP IS A
            # FAIL-OPEN. A row added tomorrow in the old four-cell shape would
            # read as "not migrated yet", quietly bypass the computed-tier
            # cross-check, the per-axis evidence requirement and the
            # access-control refusal, and look exactly like a row that had
            # passed all three. That is the shape CLAUDE.md PR §1.11 names.
            #
            # THE COMPATIBILITY BRANCH IN parse() IS KEPT RATHER THAN DELETED,
            # deliberately: deleting it would make an old-shape row unparseable
            # and it would vanish from the table entirely, which is the same
            # silence one layer down. It is parsed, then refused BY NAME.
            problems.append('NOT MIGRATED  %s is in the old four-cell shape. '
                            'Every row carries both axes as of 2026-09-22, so a '
                            'four-cell row is a new row that skipped them -- and '
                            'a skipped check reads exactly like a passed one.'
                            % name)
            if asserts_access_control(worst, ev):
                stale_boilerplate.append(name)
            continue
        migrated += 1
        # ── §2.3: A MIGRATED ROW MAY NOT CARRY THE FALSE HALF FORWARD ──────
        if asserts_access_control(worst, worst_read, ev):
            problems.append('ASSERTS A GATE  %s has migrated to the two-axis shape '
                            'and still asserts an access-control fact ("auth-gated" '
                            'or similar). That half of the old B sentence was FALSE '
                            'for all 41 SV_RESOURCES rows until 6fb6d696 -- and it '
                            'is TRUE for them now, which is the point rather than a '
                            'reason to relax: nothing in this table verified it '
                            'either way, so the sentence was right by accident on '
                            'one day and wrong on every day before it. State what '
                            'the data IS; whether a gate exists is a code fact this '
                            'file does not assert.'
                            % name)
        if conf not in VALID_TIERS:
            problems.append('BAD CONFIDENTIALITY  %s has confidentiality %r, not one '
                            'of %s' % (name, conf, '/'.join(VALID_TIERS)))
            continue
        # ── THE TIER CELL IS DERIVED, NEVER HAND-ENTERED ────────────────
        # Tier = max(Confidentiality, Integrity/Availability) on the register's
        # own A > B > C worst-consequence order. This is the same principle the
        # rollup cross-check below already applies to a computed TABLE, now
        # applied to a computed CELL: a summary that disagrees with its own
        # detail is worse than no summary. It catches exactly what a human
        # free-typing three letters into adjacent cells gets wrong -- raising
        # one axis and forgetting to bump the derived column.
        # A < B < C alphabetically IS the severity order here, so the worst
        # of the two axes is simply the smaller letter. Written as min()
        # over the pair rather than an if-ladder so a third axis, if one is
        # ever earned, is one list entry rather than a rewrite.
        computed = min([tier, conf])
        if tier != computed:
            problems.append('COMPUTED TIER MISMATCH  %s states Tier %s but '
                            'Confidentiality=%s / Integrity-Availability=%s computes '
                            'to %s. The Tier cell is derived, never hand-entered.'
                            % (name, tier, conf, tier, computed))
        # ── EVIDENCE IS REQUIRED PER AXIS, WHICH IS THE POINT OF THE SPLIT ──
        # Under the single-axis rule sd_exec_msgs never triggered the evidence
        # requirement at all: it was scored B, and B rows are classified by the
        # stated rule rather than individually read. The gap was not a missing
        # rule, it was a missing AXIS for the existing rule to apply to.
        if conf == 'A' and not ev:
            problems.append('NO EVIDENCE (confidentiality)  %s is Confidentiality-A '
                            'with an empty evidence cell.' % name)
        if not worst_read:
            problems.append('NO WORST CASE (read)  %s is migrated but states no '
                            'consequence for being read by the wrong person. An empty '
                            'cell is an unanswered axis, not a low one.' % name)

    # ── THE DOCUMENT'S OWN HEADLINE TOTAL (2026-09-24) ──────────────────────
    # The per-app rollup COUNT has been guarded since this file was written and
    # the rollup LIST since 2026-09-23. The sentence at the top of the file --
    # "All 17 apps are re-tiered: N resources, A A, B B, C C" -- is the same
    # kind of claim one level up and was guarded by NOTHING, which is exactly
    # why it is the figure that keeps rotting. The register's own prose records
    # FOUR separate incidents of it: 229/159 against an actual 231/157,
    # 195/189 against 198/186, two sessions re-deriving it concurrently and
    # disagreeing with each other AND with the merged tree, and 244/144 written
    # against an actual 247/141 on 2026-09-23. Found the fifth on 2026-09-24
    # while re-deriving it for a review: 247/141 stated, 248/140 actual.
    #
    # NOT A `--fix`. The rollup LIST is a restatement of rows and is safe to
    # write; this sentence is a restatement WRAPPED IN AN ARGUMENT -- "that is
    # 63% Tier A, and the distribution is the point" -- and a tool editing
    # numbers inside somebody's prose would be the regenerate-the-judgement
    # failure the header refuses. It is a PROBLEM line: it says what the
    # numbers are, and a person changes the sentence.
    #
    # ABSENT IS NOT CLEAN. A headline that has been deleted or reworded past
    # recognition is a COULD-NOT-TELL, and it says so rather than passing.
    # Read again rather than threaded through parse(): this is a check on the
    # DOCUMENT's prose, not on the table parse() builds, and a reader should
    # not have to know the two come from one string.
    SRC = io.open(REGISTER, encoding='utf-8').read()
    head = re.search(r'(\d+) resources, (\d+) A, (\d+) B, (\d+) C', SRC)
    n_a = sum(1 for r in rows if r[1] == 'A')
    n_b = sum(1 for r in rows if r[1] == 'B')
    n_c = sum(1 for r in rows if r[1] == 'C')
    if not head:
        problems.append('HEADLINE     the "N resources, A A, B B, C C" sentence is '
                        'NOT PRESENT in this file, so the summary a reader meets '
                        'first could not be checked. That is a could-not-tell, not '
                        'a pass -- the rows say %d/%d/%d/%d.'
                        % (len(rows), n_a, n_b, n_c))
    else:
        got = tuple(int(x) for x in head.groups())
        want = (len(rows), n_a, n_b, n_c)
        if got != want:
            problems.append('HEADLINE     the file opens by saying %d resources, '
                            '%d A, %d B, %d C. The rows say %d/%d/%d/%d. A summary '
                            'that disagrees with its own detail is worse than no '
                            'summary, and this is the fifth time this sentence has '
                            'drifted -- re-derive it, never adjust it by the size '
                            'of the edit.' % (got + want))
    # The B-tier bullet restates one of the same four numbers in its own words,
    # so it drifts on its own schedule. Checked separately rather than assumed
    # to move with the headline: they have disagreed with each other before,
    # inside one pair of brackets.
    btier = re.search(r'The B tier is (\d+) rows', SRC)
    if btier and int(btier.group(1)) != n_b:
        problems.append('HEADLINE     "The B tier is %s rows" -- the rows say %d. '
                        'This sentence and the headline above it are two '
                        'restatements of one count and have disagreed with each '
                        'other before.' % (btier.group(1), n_b))

    if not quiet:
        for p in problems:
            print(p)
        print('')
        print('APPS_WITH_REGISTRIES:%d' % len(reg))
        print('RESOURCES_REGISTERED:%d' % len(all_registered))
        # Printed so a partial migration is VISIBLE rather than inferred --
        # the same reason the file's own NOT YET RE-TIERED status exists.
        print('ROWS_MIGRATED_TWO_AXIS:%d of %d' % (migrated, len(rows)))
        # PRINTED CLEAN OR NOT. This is the §2.3 debt: un-migrated rows still
        # asserting a gate nothing verifies. It is not a problem line, because
        # firing on all of them at once is the unreviewable diff §3.4 avoids --
        # but a check that will not fire until a row moves must not be
        # indistinguishable from one that passed, so the number is stated.
        print('ROWS_STILL_ASSERTING_A_GATE:%d (un-migrated; the migrated ones are '
              'refused above)' % len(stale_boilerplate))
        print('RESOURCE_ROWS:%d' % len(rows))
        print('RETIERED_APPS:%d' % sum(
            1 for a in rollup if 'NOT YET RE-TIERED' not in rollup[a]['status']))
        print('TIER_A:%d' % sum(1 for r in rows if r[1] == 'A'))
        print('PROBLEMS:%d' % len(problems))
        if not problems:
            print('')
            print('NOTE: this says every registered resource in a RE-TIERED app has a '
                  'tier, and that every Tier A carries evidence. It does not say the '
                  'tier is right -- nothing mechanical can.')
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
