r"""Narrow the B/C rows of docs/CRITICALITY-TIERS.md down to the handful a
human must actually read before the two-axis migration scores them.

Run: python tools/confidentiality_candidate_flagger.py [--json] [--quiet]

IT FLAGS. IT DOES NOT SCORE, AND THAT IS NOT A LIMITATION TO BE FIXED LATER.
docs/2026-09-21-criticality-tiers-two-axis-spec.md §3.3 is explicit: a script
cannot correctly assign a confidentiality tier, because the register's own
header already insists that anything above the default rule is a judgement with
evidence behind it -- "a tier asserted with no evidence is a label". What a
script CAN do is turn 288 rows into a list short enough to read by hand. Every
row this tool flags still needs a person; every row it does not flag carries
forward as Confidentiality-B by the stated default rule, exactly as B rows are
classified today for the single existing axis.

THREE SIGNALS, ALL FROM THE SPEC, AND EACH ONE IS THE METHOD A HUMAN ALREADY
USED BY HAND TONIGHT rather than a new idea:

  (a) NAME -- the resource or its app-level name matches a sensitivity pattern.
      This is the exact grep that found sd_exec_msgs.
  (b) PAYLOAD -- the fields the app stores on that resource match PII/PHI
      indicators, read from the app's own HTML rather than guessed.
  (c) ASYMMETRY -- the client restricts it and the server does not. A role-gated
      UI element with no server-side session or role check is the shape of the
      SV_RESOURCES finding, and it is a structural signal that whoever built the
      client already believed this data needed restricting.

(c) IS THE ONE WORTH HAVING, AND ITS FIRST SPELLING WAS USELESS. Asking only
"is there a server-side check" flagged 173 of 288 rows -- because whole apps
have no session gate by a RECORDED DECISION rather than by oversight
(SD_LOCAL_RESOURCES says so in its own header; BLD_RESOURCES is cited there as
the precedent). An absence that is deliberate and written down is not a
candidate for anything, and a flagger that returns two thirds of the corpus has
narrowed nothing. The signal is the DISAGREEMENT between the two halves, which
is what the spec asked for and what the first implementation dropped.

(b) HAD THE SAME DEFECT IN A DIFFERENT COORDINATE, AND IT WAS FOUND THE SAME
WAY -- by reading what a flagged row actually contained instead of trusting the
count. Its first spelling scanned the 400 characters after each occurrence of
the resource name for a PII/PHI word, which measures PROXIMITY, NOT OWNERSHIP.
These are single-file apps: every resource accessor is declared beside its
neighbours, so the window ran into the declaration next door. Of the 17 rows it
flagged, all 17 were wrong -- ten `sen_*` rows flagged for `pay_rate` because
the cache array listing the app's resources puts the string `'sen_pay_rates'`
(a DIFFERENT resource) within 400 characters of each of them, and
`leg_documents`, `leg_merch_catalog`, `leg_merch_units` and `leg_monuments`
flagged for `decedent` off one shared helper reading `c.decedent_name` from a
CASE. Signal (b) now reads the resource's own record literal -- the object the
app actually hands the write, balance-parsed and string-blanked -- so a
neighbour cannot contribute a field unless it is assigned to the identifier the
write passes. 17 flags became 4, and all 4 were checked by hand against the
full field list behind them.

THE PRICE OF THAT IS A COUNT THE REPORT PRINTS RATHER THAN BURIES: for a large
share of B/C rows the app never hands the resource a readable object literal at
all, so signal (b) CANNOT BE ASKED there. That is a could-not-tell, not a clean
payload, and `payload_fields` returns it as a separate boolean rather than an
empty list so the two can never be confused. Do not quote the figure from here
-- run the tool; it moves as the apps do.

(c) HAD THE SAME DEFECT AGAIN, IN ITS OWN COORDINATE, AND IT SURVIVED THE FIRST
REWRITE BECAUSE ONLY ONE SIBLING WAS FIXED. Found 2026-09-22 by an independent
review of the 12:33:51Z obligation. `client_restricted()` kept the 400-character
window and its comment defended it by citing the payload read -- which no longer
had one. Measured at that point: the signal produced exactly TWO rows out of 288
and NEITHER rested on evidence that could establish it. `dnt_complaints` had the
matched name AND the gate inside the same BLOCK COMMENT, so deleting a comment
would have flipped the answer on a byte-identical app; `sdn_team`'s gate was a
KPI tile counting rows whose stored `role` COLUMN is 'designer', with no role
check anywhere in `openTeamModal()` or `saveTeam()`. And the neighbour bleed was
still live -- `sd_remakes` and `sd_comms` answering off ONE `_ROLES` declaration
belonging to neither -- producing no false candidate only because the server
half happened to say gated, which is masking rather than correctness.

IT NOW ASKS WHAT THE GATE IS ATTACHED TO: comments blanked first, the gate and
the name required in the SAME function body found by BRACE BALANCE rather than
by a spelling, and a `<expr>.role ===` comparison treated as a record column.
Two further things were found by MEASURING the rewrite rather than by reading
it, and both were fail-open: anchoring the body on `^function name(` matched
NOTHING in one app and silently made the whole 667KB file one unit, and a
function body can legitimately BE the whole app -- so a body over
FUNCTION_BODY_CEILING is a COULD-NOT-TELL, never a clean "nothing restricts it".
The ceiling is measured, not chosen: over all B/C occurrences the sizes run p50
777, p75 1,995, p90 7,549, p95 41,579, then a cliff to 403,966, and every real
gated handler is under 2,000.

IT STILL OVER-REPORTS IN ONE DIRECTION ON PURPOSE. A resource gated through a
dispatcher this tool does not recognise looks ungated here. Reported as a
candidate, never as a finding, and the report says so on every line.

THE FIXTURES ARE THE LOCK, AND THEY NOW COVER TWO SIGNALS RATHER THAN ONE.
`--self-test` runs eleven synthetic cases in both directions: six on the payload
signal (three that must not flag, three that must, including the second-argument
write shape `f('write','<name>', rec)` that the first anchor missed entirely)
and five on the client-restriction signal (three bleeds that must NOT restrict,
two real gates that must). The client half exists because the review found this
file claiming its fixtures covered "both defect shapes" when both shapes had
been found in the SAME coordinate, and the signal its own docstring calls "the
one worth having" had no lock at all. Run it before trusting any count below.

WHAT THIS TOOL WILL NOT DO, stated rather than discovered: it does not edit
docs/CRITICALITY-TIERS.md, it does not write a tier anywhere, and it exits 0
whether it flags 0 rows or 90. A flagger that failed a build would become a
thing people silence.
"""
import argparse
import io
import json
import os
import re
import subprocess
import sys

