#!/usr/bin/env python
r"""service_role_tier_a_gate_check.py -- item 40, continued. A module holding
the key that BYPASSES RLS, writing a Tier A resource, with nothing gating it.

    python tools/service_role_tier_a_gate_check.py
    python tools/service_role_tier_a_gate_check.py --json
    python tools/service_role_tier_a_gate_check.py --self-check

Exit 0 / 1 / 2 per tools/checker_kit.py's contract. REPORT ONLY.

BUILT THROUGH tools/checker_kit.py (item 28) RATHER THAN AROUND IT -- the exit
contract, the tracked-file walk and the comment-stripped parsing all come from
there. That is not tidiness: the first draft of
tools/advisory_lock_isolation_check.py hand-rolled its own SQL comment stripper
on 2026-09-15 and shipped a bug the kit did not have.

── WHY THIS IS NOT tools/secrets_inventory.py's QUESTION ───────────────────
`docs/SECRETS-INVENTORY.md` reports SUPABASE_SERVICE_ROLE_KEY "guarded in 61 of
63". **GUARDED THERE MEANS "the code checks the variable is SET".** That is a
configuration question. It says nothing about whether a CALLER was
authenticated before the module used that key to write a Tier A row, and the
two are routinely confused because they share the word.

This asks the second question, which is the one the 2026-09-14 audit left
explicitly unresolved.

── THE THREE THINGS IT SEPARATES, BECAUSE COLLAPSING THEM PRODUCES NOISE ───
  GATED            a session, licence or cron-secret check appears BEFORE the
                   first write in the file.
  PUBLIC_BY_DESIGN the module says in its own header that it is deliberately
                   unauthenticated. `api/sairndental/public-book.js` opens with
                   "Genuinely public, unauthenticated endpoint" and refuses
                   when its rate-limit store is unreachable. Reporting that as
                   an ungated Tier A write would be reporting a decision as a
                   defect -- and a checker that does it once gets switched off.
  UNGATED          neither. This is the finding.

A PUBLIC_BY_DESIGN module with NO rate limit at all is still a finding, because
the design note is a claim about intent and the limiter is the mechanism.

── WHAT IT CANNOT SEE, AND THE FALSE POSITIVE THAT MOTIVATED HALF OF IT ────
RESOURCE NAMES ARE MATCHED IN CODE ONLY. Comments and string literals are
blanked first, via checker_kit. Measured on the first run: `api/bridge.js`
appeared to name the Tier A resource `invoices` FOUR times -- three were prose
in its header block and the fourth was `body.invoices`, a REQUEST FIELD that
happens to share the word. A naive grep reports that module as an ungated Tier
A writer. It is not one.

ORDER IS A PROXY, AND A CRUDE ONE. "The gate appears before the first write"
is a byte-offset comparison, not control flow. It cannot see a gate inside a
branch the write does not depend on, and it cannot see a gate in a module this
one requires. It is therefore biased toward calling things GATED, which is the
direction that misses findings rather than inventing them -- stated here so
nobody reads a GATED verdict as a proof.
"""

import argparse
import io
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))

from checker_kit import (EXIT_CLEAN, EXIT_FINDING, EXIT_COULD_NOT_RUN,  # noqa: E402
                         tracked, strip_comments, finish, read)

KEY = 'SUPABASE_SERVICE_ROLE_KEY'
TIERS_DOC = os.path.join(REPO, 'docs', 'CRITICALITY-TIERS.md')
TIER_A_ROW = re.compile(r'^\|\s*`(\w+)`\s*\|\s*\*\*A\*\*', re.M)

# A caller-identity check. NOT an env-presence check -- that is the other
# question and the one this file exists to separate from.
GATES = (
    'verifySessionToken', 'requireSession', 'tokenFromRequest',
    'validateLicense', 'licenseFromRequest', 'resolveLicense', 'requireLicense',
    'licenseHashFromRequest', 'CRON_SECRET', 'requireCronSecret',
)
# Not identity, but a real access control on a deliberately public path.
LIMITS = ('rate_limit', 'rateLimit', 'checkAndLog', 'consumeAtomic', 'RATE_LIMIT')
# The module's own statement that it is unauthenticated on purpose.
PUBLIC_DECL = re.compile(
    r'(genuinely public|unauthenticated endpoint|no license key anywhere|'
    r'public, unauthenticated|deliberately public)', re.I)