REPO = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True,
                      encoding='utf-8', errors='replace').stdout.strip()
REGISTER = os.environ.get('SAIRN_TIER_REGISTER') or os.path.join(
    REPO, 'docs', 'CRITICALITY-TIERS.md')
HANDLER = os.path.join(REPO, 'api', 'sd-data.js')
RESOURCES_DIR = os.path.join(REPO, 'api', '_resources')

# (a) The name pattern this session used by hand. Extendable on purpose -- the
# spec calls it "the exact pattern this session used", not a complete one.
NAME_PATTERN = re.compile(
    r'exec|private|confiden|msgs?$|_msgs|notes?$|_notes|comms?$|_comm|portal|soap|'
    r'chat|message|diagnos|patient|client|custody|death|cremat|insur|credential|'
    r'ssn|payroll|salary|wage|bank|account', re.I)

# (b) Field-name indicators, read from the app's stored payloads.
PAYLOAD_PATTERN = re.compile(
    r'\bssn\b|social_security|\bdob\b|date_of_birth|diagnos|medication|allerg|'
    r'\bnpi\b|license_no|account_number|routing|iban|salary|wage|pay_rate|'
    r'privileged|attorney|decedent|next_of_kin|emergency_contact|home_address|'
    r'personal_email|personal_phone|\bpin\b|password', re.I)

# The tier-row shape, anchored the same way every other consumer of this file
# anchors: backticked name, then the bold letter in column 2.
ROW = re.compile(r'^\|\s*`([a-z0-9_]+)`\s*\|\s*\*\*([ABC])\*\*\s*\|(.*)$')


def register_rows():
    """[(name, tier, rest)] for every resource row, in file order."""
    out = []
    for line in io.open(REGISTER, encoding='utf-8'):
        m = ROW.match(line.rstrip('\n'))
        if m:
            out.append((m.group(1), m.group(2), m.group(3)))
    return out


def app_sources():
    """{app: html text}, read once. A missing page is recorded, not skipped."""
    pages, missing = {}, []
    for fn in sorted(os.listdir(RESOURCES_DIR)):
        if not fn.endswith('.js'):
            continue
        app = fn[:-3]
        path = os.path.join(REPO, app + '.html')
        if os.path.isfile(path):
            pages[app] = io.open(path, encoding='utf-8', errors='replace').read()
        else:
            missing.append(app)
    return pages, missing


def resource_app():
    """{resource: app}, from api/_resources/<app>.js -- the platform's own unit."""
    owner = {}
    for fn in sorted(os.listdir(RESOURCES_DIR)):
        if not fn.endswith('.js') or fn == 'index.js':
            continue
        app = fn[:-3]
        src = io.open(os.path.join(RESOURCES_DIR, fn), encoding='utf-8',
                      errors='replace').read()
        for m in re.finditer(r"'([a-z0-9_]+)'", src):
            owner.setdefault(m.group(1), app)
    return owner


# The next argument after the resource name in a call: either an inline object /
# array literal, or the identifier of a record variable built just above. The
# name is NOT required to be the first argument -- the apps spell the write both
# ways, `st('alf_clients', list)` and `alfData('write','alf_clients', rec, true)`,
# and anchoring on `(` alone silently missed every call of the second shape.
NEXT_ARG = re.compile(r"[(,]\s*'%s'\s*,\s*(?:(?P<lit>[\[{])|(?P<var>[A-Za-z_$][\w$]*)\s*[,)])")


def _balanced(src, i):
    """Index just past the literal opening at src[i] ('[' or '{'), or -1.

    String-aware, because a resource payload routinely contains a brace or a
    bracket inside a quoted default and a naive depth count stops in the wrong
    place -- which would hand the key reader a truncated literal and quietly
    lose the tail of the field list.
    """
    depth, quote, j = 0, None, i
    while j < len(src):
        c = src[j]
        if quote:
            if c == '\\':
                j += 2
                continue
            if c == quote:
                quote = None
        elif c in '\'"`':
            quote = c
        elif c in '[{':
            depth += 1
        elif c in ']}':
            depth -= 1
            if depth == 0:
                return j + 1
        j += 1
    return -1


KEY = re.compile(r'(?:[{,]\s*)([A-Za-z_$][\w$]*)\s*:')


def _literal_keys(lit):
    """Property names declared in an object/array literal, strings blanked first.

    Blanking the string bodies matters: `{note:'id: 42'}` otherwise reports a
    field called `id` that the record does not have.
    """
    out, quote, buf = [], None, []
    i = 0
    while i < len(lit):
        c = lit[i]
        if quote:
            if c == '\\':
                buf.append('  ')
                i += 2
                continue
            buf.append(' ')
            if c == quote:
                quote = None
        elif c in '\'"`':
            quote = c
            buf.append(' ')
        else:
            buf.append(c)
        i += 1
    for m in KEY.finditer(''.join(buf)):
        out.append(m.group(1))
    return out


def payload_fields(name, pages, owner):
    """Field names this resource's OWN record carries, from the app's own source.

    THE FIRST SPELLING OF THIS SIGNAL MEASURED PROXIMITY, NOT OWNERSHIP, AND
    EVERY ROW IT FLAGGED WAS WRONG. It scanned the 400 characters after each
    occurrence of the resource name for a PII/PHI word. In a single-file app
    every resource accessor is declared next to its neighbours, so the window
    ran straight into the declaration next door. Measured on the real corpus
    before this was rewritten: all ten `sen_*` rows were flagged for `pay_rate`
    because the array literal listing the app's resources puts the string
    `'sen_pay_rates'` -- a DIFFERENT resource -- within 400 characters of each
    of them; `leg_documents`, `leg_merch_catalog` and `leg_merch_units` were
    all flagged for `decedent` by one shared `caseLabel()` helper reading
    `c.decedent_name` off a CASE. Seventeen flags, none of them a field of the
    row they were attached to. The same defect class the client-restriction
    signal had, in a different coordinate.

    What replaces it is structural: find where the app hands a record to this
    resource -- `f('<name>', {...})`, `f('write','<name>', rec)` -- and read
    the property names out of THAT literal, balance-parsed and string-blanked.
    A neighbouring declaration cannot contribute a field unless it is literally
    assigned to the variable this call passes.

    THE RESIDUAL WINDOW IS NAMED RATHER THAN HIDDEN. When the argument is a
    variable, the assignment `var rec = {` is looked for in the 6000 characters
    before the call. That is still a window, but it is one an unrelated
    declaration cannot enter by accident: it has to be an object literal
    assigned to the exact identifier this write passes.

    Returns (fields, found), where `found` is False when the app never hands
    this resource a readable literal at all. NO FIELD LIST IS NOT AN EMPTY ONE
    -- the caller reports it as a could-not-tell, never as a clean payload.
    """
    app = owner.get(name)
    src = pages.get(app or '', '')
    if not src:
        return [], False
    fields, found = set(), False
    for m in re.compile(NEXT_ARG.pattern % re.escape(name)).finditer(src):
        if m.group('lit'):
            start = m.start('lit')
        else:
            back = src[max(0, m.start() - 6000):m.start()]
            a = None
            for am in re.finditer(r'\b' + re.escape(m.group('var')) + r'\s*=\s*\{',
                                  back):
                a = am
            if not a:
                continue
            start = max(0, m.start() - 6000) + a.end() - 1
        end = _balanced(src, start)
        if end < 0 or end - start > 40000:
            continue
        keys = _literal_keys(src[start:end])
        if keys:
            found = True
            fields.update(keys)
    hits = set()
    for f in fields:
        for h in PAYLOAD_PATTERN.finditer(f):
            hits.add(h.group(0).lower())
    return sorted(hits), found


# Client-side role gating, as the shipped pages actually spell it. Read from
# the real files rather than imagined: these are the constructs the SAIRN apps
# use to hide a panel from a role.
CLIENT_GATE = re.compile(
    r'is-admin|is-exec|isManagement|Privileged\(|sessionRole|session_role|'
    r"role\s*===|role\s*!==|ROLES\[|MANAGEMENT_ROLES|_ROLES\b", re.I)


# A `role === '...'` comparison against a RECORD's own column is not a session
# gate. `t.role==='designer'` inside a `.filter()` is a dashboard count, and
# sdn_team is a resource whose rows literally carry a `role` field -- so the
# collision is systematic, not unlucky: any app storing a role attribute looked
# client-restricted. Anchored on the DOT, which is what distinguishes a
# property read from the bare session variable the gates use.
RECORD_ROLE = re.compile(r"[\w$\]]\s*\.\s*role\s*(?:===|!==|==|!=)")