WRITE = re.compile(r"method\s*:\s*['\"](POST|PATCH|PUT|DELETE)['\"]", re.I)


def tier_a_resources():
    try:
        return set(TIER_A_ROW.findall(read(TIERS_DOC)))
    except OSError as exc:
        return None


def classify(rel, src):
    """(verdict, detail). `src` is the RAW text; stripping happens here."""
    # COMMENTS ONLY -- strings=False, and that is a correction rather than a
    # default. `strings=True` blanks string INTERIORS, and a resource name in
    # this codebase lives almost entirely inside one: fetch(rest('law_trusttx
    # ?...')). Blanking strings destroyed the real signal and the fixtures said
    # so immediately -- every arm collapsed to NO_WRITE because `method:'POST'`
    # went with it. The rule is that the stripping mode follows what the
    # checker's subject actually is, and here the subject lives in strings.
    code = strip_comments(src, strings=False)
    # ── THE RESOURCE MUST APPEAR IN A REST PATH, NOT MERELY IN THE FILE ─────
    # THIS IS THE THIRD VERSION OF THIS RULE AND THE FIRST CORRECT ONE, and the
    # two it replaces are both recorded because each was wrong in a different
    # direction on a real file.
    #
    #   v1, "the name appears anywhere": reported api/bridge.js as an ungated
    #       Tier A writer. Three of its four `invoices` hits were header prose
    #       and the fourth was `body.invoices`, a request field sharing a word
    #       with a SAIRNlaw table.
    #   v2, "...and it is not an object key": killed bridge.js and ALSO killed
    #       api/sv-witness.js, whose only reference is
    #       `const LOCKED_RESOURCES = { sv_controlled: true }` -- a policy
    #       registry, which is a genuine reference. SUPPRESSING A TRUE POSITIVE
    #       ON THE DEA-RELEVANT WITNESSING LOCK TO SILENCE ONE FALSE ALARM IS A
    #       BAD TRADE, and it was caught only by asking why a module had
    #       vanished from the report between two runs.
    #
    # v3 asks the question the verdict actually turns on: is this resource the
    # TARGET OF A WRITE? Every write on this platform addresses its table in the
    # path -- `/rest/v1/<name>` or `rest('<name>?...')`. bridge.js writes to
    # `bridge_data` and puts `invoices` inside the jsonb BLOB, so it is
    # correctly out; a module that genuinely POSTs to a Tier A table cannot be.
    PATH = re.compile(r"(?:/rest/v1/|rest\(\s*['\"])(\w+)")
    addressed = set(PATH.findall(code))

    # ── v4: A RESOURCE DISPATCHED THROUGH A VARIABLE IS STILL ADDRESSED ────
    # v3's path regex requires a QUOTED LITERAL after `rest(`, so it was
    # structurally blind to the shape this platform uses most:
    #
    #     const SV_RESOURCES = { sv_controlled: 'controlled_id', ... };
    #     if (SV_RESOURCES[resource] && action === 'write') {
    #       ... fetch(rest(resource + '?license_hash=eq.' + enc(licHash)), ...)
    #
    # MEASURED BEFORE THE FIX: 41 of 84 Tier A resources appear ONLY as keys of
    # a dispatch table and never as a quoted path -- including `sv_controlled`,
    # the DEA-relevant controlled-substance register, and `sv_audit_log`, which
    # carries the witnessing lock. The checker reported CLEAN over all of them.
    # A blind spot that covers half the Tier A surface is not a narrow rule, it
    # is a checker measuring the wrong thing and saying nothing.
    #
    # THE RESOLUTION IS DELIBERATELY NARROW. A Tier A name used as an OBJECT KEY
    # beside a variable-dispatched `rest(` call is a dispatch table -- that is
    # what a dispatch table looks like, and v2's own recorded lesson is that a
    # policy registry like `{ sv_controlled: true }` is a GENUINE reference, not
    # noise to suppress. The key form alone is not enough: without a
    # variable-dispatched call in the file, an object key is just an object key.
    # A TABLE NAME ASSIGNED TO A VARIABLE FIRST IS STILL A LITERAL, and the
    # first draft of this rule missed that: `const sel = 'mech_credentials?...'
    # ; rest(sel)` is the ordinary shape in this codebase, and treating every
    # such file as unresolvable produced COULD_NOT_TELL on dozens of modules
    # that name their table perfectly clearly one line up. A third state that
    # fires on the normal case is noise, and noise is how a checker gets muted.
    QUERY = re.compile(r"['\"](\w+)\?")
    addressed |= set(QUERY.findall(code))
    # AND THE TABLE CAN BE THE VALUE RATHER THAN THE KEY:
    #     const AUTH_TABLE_BY_APP = { stonedesk: 'sd_employee_auth', ... };
    #     fetch(rest(AUTH_TABLE_BY_APP[app] + '?...'))
    # A QUOTED TOKEN THAT IS EXACTLY A TIER A NAME is a reference to that table.
    # This is much tighter than v1's rejected "the name appears anywhere": that
    # matched header prose and `body.invoices`, and neither is a standalone
    # quoted string equal to a registered resource name.
    QUOTED = re.compile(r"['\"](\w+)['\"]")
    addressed |= (set(QUOTED.findall(code)) & set(TIER_A))
    # A MODULE CONSTANT IS ALSO RESOLVABLE, and missing that made the third
    # state fire on files that are perfectly readable. api/_lib/ai-rate-limit.js
    # does `const TABLE = 'sairn_ai_rate_limit_log'; rest(TABLE)` -- the table
    # is right there, it simply is not Tier A, so the correct answer is "no Tier
    # A resource" and not "cannot tell". Thirty-odd files were reported
    # unreadable for this reason on the first draft.
    CONSTVAL = re.compile(r"(?:const|let|var)\s+\w+\s*=\s*['\"]([^'\"]*)['\"]")
    const_values = set(CONSTVAL.findall(code))
    addressed |= {v.split('?')[0] for v in const_values}
    # NOT THE DEFINITION OF THE HELPER ITSELF. `function rest(path) {` matches
    # a naive "rest(<identifier>" and made six modules look like variable
    # dispatchers when they were merely declaring the helper every module uses.
    VARCALL = re.compile(r"(?<!function )(?<!function  )rest\(\s*[A-Za-z_]\w*")
    TABLEKEY = re.compile(r"(\w+)\s*:\s*['\"]")
    var_dispatched = bool(VARCALL.search(code))
    resolved = set()
    if var_dispatched:
        resolved = set(TABLEKEY.findall(code)) & set(TIER_A)
        addressed |= resolved

    names = sorted(addressed & set(TIER_A))

    # ── COULD NOT TELL IS A THIRD STATE HERE TOO (PR 1.11) ─────────────────
    # A file that dispatches through a variable and offers NO table this can
    # resolve is a file whose Tier A surface is unknown. Reporting it as "no
    # Tier A resource" would be the v3 defect with extra steps.
    # THE THIRD STATE FIRES ONLY WHEN THE FILE IS GENUINELY OPAQUE: it
    # dispatches through a variable AND offers neither a dispatch table nor a
    # resolvable string constant. A file that names its table one line up is
    # readable, and calling it unreadable is the over-report that gets a
    # checker muted.
    if var_dispatched and not resolved and not names and not const_values:
        return 'COULD_NOT_TELL', {
            'resources': [],
            'why': 'calls rest(<variable>) and declares no resolvable dispatch '
                   'table, so which tables it addresses cannot be read from the '
                   'source. Not reported as clean.'}
    if not names:
        return None, {}
    names = set(names)
    # ── ORDER IS MEASURED INSIDE THE HANDLER, NOT ACROSS THE WHOLE FILE ────
    # SECOND FALSE POSITIVE, and it would have been the expensive one.
    # api/sairndental/send-reminder.js writes at lines 58 and 79 -- inside
    # HELPER FUNCTIONS DEFINED ABOVE the handler -- and checks CRON_SECRET at
    # line 103, the first thing the handler does. A whole-file offset
    # comparison reports that as "the identity check appears AFTER the first
    # write", which is a false alarm about an ungated Tier A write on a cron
    # endpoint that is correctly gated. That is the exact kind of finding that
    # gets a checker switched off.
    #
    # So the window starts at `module.exports`. A file with no export is scanned
    # whole and SAYS SO in its detail, rather than being silently treated as
    # though it had one.
    exp = code.find('module.exports')
    window = code[exp:] if exp != -1 else code
    base = exp if exp != -1 else 0

    # EXISTENCE IS ASKED FILE-WIDE, ORDER IS ASKED INSIDE THE HANDLER, and the
    # split is the whole correction. A module whose write lives in a HELPER
    # defined above the export still writes -- asking both questions in the
    # handler window reported send-reminder.js as NO_WRITE, which is a
    # different wrong answer from the one it started with.
    w_file = WRITE.search(code)
    if not w_file:
        return 'NO_WRITE', {'resources': sorted(names),
                            'why': 'names a Tier A resource but issues no write verb'}
    w = WRITE.search(window)
    gate_at = min([window.find(g) for g in GATES if g in window] or [-1])
    limit_at = min([window.find(g) for g in LIMITS if g in window] or [-1])

    if w is None:
        # The handler itself writes nothing; the writes are in helpers it calls.
        # A gate ANYWHERE in the handler therefore runs before any of them,
        # because the handler has to reach the call to make one happen. Stated
        # rather than folded in, because it is a different argument from an
        # offset comparison and it is the one that fits a cron endpoint.
        d = {'resources': sorted(names), 'write_at': w_file.start(),
             'gate_at': gate_at, 'limit_at': limit_at,
             'scanned': 'handler only; writes are in helpers above it',
             'declared_public': bool(PUBLIC_DECL.search(src))}
        if gate_at != -1:
            d['why'] = ('the write is in a helper defined above the handler, and '
                        'the handler gates before it can call one')
            return 'GATED', d
        if d['declared_public'] and limit_at != -1:
            d['why'] = 'declares itself public and limits before calling a writer'
            return 'PUBLIC_BY_DESIGN', d
        d['why'] = ('writes through a helper and the exported handler contains '
                    'no identity check or limiter at all')
        return 'UNGATED', d
    declared_public = bool(PUBLIC_DECL.search(src))   # the DECLARATION is prose
    d = {'resources': sorted(names), 'write_at': base + w.start(),
         'gate_at': gate_at, 'limit_at': limit_at,
         'scanned': 'handler only' if exp != -1 else 'WHOLE FILE -- no module.exports',
         'declared_public': declared_public}
    if gate_at != -1 and gate_at < w.start():
        d['why'] = 'an identity check appears before the first write'
        return 'GATED', d
    if declared_public:
        if limit_at != -1 and limit_at < w.start():
            d['why'] = ('declares itself public and carries a rate limit before '
                        'the write')
            return 'PUBLIC_BY_DESIGN', d
        d['why'] = ('DECLARES ITSELF PUBLIC AND HAS NO LIMITER BEFORE THE WRITE '
                    '-- the note is a claim about intent, the limiter is the '
                    'mechanism, and only one of them stops anything')
        return 'UNGATED', d
    if gate_at != -1:
        d['why'] = ('an identity check exists but appears AFTER the first write '
                    'in file order -- read it, this is an order proxy and not '
                    'control flow')
        return 'UNGATED', d
    d['why'] = 'holds the RLS-bypassing key, writes a Tier A resource, and no '\
               'identity check or rate limit appears anywhere in the file'
    return 'UNGATED', d