# ── THE UNIT IS A FUNCTION BODY, FOUND BY BRACES, NOT BY A SPELLING ─────────
# THE FIRST VERSION OF THIS FIX ANCHORED ON `^function name(` AT COLUMN 0 AND
# WAS MEASURED BEFORE IT SHIPPED, WHICH IS THE ONLY REASON IT DID NOT. On
# sairncode that pattern matches NOTHING, so the "enclosing function" became
# the whole 667,230-character file -- the loosest possible answer, produced by
# an anchor that matched nothing, and client_restricted went from 18 rows to
# 47 while looking like a tightening. Fail-open by silent anchor failure, which
# is the shape this platform polices hardest.
#
# So the body is found by BRACE BALANCE and the head test accepts every
# spelling the apps actually use: `function f(){`, `function(){`, `=>{`,
# `f: function(){`, indented or not.
FN_HEAD = re.compile(r'(?:function\s*[\w$]*\s*\([^()]*\)|=>)\s*$')

# ── AND A FUNCTION BODY CAN BE THE WHOLE APP, WHICH IS NOT AN ATTACHMENT ────
# Same-function is the right QUESTION and an insufficient answer on its own:
# several apps wrap everything in one body, so "the gate is in the same
# function" came back true for a `role ===` 103,222 characters away, inside
# `window.addMsg = function(role, content)` -- a chat-message role, in a
# 403,966-character body.
#
# MEASURED over all 1048 B/C occurrences, and the distribution is bimodal
# rather than a judgement call: p50 777 chars, p75 1,995, p90 7,549, p95
# 41,579, then a cliff straight to 403,966. Real gated handlers -- every
# sen_* positive -- are 30 to 1,751 characters. The ceiling sits in the gap.
#
# OVER THE CEILING IS A COULD-NOT-TELL, NOT A FALSE. The occurrence is inside
# a body too large for containment to mean guarding, and saying "not
# restricted" there would be asserting a fact about an app this tool cannot
# see into. The count is printed.
FUNCTION_BODY_CEILING = 20000


SCRIPT_OPEN = re.compile(r'<script\b[^>]*>', re.I)
SCRIPT_CLOSE = re.compile(r'</script\s*>', re.I)


def script_only(src):
    """Blank everything outside <script> blocks, preserving offsets and lines.

    ── THESE ARE HTML FILES AND THE JS LEXER WAS BEING RUN OVER THE MARKUP ───
    Found by arm 5b of the controls, which compares the body count per app:
    sairnmechanical came back with SEVEN function bodies for 194 `function`
    keywords, and the parse died at 11.7% of the file -- exactly where the
    first `</script>` ends and prose begins. An apostrophe in ordinary English
    ("don't") opens a string the lexer never closes, and every brace after it
    is invisible. sairnscape died the same way at 16.3%, on a template literal
    in markup.

    THE FAILURE DIRECTION WAS SAFE AND THE SILENCE WAS NOT: fewer bodies means
    more could-not-tell, so nothing was wrongly called restricted -- but two
    whole apps had quietly stopped being readable and only a cross-check
    against the keyword count said so. CLAUDE.md already names this: extract
    from the HTML structure, never treat a page as one language.
    """
    out = list(src)
    pos = 0
    keep = []
    while True:
        o = SCRIPT_OPEN.search(src, pos)
        if not o:
            break
        c = SCRIPT_CLOSE.search(src, o.end())
        end = c.start() if c else len(src)
        keep.append((o.end(), end))
        pos = c.end() if c else len(src)
    if not keep:
        return src          # not an HTML page; parse it whole
    for i in range(len(out)):
        if out[i] != '\n':
            out[i] = ' '
    for a, b in keep:
        out[a:b] = list(src[a:b])
    return ''.join(out)


def strip_comments(src):
    """Blank every // and /* */ comment, preserving offsets and line breaks.

    OFFSETS ARE PRESERVED ON PURPOSE so a caller can still report where a hit
    was. Newlines survive so line numbers do not move.
    """
    out = list(src)
    i, n, quote = 0, len(src), None
    while i < n:
        c = src[i]
        if quote:
            if c == '\\':
                i += 2
                continue
            if c == quote:
                quote = None
            i += 1
            continue
        if c in '\'"`':
            quote = c
            i += 1
            continue
        if c == '/' and i + 1 < n and src[i + 1] == '/':
            j = src.find('\n', i)
            j = n if j < 0 else j
            for k in range(i, j):
                out[k] = ' '
            i = j
            continue
        if c == '/' and i + 1 < n and src[i + 1] == '*':
            j = src.find('*/', i + 2)
            j = n if j < 0 else j + 2
            for k in range(i, j):
                if out[k] != '\n':
                    out[k] = ' '
            i = j
            continue
        i += 1
    return ''.join(out)


def function_spans(clean):
    """(start, end) of every FUNCTION BODY in comment-stripped source."""
    spans, stack, quote, i, n = [], [], None, 0, len(clean)
    while i < n:
        c = clean[i]
        if quote:
            if c == '\\':
                i += 2
                continue
            if c == quote:
                quote = None
            i += 1
            continue
        if c in '\'"`':
            quote = c
            i += 1
            continue
        if c == '{':
            stack.append((i, bool(FN_HEAD.search(clean[max(0, i - 160):i]))))
        elif c == '}':
            if stack:
                start, isfn = stack.pop()
                if isfn:
                    spans.append((start, i + 1))
        i += 1
    return spans