# ── THE VERDICT VOCABULARY, DECLARED ────────────────────────────────────────
# Added 2026-09-18 after v4 shipped a FIFTH verdict, COULD_NOT_TELL, and broke
# tests/run_service_role_gate_probe.py's arm asserting the fixture set reaches
# "all four verdicts plus None". The arm was right and I was the one who made
# it wrong: a new verdict with a fixture, and a pinned list in another file
# that nobody updated.
#
# The list lives HERE, beside the returns it names, because the probe pinning a
# copy of it is exactly what went stale. The probe now derives the set the code
# ACTUALLY RETURNS by scanning this module's own `return '<VERDICT>'` sites --
# a structurally different derivation from this tuple -- and requires the two
# to agree AND the fixtures to cover them. A sixth verdict added without a
# fixture fails; one added without being declared here fails too.
VERDICTS = ('GATED', 'UNGATED', 'PUBLIC_BY_DESIGN', 'NO_WRITE', 'COULD_NOT_TELL')

FIXTURES = [
    ('gated',
     "const k=process.env.SUPABASE_SERVICE_ROLE_KEY;\n"
     "verifySessionToken(t);\n"
     "fetch(rest('sv_controlled?x=1'),{method:'POST'});", 'GATED'),
    ('ungated',
     "const k=process.env.SUPABASE_SERVICE_ROLE_KEY;\n"
     "fetch(rest('sv_controlled?x=1'),{method:'POST'});", 'UNGATED'),
    ('public by design with a limiter',
     "// Genuinely public, unauthenticated endpoint\n"
     "const k=process.env.SUPABASE_SERVICE_ROLE_KEY;\n"
     "rate_limit();\n"
     "fetch(rest('dnt_patients?x=1'),{method:'POST'});",
     'PUBLIC_BY_DESIGN'),
    ('public by design with NO limiter',
     "// Genuinely public, unauthenticated endpoint\n"
     "const k=process.env.SUPABASE_SERVICE_ROLE_KEY;\n"
     "fetch(rest('dnt_patients?x=1'),{method:'POST'});", 'UNGATED'),
    ('addressed in a path but never written',
     "const k=process.env.SUPABASE_SERVICE_ROLE_KEY;\n"
     "const u=rest('sv_controlled?x=1');", 'NO_WRITE'),
    # ── v4: THE VARIABLE-DISPATCH BLIND SPOT, KEPT AS FIXTURES ────────────
    # v3 required a QUOTED LITERAL after `rest(`, so it never saw the shape this
    # platform uses most. MEASURED BEFORE THE FIX: 41 of 84 Tier A resources
    # appear only as dispatch-table keys and never as a quoted path -- including
    # sv_controlled, the DEA-relevant controlled-substance register, and
    # sv_audit_log, which carries the witnessing lock. The checker reported
    # CLEAN over all of them.
    ('v4: dispatch-table KEY plus a variable rest() -- the SV_RESOURCES shape',
     "const k=process.env.SUPABASE_SERVICE_ROLE_KEY;\n"
     "const SV_RESOURCES = { sv_controlled: 'controlled_id' };\n"
     "verifySessionToken(t);\n"
     "fetch(rest(resource + '?x=1'),{method:'POST'});", 'GATED'),
    ('v4: ...and UNGATED through the same shape is still caught',
     "const k=process.env.SUPABASE_SERVICE_ROLE_KEY;\n"
     "const SV_RESOURCES = { sv_controlled: 'controlled_id' };\n"
     "fetch(rest(resource + '?x=1'),{method:'POST'});", 'UNGATED'),
    ('v4: the table is the VALUE, not the key',
     "const k=process.env.SUPABASE_SERVICE_ROLE_KEY;\n"
     "const BY_APP = { sairnvet: 'sv_controlled' };\n"
     "fetch(rest(BY_APP[app] + '?x=1'),{method:'POST'});", 'UNGATED'),
    ('v4: opaque dispatch is COULD NOT TELL, never clean',
     "const k=process.env.SUPABASE_SERVICE_ROLE_KEY;\n"
     "fetch(rest(table + '?x=1'),{method:'POST'});", 'COULD_NOT_TELL'),
    ('v4: a module CONSTANT is resolvable -- not a third state',
     "const k=process.env.SUPABASE_SERVICE_ROLE_KEY;\n"
     "const TABLE = 'sairn_ai_rate_limit_log';\n"
     "fetch(rest(TABLE + '?x=1'),{method:'POST'});", None),
    ('v4: declaring the rest() HELPER is not variable dispatch',
     "const k=process.env.SUPABASE_SERVICE_ROLE_KEY;\n"
     "function rest(path) { return BASE + path; }", None),

    # THE THREE REAL FALSE POSITIVES, KEPT AS FIXTURES. Each cost a read of
    # the real file to recover, and each would come straight back under an
    # edit that looked tidier.
    ('the name is only a jsonb KEY -- the write targets another table',
     "const k=process.env.SUPABASE_SERVICE_ROLE_KEY;\n"
     "const d={ invoices: body.invoices || null };\n"
     "fetch(rest('bridge_data?on_conflict=shop_id'),{method:'POST'});",
     None),
    ('the name is a POLICY REGISTRY key -- a real reference, but not a write target',
     "const k=process.env.SUPABASE_SERVICE_ROLE_KEY;\n"
     "const LOCKED_RESOURCES = { sv_controlled: true };", None),
    ('writes in helpers ABOVE the handler, gate first INSIDE it',
     "const k=process.env.SUPABASE_SERVICE_ROLE_KEY;\n"
     "async function helper(){ return fetch(rest('sv_controlled?x=1'),{method:'POST'}); }\n"
     "module.exports=async(req,res)=>{ if(!process.env.CRON_SECRET) return;\n"
     "  await helper(); };", 'GATED'),
]