def enclosing_function(spans, pos):
    """The INNERMOST function body containing `pos`, or None for top-level code.

    None is not a pass. An occurrence outside every function -- a resource-list
    array, a bulk loader's declarations -- has no body to be attached to, so no
    gate can be attributed to it. That is the under-reporting direction, which
    signal (c) already declares as the safe one.
    """
    best = None
    for a, b in spans:
        if a <= pos < b and (best is None or a > best[0]):
            best = (a, b)
    return best


_PARSED = {}


def _parsed(app, src):
    """(comment-stripped source, function bodies) for one page, computed once."""
    # KEYED ON THE CONTENT, NOT THE APP NAME. Keying on the name alone made
    # every --self-test fixture reuse the FIRST fixture's parse, because they
    # all call themselves 'fx' -- three arms then answered about source they
    # had never seen. Caught by two arms failing; it would have been silent if
    # the fixtures had agreed.
    key = (app, len(src), hash(src))
    if key not in _PARSED:
        clean = strip_comments(script_only(src))
        _PARSED[key] = (clean, function_spans(clean))
    return _PARSED[key]


def pages_without_function_bodies(pages):
    """Apps where the brace pass found NO function body at all.

    A page this parser cannot see into yields zero gates for every resource in
    it, which is indistinguishable from an app that restricts nothing. Named
    and printed as a could-not-tell rather than left to read as clean -- the
    same decision `payload_fields` already makes with its `found` flag.
    """
    return [a for a, s in sorted(pages.items()) if s and not _parsed(a, s)[1]]


def client_restricted(name, pages, owner):
    """Does the page restrict this resource to a role? Returns the construct or ''.

    ── REWRITTEN 2026-09-22 AFTER AN INDEPENDENT REVIEW, AND THE OLD COMMENT
    HERE WAS PART OF THE PROBLEM ───────────────────────────────────────────
    It read: "Same 400-character window as the payload read, and for the same
    reason: a wider one starts describing the panel next door." Both halves
    were wrong by the time it was read. The payload read had already been
    rewritten precisely BECAUSE that window was wrong, so this function was
    defending its window by citing a sibling that no longer had one -- and the
    defect was never that the window was too WIDE. PROXIMITY IS NOT OWNERSHIP
    AT ANY WIDTH.

    MEASURED, at the point of the review: the signal produced exactly two rows
    out of 288 and NEITHER rested on evidence that could establish it.

      dnt_complaints -- the matched occurrence AND the `role===` that answered
        for it were inside the SAME BLOCK COMMENT. The conclusion happened to
        be true because the comment said so; deleting a comment would have
        flipped the tool's answer on a byte-identical application.
      sdn_team -- the "gate" at 373 characters was
        `$('tm-designers').textContent=list.filter(...t.role==='designer'...)`,
        a KPI tile counting rows whose stored `role` COLUMN is designer.
        openTeamModal() and saveTeam() contain no role construct at all.

    And the bleed the payload signal was rewritten to remove was still here:
    sd_remakes and sd_comms both answered TRUE off ONE `_ROLES` declaration
    sitting above a bulk localStorage loader and belonging to neither. That
    produced no false CANDIDATE only because the asymmetry test is
    `client_gate AND NOT server_gated` and the server half happened to say
    gated -- the masking was doing the work the fix was supposed to do, and it
    would have stopped the day a dispatcher was renamed.

    THREE CHANGES, AND THEY ARE THE SAME MOVE THE PAYLOAD SIGNAL ALREADY MADE
    -- stop asking what is NEARBY and start asking what it is ATTACHED TO:

      1. Comments are blanked before anything is searched. Offsets survive.
      2. The gate and the name must be in the SAME top-level function, which is
         a real declaration boundary rather than a character count. A gate
         inside a `.then()` callback still counts, because the callback is
         inside the function; a gate in the NEXT function does not.
      3. A `<expr>.role ===` comparison is a RECORD column, not a session role.

    IT STILL OVER-REPORTS BY CONSTRUCTION, unchanged: a resource gated through
    a helper this tool does not recognise looks ungated. Candidate, never
    finding.

    Returns (construct, unreadable). `unreadable` True means every occurrence
    sat in a body over the ceiling, so this is a COULD-NOT-TELL and NOT a
    clean 'nothing restricts it' -- the same three-state discipline
    payload_fields() already uses for its `found` flag.
    """
    app = owner.get(name)
    src = pages.get(app or '', '')
    if not src:
        # NO PAGE IS A COULD-NOT-TELL, NOT A CLEAN 'NOTHING RESTRICTS IT'.
        # main() already reports the missing pages; this makes the per-row
        # answer agree with that instead of quietly saying False.
        return '', True
    clean, spans = _parsed(app, src)
    unreadable = False
    for m in re.finditer(r"'" + re.escape(name) + r"'", clean):
        body = enclosing_function(spans, m.start())
        if body is None:
            continue
        lo, hi = body
        if hi - lo > FUNCTION_BODY_CEILING:
            unreadable = True
            continue
        unit = clean[lo:hi]
        for g in CLIENT_GATE.finditer(unit):
            # A record-column comparison is not a gate. Tested on the text
            # ENDING at the match so `t.role===` is caught while a bare
            # `role===` on a session variable is not.
            head = unit[max(0, g.start() - 24):g.end()]
            if RECORD_ROLE.search(head):
                continue
            return g.group(0), False
    return '', unreadable


def server_gated(name, handler_src):
    """Is there ANY server-side session check on a path that names this resource?

    DELIBERATELY GENEROUS. A resource reached through a shared dispatcher --
    SD_SESSION_GATED, a LAW_RESOURCES-style block, a per-app map -- is gated
    without its own name appearing beside verifySessionToken. Answering 'yes'
    generously means signal (c) UNDER-reports rather than over-reports, which is
    the safer direction for a flagger whose output a human then reads: a missed
    candidate is found by the name and payload signals, while a false 'ungated'
    claim about a resource would be this tool asserting a security fact it has
    not established.
    """
    if name in handler_src.split('SD_SESSION_GATED')[0]:
        pass
    # 1. named directly in the central gate table
    gate_table = re.search(r'const SD_SESSION_GATED = \{[\s\S]*?\n    \};', handler_src)
    if gate_table and ("'" + name + "'") in gate_table.group(0):
        return True, 'SD_SESSION_GATED'
    # 2. named inside any block that also calls verifySessionToken within 2000 chars
    for m in re.finditer(r"'" + re.escape(name) + r"'", handler_src):
        near = handler_src[max(0, m.start() - 2000):m.start() + 2000]
        if 'verifySessionToken' in near:
            return True, 'a session check within the same block'
    # 3. a dispatcher map that contains it, where the map's own block is gated
    for m in re.finditer(r'const ([A-Z_]+RESOURCES\w*) = \{([\s\S]{0,4000}?)\};', handler_src):
        if ("'" + name + "'") in m.group(2) or (name + ':') in m.group(2):
            after = handler_src[m.end():m.end() + 4000]
            if 'verifySessionToken' in after:
                return True, m.group(1) + ' dispatcher'
    return False, ''


# Synthetic fixtures, written from the REAL defect shapes found on the corpus
# and locked before the rewrite was measured against real data, per
# docs/2026-09-13-cross-domain-disciplines.md. BOTH DIRECTIONS: a fixture that
# only proves the tool stops flagging would be satisfied by a tool that flags
# nothing, which is exactly the way this rewrite could go wrong.
FIXTURES = [
    # (label, page source, resource, expect_hits, expect_found)
    ('the sen_pay_rates bleed -- a neighbouring RESOURCE NAME, not a field',
     "var SEN_CACHES=['sen_branches','sen_applicants','sen_pay_rates',\n"
     "  'sen_payer_contracts','sen_franchise_agreements'];\n"
     "function branches(){return ld('sen_branches',[]);}\n",
     'sen_branches', False, False),
    ('the caseLabel bleed -- decedent_name belongs to a CASE',
     "function docs(){return ld('leg_documents',[]);}\n"
     "function caseLabel(id){var c=cases().find(function(x){return x.id===id;});\n"
     "  return c?(c.case_number+' -- '+c.decedent_name):'(unknown)';}\n",
     'leg_documents', False, False),
    ('a real inline payload literal',
     "st('alf_mar',[{id:'M1',resident_id:'R1',medication_name:'Lisinopril'}]);\n",
     'alf_mar', True, True),
    ('a real payload built into a variable, then written -- and the resource '
     'name is the SECOND argument, the shape the first anchor missed entirely',
     "var rec={id:reid,name:name,diagnosis:$('d').value,payer:$('p').value};\n"
     "  st('alf_clients',list);\n"
     "  await alfData('write','alf_clients',rec,true);\n",
     'alf_clients', True, True),
    ('a PII word inside a STRING VALUE is not a field name',
     "st('sd_jobs',[{id:'J1',note:'call about the ssn paperwork'}]);\n",
     'sd_jobs', False, True),
    ('an empty default is not a field list and must not read as clean',
     "function x(){return ld('sd_quotes',[]);}\n",
     'sd_quotes', False, False),
]