TIER_A = set()


def self_check(verbose=True):
    global TIER_A
    saved = TIER_A
    TIER_A = {'sv_controlled', 'dnt_patients', 'invoices'}
    bad = []
    try:
        for label, src, want in FIXTURES:
            got, _d = classify('fx.js', src)
            if verbose:
                print('    %-46s -> %-17s %s'
                      % (label, got, 'ok' if got == want else 'EXPECTED %s' % want))
            if got != want:
                bad.append((label, got, want))
    finally:
        TIER_A = saved
    return bad


def main(argv=None):
    global TIER_A
    ap = argparse.ArgumentParser()
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--self-check', action='store_true')
    args = ap.parse_args(argv)

    if args.self_check:
        bad = self_check()
        print('\n%d fixture(s) misclassified' % len(bad))
        return EXIT_CLEAN if not bad else EXIT_FINDING

    # The blind lock runs on EVERY run. A classifier that has silently stopped
    # classifying must not then report the platform clean.
    bad = self_check(verbose=False)
    if bad:
        print('COULD NOT RUN -- the blind lock failed, so nothing was scanned:')
        for label, got, want in bad:
            print('  fixture %r -> %s, expected %s' % (label, got, want))
        return EXIT_COULD_NOT_RUN

    t = tier_a_resources()
    if t is None:
        print('COULD NOT RUN: %s is unreadable, so no resource is known to be '
              'Tier A and every verdict below would be vacuous.' % TIERS_DOC)
        return EXIT_COULD_NOT_RUN
    TIER_A = t

    files, notes = tracked('api/*.js', 'api/**/*.js')
    findings, could_not_run, rows = [], [], []
    for rel in files:
        if rel.endswith('.test.js'):
            continue
        try:
            src = read(os.path.join(REPO, rel))
        except OSError as exc:
            could_not_run.append('%s: %s' % (rel, exc))
            continue
        if KEY not in src:
            continue
        verdict, d = classify(rel, src)
        if verdict is None:
            continue
        rows.append(dict(d, file=rel, verdict=verdict))
        if verdict == 'UNGATED':
            findings.append('%s -- %s (%s)'
                            % (rel, d['why'], ', '.join(d['resources'][:4])))
        elif verdict == 'COULD_NOT_TELL':
            # ── A THIRD STATE IS NEVER FOLDED INTO CLEAN (PR 1.11) ─────────
            # The v4 draft printed COULD_NOT_TELL rows and then ended with
            # "CLEAN -- ran fully, found nothing", which is the two halves of
            # one run disagreeing in the same output. A file whose Tier A
            # surface cannot be read from its source was not scanned; saying
            # the scan found nothing there is a claim about a check that did
            # not happen.
            could_not_run.append('%s: %s' % (rel, d['why']))

    if args.json:
        print(json.dumps({'rows': rows, 'tier_a': len(TIER_A),
                          'could_not_run': could_not_run}, indent=1))
        return finish(findings, could_not_run, quiet=True)

    print('%d Tier A resource(s) declared; %d api/ module(s) read %s'
          % (len(TIER_A), sum(1 for f in files if not f.endswith('.test.js')
                              and KEY in read(os.path.join(REPO, f))), KEY))
    print('%d of them name a Tier A resource IN CODE (comments and strings '
          'blanked first)' % len(rows))
    print('')
    for r in sorted(rows, key=lambda x: (x['verdict'] != 'UNGATED', x['file'])):
        mark = '  ! ' if r['verdict'] == 'UNGATED' else '    '
        print('%s%-17s %-42s %s' % (mark, r['verdict'], r['file'],
                                    ', '.join(r['resources'][:3])))
        if r['verdict'] != 'GATED':
            print('                      %s' % r['why'])
    print('')
    print('GATED IS AN ORDER PROXY, NOT A PROOF. It compares byte offsets, not')
    print('control flow -- it cannot see a gate inside a branch the write does')
    print('not depend on, nor one in a module this file requires. The bias is')
    print('toward GATED, which misses findings rather than inventing them.')
    for n in notes:
        print('  excluded: %s' % n)
    return finish(findings, could_not_run)


if __name__ == '__main__':
    sys.exit(main())