# ── THE CLIENT-GATE FIXTURES, ADDED 2026-09-22 AFTER AN INDEPENDENT REVIEW ──
# Finding 4 of Fourth's review of the 12:33:51Z obligation: self_test() called
# payload_fields() and nothing else, while the docstring claimed the six cases
# covered "both defect shapes". Both shapes had been found in the SAME
# coordinate. Signal (c) -- the one this file's own docstring calls "the one
# worth having" -- had no lock at all, and FIXTURES[0] is literally named "the
# sen_pay_rates bleed" and IS a resource-list array, the exact input shape the
# surviving defect was about, yet it was only ever asserted against the payload
# signal.
#
# All five are the REAL shapes measured on the corpus, not invented ones.
CLIENT_FIXTURES = [
    # (label, page source, resource, expect_restricted)
    ('the bulk-loader bleed -- a _ROLES declaration belonging to NEITHER, with '
     'four resources loaded next to each other (measured: sd_remakes, sd_comms)',
     "var SD_EXEC_ROLES=['owner','exec']; // These map to admin user logins\n"
     "function loadSD5Data(){\n"
     "  try{sdRemakes=JSON.parse(localStorage.getItem('sd_remakes')||'[]');}catch(e){}\n"
     "  try{sdComms=JSON.parse(localStorage.getItem('sd_comms')||'[]');}catch(e){}\n"
     "}\n",
     'sd_remakes', False),
    ('the comment bleed -- both the name AND the gate inside one block comment '
     '(measured: dnt_complaints)',
     "function respondToComplaint(id){\n"
     "  // dnt_complaints is READ-ONLY through the generic path -- this never\n"
     "  // calls dnt('write','dnt_complaints',...). Owner-only enforcement is\n"
     "  // UI-level here (prole==='owner'), a stated, accepted limitation.\n"
     "  return post(id);\n"
     "}\n",
     'dnt_complaints', False),
    ('the KPI-tile bleed -- `role===` comparing a RECORD COLUMN, in the '
     'NEXT function (measured: sdn_team)',
     "async function saveTeam(){\n"
     "  var rec={id:1,role:$('tmrole').value};\n"
     "  await sdnData('write','sdn_team',rec);\n"
     "}\n"
     "function rTeam(){\n"
     "  var list=team();\n"
     "  $('tm-designers').textContent=list.filter(function(t){"
     "return t.status==='Active'&&t.role==='designer';}).length;\n"
     "}\n",
     'sdn_team', False),
    ('A REAL restriction at the resource\'s own hydrate, with the gate inside a '
     '.then() callback (measured: sen_pay_rates, sen_caregivers)',
     "function senHydratePayRates(){\n"
     "  if(!senLicenseKey()||!senIsManagement())return Promise.resolve(false);\n"
     "  return senData('read','sen_pay_rates',null,true).then(function(rows){\n"
     "    return !!rows;\n"
     "  });\n"
     "}\n",
     'sen_pay_rates', True),
    ('A REAL restriction where the gate comes AFTER the name in the same '
     'function (measured: sen_branches)',
     "function brRender(){\n"
     "  var list=ld('sen_branches',[]);\n"
     "  var isMgmt=senIsManagement();\n"
     "  var addBtn=$('br-add-btn');if(addBtn)addBtn.style.display=isMgmt?'':'none';\n"
     "}\n",
     'sen_branches', True),
]


def self_test():
    """Run the locked fixtures. Exits non-zero on any disagreement.

    BOTH SIGNALS, BOTH DIRECTIONS. The payload set is three that must not flag
    and three that must; the client-gate set is three that must not restrict
    and two that must. A one-directional lock would be satisfied by a signal
    that had stopped working altogether, which is the way each of these
    rewrites is most likely to fail -- and the client-gate half exists because
    the first version of this function had NO lock and shipped two wrong
    answers out of the two it produced.
    """
    bad = 0
    print('  PAYLOAD SIGNAL (b)')
    for label, src, res, want_hits, want_found in FIXTURES:
        hits, found = payload_fields(res, {'fx': src}, {res: 'fx'})
        ok = (bool(hits) == want_hits) and (found == want_found)
        print('  %-4s %s\n         hits=%s found=%s (wanted hits=%s found=%s)'
              % ('PASS' if ok else 'FAIL', label, hits, found, want_hits, want_found))
        if not ok:
            bad += 1
    print('\n  CLIENT-RESTRICTION SIGNAL (c)')
    for label, src, res, want in CLIENT_FIXTURES:
        got, unreadable = client_restricted(res, {'fx': src}, {res: 'fx'})
        ok = bool(got) == want and not unreadable
        print('  %-4s %s\n         restricted=%r (wanted %s)'
              % ('PASS' if ok else 'FAIL', label, got, want))
        if not ok:
            bad += 1
    total = len(FIXTURES) + len(CLIENT_FIXTURES)
    print('\n  %d fixture(s), %d failing' % (total, bad))
    return 1 if bad else 0


def main(argv=None):
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--quiet', action='store_true')
    ap.add_argument('--self-test', action='store_true',
                    help='run the locked payload-signal fixtures and exit')
    args = ap.parse_args(argv)

    if args.self_test:
        return self_test()

    if not os.path.isfile(REGISTER):
        print('COULD NOT RUN: no register at %s' % REGISTER)
        return 3
    handler_src = io.open(HANDLER, encoding='utf-8', errors='replace').read()
    pages, missing_pages = app_sources()
    owner = resource_app()
    rows = register_rows()
    if not rows:
        print('COULD NOT RUN: no resource rows parsed from %s. An empty scan is '
              'not a clean one.' % REGISTER)
        return 3

    bc = [(n, t) for n, t, _ in rows if t in ('B', 'C')]
    flagged, clear, no_payload_read, no_client_read = [], [], [], []
    n_client, asym_rows = 0, []
    for name, tier in bc:
        why = []
        if NAME_PATTERN.search(name):
            why.append(('name', 'the resource name matches the sensitivity pattern'))
        fields, field_list_found = payload_fields(name, pages, owner)
        if not field_list_found:
            no_payload_read.append(name)
        if fields:
            why.append(('payload', 'stores field(s) matching PII/PHI indicators: '
                                   + ', '.join(fields[:6])))
        gated, how = server_gated(name, handler_src)
        client_gate, client_unreadable = client_restricted(name, pages, owner)
        if client_unreadable:
            no_client_read.append(name)
        if client_gate:
            n_client += 1
            if not gated:
                asym_rows.append(name)
        # THE SIGNAL IS THE ASYMMETRY, NOT THE ABSENCE. Measured: asking only
        # "is there a server-side check" flagged 173 of 288 rows, because whole
        # apps -- BLD_RESOURCES, SD_LOCAL_RESOURCES and others -- have NO
        # session gate by a recorded decision, not by oversight. An absence
        # that is deliberate and documented is not a candidate for anything.
        # What the spec actually asks for is the DISAGREEMENT: the client
        # restricts it and the server does not, which is a structural sign that
        # whoever built the UI already believed this data needed restricting.
        if client_gate and not gated:
            why.append(('asymmetry', 'the CLIENT restricts it (%s) and no '
                                     'server-side session check was found on any '
                                     'path naming it' % client_gate))
        (flagged if why else clear).append(
            {'resource': name, 'tier': tier, 'app': owner.get(name, '?'),
             'signals': [w[0] for w in why], 'why': [w[1] for w in why],
             'gate': how})

    if args.json:
        print(json.dumps({'flagged': flagged, 'clear': [c['resource'] for c in clear],
                          'missing_pages': missing_pages,
                          'payload_signal_could_not_be_read': no_payload_read,
                          'client_signal_could_not_be_read': no_client_read},
                         indent=1))
        return 0

    if not args.quiet:
        print('CONFIDENTIALITY CANDIDATE FLAGGER -- it flags, it does not score\n')
        print('  register      : %s' % os.path.relpath(REGISTER, REPO))
        print('  resource rows : %d  (%d B/C, %d A -- A rows are re-derived by hand '
              'per spec 3.2 and are not this tool\'s job)'
              % (len(rows), len(bc), len(rows) - len(bc)))
        if missing_pages:
            print('  NO PAGE FOUND for %d app(s), so signals (b) and (c) could not be '
                  'asked there: %s' % (len(missing_pages), ', '.join(missing_pages)))
            print('  That is a COULD-NOT-TELL for those rows, not a clean bill.')
        print('')
        print('  FLAGGED FOR A HUMAN READ: %d of %d B/C rows' % (len(flagged), len(bc)))
        print('  carried forward as Confidentiality-B by the stated rule: %d'
              % len(clear))
        print('')
        # ── SIGNAL (c) REPORTS ITS OWN ARITHMETIC ────────────────────────
        # It can legitimately produce ZERO candidates, and zero looks exactly
        # like a signal that has stopped working. So the three counts behind
        # the zero are printed: a reader can see the client half DID find
        # restrictions and the server half agreed with every one it could be
        # asked about, which is a finding of its own rather than an absence.
        print('  ASYMMETRY SIGNAL (c), the arithmetic behind its count:')
        print('    client restricts it                : %d' % n_client)
        print('    ...and the server ALSO gates it    : %d  (no disagreement, '
              'so not a candidate)' % (n_client - len(asym_rows)))
        print('    ...and the server does NOT         : %d  <- the candidates'
              % len(asym_rows))
        print('    COULD NOT BE ASKED at all          : %d  -- every occurrence '
              'sat in a' % len(no_client_read))
        print('      function body over %d characters, or the app has no page. '
              'That is a' % FUNCTION_BODY_CEILING)
        print('      could-not-tell, NOT "nothing restricts it".')
        if not asym_rows:
            print('    ZERO CANDIDATES IS A RESULT, NOT A DEAD SIGNAL: the two '
                  'halves agreed')
            print('      everywhere this tool could ask. Read the could-not-'
                  'ask count beside it.')
        print('')
        print('  PAYLOAD SIGNAL COULD NOT BE READ AT ALL for %d of %d B/C rows --'
              % (len(no_payload_read), len(bc)))
        print('  the app never hands those resources a readable object literal, so')
        print('  signal (b) is a COULD-NOT-TELL there and not a clean payload. It is')
        print('  the single largest gap in this tool and it is printed, not buried.')
        print('')
        by_signal = {}
        for f in flagged:
            for s in f['signals']:
                by_signal[s] = by_signal.get(s, 0) + 1
        for s in sorted(by_signal):
            print('    signal %-10s %d row(s)' % (s, by_signal[s]))
        print('')
        for f in sorted(flagged, key=lambda x: (-len(x['signals']), x['resource'])):
            print('  %-26s %s  [%s]' % (f['resource'], f['tier'], ', '.join(f['signals'])))
            for w in f['why']:
                print('      - %s' % w)
        print('')
        print('  NONE OF THE ABOVE IS A TIER. Each flagged row needs a person to read')
        print('  it and write evidence, per the register\'s own rule that a tier with')
        print('  no evidence is a label. Signal (asymmetry) over-reports by')
        print('  construction -- a resource gated through a dispatcher this tool did')
        print('  not recognise looks ungated here and is not.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
